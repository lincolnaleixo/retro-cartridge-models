#!/usr/bin/env python3
"""Validate articulated packaging GLBs, optionally with a real Godot audit.

Examples:
  python3 tools/inspect_game_box.py dist/game-boxes-*/templates/*/*.glb
  python3 tools/inspect_game_box.py dist/game-boxes-*/templates/*/*.glb \
      --godot godot --godot-output dist/game-boxes-godot-audit
  python3 tools/inspect_game_box.py dist/game-boxes-*/reproductions/*/*.glb \
      --template-root dist/game-boxes-20261016/templates

The optional engine check first completes asset import, then instantiates each
model, evaluates Open at 0 and 2 seconds, and compares world vertex bounds with
the adjacent construction.json. The generated audit project and script are
kept for reruns. A successful report is written only after every check passes.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys

from inspect_glb import (Accessors, ValidationError, finite, inspect as inspect_geometry,
                         read_glb, reference, require)


def quaternion(value, context):
    require(isinstance(value, (list, tuple)) and len(value) == 4,
            context + ': expected XYZW quaternion')
    finite(value, context)
    require(abs(sum(v * v for v in value) - 1) <= 1e-5,
            context + ': quaternion must be normalized')
    return value


def same_rotation(a, b):
    # q and -q encode the same rotation.
    return min(max(abs(x - y) for x, y in zip(a, b)),
               max(abs(x + y) for x, y in zip(a, b))) <= 1e-5


def float32_steps(a, b):
    """Count representable float32 steps without a magnitude-dependent epsilon."""
    def ordered(value):
        bits = struct.unpack('<I', struct.pack('<f', value))[0]
        return ~bits & 0xffffffff if bits & 0x80000000 else bits | 0x80000000
    return abs(ordered(a) - ordered(b))


def multiply(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


IDENTITY = [[int(i == j) for j in range(4)] for i in range(4)]


def transform(node, rotation=None):
    if 'matrix' in node:
        require(rotation is None, 'animated node cannot use a matrix')
        return [[node['matrix'][j * 4 + i] for j in range(4)] for i in range(4)]
    x, y, z, w = rotation or node.get('rotation', [0, 0, 0, 1])
    scale = node.get('scale', [1, 1, 1])
    translation = node.get('translation', [0, 0, 0])
    rotation_matrix = [
        [1 - 2 * (y*y + z*z), 2 * (x*y - z*w), 2 * (x*z + y*w)],
        [2 * (x*y + z*w), 1 - 2 * (x*x + z*z), 2 * (y*z - x*w)],
        [2 * (x*z - y*w), 2 * (y*z + x*w), 1 - 2 * (x*x + y*y)],
    ]
    return [[rotation_matrix[i][j] * scale[j] for j in range(3)] + [translation[i]]
            for i in range(3)] + [[0, 0, 0, 1]]


def hierarchy(document):
    nodes = document.get('nodes', [])
    scene = reference(document.get('scenes', []), document.get('scene', 0), 'default scene')
    roots = scene.get('nodes', [])
    require(roots, 'default scene has no roots')
    seen, active = set(), set()

    def visit(index):
        reference(nodes, index, 'scene node')
        require(index not in active, 'node hierarchy contains a cycle')
        require(index not in seen, 'node has multiple parents or appears twice in the scene')
        seen.add(index)
        active.add(index)
        for child in nodes[index].get('children', []):
            visit(child)
        active.remove(index)

    for root in roots:
        visit(root)
    require(len(seen) == len(nodes), 'nodes are unreachable from the default scene')
    return roots


def world_bounds(document, reader, roots, overrides=None):
    low, high = [math.inf] * 3, [-math.inf] * 3
    overrides = overrides or {}

    def visit(index, parent):
        node = document['nodes'][index]
        matrix = multiply(parent, transform(node, overrides.get(index)))
        if 'mesh' in node:
            for primitive in document['meshes'][node['mesh']]['primitives']:
                positions = reader.read(primitive['attributes']['POSITION'])
                indices = [row[0] for row in reader.read(primitive['indices'])] if 'indices' in primitive else range(len(positions))
                for vertex in set(indices):
                    point = (*positions[vertex], 1)
                    for axis in range(3):
                        value = sum(matrix[axis][j] * point[j] for j in range(4))
                        low[axis] = min(low[axis], value)
                        high[axis] = max(high[axis], value)
        for child in node.get('children', []):
            visit(child, matrix)

    for root in roots:
        visit(root, IDENTITY)
    return {'min': low, 'max': high, 'dimensions': [hi - lo for lo, hi in zip(low, high)]}


def validate_images(document, binary, reader):
    for index, image in enumerate(document.get('images', [])):
        view = reader.views[image['bufferView']]
        start = view.get('byteOffset', 0)
        payload = binary[start:start + view['byteLength']]
        mime = image['mimeType']
        valid = False
        if mime == 'image/png':
            valid = (len(payload) >= 33 and payload[:8] == b'\x89PNG\r\n\x1a\n'
                     and payload[12:16] == b'IHDR'
                     and all(v > 0 for v in struct.unpack('>II', payload[16:24])))
        elif mime == 'image/jpeg':
            valid = len(payload) >= 4 and payload[:2] == b'\xff\xd8' and payload[-2:] == b'\xff\xd9'
        elif mime == 'image/webp':
            valid = len(payload) >= 16 and payload[:4] == b'RIFF' and payload[8:12] == b'WEBP'
        elif mime == 'image/ktx2':
            valid = len(payload) >= 80 and payload[:12] == b'\xabKTX 20\xbb\r\n\x1a\n'
        require(valid, f'image {index}: embedded bytes do not match {mime}')
    for index, texture in enumerate(document.get('textures', [])):
        source = texture.get('source')
        if source is None:
            for name in ('KHR_texture_basisu', 'EXT_texture_webp'):
                source = texture.get('extensions', {}).get(name, {}).get('source', source)
        reference(document.get('images', []), source, f'texture {index}.source')
        if 'sampler' in texture:
            reference(document.get('samplers', []), texture['sampler'], f'texture {index}.sampler')

    def textures(value):
        if not isinstance(value, dict):
            return
        for key, child in value.items():
            if key.endswith('Texture') and isinstance(child, dict) and 'index' in child:
                reference(document.get('textures', []), child['index'], key + '.index')
            textures(child)
    for material in document.get('materials', []):
        textures(material)


def inspect(path):
    base = inspect_geometry(path, required_labels={})
    base['sha256'] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    document, binary, _ = read_glb(path)
    reader = Accessors(document, binary)
    roots = hierarchy(document)
    validate_images(document, binary, reader)
    nodes = document['nodes']
    slots, hinges, parts = {}, {}, []
    names = [node.get('name', '') for node in nodes]
    for index, node in enumerate(nodes):
        if 'rotation' in node:
            quaternion(node['rotation'], f'node {index}.rotation')
        extra = node.get('extras', {})
        slot = extra.get('artworkSlot')
        part = extra.get('boxPart') or extra.get('packagingPart')
        if slot or extra.get('boxHinge') or part:
            require(node.get('name') and names.count(node['name']) == 1,
                    f'node {index}: packaging part needs a unique name')
        if part:
            parts.append(node['name'])
        if slot:
            require(isinstance(slot, str), f'node {index}: artworkSlot must be a string')
            mesh = reference(document['meshes'], node.get('mesh'), node['name'] + '.mesh')
            slots[node['name']] = slot
            for primitive in mesh['primitives']:
                attributes = primitive['attributes']
                require('TEXCOORD_0' in attributes, node['name'] + ': artwork missing TEXCOORD_0')
                uv_index = attributes['TEXCOORD_0']
                require(reader.items[uv_index]['type'] == 'VEC2', node['name'] + ': artwork UV must be VEC2')
                require(all(-1e-6 <= v <= 1 + 1e-6 for row in reader.read(uv_index) for v in row),
                        node['name'] + ': artwork UV lies outside normalized 0..1 space')
                # glTF image V points downward. A printed triangle must therefore
                # have clockwise image UVs on its outward-facing mesh winding.
                # Range/parity checks alone miss a mirrored neutral template.
                uvs = reader.read(uv_index)
                indices = ([row[0] for row in reader.read(primitive['indices'])]
                           if 'indices' in primitive else list(range(len(uvs))))
                require(primitive.get('mode', 4) == 4, node['name'] + ': artwork must use triangles')
                for offset in range(0, len(indices), 3):
                    a, b, c = [uvs[index] for index in indices[offset:offset + 3]]
                    signed_area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                    require(signed_area <= 1e-12, node['name'] + ': mirrored artwork UV orientation')
                require('material' in primitive, node['name'] + ': artwork has no material')
        if extra.get('boxHinge'):
            require(extra.get('hingeAxis') in ('X', 'Y', 'Z'), node['name'] + ': invalid hinge axis')
            finite([extra.get('closedAngleDegrees'), extra.get('openAngleDegrees')], node['name'] + ': hinge angles')
            closed = quaternion(extra.get('closedQuaternion'), node['name'] + ': closed endpoint')
            opened = quaternion(extra.get('openQuaternion'), node['name'] + ': open endpoint')
            require('matrix' not in node, node['name'] + ': animated hinge cannot use matrix transform')
            require(same_rotation(node.get('rotation', [0, 0, 0, 1]), closed),
                    node['name'] + ': default node transform is not closed')
            hinges[index] = {'name': node['name'], 'closed': closed, 'open': opened}
    require('Front' in slots.values(), 'missing Front artwork slot')
    require({'Back', 'WrapBack'} & set(slots.values()), 'missing Back or WrapBack artwork slot')
    require(hinges, 'no articulated box hinges')
    animations = document.get('animations', [])
    require(len(animations) == 1 and animations[0].get('name') == 'Open',
            'expected one named Open animation')
    animation = animations[0]
    require(len(animation.get('channels', [])) == len(hinges),
            'Open must animate every hinge exactly once')
    require(len(animation.get('samplers', [])) == len(hinges),
            'Open must have one sampler per hinge')
    animated, samplers = set(), set()
    for channel in animation['channels']:
        target = channel.get('target', {})
        index = target.get('node')
        require(index in hinges and index not in animated and target.get('path') == 'rotation',
                'Open channel must target a unique hinge rotation')
        animated.add(index)
        sample_index = channel.get('sampler')
        sampler = reference(animation['samplers'], sample_index, 'animation sampler')
        require(sample_index not in samplers, 'Open samplers must not be shared between hinges')
        samplers.add(sample_index)
        require(sampler.get('interpolation', 'LINEAR') == 'LINEAR', 'Open requires LINEAR quaternion interpolation')
        times = reader.read(sampler['input'])
        rotations = reader.read(sampler['output'])
        time_accessor, rotation_accessor = reader.items[sampler['input']], reader.items[sampler['output']]
        require(time_accessor['type'] == 'SCALAR' and time_accessor['componentType'] == 5126,
                'Open time input must be floating-point SCALAR')
        require(rotation_accessor['type'] == 'VEC4' and rotation_accessor['componentType'] == 5126,
                'Open rotation output must be floating-point VEC4')
        require(len(times) == len(rotations) and len(times) >= 2, 'Open input/output key counts differ')
        require(abs(times[0][0]) <= 1e-7 and abs(times[-1][0] - 2) <= 1e-6,
                'Open must run from 0 to 2 seconds')
        require(all(a[0] < b[0] for a, b in zip(times, times[1:])), 'Open times must increase strictly')
        for rotation in rotations:
            quaternion(rotation, hinges[index]['name'] + ': animation key')
        require(same_rotation(rotations[0], hinges[index]['closed'])
                and same_rotation(rotations[-1], hinges[index]['open']),
                hinges[index]['name'] + ': animation endpoints differ from hinge extras')
    base.pop('labels')
    base.update(contract='articulated-game-box', artworkSlots=slots, namedParts=parts,
                hinges=[h['name'] for h in hinges.values()],
                animation={'name': 'Open', 'durationSeconds': 2.0, 'channels': len(hinges)},
                worldVertexBounds={'closed': world_bounds(document, reader, roots),
                                   'open': world_bounds(document, reader, roots,
                                                        {i: h['open'] for i, h in hinges.items()})})
    return base


def compare_geometry(template, reproduction, allowed_uv_mirrors=()):
    """Prove artwork application preserved the template's complete geometry.

    Compare decoded accessor values, not buffer offsets: embedded images and
    material records can move the buffers without changing a single vertex.
    Node and material array order can also change during export, so match the
    articulated scene by stable node names rather than transient numeric IDs.
    """
    before, old_binary, _ = read_glb(template)
    after, new_binary, _ = read_glb(reproduction)
    old_reader, new_reader = Accessors(before, old_binary), Accessors(after, new_binary)
    old_nodes = {node.get('name'): node for node in before.get('nodes', [])}
    new_nodes = {node.get('name'): node for node in after.get('nodes', [])}
    require(len(old_nodes) == len(before['nodes']) and len(new_nodes) == len(after['nodes']),
            'geometry parity requires unique node names')
    # An exporter may preserve a singleton mesh's source name instead of the
    # old parent/material group name. Permit only unambiguous static meshes;
    # addressable print, hinge and removable-part names remain immutable.
    def static_signature(document, node):
        extra = node.get('extras', {})
        if 'mesh' not in node or any(extra.get(key) for key in ('artworkSlot', 'boxHinge', 'boxPart', 'packagingPart')):
            return None
        parents = [parent.get('name') for parent in document['nodes']
                   if any(document['nodes'][i] is node for i in parent.get('children', []))]
        materials = tuple(document['materials'][p['material']].get('name')
                          for p in document['meshes'][node['mesh']]['primitives'])
        return tuple(parents), materials

    aliases = {}
    for old_name in old_nodes.keys() - new_nodes.keys():
        signature = static_signature(before, old_nodes[old_name])
        candidates = [name for name in new_nodes.keys() - old_nodes.keys()
                      if name not in aliases and signature is not None
                      and static_signature(after, new_nodes[name]) == signature]
        require(len(candidates) == 1, 'geometry parity: named scene parts changed')
        aliases[candidates[0]] = old_name
    new_nodes = {aliases.get(name, name): node for name, node in new_nodes.items()}
    require(old_nodes.keys() == new_nodes.keys(), 'geometry parity: named scene parts changed')
    count = {'meshNodes': 0, 'primitives': 0, 'comparedAttributeValues': 0, 'comparedIndices': 0}
    uv_rounding = []
    uv_mirrors = []
    metadata = ('artworkSlot', 'artworkAspectRatio', 'artworkWidthMm', 'artworkHeightMm',
                'boxHinge', 'hingeAxis', 'closedAngleDegrees', 'openAngleDegrees',
                'closedQuaternion', 'openQuaternion', 'animationPhase')
    for name, old in old_nodes.items():
        new = new_nodes[name]
        require(transform(old) == transform(new), f'geometry parity: {name} default transform changed')
        old_children = sorted(before['nodes'][index]['name'] for index in old.get('children', []))
        new_children = sorted(aliases.get(after['nodes'][index]['name'], after['nodes'][index]['name'])
                              for index in new.get('children', []))
        require(old_children == new_children, f'geometry parity: {name} hierarchy changed')
        for key in metadata:
            require(old.get('extras', {}).get(key) == new.get('extras', {}).get(key),
                    f'geometry parity: {name} {key} changed')
        require(('mesh' in old) == ('mesh' in new), f'geometry parity: {name} mesh attachment changed')
        if 'mesh' not in old:
            continue
        count['meshNodes'] += 1
        old_mesh, new_mesh = before['meshes'][old['mesh']], after['meshes'][new['mesh']]
        require(len(old_mesh['primitives']) == len(new_mesh['primitives']),
                f'geometry parity: {name} primitive count changed')
        for i, (old_primitive, new_primitive) in enumerate(zip(old_mesh['primitives'], new_mesh['primitives'])):
            context = f'geometry parity: {name} primitive {i}'
            count['primitives'] += 1
            require(old_primitive.get('mode', 4) == new_primitive.get('mode', 4), context + ' mode changed')
            old_attributes, new_attributes = old_primitive['attributes'], new_primitive['attributes']
            require(old_attributes.keys() == new_attributes.keys(), context + ' attribute semantics changed')
            for semantic, accessor in old_attributes.items():
                old_values = old_reader.read(accessor)
                new_values = new_reader.read(new_attributes[semantic])
                if old_values != new_values:
                    if name in allowed_uv_mirrors and semantic == 'TEXCOORD_0':
                        require(old.get('extras', {}).get('artworkSlot')
                                and len(old_values) == len(new_values)
                                and all(len(a) == len(b) == 2 and b == (1.0 - a[0], a[1])
                                        for a, b in zip(old_values, new_values)),
                                context + ' targeted U reflection differs from the declared migration')
                        uv_mirrors.append({'node': name, 'attribute': semantic,
                                           'operation': 'U = 1 - U; V unchanged',
                                           'changedScalars': sum(a[0] != b[0] for a, b in zip(old_values, new_values))})
                        count['comparedAttributeValues'] += sum(len(row) for row in old_values)
                        continue
                    # Blender can round an unprinted surface UV by two float32
                    # steps while rebuilding a material graph. Artwork UVs and
                    # every geometric attribute still require exact equality.
                    require(semantic.startswith('TEXCOORD_') and not old.get('extras', {}).get('artworkSlot')
                            and len(old_values) == len(new_values)
                            and all(len(a) == len(b) for a, b in zip(old_values, new_values)),
                            context + ' ' + semantic + ' values changed')
                    deltas = [abs(a - b) for old_row, new_row in zip(old_values, new_values)
                              for a, b in zip(old_row, new_row) if a != b]
                    steps = [float32_steps(a, b) for old_row, new_row in zip(old_values, new_values)
                             for a, b in zip(old_row, new_row) if a != b]
                    require(old_reader.items[accessor]['componentType'] == 5126
                            and new_reader.items[new_attributes[semantic]]['componentType'] == 5126
                            and max(steps) <= 2, context + ' ' + semantic + ' values changed')
                    uv_rounding.append({'node': name, 'attribute': semantic,
                                        'changedScalars': len(deltas), 'maximumDelta': max(deltas),
                                        'maximumFloat32Steps': max(steps)})
                count['comparedAttributeValues'] += sum(len(row) for row in old_values)
            require(('indices' in old_primitive) == ('indices' in new_primitive), context + ' indexing changed')
            if 'indices' in old_primitive:
                old_values = old_reader.read(old_primitive['indices'])
                require(old_values == new_reader.read(new_primitive['indices']), context + ' triangle indices changed')
                count['comparedIndices'] += len(old_values)

    def curves(document, reader):
        result = []
        for animation in document.get('animations', []):
            for channel in animation['channels']:
                target = channel['target']
                sampler = animation['samplers'][channel['sampler']]
                result.append((animation['name'], document['nodes'][target['node']]['name'],
                               target['path'], sampler.get('interpolation', 'LINEAR'),
                               reader.read(sampler['input']), reader.read(sampler['output'])))
        return sorted(result)

    require(curves(before, old_reader) == curves(after, new_reader),
            'geometry parity: opening animation key data changed')
    require(set(allowed_uv_mirrors) == {item['node'] for item in uv_mirrors},
            'geometry parity: declared UV migration was not applied exactly once')
    return {'status': 'passed', 'templateFile': Path(template).name,
            'templateSha256': hashlib.sha256(Path(template).read_bytes()).hexdigest(),
            'reproductionFile': Path(reproduction).name,
            'reproductionSha256': hashlib.sha256(Path(reproduction).read_bytes()).hexdigest(),
            **count, 'hierarchyTransformsHingesIdentical': True,
            'positionsNormalsIndicesIdentical': True, 'artworkUvsIdentical': not uv_mirrors,
            'positionsNormalsUvsIndicesIdentical': not uv_rounding and not uv_mirrors, 'animationKeysIdentical': True,
            'namedSemanticPartsIdentical': True, 'staticMeshNameAliases': aliases,
            'nonArtworkUvFloat32Rounding': uv_rounding,
            'nonArtworkUvTolerance': 'two representable float32 steps',
            'declaredArtworkUvMirrors': uv_mirrors}


GODOT_AUDIT = r'''extends SceneTree

var failures: Array[String] = []

func check(value: bool, message: String) -> bool:
    if not value:
        failures.append(message)
        push_error(message)
    return value

func all_nodes(node: Node, result: Array) -> void:
    result.append(node)
    for child in node.get_children():
        all_nodes(child, result)

func bounds_and_surfaces(node: Node, named_slots: Dictionary, state: Dictionary, parent := Transform3D.IDENTITY) -> void:
    var world := parent
    if node is Node3D:
        world = parent * node.transform
    if node is MeshInstance3D and node.mesh != null:
        for surface in node.mesh.get_surface_count():
            var arrays = node.mesh.surface_get_arrays(surface)
            var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
            var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
            check(points.size() > 0, str(node.name) + ": no imported vertices")
            var selected = indices if not indices.is_empty() else range(points.size())
            for i in selected:
                var p: Vector3 = world * points[i]
                check(p.is_finite(), str(node.name) + ": non-finite imported position")
                for axis in 3:
                    state.low[axis] = min(state.low[axis], p[axis])
                    state.high[axis] = max(state.high[axis], p[axis])
            if named_slots.has(str(node.name)):
                var uv: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
                check(uv.size() == points.size(), str(node.name) + ": imported artwork UVs missing")
                for value in uv:
                    # Godot's compressed mesh UV decoding can move an exact
                    # boundary by one 16-bit step. The source GLB remains
                    # checked at 1e-6; allow two steps only after import.
                    var error: float = max(0.0, -value.x, -value.y, value.x - 1.0, value.y - 1.0)
                    state.uv_error = max(state.uv_error, error)
                    check(value.is_finite() and error <= 2.0 / 65535.0, str(node.name) + ": imported artwork UV out of range")
            var material = node.get_active_material(surface)
            check(material != null, str(node.name) + ": imported surface material missing")
            if material is StandardMaterial3D:
                for texture in [material.albedo_texture, material.normal_texture, material.roughness_texture]:
                    if texture == null:
                        continue
                    var image = texture.get_image()
                    check(image != null and not image.is_empty(), str(node.name) + ": embedded texture did not decode")
                    var path: String = texture.resource_path
                    check(path.is_empty() or path.begins_with("res://models/") or path.begins_with("res://.godot/"), str(node.name) + ": external texture resource " + path)
            state.surfaces += 1
    for child in node.get_children():
        bounds_and_surfaces(child, named_slots, state, world)

func _initialize() -> void:
    call_deferred("run_audit")

func run_audit() -> void:
    var manifest = JSON.parse_string(FileAccess.get_file_as_string("res://audit-input.json"))
    var report := {"status": "passed", "engine": Engine.get_version_info().string,
        "boundsToleranceMeters": manifest.toleranceMeters,
        "sourceUvTolerance": 0.000001, "importedUvTolerance": 2.0 / 65535.0,
        "assets": []}
    for item in manifest.assets:
        var packed = load(item.path)
        if not check(packed is PackedScene, str(item.id) + ": GLB did not import as PackedScene"):
            continue
        var scene: Node = packed.instantiate()
        root.add_child(scene)
        var nodes: Array = []
        all_nodes(scene, nodes)
        var names: Dictionary = {}
        var players: Array = []
        for node in nodes:
            names[str(node.name)] = node
            if node is AnimationPlayer:
                for animation in node.get_animation_list():
                    if str(animation) == "Open" or str(animation).ends_with("/Open"):
                        players.append([node, animation])
        for required in item.namedNodes:
            check(names.has(required), str(item.id) + ": missing named imported part " + required)
        if not check(players.size() == 1, str(item.id) + ": expected exactly one imported Open clip"):
            scene.free()
            continue
        var player: AnimationPlayer = players[0][0]
        var clip_name = players[0][1]
        var clip: Animation = player.get_animation(clip_name)
        check(abs(clip.length - 2.0) < 0.000001, str(item.id) + ": wrong imported clip duration")
        player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
        player.play(clip_name)
        var snapshots: Dictionary = {}
        for pose in ["closed", "open"]:
            player.seek(0.0 if pose == "closed" else 2.0, true)
            player.advance(0.0)
            var state := {"low": [INF, INF, INF], "high": [-INF, -INF, -INF], "surfaces": 0, "uv_error": 0.0}
            bounds_and_surfaces(scene, item.artworkSlots, state)
            var expected: Dictionary = item[pose + "Bounds"]
            var maximum_error: float = 0.0
            for axis in 3:
                maximum_error = max(maximum_error, abs(state.low[axis] - expected.min[axis]), abs(state.high[axis] - expected.max[axis]))
            check(maximum_error <= manifest.toleranceMeters, str(item.id) + ": " + pose + " bounds differ by " + str(maximum_error) + " meters")
            snapshots[pose] = {"min": state.low, "max": state.high, "surfaces": state.surfaces, "maximumBoundsErrorMeters": maximum_error, "maximumUvQuantizationRangeError": state.uv_error}
        report.assets.append({"id": item.id, "sha256": item.sha256, "clip": str(clip_name), "durationSeconds": clip.length, "artworkSlots": item.artworkSlots, "namedPartsPresent": true, "poses": snapshots})
        scene.free()
    if not failures.is_empty():
        print("GAME_BOX_GODOT_FAILED ", JSON.stringify(failures))
        quit(1)
        return
    var file = FileAccess.open("res://godot-report.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(report, "  ") + "\n")
    print("GAME_BOX_GODOT_PASSED ", JSON.stringify(report))
    quit(0)
'''


def audit_godot(paths, reports, executable, output, tolerance=.0002):
    """Create a disposable project, finish import, and only then run its audit."""
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / 'models').mkdir(exist_ok=True)
    report_path = output / 'godot-report.json'
    if report_path.exists():
        report_path.unlink()
    manifest = {'toleranceMeters': tolerance, 'assets': []}
    ids = set()
    for path, report in zip(paths, reports):
        path = Path(path)
        require(path.stem not in ids, 'Godot audit needs unique model basenames')
        ids.add(path.stem)
        construction_path = path.with_name('construction.json')
        require(construction_path.is_file(), path.name + ': adjacent construction.json is required for Godot bounds audit')
        construction = json.loads(construction_path.read_text())
        require(construction['artworkSlots'] == report['artworkSlots'], path.name + ': construction slot names differ')
        shutil.copy2(path, output / 'models' / path.name)
        manifest['assets'].append({'id': path.stem, 'path': 'res://models/' + path.name,
                                   'sha256': report['sha256'],
                                   'artworkSlots': report['artworkSlots'],
                                   'namedNodes': list(report['artworkSlots']) + report['hinges'] + report['namedParts'],
                                   'closedBounds': construction['closedBounds'], 'openBounds': construction['openBounds']})
    (output / 'audit-input.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'audit.gd').write_text(GODOT_AUDIT)
    (output / 'project.godot').write_text('config_version=5\n\n[application]\nconfig/name="Game box import audit"\n\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    for name, arguments in [('import', ['--editor', '--import']), ('animation', ['--script', 'res://audit.gd'])]:
        command = [executable, '--headless', '--path', str(output), *arguments]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=180, check=False)
        (output / (name + '.log')).write_text(result.stdout)
        require(result.returncode == 0, 'Godot ' + name + ' failed; see ' + name + '.log')
    require(report_path.is_file(), 'Godot did not write a successful report; see animation.log')
    result = json.loads(report_path.read_text())
    require(result.get('status') == 'passed' and len(result['assets']) == len(paths), 'Godot audit report is incomplete')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, help='write the successful structural report')
    parser.add_argument('--template-root', type=Path,
                        help='also prove reproduction geometry matches the corresponding neutral template')
    parser.add_argument('--godot', help='Godot 4 executable; enables real import and animation checks')
    parser.add_argument('--godot-output', type=Path, default=Path('dist/game-boxes-godot-audit'))
    parser.add_argument('--bounds-tolerance-mm', type=float, default=.2,
                        help='source object-AABB versus engine vertex-AABB tolerance (default 0.2 mm)')
    args = parser.parse_args(argv)
    if args.output and args.output.exists():
        args.output.unlink()
    try:
        require(math.isfinite(args.bounds_tolerance_mm) and args.bounds_tolerance_mm > 0,
                'bounds tolerance must be positive and finite')
        reports = [inspect(path) for path in args.files]
        if args.template_root:
            for path, report in zip(args.files, reports):
                construction = json.loads(path.with_name('construction.json').read_text())
                template_id = construction['console'] + '-box'
                require(template_id in ('nes-box', 'snes-box', 'nintendo-64-box', 'mega-drive-box', 'playstation-1-box'),
                        path.name + ': unknown packaging console')
                template = args.template_root / template_id / (template_id + '.glb')
                report['geometryParity'] = compare_geometry(template, path)
        result = {'status': 'passed', 'assets': reports}
        if args.godot:
            result['godot'] = audit_godot(args.files, reports, args.godot, args.godot_output,
                                          args.bounds_tolerance_mm * .001)
    except (ValidationError, OSError, KeyError, TypeError, ValueError, struct.error, subprocess.TimeoutExpired) as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}, indent=2))
        return 1
    output = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    print(output, end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
