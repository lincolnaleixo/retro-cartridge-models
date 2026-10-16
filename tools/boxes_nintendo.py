"""Neutral, articulated western Nintendo retail cartons.

Coordinates: meters, X right, Y up, +Z artwork front; bottom-center pivot.
The millimeter dimensions and die cuts are visualization approximations, not
manufacturing drawings. See docs/nintendo-box-reference-evidence.json.
Build through create_media_models' API. This module does not export files.
"""
import json
import math

import bpy
from mathutils import Vector

CONFIG = {
    'nes': {'size': (128.0, 179.0, 24.0), 'board': .45,
            'title': 'NES retail carton', 'insert': 'foam spacer and black sleeve'},
    'snes': {'size': (179.0, 128.0, 31.0), 'board': .45,
             'title': 'Super Nintendo retail carton', 'insert': 'folded white tray'},
    'nintendo-64': {'size': (179.0, 128.0, 31.0), 'board': .45,
                    'title': 'Nintendo 64 retail carton', 'insert': 'folded white tray'},
}


def _localize(obj, parent):
    """The API creates world coordinates; retain them after parenting."""
    bpy.context.view_layer.update()
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world
    return obj


class Carton:
    def __init__(self, api, console):
        self.api = api
        self.console = console
        self.config = CONFIG[console]
        self.w, self.h, self.d = self.config['size']
        self.t = self.config['board']
        self.root = api.reset(console.replace('-', '_').title() + 'Box')
        self.root['nominalDimensionsMm'] = list(self.config['size'])
        self.root['boardThicknessMm'] = self.t
        self.root['construction'] = self.config['insert']
        self.root['condition'] = 'pristine; clean stock, no printed wear or aging'
        self.root['referenceEvidence'] = 'docs/nintendo-box-reference-evidence.json'
        self.root['measurementStatus'] = 'Approximate visualization; protector-fit envelope, inferred die cuts'
        self.root['containsGameMedia'] = False
        self.root['initialPose'] = 'Closed'
        self.hinges = []
        self.slots = []
        self.edge = api.material('UncoatedCardCutEdges', (.56, .525, .46), .88)
        self.inner = api.material('UnprintedInnerPaper', (.84, .824, .78), .8)
        self.white = api.material('CleanCoatedPaper', (.92, .92, .89), .4)
        self.tray_mat = api.material('CleanWhiteInsertBoard', (.9, .897, .868), .68)
        self.crease = api.material('FoldCreasePaper', (.69, .67, .61), .77)
        self.art_mats = {slot: api.material('BoxArtwork' + slot, (.91, .915, .90), .36)
                         for slot in ('Front', 'Back', 'SpineLeft', 'SpineRight', 'Top', 'Bottom')}
        for mat in self.art_mats.values():
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            bsdf.inputs['Coat Weight'].default_value = .08
            bsdf.inputs['Coat Roughness'].default_value = .42

    def hinge(self, name, pivot, axis, angle, phase, parent=None):
        parent = parent or self.root
        hinge = self.api.empty(name, pivot)
        _localize(hinge, parent)
        hinge['boxHinge'] = True
        hinge['hingeAxis'] = axis
        hinge['closedAngleDegrees'] = 0.0
        hinge['openAngleDegrees'] = float(angle)
        hinge['animationPhase'] = float(phase)
        hinge['rotationAxis'] = axis
        hinge['closedRotationDegrees'] = 0.0
        hinge['openRotationDegrees'] = float(angle)
        self.hinges.append({'name': name, 'axis': axis, 'closedAngleDegrees': 0,
                            'openAngleDegrees': angle, 'animationPhase': phase})
        return hinge

    def slab(self, name, points, normal, thickness=None, parent=None, outer=None):
        """An outward-facing polygon with inward thickness and separate stock faces."""
        thickness = self.t if thickness is None else thickness
        n = Vector(normal).normalized()
        outer_points = [Vector(p) for p in points]
        # All callers supply a visible-front outline; enforce normal winding.
        if (outer_points[1] - outer_points[0]).cross(outer_points[2] - outer_points[0]).dot(n) < 0:
            outer_points.reverse()
        inner_points = [p - n * thickness for p in outer_points]
        count = len(points)
        verts = outer_points + inner_points
        faces = [tuple(range(count)), tuple(reversed(range(count, 2 * count)))]
        faces.extend((i, count + i, count + (i + 1) % count, (i + 1) % count)
                     for i in range(count))
        obj = self.api.mesh(name, verts, faces, outer or self.white, bevel=.055)
        obj.data.materials.append(self.inner)
        obj.data.materials.append(self.edge)
        obj.data.polygons[1].material_index = 1
        for face in obj.data.polygons[2:]:
            face.material_index = 2
        obj['paperThicknessMm'] = thickness
        obj['surfaceRole'] = 'board; unprinted reverse and exposed cut edges'
        return _localize(obj, parent or self.root)

    def art(self, slot, corners, parent=None, uv=None, name=None):
        """Corners are bottom-left, bottom-right, top-right, top-left as seen outside."""
        obj = self.api.mesh(name or ('Artwork' + slot), corners, [(0, 1, 2, 3)], self.art_mats[slot])
        layer = obj.data.uv_layers.new(name='ArtworkUV')
        coords = uv or [(0, 0), (1, 0), (1, 1), (0, 1)]
        for loop in obj.data.polygons[0].loop_indices:
            layer.data[loop].uv = coords[obj.data.loops[loop].vertex_index]
        obj['artworkSlot'] = slot
        obj['artworkOrientation'] = 'upright when viewed from the outside; U right, V up'
        obj['artworkAspectRatio'] = (Vector(corners[1]) - Vector(corners[0])).length / (Vector(corners[3]) - Vector(corners[0])).length
        obj['surfaceRole'] = 'exterior print only; inner paper is separate'
        self.slots.append(obj.name)
        return _localize(obj, parent or self.root)

    def crease_line(self, name, start, end, parent=None):
        """A subtle physical scored-fold radius; not a painted damage mark."""
        a, b = Vector(start), Vector(end)
        direction = b - a
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=.075 * .001,
            depth=direction.length * .001, location=(a + b) * .0005)
        obj = bpy.context.object
        obj.name = name
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = direction.to_track_quat('Z', 'Y')
        obj.data.materials.append(self.crease)
        return _localize(obj, parent or self.root)

    def fixed_front_back(self):
        x, h, z = self.w / 2, self.h, self.d / 2
        # Leave room for the end flaps and their rounded fold stock.
        e = .11
        for front, sign in ((True, 1), (False, -1)):
            if not front and self.console == 'nes':
                self.nes_hangtab_back()
                continue
            slot = 'Front' if front else 'Back'
            corners = [(-x + e, e, sign * (z - .012)), (x - e, e, sign * (z - .012)),
                       (x - e, h - e, sign * (z - .012)), (-x + e, h - e, sign * (z - .012))]
            self.slab(slot + 'PaperBoard', corners, (0, 0, sign))
            art_x = [-x + e, x - e] if front else [x - e, -x + e]
            self.art(slot, [(art_x[0], e, sign * z), (art_x[1], e, sign * z),
                            (art_x[1], h - e, sign * z), (art_x[0], h - e, sign * z)])

    def nes_hangtab_back(self):
        """Flush early-US integrated hanger, with the rear print continuing over it."""
        x, h, z = self.w / 2, self.h, -self.d / 2
        half, bottom, gap = 20.5, self.h - 29.5, .09
        hinge = self.hinge('RearHangtabHinge', (0, h - .11, z + .03), 'X', 0, .0)
        hinge['inspectionOpenAngleDegrees'] = 180.0
        hinge['articulationPurpose'] = 'Optional retail hanger; stays flush during normal box opening'
        self.slab('RearIntegratedHangtabBoard', [(-half + gap, bottom + gap, z + .042),
            (half - gap, bottom + gap, z + .042), (half - gap, h - .11, z + .042),
            (-half + gap, h - .11, z + .042)], (0, 0, -1), parent=hinge)
        # The three surrounding boards leave genuine thin die-cut gaps along the
        # hanging tongue. All artwork uses one continuous rear-face UV field.
        panels = [(-x + .11, x - .11, .11, bottom - gap),
                  (-x + .11, -half - gap, bottom - gap, h - .11),
                  (half + gap, x - .11, bottom - gap, h - .11)]
        verts, faces = [], []
        for index, (lo, hi, y0, y1) in enumerate(panels):
            self.slab('RearSurroundBoard' + str(index), [(lo, y0, z + .042),
                (hi, y0, z + .042), (hi, y1, z + .042), (lo, y1, z + .042)], (0, 0, -1))
            offset = len(verts)
            verts.extend([(hi, y0, z + .03), (lo, y0, z + .03),
                          (lo, y1, z + .03), (hi, y1, z + .03)])
            faces.append(tuple(offset + i for i in range(4)))
        obj = self.api.mesh('ArtworkBack', verts, faces, self.art_mats['Back'])
        uv = obj.data.uv_layers.new(name='ArtworkUV')
        for poly in obj.data.polygons:
            for loop in poly.loop_indices:
                xx, yy, _ = verts[obj.data.loops[loop].vertex_index]
                uv.data[loop].uv = ((x - xx) / self.w, yy / h)
        obj['artworkSlot'] = 'Back'
        obj['artworkOrientation'] = 'upright external view; continuous rear UV field around hanging tongue'
        obj['artworkAspectRatio'] = self.w / h
        self.slots.append(obj.name)
        hanger_corners = [(half - gap, bottom + gap, z + .03), (-half + gap, bottom + gap, z + .03),
                          (-half + gap, h - .11, z + .03), (half - gap, h - .11, z + .03)]
        hanger_art = self.art('Back', hanger_corners, parent=hinge, name='ArtworkBackHangtab',
                 uv=[((x - xx) / self.w, yy / h) for xx, yy, _ in hanger_corners])
        hanger_art['artworkAspectRatio'] = self.w / h
        # Unpunched hook aperture: a shallow continuous die score, not dirt/wear.
        # Slot dimensions and rounded lower lobe are inferred from the specimen.
        cy = h - 10.5
        pts = [(-11, cy + 1.7), (11, cy + 1.7)]
        pts.extend((11 + 1.7 * math.cos(a), cy + 1.7 * math.sin(a))
                   for a in [math.pi / 2 - i * math.pi / 8 for i in range(1, 9)])
        pts.extend([(5, cy - 1.7), (3.5, cy - 4.2)])
        pts.extend((3.5 * math.cos(a), cy - 4.2 + 2 * math.sin(a))
                   for a in [-i * math.pi / 12 for i in range(1, 13)])
        pts.extend([(-5, cy - 1.7), (-11, cy - 1.7)])
        pts.extend((-11 + 1.7 * math.cos(a), cy + 1.7 * math.sin(a))
                   for a in [-math.pi / 2 - i * math.pi / 8 for i in range(1, 9)])
        curve = bpy.data.curves.new('UnpunchedHangSlotScorePath', 'CURVE')
        curve.dimensions = '3D'
        curve.bevel_depth = .025 * .001
        curve.bevel_resolution = 2
        spline = curve.splines.new('POLY')
        spline.points.add(len(pts) - 1)
        for point, (xx, yy) in zip(spline.points, pts):
            point.co = (xx * .001, yy * .001, (z + .025) * .001, 1)
        spline.use_cyclic_u = True
        obj = bpy.data.objects.new('UnpunchedHangSlotDieScore', curve)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(self.edge)
        _localize(obj, hinge)
        obj['manufacturingDetail'] = 'Unpunched hook slot on pristine integrated hanger'
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target='MESH')

    def landscape(self):
        x, h, z, t = self.w / 2, self.h, self.d / 2, self.t
        self.fixed_front_back()
        for top, y, sign in ((True, h - .012, 1), (False, .012, -1)):
            name = 'Top' if top else 'Bottom'
            self.slab(name + 'PaperBoard', [(-x + .18, y, -z + t), (x - .18, y, -z + t),
                    (x - .18, y, z - t), (-x + .18, y, z - t)], (0, sign, 0))
            yy = h if top else 0
            zz = (z - t, -z + t) if top else (-z + t, z - t)
            self.art(name, [(-x + .18, yy, zz[0]), (x - .18, yy, zz[0]),
                            (x - .18, yy, zz[1]), (-x + .18, yy, zz[1])])
        # The back/top lap is glued, unlike the independently moving end closures.
        self.slab('InteriorGlueLap', [(-x + 3, h - t, -z + t + .12),
            (x - 3, h - t, -z + t + .12), (x - 3, h - 10, -z + t + .12),
            (-x + 3, h - 10, -z + t + .12)], (0, 0, 1), thickness=.32, outer=self.inner)
        for side, word in ((-1, 'Left'), (1, 'Right')):
            xx = side * (x - .012)
            flap = self.hinge(word + 'EndFlapHinge', (xx, 0, -z + t), 'Y', side * 108, .15)
            self.slab(word + 'EndFlapPaperBoard', [(xx, t + .3, -z + t),
                (xx, h - t - .3, -z + t), (xx, h - t - .3, z - t - .22),
                (xx, t + .3, z - t - .22)], (side, 0, 0), parent=flap)
            # Looking at the left end, U points from back to front; right is reversed.
            zs = (-z + t, z - t - .22) if side == -1 else (z - t - .22, -z + t)
            self.art('Spine' + word, [(side * x, t + .3, zs[0]), (side * x, t + .3, zs[1]),
                (side * x, h - t - .3, zs[1]), (side * x, h - t - .3, zs[0])], parent=flap)
            tongue_z = z - t - .55
            tongue = self.hinge(word + 'TuckTongueHinge', (side * (x - .5), 0, tongue_z),
                                 'Y', -side * 90, .15, flap)
            start, end = side * (x - .55), side * (x - 15.5)
            self.slab(word + 'RoundedTuckTongue', [(start, 7, tongue_z),
                (end + side * 3, 7, tongue_z), (end, 10, tongue_z),
                (end, h - 10, tongue_z), (end + side * 3, h - 7, tongue_z),
                (start, h - 7, tongue_z)], (0, 0, 1), parent=tongue, outer=self.inner)
            self.crease_line(word + 'TongueScoredFold', (start, 8, tongue_z),
                             (start, h - 8, tongue_z), parent=flap)
            # Top/bottom dust ears tuck under the printed end closure.
            for top, word2 in ((True, 'Upper'), (False, 'Lower')):
                yy = h - t - .18 if top else t + .18
                inner_y = yy - 25 if top else yy + 25
                dust_x = side * (x - t - .48)
                dust = self.hinge(word + word2 + 'DustFlapHinge', (dust_x, yy, 0), 'Z',
                                  side * (90 if top else -90), .55)
                self.slab(word + word2 + 'BeveledDustFlap', [(dust_x, yy, -z + t + 1),
                    (dust_x, yy, z - t - 1), (dust_x, inner_y, z - t - 5),
                    (dust_x, inner_y, -z + t + 5)], (side, 0, 0), parent=dust, outer=self.inner)
            self.crease_line(word + 'MainScoredFold', (side * (x - .15), 1, -z + t),
                             (side * (x - .15), h - 1, -z + t))
        self.folded_tray()

    def folded_tray(self):
        w, h, d = self.w - 5.5, self.h - 4.4, self.d - 4.5
        tray = self.api.empty('InsertTray', (0, 0, 0), parent=self.root)
        tray['boxPart'] = True
        tray['packagingPart'] = 'removable folded paperboard cartridge cradle'
        tray['closedTranslationMm'] = [0.0, 0.0, 0.0]
        tray['openTranslationMm'] = [self.w * .78, 0.0, 0.0]
        tray['extractionAxis'] = '+X after opening RightEndFlapHinge'
        tray['constructionApproximation'] = 'Folded stock layout and cutouts inferred; exact original die line unmeasured'
        y0, y1, back, front = 2.2, self.h - 2.2, -d / 2, d / 2 - 1
        x0, x1 = -w / 2, w / 2
        tt = .55
        def panel(name, corners, n):
            return self.slab(name, corners, n, thickness=tt, parent=tray, outer=self.tray_mat)
        panel('TrayFlatBase', [(x0, y0, back), (x1, y0, back), (x1, y1, back), (x0, y1, back)], (0, 0, -1))
        for side, x in ((-1, x0), (1, x1)):
            panel(('Left' if side < 0 else 'Right') + 'TrayOuterWall',
                  [(x, y0, back), (x, y1, back), (x, y1, front), (x, y0, front)], (side, 0, 0))
        for top, y in ((False, y0), (True, y1)):
            panel(('Upper' if top else 'Lower') + 'TrayOuterWall',
                  [(x0, y, back), (x1, y, back), (x1, y, front), (x0, y, front)], (0, 1 if top else -1, 0))
        aperture_w, aperture_h = ((119.4, 80.8) if self.console == 'nintendo-64' else (138.0, 89.5))
        ax, ay0, ay1 = aperture_w / 2, (self.h - aperture_h) / 2, (self.h + aperture_h) / 2
        tray['cartridgeClearanceMm'] = [aperture_w, aperture_h, 23.5]
        # Four independent folded rails, hollow underneath rather than solid blocks.
        panel('TrayLowerReturn', [(x0, y0, front), (x1, y0, front), (ax, ay0, front), (-ax, ay0, front)], (0, 0, 1))
        panel('TrayUpperReturn', [(-ax, ay1, front), (ax, ay1, front), (x1, y1, front), (x0, y1, front)], (0, 0, 1))
        for side in (-1, 1):
            outer, inner = side * w / 2, side * ax
            # A smooth semicircular finger opening interrupts the inner rail edge.
            cy, radius = self.h / 2, 8.0
            pts = [(outer, y0, front), (inner, ay0, front), (inner, cy - radius, front)]
            for i in range(1, 17):
                theta = -math.pi / 2 + i * math.pi / 16
                pts.append((inner + side * radius * math.cos(theta), cy + radius * math.sin(theta), front))
            pts.extend([(inner, ay1, front), (outer, y1, front)])
            panel(('Left' if side < 0 else 'Right') + 'TrayFingerNotchRail', pts, (0, 0, 1))
            # Returns support the cartridge without a wall across the access notch.
            for index, (lo, hi) in enumerate(((ay0, cy - radius), (cy + radius, ay1))):
                panel(('Left' if side < 0 else 'Right') + 'TrayInnerReturn' + str(index),
                    [(inner, lo, front), (inner, hi, front), (inner, hi, back + 1.2),
                     (inner, lo, back + 1.2)], (-side, 0, 0))
        for top, yy in ((False, ay0), (True, ay1)):
            panel(('Upper' if top else 'Lower') + 'TrayCradleReturn',
                  [(-ax, yy, back + 1.2), (ax, yy, back + 1.2), (ax, yy, front), (-ax, yy, front)],
                  (0, -1 if top else 1, 0))
        # Visible corner tuck ears and shallow scoring make the folded construction readable.
        for side in (-1, 1):
            for top in (False, True):
                xx, yy = side * (w / 2 - tt - .25), y1 - 1 if top else y0 + 1
                end_y = yy - 15 if top else yy + 15
                panel(('Right' if side > 0 else 'Left') + ('Upper' if top else 'Lower') + 'TrayLockTab',
                      [(xx, yy, back + 1), (xx, end_y, back + 1),
                       (xx, end_y, front - 4), (xx, yy, front - 1)], (-side, 0, 0))
        return tray

    def nes(self):
        x, h, z, t = self.w / 2, self.h, self.d / 2, self.t
        self.fixed_front_back()
        self.root['editionScope'] = 'Early US integrated-hangtab carton; hanger stays flush and unpunched in pristine presentation'
        for side, word in ((-1, 'Left'), (1, 'Right')):
            xx = side * (x - .012)
            self.slab(word + 'SidePaperBoard', [(xx, .3, -z + t), (xx, h - .4, -z + t),
                (xx, h - .4, z - t), (xx, .3, z - t)], (side, 0, 0))
            zz = (-z + t, z - t) if side == -1 else (z - t, -z + t)
            self.art('Spine' + word, [(side * x, .3, zz[0]), (side * x, .3, zz[1]),
                                    (side * x, h - .4, zz[1]), (side * x, h - .4, zz[0])])
        self.slab('InteriorVerticalGlueLap', [(-x + t + .1, 2, -z + t + .15),
            (-x + 10, 2, -z + t + .15), (-x + 10, h - 2, -z + t + .15),
            (-x + t + .1, h - 2, -z + t + .15)], (0, 0, 1), thickness=.32, outer=self.inner)
        lid = self.hinge('TopLidHinge', (0, h - .05, -z + t), 'X', -110, .15)
        self.slab('TopLidPaperBoard', [(-x + t + .22, h - .012, -z + t),
            (x - t - .22, h - .012, -z + t), (x - t - .22, h - .012, z - t),
            (-x + t + .22, h - .012, z - t)], (0, 1, 0), parent=lid)
        self.art('Top', [(-x + t + .22, h, z - t), (x - t - .22, h, z - t),
                        (x - t - .22, h, -z + t), (-x + t + .22, h, -z + t)], parent=lid)
        tongue = self.hinge('TopTuckTongueHinge', (0, h - t, z - t - .38), 'X', 90, .15, lid)
        self.slab('TopRoundedTuckTongue', [(-x + 6, h - t, z - t - .38),
            (x - 6, h - t, z - t - .38), (x - 6, h - 13, z - t - .38),
            (x - 9, h - 16, z - t - .38), (-x + 9, h - 16, z - t - .38),
            (-x + 6, h - 13, z - t - .38)], (0, 0, 1), parent=tongue, outer=self.inner)
        for side, word in ((-1, 'Left'), (1, 'Right')):
            xx, yy = side * (x - t - .3), h - t - .5
            dust = self.hinge(word + 'TopDustFlapHinge', (xx, yy, 0), 'Z', -side * 105, .55)
            tip = xx - side * 25
            self.slab(word + 'TopDustFlap', [(xx, yy, -z + t + .5), (xx, yy, z - t - .5),
                (tip, yy, z - t - 4), (tip, yy, -z + t + 4)], (0, 1, 0), parent=dust, outer=self.inner)
        self.crease_line('LidScoredFold', (-x + 1, h - .15, -z + t), (x - 1, h - .15, -z + t))
        # Four separate interlocking bottom flaps. Broad faces are layered with
        # physical stock clearance; no solid plane seals over their articulation.
        for front, word, sign in ((True, 'Front', 1), (False, 'Rear', -1)):
            yy = .012 if front else t + .15
            zz = sign * (z - t)
            flap = self.hinge('Bottom' + word + 'LockHinge', (0, yy, zz), 'X', 0, .75)
            flap['inspectionOpenAngleDegrees'] = -sign * 105
            mid = -sign * 3.5
            outline = [(-x + 1, yy, zz), (x - 1, yy, zz), (x - 4, yy, mid),
                       (12, yy, mid), (9, yy, mid - sign * 4.0),
                       (-9, yy, mid - sign * 4.0), (-12, yy, mid), (-x + 4, yy, mid)]
            self.slab('Bottom' + word + 'InterlockPanel', outline, (0, -1, 0), parent=flap)
            # Each interlocking flap has its own exterior print. Both use the
            # continuous bottom UV field, so a black base never exposes a white
            # rear flap and no artwork plane bridges an articulated seam.
            face = self.api.mesh('ArtworkBottom' + ('' if front else 'Rear'),
                [(p[0], yy - .012, p[2]) for p in outline],
                [tuple(reversed(range(len(outline)))) if front else tuple(range(len(outline)))],
                self.art_mats['Bottom'])
            uv = face.data.uv_layers.new(name='ArtworkUV')
            for loop in face.data.polygons[0].loop_indices:
                p = outline[face.data.loops[loop].vertex_index]
                uv.data[loop].uv = ((p[0] + x) / self.w, (p[2] + z) / self.d)
            face['artworkSlot'] = 'Bottom'
            face['artworkOrientation'] = 'upright exterior projection; die-cut outline uses partial UV region'
            face['artworkAspectRatio'] = self.w / self.d
            _localize(face, flap)
            self.slots.append(face.name)
        for side, word in ((-1, 'Left'), (1, 'Right')):
            xx, yy = side * (x - t - .3), 2 * t + .35
            wing = self.hinge('Bottom' + word + 'LockHinge', (xx, yy, 0), 'Z', 0, .82)
            wing['inspectionOpenAngleDegrees'] = side * 105
            tip = xx - side * 26
            self.slab('Bottom' + word + 'LockEar', [(xx, yy, -z + 1), (xx, yy, z - 1),
                (tip, yy, z - 5), (tip, yy, -z + 5)], (0, -1, 0), parent=wing, outer=self.inner)
        self.nes_insert()

    def nes_insert(self):
        x, h, z = self.w / 2, self.h, self.d / 2
        assembly = self.api.empty('NESPackagingInsert', parent=self.root)
        assembly['boxPart'] = True
        assembly['packagingPart'] = 'white EPS bottom spacer and open black protective sleeve'
        foam = self.api.material('CleanWhiteFoamSpacer', (.93, .93, .91), .94)
        # Subtle native procedural pore shading, with no age or grime colors.
        nodes = foam.node_tree.nodes
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 3800
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .07
        bump.inputs['Distance'].default_value = .000045
        foam.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
        foam.node_tree.links.new(bump.outputs['Normal'], nodes.get('Principled BSDF').inputs['Normal'])
        spacer = self.api.box('WhiteFoamBottomSpacer', (0, 21.8, -.3), (self.w - 3, 39.5, self.d - 3.5),
                              foam, bevel=.7, parent=assembly)
        spacer['approximateDimensionsMm'] = [self.w - 3, 39.5, self.d - 3.5]
        spacer['exportNote'] = 'Foam microtexture is source-only procedural shading; portable export retains clean base material'
        sleeve = self.api.empty('RemovableBlackSleeve', parent=assembly)
        sleeve['boxPart'] = True
        sleeve['closedTranslationMm'] = [0.0, 0.0, 0.0]
        sleeve['openTranslationMm'] = [0.0, 145.0, 0.0]
        sleeve['extractionAxis'] = '+Y after opening TopLidHinge'
        black = self.api.material('CleanBlackCartridgeSleeve', (.014, .016, .019), .49)
        # Rounded thumb notch on the front of the empty sleeve, open at the top.
        a, y0, y1, dep = 62, 42.0, 176.0, 9.35
        outline = [(-a, y0, dep), (a, y0, dep), (a, y1 - 12, dep), (17, y1 - 12, dep)]
        for i in range(1, 21):
            angle = math.pi * i / 20
            outline.append((17 * math.cos(angle), y1 - 12 - 14 * math.sin(angle), dep))
        outline.append((-a, y1 - 12, dep))
        front = self.slab('SleeveFrontWithThumbNotch', outline, (0, 0, 1), thickness=.35, parent=sleeve, outer=black)
        back = self.slab('SleeveBackPanel', [(-a, y0, -dep), (a, y0, -dep),
                          (a, y1, -dep), (-a, y1, -dep)], (0, 0, -1), thickness=.35, parent=sleeve, outer=black)
        for side in (-1, 1):
            panel = self.slab(('Left' if side < 0 else 'Right') + 'SleeveWeldedEdge',
                [(side * a, y0, -dep), (side * a, y1 - 12, -dep),
                 (side * a, y1 - 12, dep), (side * a, y0, dep)], (side, 0, 0), thickness=.35, parent=sleeve, outer=black)
            panel.data.materials.clear()
            panel.data.materials.append(black)
            for polygon in panel.data.polygons:
                polygon.material_index = 0
        bottom = self.slab('SleeveBottomWeld', [(-a, y0, -dep), (a, y0, -dep),
                           (a, y0, dep), (-a, y0, dep)], (0, -1, 0), thickness=.35, parent=sleeve, outer=black)
        for obj in (front, back, bottom):
            obj.data.materials.clear()
            obj.data.materials.append(black)
            for polygon in obj.data.polygons:
                polygon.material_index = 0
        sleeve['copyrightNote'] = 'Neutral sleeve without Nintendo logotype'

    def finish(self):
        self.root['artworkSlots'] = json.dumps(self.slots)
        self.root['hinges'] = json.dumps(self.hinges)
        self.root['openingNote'] = 'Lids and tuck tongues counter-fold together, then dust ears open; extract the insert after the end closure is clear'
        self.root['limitations'] = ('No factory die-line measurements, pack-in leaflets, game media, shrinkwrap, or wear; '
            'NES die-cut hanger and tray folds are approximated from photographs; board gauges are inferred')
        self.root['geometryLimitations'] = self.root['limitations']
        self.root['referenceBasis'] = 'Protector manufacturer fit dimensions and inspected retail specimen photographs; see docs/nintendo-box-reference-evidence.json'
        return self.root


def build(api, console):
    """Return a closed, empty neutral carton with separately addressable packaging."""
    if console not in CONFIG:
        raise ValueError('Unsupported Nintendo box console: ' + console)
    carton = Carton(api, console)
    if console == 'nes':
        carton.nes()
    else:
        carton.landscape()
    return carton.finish()
