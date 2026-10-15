#!/usr/bin/env python3
"""Apply supplied artwork to a neutral model, locally in Blender.

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
from artwork_coordinates import photo_uv
from source_paths import sanitize_source_paths


def texture(path, name):
    image = bpy.data.images.load(str(path.resolve()), check_existing=True)
    image.name = name
    # Printed artwork is display-referred color, not a scalar/material map.
    image.colorspace_settings.name = 'sRGB'
    image.pack()
    mat = api.material(name, (1, 1, 1), roughness=.68)
    shader = mat.node_tree.nodes.get('Principled BSDF')
    # Keep broad white highlights from washing out printed dark ink. This
    # exports as KHR_materials_specular; the optical substrate stays separate.
    shader.inputs['Specular IOR Level'].default_value = .18
    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = image
    node.extension = 'EXTEND'
    mat.node_tree.links.new(node.outputs['Color'], shader.inputs['Base Color'])
    return mat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=tuple(api.BUILDERS), required=True)
    parser.add_argument('--front', type=Path, required=True)
    parser.add_argument('--front-rect', type=float, nargs=4, default=(0, 0, 1, 1), metavar=('LEFT', 'BOTTOM', 'RIGHT', 'TOP'))
    parser.add_argument('--front-quad', type=float, nargs=8, help='Photo UV corners: bottom-left, bottom-right, top-right, top-left')
    parser.add_argument('--top', type=Path)
    parser.add_argument('--top-rect', type=float, nargs=4, default=(0, 0, 1, 1))
    parser.add_argument('--top-quad', type=float, nargs=8)
    parser.add_argument('--rear', type=Path)
    parser.add_argument('--rear-rect', type=float, nargs=4, default=(0, 0, 1, 1))
    parser.add_argument('--rear-quad', type=float, nargs=8)
    parser.add_argument('--title', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    root = api.BUILDERS[args.model]()
    label = bpy.data.objects['FrontLabel']
    label.data.materials.clear()
    label.data.materials.append(texture(args.front, args.title + ' front artwork'))
    if args.top:
        if args.model != 'mega-drive' and 'artworkFoldV' not in label:
            raise ValueError('This model has no folded top label')
        label.data.materials.append(texture(args.top, args.title + ' top artwork'))
    uv = label.data.uv_layers[0]
    fold = label.get('artworkFoldV', 60 / 67)
    for polygon in label.data.polygons:
        is_top = args.top and sum(uv.data[i].uv.y for i in polygon.loop_indices) / len(polygon.loop_indices) > fold + 1e-5
        if is_top:
            polygon.material_index = 1
        rectangle = args.top_rect if is_top else args.front_rect
        quadrilateral = args.top_quad if is_top else args.front_quad
        for i in polygon.loop_indices:
            u, v = uv.data[i].uv
            if args.top:
                v = (v-fold)/(1-fold) if is_top else v/fold
            uv.data[i].uv = photo_uv(u, v, rectangle, quadrilateral)
    if args.rear:
        rear = bpy.data.objects.get('RearLabel')
        if rear is None:
            raise ValueError('This model has no rear label')
        rear.data.materials.clear()
        rear.data.materials.append(texture(args.rear, args.title + ' rear artwork'))
        for entry in rear.data.uv_layers[0].data:
            u, v = entry.uv
            entry.uv = photo_uv(u, v, args.rear_rect, args.rear_quad)
    root['exampleTitle'] = args.title
    root['artworkScope'] = 'Third-party artwork and source photographs excluded from model license'
    if root.get('physicalVariant', '').endswith('; neutral artwork'):
        root['physicalVariant'] = root['physicalVariant'].removesuffix('neutral artwork') + args.title + ' reproduction'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    stem = args.model
    api.export(root, output / (stem + '.glb'))
    api.studio(root, neutral_print=True)
    sanitize_source_paths()
    bpy.ops.wm.save_as_mainfile(filepath=str(output / (stem + '.blend')))
    inputs = [args.front] + ([args.top] if args.top else []) + ([args.rear] if args.rear else [])
    (output / 'artwork-provenance.json').write_text(json.dumps({
        'title': args.title, 'model': args.model, 'publicationRights': 'not-established',
        'inputs': [{'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size} for p in inputs],
        'frontRect': args.front_rect, 'topRect': args.top_rect if args.top else None,
        'rearRect': args.rear_rect if args.rear else None,
        'frontQuad': args.front_quad, 'topQuad': args.top_quad if args.top else None,
        'rearQuad': args.rear_quad if args.rear else None,
        'method': 'UV mapping only; original image bytes unmodified',
        'printMaterial': {'colorSpace': 'sRGB', 'roughness': .68, 'specularIORLevel': .18, 'metallic': 0},
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
