#!/usr/bin/env python3
"""Build original articulated packaging templates and artwork reproductions.

Blender usage: blender -b --python tools/create_game_boxes.py -- --console nes
Each result has one packed editable source and one closed GLB with an Open clip.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from mathutils import Quaternion, Vector
import create_media_models as api
from box_animation import append_open_animation
from source_paths import sanitize_source_paths

CONSOLES = ('nes', 'snes', 'nintendo-64', 'mega-drive', 'playstation-1')


def precise_bounds(root):
    """Measure evaluated vertices so merged rotated parts do not inflate bounds."""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lower, upper = [math.inf] * 3, [-math.inf] * 3
    for source in root.children_recursive:
        if source.type != 'MESH':
            continue
        obj = source.evaluated_get(depsgraph)
        mesh = obj.to_mesh()
        try:
            for vertex in mesh.vertices:
                point = obj.matrix_world @ vertex.co
                for axis in range(3):
                    lower[axis] = min(lower[axis], point[axis])
                    upper[axis] = max(upper[axis], point[axis])
        finally:
            obj.to_mesh_clear()
    if not all(math.isfinite(value) for value in lower + upper):
        raise ValueError('Box has no finite mesh geometry')
    return {'min': lower, 'max': upper,
            'dimensions': [b - a for a, b in zip(lower, upper)]}


def build(console):
    if console in ('nes', 'snes', 'nintendo-64'):
        from boxes_nintendo import build as builder
        return builder(api, console)
    if console == 'mega-drive':
        from boxes_mega_drive import build as builder
    else:
        from boxes_playstation import build as builder
    return builder(api)


def reopen_source(path, console):
    """Refine a released editable source without reconstructing its geometry."""
    bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
    bpy.context.scene.frame_set(1)
    roots = [obj for obj in bpy.context.scene.objects
             if obj.parent is None and obj.get('nominalDimensionsMm')]
    if len(roots) != 1:
        raise ValueError('Expected exactly one packaging root in previous source')
    root = roots[0]
    keep = {root, *root.children_recursive}
    for obj in list(bpy.data.objects):
        if obj not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)
        else:
            obj.animation_data_clear()
    api.ROOT = root
    set_pose(root, False)
    if console == 'playstation-1':
        from boxes_playstation import refine_clear_materials
        refine_clear_materials()
    return root


def xyzw(quaternion):
    return [quaternion.x, quaternion.y, quaternion.z, quaternion.w]


def record_hinges(root):
    hinges = []
    for obj in root.children_recursive:
        if not obj.get('boxHinge'):
            continue
        axis = 'XYZ'.index(obj['hingeAxis'])
        closed = obj.rotation_euler.copy()
        closed[axis] = math.radians(obj['closedAngleDegrees'])
        opened = closed.copy()
        opened[axis] = math.radians(obj['openAngleDegrees'])
        obj.rotation_euler = closed
        obj['closedQuaternion'] = xyzw(closed.to_quaternion())
        obj['openQuaternion'] = xyzw(opened.to_quaternion())
        hinges.append({'name': obj.name, 'axis': obj['hingeAxis'],
                       'closedQuaternion': list(obj['closedQuaternion']),
                       'openQuaternion': list(obj['openQuaternion']),
                       'animationPhase': float(obj.get('animationPhase', 0))})
    if not hinges:
        raise ValueError('Packaging has no articulated opening')
    return hinges


def set_pose(root, opened, imported=False):
    for obj in root.children_recursive:
        if obj.get('boxHinge'):
            q = obj['openQuaternion' if opened else 'closedQuaternion']
            obj.rotation_mode = 'QUATERNION'
            rotation = Quaternion((q[3], q[0], q[1], q[2]))
            if imported:
                # The importer conjugates each local transform into Blender's
                # Z-up basis, even though the presentation root restores Y-up.
                basis = Quaternion((1, 0, 0), math.pi / 2)
                rotation = basis @ rotation @ basis.inverted()
            obj.rotation_quaternion = rotation
    bpy.context.view_layer.update()


def source_animation(root):
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 61, 30
    for obj in root.children_recursive:
        if not obj.get('boxHinge'):
            continue
        obj.rotation_mode = 'QUATERNION'
        for frame, key in [(1, 'closedQuaternion'), (61, 'openQuaternion')]:
            q = obj[key]
            obj.rotation_quaternion = (q[3], q[0], q[1], q[2])
            obj.keyframe_insert(data_path='rotation_quaternion', frame=frame)
        phase = float(obj.get('animationPhase', 0))
        if phase:
            q = obj['closedQuaternion']
            obj.rotation_quaternion = (q[3], q[0], q[1], q[2])
            obj.keyframe_insert(data_path='rotation_quaternion', frame=1 + round(60 * phase))
        obj.animation_data.action.name = 'Open · ' + obj.name
    scene.frame_set(1)


def export(root, path):
    """Merge only static meshes with identical material and articulated parent."""
    originals = [root, *root.children_recursive]
    names = {obj: obj.name for obj in originals}
    copies = {}
    stage = bpy.data.collections.new('Temporary box export')
    bpy.context.scene.collection.children.link(stage)
    try:
        for obj in originals:
            obj.name = '__SOURCE__' + names[obj]
        for obj in originals:
            duplicate = obj.copy()
            duplicate.animation_data_clear()
            if obj.data:
                duplicate.data = obj.data.copy()
            duplicate.name = names[obj]
            stage.objects.link(duplicate)
            copies[obj] = duplicate
        for original, duplicate in copies.items():
            duplicate.parent = copies.get(original.parent)
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT')
        meshes = [obj for obj in stage.objects if obj.type == 'MESH']
        for obj in meshes:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.convert(target='MESH')
        groups = {}
        for obj in stage.objects:
            if obj.type == 'MESH' and not obj.get('artworkSlot') and not obj.get('boxPart'):
                groups.setdefault((obj.parent, tuple(obj.data.materials)), []).append(obj)
        for (parent, materials), objects in groups.items():
            if len(objects) == 1:
                continue
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.join()
            objects[0].name = parent.name + ' · ' + materials[0].name
        bpy.ops.object.select_all(action='DESELECT')
        for obj in stage.objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = copies[root]
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB',
            use_selection=True, export_apply=True, export_cameras=False,
            export_lights=False, export_yup=False, export_extras=True,
            export_animations=False)
    finally:
        for obj in list(stage.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(stage)
        for obj, name in names.items():
            obj.name = name


def apply_artwork(root, mapping):
    slots = {}
    for obj in root.children_recursive:
        if obj.get('artworkSlot'):
            slots.setdefault(obj['artworkSlot'], []).append(obj)
    if set(mapping) - set(slots):
        raise ValueError('Unknown artwork slots: ' + ', '.join(set(mapping) - set(slots)))
    for slot, filename in mapping.items():
        image = bpy.data.images.load(str(Path(filename).resolve()), check_existing=True)
        image.colorspace_settings.name = 'sRGB'
        image.pack()
        for obj in slots[slot]:
            if not obj.data.uv_layers:
                raise ValueError('Artwork slot has no UVs: ' + obj.name)
            mat = obj.data.materials[0]
            shader = mat.node_tree.nodes['Principled BSDF']
            for node in list(mat.node_tree.nodes):
                if node.type == 'TEX_IMAGE':
                    mat.node_tree.nodes.remove(node)
            image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            image_node.image = image
            mat.node_tree.links.new(image_node.outputs['Color'], shader.inputs['Base Color'])
            shader.inputs['Specular IOR Level'].default_value = 0.18
            # Ink on coated carton or paper retains the pristine finish; it is
            # not metallic, emissive or faded into the underlying paper color.
            shader.inputs['Roughness'].default_value = 0.48
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)


def render(glb, destination, view='hero', opened=False, samples=24, resolution=1200):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    top = [obj for obj in bpy.context.scene.objects if obj.parent is None]
    root = api.empty('ImportedBoxPresentation')
    for obj in top:
        obj.parent = root
    root.rotation_euler.x = -math.pi / 2
    api.ROOT = root
    # Render the actual exported endpoint; do not depend on importing a source
    # animation into the current Blender action slot or frame rate.
    for obj in root.children_recursive:
        obj.animation_data_clear()
    set_pose(root, opened, imported=True)
    api.studio(root, view, opened, neutral_print=True)
    bpy.context.scene.cycles.samples = samples
    bpy.context.scene.render.resolution_x = resolution
    bpy.context.scene.render.resolution_y = round(resolution * 5 / 6)
    bpy.context.scene.render.filepath = str(destination)
    bpy.ops.render.render(write_still=True)
    return precise_bounds(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--console', choices=CONSOLES, required=True)
    parser.add_argument('--output', type=Path, default=Path('dist/game-boxes-20261016/templates'))
    parser.add_argument('--asset-id')
    parser.add_argument('--artwork', type=Path)
    parser.add_argument('--source', type=Path, help='Previous released Blender source to refine in place in memory')
    parser.add_argument('--no-render', action='store_true')
    parser.add_argument('--samples', type=int, default=24)
    parser.add_argument('--resolution', type=int, default=1200)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    asset_id = args.asset_id or args.console + '-box'
    destination = args.output.resolve() / asset_id
    destination.mkdir(parents=True, exist_ok=True)
    root = reopen_source(args.source, args.console) if args.source else build(args.console)
    if args.artwork:
        apply_artwork(root, json.loads(args.artwork.read_text()))
    if args.source:
        hinges = [{'name': obj.name, 'axis': obj['hingeAxis'],
                   'closedQuaternion': list(obj['closedQuaternion']),
                   'openQuaternion': list(obj['openQuaternion']),
                   'animationPhase': float(obj.get('animationPhase', 0))}
                  for obj in root.children_recursive if obj.get('boxHinge')]
        if not hinges:
            raise ValueError('Previous source has no articulated packaging hinges')
    else:
        hinges = record_hinges(root)
    set_pose(root, False)
    closed = precise_bounds(root)
    set_pose(root, True)
    opened = precise_bounds(root)
    set_pose(root, False)
    glb = destination / (asset_id + '.glb')
    export(root, glb)
    animation = append_open_animation(glb, hinges)
    contract = {'assetId': asset_id, 'console': args.console, 'units': 'meters',
                'axes': {'up': '+Y', 'front': '+Z', 'width': 'X'},
                'pivot': 'bottom center of closed envelope',
                'nominalDimensionsMm': list(root['nominalDimensionsMm']),
                'closedBounds': closed, 'openBounds': opened,
                'animation': animation, 'hinges': hinges,
                'artworkSlots': {obj.name: obj['artworkSlot'] for obj in root.children_recursive
                                 if obj.get('artworkSlot')},
                'referenceBasis': root.get('referenceBasis', ''),
                'geometryLimitations': root.get('geometryLimitations', '')}
    if args.source:
        contract['previousSource'] = {'filename': args.source.name,
            'sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
            'method': 'Reopened the previous released source; preserved all packaging geometry and articulation.'}
    source_animation(root)
    api.studio(root, neutral_print=True)
    sanitize_source_paths()
    bpy.ops.wm.save_as_mainfile(filepath=str(destination / (asset_id + '.blend')))
    if not args.no_render:
        for view, is_open in [('hero', False), ('front', False), ('rear', False),
                              ('top', False), ('bottom', False), ('open', True)]:
            actual = render(glb, destination / (view + '.png'),
                            'hero' if is_open else view, is_open, args.samples, args.resolution)
            expected = opened if is_open else closed
            for edge in ('min', 'max'):
                if max(abs(a - b) for a, b in zip(actual[edge], expected[edge])) > 2e-6:
                    raise ValueError('Exported pose bounds differ from source: ' + view + ' expected=' + str(expected) + ' actual=' + str(actual))
    (destination / 'construction.json').write_text(json.dumps(contract, indent=2) + '\n')
    print('BOX_OUTPUT', destination)


if __name__ == '__main__':
    main()
