"""Original parametric western Nintendo 64 Game Pak reconstruction.

The community-measured 116 x 76.6 x 18.5 mm envelope and label template
constrain this model. Mold radii, recess depths and hidden supports are visual
approximations from photographs, not factory CAD. No external mesh is used.
See docs/nintendo-64-reference-evidence.json for the evidence and its limits.
"""
import math

import bpy
import bmesh

from media_mega_drive import (
    _apply, _subtract, _smooth, _surface_uv, _sweep,
    _packed_surface_maps, _exportable_abs,
)


def _arc(points, cx, cy, radius, start, end, steps):
    for i in range(steps + 1):
        a = start + (end - start) * i / steps
        p = (cx + radius * math.cos(a), cy + radius * math.sin(a))
        if not points or math.dist(points[-1], p) > 1e-7:
            points.append(p)


def _capsule(width, height, y):
    points = []
    radius = height / 2
    _arc(points, width/2-radius, y, radius, -math.pi/2, math.pi/2, 32)
    _arc(points, -width/2+radius, y, radius, math.pi/2, 3*math.pi/2, 32)
    return points


def _arched_outline(width, height, bottom, top_radius, top_corner, bottom_corner):
    """CCW profile with tangent round corners and a true circular crown."""
    half = width / 2
    circle_y = bottom + height - top_radius
    corner_x = half - top_corner
    corner_y = circle_y + math.sqrt((top_radius - top_corner) ** 2 - corner_x ** 2)
    angle = math.atan2(corner_y - circle_y, corner_x)
    points = []
    _arc(points, half-bottom_corner, bottom+bottom_corner, bottom_corner, -math.pi/2, 0, 8)
    points.append((half, corner_y))
    _arc(points, corner_x, corner_y, top_corner, 0, angle, 8)
    _arc(points, 0, circle_y, top_radius, angle, math.pi-angle, 48)
    _arc(points, -corner_x, corner_y, top_corner, math.pi-angle, math.pi, 8)
    points.append((-half, bottom+bottom_corner))
    _arc(points, -half+bottom_corner, bottom+bottom_corner, bottom_corner, math.pi, 3*math.pi/2, 8)
    return points


def _outward(obj):
    """Close-solid winding is explicit, so exported backface culling is safe."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-8)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def _intersect(obj, tool):
    _apply(tool)
    modifier = obj.modifiers.new('Arched molding boundary', 'BOOLEAN')
    modifier.operation = 'INTERSECT'
    modifier.solver = 'EXACT'
    modifier.object = tool
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def _front_cross_section(flat_half_width, side_radius, depth, back):
    points = []
    for i in range(33):
        angle = math.pi/2 - math.pi/2*i/32
        points.append((-flat_half_width-side_radius*math.sin(angle), .10+depth*math.cos(angle)))
    points.append((flat_half_width, .10+depth))
    for i in range(1, 33):
        angle = math.pi/2*i/32
        points.append((flat_half_width+side_radius*math.sin(angle), .10+depth*math.cos(angle)))
    if back != .10:
        points += [(flat_half_width+side_radius, back), (-flat_half_width-side_radius, back)]
    return points


def _cheek_surface_cutter(api, points):
    """A shallow relief tool follows the rounded cheek instead of flattening it."""
    tool = api.profile('Lower front relief channel', points, 1.0, -.33, None, .05)
    _apply(tool)
    bm = bmesh.new()
    bm.from_mesh(tool.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    for vertex in bm.verts:
        x = abs(vertex.co.x / api.MM)
        fraction = max(0.0, min(1.0, (x-49.0)/9.0))
        vertex.co.z += (.10 + 9.15*math.sqrt(max(0.0, 1-fraction*fraction))) * api.MM
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(tool.data)
    bm.free()
    return tool


def _artwork(api, name, points, z, material, width, height, bottom, rear=False):
    indices = tuple(range(len(points)))
    obj = api.mesh(name, [(x, y, z) for x, y in points],
                   [tuple(reversed(indices)) if rear else indices], material)
    layer = obj.data.uv_layers.new(name='ArtworkUV')
    for face in obj.data.polygons:
        for li in face.loop_indices:
            co = obj.data.vertices[obj.data.loops[li].vertex_index].co
            u = co.x / api.MM / width + .5
            layer.data[li].uv = (1-u if rear else u, (co.y/api.MM-bottom)/height)
    obj['artworkAspectRatio'] = width / height
    obj['artworkOrientation'] = 'upright; U increases viewer-left to viewer-right'
    obj['labelDimensionsMm'] = [width, height]
    return obj


def _rear_brand(api, material):
    """Subtle molded wordmark, with a geometric capsule and editable text.

    The lettering is a font approximation; it is not traced OEM logo artwork.
    Text is converted before export to keep the GLB self-contained.
    """
    outline = _capsule(29.5, 6.6, 64.8)
    badge = api.profile('MoldedBrandCapsule', outline, -8.96, -9.11, material, 0)
    inner = api.profile('Brand border core', _capsule(28.7, 5.8, 64.8),
                        -8.8, -9.3, None, 0)
    _subtract(badge, inner)
    curve = bpy.data.curves.new('Molded wordmark lettering', 'FONT')
    curve.body = 'Nintendo'
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    curve.size = .0053
    curve.extrude = .000075
    curve.bevel_depth = .000015
    curve.bevel_resolution = 1
    curve.resolution_u = 5
    obj = bpy.data.objects.new('MoldedNintendoWordmark', curve)
    bpy.context.collection.objects.link(obj)
    obj.parent = api.ROOT
    obj.location = api.mm((0, 64.65, -9.03))
    obj.rotation_euler.y = math.pi
    curve.materials.append(material)
    bpy.context.view_layer.update()
    # Match the photographed wordmark's broad, low proportion rather than
    # assuming the font's metrics match Nintendo's original logotype.
    obj.scale.x = .0242 / max(obj.dimensions.x, 1e-6)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    obj.select_set(False)
    obj['detailBasis'] = 'Approximate molded wordmark; not an exact OEM logotype'


def build(api):
    root = api.reset('NINTENDO_64')
    gray = api.material('N64 fine satin gray molded plastic', (.285, .300, .288), .42)
    rear_gray = api.material('N64 finely textured rear gray plastic', (.285, .300, .288), .44)
    dark = api.material('N64 recessed black connector guide', (.014, .017, .016), .46)
    paper = api.material('N64 neutral unprinted front label', (.69, .68, .64), .59)
    rear_paper = api.material('N64 neutral rear warning label', (.045, .045, .043), .58)
    pcb = api.material('N64 green epoxy connector substrate', (.018, .105, .042), .46)
    gold = api.material('N64 gold plated connector contacts', (.52, .30, .075), .28, .78)
    screw_metal = api.material('N64 zinc security screw heads', (.30, .28, .22), .30, .78)
    for mat in (gray, rear_gray, dark, pcb, gold, screw_metal):
        mat.use_backface_culling = True
    normal, roughness = _packed_surface_maps()
    _exportable_abs(gray, normal, roughness['molded'], .22)
    _exportable_abs(rear_gray, normal, roughness['molded'], .29)

    # The same broad circular crown appears on both shell halves. The front
    # has rounded front edges; a narrow air gap expresses the assembly seam.
    outline = _arched_outline(116, 76.6, 0, 165, 2.4, 2.7)
    # The front cheeks roll all the way to the mid-shell seam. A rectangular
    # extrusion with a tiny edge bevel gives the wrong silhouette from below.
    front = _sweep(api, 'FrontShell', _front_cross_section(49.0, 9.0, 9.15, .10),
                   0, 76.6, gray, 0)
    _intersect(front, api.profile('Front arched outer boundary', outline, 12, -2, None, 0))
    edge = front.modifiers.new('Rounded crown and lower front lip', 'BEVEL')
    edge.width = .85 * api.MM
    edge.segments = 4
    edge.limit_method = 'ANGLE'
    edge.angle_limit = math.radians(24)
    rear = api.profile('RearShell', outline, -.10, -9.25, rear_gray, .65)
    _apply(front); _apply(rear)
    inner = _arched_outline(111.6, 72.2, 2.2, 162.8, 1.2, 1.2)
    front_core = _sweep(api, 'Front hollow core', _front_cross_section(47.3, 8.5, 7.55, -1.0),
                        2.2, 74.4, None, 0)
    _intersect(front_core, api.profile('Front hollow arched boundary', inner, 10, -2, None, 0))
    _subtract(front, front_core)
    _subtract(rear, api.profile('Rear hollow core', inner, 1, -7.70, None, .25))

    # The connector is genuinely open on the underside. The front lip and
    # deeper rear return remain continuous; no gold is outside the housing.
    for shell in (front, rear):
        mouth = api.box('Connector mouth core', (0, 2.7, -.30), (73.0, 10.4, 13.4), None, .40)
        _subtract(shell, mouth)

    # Molded longitudinal channels flank the front land, continuing over
    # the curved crown. These are subtracted grooves, not colored stripes.
    for x in (-35.4, 35.4):
        _subtract(front, api.box('Front shoulder groove', (x, 39, 9.25), (.62, 84, .76), None, .19))
        _subtract(front, api.box('Crown groove continuation', (x, 76.0, 4.7), (.62, 7.0, 9.5), None, .19))
        _subtract(rear, api.box('Rear molding groove', (x, 39, -9.25), (.48, 84, .56), None, .15))
        _subtract(rear, api.box('Rear crown groove continuation', (x, 76.0, -4.7), (.48, 7.0, 9.5), None, .15))

    # The tall label's top has a 325 mm diameter bow, with tangent corners.
    # The land is slightly larger than the paper, leaving a visible rim.
    label_points = _arched_outline(54.5, 62.5, 6.1, 162.5, 4, 3)
    land = _arched_outline(55.5, 63.5, 5.6, 163.0, 4.5, 3.5)
    _subtract(front, api.profile('Recessed front label land', land, 10.0, 8.88, None, .07))
    _artwork(api, 'FrontLabel', label_points, 8.925, paper, 54.5, 62.5, 6.1)

    # Curved lower outer relief is a pair of shallow molded channels. Their
    # shape is inferred from real front/underside photos, not a factory die.
    path = [(49.7, -1), (50.3, -1), (50.3, 17.8), (50.45, 18.7),
            (50.9, 19.3), (51.7, 19.8), (54.1, 20.7), (56.6, 22.0),
            (59, 23.1), (59, 23.7), (56.4, 22.6), (53.8, 21.3),
            (51.4, 20.4), (50.5, 19.9), (49.9, 19.0), (49.7, 17.8)]
    for sign in (-1, 1):
        pts = [(sign*x, y) for x, y in path]
        if sign < 0:
            pts.reverse()
        _subtract(front, _cheek_surface_cutter(api, pts))

    # Rear paper and molded logo occupy separate shallow physical recesses.
    rear_land = api.rounded_points(82.0, 40.0, 2.8, y=34.2, steps=12)
    _subtract(rear, api.profile('Rear warning land', rear_land, -8.91, -10, None, .05))
    api.label('RearLabel', 80.9, 38.9, 0, 34.2, -8.955, rear_paper, 2.3, rear=True)
    brand_land = _capsule(30.5, 7.6, 64.8)
    _subtract(rear, api.profile('Rear wordmark land', brand_land, -8.98, -10, None, .04))
    _rear_brand(api, rear_gray)

    # Two real recessed 3.8 mm gamebit-style heads. A six-lobed external
    # drive is cut into each head; using a Phillips slot would be inaccurate.
    for x in (-35.4, 35.4):
        _subtract(rear, api.cylinder('Security screw counterbore', (x, 66.0, -8.65), 3.05, 3.5, None, 48, .22))
        api.cylinder('InternalScrewBoss', (x, 66, -4.1), 3.50, 7.1, rear_gray, 32, .08)
        api.cylinder('SecurityScrewShank', (x, 66, -7.0), 1.0, 2.4, screw_metal, 24, .05)
        head = api.cylinder('SecurityScrewHead', (x, 66, -8.20), 1.95, .82, screw_metal, 48, .25)
        _apply(head)
        for i in range(6):
            a = i * math.pi / 3
            _subtract(head, api.cylinder('Gamebit external lobe core',
                                        (x+1.95*math.cos(a), 66+1.95*math.sin(a), -8.2),
                                        .36, 1.3, None, 12, 0))

    # NTSC-U/C rear molding has the large keys at the OUTER corners. PAL/JPN
    # photos with inboard stepped keys are deliberately not used for this
    # region-specific feature. The intact rolled front shell sits behind it.
    for sign in (-1, 1):
        x = sign * 56.7
        _subtract(rear, api.box('USA outer corner key core', (x, 3.45, -5), (12.2, 14.1, 12), None, 1.7))
        _subtract(rear, api.box('Rear small lower latch core', (sign*45.2, .15, -7.5), (6.0, 4.7, 5.0), None, .20))
        api.box('FrontLowerKeyReturn', (sign*54.4, 5.0, -3.35), (6.9, 10.0, 6.9), gray, .65)
        # Retention tabs and small local lower seams visible from beneath.
        api.box('LowerShellLatch', (sign*37.5, 2.7, -3.8), (2.0, 3.9, 2.3), rear_gray, .18)

    # Black PBT-like board guide, recessed from the mouth. The visible
    # motherboard is limited to its connector tongue; unseen electronics
    # are deliberately absent from this closed visualization asset.
    api.box('ConnectorPCB', (0, 13.2, .65), (65.0, 21.0, 1.6), pcb, .12)
    for side in (-1, 1):
        # 2.50 mm pitch is corroborated by original adapter PCB documentation.
        for i in range(25):
            api.box(f'Contact_{side}_{i+1:02d}', (-30+i*2.5, 6.0, .65+side*.814),
                    (1.70, 6.0, .028), gold, 0)
    api.box('ConnectorGuideBackRail', (0, 9.5, -3.25), (70.0, 2.6, 2.2), dark, .22)
    for sign in (-1, 1):
        api.box('ConnectorGuideSide', (sign*34.0, 6.7, -.10), (2.6, 9.0, 6.7), dark, .25)
    for x in (-27.5, -17.5, 17.5, 27.5):
        api.box('ConnectorGuideRetainer', (x, 5.3, -4.3), (4.1, 3.0, 1.0), dark, .16)

    # Keep labels' UV0 isolated from the physically scaled plastic maps.
    # Opaque solid winding is validated before enabling export culling.
    bpy.context.view_layer.update()
    for obj in root.children_recursive:
        if obj.type != 'MESH' or obj.name in ('FrontLabel', 'RearLabel'):
            continue
        _apply(obj)
        # Boolean intersection can append an empty cutter material slot.
        # Every surface of the front molding must retain its gray plastic.
        if obj.name == 'FrontShell':
            obj.data.materials.clear()
            obj.data.materials.append(gray)
            for polygon in obj.data.polygons:
                polygon.material_index = 0
        _outward(obj)
        _smooth(obj)
        if any(mat in (gray, rear_gray) for mat in obj.data.materials):
            _surface_uv(obj)

    root['nominalDimensionsMm'] = [116.0, 76.6, 18.5]
    root['physicalVariant'] = 'NTSC-U/C gray Nintendo 64 Game Pak NUS-006; neutral artwork'
    root['referenceBasis'] = 'Community measured envelope and label template; original cartridge photographs and teardown; 50-contact pinout and 2.50 mm adapter documentation'
    root['measurementLimits'] = 'Envelope and label size are community values, not factory CAD; shell radii, recesses, screw centers and hidden details are visual estimates'
    root['connectorContactCount'] = 50
    root['connectorPitchMm'] = 2.5
    root['surfaceTextureBasis'] = 'Original modest procedural molded-plastic micrograin; packed normal and roughness maps, physical 8 mm tile'
    root['referenceUrls'] = [
        'https://consolemods.org/wiki/Dimensions_for_Game_Cartridges',
        'https://consolemods.org/wiki/Cart_Labels',
        'https://www.ifixit.com/Guide/Disassembling+Nintendo+64+Cartridge/3583',
        'https://commons.wikimedia.org/wiki/File:N64-Game-Cartridge.jpg',
        'https://consolemods.org/wiki/N64:Connector_Pinouts',
        'https://github.com/bigbass1997/n64-ext-adapter',
    ]
    return root
