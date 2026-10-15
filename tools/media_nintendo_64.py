"""Original parametric western Nintendo 64 Game Pak reconstruction.

The community-measured 116 x 76.6 x 18.5 mm envelope and label template
constrain this model. Mold radii, recess depths and hidden supports are visual
approximations from photographs, not factory CAD. No external mesh is used.
See docs/nintendo-64-reference-evidence.json for the evidence and its limits.
"""
import math
import re

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
    _arc(points, 0, circle_y, top_radius, angle, math.pi-angle, 96)
    _arc(points, -corner_x, corner_y, top_corner, math.pi-angle, math.pi, 8)
    points.append((-half, bottom+bottom_corner))
    _arc(points, -half+bottom_corner, bottom+bottom_corner, bottom_corner, math.pi, 3*math.pi/2, 8)
    return points


def _outward(obj):
    """Close-solid winding is explicit, so exported backface culling is safe."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-8)
    # Coplanar SVG letter floors can leave a long boundary opposite several
    # shorter edges. Split that T-junction before welding the shared floor.
    for _ in range(32):
        boundary = [edge for edge in bm.edges if edge.is_boundary]
        candidates = {vertex for edge in boundary for vertex in edge.verts}
        split = None
        for edge in boundary:
            a, b = edge.verts
            direction = b.co-a.co
            if direction.length_squared < 1e-18:
                continue
            for vertex in candidates:
                if vertex in edge.verts:
                    continue
                t = (vertex.co-a.co).dot(direction)/direction.length_squared
                if 1e-5 < t < 1-1e-5 and (a.co+t*direction-vertex.co).length < 1e-9:
                    split = (edge, a, t, vertex.co.copy())
                    break
            if split:
                break
        if not split:
            break
        edge, endpoint, t, coordinate = split
        _, vertex = bmesh.utils.edge_split(edge, endpoint, t)
        vertex.co = coordinate
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
    for i in range(65):
        angle = math.pi/2 - math.pi/2*i/64
        points.append((-flat_half_width-side_radius*math.sin(angle), .10+depth*math.cos(angle)))
    points.append((flat_half_width, .10+depth))
    for i in range(1, 65):
        angle = math.pi/2*i/64
        points.append((flat_half_width+side_radius*math.sin(angle), .10+depth*math.cos(angle)))
    if back != .10:
        points += [(flat_half_width+side_radius, back), (-flat_half_width-side_radius, back)]
    return points


def _cheek_surface_cutter(api, points):
    """A shallow relief tool follows the rounded cheek instead of flattening it."""
    tool = api.profile('Lower front relief channel', points, 1.0, -.26, None, .04)
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


# Official Nintendo website vector, inspected against the physical molded mark.
# Nintendo trademark artwork is excluded from the model geometry license.
# Source: https://www.nintendo.com/us/ (NintendoRacetrackLogoIcon, 2026-10-15).
NINTENDO_RACETRACK_PATH = 'M17.945 14.157l-4.85-7.838H9.609V17.59h3.486V9.752l4.85 7.838h3.456V6.32h-3.486l.03 7.837zm27.554-4.04V8.993H43.68v-1.52h-3.395v1.52h-1.849v1.124h1.85v7.473h3.394v-7.473h1.82zM23.341 17.56h3.364v-7.474h-3.364v7.474zm0-8.932h3.395V6.319H23.34v2.309zm59.17.942c-2.728 0-4.941 1.883-4.941 4.192s2.213 4.193 4.94 4.193c2.729 0 4.942-1.884 4.942-4.193 0-2.309-2.213-4.192-4.941-4.192zm1.364 5.772c0 1.185-.698 1.67-1.364 1.67-.667 0-1.395-.485-1.395-1.67v-3.16c0-1.184.697-1.67 1.395-1.67.666 0 1.364.486 1.364 1.67v3.16zm-10.73-4.891c-.547-.304-1.123-.608-1.91-.669-2.426-.212-4.305 1.945-4.305 3.92 0 2.612 2 3.554 2.304 3.706 1.152.516 2.607.547 3.88-.274v.426h3.334V6.32h-3.334c.03 0 .03 2.4.03 4.13zm.03 3.342v1.336c0 1.155-.789 1.458-1.334 1.458-.546 0-1.334-.303-1.334-1.458v-2.673c0-1.155.788-1.458 1.334-1.458.515 0 1.333.303 1.333 1.458v1.337zM34.616 9.752c-1.122.03-2.031.516-2.698 1.124v-.79h-3.365v7.474h3.365v-4.922c0-.638.697-1.367 1.607-1.367.909 0 1.546.73 1.546 1.367v4.922h3.364v-4.071c0-2.947-2.546-3.798-3.82-3.737zm27.433 0a4.075 4.075 0 0 0-2.698 1.124v-.79h-3.365v7.474h3.365v-4.922c0-.638.697-1.367 1.606-1.367.91 0 1.546.73 1.546 1.367v4.922h3.365v-4.071c0-2.947-2.546-3.798-3.82-3.737zm-7.063 4.101c0-2.309-2.243-4.253-4.971-4.253-2.759 0-4.972 1.884-4.972 4.193 0 2.308 2.213 4.192 4.972 4.192 2.273 0 4.213-1.306 4.789-3.068H51.44v.455c0 1.367-.91 1.671-1.394 1.671-.515 0-1.425-.304-1.425-1.67v-1.55l6.366.03zm-6.123-2.643a1.391 1.391 0 0 1 1.182-.668c.455 0 .91.213 1.182.668.212.365.212.82.212 1.458H48.62c0-.637.03-1.063.243-1.458zm39.921-3.493c0-.365-.272-.547-.818-.547h-.758v1.914h.455v-.79h.242l.364.79h.515l-.424-.851c.273-.091.424-.273.424-.516zm-.879.273h-.242v-.547h.212c.273 0 .424.091.424.274 0 .212-.12.273-.394.273zm.03-1.58c-.94 0-1.727.79-1.727 1.732s.788 1.732 1.728 1.732 1.727-.79 1.727-1.732a1.73 1.73 0 0 0-1.727-1.732zm0 3.13a1.413 1.413 0 0 1-1.394-1.398c0-.76.637-1.398 1.395-1.398.757 0 1.394.638 1.394 1.398 0 .76-.637 1.397-1.394 1.397zM84.148 0H12.64C5.062-.03 0 5.438 0 11.97c0 6.53 5.062 11.939 12.67 11.939h71.508c7.608 0 12.67-5.408 12.67-11.94C96.818 5.44 91.726 0 84.148 0zm-.03 20.993H12.671c-6.033.03-9.7-4.041-9.7-9.023 0-4.983 3.698-8.993 9.7-9.023h71.446c6.002 0 9.7 4.04 9.7 9.023 0 4.982-3.668 9.023-9.7 9.023z'


def _svg_contours(path):
    """Sample the official closed SVG outlines; retain their nested holes."""
    tokens = re.findall(r'[a-zA-Z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', path)
    contours, points = [], []
    index, command = 0, None
    current = start = complex(0, 0)
    previous_control = None
    previous_command = None

    def append(value):
        if not points or abs(value-points[-1]) > 1e-8:
            points.append(value)

    def arc(a, rx, ry, degrees, large, sweep, b):
        rx, ry = abs(rx), abs(ry)
        if not rx or not ry or abs(a-b) < 1e-8:
            append(b)
            return
        phi = math.radians(degrees)
        rotation = complex(math.cos(phi), math.sin(phi))
        q = (a-b)/2/rotation
        ratio = q.real*q.real/(rx*rx) + q.imag*q.imag/(ry*ry)
        if ratio > 1:
            rx *= math.sqrt(ratio)
            ry *= math.sqrt(ratio)
        numerator = max(0, rx*rx*ry*ry-rx*rx*q.imag*q.imag-ry*ry*q.real*q.real)
        denominator = rx*rx*q.imag*q.imag+ry*ry*q.real*q.real
        factor = math.sqrt(numerator/denominator) * (-1 if bool(large)==bool(sweep) else 1)
        c = complex(factor*rx*q.imag/ry, -factor*ry*q.real/rx)
        center = c*rotation+(a+b)/2
        u = complex((q.real-c.real)/rx, (q.imag-c.imag)/ry)
        v = complex((-q.real-c.real)/rx, (-q.imag-c.imag)/ry)
        angle = math.atan2(u.imag, u.real)
        delta = math.atan2((v/u).imag, (v/u).real)
        if sweep and delta < 0:
            delta += 2*math.pi
        if not sweep and delta > 0:
            delta -= 2*math.pi
        steps = max(3, math.ceil(abs(delta)/(math.pi/18)))
        for i in range(1, steps+1):
            t = angle+delta*i/steps
            append(center+complex(rx*math.cos(t), ry*math.sin(t))*rotation)

    sizes = {'M':2, 'L':2, 'H':1, 'V':1, 'C':6, 'S':4, 'A':7}
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        upper = command.upper()
        if upper == 'Z':
            if points and abs(points[-1]-points[0]) < 1e-8:
                points.pop()
            contours.append(points)
            points = []
            current = start
            previous_control = None
            previous_command = upper
            command = None
            continue
        values = [float(value) for value in tokens[index:index+sizes[upper]]]
        index += sizes[upper]
        offset = current if command.islower() else 0
        if upper in ('M', 'L'):
            current = complex(*values)+offset
            append(current)
            if upper == 'M':
                start = current
                command = 'l' if command.islower() else 'L'
        elif upper == 'H':
            current = complex(values[0] + (current.real if command.islower() else 0), current.imag)
            append(current)
        elif upper == 'V':
            current = complex(current.real, values[0] + (current.imag if command.islower() else 0))
            append(current)
        elif upper in ('C', 'S'):
            a = current
            if upper == 'C':
                b, c, d = [complex(*values[j:j+2])+offset for j in (0, 2, 4)]
            else:
                b = 2*a-previous_control if previous_command in ('C', 'S') else a
                c, d = [complex(*values[j:j+2])+offset for j in (0, 2)]
            for i in range(1, 13):
                t = i/12
                append((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d)
            current, previous_control = d, c
        elif upper == 'A':
            destination = complex(values[5], values[6])+offset
            arc(current, *values[:5], destination)
            current = destination
        previous_command = upper
    return contours


def _rear_brand(api, rear):
    """Cut the actual broad wordmark and surrounding moat into the rear shell.

    Macro photographs show recessed letters on a shallow central land. The
    0.1.0 generic raised font and thin extra outline had the opposite relief.
    Official vector letterforms are used; depth and fit remain photo estimates.
    """
    land = _capsule(31.2, 8.2, 64.8)
    _subtract(rear, api.profile('Wordmark shallow outer land', land, -9.10, -10, None, .10))
    curve = bpy.data.curves.new('Official Nintendo recessed outlines', 'CURVE')
    curve.dimensions = '2D'
    curve.fill_mode = 'BOTH'
    curve.extrude = .00055
    curve.resolution_u = 1
    factor = 30.5/96.848
    for contour in _svg_contours(NINTENDO_RACETRACK_PATH):
        spline = curve.splines.new('POLY')
        spline.points.add(len(contour)-1)
        for point, value in zip(spline.points, contour):
            point.co = (-(value.real-48.424)*factor*api.MM,
                        (64.8+(11.9545-value.imag)*factor)*api.MM, 0, 1)
        spline.use_cyclic_u = True
    tool = bpy.data.objects.new('Nintendo deboss cutter', curve)
    bpy.context.collection.objects.link(tool)
    tool.location.z = -.00935
    bpy.ops.object.select_all(action='DESELECT')
    tool.select_set(True)
    bpy.context.view_layer.objects.active = tool
    bpy.ops.object.convert(target='MESH')
    _outward(tool)
    _subtract(rear, tool)


def _molded_shading(obj, edge_radius=.055):
    """Round cut rims and split only real sharp corners, not curved patches."""
    if edge_radius:
        bevel = obj.modifiers.new('Fine molded recess lip radius', 'BEVEL')
        bevel.width = edge_radius*.001
        bevel.segments = 3
        bevel.limit_method = 'ANGLE'
        bevel.angle_limit = math.radians(35)
        bevel.harden_normals = True
        _apply(obj)
        _outward(obj)
    for face in obj.data.polygons:
        face.use_smooth = True
    obj.data.set_sharp_from_angle(angle=math.radians(45))
    normal = obj.modifiers.new('Continuous molded surface normals', 'WEIGHTED_NORMAL')
    normal.keep_sharp = True
    normal.weight = 50
    _apply(obj)


def _gamebit_head(api, x, material):
    """Rounded six-lobed external Gamebit head, recessed below its bore rim."""
    levels = [(-7.01, 1.72, .18), (-7.33, 1.98, .18), (-7.59, 1.94, .18),
              (-7.80, 1.72, .09), (-7.95, 1.25, .015), (-8.01, .65, 0)]
    around = 96
    vertices = []
    for z, radius, notch in levels:
        for i in range(around):
            angle = 2*math.pi*i/around
            lobe = 1-notch*(.5+.5*math.cos(6*angle))**2
            r = radius*lobe
            vertices.append((x+r*math.cos(angle), 66+r*math.sin(angle), z))
    faces = [tuple(reversed(range(around)))]
    for row in range(len(levels)-1):
        for i in range(around):
            j = (i+1)%around
            faces.append((row*around+i,row*around+j,(row+1)*around+j,(row+1)*around+i))
    pole = len(vertices)
    vertices.append((x, 66, -8.03))
    for i in range(around):
        faces.append(((len(levels)-1)*around+i,
                      (len(levels)-1)*around+(i+1)%around, pole))
    obj = api.mesh('DomedGamebitHead', vertices, faces, material)
    _outward(obj)
    return obj


def build(api):
    root = api.reset('NINTENDO_64')
    gray = api.material('N64 fine satin gray molded plastic', (.285, .300, .288), .42)
    rear_gray = api.material('N64 finely textured rear gray plastic', (.285, .300, .288), .44)
    dark = api.material('N64 recessed black connector guide', (.014, .017, .016), .46)
    paper = api.material('N64 neutral unprinted front label', (.69, .68, .64), .59)
    rear_paper = api.material('N64 neutral rear warning label', (.045, .045, .043), .58)
    pcb = api.material('N64 green epoxy connector substrate', (.018, .105, .042), .46)
    substrate = api.material('N64 unmasked tan FR4 connector tongue', (.24, .105, .022), .48)
    gold = api.material('N64 gold plated connector contacts', (.52, .30, .075), .28, .78)
    screw_metal = api.material('N64 warm zinc plated security screw heads', (.43, .32, .14), .34, .83)
    for mat in (gray, rear_gray, dark, pcb, substrate, gold, screw_metal):
        mat.use_backface_culling = True
    normal, roughness = _packed_surface_maps()
    _exportable_abs(gray, normal, roughness['molded'], .38)
    _exportable_abs(rear_gray, normal, roughness['molded'], .68)

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
    centerline = [(50.0, -1.0), (50.0, 17.6)]
    a, b, c, d = complex(50,17.6), complex(50,20.3), complex(53.3,20.0), complex(59,23.6)
    for i in range(1, 25):
        t = i/24
        value = (1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
        centerline.append((value.real,value.imag))
    borders = [[], []]
    for i, (x, y) in enumerate(centerline):
        lo, hi = centerline[max(0,i-1)], centerline[min(len(centerline)-1,i+1)]
        dx, dy = hi[0]-lo[0], hi[1]-lo[1]
        length = math.hypot(dx,dy)
        for j, sign in enumerate((-1,1)):
            borders[j].append((x+sign*.21*dy/length,y-sign*.21*dx/length))
    path = borders[0]+list(reversed(borders[1]))
    for sign in (-1, 1):
        pts = [(sign*x, y) for x, y in path]
        if sign < 0:
            pts.reverse()
        _subtract(front, _cheek_surface_cutter(api, pts))

    # Rear paper and molded logo occupy separate shallow physical recesses.
    rear_land = api.rounded_points(82.0, 40.0, 2.8, y=34.2, steps=12)
    _subtract(rear, api.profile('Rear warning land', rear_land, -8.91, -10, None, .05))
    api.label('RearLabel', 80.9, 38.9, 0, 34.2, -8.955, rear_paper, 2.3, rear=True)
    _rear_brand(api, rear)

    # Two recessed Gamebit-style heads, with rounded centers and six external
    # drive notches. The teardown's 3.8 mm is a driver size, not head metrology.
    for x in (-35.4, 35.4):
        _subtract(rear, api.cylinder('Security screw counterbore', (x, 66.0, -8.65), 3.05, 3.5, None, 48, .22))
        api.cylinder('InternalScrewBoss', (x, 66, -3.8), 3.50, 6.4, rear_gray, 32, .08)
        api.cylinder('SecurityScrewShank', (x, 66, -6.6), 1.0, 1.8, screw_metal, 24, .05)
        _gamebit_head(api, x, screw_metal)

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
    api.box('ConnectorPCB', (0, 13.2, .65), (65.0, 21.0, 1.6), substrate, .22)
    # Solder mask stops at the inner end of the fingers; the exposed tongue
    # is tan/brown FR4 in the original Nintendo boards photographed here.
    for side in (-1, 1):
        api.box('PCBGreenSolderMask', (0,16.8,.65+side*.803), (64.55,13.1,.012), pcb, 0)
    for side in (-1, 1):
        # 2.50 mm pitch is corroborated by original adapter PCB documentation.
        for i in range(25):
            api.box(f'Contact_{side}_{i+1:02d}', (-30+i*2.5, 6.0, .65+side*.814),
                    (1.70, 6.0, .028), gold, 0)
    api.box('ConnectorGuideRearWall', (0, 6.6, -5.85), (70.0, 10.0, .95), dark, .12)
    api.box('ConnectorGuideFrontWall', (0, 6.6, 4.45), (70.0, 10.0, .95), dark, .12)
    for sign in (-1, 1):
        api.box('ConnectorGuideSide', (sign*34.0, 6.6, -.70), (2.6, 10.0, 10.3), dark, .18)
    for x in (-27.5, -17.5, 17.5, 27.5):
        api.box('ConnectorGuideRetainer', (x, 2.4, -5.05), (4.1, 1.6, 1.5), dark, .12)

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
        if obj.name in ('FrontShell', 'RearShell'):
            _molded_shading(obj)
        elif obj.name.startswith('DomedGamebitHead'):
            _molded_shading(obj, 0)
        else:
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
        'https://www.nintendo.com/us/',
    ]
    return root
