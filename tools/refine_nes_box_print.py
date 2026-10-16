#!/usr/bin/env python3
"""Restore pristine NES prints from documented, matching original letterforms.

The front uses Nintendo's higher-detail archived REV-A scan as a component
reference. The early round-seal composition remains free of the later REV-A
marker. This is an explicitly documented restoration, not an untouched scan.
No game illustration or proprietary wordmark is generated or re-typeset.

Requires Pillow, NumPy, OpenCV, SciPy and scikit-image. Source PNGs and the documented
front reference are explicit inputs. --body-font and --seal-font allow the
recorded licensed fonts to be supplied from a non-macOS filesystem.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageFont
from skimage.measure import find_contours
from scipy.ndimage import distance_transform_edt

from refine_case_box_artwork import descreen, make_review, set_type

ASSET = 'nes-super-mario-bros-box'
INK = (7, 8, 10)
RED = (239, 65, 28)
YELLOW = (250, 206, 42)
GOLD = (151, 128, 50)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(mask, size, epsilon=.4, minimum=2, grow=0, smooth=0):
    """Fit original ink contours, keep nested counters, and render at 3x.

    The contour fit smooths scanner dots without substituting a font. Masks are
    restricted to reviewed single-ink print components, never a whole photo.
    """
    if smooth:
        coverage=cv2.GaussianBlur(mask.astype(np.float32)/255,(0,0),smooth)
        contours=[np.float32(c[:,::-1]-1).reshape(-1,1,2) for c in find_contours(np.pad(coverage,1),.5)]
    else:
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    scale = 3
    polygons = []
    for contour in contours:
        if cv2.contourArea(contour) < minimum:
            continue
        polygon = np.int32(np.rint(cv2.approxPolyDP(contour, epsilon, True) * scale))
        if len(polygon) > 2:
            polygons.append(polygon)
    raster = np.zeros((mask.shape[0]*scale, mask.shape[1]*scale), np.uint8)
    if polygons:
        cv2.drawContours(raster, polygons, -1, 255, cv2.FILLED)
    if grow:
        raster = cv2.dilate(raster, np.ones((grow, grow), np.uint8))
    return Image.fromarray(raster).resize(size, Image.Resampling.LANCZOS)


def bounded(mask, polygons):
    allowed = np.zeros(mask.shape, np.uint8)
    for polygon in polygons:
        cv2.fillPoly(allowed, [np.array(polygon, np.int32)], 255)
    return mask & allowed


def rectangle(mask, box):
    x0,y0,x1,y1 = box
    return bounded(mask, [[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]])


def put_ink(canvas, mask, color, epsilon=.4, minimum=2, smooth=0):
    canvas.paste(color, (0,0,*canvas.size), trace(mask, canvas.size, epsilon, minimum,smooth=smooth))


def remove_small(mask, minimum):
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    keep = np.zeros_like(mask)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] >= minimum:
            keep[labels == label] = 255
    return keep


def clean_illustration(image):
    """Restore flat pixel-art ink without replacing the original composition.

    Estimate the source palette from the bounded Mario/block area. Region
    interiors lose scanner grain; straight polygon segments follow the source
    ink boundaries. Fine motion streaks remain protected optical originals.
    """
    a=np.array(image.resize((1390,2048),Image.Resampling.LANCZOS))
    allowed=np.zeros(a.shape[:2],np.uint8)
    cv2.fillPoly(allowed,[np.int32([(100,125),(1285,125),(1285,945),(125,1167),(100,1167)])],255)

    def classify(sigma):
        smooth=cv2.GaussianBlur(a,(0,0),sigma)
        lab=cv2.cvtColor(smooth,cv2.COLOR_RGB2LAB).astype(np.float32)
        valid=(allowed>0)&(a.max(2)>58)
        samples=lab[valid][::4]
        cv2.setRNGSeed(1942)
        criteria=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,100,.05)
        _,_,centers=cv2.kmeans(samples,14,None,criteria,8,cv2.KMEANS_PP_CENTERS)
        palette=cv2.cvtColor(np.uint8(np.clip(centers,0,255))[None,:,:],cv2.COLOR_LAB2RGB)[0]
        classes=((lab[:,:,None,:]-centers[None,None,:,:])**2).sum(3).argmin(2)
        return smooth,valid,classes,palette

    _,valid,classes,palette=classify(2.0)
    edges=np.zeros(valid.shape,np.uint8)
    edges[1:]|=np.uint8(classes[1:]!=classes[:-1])
    edges[:,1:]|=np.uint8(classes[:,1:]!=classes[:,:-1])
    edges[~valid]=1
    distance=cv2.distanceTransform(1-edges,cv2.DIST_L2,5)
    weight=np.clip((distance-1)/3,0,1)*valid
    flat=a*(1-weight[:,:,None])+palette[classes]*weight[:,:,None]
    base=image.copy()
    base.paste(Image.fromarray(np.uint8(flat)).resize(image.size,Image.Resampling.LANCZOS),
               (0,0),Image.fromarray(np.uint8(weight*255)).resize(image.size,Image.Resampling.LANCZOS))

    smooth,_,classes,palette=classify(1.1)
    valid=(allowed>0)&(smooth.max(2)>54)
    classes[~valid]=14
    palette=np.concatenate([palette,[INK]]).astype(np.uint8)
    white=np.where(palette[:14].min(1)>200)[0]
    primary=white[np.argmax(palette[white].mean(1))]
    for i in white:classes[classes==i]=primary
    # Discard mixed-color fringe classes that have no real printed interior.
    seeds=np.full(classes.shape,255,np.uint8)
    for i in range(15):
        distance=cv2.distanceTransform(np.uint8(classes==i),cv2.DIST_L2,5)
        core=distance>1.8
        if core.sum()>250:seeds[core]=i
    _,indices=distance_transform_edt(seeds==255,return_indices=True)
    filled=seeds[tuple(indices)]
    contours=base.copy()
    for i,color in enumerate(palette):
        mask=np.uint8((filled==i)&(allowed>0))*255
        # Pixel artwork needs straight segments and sharp corners, not a
        # smoothed curve through scanner wobble. No spline smoothing here.
        coverage=trace(mask,image.size,3.8,25,smooth=0)
        contours.paste(tuple(int(x) for x in color),(0,0,*image.size),coverage)
    for polygon in [
        [(400,175),(520,145),(540,245),(398,272)],
        [(100,310),(330,260),(335,360),(100,410)],
        [(100,410),(280,365),(310,620),(100,665)],
        [(100,715),(250,675),(260,705),(100,750)],
        [(100,830),(300,800),(330,1015),(100,1075)],
    ]:cv2.fillPoly(allowed,[np.int32(polygon)],0)
    base.paste(contours,(0,0),Image.fromarray(allowed).resize(image.size,Image.Resampling.NEAREST))
    return base


def front(reference, size, seal_image):
    a = np.array(reference.convert('RGB')).astype(np.float32)
    r,g,b = a[:,:,0],a[:,:,1],a[:,:,2]
    canvas = Image.new('RGB', size, INK)
    # Preserve the actual original Mario illustration, including the painted
    # overlapping blocks and speed lines. The finer source scan replaces the
    # previous low-resolution specimen photograph; no pixel-art redesign.
    smooth = np.array(descreen(reference, .7, 1.2, .2))
    foreground = ((a.max(2)>44)&((a.max(2)-a.min(2)>14)|(a.min(2)>125))).astype(np.uint8)*255
    foreground = rectangle(foreground, (100,125,1285,1167))
    # The lower bound follows the original illustration, above the title.
    foreground = bounded(foreground, [[(100,125),(1285,125),(1285,945),(125,1167),(100,1167)]])
    foreground = remove_small(foreground, 13)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))
    mask = Image.fromarray(foreground).filter(ImageFilter.GaussianBlur(.45))
    canvas.paste(Image.fromarray(smooth).resize(size,Image.Resampling.LANCZOS),(0,0),mask.resize(size,Image.Resampling.LANCZOS))
    # Exact original red title and Nintendo capsule, with the original counters
    # and glyph shapes. The skew is artwork, not a perspective correction.
    red = ((r-g>65)&(r-b>75)&(r>110)).astype(np.uint8)*255
    red = bounded(red, [[(110,1170),(750,1030),(1335,1030),(1335,1260),(1170,1365),(645,1550),(110,1575)]])
    red = cv2.morphologyEx(red,cv2.MORPH_CLOSE,np.ones((2,2),np.uint8))
    red = np.uint8(cv2.GaussianBlur(red,(0,0),.8)>127)*255
    put_ink(canvas, red, RED, .2, 2, smooth=1.05)
    yellow = ((r>125)&(g>115)&(b<105)&(r-b>50)&(g-b>50)).astype(np.uint8)*255
    yellow_wordmark=np.uint8(cv2.GaussianBlur(rectangle(yellow,(630,1230,1320,1465)),(0,0),.55)>127)*255
    put_ink(canvas,yellow_wordmark,YELLOW,.35,1,smooth=.65)
    white=(a.min(2)>130).astype(np.uint8)*255
    put_ink(canvas,rectangle(white,(1120,1330,1154,1359)),(242,240,230),.18,1)
    # Original Action Series emblem: white outline, yellow explosion and panel,
    # including the original negative-space black lettering.
    action=(115,1560,530,2020)
    put_ink(canvas,rectangle(white,action),(245,244,232),.45,2)
    put_ink(canvas,rectangle(yellow,action),YELLOW,.45,2)
    # Solid panel ink and exact original black Action Series letter contours
    # avoid reproducing the scan's pinholes inside this tiny badge.
    panel=np.zeros(r.shape,np.uint8)
    cv2.fillPoly(panel,[np.int32(((137,1922),(438,1922),(395,2007),(137,2007)))],255)
    put_ink(canvas,panel,YELLOW,.15,1)
    black=((r<105)&(g<105)&(b<105)).astype(np.uint8)*255
    black=rectangle(black,(145,1936,403,1980))
    put_ink(canvas,black,INK,.15,1,smooth=.5)
    # The original round quality seal has the same wording on this early print.
    # Its contour-traced ink removes scan grit while preserving its glyphs.
    seal_box = (946,1586,1300,1948)
    paste_scaled(canvas, seal_image, seal_box, reference.size)
    # Only identifiable printed stars. Random paper fibers and abrasion are not
    # transcribed into the restored black ink.
    for x,y,rad in ((578,62,10),(44,1796,18),(768,1570,13),(1382,1511,18),(1287,1590,12),
                    (1349,827,8),(781,48,5),(90,264,4),(91,870,4),(1110,1064,4),
                    (754,1733,5),(509,1730,4),(689,1827,4),(813,1995,5)):
        patch=np.zeros((a.shape[0],a.shape[1]),np.uint8)
        cv2.circle(patch,(x,y),rad,255,-1)
        value=np.clip((a.max(2)-50)/120,0,1)
        coverage=np.uint8(value*patch)
        canvas.paste(reference.resize(size,Image.Resampling.LANCZOS),(0,0),Image.fromarray(coverage).resize(size,Image.Resampling.LANCZOS))
    return canvas


def paste_scaled(canvas, image, box, source_size):
    x0,y0,x1,y1 = box
    sx,sy = canvas.width/source_size[0],canvas.height/source_size[1]
    dest=(round(x0*sx),round(y0*sy),round(x1*sx),round(y1*sy))
    canvas.paste(image.resize((dest[2]-dest[0],dest[3]-dest[1]),Image.Resampling.LANCZOS),dest[:2])


def seal(rear_reference,font_path=Path('/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf')):
    """Restore the original round-seal construction with exact readable copy.

    The tiny source text cannot support pristine contour recovery. Its words
    are transcribed in a documented approximate narrow sans-serif, while the
    Nintendo capsule uses the actual original glyph outlines.
    """
    side=1080;im=Image.new('RGB',(side,side),INK);d=ImageDraw.Draw(im)
    center=side/2
    points=[]
    for i in range(128):
        angle=np.pi*2*i/128-np.pi/2
        radius=526 if i%2==0 else 491
        points.append((center+np.cos(angle)*radius,center+np.sin(angle)*radius))
    d.polygon(points,fill=GOLD);d.ellipse((100,100,980,980),fill=INK)
    font=ImageFont.truetype(str(font_path),64)
    def line(text,box):
        b=font.getbbox(text);m=Image.new('L',(b[2]-b[0]+4,b[3]-b[1]+4));ImageDraw.Draw(m).text((2-b[0],2-b[1]),text,font=font,fill=255)
        m=m.resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
        im.paste(GOLD,box,m)
    for text,box in [('THIS SEAL IS',(360,226,720,273)),('YOUR ASSURANCE THAT',(231,302,849,349)),
                     ('HAS APPROVED AND',(261,588,819,635)),('GUARANTEED THE',(297,665,783,712)),
                     ('QUALITY OF THIS',(308,742,772,789)),('PRODUCT.',(408,819,672,866))]:line(text,box)
    # The front Nintendo capsule is intentionally slanted; the rear supplies
    # the matching original horizontal capsule for this circular emblem.
    rear=np.array(rear_reference.convert('RGB').crop((818,1510,1374,1651))).astype(float)
    mask=((rear[:,:,0]-np.maximum(rear[:,:,1],rear[:,:,2]))>70).astype(np.uint8)*255
    m=trace(mask,(793,201),.2,1,smooth=.8)
    im.paste(GOLD,(144,385,937,586),m)
    return im


def rear(image, size, seal_image):
    a=np.array(image).astype(float)
    canvas=Image.new('RGB',size,INK)
    r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    # Retain the four original CRT photographs and their borders. Their CRT
    # raster is part of the printed design; it is not replacement gameplay.
    smooth=descreen(image,.55,1.0,.15)
    for box in ((737,299,1366,806),(54,1136,502,1492),(499,1136,932,1492),(938,1132,1377,1494)):
        x0,y0,x1,y1=box
        dest=tuple(round(v*size[0]/image.width) if i%2==0 else round(v*size[1]/image.height) for i,v in enumerate(box))
        patch=np.array(smooth.crop(box));patch[patch.max(2)<27]=INK
        canvas.paste(Image.fromarray(patch).resize((dest[2]-dest[0],dest[3]-dest[1]),Image.Resampling.LANCZOS),dest[:2])
    red=((r-g>70)&(r-b>70)&(r>100)).astype(np.uint8)*255
    red=rectangle(red,(80,290,730,475))|rectangle(red,(806,1498,1385,1650))
    put_ink(canvas,red,RED,.2,1,smooth=.8)
    white=(a.min(2)>105).astype(np.uint8)*255
    regions=((70,15,350,70),(90,497,696,707),(90,736,720,818),(90,818,1350,1066),
             (91,1080,360,1126),(666,1080,1350,1126),(810,1643,1110,1690),(382,1940,1375,2015))
    all_text=np.zeros(white.shape,np.uint8)
    for box in regions:all_text|=rectangle(white,box)
    # Thin body copy does not survive binarization. Retain its original smooth
    # optical coverage instead of fragmenting or widening the small letters.
    coverage=np.uint8(np.clip((a.max(2)-30)/190,0,1)*255)
    allowed=np.zeros_like(white)
    for box in regions:allowed|=rectangle(np.full_like(white,255),box)
    canvas.paste((242,241,231),(0,0,*size),Image.fromarray(coverage&allowed).resize(size,Image.Resampling.LANCZOS))
    # Barcode and action symbol remain original pixels, cleaned into two-color
    # contours in explicitly bounded printed fields.
    barcode=rectangle(white,(30,1580,346,2004))
    put_ink(canvas,barcode,(249,248,240),.18,.5)
    action=(1118,1671,1351,1938)
    put_ink(canvas,rectangle(white,action),(242,241,231),.2,1)
    yellow=((r>125)&(g>115)&(r-b>40)&(g-b>40)).astype(np.uint8)*255
    put_ink(canvas,rectangle(yellow,action),YELLOW,.2,1)
    paste_scaled(canvas,seal_image,(377,1558,734,1901),image.size)
    # Identifiable stars retained from original rear, excluding all text/art.
    for x,y,rad in ((887,64,10),(662,242,9),(690,385,12),(1408,511,9),(1330,943,12),
                    (15,1054,8),(1430,861,8),(418,1547,8),(957,1797,13),(327,2040,12)):
        coverage=np.zeros(a.shape[:2],np.uint8);cv2.circle(coverage,(x,y),rad,255,-1)
        coverage=np.uint8(coverage*np.clip((a.max(2)-45)/140,0,1))
        canvas.paste(image.resize(size,Image.Resampling.LANCZOS),(0,0),Image.fromarray(coverage).resize(size,Image.Resampling.LANCZOS))
    return canvas


def rectified_glyphs(reference,quad,size,yellow=False,main=False):
    a=np.array(reference).astype(float);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    mask=((r>125)&(g>115)&(b<105)&(r-b>50)&(g-b>50)) if yellow else ((r-g>65)&(r-b>75)&(r>110))
    mask=np.uint8(mask)*255
    if main:
        count,labels,stats,centers=cv2.connectedComponentsWithStats(mask,8)
        selected=np.zeros_like(mask)
        for label in range(1,count):
            x,y,w,h,area=stats[label]
            if (y>1000 and h>120 and area>3000) or (centers[label,0]>1280 and 1120<centers[label,1]<1250 and area>100):
                selected[labels==label]=255
        mask=selected
    transform=cv2.getPerspectiveTransform(np.float32(quad),np.float32(((0,0),(size[0]-1,0),(size[0]-1,size[1]-1),(0,size[1]-1))))
    return cv2.warpPerspective(mask,transform,size,flags=cv2.INTER_CUBIC)


def flat_edge(slot,image,reference,rear_reference,font_path=Path('/System/Library/Fonts/Supplemental/Arial Narrow.ttf')):
    horizontal=(image.height*2,image.width*2) if slot.startswith('Spine') else (image.width*2,image.height*2)
    canvas=Image.new('RGB',horizontal,INK)
    if slot=='Bottom':return canvas
    super_mask=rectified_glyphs(reference,((111,1180),(344,1132),(354,1211),(115,1257)),(460,150))
    main_mask=rectified_glyphs(reference,((125,1238),(1331,1018),(1340,1223),(136,1450)),(1200,210),main=True)
    main_mask=remove_small(np.uint8(main_mask>127)*255,60)
    console_mask=rectified_glyphs(reference,((637,1350),(1305,1224),(1313,1372),(645,1498)),(700,150),True)
    a=np.array(rear_reference.crop((818,1510,1374,1651))).astype(float)
    nintendo=((a[:,:,0]-np.maximum(a[:,:,1],a[:,:,2]))>70).astype(np.uint8)*255
    def mark(mask,box,color=RED):
        box=tuple(v*2 for v in box);m=trace(mask,(box[2]-box[0],box[3]-box[1]),.2,1,smooth=.85)
        canvas.paste(color,box,m)
    def line(text,box):
        set_type(canvas,text,tuple(v*2 for v in box),font_path,(242,241,231))
    if slot=='Top':
        mark(super_mask,(390,16,509,77));mark(main_mask,(383,94,1039,262))
        line('NINTENDO of America Inc.',(129,288,401,317))
        line('P.O. Box 957 Redmond, WA 98052 U.S.A.',(129,332,573,361))
        line('Made in Japan',(1138,332,1300,361))
    elif slot=='SpineLeft':
        mark(super_mask,(83,35,202,94));mark(main_mask,(70,111,724,279));mark(nintendo,(1012,77,1418,247))
        mark(console_mask,(1423,96,2008,246),YELLOW)
        canvas=canvas.rotate(-90,expand=True)
    else:
        mark(super_mask,(145,101,273,159));mark(main_mask,(137,181,826,350))
        line('WARRANTY',(1342,122,1495,161))
        line('90 day limited warranty for game pak',(1342,205,1910,241))
        line('(complete warranty information inside box)',(1342,269,1930,305))
        canvas=canvas.rotate(90,expand=True)
    return canvas


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path('dist/box-refinement-20261016/artwork')/ASSET)
    parser.add_argument('--reference',type=Path,default=Path('dist/nes-print-sharpness-20261016/references/mariowiki-10.jpg'))
    parser.add_argument('--output',type=Path,default=Path('dist/box-polish-20261016/artwork')/ASSET)
    parser.add_argument('--body-font',type=Path,default=Path('/System/Library/Fonts/Supplemental/Arial Narrow.ttf'))
    parser.add_argument('--seal-font',type=Path,default=Path('/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf'))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    mapping=json.loads((args.input/'mapping.json').read_text())
    before={slot:Image.open(args.input/(slot+'.png')).convert('RGB') for slot in mapping}
    reference=Image.open(args.reference).convert('RGB')
    after={};records={};outmap={};seal_image=seal(before['Back'],args.seal_font)
    for slot,image in before.items():
        size=(image.width*2,image.height*2)
        if slot=='Front':
            result=clean_illustration(front(reference,size,seal_image))
            method='Higher-detail Nintendo-attributed original scan supplies matching illustration and exact letter contours. Bounded Mario/block ink regions use a fitted 14-color palette and straight polygon contours to remove paper grain and shoe scuffs, retaining the original angular silhouette, blue offsets and protected fine speed lines. Single-ink title, console wordmark and Action Series emblem are contour restored; round seal combines original Nintendo glyphs with exact wording in an approximate narrow sans-serif. Clean black field excludes the later REV-A marker to retain the selected early composition.'
        elif slot=='Back':
            result=rear(image,size,seal_image)
            method='Original letter contours, barcode and Action Series emblem restored to clean ink; thin body copy retains optical coverage; original four photographed CRT screenshots retained. Round seal reconstructed with original Nintendo glyphs and exact transcribed wording in an approximate narrow sans-serif. Only identifiable printed stars retained in fresh black fields.'
        else:
            result=flat_edge(slot,image,reference,before['Back'],args.body_font)
            method='Front-scan title and console glyphs rectified into the existing documented edge layout, with subpixel-smoothed single-ink contours. Matching rear Nintendo capsule retained; exact prior address/warranty transcription typeset freshly in the same approximate narrow sans-serif.'
        path=args.output/(slot+'.png');result.save(path,optimize=True)
        after[slot]=result;outmap[slot]=str(path.resolve())
        records[slot]=dict(inputFile=slot+'.png',inputSha256=sha(args.input/(slot+'.png')),outputFile=slot+'.png',outputSha256=sha(path),outputPixels=list(result.size),method=method)
    (args.output/'mapping.json').write_text(json.dumps(outmap,indent=2)+'\n')
    provenance=dict(assetId=ASSET,workflow='Deterministic original-contour print restoration; no generative illustration.',previousProvenanceSha256=sha(args.input/'provenance.json'),
        reference=dict(id='smb-nintendo-front-archived-2048',file=args.reference.name,sha256=sha(args.reference),pixelSize=list(reference.size),sourcePage='https://www.mariowiki.com/File:SMB_USA_box_art.jpg',imageUrl='https://www.mariowiki.com/images/archive/6/6b/20230713105640%21SMB_USA_box_art.jpg',credit='Nintendo; historical image archived by Super Mario Wiki, attributed to Nintendo Facebook.',usage='Matching original print components only; later REV-A marker omitted for early-edition restoration.'),
        limitations=['Restored composite, not an untouched factory print or complete new scan.','Front title, Nintendo and console wordmark shapes are traced from original print, not substitute typefaces. Contour smoothing removes optical roughness; colors are visual estimates.','Round seal border is reconstructed; exact original wording uses approximate Arial Narrow Bold while the Nintendo capsule preserves original glyph contours.','Mario/block illustration uses fitted flat ink colors and polygonal contours from the original print. This restores its pixel-art appearance rather than recovering new scan detail. Fine speed lines and original rear CRT screenshots remain optical source imagery.','Earlier documented edge address/warranty typeface remains an approximation.'],faces=records)
    provenance['sealTypeface']=dict(file=args.seal_font.name,sha256=sha(args.seal_font))
    records['Front']['additionalPreparedInputs']=[dict(file='Back.png',sha256=sha(args.input/'Back.png'),usage='Original horizontal Nintendo glyphs for the round seal.')]
    for slot in ('Top','SpineLeft','SpineRight'):
        records[slot]['additionalPreparedInputs']=[dict(file=args.reference.name,sha256=sha(args.reference),usage='Original front title and console letterforms rectified into the documented narrow-panel layout.'),dict(file='Back.png',sha256=sha(args.input/'Back.png'),usage='Original horizontal Nintendo capsule.')]
    (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    make_review(before,after,args.output)
    strip=Image.new('RGB',(2400,780),(20,23,28))
    for i,(label,im) in enumerate((('Before',before['Front']),('Restored original lettering',after['Front']))):
        crop=im.crop((round(im.width*.08),round(im.height*.50),round(im.width*.96),round(im.height*.79)))
        crop=ImageOps.contain(crop,(1160,700));strip.paste(crop,(i*1200+20,60))
        ImageDraw.Draw(strip).text((i*1200+20,20),label,fill='white')
    strip.save(args.output/'front-type-before-after.jpg',quality=96)
    print(f'{ASSET}: {len(records)} restored print faces')


if __name__=='__main__':main()
