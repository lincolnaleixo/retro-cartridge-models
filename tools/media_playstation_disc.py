"""Standalone 120 mm PlayStation CD; no case, tray or retention hub.

Dimensions follow ECMA-130. The dark reading face is never a artwork target.
FrontLabel is an annulus with UV0 covering a 120 mm square, preserving the hole.
"""
import math

from media_playstation import _roughness_image, _attach_roughness


def build(api):
    import numpy as np
    root = api.reset('PLAYSTATION_1_DISC')
    root['mediaType'] = 'optical-disc'
    root['nominalDimensionsMm'] = [120, 120, 1.2]
    root['centerHoleDiameterMm'] = 15
    root['referenceBasis'] = 'ECMA-130, 2nd edition, sections 8.2, 8.4, 8.6 and 8.7; dark PlayStation data substrate'
    dark = api.material('PlayStation dark data substrate', (0.0055, 0.0037, 0.0105), roughness=0.075, metallic=0.24)
    shader = dark.node_tree.nodes.get('Principled BSDF')
    shader.inputs['IOR'].default_value = 1.58
    shader.inputs['Coat Weight'].default_value = 0.25
    shader.inputs['Coat Roughness'].default_value = 0.035
    axis = (np.arange(1024, dtype=np.float32) + 0.5) / 1024 - 0.5
    xx, yy = np.meshgrid(axis * 120, axis * 120)
    radius = np.sqrt(xx * xx + yy * yy)
    values = 0.074 + 0.002 * np.cos(radius * math.pi / 18)
    for r, spread, strength in ((22, .34, .017), (24.9, .2, .010), (58.15, .42, .024), (59.25, .18, .012)):
        values += strength * np.exp(-((radius-r)/spread)**2)
    values += np.random.default_rng(130).normal(0, .0015, radius.shape).astype(np.float32)
    _attach_roughness(dark, _roughness_image(api, 'Original PS1 optical-zone roughness', np.clip(values, .04, .14)))
    clear = api.material('Disc transparent clamping substrate', (.38, .36, .43), roughness=.045, transmission=1, alpha=.19)
    clear.use_backface_culling = True
    matrix = api.material('Disc reflective matrix band', (.39, .41, .44), roughness=.2, metallic=.82)
    ink = api.material('Neutral disc label ink', (.53, .55, .56), roughness=.3, metallic=.35)
    body = api.ring('Disc', (0, 60, -.0025), 60, 18, 1.195, dark, segments=256)
    for polygon in body.data.polygons:
        polygon.use_smooth = abs(polygon.normal.z) < .5
    api.ring('DiscClearHub', (0, 60, 0), 18, 7.5, 1.2, clear, segments=256)
    api.ring('DiscInnerMatrix', (0, 60, .5975), 21, 18, .005, matrix, segments=256)
    api.ring('DiscOuterRim', (0, 60, .5975), 60, 59.55, .005, matrix, segments=256)
    count = 256
    verts = [(r * math.cos(i * 2 * math.pi / count), 60 + r * math.sin(i * 2 * math.pi / count), .6)
             for r in (59.55, 21) for i in range(count)]
    faces = [(i, (i+1) % count, (i+1) % count + count, i+count) for i in range(count)]
    label = api.mesh('FrontLabel', verts, faces, ink)
    uv = label.data.uv_layers.new(name='ArtworkUV')
    for polygon in label.data.polygons:
        for index in polygon.loop_indices:
            x, y, _ = verts[label.data.loops[index].vertex_index]
            uv.data[index].uv = (x/120+.5, y/120)
    label['artworkAspectRatio'] = 1.0
    label['artworkOrientation'] = '120 mm square, upright; geometry masks outer edge and transparent center'
    return root
