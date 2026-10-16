"""Replace published artwork without re-exporting or rebuilding geometry.

Run with Blender: blender -b --python-exit-code 1 --python tools/update_packed_artwork.py --
  --blend old.blend --glb old.glb --mapping replacements.json --output dist/new

Mapping format: {"images": {"Exact Blender image name": "new-image.png"}}.
Image paths resolve relative to the JSON file. Original packed-byte hashes
identify the corresponding GLB image, even when its name differs in the export.

Optional uvRemaps entries require object, material, layer, fromRect, toRect and
framingEvidence. Rectangles use Blender's bottom-left UV origin. Remaps are only
for reviewed changes in image framing; ordinary replacements keep every UV byte.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def image_mime(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    raise ValueError('Replacement must contain PNG or JPEG bitmap bytes')


def read_glb(path):
    data = Path(path).read_bytes()
    if len(data) < 20 or struct.unpack_from('<4sII', data) != (b'glTF', 2, len(data)):
        raise ValueError('Invalid GLB header')
    offset, chunks = 12, []
    while offset < len(data):
        length, kind = struct.unpack_from('<II', data, offset)
        offset += 8
        if length % 4 or offset + length > len(data):
            raise ValueError('Invalid GLB chunk length')
        chunks.append((kind, data[offset:offset + length]))
        offset += length
    if [kind for kind, _ in chunks] != [0x4E4F534A, 0x004E4942]:
        raise ValueError('Expected one JSON and one embedded BIN chunk')
    document = json.loads(chunks[0][1])
    binary = chunks[1][1]
    validate_layout(document, binary)
    return document, binary


def write_glb(path, document, binary):
    metadata = json.dumps(document, separators=(',', ':'), ensure_ascii=False).encode()
    metadata += b' ' * (-len(metadata) % 4)
    binary += b'\0' * (-len(binary) % 4)
    total = 12 + 8 + len(metadata) + 8 + len(binary)
    Path(path).write_bytes(struct.pack('<4sII', b'glTF', 2, total)
                          + struct.pack('<II', len(metadata), 0x4E4F534A) + metadata
                          + struct.pack('<II', len(binary), 0x004E4942) + binary)


def validate_layout(document, binary):
    compression = {'EXT_meshopt_compression', 'KHR_draco_mesh_compression'}
    if compression & set(document.get('extensionsUsed', []) + document.get('extensionsRequired', [])):
        raise ValueError('Only uncompressed geometry buffers are supported')
    buffers = document.get('buffers', [])
    if len(buffers) != 1 or buffers[0].get('uri') or buffers[0]['byteLength'] > len(binary):
        raise ValueError('Only a single self-contained GLB buffer is supported')
    intervals = []
    for index, view in enumerate(document.get('bufferViews', [])):
        start, length = view.get('byteOffset', 0), view['byteLength']
        if view.get('buffer', 0) != 0 or start < 0 or length <= 0 or start + length > buffers[0]['byteLength']:
            raise ValueError('Invalid bufferView range')
        intervals.append((start, start + length, index))
    intervals.sort()
    if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
        raise ValueError('Overlapping bufferViews are not safe to repack')
    image_views = [image['bufferView'] for image in document.get('images', [])
                   if 'bufferView' in image and 'uri' not in image]
    if len(image_views) != len(document.get('images', [])) or len(set(image_views)) != len(image_views):
        raise ValueError('Images must have distinct embedded bufferViews')
    def references(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == 'bufferView':
                    yield child
                else:
                    yield from references(child)
        elif isinstance(value, list):
            for child in value:
                yield from references(child)
    # Includes sparse accessors and extension-owned geometry references.
    for key, value in document.items():
        if key != 'images' and set(references(value)) & set(image_views):
            raise ValueError('An image bufferView is also used by non-image data')


def view_bytes(document, binary, index):
    view = document['bufferViews'][index]
    start = view.get('byteOffset', 0)
    return binary[start:start + view['byteLength']]


def find_image_by_packed_hash(document, binary, original_bytes):
    matches = [index for index, image in enumerate(document['images'])
               if digest(view_bytes(document, binary, image['bufferView'])) == digest(original_bytes)]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one GLB image matching packed bytes; found {len(matches)}')
    return matches[0]


def validate_remaps(remaps):
    targets = set()
    for entry in remaps:
        required = ('object', 'material', 'layer', 'fromRect', 'toRect', 'framingEvidence')
        if any(key not in entry for key in required) or not str(entry['framingEvidence']).strip():
            raise ValueError('UV remaps require an explicit target and framingEvidence')
        target = (entry['object'], entry['material'], entry['layer'])
        if target in targets:
            raise ValueError('Duplicate UV remap target')
        targets.add(target)
        for key in ('fromRect', 'toRect'):
            rect = entry[key]
            if len(rect) != 4 or not all(math.isfinite(value) for value in rect) or rect[0] == rect[2] or rect[1] == rect[3]:
                raise ValueError('UV rectangles must have finite, nonzero extents')
        if entry['fromRect'] == entry['toRect']:
            raise ValueError('A framing remap must change the rectangle')


def remap_uv(uv, entry, gltf=False):
    u, v = uv
    if gltf:
        v = 1 - v
    source, target = entry['fromRect'], entry['toRect']
    u = target[0] + (u - source[0]) / (source[2] - source[0]) * (target[2] - target[0])
    v = target[1] + (v - source[1]) / (source[3] - source[1]) * (target[3] - target[1])
    return u, 1 - v if gltf else v


def accessor_values(document, views, index):
    accessor = document['accessors'][index]
    if 'sparse' in accessor or 'bufferView' not in accessor:
        raise ValueError('Sparse or implicit accessors are not supported for UV remapping')
    sizes = {5121: ('B', 1), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
    counts = {'SCALAR': 1, 'VEC2': 2}
    if accessor['componentType'] not in sizes or accessor['type'] not in counts:
        raise ValueError('Unsupported UV/index accessor format')
    code, size = sizes[accessor['componentType']]
    width = counts[accessor['type']]
    view = document['bufferViews'][accessor['bufferView']]
    stride = view.get('byteStride', size * width)
    start = accessor.get('byteOffset', 0)
    data = views[accessor['bufferView']]
    if start + (accessor['count'] - 1) * stride + size * width > len(data):
        raise ValueError('Accessor exceeds its bufferView')
    return [struct.unpack_from('<' + code * width, data, start + i * stride)
            for i in range(accessor['count'])]


def primitive_indices(document, views, primitive):
    if 'indices' in primitive:
        return {value[0] for value in accessor_values(document, views, primitive['indices'])}
    return set(range(document['accessors'][primitive['attributes']['POSITION']]['count']))


def apply_glb_remaps(document, views, remaps):
    """Update only targeted UV0 elements; preserve positions/normals/index bytes."""
    pending, selected, changed_views, changed_accessors = {}, set(), set(), set()
    for entry in remaps:
        nodes = [node for node in document['nodes'] if node.get('name') == entry['object']]
        if len(nodes) != 1 or 'mesh' not in nodes[0]:
            raise ValueError('UV remap object must identify one mesh node')
        mesh_index = nodes[0]['mesh']
        if sum(node.get('mesh') == mesh_index for node in document['nodes']) != 1:
            raise ValueError('Cannot remap an instanced mesh')
        found = False
        for primitive_index, primitive in enumerate(document['meshes'][mesh_index]['primitives']):
            if document['materials'][primitive['material']].get('name') != entry['material']:
                continue
            found = True
            selected.add((mesh_index, primitive_index))
            accessor_index = primitive['attributes']['TEXCOORD_0']
            accessor = document['accessors'][accessor_index]
            if accessor['componentType'] != 5126 or accessor['type'] != 'VEC2' or accessor.get('normalized'):
                raise ValueError('UV remapping requires float32 TEXCOORD_0')
            # Dedicated views avoid accidentally changing interleaved geometry.
            if 'byteStride' in document['bufferViews'][accessor['bufferView']] or sum(a.get('bufferView') == accessor['bufferView'] for a in document['accessors']) != 1:
                raise ValueError('UV remapping requires a dedicated accessor bufferView')
            for other in document['accessors']:
                sparse = other.get('sparse', {})
                if any(sparse.get(key, {}).get('bufferView') == accessor['bufferView'] for key in ('indices', 'values')):
                    raise ValueError('UV view is also used by a sparse accessor')
            old_values = accessor_values(document, views, accessor_index)
            for vertex in primitive_indices(document, views, primitive):
                if vertex >= len(old_values):
                    raise ValueError('Primitive index exceeds UV accessor')
                key = accessor_index, vertex
                value = remap_uv(old_values[vertex], entry, gltf=True)
                if key in pending and pending[key] != value:
                    raise ValueError('Conflicting UV remaps share a vertex')
                pending[key] = value
        if not found:
            raise ValueError('UV remap material was not found on the target mesh')
    modified_accessors = {index for index, _ in pending}
    for mi, mesh in enumerate(document.get('meshes', [])):
        for pi, primitive in enumerate(mesh['primitives']):
            if any(index in modified_accessors for semantic, index in primitive.get('attributes', {}).items() if semantic != 'TEXCOORD_0'):
                raise ValueError('UV accessor is also used by another attribute semantic')
            if primitive.get('indices') in modified_accessors or any(index in modified_accessors for target in primitive.get('targets', []) for index in target.values()):
                raise ValueError('UV accessor is also used by non-UV geometry')
            uv = primitive.get('attributes', {}).get('TEXCOORD_0')
            if (mi, pi) not in selected and uv is not None:
                if any((uv, vertex) in pending for vertex in primitive_indices(document, views, primitive)):
                    raise ValueError('UV remap would affect an unselected primitive')
    if any(sampler.get(key) in modified_accessors for animation in document.get('animations', []) for sampler in animation.get('samplers', []) for key in ('input', 'output')) or any(skin.get('inverseBindMatrices') in modified_accessors for skin in document.get('skins', [])):
        raise ValueError('UV accessor is also used by animation or skin data')
    for (accessor_index, vertex), value in pending.items():
        accessor = document['accessors'][accessor_index]
        view_index = accessor['bufferView']
        struct.pack_into('<ff', views[view_index], accessor.get('byteOffset', 0) + vertex * 8, *value)
        changed_views.add(view_index)
        changed_accessors.add(accessor_index)
    for index in changed_accessors:
        accessor = document['accessors'][index]
        values = accessor_values(document, views, index)
        for key, function in (('min', min), ('max', max)):
            if key in accessor:
                accessor[key] = [function(value[axis] for value in values) for axis in range(2)]
    return changed_views, changed_accessors


def patch_glb(document, binary, replacements, remaps=()):
    validate_layout(document, binary)
    validate_remaps(remaps)
    result = copy.deepcopy(document)
    views = [bytearray(view_bytes(document, binary, i)) for i in range(len(document['bufferViews']))]
    replacement_views = set()
    for index, data in replacements.items():
        image = result['images'][index]
        image['mimeType'] = image_mime(data)
        replacement_views.add(image['bufferView'])
        views[image['bufferView']] = bytearray(data)
    uv_views, uv_accessors = apply_glb_remaps(result, views, remaps)
    output = bytearray()
    for index, (view, data) in enumerate(zip(result['bufferViews'], views)):
        output.extend(b'\0' * (-len(output) % 4))
        view['byteOffset'] = len(output)
        view['byteLength'] = len(data)
        output.extend(data)
        if index not in replacement_views | uv_views and bytes(data) != view_bytes(document, binary, index):
            raise AssertionError('Non-artwork bufferView changed')
    result['buffers'][0]['byteLength'] = len(output)
    # All scene/mesh/material definitions stay identical, including node transforms.
    for key in set(document) | set(result):
        if key not in ('buffers', 'bufferViews', 'images', 'accessors') and document.get(key) != result.get(key):
            raise AssertionError(f'Unexpected GLB structure change: {key}')
    for index, original in enumerate(document.get('accessors', [])):
        actual = result['accessors'][index]
        if index not in uv_accessors and actual != original:
            raise AssertionError('Non-UV accessor metadata changed')
        if index in uv_accessors and {k: v for k, v in actual.items() if k not in ('min', 'max')} != {k: v for k, v in original.items() if k not in ('min', 'max')}:
            raise AssertionError('UV accessor layout changed')
    validate_layout(result, output)
    return result, bytes(output), {'meshNodeMaterialDefinitionsUnchanged': True,
                                  'nonImageNonRemappedBufferViewsByteIdentical': True,
                                  'allUvBytesUnchanged': not remaps,
                                  'remappedUvAccessors': sorted(uv_accessors),
                                  'replacedImageIndices': sorted(replacements)}


def blender_snapshot(bpy):
    """Fingerprint original source geometry and all UV layers before/after save."""
    geometry, uvs = [], {}
    bpy.context.view_layer.update()
    for obj in sorted(bpy.data.objects, key=lambda value: value.name):
        item = {'name': obj.name, 'type': obj.type,
                'parent': obj.parent.name if obj.parent else None,
                'matrixLocal': [list(row) for row in obj.matrix_local],
                'matrixWorld': [list(row) for row in obj.matrix_world]}
        if obj.type == 'MESH':
            mesh = obj.data
            item.update(vertices=[list(v.co) for v in mesh.vertices],
                        edges=[list(e.vertices) for e in mesh.edges],
                        loops=[loop.vertex_index for loop in mesh.loops],
                        polygons=[(p.loop_start, p.loop_total, p.material_index, p.use_smooth) for p in mesh.polygons],
                        cornerNormals=[list(normal.vector) for normal in mesh.corner_normals],
                        materials=[material.name if material else None for material in mesh.materials])
            uvs[obj.name] = {layer.name: [list(value.uv) for value in layer.data] for layer in mesh.uv_layers}
        geometry.append(item)
    return {'geometrySha256': json_digest(geometry), 'uvSha256': json_digest(uvs), 'uvs': uvs}


def apply_blender_remaps(bpy, remaps, replacement_names):
    for entry in remaps:
        obj = bpy.data.objects.get(entry['object'])
        if obj is None or obj.type != 'MESH' or obj.data.users != 1:
            raise ValueError('UV remap requires one unshared Blender mesh')
        layer = obj.data.uv_layers.get(entry['layer'])
        if layer is None or layer != obj.data.uv_layers[0]:
            raise ValueError('Only the named UV0 artwork layer can be remapped')
        slots = [i for i, mat in enumerate(obj.data.materials) if mat and mat.name == entry['material']]
        if len(slots) != 1:
            raise ValueError('UV remap material must identify one source slot')
        material = obj.data.materials[slots[0]]
        linked_images = {node.image.name for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image}
        if not linked_images & replacement_names:
            raise ValueError('UV remap material does not use a replaced image')
        for face in obj.data.polygons:
            if face.material_index == slots[0]:
                for index in face.loop_indices:
                    layer.data[index].uv = remap_uv(layer.data[index].uv, entry)


def update(blend, glb, mapping, output, stem=None, overwrite=False):
    import bpy
    blend, glb, mapping, output = map(lambda value: Path(value).resolve(), (blend, glb, mapping, output))
    config = json.loads(mapping.read_text())
    if not isinstance(config.get('images'), dict) or not config['images']:
        raise ValueError('Mapping must contain a nonempty images object')
    remaps = config.get('uvRemaps', [])
    validate_remaps(remaps)
    stem = stem or glb.stem
    if Path(stem).name != stem or not re.fullmatch(r'[A-Za-z0-9._-]+', stem):
        raise ValueError('Output stem must be a filename without directories')
    output.mkdir(parents=True, exist_ok=True)
    paths = {suffix: output / (stem + suffix) for suffix in ('.blend', '.glb')}
    def protect_inputs(inputs):
        for path in [*paths.values(), output / 'artwork-update-report.json']:
            for source in inputs:
                if path.resolve() == source or (path.exists() and path.samefile(source)):
                    raise ValueError('Input files must not be overwritten, including linked paths')
    protect_inputs((blend, glb, mapping))
    if not overwrite and (any(path.exists() for path in paths.values()) or (output / 'artwork-update-report.json').exists()):
        raise ValueError('Output already exists; choose a new directory or use --overwrite')
    document, binary = read_glb(glb)
    input_hashes = {'blend': digest(blend.read_bytes()), 'glb': digest(glb.read_bytes())}
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    before = blender_snapshot(bpy)
    expected_packed = {image.name: digest(bytes(image.packed_file.data))
                       for image in bpy.data.images if image.packed_file}
    replacements, image_report = {}, []
    # Validate all mappings before changing any Blender datablock.
    prepared = []
    for name, path in config['images'].items():
        image = bpy.data.images.get(name)
        if image is None or image.packed_file is None:
            raise ValueError(f'Missing packed Blender image: {name}')
        target = (mapping.parent / path).resolve()
        data = target.read_bytes()
        mime = image_mime(data)
        old = bytes(image.packed_file.data)
        index = find_image_by_packed_hash(document, binary, old)
        if index in replacements:
            raise ValueError('Multiple replacement names resolve to the same GLB image')
        replacements[index] = data
        expected_packed[name] = digest(data)
        prepared.append((image, target, data, mime))
        image_report.append({'blenderImage': name, 'glbImage': document['images'][index].get('name'),
                             'originalSha256': digest(old), 'replacementSha256': digest(data),
                             'originalDimensions': list(image.size), 'replacementFile': target.name})
    protect_inputs([target for _, target, _, _ in prepared])
    patched, patched_binary, glb_report = patch_glb(document, binary, replacements, remaps)
    for image, target, data, mime in prepared:
        color_space = image.colorspace_settings.name
        alpha_mode = image.alpha_mode
        image.unpack(method='REMOVE')
        image.filepath = str(target)
        image.reload()
        image.colorspace_settings.name = color_space
        image.alpha_mode = alpha_mode
        image.pack()
        if not image.packed_file or bytes(image.packed_file.data) != data:
            raise ValueError('Blender did not pack the original replacement bytes')
    apply_blender_remaps(bpy, remaps, set(config['images']))
    expected = blender_snapshot(bpy)
    if before['geometrySha256'] != expected['geometrySha256']:
        raise AssertionError('Source mesh geometry, normals or transforms changed')
    if not remaps and before['uvSha256'] != expected['uvSha256']:
        raise AssertionError('UVs changed without an explicit framing remap')
    # Store portable paths for every packed image; no local authoring paths.
    for image in bpy.data.images:
        if image.packed_file:
            suffix = '.jpg' if image_mime(bytes(image.packed_file.data)) == 'image/jpeg' else '.png'
            image.filepath_raw = '//textures/' + re.sub(r'[^A-Za-z0-9_-]+', '_', image.name) + suffix
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(paths['.blend']))
    write_glb(paths['.glb'], patched, patched_binary)
    bpy.ops.wm.open_mainfile(filepath=str(paths['.blend']))
    saved = blender_snapshot(bpy)
    if (saved['geometrySha256'], saved['uvSha256']) != (expected['geometrySha256'], expected['uvSha256']):
        raise AssertionError('Saved Blender source does not preserve the checked geometry/UVs')
    actual_packed = {image.name: digest(bytes(image.packed_file.data))
                     for image in bpy.data.images if image.packed_file}
    if actual_packed != expected_packed:
        raise AssertionError('Saved Blender changed an undeclared packed bitmap')
    for entry in image_report:
        image = bpy.data.images[entry['blenderImage']]
        if digest(bytes(image.packed_file.data)) != entry['replacementSha256']:
            raise AssertionError('Saved Blender packed image changed')
        entry['replacementDimensions'] = list(image.size)
    saved_document, saved_binary = read_glb(paths['.glb'])
    if saved_document != patched or saved_binary[:len(patched_binary)] != patched_binary:
        raise AssertionError('Written GLB differs from the validated patch')
    if input_hashes != {'blend': digest(blend.read_bytes()), 'glb': digest(glb.read_bytes())}:
        raise AssertionError('Published source inputs changed')
    report = {'status': 'passed', 'method': 'Packed image replacement and direct GLB bufferView patch; no geometry rebuild/export.',
              'baselineSha256': input_hashes, 'images': image_report, 'uvRemaps': remaps,
              'blender': {'geometrySha256': saved['geometrySha256'], 'baselineUvSha256': before['uvSha256'],
                          'outputUvSha256': saved['uvSha256'], 'savedAndReopened': True,
                          'allOtherPackedImagesByteIdentical': True},
              'glb': glb_report,
              'outputs': {path.name: {'bytes': path.stat().st_size, 'sha256': digest(path.read_bytes())} for path in paths.values()}}
    (output / 'artwork-update-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('blend', 'glb', 'mapping', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--stem')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    update(**vars(args))


if __name__ == '__main__':
    main()
