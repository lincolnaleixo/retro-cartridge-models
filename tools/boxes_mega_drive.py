"""Original, articulated western Mega Drive plastic game case.

The 129 x 177 x 26 mm body and all small tooling details are estimates, not
factory drawings. The intact retail hanger extends beyond the body envelope.
See docs/mega-drive-box-reference-evidence.json for the specimen references.

Build with the create_media_models API. Closed is the default; two nested
living-hinge pivots unfold the spine and lid to a flat, open case. No third-party
artwork or reference photograph is included in this neutral template.
"""
import math

import bpy
import bmesh


WIDTH, HEIGHT, DEPTH = 129.0, 177.0, 26.0


def _adopt(obj, parent):
    """Change assembly parent while preserving the authored closed transform."""
    bpy.context.view_layer.update()
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def _hinge(api, name, location, parent, angle):
    obj = api.empty(name, location, parent)
    obj['boxHinge'] = True
    obj['hingeAxis'] = 'Y'
    obj['closedAngleDegrees'] = 0.0
    obj['openAngleDegrees'] = angle
    obj['rotationAxis'] = 'Y'
    obj['closedRotationDegrees'] = 0.0
    obj['openRotationDegrees'] = angle
    obj['mechanism'] = 'Idealized polypropylene flexure; no pin or metal barrel'
    return obj


def _extrusion(api, name, points, back, front, mat, parent, bevel=.12):
    n = len(points)
    vertices = [(x, y, z) for z in (back, front) for x, y in points]
    faces = [tuple(reversed(range(n))), tuple(range(n, n * 2))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return _adopt(api.mesh(name, vertices, faces, mat, bevel), parent)


def _wall(api, name, z0, z1, mat, parent, inset=0.0, wall=1.25):
    """An actual hollow U-shaped rim, open along the living-hinge edge."""
    outer = api.rounded_points(WIDTH - inset * 2, HEIGHT - inset * 2,
                               max(.35, 1.6 - inset), 0, HEIGHT / 2, 8)
    inner = api.rounded_points(WIDTH - inset * 2 - wall * 2,
                               HEIGHT - inset * 2 - wall * 2,
                               max(.25, 1.6 - inset - wall), 0, HEIGHT / 2, 8)
    n = len(outer)
    vertices = [(x, y, z) for z in (z0, z1) for loop in (outer, inner)
                for x, y in loop]
    faces = []
    active = []
    for i in range(n):
        j = (i + 1) % n
        active.append((outer[i][0] + outer[j][0]) / 2 > -WIDTH / 2 + inset + 1.8)
    for i in range(n):
        j = (i + 1) % n
        if not active[i]:
            continue
        faces += [(i, j, j + n * 2, i + n * 2),
                  (i + n, i + n * 3, j + n * 3, j + n),
                  (i, i + n, j + n, j),
                  (i + n * 2, j + n * 2, j + n * 3, i + n * 3)]
        if not active[(i - 1) % n]:
            faces.append((i, i + n * 2, i + n * 3, i + n))
        if not active[j]:
            faces.append((j, j + n, j + n * 3, j + n * 2))
    return _adopt(api.mesh(name, vertices, faces, mat, .12), parent)


def _apply(obj):
    bpy.context.view_layer.objects.active = obj
    for modifier in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=modifier.name)


def _cut(api, obj, center, size):
    cutter = api.box('Temporary tooling opening', center, size, None, .25)
    _apply(cutter)
    mod = obj.modifiers.new('Open molding slot', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def _block(api, name, center, size, mat, parent, bevel=.18):
    return _adopt(api.box(name, center, size, mat, bevel), parent)


def _slot(api, name, slot, width, height, center, material, parent, rear=False):
    obj = api.label(name, width, height, *center, material, radius=.3, rear=rear)
    obj['artworkSlot'] = slot
    obj['artworkWidthMm'] = width
    obj['artworkHeightMm'] = height
    obj['artworkCondition'] = 'Pristine, unprinted replacement surface'
    obj['paperConstruction'] = 'Separate paper below the clear exterior sleeve'
    return _adopt(obj, parent)


def _spine_surface(api, name, x, width, height, material, parent, artwork=False):
    """Printed spine reads from left to right when viewed from outside (-X)."""
    y0, y1 = (HEIGHT - height) / 2, (HEIGHT + height) / 2
    z0, z1 = -width / 2, width / 2
    vertices = [(x, y0, z1), (x, y0, z0), (x, y1, z0), (x, y1, z1)]
    obj = api.mesh(name, vertices, [(0, 3, 2, 1)], material)
    uv = obj.data.uv_layers.new(name='ArtworkUV')
    coordinates = ([(1, 0), (0, 0), (0, 1), (1, 1)] if artwork
                   else [(0, 0), (1, 0), (1, 1), (0, 1)])
    for face in obj.data.polygons:
        for loop_index in face.loop_indices:
            uv.data[loop_index].uv = coordinates[obj.data.loops[loop_index].vertex_index]
    if artwork:
        obj['artworkSlot'] = 'Spine'
        obj['artworkAspectRatio'] = width / height
        obj['artworkWidthMm'] = width
        obj['artworkHeightMm'] = height
        obj['artworkOrientation'] = 'upright from outside (-X); U increases rear edge to front edge'
        obj['paperConstruction'] = 'Continuous wrap insert, partitioned at the two flexures'
    return _adopt(obj, parent)


def refine_spine_uvs():
    """Correct a released spine's U direction once without changing its mesh."""
    obj = bpy.data.objects.get('SpinePrint')
    if obj is None or obj.type != 'MESH' or obj.get('artworkSlot') != 'Spine':
        raise ValueError('Expected the named Mega Drive spine artwork surface')
    layer = obj.data.uv_layers.get('ArtworkUV')
    if layer is None:
        raise ValueError('Mega Drive spine has no ArtworkUV layer')
    bpy.context.view_layer.update()
    samples = [(float((obj.matrix_world @ obj.data.vertices[loop.vertex_index].co).z),
                float(layer.data[index].uv.x)) for index, loop in enumerate(obj.data.loops)]
    low, high = min(z for z, _ in samples), max(z for z, _ in samples)
    if high - low < .001:
        raise ValueError('Mega Drive spine is not in its closed inspection pose')
    expected = [(z - low) / (high - low) for z, _ in samples]
    correct = all(abs(u - target) < 1e-6 for (_, u), target in zip(samples, expected))
    mirrored = all(abs((1 - u) - target) < 1e-6 for (_, u), target in zip(samples, expected))
    if not correct and not mirrored:
        raise ValueError('Unexpected Mega Drive spine UV layout; refusing a broad rewrite')
    if mirrored and not correct:
        for value in layer.data:
            value.uv.x = 1.0 - value.uv.x
    obj['artworkOrientation'] = 'upright from outside (-X); U increases rear edge to front edge'
    return {'node': obj.name, 'changed': mirrored and not correct,
            'operation': 'U = 1 - U; V, geometry and articulation unchanged'}


def _spring_clip(api, name, x, y, z0, mat, parent, horizontal=False):
    """Tapered resilient stem and overhanging lip; not a solid support peg."""
    # Profile in local Y/Z, swept across a 9 mm width.
    section = [(0, z0), (1.1, z0), (1.1, z0 + 10.2),
               (-1.4, z0 + 11.1), (-3.0, z0 + 10.4),
               (-3.0, z0 + 9.5), (0, z0 + 9.8)]
    vertices = [(x + dx, y + dy, z) for dx in (-4.5, 4.5) for dy, z in section]
    if horizontal:
        vertices = [(x - (vy - y), y + (vx - x), vz) for vx, vy, vz in vertices]
    n = len(section)
    faces = [tuple(reversed(range(n))), tuple(range(n, n * 2))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return _adopt(api.mesh(name, vertices, faces, mat, .12), parent)


def _hanger(api, material, parent):
    """Intact early retail tab, with a real elongated hook opening."""
    points = [(-13, 175.4), (13, 175.4), (13, 184.7), (10.2, 188.0),
              (-10.2, 188.0), (-13, 184.7)]
    tab = _extrusion(api, 'RetailHanger', points, -2.6, -.9, material, parent, .55)
    _apply(tab)
    _cut(api, tab, (0, 182.8, -1.75), (16.0, 4.8, 5))
    tab['partRole'] = 'Intact molded retail hanging tab; removable by editing the source'
    tab['boxPart'] = 'RetailHanger'
    tab['nominalBodyEnvelopeExcludesThisPart'] = True
    return tab


def _grain(materials, objects):
    """Original periodic normal/roughness maps that survive glTF export."""
    from media_mega_drive import _packed_surface_maps, _exportable_abs, _surface_uv
    normal, maps = _packed_surface_maps()
    normal.name = 'PP case micrograin tangent normal 8mm'
    maps['satin'].name = 'PP case satin roughness'
    maps['molded'].name = 'PP case molded roughness'
    for mat, finish, strength in materials:
        _exportable_abs(mat, normal, maps[finish], strength)
        mat['surfaceFinish'] = 'Fine original isotropic PP-like micrograin; not scanned tooling'
    for obj in objects:
        if obj.type == 'MESH' and any(mat.name in obj.data.materials for mat, _, _ in materials):
            _surface_uv(obj)


def build(api):
    root = api.reset('MegaDriveGameBox')
    root['assetFamily'] = 'game-box'
    root['console'] = 'mega-drive'
    root['nominalDimensionsMm'] = [WIDTH, 188.0, DEPTH]
    root['caseBodyDimensionsMm'] = [WIDTH, HEIGHT, DEPTH]
    root['dimensionsIncludeRetailHanger'] = True
    root['hangerProjectionMm'] = 11.0
    root['heightWithRetailHangerMm'] = 188.0
    root['referenceEvidence'] = 'docs/mega-drive-box-reference-evidence.json'
    root['referenceBasis'] = 'Original Sonic PAL case photograph; auction specimen description; manufacturer protector fit envelope'
    root['geometryLimitations'] = 'Nominal dimensions; inferred tooling details; early projecting-hanger variant; idealized flexure pivots; blank booklet placeholder'
    root['packagingVariant'] = 'Early western black clamshell with intact retail hanger'
    root['openPose'] = 'Both Y flexures at -90 degrees; interior floors face +Z'
    root['construction'] = 'Hollow molded shell, paper wrap beneath a clear sleeve, removable booklet'
    root['printWrapNominalMm'] = [269.0, 172.0]
    root['measurementConfidence'] = 'Nominal visualization approximation; not a manufacturing replica'

    shell = api.material('Case molded polypropylene', (.019, .021, .023), .42)
    rim = api.material('Case satin rims and flexures', (.013, .015, .017), .36)
    page_edge = api.material('Unprinted booklet page edges', (.89, .885, .855), .78)
    paper_materials = {slot: api.material('Blank paper ' + slot, (.94, .935, .905), .67)
                       for slot in ('Front', 'Back', 'Spine', 'BookletFront', 'BookletBack')}
    sleeve = api.material('Clear flexible exterior sleeve', (.98, .99, 1.0), .19,
                           transmission=0.0, alpha=.055)
    sleeve['materialPurpose'] = 'Thin optically clear protector; restrained opacity preserves printed color'
    sleeve['nominalThicknessMm'] = .055
    sleeve['renderingApproximation'] = 'Alpha blend avoids unsupported refraction in portable viewers'

    rear_hinge = _hinge(api, 'RearSpineHinge', (-63.15, 0, -11.6), root, -90)
    lid = _hinge(api, 'FrontLid', (0, 0, 23.2), rear_hinge, -90)
    # Floors are thin shells. Four real slots in the lid expose the white wrap
    # below retaining tongues; the cartridge-side clips have their own slots.
    back = _block(api, 'BackShellFloor', (0, HEIGHT / 2, -12.05),
                  (126.8, 174.8, 1.25), shell, root, .45)
    front = _block(api, 'FrontShellFloor', (0, HEIGHT / 2, 12.05),
                   (126.8, 174.8, 1.25), shell, root, .45)
    _apply(front)
    for x, y, w, h in ((0, 5, 12, 5.5), (0, 172, 12, 5.5),
                        (59.2, 31, 6, 9), (59.2, 146, 6, 9)):
        _cut(api, front, (x, y, 12.05), (w, h, 4))
    _adopt(front, lid)
    _apply(back)
    for y in (31.0, 146.0):
        _cut(api, back, (0, y, -12.05), (10.8, 5.0, 4))

    _wall(api, 'BackShellPerimeterRim', -12.45, .25, rim, root)
    _wall(api, 'FrontShellPerimeterRim', .65, 12.45, rim, lid)
    _wall(api, 'BackInnerLocatingLip', -1.5, 1.45, rim, root, inset=1.35, wall=.62)

    # A broad flexible spine links the two shell edges. It is not a jewel-case
    # barrel hinge; the two fine flexure strips remain separately articulated.
    _block(api, 'SpineWeb', (-63.15, HEIGHT / 2, 0), (1.25, 174.2, 22.0),
           shell, rear_hinge, .35)
    for name, z, parent in (('RearFlexureFold', -11.6, rear_hinge),
                             ('FrontFlexureFold', 11.6, lid)):
        _block(api, name, (-63.15, HEIGHT / 2, z), (.38, 173.8, 1.6), rim, parent, .17)
    for y in (1.8, HEIGHT - 1.8):
        _block(api, 'SpineEndSeal', (-63.15, y, 0), (1.35, 1.0, 22.8), rim,
               rear_hinge, .18)

    # Molded U guides locate the cartridge sideways. The fitted game's width
    # runs along the case height, as on the inspected Sonic PAL specimen.
    upper = [(-37, 125), (-35.5, 125), (-35.5, 143.8),
             (35.5, 143.8), (35.5, 125), (37, 125), (37, 145.3), (-37, 145.3)]
    lower = [(x, HEIGHT - y) for x, y in reversed(upper)]
    _extrusion(api, 'UpperCartridgeGuide', upper, -11.45, -2.5, shell, root, .32)
    _extrusion(api, 'LowerCartridgeGuide', lower, -11.45, -2.5, shell, root, .32)
    _spring_clip(api, 'UpperCartridgeSpringClip', 0, 145.2, -11.45, rim, root)
    lower_clip = _spring_clip(api, 'LowerCartridgeSpringClip', 0, 31.8, -11.45, rim, root)
    # Reflect only its local Y coordinates to aim the tongue inward.
    for v in lower_clip.data.vertices:
        v.co.y = .0636 - v.co.y
    for x in (-36.2, 36.2):
        for y in (38.0, 139.0):
            _block(api, 'CartridgeCornerSupport', (x, y, -8.1),
                   (3.0, 8.0, 6.6), shell, root, .4)

    # Two end tongues and two outer-edge tongues hold the booklet. Two low
    # inner stops keep it aligned without covering its printable face.
    for y, sign in ((5.0, 1), (172.0, -1)):
        _block(api, 'BookletEndTongueStem', (0, y, 9.7), (9.5, 1.1, 4.5), rim, lid)
        _block(api, 'BookletEndTongueLip', (0, y + sign * 2.0, 7.8),
               (9.5, 4.8, 1.0), rim, lid, .24)
    for y in (31.0, 146.0):
        _block(api, 'BookletOuterTongueStem', (60.0, y, 9.5), (1.1, 7.5, 4.9), rim, lid)
        _block(api, 'BookletOuterTongueLip', (57.6, y, 7.45), (5.8, 7.5, 1.0), rim, lid, .24)
        _block(api, 'BookletInnerStop', (-54.5, y, 10.25), (1.4, 8.0, 2.5), rim, lid, .3)

    # Opposing snap hooks, shallow rim recesses and thumb grips make the
    # opening edge readable in both closed and open views.
    for y in (35.0, 142.0):
        _block(api, 'BackLatchCatch', (62.6, y, -.6), (1.8, 7.4, 2.4), rim, root, .3)
        _block(api, 'LidLatchHook', (62.2, y, 1.05), (1.3, 6.5, 2.3), rim, lid, .25)
        _block(api, 'LidLatchHookNose', (61.6, y, .0), (1.9, 6.5, .65), rim, lid, .18)
    for z, parent in ((-.7, root), (1.4, lid)):
        for y in (82.6, 85.5, 88.5, 91.5, 94.4):
            _block(api, 'OpeningEdgeThumbRidge', (64.1, y, z),
                   (.5, 1.0, 4.3), rim, parent, .22)
    _hanger(api, rim, root)

    # Subtle round ejector witness discs: pristine manufacturing details,
    # deliberately not cracks, scratches, weathering, or counterfeit stamps.
    for x in (-55.2, 55.2):
        for y in (15.5, 58.5, 118.5, 161.5):
            for z, parent in ((-11.405, root), (11.405, lid)):
                witness = api.cylinder('MoldEjectorWitness', (x, y, z), 2.65, .025,
                                       shell, vertices=32, bevel=0)
                _adopt(witness, parent)
    _slot(api, 'FrontPrint', 'Front', 122.0, 172.0, (0, 88.5, 12.71),
          paper_materials['Front'], lid)
    _slot(api, 'BackPrint', 'Back', 122.0, 172.0, (0, 88.5, -12.71),
          paper_materials['Back'], root, rear=True)
    _spine_surface(api, 'SpinePrint', -63.82, 25.0, 172.0,
                   paper_materials['Spine'], rear_hinge, artwork=True)
    # Optical sleeve faces are independent so no opaque duplicate paper or
    # sleeve can accidentally tint the consumer's print replacement.
    for name, z, parent, rear in (('FrontClearSleeve', 12.80, lid, False),
                                   ('BackClearSleeve', -12.80, root, True)):
        clear = api.label(name, 125.2, 174.1, 0, 88.5, z, sleeve, radius=.65, rear=rear)
        clear['partRole'] = 'Unprinted clear sleeve; retain when replacing paper artwork'
        _adopt(clear, parent)
    _spine_surface(api, 'SpineClearSleeve', -63.91, 25.25, 174.1, sleeve, rear_hinge)

    booklet = api.empty('Booklet', parent=root)
    _adopt(booklet, lid)
    booklet['partRole'] = 'Removable blank instruction booklet placeholder'
    booklet['nominalDimensionsMm'] = [93.2, 164.0, 2.1]
    booklet['referenceAspectRatio'] = 'Landscape Sonic PAL cover, approximately 1939:1102, stored sideways'
    booklet['printRotationDegrees'] = 90.0
    # Keep the outer edge beneath the retaining tongues. The reference manual
    # is narrower than the full lid, leaving a deliberate hinge-side margin.
    _block(api, 'BookletPageBlock', (10, 88.5, 9.35), (93.2, 164, 2.1),
           page_edge, booklet, .15)
    _slot(api, 'BookletFrontPrint', 'BookletFront', 93.2, 164, (10, 88.5, 8.275),
          paper_materials['BookletFront'], booklet, rear=True)
    _slot(api, 'BookletBackPrint', 'BookletBack', 93.2, 164, (10, 88.5, 10.425),
          paper_materials['BookletBack'], booklet)
    for z in (8.65, 9.02, 9.39, 9.76, 10.13):
        _block(api, 'BookletPageEdge', (56.6, 88.5, z), (.035, 163.2, .035),
               page_edge, booklet, 0)

    placement = api.empty('CartridgePlacement', (35.0, 88.5, -2.9), root)
    placement.rotation_euler.z = math.pi / 2
    placement['partRole'] = 'Insertion anchor for the existing bottom-centered Mega Drive cartridge'
    placement['fitsMediaAssetId'] = 'mega-drive'
    placement['expectedMediaDimensionsMm'] = [109.0, 70.0, 17.0]
    placement['mediaIsIncluded'] = False

    bpy.context.view_layer.update()
    _grain([(shell, 'molded', .16), (rim, 'satin', .08)], root.children_recursive)
    for obj in root.children_recursive:
        if obj.type != 'MESH':
            continue
        # Boolean and swept guide faces need unambiguous outward normals.
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        # The U-rim generator omits its hinge-side wall. Discard orphan corner
        # vertices too so source bounds match glTF, which removes them.
        unused = [vertex for vertex in bm.verts if not vertex.link_faces]
        if unused:
            bmesh.ops.delete(bm, geom=unused, context='VERTS')
        if not obj.get('artworkSlot') and len(obj.data.polygons) > 1:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(obj.data)
        bm.free()
    return root
