"""Original parametric western NES five-screw Game Pak reconstruction.

The 119.7 x 134 x 16.75 mm envelope follows the approximate no$nes drawing.
Rib placement, sloping rear returns and screw locations follow photographs of
an original five-screw Super Mario Bros. cartridge, not a third-party mesh.
See docs/nes-reference-evidence.json for measurements and their limitations.
"""
import math

import bpy
import bmesh

from media_mega_drive import (
    _apply, _subtract, _smooth, _packed_surface_maps, _exportable_abs, _surface_uv,
)


WIDTH = 119.7
HEIGHT = 134.0
DEPTH = 16.75
FRONT = DEPTH / 2
BACK = -DEPTH / 2
GRIP_X = -27.2
LABEL_X = 16.5
LABEL_WIDTH = 55.0
LABEL_FRONT = 90.0
LABEL_TOTAL = 97.0


def _normals(obj):
    data = bmesh.new()
    data.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(data, faces=list(data.faces))
    data.to_mesh(obj.data)
    data.free()
    obj.data.update()
    return obj


def _outline(width=WIDTH, top=HEIGHT, bottom=0, shoulder=22.5, foot=106.0):
    return [(-foot / 2, bottom), (foot / 2, bottom),
            (foot / 2, shoulder), (width / 2, shoulder),
            (width / 2, top), (-width / 2, top),
            (-width / 2, shoulder), (-foot / 2, shoulder)]


def _rear_cover(api, material):
    # The old five-screw cover has broad tapered returns, especially along its
    # top. There are no later REV-A hooked clips or invented shoulder lobes.
    seam = _outline(119.5, 133.85, .20, 22.6, 105.8)
    outside = _outline(113.3, 129.6, 4.4, 24.5, 101.6)
    n = len(seam)
    verts = [(x, y, -4.70) for x, y in seam]
    verts += [(x, y, BACK) for x, y in outside]
    faces = [tuple(range(n)), tuple(reversed(range(n, n * 2)))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    obj = _normals(api.mesh('RearShell', verts, faces, material, .30))
    _apply(obj)
    return obj


def _fold_land(api, shell):
    # One continuous recessed land runs up the front and over the rounded
    # top edge. Its narrow lip remains visible around the paper.
    front_cut = api.profile('Front label recess tool',
                            api.rounded_points(56.2, 91.2, 1.1, LABEL_X, 87.8),
                            FRONT + 1, FRONT - .32, None, 0)
    _subtract(shell, front_cut)
    radius = .80
    start_y, start_z = HEIGHT - radius, FRONT - radius
    rows = [(start_y - 2, FRONT, 0, 1)]
    for i in range(17):
        angle = math.pi / 2 * i / 16
        rows.append((start_y + radius * math.sin(angle),
                     start_z + radius * math.cos(angle),
                     math.sin(angle), math.cos(angle)))
    rows.append((HEIGHT, .8, 1, 0))
    section = [(y + ny, z + nz) for y, z, ny, nz in rows]
    section += [(y - .32 * ny, z - .32 * nz) for y, z, ny, nz in reversed(rows)]
    n = len(section)
    verts = [(x, y, z) for x in (LABEL_X - 28.1, LABEL_X + 28.1) for y, z in section]
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    faces += [(i, i + n, (i + 1) % n + n, (i + 1) % n) for i in range(n)]
    _subtract(shell, _normals(api.mesh('Wrapped label recess tool', verts, faces, None)))


def _folded_label(api, paper):
    radius = .80 - .32 + .035
    fold_length = math.pi * radius / 2
    start_y, start_z = HEIGHT - .80, FRONT - .80
    values = [0, .12, .35, .65, 1, 20, 40, 60, 80, LABEL_FRONT]
    values += [LABEL_FRONT + fold_length * i / 16 for i in range(1, 17)]
    values += [92, 94, 96, 96.35, 96.65, 96.88, LABEL_TOTAL]
    vertices, coordinates = [], []
    for distance in sorted(set(values)):
        inset = 0
        if distance < 1:
            inset = 1 - math.sqrt(max(0, 1 - (1 - distance) ** 2))
        elif distance > LABEL_TOTAL - 1:
            inset = 1 - math.sqrt(max(0, 1 - (distance - LABEL_TOTAL + 1) ** 2))
        if distance <= LABEL_FRONT:
            y, z = start_y - LABEL_FRONT + distance, start_z + radius
        elif distance < LABEL_FRONT + fold_length:
            angle = (distance - LABEL_FRONT) / radius
            y, z = start_y + radius * math.sin(angle), start_z + radius * math.cos(angle)
        else:
            y, z = start_y + radius, start_z - (distance - LABEL_FRONT - fold_length)
        for local_x in (-LABEL_WIDTH / 2 + inset, LABEL_WIDTH / 2 - inset):
            vertices.append((LABEL_X + local_x, y, z))
            coordinates.append((local_x / LABEL_WIDTH + .5, distance / LABEL_TOTAL))
    faces = [(i * 2, i * 2 + 1, i * 2 + 3, i * 2 + 2) for i in range(len(values) - 1)]
    obj = api.mesh('FrontLabel', vertices, faces, paper)
    uv = obj.data.uv_layers.new(name='ArtworkUV')
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
        for index in polygon.loop_indices:
            uv.data[index].uv = coordinates[obj.data.loops[index].vertex_index]
    obj['artworkAspectRatio'] = LABEL_WIDTH / LABEL_TOTAL
    obj['artworkOrientation'] = 'U viewer-left to viewer-right; V bottom-to-top across unfolded label'
    obj['unfoldedDimensionsMm'] = [LABEL_WIDTH, LABEL_TOTAL]
    obj['frontDimensionsMm'] = [LABEL_WIDTH, LABEL_FRONT]
    obj['topFoldMm'] = LABEL_TOTAL - LABEL_FRONT
    obj['artworkFoldV'] = LABEL_FRONT / LABEL_TOTAL
    return obj


def _grip(api, front, rear, gray):
    # The narrow left stripe is shallow below a deeper upper finger pocket.
    # Individual ribs have true relief; no painted dark stripes are used.
    _subtract(front, api.box('Front rib channel tool', (GRIP_X, 56.5, FRONT + .2),
                            (26.7, 114.0, 1.3), None, .45))
    upper = api.profile('Front finger recess tool',
                        api.rounded_points(27.0, 23.0, 1.25, GRIP_X, 125.1),
                        FRONT + 1, FRONT - 1.35, None, 0)
    _subtract(front, upper)
    for i in range(40):
        api.box(f'FrontGripRib_{i:02}', (GRIP_X, 13.7 + i * 2.5, FRONT - .25),
                (25.85, 1.65, .46), gray, .12)
    api.box('FrontGripFoot', (GRIP_X, 5.6, FRONT - .27), (25.85, 11.2, .50), gray, .65)
    for i in range(6):
        api.box(f'FrontUpperGripRib_{i:02}', (GRIP_X, 119.0 + i * 2.45, FRONT - .91),
                (25.6, 1.72, .90), gray, .15)
    # The same finger location is viewer-right from behind. Its channel extends
    # across the rear return but there is no full-height ribbed rear stripe.
    rear_tool = api.profile('Rear finger recess tool',
                           api.rounded_points(27.2, 23.2, 1.3, GRIP_X, 125.3),
                           BACK + 1.25, BACK - 2, None, 0)
    _subtract(rear, rear_tool)
    for i in range(5):
        api.box(f'RearUpperGripRib_{i:02}', (GRIP_X, 117.4 + i * 2.45, BACK + .80),
                (25.7, 1.7, .94), gray, .15)


def _screws(api, rear, gray, metal):
    # Five recessed slotted heads as photographed; not the later 3.8mm Gamebit
    # revision. Seat coordinates/depths are photo estimates, not factory CAD.
    positions = [(-52.0, 121.4), (52.0, 121.4),
                 (0, 70.5), (-52.0, 30.7), (52.0, 30.7)]
    for index, (x, y) in enumerate(positions):
        _subtract(rear, api.cylinder('Screw counterbore tool', (x, y, BACK + .4),
                                    2.65, 4.5, None, 48, 0))
        api.ring(f'ScrewBoss_{index}', (x, y, -4.2), 3.8, 1.25, 4.3, gray, 40)
        api.cylinder(f'ScrewShaft_{index}', (x, y, -5.6), 1.05, 3.2, metal, 24, .04)
        head = api.cylinder(f'SlottedScrew_{index}', (x, y, BACK + 1.12),
                            2.05, .90, metal, 48, .14)
        _apply(head)
        tool = api.box('Slotted drive tool', (x, y, BACK + .60), (4.7, .65, .63), None, .08)
        tool.rotation_euler.z = math.radians(25 + index * 39)
        _subtract(head, tool)
        head['drive'] = 'Single slot, early five-screw shell'


def _connector(api, front, rear, gray, pcb, gold):
    for shell in (front, rear):
        _subtract(shell, api.box('Recessed connector mouth tool', (0, 4.0, -1.0),
                                (100.5, 20.0, 10.75), None, .25))
    # The edge sits seven millimeters inside the leading front-shell lip.
    # NES-specific measurements: 1.2mm board, 93.5mm card edge, 2.50mm pitch.
    outline = [(-46.75, 7), (46.75, 7), (46.75, 21.5), (50, 21.5),
               (50, 47), (-50, 47), (-50, 21.5), (-46.75, 21.5)]
    api.profile('ConnectorPCB', outline, -2.375, -3.575, pcb, .08)
    for side, z in (('front', -2.361), ('rear', -3.589)):
        for index in range(36):
            api.box(f'Contact_{side}_{index:02}', (-43.75 + index * 2.50, 14.5, z),
                    (2.0, 12.0, .028), gold, 0)
    for x in (-50.7, 50.7):
        api.box('PCBGuide_' + str(x), (x, 26.0, -2.975), (1.0, 35, 3.1), gray, .12)


def _arrow(api, shell):
    points = [(-3.5, 34.0), (5.5, 34.0), (1.0, 26.0)]
    for index in range(3):
        a, b = points[index], points[(index + 1) % 3]
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        tool = api.box('Insertion arrow engraving tool',
                       ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, FRONT - .04),
                       (length + .1, .28, .32), None, .06)
        tool.rotation_euler.z = math.atan2(b[1] - a[1], b[0] - a[0])
        _subtract(shell, tool)


def build(api):
    root = api.reset('NES')
    gray = api.material('NES fine neutral gray ABS', (.265, .267, .275), .45)
    back_gray = api.material('NES rear neutral gray ABS', (.255, .258, .267), .47)
    paper = api.material('NES neutral front label paper', (.68, .68, .65), .68)
    back_paper = api.material('NES neutral rear label paper', (.22, .225, .23), .70)
    pcb = api.material('NES green epoxy PCB', (.018, .074, .032), .53)
    gold = api.material('NES gold plated contact pads', (.58, .32, .085), .31, .78)
    metal = api.material('NES dark steel slotted fasteners', (.10, .105, .115), .36, .78)
    normal, roughness = _packed_surface_maps()
    _exportable_abs(gray, normal, roughness['molded'], .22)
    _exportable_abs(back_gray, normal, roughness['molded'], .25)
    for material in (gray, back_gray, pcb, gold, metal):
        material.use_backface_culling = True
    for material in (paper, back_paper):
        material.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .18
    front = api.profile('FrontShell', _outline(), FRONT, -4.50, gray, .80)
    _apply(front)
    rear = _rear_cover(api, back_gray)
    # The inner core narrows at the lower shoulders too. A rectangular core
    # would incorrectly punch windows through the thin connector side walls.
    _subtract(front, api.profile('Front interior core tool',
                                _outline(114.0, 131.0, 7.0, 25.0, 100.5),
                                6.15, -7.15, None, .30))
    _subtract(rear, api.profile('Rear interior core tool',
                               _outline(110.5, 128.0, 10.0, 27.5, 96.0),
                               -.90, -6.70, None, .30))
    _fold_land(api, front)
    _grip(api, front, rear, gray)
    _arrow(api, front)
    # Back warning-label and molded mark lands are physically inset.
    _subtract(rear, api.profile('Rear warning label recess tool',
                               api.rounded_points(79.4, 31.9, 1.1, 0, 48.8),
                               BACK + .24, BACK - 1, None, 0))
    api.label('RearLabel', 78.5, 31.0, 0, 48.8, BACK + .205,
              back_paper, .8, rear=True)
    _subtract(rear, api.profile('Rear molded mark panel tool',
                               api.rounded_points(48.0, 13.5, .45, 0, 15.6),
                               BACK + .13, BACK - 1, None, 0))
    _screws(api, rear, gray, metal)
    _connector(api, front, rear, gray, pcb, gold)
    _folded_label(api, paper)
    _smooth(front)
    _smooth(rear)
    bpy.context.view_layer.update()
    for obj in root.children_recursive:
        if obj.type == 'MESH' and any(material in (gray, back_gray) for material in obj.data.materials):
            _surface_uv(obj)
    root['nominalDimensionsMm'] = [WIDTH, HEIGHT, DEPTH]
    root['physicalVariant'] = 'Western Nintendo Entertainment System early five-screw gray shell'
    root['referenceBasis'] = 'no$nes approximate shell drawing; NESdev measured PCB/pitch and approximate label sizes; original five-screw Super Mario Bros. product photographs'
    root['measurementLimits'] = 'Visualization reconstruction, not manufacturing CAD. Shell envelope is approximate; recesses, radii, screws and rib placements are estimated from photos.'
    root['referenceUrls'] = ['https://problemkaputt.de/everynes.htm',
                             'https://www.nesdev.org/wiki/NES_cartridge_dimensions',
                             'https://www.nesdev.org/wiki/Cartridge_connector',
                             'https://www.fenyxgames.com/product-page/super-mario-bros-nes-5-screw-1985-nintendo']
    root['connectorContactCount'] = 72
    root['connectorPitchMm'] = 2.5
    root['screwCount'] = 5
    root['surfaceTextureBasis'] = 'Original deterministic procedural ABS micrograin; packed normal and roughness images'
    root['omittedDetails'] = 'Hidden ROM electronics and molded Nintendo trademark lettering; rear molded mark land retained'
    return root
