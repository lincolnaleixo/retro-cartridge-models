#!/usr/bin/env python3
"""Prepare pristine SNES/N64 print surfaces with explicit source-based reconstruction.

The output is a digital reconstruction, not a claim of calibrated factory ink.
Published assets remain immutable. Geometry and UV orientation are not changed.

Workspace inputs deliberately use the dated dist/game-boxes-20261016,
dist/snes-box-refinement-20261016 and dist/box-refinement-20261016 reference
collections. New references and output live under dist/box-polish-20261016.
Dependencies: Pillow, NumPy, OpenCV, SciPy and the Arial TTF family. Fonts default
to macOS /System/Library/Fonts/Supplemental; use --font-dir for another location.
"""
from pathlib import Path
import argparse
import hashlib
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import refine_snes_box_artwork as snes

ROOT=Path(__file__).resolve().parents[1]
PREVIOUS=ROOT/'dist/box-refinement-20261016/artwork'
OUTPUT=ROOT/'dist/box-polish-20261016/artwork'
REFERENCES=ROOT/'dist/box-polish-20261016/references'
FACES=('Front','Back','Top','Bottom','SpineLeft','SpineRight')
INK=(8,10,13)
FONT_DIR=Path('/System/Library/Fonts/Supplemental')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size,bold=False,italic=False,narrow=False):
    name='Arial'+(' Narrow' if narrow else '')+(' Bold' if bold else '')+(' Italic' if italic else '')+'.ttf'
    path=FONT_DIR/name
    if not path.exists():path=FONT_DIR/'Arial.ttf'
    return ImageFont.truetype(str(path),size)


def clean_ink(image, strength=10, bilateral=35):
    """Suppress halftone/paper grain while retaining strong illustrated contours."""
    rgb=np.array(image.convert('RGB'))
    rgb=cv2.fastNlMeansDenoisingColored(rgb,None,strength,strength+4,7,21)
    for amount in (bilateral,bilateral-5):rgb=cv2.bilateralFilter(rgb,15,amount,8)
    return Image.fromarray(rgb)


def line(canvas,text,box,color=(235,235,228),bold=False,italic=False,narrow=False):
    """Render exact transcribed wording into a source-measured line rectangle."""
    x,y,w,h=box;f=font(100,bold=bold,italic=italic,narrow=narrow);b=f.getbbox(text)
    temp=Image.new('RGBA',(b[2]-b[0]+6,b[3]-b[1]+6))
    ImageDraw.Draw(temp).text((3-b[0],3-b[1]),text,font=f,fill=(*color,255))
    temp=temp.resize((round(w),round(h)),Image.Resampling.LANCZOS)
    canvas.alpha_composite(temp,(round(x),round(y)))


def scaled_line(canvas,text,box,scale=1,**kwargs):
    line(canvas,text,[v*scale for v in box],**kwargs)


def paste(canvas,image,box):
    x,y,w,h=[round(v) for v in box];im=image.convert('RGBA').resize((w,h),Image.Resampling.LANCZOS)
    canvas.alpha_composite(im,(x,y))


def transparent_capsule():
    """Use the period racetrack vector mark on a clean warm-white capsule."""
    clean_path=REFERENCES/'Nintendo-red-logo-3840.png'
    if clean_path.exists():
        logo=Image.open(clean_path).convert('RGBA');out=Image.new('RGBA',logo.size)
        ImageDraw.Draw(out).rounded_rectangle((1,1,logo.width-2,logo.height-2),radius=logo.height/2,fill=(250,248,236,255))
        a=np.array(logo);a[(a[:,:,:3].min(2)>240),:3]=(250,248,236)
        out.alpha_composite(Image.fromarray(a));return out
    # Archival fallback keeps the original glyph shapes if the clean reference is absent.
    original=Image.open(snes.OLD_REFS/'smw-launchbox-19789364.png').convert('RGBA').crop((2070,145,2440,252))
    a=np.array(original);a[:,:,3]=np.where(a[:,:,:3].max(2)<45,0,255)
    red=(a[:,:,0].astype(float)-a[:,:,1]>38)&(a[:,:,0]>110)&(a[:,:,3]>0)
    white=(a[:,:,3]>0)&~red
    scale=5;out=Image.new('RGBA',(original.width*scale,original.height*scale));d=ImageDraw.Draw(out)
    for mask,color in [(a[:,:,3]>0,(250,248,236,255)),(red,(218,0,36,255))]:
        contours,hierarchy=cv2.findContours(mask.astype(np.uint8),cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:continue
        for i in sorted(range(len(contours)),key=lambda i:cv2.contourArea(contours[i]),reverse=True):
            c=contours[i]
            if cv2.contourArea(c)<2:continue
            points=cv2.approxPolyDP(c,.32,True).reshape(-1,2)*scale
            if len(points)>2:d.polygon([tuple(v) for v in points],fill=color if hierarchy[0,i,3]<0 else (250,248,236,255))
    return out


def barcode(digits,width,height):
    odd=['0001101','0011001','0010011','0111101','0100011','0110001','0101111','0111011','0110111','0001011']
    assert len(digits)==12 and (sum(int(x) for x in digits[:11:2])*3+sum(int(x) for x in digits[1:11:2])+int(digits[11]))%10==0
    bits='101'+''.join(odd[int(v)] for v in digits[:6])+'01010'+''.join(''.join('1' if b=='0' else '0' for b in odd[int(v)]) for v in digits[6:])+'101'
    out=Image.new('RGBA',(width,height),'#fffef4');d=ImageDraw.Draw(out);margin=width*.115;module=(width-2*margin)/95
    for i,b in enumerate(bits):
        if b=='1':d.rectangle((round(margin+i*module),round(height*.05),round(margin+(i+1)*module)-1,round(height*(.86 if i<3 or 45<=i<50 or i>=92 else .81))),fill='#08090a')
    line(out,digits[0],(width*.025,height*.85,width*.055,height*.115),color=(8,9,10),narrow=True)
    line(out,digits[1:6],(width*.18,height*.85,width*.295,height*.115),color=(8,9,10),narrow=True)
    line(out,digits[6:11],(width*.52,height*.85,width*.295,height*.115),color=(8,9,10),narrow=True)
    line(out,digits[11],(width*.925,height*.85,width*.05,height*.115),color=(8,9,10),narrow=True)
    return out


def clean_seal(source,box,size):
    crop=source.crop(box).convert('RGB');a=np.array(clean_ink(crop,7,24));gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
    # Reuse the recognizable seal geometry; preserve fine original lettering.
    return Image.fromarray(a).resize(size,Image.Resampling.LANCZOS).convert('RGBA')


def print_seal(size,background=INK):
    """Reconstruct the original oval quality-seal geometry and exact wording."""
    import math
    out=Image.new('RGBA',(1200,900),(*background,255));d=ImageDraw.Draw(out)
    gold=(163,151,83);cream=(250,247,218)
    pts=[]
    for i in range(64):
        t=i*math.pi/32;r=1 if i%2==0 else .91
        pts.append((570+555*r*math.cos(t),435+422*r*math.sin(t)))
    d.polygon(pts,fill=gold);d.ellipse((90,95,1050,775),fill=cream)
    d.ellipse((112,115,1028,755),outline=gold,width=10)
    logo=transparent_capsule();a=np.array(logo);a[:,:,:3]=gold;a[:,:,3]=np.where((np.array(logo)[:,:,0]>150)&(np.array(logo)[:,:,1]<100),255,0)
    paste(out,Image.fromarray(a),(190,340,760,187))
    line(out,'Official',(430,228,280,78),color=gold,bold=True)
    line(out,'Seal of Quality',(271,585,595,79),color=gold,bold=True)
    line(out,'®',(1090,782,55,60),color=gold)
    return out.resize(size,Image.Resampling.LANCZOS)


def recycling_symbol(size,background,foreground,field):
    """Trace the source arrows onto an antialiased circular ink field."""
    raw=Image.open(snes.REFS/'cibby-back.jpg').convert('RGB').crop((472,686,529,742))
    a=np.array(raw);mask=np.uint8((a.max(2)-a.min(2)<65)&(a.max(2)>130))*255
    out=Image.new('RGBA',(1000,1000),(*background,255));d=ImageDraw.Draw(out)
    d.ellipse((4,4,996,996),fill=(*field,255))
    contours,hierarchy=cv2.findContours(mask,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    for i in sorted(range(len(contours)),key=lambda i:cv2.contourArea(contours[i]),reverse=True):
        c=contours[i]
        if cv2.contourArea(c)<8:continue
        pts=cv2.approxPolyDP(c,.4,True).reshape(-1,2)*np.array([1000/57,1000/56])
        if len(pts)>2:d.polygon([tuple(v) for v in pts],fill=(*foreground,255) if hierarchy[0,i,3]<0 else (*field,255))
    return out.resize(size,Image.Resampling.LANCZOS)


def snes_rear():
    """Rebuild all rear typography and flat graphics around original screenshots."""
    raw=Image.open(snes.REFS/'cibby-back.jpg').convert('RGB');S=4096/1143
    out=Image.new('RGBA',(4096,2874),(*INK,255));d=ImageDraw.Draw(out)
    # Original gray stripe field and diagonal motif behind the four screenshots.
    for y in range(18,565,23):d.rectangle((685*S,y*S,4096,(y+9)*S),fill=(48,50,52,255))
    motif=snes.striped_symbol((round(442*S),round(370*S)));paste(out,motif,(687*S,197*S,442*S,370*S))
    logo=snes.title_art();paste(out,logo,(38*S,32*S,557*S,157*S))
    scaled_line(out,'SNS P MW',(1010,26,113,16),S,bold=True)
    scaled_line(out,'Tackle a whole new world',(160,205,294,22),S,color=(237,190,56),bold=True)
    scaled_line(out,'with Mario & Yoshi!',(192,230,231,22),S,color=(237,190,56),bold=True)
    lines=[
      ("Mario’s off on his biggest adventure ever, and this time he’s",261,543),
      ('brought along a friend. Yoshi the dinosaur teams up with Mario',284,581),
      ('to battle Bowser, who has kidnapped Princess Toadstool once',307,572),
      ('again. Guide Mario and Yoshi through nine peril-filled worlds to',330,584),
      ('the final showdown in Bowser’s castle.',353,365),
      ('Use Mario’s new powers and Yoshi’s voracious monster-',383,531),
      ('gobbling appetite as you explore 96 levels filled with dangerous',406,585),
      ('new monsters and traps. Climb mountains and cross rivers, and',429,583),
      ('descend into subterranean depths. Destroy the seven Koopa',452,563),
      ('castles and find keys to gain entrance to hidden levels. Discover',475,588),
      ('more warps and thrilling bonus worlds than ever before!',498,526)]
    for text,y,w in lines:scaled_line(out,text,(15,y,w,20),S)
    scaled_line(out,'Mario’s back, and this time he’s better than ever!',(15,529,465,20),S,bold=True)
    # Original printed screenshots: mild screen-noise cleanup, no substituted scenes.
    for box in [(639,70,870,250),(891,69,1123,250),(640,272,870,449),(892,271,1123,449)]:
        x0,y0,x1,y1=box;pic=clean_ink(raw.crop(box),4,14)
        paste(out,pic,(x0*S,y0*S,(x1-x0)*S,(y1-y0)*S))
    scaled_line(out,'FOR USE ON YOUR SUPER NINTENDO',(15,598,208,10),S)
    scaled_line(out,'ENTERTAINMENT SYSTEM.',(15,611,145,10),S)
    # Barcode retains the original bar pattern, with clean binary ink.
    bar=barcode('045496830014',round(221*S),round(150*S))
    paste(out,bar,(16*S,634*S,221*S,150*S))
    d.rectangle((251*S,634*S,447*S,702*S),fill=(230,55,29,255))
    for text,y,w in [('VALUABLE LIMITED WARRANTY',646,179),('PURCHASE RECEIPT REQUIRED',659,180),('CALL 1-800-255-3700 FOR',672,154),('SERVICE INFORMATION',685,144)]:
        scaled_line(out,text,(259,y,w,10),S,bold=True,italic=True)
    for text,y,w in [('FOR SALE AND USE IN',719,169),('THE USA, CANADA',744,146),('AND MEXICO ONLY.',769,156)]:scaled_line(out,text,(251,y,w,18),S,bold=True,italic=True)
    # Recycle mark: keep original shape, clean the red field and white arrows.
    paste(out,recycling_symbol((400,400),INK,(248,248,238),(238,57,30)),(472*S,686*S,57*S,56*S))
    for text,y,w in [('THIS PACKAGE IS MADE',752,130),('FROM RECYCLED MATERIALS',763,157),('AND IS RECYCLABLE.',774,120)]:scaled_line(out,text,(475,y,w,9),S)
    seal=print_seal((round(116*S),round(88*S)));paste(out,seal,(684*S,593*S,116*S,88*S))
    sealtext=['THIS OFFICIAL SEAL IS YOUR','ASSURANCE THAT NINTENDO HAS','APPROVED THE QUALITY OF THIS','PRODUCT. ALWAYS LOOK FOR THIS','SEAL WHEN BUYING GAMES AND','ACCESSORIES TO ENSURE COMPLETE','COMPATIBILITY WITH YOUR SUPER','NINTENDO ENTERTAINMENT SYSTEM.']
    widths=[169,188,187,191,178,211,196,211]
    for i,(text,w) in enumerate(zip(sealtext,widths)):scaled_line(out,text,(688,694+i*11,w,9),S)
    paste(out,transparent_capsule(),(918*S,684*S,170*S,42*S))
    scaled_line(out,'Game Pak (SNS-006)',(945,733,112,10),S)
    for text,y,w in [('TM AND ® ARE TRADEMARKS OF',751,188),('NINTENDO OF AMERICA INC.',763,166),('© 1992 NINTENDO OF AMERICA INC.',775,206)]:scaled_line(out,text,(918,y,w,9),S)
    return out.convert('RGB')


def snes_faces():
    raw=Image.open(snes.OLD_REFS/'smw-launchbox-19789364.png').convert('RGB')
    front=clean_ink(raw,10,35)
    # A tiny green TM is thinner than the scan's halftone period. Restore its
    # exact wording explicitly after cleaning instead of leaving a green smear.
    a=np.array(front);mask=np.zeros(a.shape[:2],np.uint8);mask[228:271,1688:1755]=255
    front=Image.fromarray(cv2.inpaint(a,mask,9,cv2.INPAINT_NS)).convert('RGBA')
    line(front,'TM',(1695,234,49,30),color=(99,157,60))
    paste(front,print_seal((245,180),(0,0,0)),(29,1500,245,180))
    paste(front,transparent_capsule(),(2070,145,370,107))
    # The untouched digital outline and original gradient shapes survive grain removal.
    front=front.convert('RGB').resize((4096,2874),Image.Resampling.LANCZOS)
    results={'Front':front,'Back':snes_rear()}
    old_cutout=snes.official_cutout
    def polished_cutout(*args,**kwargs):
        cut=old_cutout(*args,**kwargs);alpha=cut.getchannel('A')
        strength,bilateral=(16,56) if 'Dry_Bones' in args[0] else (10,40)
        clean=clean_ink(cut,strength,bilateral).convert('RGBA');clean.putalpha(alpha);return clean
    snes.official_cutout=polished_cutout
    original_oval=snes.oval_art;snes.oval_art=transparent_capsule
    original_font=snes.font;snes.font=lambda size,narrow=False:font(size,narrow=narrow)
    try:
        for slot,image in snes.make_edges().items():results[slot]=image.resize((image.width*2,image.height*2),Image.Resampling.LANCZOS)
    finally:snes.official_cutout=old_cutout;snes.oval_art=original_oval;snes.font=original_font
    return results


def n64_rear():
    aid='nintendo-64-super-mario-64-box';old=Image.open(PREVIOUS/aid/'Back.png').convert('RGB')
    a=np.array(old);gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
    mask=np.zeros(gray.shape,np.uint8)
    # Remove thin printed glyphs before descreening, preserving the broad Mario
    # illustration beneath them. The same exact wording is then re-typeset.
    for box,bright in [((620,475,1605,920),False),((620,990,1605,1840),True),((665,2000,1280,2085),True)]:
        x0,y0,x1,y1=box;rgb=a[y0:y1,x0:x1]
        g=gray[y0:y1,x0:x1]
        hat=cv2.morphologyEx(g,cv2.MORPH_TOPHAT if bright else cv2.MORPH_BLACKHAT,np.ones((17,17),np.uint8))
        m=np.uint8(hat>16)*255;m=cv2.dilate(m,np.ones((5,5),np.uint8))
        mask[y0:y1,x0:x1]=m
    clean=cv2.inpaint(a,mask,9,cv2.INPAINT_TELEA)
    # Remove the old product caption before the identical clean caption is set.
    for y in range(1618,1674):clean[y,2440:3025]=np.median(a[y,2900:3030],axis=0)
    out=clean_ink(Image.fromarray(clean),11,35).convert('RGBA')
    # Keep the five original gameplay scenes at their original boundaries and
    # avoid treating polygon edges as typography or reconstructing game pixels.
    for box in [(1623,118,2355,676),(2259,367,2992,922),(1623,779,2354,1339),(2259,1022,2991,1588),(1623,1431,2356,1985)]:
        x0,y0,x1,y1=box
        pic=np.array(clean_ink(old.crop(box),7,22));pic[pic.max(2)<30]=(5,6,9)
        border=np.ones(pic.shape[:2],bool);border[16:-16,16:-16]=False
        pic[border&(pic.max(2)<100)]=(5,6,9)
        paste(out,Image.fromarray(pic),(x0,y0,x1-x0,y1-y0))
    d=ImageDraw.Draw(out);d.rectangle((0,0,594,2155),fill=(244,18,39,255))
    # The source title is replaced with the matching clean original mark.
    logo=Image.open(ROOT/'dist/box-refinement-20261016/references/n64/SuperMario64Logo4.png').convert('RGBA')
    ImageDraw.Draw(logo).rectangle((1395,440,1500,555),fill=(0,0,0,0))
    # The original title is slightly wider than the clean mark. Remove its
    # full bounded footprint before compositing to prevent doubled edges.
    b=np.array(out.convert('RGB'));m=np.zeros(b.shape[:2],np.uint8);m[18:420,610:1590]=255
    small=cv2.resize(b,(768,539));sm=cv2.resize(m,(768,539),interpolation=cv2.INTER_NEAREST)
    fill=cv2.inpaint(small,sm,9,cv2.INPAINT_NS);fill=cv2.GaussianBlur(fill,(0,0),18)
    fill=cv2.resize(fill,out.size);alpha=cv2.GaussianBlur(m.astype(np.float32)/255,(0,0),10)[:,:,None]
    b=np.uint8(b*(1-alpha)+fill*alpha);out=Image.fromarray(b).convert('RGBA')
    paste(out,logo,(635,45,895,345));line(out,'TM',(1492,343,35,20),color=(18,15,12))
    black_lines=[
      ('Mario is super in a whole new way! Combining',874),
      ('the finest 3-D graphics ever developed for',802),
      ('a video game and an explosive sound track.',819),
      ('Super Mario 64™ becomes a new standard for',849),
      ('video games. It’s packed with bruising battles,',874),
      ('daunting obstacle courses and underwater',815),
      ('adventures. Retrieve the Power Stars from their',871),
      ('hidden locations and confront your arch nemesis',922),
      ('-- Bowser, King of the Koopas!',594)]
    for i,(text,w) in enumerate(black_lines):line(out,text,(656,484+i*46,w,36),color=(25,20,15))
    paragraphs=[(1005,[('Run freely in a grassy meadow, tip-toe through a',880),('gloomy dungeon, climb to the top of a mountain',873),('or take a swim in the moat!',487)]),
      (1152,[('Leap head first into a watery painting and soon',858),("you’ll be searching for the surface in an underwater",915),('realm!',114)]),
      (1299,[('On-the-fly, 3-D rendered game play delivers the',852),('action of ruthless enemy attacks from every angle!',912)]),
      (1403,[('Find the Caps that give Mario super powers, ponder',923),('the mysteries of the pyramid, you can even race',864),('Koopas for fabulous prizes!',483)]),
      (1551,[('With the Nintendo 64 Controller and its analog',829),('Control Stick, Mario can crawl, kick down obstacles,',924),('swim, do reverse flips, and even stick the landing',883),('on his backwards somersault!',538)]),
      (1743,[('Saved game information is stored for up to four',867),('players in memory.',354)])]
    for y,lines in paragraphs:
        line(out,'•',(626,y-2,18,30),color=(250,246,222))
        for i,(text,w) in enumerate(lines):line(out,text,(656,y+i*44,w,35),color=(250,246,222))
    # Flat red legal panel; exact text from the selected US K-A carton.
    seal=print_seal((297,217),(244,18,39));paste(out,seal,(138,55,297,217))
    legal=[('MADE IN JAPAN',334,292,36),('MODEL # NUS-006 (USA)',398,390,28),('FOR SALE, RENTAL AND USE',451,453,30),('ONLY IN USA, CANADA, MEXICO',495,492,30),('AND LATIN AMERICA',539,328,30)]
    for text,y,w,h in legal:line(out,text,((594-w)/2,y,w,h))
    d=ImageDraw.Draw(out);d.rectangle((67,652,514,698),fill=(254,251,231,255));line(out,'IMPORTANT!',(175,658,229,35),color=(189,34,28))
    for text,y,w in [('BEFORE USING YOUR SYSTEM,',720,398),('CAREFULLY READ THE CONSUMER',764,465),('INFORMATION AND',808,277),('PRECAUTIONS BOOKLET.',852,340)]:line(out,text,((594-w)/2,y,w,27),narrow=True)
    paste(out,recycling_symbol((400,400),(244,18,39),(7,8,10),(250,247,231)),(232,924,116,117))
    for text,y,w,h in [('78%',1067,50,27),('TOTAL RECOVERED FIBER',1108,296,32),('73% POST CONSUMER CONTENT',1152,385,30),('PLEASE RECYCLE WHERE FACILITIES EXIST',1211,489,25),('CHECK TO SEE IF RECYCLING FACILITIES EXIST IN YOUR AREA',1252,548,19)]:line(out,text,((594-w)/2,y,w,h),narrow=True)
    d=ImageDraw.Draw(out);d.rectangle((75,1338,498,1577),fill=(194,112,62,255))
    for i,(text,w) in enumerate([('VALUABLE LIMITED',284),('WARRANTY. PURCHASE',350),('RECEIPT REQUIRED. CALL',384),('1-800-255-3700 FOR',300),('SERVICE INFORMATION.',375)]):line(out,text,((594-w)/2,1367+i*40,w,30),narrow=True)
    for text,y,w in [('™ AND ® ARE TRADEMARKS OF',1622,443),('NINTENDO OF AMERICA INC.',1656,390),('© 1996 NINTENDO OF AMERICA INC.',1700,470)]:line(out,text,((594-w)/2,y,w,23),narrow=True)
    paste(out,transparent_capsule(),(671,1906,321,78))
    line(out,'NINTENDO OF AMERICA, INC.',(671,2007,384,23),narrow=True)
    line(out,'PO BOX 957, REDMOND, WA 98073-0957 U.S.A.',(671,2048,592,23),narrow=True)
    # Barcode and caption become clean digital print instead of wavy scan lines.
    paste(out,barcode('045496870010',585,400),(2440,1674,585,400));line(out,'NUS P NSME',(2635,1634,180,24),color=(30,27,19),narrow=True)
    return out.convert('RGB').resize((4096,2874),Image.Resampling.LANCZOS)


def n64_cutout(filename):
    """Separate the original period render from its neutral archival paper."""
    source=Image.open(REFERENCES/'n64'/filename)
    if source.mode=='RGBA':return source
    a=np.array(source.convert('RGB'));h,w=a.shape[:2]
    hsv=cv2.cvtColor(a,cv2.COLOR_RGB2HSV)
    mask=np.full((h,w),cv2.GC_PR_BGD,np.uint8)
    mask[(hsv[:,:,1]>45)&(hsv[:,:,2]>35)]=cv2.GC_PR_FGD
    mask[(hsv[:,:,1]>110)&(hsv[:,:,2]>75)]=cv2.GC_FGD
    mask[:3]=mask[-3:]=cv2.GC_BGD;mask[:,:3]=mask[:,-3:]=cv2.GC_BGD
    cv2.setRNGSeed(0)
    cv2.grabCut(a,mask,None,np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),7,cv2.GC_INIT_WITH_MASK)
    alpha=np.uint8((mask==cv2.GC_FGD)|(mask==cv2.GC_PR_FGD))*255
    # Enclosed white eyes, gloves and bellies are printed character artwork,
    # never transparent paper. Keep those interiors even when their RGB color
    # resembles the archival background.
    from scipy.ndimage import binary_fill_holes
    alpha=np.uint8(binary_fill_holes(alpha>127))*255
    if filename=='SM64PenguinFront.png':
        # This reference has a uniform neutral-gray paper field. Flood only
        # border-connected gray, preserving the complete white chest shading.
        gray_paper=(a.max(2).astype(float)-a.min(2)<16)&(np.abs(a.mean(2)-216)<20)
        count,labels=cv2.connectedComponents(np.uint8(gray_paper),8)
        outside=set(np.unique(np.r_[labels[0],labels[-1],labels[:,0],labels[:,-1]]));outside.discard(0)
        alpha=np.uint8(~np.isin(labels,list(outside)))*255
        alpha=cv2.erode(alpha,np.ones((3,3),np.uint8))
    if filename=='Mario_Diving_Artwork_-_Super_Mario_64.png':
        # The white gloves touch the neutral photo background. Their outline is
        # traced explicitly from this source so color segmentation cannot erase
        # them. This contour edits the matte only, never the original artwork.
        points=[(283,188),(293,115),(339,54),(417,14),(481,17),(548,44),(598,81),(648,91),(683,89),(699,125),(694,164),(741,168),(780,188),(801,228),(813,260),(801,294),(758,339),(718,400),(688,427),(699,483),(697,552),(667,622),(626,654),(597,639),(571,598),(544,559),(510,548),(478,560),(460,542),(456,519),(482,468),(504,439),(463,444),(433,467),(385,473),(344,453),(322,432),(286,454),(279,481),(248,492),(218,482),(214,453),(196,455),(174,471),(158,481),(126,485),(117,471),(141,447),(123,450),(99,455),(78,456),(65,441),(62,424),(92,409),(124,388),(174,363),(208,351),(224,341),(240,327),(261,335),(284,348),(310,340),(333,338),(340,313),(350,276),(346,254),(291,247),(286,230)]
        alpha[:]=0;cv2.fillPoly(alpha,[np.array(points,np.int32)],255)
    alpha=cv2.GaussianBlur(alpha,(3,3),.5)
    rgb=np.array(clean_ink(Image.fromarray(a),4,18))
    return Image.fromarray(np.dstack((rgb,alpha)))


def n64_badge():
    front=Image.open(ROOT/'dist/box-refinement-20261016/references/n64/front-nintendo-classics.png').convert('RGB')
    a=np.array(front.crop((1295,36,1505,220)))
    # Delete only the pale folded "Only For" corner contamination; the saturated
    # six-face N and original printed console lettering remain untouched.
    hsv=cv2.cvtColor(a,cv2.COLOR_RGB2HSV);a[(hsv[:,:,1]<52)&(hsv[:,:,2]>160)]=(255,255,255)
    out=Image.new('RGB',(210,184),'white')
    for box in ((10,8,203,46),(40,47,170,176)):out.paste(Image.fromarray(a).crop(box),box[:2])
    return out


def n64_edge(slot):
    aid='nintendo-64-super-mario-64-box';old=Image.open(PREVIOUS/aid/(slot+'.png')).convert('RGB')
    angle={'SpineLeft':90,'SpineRight':-90}.get(slot,0);old=old.rotate(angle,expand=True)
    w,h=old.size;factor=2;W,H=w*factor,h*factor
    configs={
      'Top':('Mario_Diving_Artwork_-_Super_Mario_64.png',[[.72,0,793],[0,.72,-70]],(36,57,133),(142,165,222),(15,28,75)),
      'Bottom':('SM64_Artwork_Mario_(Jump).png',[[1.78772,-.59240,919.49],[.59240,1.78772,-122.60]],(19,101,95),(140,203,188),(7,45,45)),
      'SpineLeft':('SM64PenguinFront.png',[[-.2702,.4325,908.4],[-.4325,-.2702,326.2]],(221,156,31),(255,233,111),(139,86,26)),
      'SpineRight':('BowserLeaks.jpg',[[.05613,-1.05622,1050.62],[1.27244,-.00952,-677.12]],(160,4,17),(237,106,113),(91,2,15)),
    }
    filename,affine,base,light,dark=configs[slot]
    yy,xx=np.mgrid[0:H,0:W];v=.92+.08*(1-yy/H)
    rgb=np.uint8(np.array(base)[None,None,:]*v[:,:,None]);out=Image.fromarray(rgb).convert('RGBA')
    art=n64_cutout(filename);a=np.array(art);lum=cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY).astype(float)/255
    # Original carton uses one-color duotone illustrations, not full-color poses.
    tone=np.array(dark)[None,None,:]+(np.array(light)-np.array(dark))[None,None,:]*(lum**.84)[:,:,None]
    art=np.dstack((np.uint8(np.clip(tone,0,255)),a[:,:,3]))
    matrix=np.array(affine,float)*factor
    warped=cv2.warpAffine(art,matrix,(W,H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    out.alpha_composite(Image.fromarray(warped))
    logo=Image.open(ROOT/'dist/box-refinement-20261016/references/n64/SuperMario64Logo4.png').convert('RGBA')
    ImageDraw.Draw(logo).rectangle((1395,440,1500,555),fill=(0,0,0,0))
    if slot in ('Top','Bottom'):
        logo_box=(w*.018,h*.035,w*(.375-.018),h*(.955-.035));console_box=(w*.848,h*.10,w*(.981-.848),h*(.94-.10))
    elif slot=='SpineLeft':
        logo_box=(w*.023,h*.055,w*(.515-.023),h*(.89-.055));console_box=(w*.78,h*.13,w*(.966-.78),h*(.84-.13))
    else:logo_box=None;console_box=(w*.795,h*.14,w*(.978-.795),h*(.91-.14))
    if logo_box:
        paste(out,logo,[x*factor for x in logo_box]);x,y,lw,lh=logo_box
        line(out,'TM',((x+lw*.90)*factor,(y+lh*.82)*factor,lw*.03*factor,lh*.035*factor),color=(12,12,14))
    badge=n64_badge()
    if slot=='SpineRight':badge=badge.rotate(-90,expand=True)
    paste(out,badge,[x*factor for x in console_box])
    return out.convert('RGB').rotate(-angle,expand=True)


def n64_faces():
    front=Image.open(ROOT/'dist/box-refinement-20261016/references/n64/front-nintendo-classics.png').convert('RGB')
    return {'Front':front.resize((4096,2874),Image.Resampling.LANCZOS),'Back':n64_rear(),**{s:n64_edge(s) for s in FACES[2:]}}


def evidence(aid,results,records):
    dest=OUTPUT/aid;dest.mkdir(parents=True,exist_ok=True);mapping={};faces={}
    for slot,im in results.items():
        p=dest/(slot+'.png');im.save(p,optimize=True);mapping[slot]=str(p.relative_to(ROOT))
        faces[slot]={'previousSha256':sha(PREVIOUS/aid/(slot+'.png')),'outputSha256':sha(p),'outputPixels':list(im.size),'method':records.get(slot,records.get('default',''))}
    (dest/'mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
    old=json.loads((PREVIOUS/aid/'provenance.json').read_text())
    provenance={'assetId':aid,'publicationRights':'not-established','workflow':'Deterministic print reconstruction: selectively remove halftone grain, rebuild flat fields and exact transcribed text, preserve original illustration contours and gameplay scenes. No generative imagery.','previousProvenanceSha256':sha(PREVIOUS/aid/'provenance.json'),'previousSources':old.get('sources',[]),'limitations':['Digital reconstruction, not an untouched original scan.','Colors and replacement typefaces are visual approximations, not calibrated factory inks.','Original gameplay screenshots retain their source-resolution limit.','The quality seal and recycling symbol are documented geometric reconstructions of the original marks.'],'faces':faces}
    provenance['sources']=[json.loads((REFERENCES/'Nintendo-red-logo-source.json').read_text())]
    if aid.startswith('nintendo'):
        source_file=REFERENCES/'n64/source-records.json'
        used={'Mario_Diving_Artwork_-_Super_Mario_64.png','SM64_Artwork_Mario_(Jump).png','SM64PenguinFront.png','BowserLeaks.jpg'}
        provenance['sources']+=[r for r in json.loads(source_file.read_text()) if r['filename'] in used] if source_file.exists() else []
    for source in provenance['sources']:
        path=REFERENCES/source['filename']
        if not path.exists():path=REFERENCES/'n64'/source['filename']
        source['sha256']=sha(path)
        source['rights']='Third-party copyrighted reference; no separate redistribution license established.'
    (dest/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    # Real-detail crops, not resized hero views. Equal physical crop bounds on each side.
    crops={'Front':(.15,.05,.75,.53),'Back':(.01,.03,.55,.58),'Top':(.38,0,.80,1),'Bottom':(.38,0,.80,1),'SpineLeft':(.47,0,.79,1),'SpineRight':(.47,0,.79,1)}
    y=70;sheet=Image.new('RGB',(2400,6*770+70),'#171d1b');draw=ImageDraw.Draw(sheet)
    draw.text((30,20),'PREVIOUS PRINT / CLOSE-UP',fill='white',font=font(30,True));draw.text((1230,20),'POLISHED PRINT / SAME REGION',fill='white',font=font(30,True))
    for slot in FACES:
        for col,image in enumerate([Image.open(PREVIOUS/aid/(slot+'.png')),results[slot]]):
            if slot.startswith('Spine'):image=image.rotate(90 if slot=='SpineLeft' else -90,expand=True)
            box=crops[slot];image=image.crop(tuple(round(v*(image.width if i%2==0 else image.height)) for i,v in enumerate(box)))
            im=ImageOps.contain(image,(1150,690),Image.Resampling.LANCZOS);sheet.paste(im,(col*1200+25+(1150-im.width)//2,y+45))
        draw.text((30,y+4),slot,fill='#acd6c3',font=font(28,True));y+=770
    sheet.save(dest/'close-up-before-after.jpg',quality=95,subsampling=0)
    print(str(dest))


def main():
    global FONT_DIR
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--console',choices=['snes','n64','all'],default='all');p.add_argument('--font-dir',type=Path,default=FONT_DIR);args=p.parse_args();FONT_DIR=args.font_dir
    if args.console in ('snes','all'):
        evidence('snes-super-mario-world-box',snes_faces(),{'Front':'Original 2460-pixel scan, strong edge-preserving halftone removal at native resolution, then 4096-pixel output. Character contours, original title lettering and shading preserved; the small green TM is explicitly re-typeset, and the capsule/quality-seal marks reconstructed.','Back':'Original layout rebuilt with exact transcribed promotional/legal wording, clean title mark, flat black and gray ink, a valid UPC-A with original digits, original four printed screenshots, and reconstructed quality-seal/recycling geometry. Approximate Arial metrics.','default':'Existing correct source-based edge layout retained; original character illustration grain removed at native resolution while keeping the contour and alpha; Nintendo capsule uses the period vector-derived mark.'})
    if args.console in ('n64','all'):
        evidence('nintendo-64-super-mario-64-box',n64_faces(),{'Front':'Matching clean Nintendo Classics original US K-A digital front retained, resampled to 4096 pixels.','Back':'Original five screenshots and gold illustration retained; exact original promotional/legal wording re-typeset after bounded ink removal; original UPC digits encoded cleanly; quality seal, recycling symbol and capsule reconstructed.','default':'Original period Mario / penguin / Bowser pose composited into the original measured panel composition with clean duotone fields, title, console badge, and template orientation. Colors and placement are explicit visual reconstructions.'})


if __name__=='__main__':main()
