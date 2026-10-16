#!/usr/bin/env python3
"""Reopen a PS1 disc and correct its clamping material and hidden front underlay.

Run with Blender --background --python tools/refine_playstation_disc.py --
  --source DIR/asset.blend --model DIR/asset.glb --output DIR/asset
Both source and GLB are required. Positions, normals, UVs, images and unrelated
indices are preserved; 512 hidden body-top triangles and release metadata change.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from box_animation import read_glb, write_glb
from playstation_disc_materials import DEFAULT_PROFILE, PROFILES, correct_disc, refine_blender_materials, remove_hidden_blender_front, validate_correction


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_snapshot(ignore_hidden_front=False):
    import bpy
    meshes = {}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj.name.startswith('Studio'):
            continue
        mesh = obj.data
        polygons = [p for p in mesh.polygons if not (ignore_hidden_front and obj.name == 'Disc'
            and all(abs(mesh.vertices[v].co.z - .000595) < 1e-9 for v in p.vertices))]
        values = {'vertices': [list(v.co) for v in mesh.vertices],
                  'polygons': [list(p.vertices) for p in polygons],
                  'uvs': {layer.name: [[list(layer.data[i].uv) for i in p.loop_indices] for p in polygons] for layer in mesh.uv_layers},
                  'matrix': [list(row) for row in obj.matrix_world],
                  'parent': obj.parent.name if obj.parent else None}
        meshes[obj.name] = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
    images = {image.name: hashlib.sha256(image.packed_file.data).hexdigest()
              for image in bpy.data.images if image.packed_file}
    return {'meshStateHashes': meshes, 'packedImageHashes': images}


def main():
    import bpy
    from source_paths import sanitize_source_paths
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--model', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--profile', choices=tuple(PROFILES), default=DEFAULT_PROFILE)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source, model, output = args.source.resolve(), args.model.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if source.parent == output or model.parent == output:
        raise ValueError('Source payload must remain immutable in a separate folder')
    document, binary = read_glb(model)
    updated, updated_binary = correct_disc(document, binary, args.profile, model.stem)
    new_glb, new_blend = output / model.name, output / source.name
    write_glb(new_glb, updated, updated_binary)
    actual_doc, actual_bin = read_glb(new_glb)
    proof = validate_correction(document, binary, actual_doc, actual_bin, args.profile, model.stem)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    before = source_snapshot(ignore_hidden_front=True)
    refine_blender_materials(args.profile)
    remove_hidden_blender_front()
    for change in proof['releaseMetadataChanges']:
        root = bpy.data.objects[change['nodeName']]
        if root.get(change['key']) != change['old']:
            raise ValueError('Native source release metadata differs from its original GLB')
        root[change['key']] = change['new']
    if before != source_snapshot():
        raise ValueError('Material refinement changed native mesh/transforms/images')
    sanitize_source_paths()
    bpy.ops.wm.save_as_mainfile(filepath=str(new_blend))
    bpy.ops.wm.open_mainfile(filepath=str(new_blend))
    if before != source_snapshot():
        raise ValueError('Reopened source changed native mesh/transforms/images')
    receipt = {'schemaVersion': 1, 'status': 'candidate',
        'method': 'Dark clamping material and dedicated inner-matrix assignment; removed only 512 hidden Disc top triangles to prevent front ink depth fighting. Positions, normals, UVs, embedded image bytes, all other indices, node transforms and dimensions preserved.',
        'referenceBasis': ['https://psxdatacenter.com/images/hires/U/C/SCUS-94900/SCUS-94900-D-ALL.jpg', 'https://www.ebay.com/itm/186116411851'],
        'limitations': 'Photo-matched visualization parameters, not measured optical constants. Existing 21 mm print-mask radius and 18 mm clamping-material boundary are unchanged; references only establish a roughly 20 mm dark annulus.',
        'source': {'glb': {'file': model.name, 'sha256': sha(model)}, 'blend': {'file': source.name, 'sha256': sha(source)}},
        'output': {'glb': {'file': new_glb.name, 'sha256': sha(new_glb)}, 'blend': {'file': new_blend.name, 'sha256': sha(new_blend)}},
        'preservation': proof, 'nativeSource': {'status': 'passed', **before}}
    (output / 'disc-material-refinement.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('DISC_MATERIAL_CANDIDATE ' + str(output))


if __name__ == '__main__':
    main()
