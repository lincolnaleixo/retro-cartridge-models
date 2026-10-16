#!/usr/bin/env python3
"""Rebuild the worn SMW box edges and preserve a complete original rear scan.

This is a documented restoration/reconstruction, not a newly discovered full-box
scan. Requires the individually attributed references in the ignored reference
directory. Existing immutable releases are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parents[1]
ASSET = 'snes-super-mario-world-box'
INK = (9, 11, 14)
REFS = ROOT / 'dist/snes-box-refinement-20261016/references'
OLD = ROOT / 'dist/game-boxes-20261016/artwork' / ASSET
OLD_REFS = ROOT / 'dist/game-boxes-20261016/references'
DEFAULT_OUTPUT = ROOT / 'dist/box-refinement-20261016/artwork' / ASSET


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size, narrow=False):
    names = [
        Path('/System/Library/Fonts/Supplemental') / ('Arial Narrow.ttf' if narrow else 'Arial.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ]
    for path in names:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise RuntimeError('An Arial or DejaVu Sans font is required for the restored legal line.')


def official_cutout(filename, *, negative_seeds=(), motion_lines=False):
    """Remove only border-connected white paper; keep enclosed character whites.

    Small detached strokes are original motion marks. On the black retail box
    those strokes are printed white, so they are recolored without changing
    their paths. The character outline and internal black shading stay black.
    """
    rgb = np.array(Image.open(REFS / filename).convert('RGB'))
    white = (rgb.min(axis=2) > 216) & ((rgb.max(axis=2)-rgb.min(axis=2)) < 38)
    components, _ = label(white)
    outside = set(np.unique(np.concatenate((components[0], components[-1], components[:, 0], components[:, -1]))))
    outside.discard(0)
    for x, y in negative_seeds:
        if components[y, x]:
            outside.add(int(components[y, x]))
    paper = np.isin(components, list(outside))
    foreground = (~paper).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    alpha = np.zeros(foreground.shape, np.uint8)
    for index in range(1, n):
        area = stats[index, cv2.CC_STAT_AREA]
        if area < 24:
            continue
        mask = labels == index
        alpha[mask] = 255
        if motion_lines and area < 11000:
            rgb[mask] = (235, 235, 225)
    # Remove the bright paper fringe by pulling the matte inward by one pixel.
    alpha = cv2.erode(alpha, np.ones((2, 2), np.uint8))
    alpha = cv2.GaussianBlur(alpha, (3, 3), .42)
    result = Image.fromarray(np.dstack((rgb, alpha)), 'RGBA')
    return result.crop(result.getbbox())


def paste_fit(canvas, art, bounds):
    x, y, width, height = bounds
    art = ImageOps.contain(art, (width, height), Image.Resampling.LANCZOS)
    canvas.alpha_composite(art, (x + (width-art.width)//2, y+(height-art.height)//2))


def title_art():
    # Archived clean international mark: same lettering and two-line arrangement
    # as the original side prints. Documented vector-derived reference, not scan.
    art = Image.open(REFS / 'Logo_EN_(alt)_-_Super_Mario_World.png').convert('RGBA')
    pixels = np.array(art)
    # The retail black-field mark uses a green TM; keep the archived glyph
    # alpha, changing only its ink color so it does not disappear on black.
    pixels[198:230, 1427:1491, :3] = (112, 166, 38)
    art = Image.fromarray(pixels, 'RGBA')
    return art.crop(art.getbbox())


def oval_art():
    # The original front supplies the exact red/cream Nintendo capsule.
    front = Image.open(OLD_REFS / 'smw-launchbox-19789364.png').convert('RGBA')
    oval = front.crop((2070, 145, 2440, 252))
    arr = np.array(oval)
    # Only exterior near-black paper becomes transparent. The wordmark stays.
    arr[:, :, 3] = np.where(arr[:, :, :3].max(axis=2) < 45, 0, 255)
    oval = Image.fromarray(arr, 'RGBA')
    return oval.crop(oval.getbbox())


def striped_symbol(size):
    """Trace the two diagonal negative shapes of the original gray SNES motif."""
    w, h = size
    factor = 3
    im = Image.new('RGBA', (w*factor, h*factor))
    draw = ImageDraw.Draw(im)
    for y in range(0, h*factor, 23*factor):
        draw.rectangle((0, y, w*factor, y+10*factor), fill=(70, 72, 73, 255))
    # Normalized contours traced from the undistorted front motif: one thin
    # diagonal and four rounded diagonal lobes, rather than a generic Z shape.
    cutouts = [
        [(1, .035), (.74, .105), (0, .43), (0, .535), (.72, .135)],
        [(.43,.285),(.56,.285),(.585,.305),(.58,.36),(.50,.425),(.32,.55),(.22,.61),(.17,.62),(.155,.595),(.17,.54),(.36,.35)],
        [(.84,.285),(.92,.285),(.945,.31),(.93,.37),(.86,.43),(.68,.56),(.58,.62),(.535,.63),(.51,.61),(.515,.555),(.75,.35)],
        [(.38,.64),(.47,.64),(.50,.665),(.485,.72),(.40,.79),(.20,.935),(.12,.975),(.08,.975),(.06,.95),(.065,.895),(.28,.715)],
        [(.80,.64),(.89,.64),(.915,.665),(.90,.72),(.82,.79),(.62,.935),(.53,.975),(.48,.975),(.45,.95),(.455,.895),(.68,.715)],
    ]
    for pts in cutouts:
        draw.polygon([(round(x*w*factor), round(y*h*factor)) for x, y in pts], fill=(*INK, 255))
    return im.resize(size, Image.Resampling.LANCZOS)


def legal_line(width, height):
    text = 'NINTENDO OF AMERICA INC.    P.O. BOX 957, REDMOND, WA 98073-0957 U.S.A.    MADE IN JAPAN'
    f = font(64, narrow=True)
    box = f.getbbox(text)
    im = Image.new('RGBA', (box[2]+8, box[3]-box[1]+8))
    ImageDraw.Draw(im).text((4, 4-box[1]), text, font=f, fill=(230, 230, 225, 255))
    return im.resize((width, height), Image.Resampling.LANCZOS)


def clean_back():
    rgb = np.array(Image.open(REFS / 'cibby-back.jpg').convert('RGB')).astype(np.float32)
    # A smooth dark-ink curve removes scanner fog without thresholding away
    # letters, screenshots, barcode bars, gray stripes or colored title shadows.
    value = rgb.max(axis=2)
    blend = np.clip((value-19)/35, 0, 1)
    blend = blend*blend*(3-2*blend)
    rgb = rgb*blend[:, :, None] + np.array(INK)*(1-blend[:, :, None])
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    # These areas are unprinted margin damage in the source, not content.
    rgb[:29, :635] = INK
    rgb[29:86, 7:165] = INK
    rgb[:, :7] = INK
    rgb[-11:, :] = INK
    rgb[:4, :] = INK
    rgb[:, -3:] = INK
    # The upper-right crease crosses only regular horizontal gray ink stripes.
    # Restore each row from the undamaged adjacent stripe field, stopping before
    # the original product code. No source lettering is regenerated.
    for y in range(0, 19):
        rgb[y, 686:1143] = np.median(rgb[y, 740:930], axis=0)
    rgb[:4, :] = INK
    # A diagonal crease crosses the final copyright line, so retain the exact
    # wording but typeset these three small lines instead of blurring glyphs.
    rgb[746:, 916:] = INK
    restored = Image.fromarray(rgb).convert('RGBA')
    lines = [('TM AND ® ARE TRADEMARKS OF', 750, 190),
             ('NINTENDO OF AMERICA INC.', 761, 166),
             ('© 1992 NINTENDO OF AMERICA INC.', 773, 206)]
    for text, y, width in lines:
        f = font(44)
        box = f.getbbox(text)
        line = Image.new('RGBA', (box[2]+4, box[3]-box[1]+4))
        ImageDraw.Draw(line).text((2, 2-box[1]), text, font=f, fill=(220,220,216,255))
        line = line.resize((width, 10), Image.Resampling.LANCZOS)
        restored.alpha_composite(line, (919,y))
    return restored.convert('RGB').resize((2048, 1437), Image.Resampling.LANCZOS)


def make_edges():
    logo, oval = title_art(), oval_art()
    stomp = official_cutout('SMW_Art_-_Mario_Shell_Stomp.png', motion_lines=True)
    landing = official_cutout('SMW_Cape_Mario_landing_on_a_Dry_Bones.jpg', motion_lines=True)
    landing = ImageOps.mirror(landing)
    flying = official_cutout('SMW_Art_-_Cape_Mario_Flying.png', motion_lines=True)
    diving = official_cutout('SMW_Art_-_Cape_Mario_Diving.png', negative_seeds=[(320, 335)], motion_lines=True)
    result = {}
    for slot, character in [('Top', stomp), ('Bottom', landing)]:
        canvas = Image.new('RGBA', (2048, 403), (*INK, 255))
        paste_fit(canvas, logo, (35, 24, 970, 325))
        paste_fit(canvas, character, (1285, 16, 400, 365))
        paste_fit(canvas, oval, (1713, 125, 295, 130))
        result[slot] = canvas.convert('RGB')
    # Opposing flaps carry different original Mario poses. They must not be
    # blended together, which was the major authenticity error in the old prep.
    for slot, character, angle in [('SpineLeft', flying, -90), ('SpineRight', diving, 90)]:
        canvas = Image.new('RGBA', (1437, 403), (*INK, 255))
        paste_fit(canvas, logo, (24, 34, 790, 288))
        paste_fit(canvas, character, (815, 30, 225, 305))
        canvas.alpha_composite(striped_symbol((320, 362)), (1085, 18))
        canvas.alpha_composite(legal_line(1015, 25), (26, 360))
        result[slot] = canvas.convert('RGB').rotate(angle, expand=True)
    return result


def source_record(path, page, image_url, role, method):
    return dict(file=path.name, sha256=digest(path), pixelSize=list(Image.open(path).size),
                sourcePage=page, imageUrl=image_url, role=role, method=method,
                credit='Nintendo; archival reference contributor credited by the linked source page',
                rights='Third-party copyrighted artwork; no separate redistribution license established.')


def prepare(destination):
    destination.mkdir(parents=True, exist_ok=True)
    results = {'Front': Image.open(OLD / 'Front.png').convert('RGB'), 'Back': clean_back(), **make_edges()}
    mapping = {}
    for slot, im in results.items():
        output = destination / (slot+'.png')
        im.save(output)
        mapping[slot] = output.relative_to(ROOT).as_posix()
    # The front is copied byte for byte rather than encoded again.
    (destination/'Front.png').write_bytes((OLD/'Front.png').read_bytes())
    (destination/'mapping.json').write_text(json.dumps(mapping, indent=2)+'\n')
    records = []
    records.append(source_record(REFS/'cibby-back.jpg', 'https://cibby.app/games/super-mario-world-snes/',
        'https://media.cibby.app/games/72626b9d-ad8e-45da-b583-4c67683d2329/media/66bc1053-cf0b-40de-92a4-dde25585b932.jpg',
        'Back', 'Complete original US 1992 retail rear scan, including the original four printed screenshots.'))
    src_records = json.loads((REFS/'mario-official-reference-records.json').read_text())
    src_records += [json.loads((REFS/(f+'.json')).read_text()) for f in ['SMW_Art_-_Cape_Mario_Diving.png', 'Logo_EN_(alt)_-_Super_Mario_World.png']]
    used = {'SMW_Art_-_Mario_Shell_Stomp.png':'Top', 'SMW_Cape_Mario_landing_on_a_Dry_Bones.jpg':'Bottom',
            'SMW_Art_-_Cape_Mario_Flying.png':'SpineLeft', 'SMW_Art_-_Cape_Mario_Diving.png':'SpineRight',
            'Logo_EN_(alt)_-_Super_Mario_World.png':'All four edges'}
    for record in src_records:
        name = record['file']
        if name in used:
            records.append(source_record(REFS/name, record['sourcePage'], record['imageUrl'], used[name],
                'Archived period illustration, composited in the physical specimen layout.' if name != 'Logo_EN_(alt)_-_Super_Mario_World.png' else
                'Archived clean vector-derived international title mark; a reconstruction reference rather than original box-scan pixels.'))
    records.append(source_record(OLD_REFS/'smw-launchbox-19789364.png', 'https://gamesdb.launchbox-app.com/games/images/131-super-mario-world',
        'https://images.launchbox-app.com/00fb4aca-c22f-4ca9-84d0-90cf8c22d4af.png', 'Front and Nintendo capsule on Top/Bottom',
        'Front retained byte for byte; original Nintendo capsule cropped from [2070,145,2440,252].'))
    provenance = dict(assetId=ASSET, edition='United States, original black-label retail box, SNS P MW, copyright 1992',
        workflow='Original full rear scan restored with a continuous dark-ink curve; three creased lower-right trademark/copyright lines re-typeset with their exact original wording. Four edges reconstructed from archived matching period illustrations, title lettering and front-scan Nintendo capsule, with clean flat ink fields. Original side legal line re-typeset and gray striped motif traced from specimen. No generative imagery.',
        fixes=['The complete original back text, barcode and screenshots replace the damaged oblique photograph.',
               'Top shows Mario stomping the shell and ejecting the Koopa; bottom shows the mirrored Dry Bones landing.',
               'Left flap uses the original upward flying pose; right flap uses the distinct diving pose.',
               'Black print backgrounds, margins and legal line are clean and complete.'],
        limitations=['Edges are a documented reconstruction, not a claim of a new factory-flat scan.',
                     'Original rear source is 1143 × 800 pixels; enlargement does not add fine print information.',
                     'Original Dry Bones landing artwork is 429 × 438 pixels.',
                     'Colors are visually normalized; no physical ink calibration is available.',
                     'Gray striped motif and legal-line typeface are close reconstructions with approximately placed layout.'],
        publicationRights='not-established', sources=records,
        faces={slot:dict(outputPixels=list(im.size),outputSha256=digest(destination/(slot+'.png')),
             templateUvRotationDegrees=(-90 if slot=='SpineLeft' else 90 if slot=='SpineRight' else 0)) for slot, im in results.items()})
    (destination/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    # Horizontal review avoids confusing narrow panel UV orientation with print.
    rows = [('Back',520),('Top',190),('Bottom',190),('SpineLeft',250),('SpineRight',250)]
    total = 80 + sum(height+45 for _,height in rows)
    sheet = Image.new('RGB', (2200,total), '#202328')
    draw=ImageDraw.Draw(sheet)
    draw.text((30,20),'PREVIOUS RELEASE',font=font(26),fill='white')
    draw.text((1130,20),'RESTORED PRINT',font=font(26),fill='white')
    y=70
    for slot,height in rows:
        draw.text((30,y),slot,font=font(22),fill='#a8c4d6')
        for col,im in enumerate([Image.open(OLD/(slot+'.png')),results[slot]]):
            if slot=='SpineLeft': im=im.rotate(90,expand=True)
            if slot=='SpineRight': im=im.rotate(-90,expand=True)
            im=ImageOps.contain(im,(1050,height),Image.Resampling.LANCZOS)
            sheet.paste(im,(col*1100+25+(1050-im.width)//2,y+32))
        y+=height+45
    sheet.save(destination/'before-after-review.jpg',quality=95)
    print(json.dumps({'mapping':mapping,'review':str(destination/'before-after-review.jpg')},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    prepare(args.output.resolve())
