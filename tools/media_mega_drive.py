"""Western Sega Mega Drive / Genesis media reconstruction.

Original parametric geometry; references are measurements and real photographs,
not imported third-party meshes. Nominal outer envelope 109 x 70 x 17 mm.
See root documentation for source URLs and measurement confidence.
"""
import math
import bpy
import bmesh
import numpy as np


def _packed_surface_maps():
    """Generate original periodic micrograin, without external texture files.

    The 512px tile covers 8 mm of plastic. Fourier filtering makes both ends
    periodic; seeded noise produces the same data on every rebuild. This is a
    restrained visualization of molded ABS, not a measured factory texture.
    """
    size = 512
    rng = np.random.default_rng(19881029)
    frequency = np.fft.fftfreq(size)
    radius_sq = frequency[:, None] ** 2 + frequency[None, :] ** 2

    def filtered_noise(sigma):
        spectrum = np.fft.fft2(rng.standard_normal((size, size)))
        filtered = np.fft.ifft2(spectrum * np.exp(-2 * math.pi ** 2 * sigma ** 2 * radius_sq)).real
        return filtered / filtered.std()

    grain = filtered_noise(2.5) * 0.80 + filtered_noise(0.8) * 0.20
    dx = (np.roll(grain, -1, axis=1) - np.roll(grain, 1, axis=1)) * 0.09
    dy = (np.roll(grain, -1, axis=0) - np.roll(grain, 1, axis=0)) * 0.09
    normals = np.stack((-dx, -dy, np.ones_like(grain)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)

    def packed_image(name, rgb):
        image = bpy.data.images.new(name, width=size, height=size, alpha=False)
        image.colorspace_settings.name = 'Non-Color'
        rgba = np.ones((size, size, 4), dtype=np.float32)
        rgba[:, :, :3] = rgb
        image.pixels.foreach_set(rgba.ravel())
        image.update()
        image.pack()
        image['provenance'] = 'Original deterministic procedural material; no source photograph'
        image['physicalTileSizeMm'] = 8.0
        return image

    normal = packed_image('ABS micrograin tangent normal 8mm', normals * 0.5 + 0.5)
    maps = {}
    for finish, base, variation in (('satin', .36, .010), ('molded', .42, .014)):
        roughness = np.clip(base + variation * grain, base - .035, base + .035)
        # Standard glTF ORM ordering: unused R=1, roughness G, metallic B=0.
        rgb = np.stack((np.ones_like(grain), roughness, np.zeros_like(grain)), axis=-1)
        maps[finish] = packed_image('ABS ' + finish + ' roughness', rgb)
    return normal, maps


def _exportable_abs(material, normal_image, roughness_image, strength):
    """Use glTF-supported image nodes instead of Blender-only Noise/Bump."""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get('Principled BSDF')
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'SurfaceUV'
    normal_texture = nodes.new('ShaderNodeTexImage')
    normal_texture.image = normal_image
    normal_texture.extension = 'REPEAT'
    normal_texture.interpolation = 'Linear'
    normal = nodes.new('ShaderNodeNormalMap')
    normal.uv_map = 'SurfaceUV'
    normal.inputs['Strength'].default_value = strength
    links.new(uv.outputs['UV'], normal_texture.inputs['Vector'])
    links.new(normal_texture.outputs['Color'], normal.inputs['Color'])
    links.new(normal.outputs['Normal'], shader.inputs['Normal'])
    roughness_texture = nodes.new('ShaderNodeTexImage')
    roughness_texture.image = roughness_image
    roughness_texture.extension = 'REPEAT'
    roughness_texture.interpolation = 'Linear'
    channels = nodes.new('ShaderNodeSeparateColor')
    links.new(uv.outputs['UV'], roughness_texture.inputs['Vector'])
    links.new(roughness_texture.outputs['Color'], channels.inputs['Color'])
    links.new(channels.outputs['Green'], shader.inputs['Roughness'])
    material['surfaceFinish'] = 'Fine isotropic ABS grain, 8 mm periodic tile; glTF normal and roughness textures'


def _surface_uv(obj):
    """Physical 8mm isotropic grain scale, separate from artwork UVs.

    Box projections preserve scale on large flat faces. The cheeks switch
    projection only at tangent directions; isotropic grain hides that seam.
    """
    data = obj.data
    layer = data.uv_layers.get('SurfaceUV') or data.uv_layers.new(name='SurfaceUV')
    for polygon in data.polygons:
        axis = max(range(3), key=lambda i: abs(polygon.normal[i]))
        axes = ((2, 1), (0, 2), (0, 1))[axis]
        for index in polygon.loop_indices:
            position = obj.matrix_world @ data.vertices[data.loops[index].vertex_index].co
            layer.data[index].uv = (position[axes[0]] / .008, position[axes[1]] / .008)


def _apply(obj):
    bpy.context.view_layer.objects.active = obj
    for modifier in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def _subtract(obj, cutter):
    _apply(cutter)
    modifier = obj.modifiers.new('Physical molded recess', 'BOOLEAN')
    modifier.operation = 'DIFFERENCE'
    modifier.solver = 'EXACT'
    modifier.object = cutter
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def _smooth(obj):
    # Keep broad manufactured planes flat, smoothly shade the swept cheeks.
    for polygon in obj.data.polygons:
        n = polygon.normal
        polygon.use_smooth = max(abs(n.x), abs(n.y), abs(n.z)) < 0.9999


def _sweep(api, name, points, low, high, material, bevel=0.4):
    # Cross-section lives in X/Z; extrusion runs along Y.
    n = len(points)
    vertices = [(x, y, z) for y in (low, high) for x, z in points]
    faces = [tuple(range(n)), tuple(reversed(range(n, 2*n)))]
    faces += [(i, i+n, (i+1)%n+n, (i+1)%n) for i in range(n)]
    obj = api.mesh(name, vertices, faces, material)
    # Recalculate to avoid depending on the profile's handedness.
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    if bevel:
        m = obj.modifiers.new('Small injection molded edge radius', 'BEVEL')
        m.width = bevel * api.MM
        m.segments = 4
        m.limit_method = 'ANGLE'
        m.angle_limit = math.radians(25)
    _apply(obj)
    _smooth(obj)
    return obj


def _capsule_cutter(api, name, center, width, height, depth):
    # Smooth swept ellipsoid: creates a real concavity, not a dark overlay.
    cx, cy, cz = center
    r = height/2
    half_straight = width/2-r
    rows = []
    steps, around = 12, 64
    for i in range(steps+1):
        a = -math.pi/2 + i*math.pi/2/steps
        rows.append((-half_straight + r*math.sin(a), math.cos(a)))
    for i in range(steps+1):
        a = i*math.pi/2/steps
        rows.append((half_straight + r*math.sin(a), math.cos(a)))
    vertices = [(cx+x, cy+r*rr*math.cos(j*2*math.pi/around),
                 cz+depth/2*rr*math.sin(j*2*math.pi/around))
                for x,rr in rows for j in range(around)]
    faces = []
    for i in range(len(rows)-1):
        for j in range(around):
            nj=(j+1)%around
            faces.append((i*around+j,(i+1)*around+j,(i+1)*around+nj,i*around+nj))
    obj=api.mesh(name, vertices, faces, None)
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.0000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    for p in obj.data.polygons: p.use_smooth=True
    return obj


def _folded_label(api, material):
    # 74 x 67 unfolded, with last 7 mm folding over the top. Printed-to-fit
    # community template; 2 mm corner radius. Surface is one UV island.
    width,total,front = 74.0,67.0,60.0
    # Paper lies 0.035 mm above the 0.4572 mm recessed land.
    radius=0.8-0.4572+0.035
    y_start=9.2
    fold_length=math.pi*radius/2
    samples = sorted(set([0,.12,.35,.7,1.1,1.5,2,20,40,58,59,60,
                          *[front+fold_length*i/16 for i in range(1,17)],
                          63,65,65.5,65.9,66.3,66.65,66.88,67]))
    verts,uv=[],[]
    for s in samples:
        inset=0.0
        if s<2: inset=2-math.sqrt(max(0,4-(2-s)**2))
        elif s>65: inset=2-math.sqrt(max(0,4-(s-65)**2))
        if s<=front:
            y,z=y_start+s,7.7+radius
        elif s<front+fold_length:
            a=(s-front)/radius
            y,z=69.2+radius*math.sin(a),7.7+radius*math.cos(a)
        else:
            y,z=69.2+radius,7.7-(s-front-fold_length)
        for x in (-width/2+inset,width/2-inset):
            verts.append((x,y,z));uv.append((x/width+.5,s/total))
    faces=[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(samples)-1)]
    obj=api.mesh('FrontLabel',verts,faces,material)
    layer=obj.data.uv_layers.new(name='ArtworkUV')
    for p in obj.data.polygons:
        p.use_smooth=True
        for li in p.loop_indices:layer.data[li].uv=uv[obj.data.loops[li].vertex_index]
    obj['artworkAspectRatio']=width/total
    obj['artworkOrientation']='U left-to-right; V bottom-to-top of unfolded label'
    obj['unfoldedDimensionsMm']=[74.0,67.0]
    obj['topFoldMm']=7.0
    return obj


def build(api):
    root=api.reset('MEGA_DRIVE')
    black=api.material('Fine satin injection molded black ABS',(0.012,0.014,0.016),.36)
    rear_black=api.material('Fine textured rear molded black ABS',(0.012,0.014,0.016),.42)
    inset=api.material('Recessed molded black ABS',(0.010,0.012,0.014),.46)
    # Godot promotes a material's active texture UV set to UV0. Keep the
    # replaceable artwork land untextured so its authored 0-1 UV0 survives.
    rear_artwork=api.material('Neutral molded rear artwork land',(0.010,0.012,0.014),.42)
    paper=api.material('Neutral unprinted paper label',(0.67,0.66,0.60),.60)
    pcb=api.material('Connector green epoxy substrate',(0.015,0.075,0.035),.47)
    metal=api.material('Dark zinc security fasteners',(0.13,0.14,0.15),.32,.75)
    gold=api.material('Connector gold plated pads',(0.50,0.28,0.08),.3,.75)
    for solid in (black, rear_black, pcb, metal, gold):
        solid.use_backface_culling = True
    normal_image, roughness_maps = _packed_surface_maps()
    _exportable_abs(black, normal_image, roughness_maps['satin'], .28)
    _exportable_abs(rear_black, normal_image, roughness_maps['molded'], .40)
    _exportable_abs(inset, normal_image, roughness_maps['molded'], .34)

    # The front is a broad flat label land with curved cheeks in cross-section.
    # It retains straight top/bottom outlines rather than round shoulder lobes.
    cross=[]
    for i in range(33):
        a=math.pi/2-i*math.pi/2/32
        cross.append((-42.0-12.5*math.sin(a),-1.1+9.6*math.cos(a)))
    cross.append((42.0,8.5))
    for i in range(1,33):
        a=i*math.pi/2/32
        cross.append((42.0+12.5*math.sin(a),-1.1+9.6*math.cos(a)))
    front_shell=_sweep(api,'FrontShell',cross,0,70,black,.8)
    # Hollow the shell. Interior remains closed on the front face and opens
    # solely through the actual underside slot, keeping frontal gold hidden.
    _subtract(front_shell,api.box('Front interior core',(0,35.8,-.6),(96.5,65.4,14.8),None,1.2))
    mouth=api.box('Front connector opening',(0,1.5,0),(90.5,8,9.0),None,.45)
    _subtract(front_shell,mouth)
    # OEM-like label channel: cut both the upright land and the wrap across
    # the rounded top edge. It is a physical 0.4572 mm recess, not an overlay.
    label_core=api.profile('Front label recessed land',api.rounded_points(76.2,61.3,2.3,y=39.0),9.3,8.0428,None,0)
    _subtract(front_shell,label_core)
    path=[]
    fold=math.pi*.8/2
    for value in [59.0,60.0,*[60+fold*i/16 for i in range(1,17)],68.1]:
        if value<=60:y,z,ny,nz=9.2+value,8.5,0,1
        elif value<60+fold:
            a=(value-60)/.8;y,z,ny,nz=69.2+.8*math.sin(a),7.7+.8*math.cos(a),math.sin(a),math.cos(a)
        else:y,z,ny,nz=70.0,7.7-(value-60-fold),1,0
        path.append((y,z,ny,nz))
    yz=[(y+.8*ny,z+.8*nz) for y,z,ny,nz in path]
    yz += [(y-.4572*ny,z-.4572*nz) for y,z,ny,nz in reversed(path)]
    n=len(yz)
    verts=[(x,y,z) for x in (-38.1,38.1) for y,z in yz]
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    faces += [(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)]
    core=api.mesh('Top label fold recessed land',verts,faces,None)
    bm=bmesh.new();bm.from_mesh(core.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(core.data);bm.free()
    _subtract(front_shell,core)
    # A separate, flatter rear molding steps in at the lower side margins.
    outline=[(-47.5,0),(47.5,0),(47.5,39.8),(54.1,39.8),
             (54.1,70),(-54.1,70),(-54.1,39.8),(-47.5,39.8)]
    rear=api.profile('RearShell',outline,-1.22,-8.5,rear_black,.5)
    _apply(rear)
    _subtract(rear,api.box('Rear interior core',(0,35.8,-.4),(91.8,65.4,11.8),None,.8))
    _subtract(rear,api.box('Rear connector opening',(0,1.5,0),(90.5,8,9.0),None,.45))
    # The thin side returns are structural lower side walls, not finger ribs.
    for side in (-1,1):
        rail=api.box('FrontSideReturn_'+str(side),(side*50.8,19.9,-3.75),(6.5,39.8,5.05),black,.45)
        _apply(rail)
    # Real rear finger recess near the top, with smoothly curved concave floor.
    cutter=_capsule_cutter(api,'Grip cavity tool',(0,54.7,-9.8),80.0,10.6,6.0)
    _subtract(rear,cutter)
    # The warning and mark panels are shallow molded lands, not pale stickers.
    for name,w,h,y in [('RearLabel',78.0,22.0,14.4),('RearMark',27.0,13.0,38.1)]:
        cutter=api.profile(name+' recess tool',api.rounded_points(w,h,1.6,y=y),-8.18,-9.0,None,0)
        _subtract(rear,cutter)
        panel_material = rear_artwork if name == 'RearLabel' else inset
        panel=api.label(name,w-.25,h-.25,0,y,-8.195,panel_material,1.5,rear=True)
        if name=='RearMark':del panel['artworkAspectRatio'];del panel['artworkOrientation']
    # Two recessed screw seats, centered to match the physical board's ~70mm
    # mounting pattern; outer heads have security-like six lobes, no slot.
    for x in (-34.8,34.8):
        tool=api.cylinder('Rear screw seat tool',(x,36.1,-8.1),3.05,4,None,64,0)
        _subtract(rear,tool)
        api.cylinder('InternalScrewBoss_'+str(x),(x,36.1,-3.8),3.6,5.0,black,48,.1)
        api.cylinder('ScrewShaft_'+str(x),(x,36.1,-6.4),1.1,2.3,metal,32,.05)
        seat=api.cylinder('ScrewSeat_'+str(x),(x,36.1,-6.30),2.8,.4,inset,64,.1)
        head=api.cylinder('SecurityScrew_'+str(x),(x,36.1,-7.18),1.95,.85,metal,64,.15)
        _apply(head)
        for i in range(6):
            a=i*math.pi/3
            cutter=api.cylinder('Security notch tool',(x+2.0*math.cos(a),36.1+2.0*math.sin(a),-7.18),.42,1.4,None,16,0)
            _subtract(head,cutter)
    # Bottom slot: PCB sits well inside the housing with 32 pads each side.
    api.box('ConnectorPCB',(0,20,0),(83.0,35.2,1.6),pcb,.12)
    for side in (-1,1):
        for i in range(32):
            # Plating is only 0.028 mm thick: retain its envelope with simple
            # planar faces instead of thousands of invisible bevel triangles.
            api.box(f'Contact_{side}_{i:02}',(-39.37+i*2.54,5.4,side*.814),(1.55,5.2,.028),gold,0)
    _folded_label(api,paper)
    _smooth(front_shell);_smooth(rear)
    bpy.context.view_layer.update()
    for obj in root.children_recursive:
        if obj.type == 'MESH' and any(material in (black, rear_black, inset) for material in obj.data.materials):
            _surface_uv(obj)
    root['nominalDimensionsMm']=[109.0,70.0,17.0]
    root['physicalVariant']='Western Sega standard shell (PAL Mega Drive / Genesis), neutral labels'
    root['referenceBasis']='HDRV independently reconstructed shell footprint; community and physical-reader measurements; OEM photo morphology'
    root['measurementLimits']='Visualization reconstruction: nominal envelope corroborated; recess depths, radii and hidden internal details inferred, not factory CAD'
    root['surfaceTextureBasis']='Original subtle procedural approximation of molded ABS; 512px periodic normal and roughness textures embedded in GLB and packed in Blender'
    root['referenceUrls']=['https://www.hdretrovision.com/free-stuff/','https://consolemods.org/wiki/Cart_Labels','https://aaltomies.wordpress.com/2016/01/08/games-on-your-wall/']
    return root
