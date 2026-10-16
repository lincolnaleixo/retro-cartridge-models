#!/usr/bin/env python3
"""Prepare reviewed Sonic/Crash case scans without redrawing original artwork.

Inputs are reference files documented in docs/game-box-artwork-sources.json.
The Sonic manual cover PNGs are losslessly extracted with Poppler pdfimages
from pages 1 and 40 of Sonic1_MD_EU_manual.pdf. Original files stay unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_manual(rgb, back):
    """Restore empty black/grid ink while retaining scanned printed foreground."""
    h, w = rgb.shape[:2]
    clean = np.full_like(rgb, (12, 15, 18))
    xs = [92, 217, 342, 467, 592, 717, 842, 967, 1092, 1217, 1342, 1467, 1592, 1717, 1842]
    ys = [60, 185, 310, 435, 560, 685, 810, 935, 1060]
    if not back:
        xs = [1055, 1178, 1301, 1424, 1547, 1670, 1793, 1916]
        ys = [190, 315, 440, 565, 690, 815, 940, 1065]
    for x in xs:
        cv2.line(clean, (x, 0), (x, h-1), (32, 34, 37), 2, cv2.LINE_AA)
    for y in ys:
        cv2.line(clean, (0, y), (w-1, y), (32, 34, 37), 2, cv2.LINE_AA)
    if back:
        # Preserve original legal/code lettering in its original position.
        alpha = np.zeros((h, w), np.float32)
        for x0, y0, x1, y1 in [(1080, 812, 1900, 896), (1090, 956, 1900, 1088)]:
            luminance = rgb[y0:y1, x0:x1].mean(axis=2)
            alpha[y0:y1, x0:x1] = np.clip((luminance-72)/110, 0, 1)
        return np.uint8(rgb*alpha[..., None] + clean*(1-alpha[..., None]))
    region = rgb[:, 1055:]
    lum = region.max(axis=2).astype(float)
    chroma = region.max(axis=2).astype(float)-region.min(axis=2)
    alpha = np.clip(np.maximum((lum-65)/55, (chroma-20)/30), 0, 1)
    alpha[595:940] = 0
    rgb[:, 1055:] = np.uint8(region*alpha[..., None]+clean[:, 1055:]*(1-alpha[..., None]))
    return rgb


def restore(source, crop, points=(), border=0, rotate=False):
    rgb = np.array(Image.open(source).convert('RGB'))
    if source.name.startswith('sonic-manual-'):
        rgb = clean_manual(rgb, 'last' in source.name)
    mask = np.zeros(rgb.shape[:2], np.uint8)
    for x, y, radius in points:
        cv2.circle(mask, (x, y), radius, 255, -1)
    if mask.any():
        rgb = cv2.inpaint(rgb, mask, 4, cv2.INPAINT_TELEA)
    image = Image.fromarray(rgb).crop(crop)
    if border:
        # Scan binding damage falls only in the empty black trim. Extend the
        # neighboring ink, not the printed title, logos or illustration.
        a = np.array(image)
        a[:, :border] = a[:, border:border + 1]
        a[:, -border:] = a[:, -border - 1:-border]
        a[:border] = a[border:border + 1]
        a[-border:] = a[-border - 1:-border]
        image = Image.fromarray(a)
    if rotate:
        image = image.transpose(Image.Transpose.ROTATE_90)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--references', type=Path, default=Path('dist/game-boxes-20261016/references'))
    parser.add_argument('--output', type=Path, default=Path('dist/game-boxes-20261016/artwork'))
    args = parser.parse_args()
    plans = {
        'playstation-1-crash-bandicoot-box': {
            'Front': ('crash-F-ALL.jpg', (10, 4, 1435, 1405), [(814, 1380, 8)], 10, False),
            'WrapBack': ('crash-B-ALL.jpg', (4, 3, 1772, 1371), [(234, 228, 7)], 2, False),
            'BookletBack': ('crash-I-1.jpg', (5, 3, 1422, 1407), [], 3, False),
            'WrapInside': ('crash-I-2.jpg', (4, 4, 1759, 1384), [], 2, False),
        },
        'mega-drive-sonic-the-hedgehog-box': {
            'Front': ('sonic-eu-wrap.jpg', (1735, 4, 3176, 2030), [], 0, False),
            'Back': ('sonic-eu-wrap.jpg', (4, 4, 1404, 2030), [(140, 118, 5), (1330, 77, 4)], 0, False),
            'Spine': ('sonic-eu-wrap.jpg', (1424, 4, 1704, 2030), [], 0, False),
            'BookletFront': ('sonic-manual-cover-000.png', (5, 4, 1935, 1099), [], 0, True),
            'BookletBack': ('sonic-manual-last-000.png', (5, 4, 1933, 1099), [], 0, True),
        },
    }
    for asset_id, slots in plans.items():
        destination = args.output / asset_id
        destination.mkdir(parents=True, exist_ok=True)
        mapping, records = {}, {}
        for slot, (filename, crop, points, border, rotate) in slots.items():
            source = args.references / filename
            image = restore(source, crop, points, border, rotate)
            output = destination / (slot + '.png')
            image.save(output, optimize=True)
            mapping[slot] = str(output.resolve())
            records[slot] = {'source': filename, 'sourceSha256': sha(source),
                'sourcePixels': list(Image.open(source).size), 'cropPixels': crop,
                'inpaintCircles': points, 'blackTrimExtensionPixels': border,
                'rotateCounterclockwise90': rotate, 'outputPixels': list(image.size),
                'output': output.name, 'sha256': sha(output)}
        (destination / 'mapping.json').write_text(json.dumps(mapping, indent=2) + '\n')
        (destination / 'provenance.json').write_text(json.dumps({
            'assetId': asset_id, 'method': ('Local scan cleanup; no generated illustration or replacement lettering.' + (' Sonic manual empty black/grid fields are restored from measured grid spacing while original foreground print is retained.' if asset_id.startswith('mega-drive') else '')),
            'color': 'Original sRGB scan colors preserved; no global saturation or white-balance shift.',
            'limitations': 'Source printing and scan resolution are preserved. Fine paper texture and residual minor scan variation remain approximate.',
            'slots': records}, indent=2) + '\n')
        print(asset_id, len(records), 'prepared print surfaces')


if __name__ == '__main__':
    main()
