"""Refine a verified SNES baseline without changing its published snapshot.

blender --factory-startup -b baseline.blend --python tools/refine_snes.py -- OUTPUT

OUTPUT receives editable source, a portable GLB and matched before/after renders.
The source uses the collection's native Y-up axes (export_yup=False).
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def frame_camera(camera, eye):
    camera.location = eye
    direction = (Vector((0, 0.044, 0)) - camera.location).normalized()
    right = direction.cross(Vector((0, 1, 0))).normalized()
    up = right.cross(direction)
    camera.rotation_mode = 'QUATERNION'
    camera.rotation_quaternion = Matrix((right, up, -direction)).transposed().to_quaternion()


def render(scene, output, name, eye):
    frame_camera(scene.camera, eye)
    scene.render.filepath = str(output / (name + '.png'))
    bpy.ops.render.render(write_still=True)


def grain_image():
    """A seeded, packed roughness map survives GLB export; no procedural dependency."""
    image = bpy.data.images.new('Neutral ABS micrograin roughness', 512, 512)
    image.colorspace_settings.name = 'Non-Color'
    rng = random.Random(20261002)
    pixels = []
    for _ in range(512 * 512):
        value = 0.57 + rng.uniform(-0.035, 0.035)
        pixels.extend((value, value, value, 1))
    image.pixels.foreach_set(pixels)
    image.pack()
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--skip-renders', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = bpy.data.objects.get('SNES_NTSC_U')
    if root is None:
        raise ValueError('Open the verified snes-ntsc-u baseline Blender source first')
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 0.185
    views = {
        'hero': (0.20, 0.14, 0.36),
        'top': (0.15, 0.29, 0.25),
        'bottom': (0.16, -0.16, 0.27),
    }
    if not args.skip_renders:
        for view, eye in views.items():
            render(scene, output, 'before-' + view, eye)
    grain = grain_image()
    for material in bpy.data.materials:
        if not material.use_nodes:
            continue
        for node in material.node_tree.nodes:
            if node.type != 'BSDF_PRINCIPLED':
                continue
            if 'shell finish' in material.name or 'molded ABS relief' in material.name:
                node.inputs['Roughness'].default_value = 0.57
                node.inputs['Specular IOR Level'].default_value = 0.27
                texture = material.node_tree.nodes.new('ShaderNodeTexImage')
                texture.name = 'Portable ABS roughness grain'
                texture.image = grain
                uv = material.node_tree.nodes.new('ShaderNodeUVMap')
                uv.uv_map = 'DetailUV'
                material.node_tree.links.new(uv.outputs['UV'], texture.inputs['Vector'])
                material.node_tree.links.new(texture.outputs['Color'], node.inputs['Roughness'])
            elif material.name == 'Unprinted charcoal label':
                node.inputs['Roughness'].default_value = 0.78
                node.inputs['Specular IOR Level'].default_value = 0.20
    for name in ('FrontShell', 'BackShell'):
        shell = bpy.data.objects[name]
        bevel = shell.modifiers.new('Molded edge bevel 0.12 mm', 'BEVEL')
        bevel.width = 0.00012
        # At this subpixel width, one chamfer segment softens the highlight
        # without doubling the already detailed shell's triangle count.
        bevel.segments = 1
        bevel.limit_method = 'ANGLE'
        bevel.angle_limit = math.radians(50)
        bevel.use_clamp_overlap = True
        bevel.harden_normals = True
    root['development_status'] = 'Unreleased material and edge refinement'
    root['baseline'] = 'snes-ntsc-u-v0.1.0'
    root['units'] = 'meters; X width, Y up, +Z front; bottom connector origin'
    # Keep the folded labels and their UV maps exactly as supplied by the source.
    for image in bpy.data.images:
        image.pack()
        image.filepath_raw = '//textures/' + image.name.replace(' ', '_') + '.png'
    frame_camera(scene.camera, views['hero'])
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'snes-ntsc-u.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for child in root.children_recursive:
        if child.type == 'MESH':
            child.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=str(output / 'snes-ntsc-u.glb'), export_format='GLB',
        use_selection=True, export_apply=True, export_cameras=False,
        export_lights=False, export_yup=False, export_extras=True,
    )
    if not args.skip_renders:
        for view, eye in views.items():
            render(scene, output, 'after-' + view, eye)
    summary = {
        'status': 'unreleased', 'baseline': 'snes-ntsc-u-v0.1.0',
        'changes': ['0.12 mm shell edge bevel', 'packed 512 px ABS roughness grain',
                    'matte paper labels; unchanged folded-label meshes and UVs'],
        'comparison': 'Identical Cycles lighting, orthographic framing and 48 samples before/after',
        'export': 'Self-contained GLB, meters, Y up, +Z front, existing bottom pivot',
        'limitations': ['Photo-derived dimensions remain approximate', 'Not a published model release'],
    }
    (output / 'development.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('SNES refinement complete:', output)


if __name__ == '__main__':
    main()
