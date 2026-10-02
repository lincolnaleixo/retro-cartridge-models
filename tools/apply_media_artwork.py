#!/usr/bin/env python3
"""Apply owner-provided artwork to a neutral model, locally in Blender.

No images are downloaded or bundled with this tool. Inputs stay unchanged;
optional UV rectangles select artwork in a scan without editing its pixels.
Outputs are derivatives for local preview until publication rights are established.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_media_models as api


def texture(path, name):
    image = bpy.data.images.load(str(path.resolve()), check_existing=True)
    image.name = name
    image.pack()
    mat = api.material(name, (1, 1, 1), roughness=.52)
    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = image
    node.extension = 'EXTEND'
    mat.node_tree.links.new(node.outputs['Color'], mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    return mat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=('mega-drive', 'playstation-1'), required=True)
    parser.add_argument('--front', type=Path, required=True)
    parser.add_argument('--front-rect', type=float, nargs=4, default=(0, 0, 1, 1), metavar=('LEFT', 'BOTTOM', 'RIGHT', 'TOP'))
    parser.add_argument('--top', type=Path)
    parser.add_argument('--top-rect', type=float, nargs=4, default=(0, 0, 1, 1))
    parser.add_argument('--title', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    root = api.mega_drive() if args.model == 'mega-drive' else api.playstation()
    label = bpy.data.objects['FrontLabel']
    label.data.materials.clear()
    label.data.materials.append(texture(args.front, args.title + ' front artwork'))
    if args.top:
        if args.model != 'mega-drive':
            raise ValueError('A top fold belongs to the Mega Drive cartridge only')
        label.data.materials.append(texture(args.top, args.title + ' top artwork'))
    uv = label.data.uv_layers[0]
    fold = 60 / 67
    for polygon in label.data.polygons:
        is_top = args.top and sum(uv.data[i].uv.y for i in polygon.loop_indices) / len(polygon.loop_indices) > fold + 1e-5
        if is_top:
            polygon.material_index = 1
        left, bottom, right, top = args.top_rect if is_top else args.front_rect
        for i in polygon.loop_indices:
            u, v = uv.data[i].uv
            if args.top:
                v = (v-fold)/(1-fold) if is_top else v/fold
            uv.data[i].uv = (left + u*(right-left), bottom + v*(top-bottom))
    root['exampleTitle'] = args.title
    root['artworkScope'] = 'Owner-provided local preview; third-party artwork excluded from model license'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    stem = args.model
    api.export(root, output / (stem + '.glb'))
    # Packed textures make the source portable. Never persist private input paths.
    for image in bpy.data.images:
        if image.packed_file:
            image.filepath = '//textures/' + image.name
    bpy.ops.wm.save_as_mainfile(filepath=str(output / (stem + '.blend')))
    inputs = [args.front] + ([args.top] if args.top else [])
    (output / 'artwork-provenance.json').write_text(json.dumps({
        'title': args.title, 'model': args.model, 'publicationRights': 'not-established',
        'inputs': [{'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size} for p in inputs],
        'frontRect': args.front_rect, 'topRect': args.top_rect if args.top else None,
        'method': 'UV mapping only; original image bytes unmodified',
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
