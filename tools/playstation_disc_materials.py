"""Bounded PS1 disc material and hidden-underlay correction.

The original SCUS-94900 scan and physical-disc photograph show a dark/tinted
clamping annulus, not a bright silver donut. These are visual material estimates,
not measured optical constants. Keep the generic 21 mm print-mask radius: the
photographs only establish an approximately 20 mm dark-region radius.
Visible geometry, positions, normals, UVs and artwork stay intact; only hidden
body-top triangle indices are removed to prevent consumer depth fighting.
"""
from copy import deepcopy
import struct


PROFILES = {
    'smoke': {'hubColor': [.025, .019, .029], 'hubAlpha': .70,
              'hubTransmission': .12, 'hubRoughness': .10,
              'matrixColor': [.018, .014, .022], 'matrixMetallic': .30,
              'matrixRoughness': .19},
    'dense': {'hubColor': [.025, .019, .029], 'hubAlpha': .84,
              'hubTransmission': .08, 'hubRoughness': .10,
              'matrixColor': [.018, .014, .022], 'matrixMetallic': .30,
              'matrixRoughness': .19},
}
DEFAULT_PROFILE = 'smoke'
HUB_NAME = 'Disc smoke tinted clamping substrate'
MATRIX_NAME = 'Disc dark clamping transition'


def _primitive(document, name):
    nodes = [node for node in document['nodes'] if node.get('name') == name]
    if len(nodes) != 1 or 'mesh' not in nodes[0]:
        raise ValueError(f'Expected one mesh node named {name}')
    mesh_index = nodes[0]['mesh']
    if sum(node.get('mesh') == mesh_index for node in document['nodes']) != 1:
        raise ValueError(f'{name} mesh is unexpectedly shared')
    primitives = document['meshes'][mesh_index]['primitives']
    if len(primitives) != 1:
        raise ValueError(f'{name} must have exactly one material primitive')
    return primitives[0]


def patch_document(document, profile=DEFAULT_PROFILE):
    """Return a material-only copy; never edit or re-encode the GLB BIN chunk."""
    result = deepcopy(document)
    values = PROFILES[profile]
    hub = _primitive(result, 'DiscClearHub')
    inner = _primitive(result, 'DiscInnerMatrix')
    outer = _primitive(result, 'DiscOuterRim')
    if inner['material'] != outer['material']:
        raise ValueError('Expected original shared inner-matrix/outer-rim material')
    hub_index = hub['material']
    if sum(p.get('material') == hub_index for m in result['meshes'] for p in m['primitives']) != 1:
        raise ValueError('Clamping substrate material is unexpectedly shared')
    material = result['materials'][hub_index]
    if material.get('name') != 'Disc transparent clamping substrate':
        raise ValueError('Expected the original transparent clamping substrate')
    material['name'] = HUB_NAME
    material['alphaMode'] = 'BLEND'
    material.setdefault('pbrMetallicRoughness', {}).update({
        'baseColorFactor': values['hubColor'] + [values['hubAlpha']],
        'roughnessFactor': values['hubRoughness'],
        'metallicFactor': 0,
    })
    material.setdefault('extensions', {}).setdefault('KHR_materials_transmission', {})['transmissionFactor'] = values['hubTransmission']
    matrix = deepcopy(result['materials'][inner['material']])
    matrix['name'] = MATRIX_NAME
    matrix.setdefault('pbrMetallicRoughness', {}).update({
        'baseColorFactor': values['matrixColor'] + [1.0],
        'roughnessFactor': values['matrixRoughness'],
        'metallicFactor': values['matrixMetallic'],
    })
    inner['material'] = len(result['materials'])
    result['materials'].append(matrix)
    return result


def validate_patch(before, before_binary, after, after_binary, profile=DEFAULT_PROFILE):
    """Strictly reject changes beyond the exact declared material transformation."""
    if before_binary != after_binary:
        raise ValueError('Disc geometry, UVs, normals, indices or embedded images changed')
    if after != patch_document(before, profile):
        raise ValueError('Disc patch includes undeclared JSON changes')
    return {'status': 'passed', 'geometryAndArtworkBytesUnchanged': True,
            'nodesAndTransformsUnchanged': True, 'outerRimMaterialUnchanged': True,
            'profile': profile, 'materialParameters': deepcopy(PROFILES[profile])}


def remove_hidden_disc_front(document, binary):
    """Remove only the 512 body triangles 5 micrometers below the front stack.

    The unchanged matrix, label and outer rim cover radii 18..60 mm at z=0.6
    mm. Removing their hidden underlay avoids depth fighting at consumer camera
    near/far ratios. Preserve every position/normal/UV/image byte and all other
    index buffers. The vacated end of the original index view is left unused.
    """
    from inspect_glb import Accessors
    result = deepcopy(document)
    primitive = _primitive(result, 'Disc')
    accessor_index = primitive['indices']
    accessor = result['accessors'][accessor_index]
    if sum(p.get('indices') == accessor_index for mesh in result['meshes'] for p in mesh['primitives']) != 1:
        raise ValueError('Disc index accessor is unexpectedly shared')
    view = result['bufferViews'][accessor['bufferView']]
    if sum(a.get('bufferView') == accessor['bufferView'] for a in result['accessors']) != 1:
        raise ValueError('Disc index buffer view is unexpectedly shared')
    if accessor['componentType'] != 5123 or accessor['type'] != 'SCALAR' or view.get('byteStride'):
        raise ValueError('Expected original tightly packed unsigned-short disc indices')
    reader = Accessors(document, binary)
    vertices = reader.read(primitive['attributes']['POSITION'])
    indices = [row[0] for row in reader.read(accessor_index)]
    kept, removed = [], 0
    for i in range(0, len(indices), 3):
        triangle = indices[i:i+3]
        hidden = all(abs(vertices[j][2] - .000595) < 1e-9 for j in triangle)
        if hidden:
            removed += 1
        else:
            kept.extend(triangle)
    if removed != 512 or len(indices) != 6144:
        raise ValueError('Disc top does not match the approved original 512-triangle underlay')
    offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    encoded = struct.pack('<' + 'H' * len(kept), *kept)
    output = bytearray(binary)
    output[offset:offset+len(encoded)] = encoded
    accessor['count'] = len(kept)
    return result, bytes(output)


def release_metadata(document, asset_id, version='0.2.0'):
    """Update only the known original standalone root's release identification."""
    if asset_id not in ('playstation-1', 'playstation-1-crash-bandicoot') or version != '0.2.0':
        raise ValueError('Only the two approved upstream disc 0.2.0 releases are supported')
    roots = [node for node in document['nodes'] if node.get('name') == 'PLAYSTATION_1_DISC']
    if len(roots) != 1:
        raise ValueError('Expected one standalone PS1 disc root')
    extras = roots[0]['extras']
    expected = {'playstation-1': ('unreleased reference-based reconstruction; see dimensional sources', None),
                'playstation-1-crash-bandicoot': ('versioned textured example 0.1.0', '0.1.0')}[asset_id]
    if extras.get('status') != expected[0] or extras.get('assetVersion') != expected[1]:
        raise ValueError('Unexpected previous release root metadata')
    if extras.get('assetId') not in (None, asset_id):
        raise ValueError('Previous source identifies another asset')
    updated = {'status': 'versioned standalone disc 0.2.0', 'assetId': asset_id, 'assetVersion': version}
    changes = [{'nodeName': 'PLAYSTATION_1_DISC', 'key': key, 'old': extras.get(key), 'new': value}
               for key, value in updated.items() if extras.get(key) != value]
    extras.update(updated)
    return changes


def correct_disc(document, binary, profile=DEFAULT_PROFILE, asset_id=None):
    result, output = remove_hidden_disc_front(patch_document(document, profile), binary)
    if asset_id:
        release_metadata(result, asset_id)
    return result, output


def validate_correction(before, before_binary, after, after_binary, profile=DEFAULT_PROFILE, asset_id=None):
    expected, expected_binary = correct_disc(before, before_binary, profile, asset_id)
    if after != expected or after_binary != expected_binary:
        raise ValueError('Disc correction differs from the exact material and hidden-top index patch')
    metadata_changes = release_metadata(deepcopy(before), asset_id) if asset_id else []
    return {'status': 'passed', 'removedHiddenBodyTriangles': 512,
            'positionsNormalsUvsAndEmbeddedImagesUnchanged': True,
            'allOtherTriangleIndicesUnchanged': True,
            'nodesTransformsAndDimensionsUnchanged': True,
            'outerRimMaterialUnchanged': True,
            'releaseMetadataChanges': metadata_changes,
            'profile': profile, 'materialParameters': deepcopy(PROFILES[profile])}


def remove_hidden_blender_front():
    import bpy
    import bmesh
    obj = bpy.data.objects['Disc']
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    faces = [face for face in bm.faces if all(abs(v.co.z - .000595) < 1e-9 for v in face.verts)]
    if len(faces) != 256 or any(len(face.verts) != 4 for face in faces):
        bm.free()
        raise ValueError('Native disc does not contain the original 256 hidden top quads')
    bmesh.ops.delete(bm, geom=faces, context='FACES_ONLY')
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def refine_blender_materials(profile=DEFAULT_PROFILE):
    """Apply equivalent parameters to a reopened native source, without export."""
    import bpy
    values = PROFILES[profile]
    hub = bpy.data.objects['DiscClearHub']
    inner = bpy.data.objects['DiscInnerMatrix']
    outer = bpy.data.objects['DiscOuterRim']
    if len(hub.data.materials) != 1 or len(inner.data.materials) != 1 or len(outer.data.materials) != 1:
        raise ValueError('Unexpected native disc material slots')
    if inner.data.materials[0] != outer.data.materials[0]:
        raise ValueError('Native inner and outer matrix materials must initially match')
    material = hub.data.materials[0]
    if material.name != 'Disc transparent clamping substrate':
        raise ValueError('Native disc is not an original source')
    material.name = HUB_NAME
    material.diffuse_color = (*values['hubColor'], values['hubAlpha'])
    material.surface_render_method = 'BLENDED'
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = (*values['hubColor'], 1)
    shader.inputs['Alpha'].default_value = values['hubAlpha']
    shader.inputs['Transmission Weight'].default_value = values['hubTransmission']
    shader.inputs['Roughness'].default_value = values['hubRoughness']
    shader.inputs['Metallic'].default_value = 0
    matrix = inner.data.materials[0].copy()
    matrix.name = MATRIX_NAME
    matrix.diffuse_color = (*values['matrixColor'], 1)
    shader = matrix.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = (*values['matrixColor'], 1)
    shader.inputs['Roughness'].default_value = values['matrixRoughness']
    shader.inputs['Metallic'].default_value = values['matrixMetallic']
    inner.data.materials[0] = matrix
