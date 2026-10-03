"""Reference-based NTSC-U/C standard single-disc jewel case and PlayStation CD.

Case envelope: midpoint of CMC's original jewel-case assembly inspection ranges,
142.20–142.50 x 124.60–124.90 x 10.40 +/- 0.2 mm. This is a standard
replacement-compatible case dimension, NOT a Sony manufacturing specification.
https://cmcdisc.com/media-packaging/original-jewel-case/

Visual specimen: Grillo Games' four photographs of Silent Hill, NTSC-U/C.
https://www.grillogames.de/en/products/sony-playstation-1-spiel-silent-hill-ovp-anleitung-ntsc-u-c-usa-konami
Fine molded features are proportioned from photographs and CMC drawings;
original Sony-tooling dimensions have not been measured. No borrowed artwork.

Disc dimensions follow ECMA-130, 2nd edition, sections 8.2, 8.4, 8.6 and 8.7.
The 120 mm / 15 mm / 1.2 mm nominal disc is split into non-overlapping clear
clamping and reflective regions, with a dark underside rather than a silver CD-R.
"""
import math


def _roughness_image(api, name, values):
    """Pack original scalar texture data in a glTF-compatible image node."""
    import numpy as np
    height, width = values.shape
    rgba = np.empty((height, width, 4), dtype=np.float32)
    rgba[:, :, :3] = values[:, :, None]
    rgba[:, :, 3] = 1.0
    image = api.bpy.data.images.new(name, width=width, height=height, alpha=True)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    return image


def _attach_roughness(mat, image):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    texture = nodes.new('ShaderNodeTexImage')
    texture.name = image.name
    texture.image = image
    texture.interpolation = 'Linear'
    channels = nodes.new('ShaderNodeSeparateColor')
    links.new(texture.outputs['Color'], channels.inputs['Color'])
    links.new(channels.outputs['Green'], nodes.get('Principled BSDF').inputs['Roughness'])


def build(api):
    import bmesh
    import numpy as np
    root = api.reset('PLAYSTATION_1')
    root['variant'] = 'NTSC-U/C standard single-disc jewel case, clear tray'
    root['status'] = 'Unreleased photograph-based reconstruction; molded details approximate'
    root['nominalDimensionsMm'] = [142.35, 124.75, 10.4]
    root['referenceBasis'] = 'CMC standard case inspection dimensions; Silent Hill NTSC-U/C specimen photographs; ECMA-130 disc dimensions'
    root['caseDimensionsSource'] = 'https://cmcdisc.com/media-packaging/original-jewel-case/'
    root['discDimensionsSource'] = 'https://ecma-international.org/wp-content/uploads/ECMA-130_2nd_edition_june_1996.pdf'
    root['geometryLimitations'] = 'Case dimensions are standard-compatible, not Sony tooling measurements. Wall thickness, hinge clearances and tray ribs are photo-derived approximations.'

    W, H, D = 142.35, 124.75, 10.4
    cy, cx = H / 2, 6.4
    clear = api.material('Clear molded polystyrene', (0.99, 0.995, 1.0),
                         roughness=0.027, transmission=1.0, alpha=0.055)
    edges = api.material('Polystyrene rims and catches', (0.88, 0.90, 0.92),
                         roughness=0.045, transmission=1.0, alpha=0.18)
    tray_mat = api.material('Clear injection molded tray', (0.94, 0.96, 0.98),
                            roughness=0.038, transmission=1.0, alpha=0.12)
    paper = api.material('Neutral booklet cover paper', (0.72, 0.72, 0.67), roughness=0.68)
    pages = api.material('Booklet cut paper edges', (0.68, 0.68, 0.64), roughness=0.88)
    back_paper = api.material('Neutral printed tray card', (0.075, 0.085, 0.095), roughness=0.67)
    label_ink = api.material('Neutral disc label ink', (0.53, 0.55, 0.56), roughness=0.3, metallic=0.7)
    matrix = api.material('Disc reflective matrix band', (0.39, 0.41, 0.44), roughness=0.2, metallic=0.82)
    dark_disc = api.material('PlayStation dark data substrate', (0.0055, 0.0037, 0.0105), roughness=0.075, metallic=0.24)
    clear_disc = api.material('Disc transparent clamping substrate', (0.38, 0.36, 0.43),
                              roughness=0.045, transmission=1.0, alpha=0.19)
    for mat in (clear, edges, tray_mat):
        mat.node_tree.nodes.get('Principled BSDF').inputs['IOR'].default_value = 1.59
    # Opaque paper remains double-sided. Clear parts are real closed solids:
    # outward-only rendering avoids doubling their alpha in Compatibility.
    for mat in (clear, edges, tray_mat, clear_disc):
        mat.use_backface_culling = True
    dark_shader = dark_disc.node_tree.nodes.get('Principled BSDF')
    dark_shader.inputs['IOR'].default_value = 1.58
    dark_shader.inputs['Coat Weight'].default_value = 0.25
    dark_shader.inputs['Coat Roughness'].default_value = 0.035

    # These radial optical zones alter roughness, not hue. They represent the
    # inner transition/outer lead-out appearance; individual micron CD tracks
    # cannot be resolved at this texture scale and are not falsely modeled.
    size = 1024
    axis = (np.arange(size, dtype=np.float32) + 0.5) / size - 0.5
    xx, yy = np.meshgrid(axis * 120, axis * 120)
    radius = np.sqrt(xx * xx + yy * yy)
    roughness = np.full_like(radius, 0.074)
    # Avoid periodic rings: visible, evenly spaced grooves would resemble a
    # vinyl record. Only broad finish variation and zone transitions belong here.
    roughness += 0.002 * np.cos(radius * math.pi / 18.0)
    roughness += 0.017 * np.exp(-((radius - 22.0) / 0.34) ** 2)
    roughness += 0.010 * np.exp(-((radius - 24.9) / 0.20) ** 2)
    roughness += 0.024 * np.exp(-((radius - 58.15) / 0.42) ** 2)
    roughness += 0.012 * np.exp(-((radius - 59.25) / 0.18) ** 2)
    roughness += np.random.default_rng(130).normal(0, 0.0015, radius.shape).astype(np.float32)
    optical_map = _roughness_image(api, 'Original PS1 optical-zone roughness', np.clip(roughness, 0.04, 0.14))
    _attach_roughness(dark_disc, optical_map)
    # Original paper microtexture is kept subtle so runtime cover art remains
    # the focal surface; unlike shader-only Noise nodes it survives GLB export.
    paper_values = np.random.default_rng(151118).normal(0.69, 0.018, (256,256)).astype(np.float32)
    paper_map = _roughness_image(api, 'Original booklet paper roughness', np.clip(paper_values,0.63,0.76))
    _attach_roughness(paper, paper_map)

    def cube(name, center, size, mat, bevel=0.07):
        return api.box(name, center, size, mat, bevel)

    def prism(name, points, low, high, mat, bevel=0):
        return api.profile(name, points, high, low, mat, bevel)

    def sector(name, center, outer, inner, z0, z1, a0, a1, mat, steps=32):
        """Closed annular-sector extrusion with no hidden solid disk beneath it."""
        x, y = center
        points = [(x + outer * math.cos(a0 + (a1-a0)*i/steps),
                   y + outer * math.sin(a0 + (a1-a0)*i/steps)) for i in range(steps+1)]
        points += [(x + inner * math.cos(a0 + (a1-a0)*i/steps),
                    y + inner * math.sin(a0 + (a1-a0)*i/steps)) for i in reversed(range(steps+1))]
        return prism(name, points, z0, z1, mat)

    def shell_band(name, coords, z0, z1, mat):
        return prism(name, coords, z0, z1, mat, 0.055)

    # Rear shell is a thin, clear molded cup, not a solid jewel-sized block.
    cube('RearPanel', (0, cy, -4.78), (W, H, 0.84), clear, 0.12)
    for y in (0.52, H-0.52):
        cube(f'RearTopBottomWall_{y:.2f}', (0, y, -1.455), (W, 1.04, 5.8), edges)
    for x in (-70.665, 70.665):
        height=H-10.0 if x<0 else H-2.08
        cube(f'RearSpineWall_{x:.2f}', (x, cy, -1.28), (1.02, height, 6.15), clear)
    # Small moulded stepped lips locate the tray at the top and bottom edges.
    for y in (2.02, H-2.02):
        cube(f'TraySeat_{y:.2f}', (0, y, -2.03), (137.5, 0.64, 1.1), edges)

    # Rear artwork lies INSIDE the clear shell; the standard 151 x 118 mm sheet
    # has a 138 mm main field and two 6.5 mm folded spine strips.
    # Unfolded U runs continuously through both spine strips and the back.
    cross_section=[(69,2.27),(69,-4.28),(-69,-4.28),(-69,2.27)]
    rear_verts=[(x,cy+dy,z) for x,z in cross_section for dy in (-59,59)]
    rear_faces=[(2*i,2*i+2,2*i+3,2*i+1) for i in range(3)]
    rear=api.mesh('RearLabel',rear_verts,rear_faces,back_paper)
    rear_uv=rear.data.uv_layers.new(name='ArtworkUV')
    unfolded_u=[0,6.5/151,144.5/151,1]
    for polygon in rear.data.polygons:
        for index in polygon.loop_indices:
            vi=rear.data.loops[index].vertex_index
            rear_uv.data[index].uv=(unfolded_u[vi//2],vi%2)
    rear['artworkAspectRatio']=151/118
    rear['artworkOrientation']='Full unfolded tray card including two 6.5 mm spine strips; U increases viewer-left to viewer-right'
    rear['paperSizeMm']=[151,118]
    rear['paperLocation'] = 'Inside rear panel; rear plastic outer Z=-5.20 mm, inner Z=-4.36 mm'
    api.label('RearCardInside', 138, 118, 0, cy, -4.19, back_paper, radius=0.04)

    # The removable clear tray has a shallow circular well. Outside the well,
    # the four corner webs rise to a higher rim. No invented black corner pads.
    tray = api.ring('TrayWellFloor', (cx, cy, -2.55), 60.5, 14.9, 0.64, tray_mat, segments=128)
    # Squared outer boundary joined to the circular recess, including top and
    # bottom finger scallops. These are radial quads, not a box under the disc.
    outer = []
    inner = []
    count = 160
    xmin, xmax, ymin, ymax = -56.6, 68.7, 1.68, H-1.68
    for i in range(count):
        a = 2*math.pi*i/count
        dx, dy = math.cos(a), math.sin(a)
        tx = ((xmax-cx) if dx >= 0 else (xmin-cx))/dx if abs(dx)>1e-8 else 1e8
        ty = ((ymax-cy) if dy >= 0 else (ymin-cy))/dy if abs(dy)>1e-8 else 1e8
        r = min(tx,ty)
        ox, oy = cx+r*dx, cy+r*dy
        # Rounded access scallops align with the four booklet-tab positions.
        if abs(oy-ymin)<0.01 or abs(oy-ymax)<0.01:
            for sx in (-37.3, 51.7):
                if abs(ox-sx)<5.2:
                    inward = math.sqrt(max(0,5.2**2-(ox-sx)**2))
                    oy += inward if oy < cy else -inward
        outer.append((ox,oy,-0.5))
        inner.append((cx+60.5*dx,cy+60.5*dy,-1.93))
    verts = outer + inner + [(x,y,z-0.65) for x,y,z in outer] + [(x,y,z-0.65) for x,y,z in inner]
    faces = []
    for i in range(count):
        j = (i+1)%count
        faces += [(i,j,count+j,count+i), (2*count+i,3*count+i,3*count+j,2*count+j),
                  (i,2*count+i,2*count+j,j),(count+i,count+j,3*count+j,3*count+i)]
    api.mesh('TrayCornerWebs',verts,faces,tray_mat)
    # Raised outer disc rim is interrupted for finger access at cardinal edges.
    for i in range(4):
        a0 = math.radians(i*90+7)
        a1 = math.radians((i+1)*90-7)
        sector(f'TrayPeripheralRim_{i}',(cx,cy),61.0,60.35,-1.95,-0.20,a0,a1,tray_mat)

    # The clear strip visible left of the booklet is the ribbed tray edge;
    # corrugations are thin molded ribs backed by an open cavity, never a black block.
    cube('TrayRibbedSpineWeb',(-63.0,cy,-1.20),(13.9,121.3,0.65),tray_mat)
    for i in range(35):
        y = 4.6+i*3.38
        points = [(-69.8,y-0.58),(-58.0,y-0.58),(-56.6,y),(-58.0,y+0.58),(-69.8,y+0.58)]
        prism(f'TraySpineCorrugation_{i:02}',points,-0.98,0.95,tray_mat,0.11)
    for x in (-69.65,-56.5):
        cube(f'TraySpineEdge_{x}',(x,cy,-0.34),(0.7,121.3,2.0),tray_mat)

    # A real hub is a set of cantilever fingers rising inward from an annular
    # base. Its radial slots remain open and it has no filled center peg.
    hub = api.ring('DiscHub', (cx,cy,-2.15),15.5,12.25,1.4,tray_mat,segments=96)
    hub['part'] = 'Fixed tray hub base; does not travel with the CD'
    for i in range(12):
        a = 2*math.pi*i/12
        # Successive radius/height sections make the sprung arm and the small
        # outward retaining lip; angular gaps are real empty space.
        sections = [(13.6,-1.48,1.7),(11.1,-1.30,1.55),(8.0,-1.00,1.35),
                    (7.10,-0.95,1.25),(7.05,0.90,1.25),
                    (7.65,1.14,1.25),(7.25,1.50,1.10)]
        vv=[]
        for r,z,width in sections:
            for dz in (0,-0.5):
                for side in (-1,1):
                    vv.append((cx+r*math.cos(a)-side*width/2*math.sin(a),
                               cy+r*math.sin(a)+side*width/2*math.cos(a),z+dz))
        ff=[(0,2,3,1)]
        for j in range(len(sections)-1):
            p,q=j*4,(j+1)*4
            ff += [(p,q,q+1,p+1),(p+2,p+3,q+3,q+2),
                   (p,p+2,q+2,q),(p+1,q+1,q+3,p+3)]
        k=(len(sections)-1)*4
        ff += [(k,k+1,k+3,k+2)]
        api.mesh(f'HubSpringFinger_{i:02}',vv,ff,tray_mat,bevel=0.045)

    # Disc body and transparent center are disjoint solids. Printed/silver
    # label face is separate in material assignment from the dark data side.
    disc = api.ring('Disc',(cx,cy,-0.15),60.0,18.0,1.2,dark_disc,segments=192)
    disc.data.materials.append(label_ink)
    for polygon in disc.data.polygons:
        if polygon.normal.z > 0.5:
            polygon.material_index=1
        polygon.use_smooth = abs(polygon.normal.z)<0.5
    disc['nominalDimensionsMm']=[120,120,1.2]
    disc['centerHoleDiameterMm']=15
    clear_hub=api.ring('DiscClearHub',(cx,cy,-0.15),18.0,7.5,1.2,clear_disc,segments=192)
    matrix_ring=api.ring('DiscInnerMatrix',(cx,cy,0.455),21.0,18.0,0.01,matrix,segments=192)
    rim=api.ring('DiscOuterRim',(cx,cy,0.455),59.95,59.55,0.01,matrix,segments=192)
    for obj in (disc,clear_hub,matrix_ring,rim):
        obj['isDiscComponent']=True
    clear_hub['construction']='Transparent 7.5–18 mm annulus; no opaque geometry underneath'

    # Hinge pins and socket bores share this exact vertical axis. The long lid
    # arms run across the top and bottom of the ribbed strip to the far-left
    # corners, as in the manufacturer's lid drawing.
    hinge_x, hinge_z = -69.60, 2.03
    lid = api.empty('FrontLid',(hinge_x,cy,hinge_z),root)
    lid['openRotationYDegrees']=-110
    lid['closedRotationYDegrees']=0
    lid['hingeAxisMm']=[hinge_x,cy,hinge_z]
    lid['rotationAxis']='Local +Y; coaxial with fixed case pins'
    lid_objects=[]
    lid_objects.append(cube('FrontPanel',(6.10,cy,4.825),(130.15,H,0.75),clear,0.10))
    for y in (0.63,H-0.63):
        lid_objects.append(cube(f'LidTopBottomRail_{y:.2f}',(-0.1,y,3.04),(142.05,1.0,2.82),edges,0.08))
    lid_objects.append(cube('LidLatchEdge',(70.66,cy,3.26),(1.02,H-2.2,2.38),edges))
    # Raised internal booklet guide at the panel's left edge, not a solid spine.
    lid_objects.append(cube('LidBookletGuide',(-58.5,cy,3.97),(0.6,H-2.4,0.96),clear))
    for y in (1.75,H-1.75):
        # Fixed body pins extend into actual annular sockets in the lid arms.
        pin=api.cylinder(f'HingePin_{y:.2f}',(hinge_x,y,hinge_z),0.76,1.75,edges,32,bevel=0.045)
        pin.rotation_euler.x=math.pi/2
        socket=api.ring(f'LidHingeSocket_{y:.2f}',(0,0,0),1.23,0.82,1.05,edges,segments=40)
        socket.rotation_euler.x=math.pi/2
        socket.location=api.mm((hinge_x,y,hinge_z))
        lid_objects.append(socket)
        lid_objects.append(cube(f'LidHingeEar_{y:.2f}',(-69.6,y,3.65),(2.4,1.4,1.1),edges,0.055))
    # Small closure catches nest behind the lid edge. They do not bridge the lid.
    for y in (18.5,H-18.5):
        cube(f'CaseCatch_{y:.2f}',(69.50,y,1.95),(0.55,4.4,1.0),edges,0.09)
        lid_objects.append(cube(f'LidCatch_{y:.2f}',(70.02,y,2.8),(0.5,4.1,0.75),edges,0.09))

    # Eight shallow page sections retain the verified 1 mm booklet envelope.
    # Cut edges are inset from the cover and separated by hairline shadow gaps,
    # so the open booklet reads as layered paper instead of a plastic block.
    page_parts=[]
    for i in range(8):
        section = cube(f'BookletLeaf_{i:02}',(6.08,cy,3.3615+i*0.125),
                       (119.74-0.018*(i%3),119.72-0.014*(i%2),0.122),pages,0.007)
        page_parts.append(section)
    api.bpy.ops.object.select_all(action='DESELECT')
    for obj in page_parts:
        obj.select_set(True)
    api.bpy.context.view_layer.objects.active=page_parts[0]
    # Apply each bevel before joining so subsequent leaves keep their edges.
    api.bpy.ops.object.convert(target='MESH')
    api.bpy.ops.object.join()
    booklet=api.bpy.context.object
    booklet.name='BookletPages'
    booklet['part']='Removable booklet with eight editable page sections in one mesh'
    booklet['pageSectionCount']=8
    lid_objects.append(booklet)
    lid_objects.append(api.label('FrontLabel',120,120,6.1,cy,4.315,paper,radius=0.04))
    lid_objects.append(api.label('InsertInnerPaper',120,120,6.1,cy,3.285,paper,radius=0.04,rear=True))
    for y,sign in ((1.68,1),(H-1.68,-1)):
        for x in (-37.3,51.7):
            # Rounded molded tabs reach over the booklet from the outer rail.
            points=[(x-4.3,y-sign*0.6),(x+4.3,y-sign*0.6)]
            points += [(x+4.3*math.cos(math.pi*i/20),
                        y+sign*4.0*math.sin(math.pi*i/20)) for i in range(21)]
            if sign<0:
                points.reverse()
            lid_objects.append(prism(f'BookletRetentionTab_{x}_{y:.2f}',points,3.03,3.27,edges,0.035))
    # Preserve authored world-space coordinates while parenting to the hinge.
    api.bpy.context.view_layer.update()
    for obj in lid_objects:
        world=obj.matrix_world.copy()
        obj.parent=lid
        obj.matrix_world=world
    # The old two-sided display hid some inward hub-face normals. Recalculate
    # all transparent closed components before exporting single-sided surfaces.
    transparent_materials={clear,edges,tray_mat,clear_disc}
    for obj in root.children_recursive:
        if obj.type=='MESH' and obj.data.materials and obj.data.materials[0] in transparent_materials:
            bm=bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
            # Recalc guarantees consistency but can choose inward orientation
            # for the bent spring solids. Use their signed enclosed volume.
            if bm.calc_volume(signed=True) < 0:
                bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
            bm.to_mesh(obj.data)
            bm.free()
    api.bpy.context.view_layer.update()
    return root
