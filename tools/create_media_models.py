#!/usr/bin/env python3
"""Create original, neutral-label Mega Drive and PlayStation game media.

Run with Blender, not system Python:
  blender -b --python tools/create_media_models.py -- --output dist/development

The default output directory is ignored by Git. No release metadata is created.
Coordinates are authored directly in meters, X right, Y up, +Z front. Each root
has its bottom at Y=0. Nominal measurements are visualization approximations.
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy
from mathutils import Matrix, Vector

MM = 0.001
ROOT = None


def mm(values):
    return tuple(value * MM for value in values)


def material(name, color, roughness=0.35, metallic=0.0, transmission=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Transmission Weight'].default_value = transmission
    shader.inputs['IOR'].default_value = 1.49
    shader.inputs['Alpha'].default_value = alpha
    if alpha < 1.0:
        mat.surface_render_method = 'BLENDED'
    return mat


def finish(obj, mat, parent=None, bevel=0):
    obj.parent = parent or ROOT
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new('Molded edge radii', 'BEVEL')
        modifier.width = bevel * MM
        modifier.segments = 3
        modifier.affect = 'EDGES'
        modifier = obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
        modifier.keep_sharp = True
    return obj


def box(name, center, size, mat, bevel=0.2, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=mm(center))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = mm(size)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, mat, parent, bevel)


def mesh(name, verts, faces, mat, bevel=0, parent=None):
    data = bpy.data.meshes.new(name + 'Geometry')
    data.from_pydata([mm(v) for v in verts], [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return finish(obj, mat, parent, bevel)


def profile(name, points, front, back, mat, bevel=0.3):
    count = len(points)
    verts = [(x, y, z) for z in (back, front) for x, y in points]
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    faces.extend((i, (i + 1) % count, (i + 1) % count + count, i + count)
                 for i in range(count))
    return mesh(name, verts, faces, mat, bevel)


def rounded_points(width, height, radius, x=0, y=0, steps=8):
    points = []
    for cx, cy, start in ((width / 2 - radius, -height / 2 + radius, -90),
                          (width / 2 - radius, height / 2 - radius, 0),
                          (-width / 2 + radius, height / 2 - radius, 90),
                          (-width / 2 + radius, -height / 2 + radius, 180)):
        for step in range(steps + 1):
            angle = math.radians(start + step * 90 / steps)
            points.append((x + cx + radius * math.cos(angle),
                           y + cy + radius * math.sin(angle)))
    return points


def label(name, width, height, x, y, z, mat, radius=0.4, rear=False, parent=None):
    points = rounded_points(width, height, radius, x, y)
    verts = [(px, py, z) for px, py in points]
    face = tuple(range(len(verts)))
    obj = mesh(name, verts, [tuple(reversed(face)) if rear else face], mat, parent=parent)
    uv = obj.data.uv_layers.new(name='ArtworkUV')
    for poly in obj.data.polygons:
        for index in poly.loop_indices:
            vertex = obj.data.vertices[obj.data.loops[index].vertex_index].co
            u = (vertex.x / MM - x) / width + 0.5
            v = (vertex.y / MM - y) / height + 0.5
            uv.data[index].uv = (1 - u if rear else u, v)
    obj['artworkAspectRatio'] = width / height
    obj['artworkOrientation'] = 'upright; U increases viewer-left to viewer-right'
    return obj


def cylinder(name, center, radius, depth, mat, vertices=64, bevel=0.08):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius * MM,
                                       depth=depth * MM, location=mm(center))
    obj = bpy.context.object
    obj.name = name
    return finish(obj, mat, bevel=bevel)


def ring(name, center, outer, inner, depth, mat, segments=128):
    cx, cy, cz = center
    verts = [(cx + radius * math.cos(2 * math.pi * i / segments),
              cy + radius * math.sin(2 * math.pi * i / segments), cz + dz)
             for dz in (-depth / 2, depth / 2) for radius in (outer, inner)
             for i in range(segments)]
    faces = []
    for i in range(segments):
        nxt = (i + 1) % segments
        faces.extend(((i, nxt, nxt + 2 * segments, i + 2 * segments),
                      (i + segments, i + 3 * segments, nxt + 3 * segments, nxt + segments),
                      (i + 2 * segments, nxt + 2 * segments, nxt + 3 * segments, i + 3 * segments),
                      (i, i + segments, nxt + segments, nxt)))
    obj = mesh(name, verts, faces, mat)
    uv = obj.data.uv_layers.new(name='DiscUV')
    for polygon in obj.data.polygons:
        for index in polygon.loop_indices:
            vertex = obj.data.vertices[obj.data.loops[index].vertex_index].co
            uv.data[index].uv = ((vertex.x / MM - cx) / (outer * 2) + 0.5,
                                 (vertex.y / MM - cy) / (outer * 2) + 0.5)
    return obj


def empty(name, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = mm(location)
    obj.parent = parent
    return obj


def reset(root_name):
    global ROOT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ROOT = empty(root_name)
    ROOT['units'] = 'meters'
    ROOT['axes'] = 'X right, Y up, +Z front'
    ROOT['pivot'] = 'bottom center of nominal closed envelope'
    ROOT['status'] = 'unreleased reference-based reconstruction; see dimensional sources'
    bpy.context.scene.unit_settings.system = 'METRIC'
    return ROOT


def mega_drive():
    from media_mega_drive import build
    return build(sys.modules[__name__])


def playstation():
    from media_playstation_disc import build
    return build(sys.modules[__name__])


def bounds(root):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = [obj.matrix_world @ Vector(corner) for original in root.children_recursive
              if original.type == 'MESH' for obj in (original.evaluated_get(depsgraph),)
              for corner in obj.bound_box]
    lower = [min(point[i] for point in points) for i in range(3)]
    upper = [max(point[i] for point in points) for i in range(3)]
    return {'min': lower, 'max': upper,
            'dimensions': [upper[i] - lower[i] for i in range(3)]}


def export(root, path):
    """Merge static export geometry while retaining the complete source assembly.

    Grouping by parent preserves the live FrontLid pivot. Named labels, CD and
    hub remain addressable. Merging contacts/ribs by material cuts draw calls.
    """
    originals = [root, *root.children_recursive]
    names = {obj: obj.name for obj in originals}
    copies = {}
    staging = bpy.data.collections.new('Temporary optimized export')
    bpy.context.scene.collection.children.link(staging)
    preserve = {'FrontLabel', 'RearLabel', 'InsertInnerPaper', 'BookletPages', 'Disc', 'DiscHub',
                'DiscInnerMatrix', 'DiscClearHub', 'DiscOuterRim'}
    try:
        for original in originals:
            original.name = '__SOURCE__' + names[original]
        for original in originals:
            duplicate = original.copy()
            if original.data:
                duplicate.data = original.data.copy()
            duplicate.name = names[original]
            staging.objects.link(duplicate)
            copies[original] = duplicate
        for original, duplicate in copies.items():
            duplicate.parent = copies.get(original.parent)
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT')
        mesh_objects = [obj for obj in staging.objects if obj.type == 'MESH']
        for obj in mesh_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh_objects[0]
        bpy.ops.object.convert(target='MESH')
        groups = {}
        for obj in list(staging.objects):
            if obj.type == 'MESH' and obj.name not in preserve:
                key = (obj.parent, tuple(obj.data.materials))
                groups.setdefault(key, []).append(obj)
        for (parent, materials), objects in groups.items():
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.join()
            objects[0].name = ('Lid_' if parent.name == 'FrontLid' else 'Body_') + materials[0].name
        bpy.ops.object.select_all(action='DESELECT')
        for obj in staging.objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = copies[root]
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
            export_apply=True, export_cameras=False, export_lights=False, export_yup=False,
            export_extras=True)
    finally:
        for obj in list(staging.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(staging)
        for original, name in names.items():
            original.name = name


def export_disc(root, path):
    """Export the removable CD assembly at a bottom-center pivot."""
    components = [obj for obj in root.children_recursive if obj.get('isDiscComponent')]
    if not components:
        raise ValueError('PlayStation builder did not identify the removable disc components')
    disc_root = empty('PLAYSTATION_1_DISC')
    disc_root['units'] = 'meters'
    disc_root['axes'] = 'X right, Y up, +Z printed face'
    disc_root['nominalDimensionsMm'] = [120, 120, 1.2]
    saved = {obj: (obj.parent, obj.matrix_world.copy()) for obj in components}
    try:
        for obj in components:
            world = obj.matrix_world.copy()
            obj.parent = disc_root
            obj.matrix_world = world
        b = bounds(disc_root)
        offset = Vector(((b['min'][0] + b['max'][0]) / 2,
                         b['min'][1], (b['min'][2] + b['max'][2]) / 2))
        for obj in components:
            obj.location -= offset
        export(disc_root, path)
    finally:
        for obj, (parent, world) in saved.items():
            obj.parent = parent
            obj.matrix_world = world
        bpy.data.objects.remove(disc_root, do_unlink=True)


def studio(root, view='hero', opened=False):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new('StudioWorld')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes.get('Background').inputs[0].default_value = (0.17, 0.2, 0.24, 1)
    scene.world.node_tree.nodes.get('Background').inputs[1].default_value = 0.35
    scene.view_settings.view_transform = 'AgX'
    b = bounds(root)
    center = Vector([(a + z) / 2 for a, z in zip(b['min'], b['max'])])
    diagonal = max(b['dimensions'][0], b['dimensions'][1])
    floor_mat = material('Studio floor', (0.085, 0.1, 0.115), 0.68)
    floor = box('StudioFloor', (0, -1, 0), (1200, 1.5, 1200), floor_mat, 0)
    floor.parent = None
    positions = {'hero': (0.65, 0.34, 1.2), 'rear': (-0.65, 0.34, -1.2),
                 'top': (0.52, 1.2, 0.68), 'bottom': (0.35, -0.38, 1.15),
                 'front': (0, 0, 1), 'back': (0, 0, -1),
                 'left': (-1, 0, 0), 'right': (1, 0, 0),
                 'top-ortho': (0, 1, 0), 'bottom-ortho': (0, -1, 0)}
    direction = Vector(positions[view]).normalized()
    if direction.y < 0:
        floor.hide_render = True
    bpy.ops.object.camera_add(location=center + direction * diagonal * 2.8)
    camera = bpy.context.object
    camera.name = 'StudioCamera'
    camera_z = (camera.location - center).normalized()
    camera_up = Vector((0, 0, -1)) if abs(camera_z.y) > 0.99 else Vector((0, 1, 0))
    camera_x = camera_up.cross(camera_z).normalized()
    camera_y = camera_z.cross(camera_x).normalized()
    camera.rotation_euler = Matrix((camera_x, camera_y, camera_z)).transposed().to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = diagonal * (1.40 if opened else 1.33)
    camera.data.lens = 52
    scene.camera = camera
    for name, relative, energy, size in (
        ('KeySoftbox', (-1.2, 1.7, 1.7), 3.2, 0.36),
        ('FillSoftbox', (1.5, 0.6, 0.75), 1.8, 0.3),
        ('RimSoftbox', (-0.5, 1.4, -1.5), 2.8, 0.22)):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy = energy
        data.shape = 'DISK'
        data.size = size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = center + Vector(relative) * 0.2
        obj.rotation_euler = (center - obj.location).to_track_quat('-Z', 'Y').to_euler()


def imported_render(path, output, view='hero'):
    """Render the actual GLB, never a different in-memory source model."""
    global ROOT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    roots = [obj for obj in bpy.context.scene.objects if obj.parent is None]
    # Blender's importer converts GLB Y-up into Blender Z-up. Put the imported
    # hierarchy back in authored axes for our constant studio/camera setup.
    root = empty('ImportedPresentationRoot')
    for obj in roots:
        obj.parent = root
    root.rotation_euler.x = -math.pi / 2
    ROOT = root
    bpy.context.view_layer.update()
    studio(root, view, 'open' in path.stem)
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    return bounds(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='dist/development', type=Path)
    parser.add_argument('--only', choices=('mega-drive', 'playstation-1'))
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    for asset_id, builder in (('mega-drive', mega_drive), ('playstation-1', playstation)):
        if args.only and args.only != asset_id:
            continue
        destination = args.output.resolve() / asset_id
        destination.mkdir(parents=True, exist_ok=True)
        root = builder()
        contract = {'assetId': asset_id, 'status': 'unreleased', 'units': 'meters',
                    'axes': {'up': '+Y', 'front': '+Z', 'width': 'X'},
                    'bounds': bounds(root), 'labels': {obj.name: obj['artworkAspectRatio']
                    for obj in root.children_recursive if 'artworkAspectRatio' in obj}}
        contract['referenceBasis'] = root.get('referenceBasis', '')
        contract['nominalDimensionsMm'] = list(root.get('nominalDimensionsMm', []))
        export(root, destination / f'{asset_id}.glb')
        studio(root)
        bpy.ops.wm.save_as_mainfile(filepath=str(destination / f'{asset_id}.blend'))
        if not args.no_render:
            contract['roundTripBounds'] = imported_render(destination / f'{asset_id}.glb', destination / 'hero.png')
            for edge in ('min', 'max'):
                if any(abs(a - b) > 1e-6 for a, b in zip(
                        contract['bounds'][edge], contract['roundTripBounds'][edge])):
                    raise ValueError(f'{asset_id}: GLB round-trip changed world bounds')
            for view in ('rear', 'top', 'front', 'back', 'left', 'right', 'top-ortho', 'bottom-ortho'):
                imported_render(destination / f'{asset_id}.glb', destination / f'{view}.png', view)
        (destination / 'development.json').write_text(json.dumps(contract, indent=2) + '\n')
        print('DEVELOPMENT_OUTPUT ' + str(destination))


if __name__ == '__main__':
    main()
