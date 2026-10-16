"""Empty North American standard jewel case, reusing the verified case assembly.

The disc remains its own immutable asset. This packaging builder does not alter
the published disc or the earlier reference module.
"""
import math
from media_playstation import build as build_case_with_disc


def build(api):
    root = build_case_with_disc(api)
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
    return root
