#!/usr/bin/env python3
"""Prepare private-review Nintendo box textures from documented source pixels.

This tool never downloads or publishes artwork. Inputs remain in the ignored
reference directory. Perspective correction and conservative local retouch do
not restore detail absent from a photograph, and do not establish reuse rights.
Run from the repository root after obtaining the references in the source catalog.
"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


DEFAULT_ROOT = Path('dist/game-boxes-20261016')


def face(filename, size, quad=None, rotation=0, levels=None, trim=0, note=''):
    return dict(file=filename, size=size, quad=quad, rotation=rotation,
                levels=levels, trim=trim, note=note)


# Quads follow the source's visible plane, in TL/TR/BR/BL order. Rotations
# happen after rectification. Texture pixel sizes are not source resolution.
CONFIG = {
    'nintendo-64-super-mario-64-box': {
        'Front': face('sm64-front-cover.jpg', (2048, 1437)),
        'Back': face('sm64-launchbox-1927.jpg', (2048, 1437), trim=3),
        'SpineLeft': face('sm64-launchbox-1952581.jpg', (1476, 417), rotation=90),
        'SpineRight': face('sm64-1904-full-4.jpg', (1476, 417),
            [(211, 1730), (1818, 1730), (1707, 1993), (306, 1998)],
            levels=(3, 107), trim=4,
            note='Bowser end panel; no game title appears on this original face.'),
        'Top': face('sm64-1904-full-2.jpg', (2048, 403),
            [(89, 1708), (1989, 1701), (1897, 1899), (186, 1908)],
            levels=(3, 170), trim=3),
        'Bottom': face('sm64-1904-full-2.jpg', (2048, 403),
            [(137, 744), (1948, 735), (1868, 916), (227, 924)],
            rotation=180, levels=(3, 170), trim=3,
            note='Green Mario panel, independently verified against the flat Cibby scan.'),
    },
    'nes-super-mario-bros-box': {
        'Front': face('smb-specimen-2.webp', (1437, 2048),
            [(113, 103), (695, 105), (680, 959), (81, 934)],
            levels=(24, 195), trim=7,
            note='Original non-REV-A front. Effective source is approximately 590 by 840 pixels.'),
        'Back': face('smb-launchbox-1178.jpg', (1437, 2048), trim=3,
            note='Round seal, NES P SM, copyright 1985. Hangtab cut is modeled separately.'),
        'SpineLeft': face('smb-specimen-3.webp', (2048, 403),
            [(211, 96), (329, 107), (322, 1189), (199, 1189)],
            rotation=90, levels=(20, 152), trim=7,
            note='Nintendo and Entertainment System logos; low source optical resolution.'),
        'SpineRight': face('smb-specimen-5.webp', (2048, 403),
            [(165, 113), (286, 111), (337, 1145), (223, 1149)],
            rotation=-90, levels=(20, 151), trim=7,
            note='Legal-text spine; low source optical resolution.'),
        'Top': face('smb-specimen-6.webp', (1437, 403),
            [(512, 76), (664, 104), (721, 1197), (557, 1227)],
            rotation=-90, levels=(24, 168), trim=9,
            note='Title and address tuck flap; printed face only, no worn paper edge.'),
        'Bottom': face('smb-specimen-7.webp', (1437, 403),
            [(486, 120), (574, 129), (567, 922), (475, 914)],
            rotation=-90, levels=(24, 165), trim=6,
            note='Unprinted black closure; original glued-bottom construction is separate geometry.'),
    },
    'snes-super-mario-world-box': {
        'Front': face('smw-launchbox-19789364.png', (2048, 1437)),
        'Back': face('smw-specimen-9.webp', (2048, 1437),
            [(241, 145), (1439, 179), (1450, 1058), (153, 998)],
            levels=(13, 211), trim=3,
            note='Original four printed screenshots, copyright 1992, SNS P MW.'),
        'Top': face('smw-specimen-8.webp', (2048, 403),
            [(152, 76), (1580, 522), (1624, 683), (-62, 157)],
            levels=(45, 223), trim=3,
            note='Top photo clips a small unprinted corner. No title or character is synthesized.'),
        'Bottom': face('smw-specimen-10.webp', (2048, 403),
            [(-180, 242), (1520, 436), (1591, 622), (-182, 431)],
            rotation=180, levels=(40, 217), trim=3,
            note='Bottom photo clips the Nintendo oval at one end; complemented by the matching top print.'),
        'SpineLeft': face('smw-specimen-12.webp', (1437, 403),
            [(178, 103), (1531, 540), (1560, 746), (-82, 198)],
            rotation=180, levels=(34, 211), trim=3,
            note='Short-flap print. A second original photograph supplies the clipped gray console symbol.'),
        'SpineRight': face('smw-specimen-11.webp', (1437, 403),
            [(106, 490), (1871, 330), (1890, 598), (-35, 766)],
            rotation=180, levels=(34, 211), trim=3,
            note='Same original short-flap layout; complementary source photographs retain the complete print.'),
    },
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rectify(source, cfg):
    if cfg['quad'] is None:
        corrected = source.copy()
        effective = [source.shape[1], source.shape[0]]
    else:
        q = np.asarray(cfg['quad'], np.float32)
        width = int(round((np.linalg.norm(q[1]-q[0]) + np.linalg.norm(q[2]-q[3]))/2))
        height = int(round((np.linalg.norm(q[3]-q[0]) + np.linalg.norm(q[2]-q[1]))/2))
        effective = [width, height]
        target = np.array([(0, 0), (width-1, 0), (width-1, height-1), (0, height-1)], np.float32)
        corrected = cv2.warpPerspective(source, cv2.getPerspectiveTransform(q, target),
                                        (width, height), flags=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_REPLICATE)
    if cfg['rotation']:
        corrected = np.array(Image.fromarray(corrected).rotate(cfg['rotation'], expand=True))
        if abs(cfg['rotation']) == 90:
            effective.reverse()
    before = corrected.copy()
    if cfg['levels']:
        low, high = cfg['levels']
        corrected = np.clip((corrected.astype(float)-low) * (242/(high-low)) + 8, 0, 255).astype(np.uint8)
    # Only the already photographed border is extended inward; this masks
    # exposed fibers and fold abrasion without replacing any central lettering.
    trim = cfg['trim']
    if trim:
        corrected[:trim] = corrected[trim]
        corrected[-trim:] = corrected[-trim-1]
        corrected[:, :trim] = corrected[:, trim:trim+1]
        corrected[:, -trim:] = corrected[:, -trim-1:-trim]
    return corrected, before, effective


def black_field_cleanup(image, regions, border=0):
    """Heal only explicitly marked neutral scuff fields, retaining colored ink."""
    h, w = image.shape[:2]
    allowed = np.zeros((h, w), np.uint8)
    for x1, y1, x2, y2 in regions:
        allowed[int(y1*h):int(y2*h), int(x1*w):int(x2*w)] = 255
    if border:
        allowed[:border] = 255
        allowed[-border:] = 255
        allowed[:, :border] = 255
        allowed[:, -border:] = 255
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    base = cv2.medianBlur(gray, 9)
    mask = ((allowed > 0) & (hsv[:, :, 1] < 85) & (gray > base + 16) & (base < 85)).astype(np.uint8)*255
    mask = cv2.dilate(mask, np.ones((2, 2), np.uint8))
    return cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA), int(np.count_nonzero(mask))


def remove_photographic_black_cast(image, *, warm=False):
    """Estimate low-frequency glare/color cast from neighboring dark ink."""
    h, w = image.shape[:2]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, w//12)|1, max(15, h//3)|1))
    floor = cv2.erode(image, kernel).astype(np.float32)
    floor = cv2.GaussianBlur(floor, (0, 0), max(3, min(w, h)/10))
    if not warm:
        floor[:] = np.min(floor, axis=2, keepdims=True)
    floor = np.maximum(floor-8, 0)
    result = np.clip((image.astype(float)-floor)*245/(255-floor)+6, 0, 255)
    if warm:
        result *= np.array([1.0, 1.09, 1.34])
    return np.clip(result, 0, 255).astype(np.uint8)


def restore_black_print_fields(image, slot):
    """Neutralize exposed black-paper wear while retaining original ink pixels."""
    rgb = np.array(image)
    h, w = rgb.shape[:2]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    keep = ((hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 115)).astype(np.uint8)
    # Colored ink includes small edge antialiasing and its dark printed outline.
    keep = cv2.dilate(keep, np.ones((5, 5), np.uint8))
    value = hsv[:, :, 2]
    def region(x1, y1, x2, y2, threshold=130):
        ys, xs = slice(int(y1*h), int(y2*h)), slice(int(x1*w), int(x2*w))
        keep[ys, xs] |= (value[ys, xs] > threshold).astype(np.uint8)
    if slot in ('Top', 'Bottom'):
        region(.60, .02, .88, .95, 190)  # Original character highlights and speed lines.
        region(.83, .15, 1, .85, 145)   # Original white Nintendo oval.
    elif slot in ('SpineLeft', 'SpineRight'):
        region(.57, .08, .79, .90, 95)
        region(.74, .02, .985, .90, 80)  # Gray striped console symbol.
        region(.02, .85, .91, .98, 110)  # Fine legal print.
    elif slot == 'Back':
        region(.87, 0, .995, .07, 210)  # Original SNS P MW product code, excluding gray paper glare.
        region(0, .27, .53, .68, 100)
        region(0, .72, .99, .99, 100)
        region(.54, .56, .99, .77, 65)
        keep[int(.075*h):int(.57*h), int(.53*w):int(.99*w)] = 1
        # The gray console emblem consists of continuous horizontal ink lines.
        # Retain those original scan pixels; reject isolated crease/glare spots.
        ys, xs = slice(int(.565*h), int(.775*h)), slice(int(.54*w), int(.99*w))
        symbol = ((value[ys, xs] > 65) & (value[ys, xs] < 210)).astype(np.uint8)
        symbol = cv2.morphologyEx(symbol, cv2.MORPH_OPEN, np.ones((1, 13), np.uint8))
        keep[ys, xs] = symbol
        keep[:int(.012*h)] = 0
    mask = cv2.GaussianBlur(keep.astype(np.float32), (3, 3), .5)[:, :, None]
    black = np.array([10, 12, 15], np.float32)
    restored = rgb.astype(float)*mask+black*(1-mask)
    # A conservative gain restores muted photographed ink; clipped values are
    # limited to highlights, with no redraw or replacement of character detail.
    restored = np.where(mask > .5, restored*1.12, restored)
    return Image.fromarray(np.clip(restored, 0, 255).astype(np.uint8))


def prepare(root, selected=None):
    refs = root/'references'
    index = {}
    for asset, faces in CONFIG.items():
        if selected and asset != selected:
            continue
        destination = root/'artwork'/asset
        destination.mkdir(parents=True, exist_ok=True)
        results, provenance, originals = {}, {}, {}
        for slot, cfg in faces.items():
            path = refs/cfg['file']
            source = np.array(Image.open(path).convert('RGB'))
            corrected, before, effective = rectify(source, cfg)
            photo = '-specimen-' in cfg['file']
            if photo and not asset.startswith('nintendo-64-'):
                corrected = remove_photographic_black_cast(before, warm=asset.startswith('nes-'))
                if asset.startswith('nes-'):
                    value = corrected.max(axis=2).astype(float)
                    factor = np.where(value < 100, .12+.88*(value/100)**2, 1)
                    corrected = np.clip(corrected*factor[:, :, None], 0, 255).astype(np.uint8)
            # NES stars are intentional printed art. Never run automatic dust
            # removal across that face or its back-cover star field.
            regions = []
            if asset.startswith('nes-') and slot in ('SpineLeft', 'SpineRight', 'Top', 'Bottom'):
                regions = [(0, 0, 1, .10), (0, .90, 1, 1)]
            if asset.startswith('snes-'):
                regions = [(0, 0, 1, .04), (0, .96, 1, 1)]
            corrected, changed = black_field_cleanup(corrected, regions)
            results[slot] = Image.fromarray(corrected).resize(cfg['size'], Image.Resampling.LANCZOS)
            originals[slot] = Image.fromarray(before).resize(cfg['size'], Image.Resampling.LANCZOS)
            provenance[slot] = dict(sourceFile=cfg['file'], sourceSha256=sha256(path),
                sourcePixelSize=[source.shape[1], source.shape[0]],
                effectiveRectifiedPixels=effective, outputPixels=list(cfg['size']),
                sourceQuadPixels=cfg['quad'], rotationDegrees=cfg['rotation'],
                levels=cfg['levels'] if not photo else None, borderExtensionPixels=cfg['trim'] if not photo else 0,
                maskedRetouchPixels=changed, notes=cfg['note'])
            provenance[slot]['photographicCastCorrection'] = photo
        if asset.startswith('snes-'):
            # The two opposing retail short flaps carry the same design. Each
            # photo cuts a different end; combine only corresponding face pixels.
            left = np.array(results['SpineLeft'])
            right = np.array(results['SpineRight'])
            width = left.shape[1]
            t = np.clip((np.arange(width)-width*.66)/(width*.08), 0, 1)[None, :, None]
            composite = np.clip(left*(1-t)+right*t, 0, 255).astype(np.uint8)
            results['SpineLeft'] = results['SpineRight'] = Image.fromarray(composite)
            for slot in ('SpineLeft', 'SpineRight'):
                provenance[slot]['composite'] = 'Corresponding original opposite-flap photographs, blend across unprinted field at 66–74% width.'
            # Top and bottom both show the same Nintendo-oval composition. The
            # complete top source supplies only the bottom photo's cropped oval.
            top = np.array(results['Top'])
            bottom = np.array(results['Bottom'])
            start = int(top.shape[1]*.845)
            bottom[int(top.shape[0]*.34):int(top.shape[0]*.86), int(top.shape[1]*.825):] = np.array([15, 17, 20], np.uint8)
            oval = Image.fromarray(top).crop((int(top.shape[1]*.84), int(top.shape[0]*.2), top.shape[1], int(top.shape[0]*.85)))
            oval = oval.resize((top.shape[1]-start, int(top.shape[0]*.65)), Image.Resampling.LANCZOS)
            bottom[int(top.shape[0]*.2):int(top.shape[0]*.2)+oval.height, start:] = np.array(oval)
            results['Bottom'] = Image.fromarray(bottom)
            provenance['Bottom']['composite'] = 'Corresponding Nintendo oval cropped from the original top print supplies the cropped end of the bottom photograph. Original bottom character retained.'
            for slot in ('Back', 'Top', 'Bottom', 'SpineLeft', 'SpineRight'):
                results[slot] = restore_black_print_fields(results[slot], slot)
                provenance[slot]['blackFieldRestoration'] = 'Locally selected neutral-black paper fields; original colored ink, character pixels, grayscale symbol, screenshots and legal type protected.'
        if asset.startswith('nes-'):
            # The bottom is unprinted black. The photographed seam and bare
            # paper are physical wear, not artwork. Sample original black ink.
            bottom = np.array(results['Bottom'])
            sample = np.median(bottom[80:140, 550:650].reshape(-1, 3), axis=0).astype(np.uint8)
            bottom[:] = sample
            results['Bottom'] = Image.fromarray(bottom)
            provenance['Bottom']['plainInkSample'] = dict(bounds=[550, 80, 650, 140], rgb=sample.tolist())
            for slot in ('Front', 'SpineLeft', 'SpineRight', 'Top'):
                im = np.array(results[slot])
                edge = 13 if slot == 'Front' else 12
                ink = np.array([7, 8, 10], np.uint8)
                im[:edge] = ink; im[-edge:] = ink
                im[:, :edge] = ink; im[:, -edge:] = ink
                if slot != 'Front':
                    im = np.clip(im.astype(float)*1.22, 0, 255).astype(np.uint8)
                if slot == 'Front':
                    h, w = im.shape[:2]
                    # Smooth low-value correction avoids visible rectangular
                    # mask boundaries. Bright printed stars remain untouched.
                    blend = np.clip((im.max(axis=2).astype(float)-65)/40, 0, 1)
                    blend = blend*blend*(3-2*blend)
                    # Fine metallic-gold seal lettering is intentionally much
                    # darker than the surrounding yellow action emblem.
                    ys, xs = slice(int(.755*h), int(.99*h)), slice(int(.67*w), int(.985*w))
                    seal_hsv = cv2.cvtColor(im[ys, xs], cv2.COLOR_RGB2HSV)
                    gold = (seal_hsv[:, :, 1] > 100) & (seal_hsv[:, :, 2] > 45)
                    blend[ys, xs] = np.maximum(blend[ys, xs], gold.astype(float))
                    im = np.clip(im*blend[:, :, None]+ink*(1-blend[:, :, None]), 0, 255).astype(np.uint8)
                    im[:int(.018*h), :int(.36*w)] = ink
                    im[:int(.022*h), int(.55*w):] = ink
                    im[:, :int(.014*w)] = ink
                    im[:, -int(.014*w):] = ink
                    im[-int(.009*h):] = ink
                    provenance[slot]['blackPaperCleanup'] = 'Dark lower paper discoloration and exposed outer fiber wear removed. Original white star pattern retained.'
                elif slot == 'Top':
                    h, w = im.shape[:2]
                    im[:, :int(.055*w)] = ink
                    im[:, -int(.055*w):] = ink
                results[slot] = Image.fromarray(im)
                provenance[slot]['outerPaperWearMaskPixels'] = edge
        # The template spine UVs are tall exterior projections. The physical
        # left panel reads clockwise; the opposing right panel reads the other
        # way. Keep this separate from source-photo rectification above.
        for slot, angle in [('SpineLeft', -90), ('SpineRight', 90)]:
            results[slot] = results[slot].rotate(angle, expand=True)
            originals[slot] = originals[slot].rotate(angle, expand=True)
            provenance[slot]['templateUvRotationDegrees'] = angle
            provenance[slot]['outputPixels'] = list(results[slot].size)
        mapping = {}
        for slot, im in results.items():
            output = destination/(slot+'.png')
            im.save(output)
            originals[slot].save(destination/(slot+'-before.png'))
            mapping[slot] = output.as_posix()
            provenance[slot]['outputSha256'] = sha256(output)
        (destination/'mapping.json').write_text(json.dumps(mapping, indent=2)+'\n')
        (destination/'provenance.json').write_text(json.dumps(dict(
            assetId=asset, publicationRights='not-established',
            sourceCatalog='docs/game-box-artwork-sources.json',
            workflow='Original scan pixels; perspective rectification, bounded tonal normalization, border repair and explicitly masked local inpainting. No generated art or typography.',
            limitations='Upsampling does not restore absent print detail. Photograph lighting is estimated; colors are not a calibrated match to the physical ink. See per-face effective resolution.',
            faces=provenance), indent=2)+'\n')
        sheet = Image.new('RGB', (1600, 1600), '#202124')
        draw = ImageDraw.Draw(sheet)
        for i, slot in enumerate(faces):
            x, y = (i%2)*800, (i//2)*530
            draw.text((x+15, y+12), slot, fill='white')
            im = ImageOps.contain(results[slot], (770, 480))
            sheet.paste(im, (x+(800-im.width)//2, y+42))
        sheet.save(destination/'review.jpg', quality=94)
        index[asset] = (destination/'mapping.json').as_posix()
    print(json.dumps(index, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--asset', choices=list(CONFIG))
    args = parser.parse_args()
    prepare(args.output_root, args.asset)
