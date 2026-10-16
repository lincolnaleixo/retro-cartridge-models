"""Lossless glTF composition of an unchanged box and its published game media.

Only the containing scene graph changes. Embedded mesh, UV, normal, image and
animation bytes are copied verbatim, with explicit index remapping. The helper
rejects unsupported features rather than silently losing them.
"""
from copy import deepcopy
import hashlib
from pathlib import Path

from box_animation import read_glb, write_glb

ARRAYS = ('nodes', 'meshes', 'accessors', 'bufferViews', 'materials', 'textures', 'images', 'samplers')
PREFIX = 'Contents · '
NINTENDO_LIMITATIONS = ('No factory die-line measurements, pack-in leaflets, game media, shrinkwrap, or wear; '
    'NES die-cut hanger and tray folds are approximated from photographs; board gauges are inferred')
PS1_LIMITATIONS = 'Standard-compatible envelope; fine molded features and booklet leaves approximate. No disc included.'
BOX_MEDIA = {'NesBox': 'nes-super-mario-bros', 'SnesBox': 'snes-super-mario-world',
             'Nintendo_64Box': 'nintendo-64-super-mario-64',
             'PLAYSTATION_1_BOX': 'playstation-1-crash-bandicoot'}


def permitted_metadata(node_name, key, old, media_id, version):
    """A finite whitelist, not a general exemption for modifying model extras."""
    if node_name == 'CartridgePlacement' and key == 'mediaIsIncluded' and old is False and media_id == 'mega-drive-sonic-the-hedgehog':
        return True
    if (node_name in ('NesBox', 'SnesBox', 'Nintendo_64Box') and BOX_MEDIA[node_name] == media_id
            and key == 'containsGameMedia' and old is False):
        return True
    if BOX_MEDIA.get(node_name) != media_id or key not in ('limitations', 'geometryLimitations'):
        raise ValueError('Metadata correction is not whitelisted')
    if node_name == 'PLAYSTATION_1_BOX':
        if key != 'geometryLimitations' or old != PS1_LIMITATIONS:
            raise ValueError('Unexpected original PlayStation limitations')
        description = old.replace(' No disc included.', '')
    else:
        if old != NINTENDO_LIMITATIONS:
            raise ValueError('Unexpected original Nintendo limitations')
        description = old.replace('pack-in leaflets, game media, shrinkwrap', 'pack-in leaflets, shrinkwrap')
    return description.rstrip('.') + '. Enclosed media: ' + media_id + ' v' + version + '; original scale and published media geometry preserved.'


def update_descriptive_metadata(document, media_id, version):
    changes = []
    for index, node in enumerate(document['nodes']):
        name, extras = node.get('name'), node.get('extras', {})
        keys = ('mediaIsIncluded',) if name == 'CartridgePlacement' else ('limitations', 'geometryLimitations', 'containsGameMedia') if name in BOX_MEDIA else ()
        for key in keys:
            if key not in extras:
                continue
            old = extras[key]
            new = permitted_metadata(name, key, old, media_id, version)
            changes.append({'nodeIndex': index, 'nodeName': name, 'key': key, 'old': old, 'new': new})
            extras[key] = new
    return changes


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_input(document, binary, media=False):
    if len(document.get('buffers', [])) != 1 or document['buffers'][0].get('uri'):
        raise ValueError('Composition requires one embedded buffer')
    if document['buffers'][0]['byteLength'] > len(binary):
        raise ValueError('Truncated embedded buffer')
    if document.get('skins') or document.get('cameras') or document.get('extensions'):
        raise ValueError('Skins, cameras and document extensions are not supported')
    if media and document.get('animations'):
        raise ValueError('Published media must be static')
    if len(document.get('scenes', [])) != 1:
        raise ValueError('Expected one scene')
    for view in document.get('bufferViews', []):
        if view.get('buffer', 0) != 0 or view.get('extensions'):
            raise ValueError('External or compressed buffer view is not supported')
    for mesh in document.get('meshes', []):
        for primitive in mesh['primitives']:
            if primitive.get('extensions'):
                raise ValueError('Compressed/extended mesh primitives are not supported')
    for image in document.get('images', []):
        if 'bufferView' not in image or 'uri' in image:
            raise ValueError('All images must be embedded')


def remap_media(document, offsets, binary_offset):
    result = deepcopy(document)
    def texture_indices(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.endswith('Texture') and isinstance(child, dict) and 'index' in child:
                    child['index'] += offsets['textures']
                else:
                    texture_indices(child)
        elif isinstance(value, list):
            for child in value:
                texture_indices(child)
    for node in result.get('nodes', []):
        node['name'] = PREFIX + node.get('name', 'Unnamed media node')
        if 'mesh' in node:
            node['mesh'] += offsets['meshes']
        if 'children' in node:
            node['children'] = [index + offsets['nodes'] for index in node['children']]
    for mesh in result.get('meshes', []):
        for primitive in mesh['primitives']:
            for key in primitive['attributes']:
                primitive['attributes'][key] += offsets['accessors']
            for target in primitive.get('targets', []):
                for key in target:
                    target[key] += offsets['accessors']
            if 'indices' in primitive:
                primitive['indices'] += offsets['accessors']
            if 'material' in primitive:
                primitive['material'] += offsets['materials']
    for accessor in result.get('accessors', []):
        if 'bufferView' in accessor:
            accessor['bufferView'] += offsets['bufferViews']
        for part in ('indices', 'values'):
            if part in accessor.get('sparse', {}):
                accessor['sparse'][part]['bufferView'] += offsets['bufferViews']
    for view in result.get('bufferViews', []):
        view['byteOffset'] = view.get('byteOffset', 0) + binary_offset
    for material in result.get('materials', []):
        texture_indices(material)
    for texture in result.get('textures', []):
        if 'source' in texture:
            texture['source'] += offsets['images']
        if 'sampler' in texture:
            texture['sampler'] += offsets['samplers']
        for extension in texture.get('extensions', {}).values():
            if 'source' in extension:
                extension['source'] += offsets['images']
    for image in result.get('images', []):
        image['bufferView'] += offsets['bufferViews']
    return result


def compose(box, box_binary, media, media_binary, parent_name, translation, rotation, media_id, version):
    check_input(box, box_binary)
    check_input(media, media_binary, media=True)
    if any(n.get('extras', {}).get('boxContents') for n in box['nodes']):
        raise ValueError('Box already contains a Contents assembly')
    parents = [i for i, n in enumerate(box['nodes']) if n.get('name') == parent_name]
    if len(parents) != 1:
        raise ValueError('Missing or ambiguous insertion parent: ' + parent_name)
    result = deepcopy(box)
    offsets = {key: len(box.get(key, [])) for key in ARRAYS}
    remapped = remap_media(media, offsets, len(box_binary))
    for key in ARRAYS:
        if key in remapped:
            result.setdefault(key, []).extend(remapped[key])
    contents_index = len(result['nodes'])
    contents = {'name': 'Contents', 'translation': translation, 'rotation': rotation,
                'scale': [1, 1, 1],
                'children': [i + offsets['nodes'] for i in media['scenes'][media.get('scene', 0)]['nodes']],
                'extras': {'boxContents': True, 'removable': True, 'mediaAssetId': media_id,
                           'mediaVersion': version, 'preservation': 'Published geometry, materials and images; rigid placement only'}}
    result['nodes'].append(contents)
    result['nodes'][parents[0]].setdefault('children', []).append(contents_index)
    metadata_changes = update_descriptive_metadata(result, media_id, version)
    for key in ('extensionsUsed', 'extensionsRequired'):
        extensions = list(dict.fromkeys(box.get(key, []) + media.get(key, [])))
        if extensions:
            result[key] = extensions
    binary = box_binary + media_binary
    result['buffers'][0]['byteLength'] = len(binary)
    receipt = {'offsets': offsets, 'mediaCounts': {key: len(media.get(key, [])) for key in ARRAYS},
               'boxBinaryBytes': len(box_binary), 'mediaBinaryBytes': len(media_binary),
               'boxBufferByteLength': box['buffers'][0]['byteLength'],
               'boxExtensions': {key: box.get(key) for key in ('extensionsUsed', 'extensionsRequired')},
               'descriptiveMetadataOverrides': metadata_changes,
               'contents': {'nodeName': 'Contents', 'nodeIndex': contents_index,
                            'parentName': parent_name, 'parentIndex': parents[0],
                            'translationMeters': translation, 'rotationXyzw': rotation, 'scale': [1, 1, 1]}}
    return result, binary, receipt


def box_only(document, binary, receipt):
    """Recover the original box document/buffer for existing template audits."""
    roots = [i for i, node in enumerate(document.get('nodes', []))
             if node.get('extras', {}).get('boxContents')]
    contents = receipt['contents']
    if roots != [contents['nodeIndex']]:
        raise ValueError('Expected exactly the receipt-bound Contents node')
    node = document['nodes'][roots[0]]
    if (node.get('name') != contents['nodeName'] or node.get('scale') != [1, 1, 1] or
            node.get('translation') != contents['translationMeters'] or
            node.get('rotation') != contents['rotationXyzw'] or node.get('extras', {}).get('removable') is not True):
        raise ValueError('Invalid Contents rigid placement')
    if 'mediaSource' in receipt and any(node['extras'].get(node_key) != receipt['mediaSource'].get(source_key)
            for node_key, source_key in (('mediaAssetId', 'assetId'), ('mediaVersion', 'version'))):
        raise ValueError('Contents identity differs from the pinned media receipt')
    for key in ARRAYS:
        before, added = receipt['offsets'][key], receipt['mediaCounts'][key]
        if not isinstance(before, int) or not isinstance(added, int) or min(before, added) < 0:
            raise ValueError('Invalid composition array range')
        expected = before + added + (1 if key == 'nodes' else 0)
        if len(document.get(key, [])) != expected:
            raise ValueError('Composition array extent differs: ' + key)
    if contents['nodeIndex'] != len(document['nodes']) - 1:
        raise ValueError('Contents must be the final appended node')
    parents = [i for i, item in enumerate(document['nodes']) if roots[0] in item.get('children', [])]
    if parents != [contents['parentIndex']] or not 0 <= parents[0] < receipt['offsets']['nodes']:
        raise ValueError('Contents parent differs from receipt')
    if document['nodes'][parents[0]].get('name') != contents['parentName']:
        raise ValueError('Contents parent name differs from receipt')
    if document['nodes'][parents[0]]['children'].count(roots[0]) != 1:
        raise ValueError('Contents is attached more than once')
    start = receipt['offsets']['nodes']
    media_indices = set(range(start, contents['nodeIndex']))
    seen = set()
    def visit(index):
        if index not in media_indices or index in seen:
            raise ValueError('Contents subtree escapes the published media range')
        seen.add(index)
        for child in document['nodes'][index].get('children', []):
            visit(child)
    for child in node.get('children', []):
        visit(child)
    if seen != media_indices:
        raise ValueError('Unreachable published media node')
    for index, item in enumerate(document['nodes'][:start]):
        if any(child >= start and not (index == parents[0] and child == roots[0])
               for child in item.get('children', [])):
            raise ValueError('Box has an unexpected attachment to media nodes')
    if len(binary) != receipt['boxBinaryBytes'] + receipt['mediaBinaryBytes']:
        raise ValueError('Composition binary extent differs from receipt')
    if document['buffers'][0]['byteLength'] != len(binary):
        raise ValueError('Composition buffer declaration differs from its binary extent')
    result = deepcopy(document)
    modified = set()
    for change in receipt.get('descriptiveMetadataOverrides', []):
        if set(change) != {'nodeIndex', 'nodeName', 'key', 'old', 'new'}:
            raise ValueError('Invalid descriptive metadata correction record')
        index, key = change['nodeIndex'], change['key']
        if not 0 <= index < start or (index, key) in modified:
            raise ValueError('Duplicate or non-box metadata correction')
        modified.add((index, key))
        item = result['nodes'][index]
        if item.get('name') != change['nodeName'] or item.get('extras', {}).get(key) != change['new']:
            raise ValueError('Descriptive metadata differs from its exact correction record')
        expected = permitted_metadata(change['nodeName'], key, change['old'],
                                      node['extras']['mediaAssetId'], node['extras']['mediaVersion'])
        if change['new'] != expected:
            raise ValueError('Descriptive metadata correction is outside the whitelist')
        item['extras'][key] = change['old']
    for key, count in receipt['offsets'].items():
        if count:
            result[key] = result[key][:count]
        else:
            result.pop(key, None)
    parent = result['nodes'][receipt['contents']['parentIndex']]
    parent['children'].remove(receipt['contents']['nodeIndex'])
    if not parent['children']:
        parent.pop('children')
    result['buffers'][0]['byteLength'] = receipt['boxBufferByteLength']
    for key, value in receipt['boxExtensions'].items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = value
    return result, binary[:receipt['boxBinaryBytes']]


def validate_composition(box_glb, media_glb, composed_glb, receipt):
    """Prove every original box/media record and embedded byte was retained."""
    box, box_binary = read_glb(box_glb)
    media, media_binary = read_glb(media_glb)
    actual, actual_binary = read_glb(composed_glb)
    recovered, recovered_binary = box_only(actual, actual_binary, receipt)
    if recovered != box or recovered_binary != box_binary:
        raise ValueError('Composition changed original box data')
    expected = remap_media(media, receipt['offsets'], receipt['boxBinaryBytes'])
    for key in ARRAYS:
        start, count = receipt['offsets'][key], receipt['mediaCounts'][key]
        if actual.get(key, [])[start:start + count] != expected.get(key, []):
            raise ValueError('Composition changed published media records: ' + key)
    start = receipt['boxBinaryBytes']
    if actual_binary[start:start + receipt['mediaBinaryBytes']] != media_binary:
        raise ValueError('Composition changed published media binary bytes')
    if len(actual_binary) != start + len(media_binary):
        raise ValueError('Unexpected appended binary bytes')
    index = receipt['contents']['nodeIndex']
    node = actual['nodes'][index]
    if (node['translation'] != receipt['contents']['translationMeters'] or
            node['rotation'] != receipt['contents']['rotationXyzw'] or node.get('scale') != [1, 1, 1]):
        raise ValueError('Contents transform differs from the recorded rigid placement')
    if node['children'] != [i + receipt['offsets']['nodes'] for i in media['scenes'][media.get('scene', 0)]['nodes']]:
        raise ValueError('Contents roots differ from the published media scene')
    for key in ('extensionsUsed', 'extensionsRequired'):
        expected_extensions = list(dict.fromkeys(box.get(key, []) + media.get(key, [])))
        if actual.get(key, []) != expected_extensions:
            raise ValueError('Composition extension declarations differ from its sources')
    return {'status': 'passed', 'boxGlbSha256': sha(box_glb), 'mediaGlbSha256': sha(media_glb),
            'composedGlbSha256': sha(composed_glb), 'boxBinaryBytesPreserved': len(box_binary),
            'mediaBinaryBytesPreserved': len(media_binary), 'mediaNodeCount': len(media['nodes']),
            'mediaImagesPreserved': len(media.get('images', [])), 'mediaScale': [1, 1, 1]}
