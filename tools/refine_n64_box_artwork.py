#!/usr/bin/env python3
"""Restore the selected original US K-A Mario 64 packaging print.

Uses cited original artwork and the previous release's rectified scan pixels.
Colors and restored empty fields are visual approximations, not measured inks.
Published input files are never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from refine_case_box_artwork import descreen

ASSET = 'nintendo-64-super-mario-64-box'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def restore_field(image, boxes):
    """Replace only known logo fields, retaining the original character print."""
    a = np.array(image.convert('RGB'))
    mask = np.zeros(a.shape[:2], np.uint8)
    for x0, y0, x1, y1 in boxes:
        mask[y0:y1, x0:x1] = 255
    # Broad background reconstruction is deliberately recorded as approximate.
    small = cv2.resize(a, (a.shape[1]//5, a.shape[0]//5), interpolation=cv2.INTER_AREA)
    small_mask = cv2.resize(mask, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    filled = cv2.inpaint(small, small_mask, 7, cv2.INPAINT_NS)
    filled = cv2.resize(filled, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_CUBIC)
    alpha = cv2.GaussianBlur(mask.astype(np.float32)/255, (0, 0), 2.0)[:, :, None]
    return Image.fromarray(np.uint8(a*(1-alpha)+filled*alpha))


def paste(canvas, image, box):
    image = image.resize((box[2]-box[0], box[3]-box[1]), Image.Resampling.LANCZOS)
    canvas.paste(image, box[:2], image if image.mode == 'RGBA' else None)


def edge(slot, original, logo, console):
    angle = {'SpineLeft': 90, 'SpineRight': -90}.get(slot, 0)
    source = original.rotate(angle, expand=True).convert('RGB')
    w, h = source.size
    # Remove the specimen's narrow damaged trim without stretching unrelated
    # panels or sampling outside the photograph.
    trim = 5 if slot != 'SpineRight' else 10
    source = source.crop((trim, trim, w-trim, h-trim)).resize((w, h), Image.Resampling.LANCZOS)
    source = descreen(source, 1.1, 1.6, .15)
    a = np.array(source).astype(np.float32)/255
    if slot in ('Top', 'Bottom'):
        # Estimated photographic exposure correction, applied in the original
        # duotone areas before clean full-color logos are composited.
        a = np.power(a, .78 if slot == 'Top' else .72)
    elif slot == 'SpineRight':
        # Preserve Bowser's original printed silhouette; reduce white flash
        # contamination in this red-only print rather than invent a new pose.
        lum = cv2.cvtColor(np.uint8(a*255), cv2.COLOR_RGB2GRAY)/255
        a = np.stack((.40+.53*lum, .015+.60*lum**1.8, .035+.58*lum**1.8), axis=2)
    source = Image.fromarray(np.uint8(np.clip(a*255, 0, 255)))
    if slot in ('Top', 'Bottom'):
        logo_box = (int(w*.018), int(h*.035), int(w*.375), int(h*.955))
        console_box = (int(w*.848), int(h*.10), int(w*.981), int(h*.94))
        clear = [(0, 0, int(w*.40), h), (int(w*.835), 0, w, h)]
    elif slot == 'SpineLeft':
        logo_box = (int(w*.023), int(h*.055), int(w*.515), int(h*.89))
        console_box = (int(w*.78), int(h*.13), int(w*.966), int(h*.84))
        clear = [(0, 0, int(w*.54), h), (int(w*.77), 0, w, h)]
    else:
        logo_box = None
        console_box = (int(w*.795), int(h*.14), int(w*.978), int(h*.91))
        clear = [(int(w*.78), 0, w, h)]
    result = restore_field(source, clear)
    if logo_box:
        paste(result, logo, logo_box)
    badge = console.rotate(-90, expand=True) if slot == 'SpineRight' else console
    paste(result, badge, console_box)
    return result.rotate(-angle, expand=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--previous', type=Path, default=Path('dist/game-boxes-20261016/artwork')/ASSET)
    p.add_argument('--references', type=Path, default=Path('dist/box-refinement-20261016/references/n64'))
    p.add_argument('--output', type=Path, default=Path('dist/box-refinement-20261016/artwork')/ASSET)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    front_file = args.references/'front-nintendo-classics.png'
    front = Image.open(front_file).convert('RGB')
    console = front.crop((1295, 36, 1505, 220))
    # The adjacent folded-corner "Only For" arrow overlaps the lower-left
    # background of this crop. Keep only the rectangular console mark itself.
    badge = Image.new('RGB', console.size, 'white')
    for box in ((10, 8, 203, 46), (40, 47, 170, 176)):
        badge.paste(console.crop(box), box[:2])
    console = badge
    logo_file = args.references/'SuperMario64Logo4.png'
    logo = Image.open(logo_file).convert('RGBA')
    # The separate logo's registration mark differs from the original carton.
    # Retain the original tiny TM from the clean front rather than substitute ®.
    ImageDraw.Draw(logo).rectangle((1395, 440, 1500, 555), fill=(0, 0, 0, 0))
    tm = front.crop((848, 973, 884, 997))
    tm_a = np.array(tm); alpha = np.clip((130-tm_a.mean(axis=2))/100, 0, 1)
    tm = Image.new('RGBA', tm.size, (12, 12, 14, 255));tm.putalpha(Image.fromarray(np.uint8(alpha*255)))
    paste(logo, tm, (1420, 467, 1480, 508))
    old_provenance = json.loads((args.previous/'provenance.json').read_text())
    mapping, records, originals, prepared = {}, {}, {}, {}
    for slot in ('Front', 'Back', 'SpineLeft', 'SpineRight', 'Top', 'Bottom'):
        previous = args.previous/(slot+'.png');old = Image.open(previous).convert('RGB');originals[slot] = old
        if slot == 'Front':
            result = front.resize(old.size, Image.Resampling.LANCZOS)
            method = 'Replaced the soft specimen image with matching original US K-A artwork sourced from Nintendo Classics via MarioWiki; no generated replacement illustration.'
        elif slot == 'Back':
            raw = args.references.parent.parent.parent/'game-boxes-20261016'/'references'/'sm64-launchbox-1927.jpg'
            result = Image.open(raw).convert('RGB')
            result = descreen(result, .95, 1.5, .22).crop((3, 3, result.width-3, result.height-3))
            result = result.resize((3072, 2155), Image.Resampling.LANCZOS)
            method = 'Returned to the 4170-pixel original rear scan, descreened before downsampling to 3072 pixels; retained every paragraph, original screenshot and barcode.'
        else:
            result = edge(slot, old, logo, console)
            method = 'Retained original duotone character pixels and orientation; removed damaged outer trim and scan noise, estimated exposure correction, reconstructed only logo background fields, composited clean original title/console marks.'
        out = args.output/(slot+'.png');result.save(out, optimize=True);prepared[slot] = result
        record = dict(old_provenance['faces'][slot]);record.update({'previousPreparedSha256': sha(previous), 'method': method,
            'output': 'artwork/'+slot+'.png', 'outputPixels': list(result.size), 'outputSha256': sha(out)})
        if slot == 'Front':
            record.update({'sourceFile': front_file.name, 'sourceSha256': sha(front_file), 'sourcePixelSize': list(front.size), 'effectiveRectifiedPixels': list(front.size)})
        if slot not in ('Front', 'Back'):
            record['cleanLogoSources'] = [{'filename': f.name, 'sha256': sha(f)} for f in (logo_file,front_file)]
            record['restorationLimitations'] = 'Empty field reconstruction and photographic exposure are approximate. Original character print remains limited by the photographed source; source-layout title proportions are retained.'
        records[slot] = record;mapping[slot] = str(out.resolve())
    (args.output/'mapping.json').write_text(json.dumps(mapping, indent=2)+'\n')
    (args.output/'provenance.json').write_text(json.dumps({'assetId': ASSET, 'publicationRights': 'not-established',
        'method': 'Pristine print restoration using original Nintendo artwork, source scans, deterministic descreening and explicitly bounded compositing.',
        'limitations': 'Photographic colors and reconstructed empty edge fields are approximations, not calibrated factory inks. No new game illustration was generated. Small original character details retain source-resolution limits.',
        'faces': records}, indent=2)+'\n')
    sheet = Image.new('RGB', (1600, 6*440), '#202226');d = ImageDraw.Draw(sheet)
    for row, slot in enumerate(originals):
        for col, (label, im) in enumerate((('Previous', originals[slot]), ('Refined', prepared[slot]))):
            if slot.startswith('Spine'): im=im.rotate(90 if slot=='SpineLeft' else -90,expand=True)
            im = ImageOps.contain(im, (760, 400));x=col*800+(800-im.width)//2;y=row*440+32
            sheet.paste(im,(x,y));d.text((col*800+12,row*440+10),slot+' / '+label,fill='white')
    sheet.save(args.output/'before-after.jpg',quality=94)
    print(args.output)


if __name__ == '__main__':
    main()
