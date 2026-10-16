#!/usr/bin/env python3
"""Clean the original SCUS-94900 print set without changing its layout.

Keep the original US K-A artwork, screenshots and text. Remove scanner grain
in color/luminance separately; reconstruct only reviewed single-ink brand
panels, spine text and trim. This never modifies jewel-case geometry/materials.

Requires Pillow, NumPy, OpenCV and scikit-image. --wordmark accepts a prepared
6000px transparent PNG rendered from --wordmark-vector (for example by Sharp).
--font allows the documented licensed font to be supplied on other systems.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from refine_case_box_artwork import make_review, sha, set_type
from refine_nes_box_print import trace

ASSET='playstation-1-crash-bandicoot-box'
INK=(6,7,9)
WHITE=(245,245,240)
WORDMARK_ID='playstation-1994-wordmark-vector'
WORDMARK_PAGE='https://commons.wikimedia.org/wiki/File:PlayStation_wordmark_(1994-2009).svg'
WORDMARK_URL='https://upload.wikimedia.org/wikipedia/commons/2/28/PlayStation_wordmark_%281994-2009%29.svg'
FONT=Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf')


def smooth_print(image):
    a=np.array(image.convert('RGB'))
    # Non-local averaging targets repeated scan grain. It retains broad source
    # edges and gradients; no fabricated high-resolution image detail.
    b=cv2.fastNlMeansDenoisingColored(a,None,7,10,7,21)
    lab=cv2.cvtColor(b,cv2.COLOR_RGB2LAB)
    lab[:,:,1:]=cv2.GaussianBlur(lab[:,:,1:],(0,0),.65)
    b=cv2.cvtColor(lab,cv2.COLOR_LAB2RGB).astype(np.float32)
    b+=.25*(b-cv2.GaussianBlur(b,(0,0),1.3))
    return Image.fromarray(np.uint8(np.clip(b,0,255)))


def single_ink_panel(image,size,broad=False):
    a=np.array(image).astype(float)
    mask=(a.min(2)>118).astype(np.uint8)*255
    if broad:
        mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
        count,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
        for label in range(1,count):
            if stats[label,cv2.CC_STAT_AREA]<4:mask[labels==label]=0
    canvas=Image.new('RGB',size,INK)
    canvas.paste(WHITE,(0,0,*size),trace(mask,size,.12,.5,smooth=1.8 if broad else .45))
    return canvas


def wordmark_mask(wordmark):
    mask=wordmark.convert('RGBA').getchannel('A')
    mask=mask.crop((0,0,round(mask.width*.949),mask.height))
    return mask.crop(mask.getbbox())


def region_label(size=(272,38),font=FONT):
    label=Image.new('RGB',(272,38),WHITE)
    ImageDraw.Draw(label).rectangle((160,0,163,37),fill=INK)
    set_type(label,'NTSC',(16,6,148,32),font,INK)
    set_type(label,'U/C',(180,6,258,32),font,INK)
    return label.resize(size,Image.Resampling.LANCZOS)


def brand_panel(result,slot,wordmark,font=FONT):
    """Use the matching 1994 wordmark, not the differently shaped modern logo.

    The prepared 6000px RGBA input is rasterized from the documented original
    SVG (e.g. with Sharp). Its final registered mark is excluded: the actual
    game cover carries TM, which is restored at its original position.
    """
    mask=wordmark_mask(wordmark).rotate(90,expand=True)
    box=(28,236,202,1063) if slot=='Front' else (24,249,196,1077)
    clear=(15,212,205,1085) if slot=='Front' else (15,220,204,1094)
    result.paste(INK,tuple(v*2 for v in clear))
    box=tuple(v*2 for v in box)
    result.paste(WHITE,box,mask.resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS))
    # Exact wording and boxes, in a documented approximate bold sans-serif.
    x,y=(25,186) if slot=='Front' else (30,192)
    result.paste(region_label(font=font),(2*x,2*y))
    tm=Image.new('RGB',(38,20),INK);set_type(tm,'TM',(1,1,37,19),font,WHITE)
    result.paste(tm.rotate(90,expand=True),((142 if slot=='Front' else 137)*2,(215 if slot=='Front' else 229)*2))


def restore(slot,image,wordmark,font=FONT):
    size=(image.width*2,image.height*2)
    result=smooth_print(image)
    a=np.array(result).astype(float)
    if slot in ('Front','BookletBack'):
        # Black front branding and footer fields are reviewed separately from
        # the torn-paper graphic, Crash render and jungle illustration.
        allowed=np.zeros(a.shape[:2],np.float32)
        allowed[:,:202 if slot=='Front' else 208]=1
        allowed[1235 if slot=='Front' else 1302:]=1
        # Continuous curve suppresses grain in dark ink without abruptly
        # clipping a white glyph or colored publisher logo.
        value=a.max(2)
        amount=np.maximum(np.clip((78-value)/52,0,1)*allowed,np.clip((50-value)/33,0,1))
        a=a*(1-amount[:,:,None])+np.array(INK)*amount[:,:,None]
        a[:3]=INK;a[-3:]=INK;a[:,:15]=INK;a[:,-3:]=INK
        result=Image.fromarray(np.uint8(np.clip(a,0,255))).resize(size,Image.Resampling.LANCZOS)
        brand_panel(result,slot,wordmark,font)
    elif slot=='WrapBack':
        # Fine rear legal type cannot survive aggressive text masks. Restore
        # its original coverage with a smaller noise estimate than the art.
        fine=np.array(image)
        cleaned=cv2.fastNlMeansDenoisingColored(fine,None,3,5,7,15)
        a[1160:,80:1688]=cleaned[1160:,80:1688]
        result=Image.fromarray(np.uint8(a)).resize(size,Image.Resampling.LANCZOS)
        for box in ((0,0,76,image.height),(1692,0,image.width,image.height)):
            patch=single_ink_panel(image.crop(box),(2*(box[2]-box[0]),2*image.height))
            result.paste(patch,(box[0]*2,0))
        # The narrow spine carries the same classic wordmark and region code.
        result.paste(INK,(20,90,110,430))
        mask=wordmark_mask(wordmark).rotate(-90,expand=True).resize((66,308),Image.Resampling.LANCZOS)
        result.paste(WHITE,(30,106,96,414),mask)
        result.paste(INK,(3434,92,3484,398))
        result.paste(region_label((298,42),font).rotate(-90,expand=True),(3438,96))
    else:
        # The molded-looking inner-left artwork is part of the original print
        # and remains. Only the unprinted outside trim loses crease glare.
        a[:,:62]=INK
        a[:,1690:]=INK
        result=Image.fromarray(np.uint8(a)).resize(size,Image.Resampling.LANCZOS)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path('dist/box-refinement-20261016/artwork')/ASSET)
    parser.add_argument('--output',type=Path,default=Path('dist/box-polish-20261016/artwork')/ASSET)
    parser.add_argument('--wordmark',type=Path,default=Path('dist/box-polish-20261016/references/ps1/PlayStation_wordmark_1994.png'),help='6000px RGBA render of the documented matching 1994 SVG; Sharp or another SVG renderer may prepare it.')
    parser.add_argument('--wordmark-vector',type=Path,default=Path('dist/box-polish-20261016/references/ps1/PlayStation_wordmark_1994.svg'))
    parser.add_argument('--font',type=Path,default=FONT)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    wordmark=Image.open(args.wordmark).convert('RGBA')
    mapping=json.loads((args.input/'mapping.json').read_text())
    before={slot:Image.open(args.input/(slot+'.png')).convert('RGB') for slot in mapping}
    after={};records={};outmap={}
    for slot,image in before.items():
        result=restore(slot,image,wordmark,args.font);path=args.output/(slot+'.png');result.save(path,optimize=True)
        after[slot]=result;outmap[slot]=str(path.resolve())
        method='Original print-color scan grain reduced with non-local luminance/chroma averaging; antialiased output enlargement retains source illustrations and layout.'
        if slot in ('Front','BookletBack'):method+=' Reviewed dark brand/footer fields normalized; matching 1994 PlayStation wordmark restored from Sony-manual-derived vector. Exact NTSC U/C and TM copy typeset in an explicitly approximate bold sans-serif.'
        elif slot=='WrapBack':method+=' Original Crash spine title contours restored on clean black fields; classic vector PlayStation spine mark and exact NTSC U/C copy restored; fine rear legal type receives a gentler noise pass.'
        else:method+=' Outer unprinted trim restored; printed inner spine/rib design and original screenshots retained.'
        records[slot]=dict(inputFile=slot+'.png',inputSha256=sha(args.input/(slot+'.png')),outputFile=slot+'.png',outputSha256=sha(path),outputPixels=list(result.size),method=method)
        if slot in ('Front','BookletBack','WrapBack'):records[slot]['additionalPreparedInputs']=[dict(sourceId=WORDMARK_ID,file=args.wordmark.name,sha256=sha(args.wordmark),vectorFile=args.wordmark_vector.name,vectorSha256=sha(args.wordmark_vector))]
    (args.output/'mapping.json').write_text(json.dumps(outmap,indent=2)+'\n')
    (args.output/'provenance.json').write_text(json.dumps(dict(assetId=ASSET,workflow='Deterministic original-print noise reduction, matching classic vector branding, and bounded single-ink contour restoration.',previousProvenanceSha256=sha(args.input/'provenance.json'),sourceCatalog='docs/game-box-artwork-sources.json',usedSourceIds=['crash-F-ALL','crash-B-ALL','crash-I-1','crash-I-2',WORDMARK_ID],vectorReference=dict(sourceId=WORDMARK_ID,page=WORDMARK_PAGE,url=WORDMARK_URL,sha256=sha(args.wordmark_vector),preparedRasterSha256=sha(args.wordmark),credit='Sony Computer Entertainment; vector archived by Techtri from Sony SCPH-90002/90003 instruction manual.',rights='Commons marks the text logo PD-textlogo; trademark restrictions remain.'),restorationFont=dict(name=args.font.stem,sha256=sha(args.font),scope='NTSC U/C and TM only'),limitations=['The original four-part SCUS-94900 K-A print set and all game illustrations are retained. The matching classic 1994 wordmark replaces only worn branding.','NTSC U/C and TM text is reproduced exactly, using a documented approximate Arial Bold face rather than a verified original production font.','Enlargement supplies antialiased lettering but does not recover new photographic detail. Original game screenshot detail remains source-limited.','Sony official timeline artwork was researched but rejected as a 400×400 jewel-case product image with lower effective cover detail. Modern PlayStation wordmarks were rejected because their letter shapes differ.'],faces=records),indent=2)+'\n')
    make_review(before,after,args.output)
    sheet=Image.new('RGB',(2400,1050),(22,25,30))
    for i,(label,group) in enumerate((('Before',before),('Restored print',after))):
        im=group['Front'];factor=im.width/before['Front'].width
        crop=im.crop(tuple(round(v*factor) for v in (0,180,800,850)))
        crop=ImageOps.contain(crop,(1160,970));sheet.paste(crop,(i*1200+20,60))
        ImageDraw.Draw(sheet).text((i*1200+20,20),label,fill='white')
    sheet.save(args.output/'front-detail-before-after.jpg',quality=96)
    print(f'{ASSET}: {len(records)} print faces restored')


if __name__=='__main__':main()
