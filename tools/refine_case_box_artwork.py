#!/usr/bin/env python3
"""Prepare a pristine review revision of Crash, Sonic and NES packaging prints.

This deterministic local workflow reads the previously reviewed textures and
never changes their published package. It does not download or invent artwork.
NES edge logos are composited from the matching original rear print; the small
address/warranty wording is transcribed from the original specimen, using an
explicitly approximate typeface. Artwork rights remain with their owners.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


ASSETS = ('playstation-1-crash-bandicoot-box',
          'mega-drive-sonic-the-hedgehog-box', 'nes-super-mario-bros-box')
INK = (7, 8, 10)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descreen(image, luminance=.65, chroma=1.15, sharpen=.25):
    """Suppress scanned print-screen color noise before texture minification."""
    a = np.array(image.convert('RGB'))
    lab = cv2.cvtColor(a, cv2.COLOR_RGB2LAB)
    lab[:, :, 0] = cv2.GaussianBlur(lab[:, :, 0], (0, 0), luminance)
    lab[:, :, 1:] = cv2.GaussianBlur(lab[:, :, 1:], (0, 0), chroma)
    b = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB).astype(np.float32)
    # Broad, bounded sharpening restores readable edges without restoring the
    # original high-frequency color dots that shimmer in the 3D viewer.
    b += sharpen * (b-cv2.GaussianBlur(b, (0, 0), 1.8))
    return Image.fromarray(np.uint8(np.clip(b, 0, 255)))


def clean_white_on_black(image, regions):
    """Separate white print from a known plain-black strip using soft coverage."""
    a = np.array(image.convert('RGB')).astype(np.float32)
    value = a.mean(axis=2)
    alpha = np.clip((value-42)/170, 0, 1)
    allowed = np.zeros(alpha.shape, np.float32)
    for x0, y0, x1, y1 in regions:
        allowed[y0:y1, x0:x1] = 1
    alpha *= allowed
    alpha = cv2.GaussianBlur(alpha, (0, 0), .35)
    out = np.array(INK)+(np.array((242, 242, 239))-INK)*alpha[:, :, None]
    return Image.fromarray(np.uint8(np.clip(out, 0, 255)))


def crash(slot, image):
    if slot == 'WrapBack':
        # Keep fine legal type crisper than the photographic/screenshotted art.
        smooth = descreen(image, .85, 1.3, .3)
        fine = descreen(image, .50, 1.05, .25)
        a, b = np.array(smooth), np.array(fine)
        a[1130:, 76:1685] = b[1130:, 76:1685]
        result = Image.fromarray(a)
        # These are the two actual black spine panels in the full tray scan.
        for box, regions in (
            ((0, 0, 76, image.height), ((8, 44, 59, 220), (7, 247, 59, 1150), (20, 1256, 64, image.height))),
            ((1692, 0, image.width, image.height), ((12, 44, 65, 204), (9, 242, 67, 1150), (18, 1256, 68, image.height))),
        ):
            result.paste(clean_white_on_black(image.crop(box), regions), box[:2])
        # Only the unprinted outside trim; no legal text is removed.
        draw = ImageDraw.Draw(result)
        draw.line((0, 0, 0, image.height), fill=INK, width=2)
        draw.line((image.width-1, 0, image.width-1, image.height), fill=INK, width=2)
        return result, 'Separate luminance/chroma descreen; fine legal-type region uses a gentler kernel; known plain-black spine fields restored with soft white-ink coverage.'
    result = descreen(image, .58 if slot == 'Front' else .72, 1.15, .28)
    # The narrow outer trim is plain black, while the white torn-paper graphic
    # and all illustrations remain untouched by black-field restoration.
    a = np.array(result)
    if slot in ('Front', 'BookletBack'):
        a[:, :5] = INK
        a[:, -5:] = INK
        a[-4:] = INK
    return Image.fromarray(a), 'Controlled scan descreen; original illustrations and typography retained. Plain outer black trim repaired.'


def sonic(slot, image):
    result = descreen(image, .43, .8, .22)
    if slot != 'Spine':
        return result, 'Mild luminance/chroma descreen to reduce scanner color speckle while retaining all printed text and original screenshots.'
    a = np.array(result).astype(np.float32)
    h, w = a.shape[:2]
    clean = np.full((h, w, 3), INK, np.uint8)
    for x in (45, 169):
        cv2.line(clean, (x, 0), (x, h-1), (39, 40, 42), 3, cv2.LINE_AA)
    for y in range(86, h, 124):
        cv2.line(clean, (0, y), (w-1, y), (39, 40, 42), 3, cv2.LINE_AA)
    allowed = np.zeros((h, w), np.float32)
    allowed[300:875, 68:265] = 1
    allowed[1258:1945, 99:227] = 1
    value = a.max(axis=2)
    chroma = value-a.min(axis=2)
    coverage = np.maximum(np.clip((value-67)/62, 0, 1),
                          np.clip((chroma-15)/35, 0, 1))*allowed
    coverage = cv2.GaussianBlur(coverage, (0, 0), .35)
    out = a*coverage[:, :, None]+clean*(1-coverage[:, :, None])
    return Image.fromarray(np.uint8(out)), 'Spine fold glare and dust removed by rebuilding the measured empty grid; original Sonic title and Mega Drive logo pixels retained with soft coverage.'


def red_glyphs(image, box, color=(236, 75, 36)):
    """Extract only a reviewed single-color logo, never a full illustration."""
    crop = np.array(image.crop(box)).astype(np.float32)
    alpha = np.clip((crop[:, :, 0]-np.maximum(crop[:, :, 1], crop[:, :, 2])-20)/135, 0, 1)
    alpha = cv2.GaussianBlur(alpha, (0, 0), .55)
    # Smooth antialiasing remains; this is not a binary mask.
    result = Image.new('RGBA', (crop.shape[1], crop.shape[0]), (*color, 255))
    result.putalpha(Image.fromarray(np.uint8(alpha*255)))
    return result


def paste_logo(canvas, logo, bounds):
    x0, y0, x1, y1 = bounds
    logo = logo.resize((x1-x0, y1-y0), Image.Resampling.LANCZOS)
    canvas.paste(logo, (x0, y0), logo)


def set_type(canvas, text, bounds, font, color=(225, 225, 220)):
    """Typeset only legible, explicitly transcribed specimen wording."""
    face = ImageFont.truetype(str(font), 100)
    b = face.getbbox(text)
    mask = Image.new('L', (b[2]-b[0]+4, b[3]-b[1]+4))
    ImageDraw.Draw(mask).text((2-b[0], 2-b[1]), text, fill=255, font=face)
    mask = mask.resize((bounds[2]-bounds[0], bounds[3]-bounds[1]), Image.Resampling.LANCZOS)
    solid = Image.new('RGB', mask.size, color)
    canvas.paste(solid, bounds[:2], mask)


def clean_nes_empty_fields(image, slot):
    """Remove bounded abrasion only; retain identifiable printed rear stars."""
    a = np.array(image)
    mask = np.zeros(a.shape[:2], np.uint8)
    if slot == 'Front':
        # Reviewed oblong fibers and irregular flakes in empty black areas.
        # The larger star at the lower left and colored foreground are outside
        # these masks. No generic threshold touches the Mario illustration.
        for x, y, r in ((610, 46, 20), (113, 259, 8), (1392, 707, 10),
                        (1394, 827, 12), (1417, 1526, 12), (796, 1587, 20),
                        (664, 1645, 15), (1328, 1610, 18), (862, 1518, 11),
                        (962, 1887, 11), (977, 1987, 12)):
            cv2.circle(mask, (x, y), r, 255, -1)
    else:
        # Small scan debris in known empty fields only. Connected components
        # above 16 pixels include the genuine star graphics and are retained.
        allowed = np.zeros(mask.shape, np.uint8)
        for x0, y0, x1, y1 in ((0, 75, 1437, 290), (0, 290, 80, 1125),
                              (1377, 50, 1437, 1125), (725, 1505, 810, 1930),
                              (0, 1505, 360, 1570)):
            allowed[y0:y1, x0:x1] = 1
        values = a.max(axis=2)
        candidate = ((values > 35) & (allowed > 0)).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, 8)
        for label in range(1, count):
            if stats[label, cv2.CC_STAT_AREA] <= 16:
                mask[labels == label] = 255
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    return Image.fromarray(cv2.inpaint(a, mask, 3, cv2.INPAINT_TELEA)), int(np.count_nonzero(mask))


def nes(slot, image, originals, font):
    if slot == 'Bottom':
        return Image.new('RGB', image.size, INK), 'Unprinted black closure, uniform fresh ink.'
    if slot == 'Back':
        repaired, count = clean_nes_empty_fields(image, slot)
        return descreen(repaired, .62, 1.0, .25), f'Original scanned rear, including identifiable printed stars and all four original screenshots; {count} pixels in bounded empty fields locally repaired, then print-screen noise reduced.'
    if slot == 'Front':
        # The intentionally printed star field and warm metallic gold seal
        # remain. No full-face foreground threshold is used.
        repaired, count = clean_nes_empty_fields(image, slot)
        a = np.array(repaired)
        filtered = cv2.bilateralFilter(a, 5, 12, 1.1)
        return Image.fromarray(filtered), f'Gentle edge-preserving scan-noise reduction; {count} masked pixels in reviewed empty black fields locally repaired. Original art, gold seal and identifiable printed stars retained.'
    rear = descreen(originals['Back'], .65, 1.0, .15)
    super_logo = red_glyphs(rear, (98, 299, 428, 377))
    main_logo = red_glyphs(rear, (98, 389, 722, 466))
    nintendo = red_glyphs(rear, (818, 1510, 1374, 1651))
    canvas = Image.new('RGB', (image.height, image.width) if slot.startswith('Spine') else image.size, INK)
    if slot == 'Top':
        paste_logo(canvas, super_logo, (390, 16, 509, 77))
        paste_logo(canvas, main_logo, (383, 94, 1039, 262))
        set_type(canvas, 'NINTENDO of America Inc.', (129, 288, 401, 317), font)
        set_type(canvas, 'P.O. Box 957 Redmond, WA 98052 U.S.A.', (129, 332, 573, 361), font)
        set_type(canvas, 'Made in Japan', (1138, 332, 1300, 361), font)
    else:
        if slot == 'SpineLeft':
            paste_logo(canvas, super_logo, (83, 35, 202, 94))
            paste_logo(canvas, main_logo, (70, 111, 724, 279))
            paste_logo(canvas, nintendo, (1012, 77, 1418, 247))
            # The original two-line console wordmark has a proprietary shape;
            # retain its photographed glyphs instead of substituting a font.
            old = originals['SpineLeft'].rotate(90, expand=True)
            patch = np.array(old.crop((1423, 96, 2008, 246))).astype(float)
            value = patch.max(axis=2)
            coverage = np.clip((value-70)/135, 0, 1)
            coverage = cv2.GaussianBlur(coverage.astype(np.float32), (0, 0), .6)
            clean = np.array(INK)+(np.array((245, 205, 60))-INK)*coverage[:, :, None]
            canvas.paste(Image.fromarray(np.uint8(clean)), (1423, 96))
            canvas = canvas.rotate(-90, expand=True)
        else:
            paste_logo(canvas, super_logo, (145, 101, 273, 159))
            paste_logo(canvas, main_logo, (137, 181, 826, 350))
            set_type(canvas, 'WARRANTY', (1342, 122, 1495, 161), font)
            set_type(canvas, '90 day limited warranty for game pak', (1342, 205, 1910, 241), font)
            set_type(canvas, '(complete warranty information inside box)', (1342, 269, 1930, 305), font)
            canvas = canvas.rotate(90, expand=True)
    return canvas, 'Clean edge reconstruction: matching rear-scan title/Nintendo glyphs reused in specimen layout; exact legible address/warranty wording typeset with an approximate narrow sans-serif. Black fields are uniform; no wear is retained.'


def make_review(before, after, destination):
    slots = list(after)
    width, row = 1600, 620
    sheet = Image.new('RGB', (width, row*len(slots)), (25, 27, 31))
    draw = ImageDraw.Draw(sheet)
    for i, slot in enumerate(slots):
        for column, (label, group) in enumerate((('Previous', before), ('Refined', after))):
            im = group[slot]
            if slot == 'SpineLeft': im = im.rotate(90, expand=True)
            if slot == 'SpineRight': im = im.rotate(-90, expand=True)
            im = ImageOps.contain(im, (770, 560))
            x, y = column*800, i*row
            draw.text((x+20, y+12), f'{slot} / {label}', fill='white')
            sheet.paste(im, (x+(800-im.width)//2, y+45+(560-im.height)//2))
    sheet.save(destination/'before-after.jpg', quality=95)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('dist/game-boxes-20261016/artwork'))
    parser.add_argument('--output', type=Path, default=Path('dist/box-refinement-20261016/artwork'))
    parser.add_argument('--asset', choices=ASSETS)
    parser.add_argument('--text-font', type=Path,
                        default=Path('/System/Library/Fonts/Supplemental/Arial Narrow.ttf'))
    args = parser.parse_args()
    for asset in ASSETS:
        if args.asset and asset != args.asset: continue
        source = args.input/asset
        mapping = json.loads((source/'mapping.json').read_text())
        before = {slot: Image.open(source/(slot+'.png')).convert('RGB') for slot in mapping}
        after, records, output_mapping = {}, {}, {}
        destination = args.output/asset
        destination.mkdir(parents=True, exist_ok=True)
        for slot, image in before.items():
            if asset.startswith('playstation'): result, method = crash(slot, image)
            elif asset.startswith('mega-drive'): result, method = sonic(slot, image)
            else: result, method = nes(slot, image, before, args.text_font)
            result.save(destination/(slot+'.png'), optimize=True)
            output_mapping[slot] = str((destination/(slot+'.png')).resolve())
            after[slot] = result
            records[slot] = dict(inputFile=slot+'.png', inputSha256=sha(source/(slot+'.png')),
                                 outputFile=slot+'.png', outputSha256=sha(destination/(slot+'.png')),
                                 outputPixels=list(result.size), method=method)
            if asset.startswith('nes') and slot in ('Top', 'SpineLeft', 'SpineRight'):
                records[slot]['additionalPreparedInputs'] = [dict(file='Back.png',
                    sha256=sha(source/'Back.png'), usage='Matching original rear print supplies cleaner title and Nintendo glyph contours.')]
        (destination/'mapping.json').write_text(json.dumps(output_mapping, indent=2)+'\n')
        provenance = dict(assetId=asset, sourceCatalog='docs/game-box-artwork-sources.json',
                          workflow='Deterministic local scan descreen and documented face-specific pristine reconstruction.',
                          limitations='No scan detail is invented. Colors are estimated from uncalibrated references. NES original illustration and small photographed console wordmark remain optically softer than reconstructed edges.',
                          previousProvenanceSha256=sha(source/'provenance.json'), faces=records)
        if asset.startswith('nes'):
            provenance['transcribedTextTypeface'] = dict(file=args.text_font.name, sha256=sha(args.text_font),
                fidelity='Approximate narrow sans-serif; wording and line breaks transcribed from the documented early US specimen.')
        (destination/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
        make_review(before, after, destination)
        print(asset, len(after), 'reviewed face revisions')


if __name__ == '__main__':
    main()
