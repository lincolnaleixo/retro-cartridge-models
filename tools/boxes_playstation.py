"""Empty North American standard jewel case, reusing the verified case assembly.

The disc remains its own immutable asset. This packaging builder does not alter
the published disc or the earlier reference module.
"""
import math
from media_playstation import build as build_case_with_disc


LEFT_SPINE_LIMIT_MM = -68.84
LEFT_SPINE_PARTS = frozenset({'TrayRibbedSpineWeb', 'TraySpineEdge_-69.65',
                             *(f'TraySpineCorrugation_{i:02}' for i in range(35))})


def left_spine_affine(name, minimum_x_mm, maximum_x_mm):
    """Return a positive X scale/offset that keeps the tray behind its paper."""
    if name not in LEFT_SPINE_PARTS:
        raise ValueError('Not a left spine component: ' + name)
    if not all(math.isfinite(x) for x in (minimum_x_mm, maximum_x_mm)):
        raise ValueError('Spine bounds must be finite')
    if maximum_x_mm <= minimum_x_mm:
        raise ValueError('Spine component must have positive width')
    if minimum_x_mm >= LEFT_SPINE_LIMIT_MM - 0.00001:
        return 1.0, 0.0
    if name == 'TraySpineEdge_-69.65':
        # This entire rail was outside the folded paper. Preserve its width;
        # clamping its vertices to the paper would collapse the closed solid.
        return 1.0, LEFT_SPINE_LIMIT_MM - minimum_x_mm
    if maximum_x_mm <= LEFT_SPINE_LIMIT_MM:
        raise ValueError('Spine web/rib has no valid inboard endpoint')
    scale = (maximum_x_mm - LEFT_SPINE_LIMIT_MM) / (maximum_x_mm - minimum_x_mm)
    return scale, maximum_x_mm * (1.0 - scale)


def refine_left_spine_clearance(root=None):
    """Move only 37 molded tray parts behind the left folded paper face.

    Use evaluated bounds and a root-space affine transform. Existing bevels,
    polygons and UVs remain intact; right endpoints stay fixed except for the
    complete 0.7 mm rail, whose width is preserved by an inward translation.
    """
    import bpy
    from mathutils import Matrix
    if root is None:
        root = bpy.data.objects.get('PLAYSTATION_1_BOX')
    if root is None:
        raise ValueError('PlayStation box root is missing')
    parts = {obj.name: obj for obj in root.children_recursive
             if obj.name in LEFT_SPINE_PARTS}
    if set(parts) != LEFT_SPINE_PARTS:
        raise ValueError('Expected all 37 original left spine components')
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    inverse_root = root.matrix_world.inverted()
    for name, obj in parts.items():
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            coordinates = [(inverse_root @ evaluated.matrix_world @ vertex.co).x * 1000
                           for vertex in mesh.vertices]
        finally:
            evaluated.to_mesh_clear()
        scale, offset = left_spine_affine(name, min(coordinates), max(coordinates))
        if scale == 1.0 and offset == 0.0:
            continue
        affine = Matrix.Identity(4)
        affine[0][0] = scale
        affine[0][3] = offset / 1000
        obj.matrix_world = root.matrix_world @ affine @ inverse_root @ obj.matrix_world
    bpy.context.view_layer.update()


def refine_clear_materials(alpha_coverage=None):
    """Update the box's stable clear-material names, including a loaded source."""
    import bpy
    coverage = {'Clear molded polystyrene': .035,
                'Polystyrene rims and catches': .12,
                'Clear injection molded tray': .06,
                'Clear polystyrene spring hub': .20}
    if alpha_coverage:
        coverage.update(alpha_coverage)
    # A single alpha-blended glossy approximation keeps paper readable in
    # glTF viewers and Godot, where transmission is not consistently imported.
    # Combining transmission and low alpha produced unstable overlapping
    # clear surfaces, while full transmission made the Godot case opaque.
    # Retain a distinct hub material so its small retaining fingers remain
    # visible without frosting the entire tray. This does not touch media.
    hub_name = 'Clear polystyrene spring hub'
    hub = bpy.data.materials.get(hub_name)
    if hub is None:
        hub = bpy.data.materials['Clear injection molded tray'].copy()
        hub.name = hub_name
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and (obj.name == 'DiscHub' or obj.name.startswith('HubSpringFinger')):
            obj.data.materials.clear()
            obj.data.materials.append(hub)
    for name, roughness in [('Clear molded polystyrene', .035),
                            ('Polystyrene rims and catches', .05),
                            ('Clear injection molded tray', .045),
                            (hub_name, .12)]:
        mat = bpy.data.materials[name]
        alpha = coverage[name]
        mat.diffuse_color = (*mat.diffuse_color[:3], alpha)
        mat.surface_render_method = 'BLENDED' if alpha < 1.0 else 'DITHERED'
        shader = mat.node_tree.nodes['Principled BSDF']
        shader.inputs['Alpha'].default_value = alpha
        shader.inputs['Transmission Weight'].default_value = 0.0
        shader.inputs['Roughness'].default_value = roughness
        shader.inputs['IOR'].default_value = 1.59


def build(api):
    root = build_case_with_disc(api)
    refine_clear_materials()
    root.name = 'PLAYSTATION_1_BOX'
    root['variant'] = 'North American standard single-disc jewel case; blank paper inserts'
    root['referenceBasis'] = 'CMC original jewel-case inspection dimensions and standard-tray drawings; NTSC-U/C specimen photographs'
    root['geometryLimitations'] = 'Standard-compatible envelope; fine molded features and booklet leaves approximate. No disc included.'
    root['packagingType'] = 'Jewel case'
    # Keep the real tray hub; remove only the separate optical media assembly.
    for obj in list(root.children_recursive):
        if obj.get('isDiscComponent'):
            api.bpy.data.objects.remove(obj, do_unlink=True)
    lid = api.bpy.data.objects['FrontLid']
    lid['boxHinge'] = True
    lid['hingeAxis'] = 'Y'
    lid['closedAngleDegrees'] = 0.0
    lid['openAngleDegrees'] = -110.0
    lid['animationPhase'] = 0.0
    # Fresh paper is neutral in the template. Fine, packed paper roughness from
    # the source assembly remains present; no age stains or printed graphics.
    for name, color in [('Neutral booklet cover paper', (.82, .82, .80)),
                        ('Booklet cut paper edges', (.78, .78, .75)),
                        ('Neutral printed tray card', (.82, .82, .80))]:
        mat = api.bpy.data.materials[name]
        mat.diffuse_color = (*color, 1)
        mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*color, 1)
    for name, slot in [('FrontLabel', 'Front'), ('RearLabel', 'WrapBack'),
                       ('InsertInnerPaper', 'BookletBack')]:
        obj = api.bpy.data.objects[name]
        obj['artworkSlot'] = slot
        original = obj.data.materials[0]
        mat = original.copy()
        mat.name = 'Box print · ' + slot
        obj.data.materials[0] = mat
    # A clear-tray edition can print both sides of the same folded tray card.
    # Give the inner sheet its own UVs and image, rather than mirroring the back.
    old_inside = api.bpy.data.objects['RearCardInside']
    api.bpy.data.objects.remove(old_inside, do_unlink=True)
    outside = api.bpy.data.objects['RearLabel']
    inside = outside.copy()
    inside.data = outside.data.copy()
    inside.name = 'TrayCardInside'
    api.bpy.context.collection.objects.link(inside)
    inside.parent = root
    for vertex in inside.data.vertices:
        vertex.co.z += 0.08 * api.MM
        if abs(vertex.co.x) > 68.9 * api.MM:
            vertex.co.x -= math.copysign(0.06 * api.MM, vertex.co.x)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(inside.data)
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(inside.data)
    bm.free()
    for uv in inside.data.uv_layers.active.data:
        uv.uv.x = 1.0 - uv.uv.x
    inside['artworkSlot'] = 'WrapInside'
    mat = inside.data.materials[0].copy()
    mat.name = 'Box print · WrapInside'
    inside.data.materials[0] = mat
    tray = api.empty('RemovableTray', parent=root)
    tray['packagingPart'] = 'Removable injection-molded tray with spring hub'
    for obj in list(root.children_recursive):
        if obj.type == 'MESH' and (obj.name.startswith('Tray') or
                                  obj.name.startswith('HubSpringFinger') or obj.name == 'DiscHub'):
            world = obj.matrix_world.copy()
            obj.parent = tray
            obj.matrix_world = world
    root['artworkSlots'] = ['Front', 'WrapBack', 'BookletBack', 'WrapInside']
    refine_left_spine_clearance(root)
    from playstation_booklet import remove_hidden_booklet_caps
    remove_hidden_booklet_caps(root)
    return root
