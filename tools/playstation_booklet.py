"""Omit hidden page caps that interfere with opaque jewel-case booklet print.

The eight beveled page sections keep their vertex positions and visible edge
bands. Only their sixteen broad internal caps are removed; the unchanged outer
printed sheets remain the visible front and back. This is a display model, not
a collection of individually closed manufacturing solids.
"""
import hashlib
import json
import math


CAP_LEVELS_MM = tuple(z for i in range(8)
                      for z in (3.3005 + i * .125, 3.4225 + i * .125))
ORIGINAL_TOPOLOGY = '941de957009319692215104d27c062019dbdbb3331e89f71d8c4d64e9945504e'
OPEN_EDGE_TOPOLOGY = 'a18bf2b19560afd942a5d0cc46bb956eff06837a55e8b1d7421700df4fed2422'


def topology_hash(faces):
    return hashlib.sha256(json.dumps(faces, separators=(',', ':')).encode()).hexdigest()


def hidden_cap_indices(vertices_mm, faces):
    """Select all sixteen original broad caps, or none after their removal.

    Bevels and narrow edge faces are never selected. Partial edits, duplicate
    caps, nonplanar caps and broad faces at unexpected depths are rejected.
    Native topology is independently pinned before this selector is used.
    """
    if any(len(v) != 3 or not all(math.isfinite(x) for x in v) for v in vertices_mm):
        raise ValueError('Booklet coordinates must be finite 3D vectors')
    result, levels = [], []
    for index, face in enumerate(faces):
        if len(face) < 3 or any(type(i) is not int or not 0 <= i < len(vertices_mm) for i in face):
            raise ValueError('Invalid booklet polygon indices')
        points = [vertices_mm[i] for i in face]
        width = max(v[0] for v in points) - min(v[0] for v in points)
        height = max(v[1] for v in points) - min(v[1] for v in points)
        if width < 100 or height < 100:
            continue
        if len(face) != 4 or max(v[2] for v in points) - min(v[2] for v in points) > .00001:
            raise ValueError('Unexpected broad booklet face')
        depth = sum(v[2] for v in points) / 4
        matching = [i for i, z in enumerate(CAP_LEVELS_MM) if abs(depth - z) < .00001]
        if len(matching) != 1 or matching[0] in levels:
            raise ValueError('Unexpected or duplicate booklet cap depth')
        leaf = matching[0] // 2
        expected_width = 119.726 - .018 * (leaf % 3)
        expected_height = 119.706 - .014 * (leaf % 2)
        if (abs(width - expected_width) > .0001 or abs(height - expected_height) > .0001
                or abs((max(v[0] for v in points) + min(v[0] for v in points)) / 2 - 6.08) > .0001
                or abs((max(v[1] for v in points) + min(v[1] for v in points)) / 2 - 62.375) > .0001):
            raise ValueError('Booklet cap no longer fits its original hidden footprint')
        levels.append(matching[0])
        result.append(index)
    if result and (len(result) != 16 or set(levels) != set(range(16))):
        raise ValueError('Expected all sixteen original booklet caps')
    return result


def remove_hidden_booklet_caps(root=None):
    """Remove exactly sixteen native BookletPages quads; return 16 or 0.

    Work on a temporary mesh and fail before replacing the source if the
    approved topology or any remaining vertex, face, UV or corner normal differs.
    """
    import bpy
    import bmesh
    if root is None:
        root = bpy.data.objects.get('PLAYSTATION_1_BOX')
    if root is None:
        raise ValueError('PlayStation box root is missing')
    matches = [obj for obj in root.children_recursive if obj.name == 'BookletPages']
    if len(matches) != 1 or matches[0].type != 'MESH':
        raise ValueError('Expected one BookletPages mesh beneath the box root')
    obj = matches[0]
    mesh = obj.data
    if obj.modifiers or mesh.users != 1 or len(mesh.vertices) != 768:
        raise ValueError('Unexpected shared, modified or rebuilt booklet mesh')
    faces = [list(p.vertices) for p in mesh.polygons]
    fingerprint = topology_hash(faces)
    if fingerprint not in (ORIGINAL_TOPOLOGY, OPEN_EDGE_TOPOLOGY):
        raise ValueError('Booklet topology differs from the approved source')
    bpy.context.view_layer.update()
    transform = root.matrix_world.inverted() @ obj.matrix_world
    vertices_mm = [tuple(x * 1000 for x in transform @ vertex.co) for vertex in mesh.vertices]
    removed = set(hidden_cap_indices(vertices_mm, faces))
    if fingerprint == OPEN_EDGE_TOPOLOGY:
        if removed:
            raise ValueError('Corrected booklet unexpectedly contains hidden caps')
        return 0
    if len(removed) != 16:
        raise ValueError('Original booklet is missing expected hidden caps')
    kept = [p for p in mesh.polygons if p.index not in removed]
    loop_indices = [i for p in kept for i in p.loop_indices]
    original_vertices = [tuple(v.co) for v in mesh.vertices]
    original_uvs = {layer.name: [tuple(layer.data[i].uv) for i in loop_indices]
                    for layer in mesh.uv_layers}
    original_normals = [tuple(mesh.corner_normals[i].vector) for i in loop_indices]
    working = mesh.copy()
    try:
        bm = bmesh.new()
        try:
            bm.from_mesh(working)
            bm.faces.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[bm.faces[i] for i in sorted(removed)], context='FACES_ONLY')
            bm.to_mesh(working)
        finally:
            bm.free()
        working.update()
        if ([tuple(v.co) for v in working.vertices] != original_vertices
                or [list(p.vertices) for p in working.polygons] != [list(p.vertices) for p in kept]
                or [p.material_index for p in working.polygons] != [p.material_index for p in kept]
                or [p.use_smooth for p in working.polygons] != [p.use_smooth for p in kept]
                or topology_hash([list(p.vertices) for p in working.polygons]) != OPEN_EDGE_TOPOLOGY):
            raise ValueError('Booklet deletion changed unrelated mesh data')
        if {layer.name: [tuple(v.uv) for v in layer.data] for layer in working.uv_layers} != original_uvs:
            raise ValueError('Booklet deletion changed remaining UVs')
        if [tuple(v.vector) for v in working.corner_normals] != original_normals:
            raise ValueError('Booklet deletion changed remaining corner normals')
    except Exception:
        bpy.data.meshes.remove(working)
        raise
    name = mesh.name
    obj.data = working
    bpy.data.meshes.remove(mesh)
    working.name = name
    return 16
