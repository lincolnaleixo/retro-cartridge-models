#!/usr/bin/env python3
"""Reconstruct clean Sonic European box print from the documented original scan.

Original letter outlines are traced into antialiased flat ink; the decorative
grid is measured and redrawn. The original shaded illustration is denoised,
while its cream/pink background is separated from paper dirt. This is an
explicit restoration, not an assertion that a new factory master was found.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

INK = (8, 10, 13)
GRID = (39, 41, 44)
BLUE = (0, 88, 187)
WHITE = (247, 247, 242)
SCALE = 2
SEGA_REFERENCE = Path('dist/box-polish-20261016/references/sega-logo.png')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(mask, scale=SCALE, smooth=.8, minimum=2):
    """Trace observed contours, including counters, at subpixel output scale."""
    a = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), smooth)
    binary = np.uint8(a > .48) * 255
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros((mask.shape[0]*scale, mask.shape[1]*scale), np.uint8)
    paths = []
    for i, contour in enumerate(contours):
        if abs(cv2.contourArea(contour)) < minimum:
            continue
        depth, parent = 0, hierarchy[0][i][3]
        while parent != -1:
            depth += 1
            parent = hierarchy[0][parent][3]
        poly = cv2.approxPolyDP(contour, .5, True)
        cv2.fillPoly(out, [np.rint(poly*scale).astype(np.int32)], 255 if depth % 2 == 0 else 0,
                     lineType=cv2.LINE_AA)
        paths.append({'hole': bool(depth % 2), 'points': poly[:, 0].tolist()})
    return Image.fromarray(out), paths


def gray_mask(image):
    a = np.asarray(image).astype(float)
    return np.clip((a.min(2)-50)/140, 0, 1)


def blue_mask(image):
    a = np.asarray(image).astype(float)
    return np.clip((a[:, :, 2]-a[:, :, 0]-35)/65, 0, 1)


def paste_ink(out, original, box, color, mode='white', contours=None, key=None):
    crop = original.crop(box)
    raw = blue_mask(crop) if mode == 'blue' else gray_mask(crop)
    mask, paths = trace(raw)
    out.paste(Image.new('RGB', mask.size, color), (box[0]*SCALE, box[1]*SCALE), mask)
    if contours is not None:
        contours[key] = {'sourceBox': box, 'sourcePixels': crop.size, 'paths': paths}


def grid(size, x0=0, y0=0, step=124):
    out = Image.new('RGB', (size[0]*SCALE, size[1]*SCALE), INK)
    d = ImageDraw.Draw(out)
    for x in range(x0, size[0], step):
        d.line((x*SCALE, 0, x*SCALE, out.height), fill=GRID, width=2*SCALE)
    for y in range(y0, size[1], step):
        d.line((0, y*SCALE, out.width, y*SCALE), fill=GRID, width=2*SCALE)
    return out


def denoise(im):
    # Remove scanner speckles without turning the original airbrushed shading
    # into flat colors. Text is reconstructed separately, never blurred here.
    a = cv2.fastNlMeansDenoisingColored(np.array(im), None, 4.5, 7.0, 7, 21)
    a = cv2.bilateralFilter(a, 5, 15, 1.2)
    return Image.fromarray(a)


def clean_chrome(source):
    a = np.asarray(source).copy()
    a = cv2.fastNlMeansDenoisingColored(a, None, 5, 9, 7, 21)
    # Restore the black plate independently from the deliberate chrome bands.
    dark = a.max(2) < 49
    a[dark] = INK
    return Image.fromarray(a).resize((source.width*SCALE, source.height*SCALE), Image.Resampling.LANCZOS)


def sega_logo(size, color=BLUE):
    """Render the archived clean SEGA wordmark with its printed white keyline."""
    original=Image.open(SEGA_REFERENCE).convert('RGBA')
    data=np.asarray(original).astype(float)
    a=Image.fromarray(np.uint8(np.clip((data[:,:,2]-data[:,:,0]-20)/80,0,1)*data[:,:,3]))
    logo=Image.new('RGBA',original.size,(*color,255));logo.putalpha(a)
    # Fill internal keyline gaps as white, using the wordmark silhouette.
    raw=np.uint8(np.array(a)>100)*255
    contours_,_=cv2.findContours(raw,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    silhouette=np.zeros(raw.shape,np.uint8)
    cv2.drawContours(silhouette,contours_,-1,255,-1)
    silhouette=cv2.dilate(silhouette,np.ones((25,25),np.uint8))
    background=Image.new('RGBA',original.size,(*WHITE,255));background.putalpha(Image.fromarray(silhouette))
    background.alpha_composite(logo)
    return background.resize(size,Image.Resampling.LANCZOS)


def chrome_cutout(front):
    """Reconstruct the measured chrome plate with clean original letter paths.

    The silver/gold reflection bands are a documented graphic approximation;
    their printed shape is independent of a 3D material or artificial wear.
    """
    w,h=919*SCALE,149*SCALE
    chrome=Image.new('RGBA',(w,h));mask=Image.new('L',(w,h));d=ImageDraw.Draw(mask)
    d.ellipse((0,61*SCALE,918*SCALE,145*SCALE),fill=255)
    d.polygon([(x*SCALE,y*SCALE) for x,y in [(145,69),(318,55),(340,36),(365,58),(555,58),(575,36),(602,55),(775,69)]],fill=255)
    stops=[(0,(31,50,80)),(.27,(160,183,215)),(.43,(250,251,250)),(.55,(57,66,81)),(.64,(244,246,242)),(.74,(246,246,232)),(.79,(35,32,26)),(.87,(177,139,64)),(1,(248,246,227))]
    ramp=np.stack([np.interp(np.linspace(0,1,h),[s[0] for s in stops],[s[1][c] for s in stops]) for c in range(3)],1)
    gradient=Image.fromarray(np.uint8(np.tile(ramp[:,None,:],(1,w,1))))
    chrome.paste(gradient,(0,0),mask)
    d=ImageDraw.Draw(chrome);d.ellipse((13*SCALE,67*SCALE,904*SCALE,138*SCALE),fill=(*INK,255))
    # Original MEGA DRIVE lettering is traced from the larger front scan.
    box=(350,140,1107,192);a=np.asarray(front.crop(box)).astype(float)
    raw=np.uint8(a.max(2)>65)*255
    # Treat the deliberate horizontal split separately: closing photographic
    # nicks must never bridge the characteristic top bars to the lower glyphs.
    for y0,y1 in ((0,14),(16,49)):
        raw[y0:y1]=cv2.morphologyEx(raw[y0:y1],cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    raw[14:16]=0;raw[49:]=0
    n,labels,stats,_=cv2.connectedComponentsWithStats(255-raw,8)
    for i in range(1,n):
        x,y,cw,ch,area=stats[i]
        if area<160 and x>0 and y>0 and x+cw<raw.shape[1] and y+ch<raw.shape[0]:raw[labels==i]=255
    glyphs,_=trace(raw/255,smooth=1.1,minimum=6)
    # Place the reflection bands inside the original split-letter outlines.
    bands=[(0,(158,180,211)),(.22,(226,234,243)),(.28,(58,69,83)),(.34,(243,246,241)),(.52,(255,255,250)),(.59,(24,25,22)),(.72,(183,145,70)),(.86,(218,206,162)),(1,(250,250,238))]
    gh=glyphs.height;gw=glyphs.width
    gr=np.stack([np.interp(np.linspace(0,1,gh),[s[0] for s in bands],[s[1][c] for s in bands]) for c in range(3)],1)
    fill=Image.fromarray(np.uint8(np.tile(gr[:,None,:],(1,gw,1))))
    chrome.paste(fill,((350-266)*SCALE,(140-61)*SCALE),glyphs)
    for x in (39,878):
        d.ellipse(((x-10)*SCALE,94*SCALE,(x+10)*SCALE,111*SCALE),fill=(238,236,213,255))
        d.line(((x-9)*SCALE,104*SCALE,(x+9)*SCALE,104*SCALE),fill=(*INK,255),width=3*SCALE)
    oval=Image.new('L',(w,h));ImageDraw.Draw(oval).ellipse((354*SCALE,7*SCALE,558*SCALE,66*SCALE),fill=255)
    chrome.paste(gradient,(0,0),oval)
    ImageDraw.Draw(chrome).ellipse((354*SCALE,7*SCALE,558*SCALE,66*SCALE),outline=(239,238,224,255),width=2*SCALE)
    badge=sega_logo((108*SCALE,36*SCALE),(18,40,77));chrome.alpha_composite(badge,(403*SCALE,15*SCALE))
    return chrome


def clean_front(source, contours):
    a = np.asarray(source).astype(float)
    smooth = denoise(source)
    spot_mask=np.zeros((source.height,source.width),np.uint8)
    # Three isolated, reviewed scan defects in otherwise continuous original
    # shading: a white head chip, a dark belly speck and a cyan body fleck.
    for x,y,radius in ((1189,373,5),(876,978,5),(942,996,5)):
        cv2.circle(spot_mask,(x,y),radius,255,-1)
    smooth=Image.fromarray(cv2.inpaint(np.asarray(smooth),spot_mask,5,cv2.INPAINT_TELEA))
    # Identify the cream/pink printing, then isolate the single connected Sonic
    # silhouette so eye/glove highlights and warm shaded skin remain intact.
    background = ((a[:, :, 0] > 178) & (a[:, :, 1] > 148) &
                  (a[:, :, 2] > 130) & (a[:, :, 0]-a[:, :, 1] > 6))
    candidate = np.uint8(~background)
    candidate[:225] = 0
    candidate[1550:] = 0
    n, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, 8)
    label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    shape = np.uint8(labels == label)
    cs, _ = cv2.findContours(shape, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    shape[:] = 0
    cv2.drawContours(shape, cs, -1, 1, -1)
    shape = cv2.dilate(shape, np.ones((3, 3), np.uint8))
    clean = np.asarray(smooth).copy()
    cream = np.array((253, 244, 217)); pink = np.array((240, 186, 174))
    coverage = np.clip((a[:, :, 0]-a[:, :, 1]-11)/36, 0, 1)
    coverage = cv2.GaussianBlur(coverage, (0, 0), .5)
    paper = cream[None, None, :]*(1-coverage[:, :, None])+pink[None, None, :]*coverage[:, :, None]
    allowed = shape == 0
    allowed[1475:] = False
    allowed[61:211, 260:1187] = False
    clean[allowed] = np.uint8(paper[allowed])
    # The outside paper at either side of the lower title plinth also retains
    # the original pink design, without yellow paper stains or scan grain.
    for y in range(1475, 1734):
        left = max(0, int(345-(y-1475)*.55)-14)
        right = min(source.width, int(1120+(y-1475)*.55)+22)
        sel = shape[y, :left] == 0
        clean[y, :left][sel] = np.uint8(paper[y, :left][sel])
        sel = shape[y, right:] == 0
        clean[y, right:][sel] = np.uint8(paper[y, right:][sel])
    out = Image.fromarray(clean).resize((source.width*SCALE, source.height*SCALE), Image.Resampling.LANCZOS)
    fresh_grid = grid(source.size, 103, 1575, 124)
    region = Image.new('L', out.size)
    ImageDraw.Draw(region).polygon([(x*SCALE,y*SCALE) for x,y in
        [(218,1750),(328,1550),(1136,1550),(1247,1750),(1441,1750),(1441,2026),(0,2026),(0,1750)]], fill=255)
    out.paste(fresh_grid, (0, 0), region)
    paste_ink(out, source, (330,1595,1124,1777), BLUE, 'blue', contours, 'front-title')
    paste_ink(out, source, (337,1790,1125,1855), WHITE, contours=contours,key='front-subtitle')
    paste_ink(out, source, (68,1890,1060,1982), WHITE, contours=contours,key='front-cartridge-copy')
    # The two-color SEGA outline is traced independently to avoid retaining
    # photographed holes and paper flecks inside its white keyline.
    logo=sega_logo((252*SCALE,83*SCALE))
    out.paste(logo,(1110*SCALE,1895*SCALE),logo)
    box=(266,61,1185,210)
    # Erase the photographed logo only inside its original silhouette, then
    # apply the restored plate in the same placement.
    old=source.crop(box);a=np.asarray(old).astype(float)
    old_ink=(a.min(2)<145)|((a.max(2)-a.min(2)<22)&(a.min(2)>160))
    old_ink=cv2.morphologyEx(np.uint8(old_ink)*255,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    cs,_=cv2.findContours(old_ink,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    old_ink[:]=0
    for c in cs:
        if cv2.contourArea(c)>250:cv2.drawContours(old_ink,[c],-1,255,-1)
    old_ink=cv2.dilate(old_ink,np.ones((3,3),np.uint8))
    coverage=np.clip((a[:,:,0]-a[:,:,1]-11)/36,0,1);coverage[old_ink>0]=0
    cream=np.array((253,244,217));pink=np.array((240,186,174))
    paper=cream*(1-coverage[:,:,None])+pink*coverage[:,:,None]
    patch=Image.fromarray(np.uint8(paper)).resize((old.width*SCALE,old.height*SCALE),Image.Resampling.LANCZOS)
    logo=chrome_cutout(source);patch.paste(logo,(0,0),logo)
    out.paste(patch,(box[0]*SCALE,box[1]*SCALE))
    return out


def clean_spine(source, front, contours):
    out = grid(source.size,45,86,124)
    # Use the larger original front title, not the narrow and softened scan
    # from the folded spine. Its observed proportions remain those of the spine.
    title=front.crop((330,1595,1124,1777)); mask,paths=trace(blue_mask(title))
    logo=Image.new('RGBA',mask.size,(*BLUE,255)); logo.putalpha(mask)
    logo=logo.resize((562*SCALE,121*SCALE),Image.Resampling.LANCZOS).rotate(-90,expand=True)
    out.paste(logo,(143*SCALE,300*SCALE),logo)
    sub=front.crop((337,1790,1125,1855)); mask,_=trace(gray_mask(sub))
    logo=Image.new('RGBA',mask.size,(*WHITE,255));logo.putalpha(mask)
    logo=logo.resize((548*SCALE,31*SCALE),Image.Resampling.LANCZOS).rotate(-90,expand=True)
    out.paste(logo,(87*SCALE,308*SCALE),logo)
    chrome=chrome_cutout(front).resize((685*SCALE,116*SCALE),Image.Resampling.LANCZOS).rotate(-90,expand=True)
    out.paste(chrome,(102*SCALE,1259*SCALE),chrome)
    contours['spine-title']={'source':'Front.png','sourceBox':(330,1595,1124,1777),'paths':paths}
    return out


def clean_back(source, front, contours):
    out=grid(source.size,101,89,124)
    ImageDraw.Draw(out).rectangle((38*SCALE,240*SCALE,out.width,1795*SCALE), fill=INK)
    # Every text line and screenshot remains in the observed original layout.
    # White original glyphs get antialiased clean ink; no wording is guessed.
    for box,key in [((455,470,1395,1670),'multilingual-copy'),((795,280,1385,390),'players'),
                    ((55,1710,770,1790),'patents'),((50,1880,900,1965),'copyright')]:
        paste_ink(out,source,box,WHITE,contours=contours,key=key)
    paste_ink(out,source,(70,280,493,385),BLUE,'blue',contours,'back-title')
    paste_ink(out,source,(70,390,495,430),WHITE,contours=contours,key='back-subtitle')
    # Screen images and barcode need their original pixels and exact digits.
    for box in [(64,466,432,745),(64,795,432,1072),(64,1120,432,1400),
                (64,1451,432,1722),(999,1721,1364,1960)]:
        patch=denoise(source.crop(box)).resize(((box[2]-box[0])*SCALE,(box[3]-box[1])*SCALE),Image.Resampling.LANCZOS)
        out.paste(patch,(box[0]*SCALE,box[1]*SCALE))
    # Logo is taken from this panel to preserve its distinct original placement.
    logo=chrome_cutout(front).resize((666*SCALE,108*SCALE),Image.Resampling.LANCZOS)
    out.paste(logo,(387*SCALE,98*SCALE),logo)
    return out


def clean_booklet(source, contours, back=False):
    # Work in the original portrait texture orientation. Restore the exact
    # observed grid and isolated type in the dark half of the manual cover.
    cleaned=denoise(source)
    if not back:
        a=np.asarray(source).astype(float)
        paper=(a[:,:,0]>175)&(a[:,:,1]>145)&(a[:,:,2]>120)&(a[:,:,0]-a[:,:,1]>9)
        candidate=np.uint8(~paper);candidate[:900]=0;candidate[1450:]=0
        _,labels,stats,_=cv2.connectedComponentsWithStats(candidate,8)
        main=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);mask=np.uint8(labels==main)
        cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        mask[:]=0;cv2.drawContours(mask,cs,-1,1,-1)
        mask=cv2.dilate(mask,np.ones((3,3),np.uint8))
        # The matte paper and pale pink pattern are flat print, not material
        # grain. Their original contours are retained independently of Sonic.
        coverage=np.clip((a[:,:,0]-a[:,:,1]-12)/36,0,1)
        coverage=cv2.GaussianBlur(coverage,(0,0),.65)
        cream=np.array((253,244,217));pink=np.array((240,186,174))
        flat=cream*(1-coverage[:,:,None])+pink*coverage[:,:,None]
        clean=np.asarray(cleaned).copy();allowed=mask==0;allowed[:895]=False
        clean[allowed]=np.uint8(flat[allowed]);cleaned=Image.fromarray(clean)
    out=cleaned.resize((source.width*SCALE,source.height*SCALE),Image.Resampling.LANCZOS)
    panel=grid(source.size,50,80,124)
    cutoff=source.height if back else 884
    out.paste(panel.crop((0,0,panel.width,cutoff*SCALE)),(0,0))
    if back:
        paste_ink(out,source,(700,35,1090,870),WHITE,contours=contours,key='manual-back-copy')
    else:
        paste_ink(out,source,(300,110,490,830),BLUE,'blue',contours,'manual-title')
        for box,key in [((505,95,565,840),'manual-subtitle'),((18,302,145,840),'manual-heading')]:
            paste_ink(out,source,box,WHITE,contours=contours,key=key)
        logo=sega_logo((375*SCALE,125*SCALE),(0,130,169)).rotate(90,expand=True)
        out.paste(logo,(957*SCALE,64*SCALE),logo)
    return out


def main():
    global SEGA_REFERENCE
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=Path('dist/box-refinement-20261016/artwork/mega-drive-sonic-the-hedgehog-box'))
    p.add_argument('--output',type=Path,default=Path('dist/box-polish-20261016/artwork/mega-drive-sonic-the-hedgehog-box'))
    p.add_argument('--sega-logo',type=Path,default=SEGA_REFERENCE)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    SEGA_REFERENCE=args.sega_logo
    images={slot:Image.open(args.input/(slot+'.png')).convert('RGB') for slot in json.loads((args.input/'mapping.json').read_text())}
    contours={};results={'Front':clean_front(images['Front'],contours),
        'Spine':clean_spine(images['Spine'],images['Front'],contours),
        'Back':clean_back(images['Back'],images['Front'],contours),
        'BookletFront':clean_booklet(images['BookletFront'],contours),
        'BookletBack':clean_booklet(images['BookletBack'],contours,True)}
    mapping={};faces={}
    for slot,im in results.items():
        path=args.output/(slot+'.png');im.save(path,optimize=True);mapping[slot]=str(path.resolve())
        faces[slot]={'inputFile':slot+'.png','inputSha256':digest(args.input/(slot+'.png')),
                     'outputFile':slot+'.png','outputPixels':im.size,'outputSha256':digest(path)}
    (args.output/'mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
    (args.output/'traced-contours.json').write_text(json.dumps(contours,separators=(',',':'))+'\n')
    provenance={'assetId':'mega-drive-sonic-the-hedgehog-box','sourceCatalog':'docs/game-box-artwork-sources.json',
      'workflow':'Original glyph contour reconstruction, clean measured grid, bounded paper/color restoration and original illustration denoise. Chrome plate silhouette and reflection bands are explicitly reconstructed; clean archived SEGA vector supplies the wordmark.',
      'previousProvenanceSha256':digest(args.input/'provenance.json'),'faces':faces,
      'additionalReferences':[{'file':args.sega_logo.name,'sha256':digest(args.sega_logo),
        'sourcePage':'https://commons.wikimedia.org/wiki/File:SEGA_logo_(no_R_mark).svg',
        'usage':'Clean SEGA wordmark from the archived vector logo; white keyline and period print colors restored.'}],
      'frontSpotRepairsNativePixels':[[1189,373,5],[876,978,5],[942,996,5]],
      'limitations':['Contours and flat colors are restored approximations of the original print, not recovered factory vectors.',
                     'Original screenshots and shaded character art retain source-resolution limits. Colors are visually estimated.']}
    (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({'asset':provenance['assetId'],'faces':list(results),'output':str(args.output)}))


if __name__=='__main__':
    main()
