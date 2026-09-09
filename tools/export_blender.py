"""Blender: blender -b source.blend --python tools/export_blender.py -- output.glb

Preserves the meter/Y-up import contract. This tool does not publish files.
"""
import sys
from pathlib import Path
import bpy

args=sys.argv[sys.argv.index('--')+1:]
if len(args)!=1:raise ValueError('provide exactly one output .glb path')
output=Path(args[0]).resolve()
if output.suffix.lower()!='.glb':raise ValueError('output must be .glb')
root=bpy.data.objects.get('SNES_NTSC_U')
if root is None:raise ValueError('expected SNES_NTSC_U model root')
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for child in root.children_recursive:
    if child.type=='MESH':child.select_set(True)
bpy.context.view_layer.objects.active=root
output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,
    export_apply=True,export_cameras=False,export_lights=False,export_yup=False,export_extras=True)
