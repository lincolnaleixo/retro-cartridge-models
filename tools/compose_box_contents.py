#!/usr/bin/env python3
"""Add a verified published game cartridge/disc to a reproduction box.

Run in Blender, passing an immutable print-only box source and a media directory
extracted from the catalog's published archive. Neutral templates are not inputs.
The final GLB uses exact source buffers; the editable blend keeps native objects.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from box_contents import PREFIX, compose, read_glb, sha, validate_composition, write_glb

PLACEMENTS = {
    'nes': ('RemovableBlackSleeve', [0, .0424, 0], [0, 0, 0, 1]),
    'snes': ('InsertTray', [0, .020, -.0042399802], [0, 0, 0, 1]),
    'nintendo-64': ('InsertTray', [0, .0257, -.0034], [0, 0, 0, 1]),
    'mega-drive': ('CartridgePlacement', [0, 0, 0], [0, 0, 0, 1]),
    'playstation-1': ('RemovableTray', [.0064, .002375, -.00015], [0, 0, 0, 1]),
}


def scene_bounds(document, binary, media_start):
    from inspect_game_box import Accessors, hierarchy, world_bounds
    reader = Accessors(document, binary)
    roots = hierarchy(document)
    media_only = deepcopy(document)
    for node in media_only['nodes'][:media_start]:
        node.pop('mesh', None)
    poses = {}
    for pose in ('closed', 'open'):
        rotations = {i: n['extras']['openQuaternion'] for i, n in enumerate(document['nodes'])
                     if pose == 'open' and n.get('extras', {}).get('boxHinge')}
        poses[pose] = {'combined': world_bounds(document, reader, roots, rotations),
                       'media': world_bounds(media_only, reader, roots, rotations)}
    return poses


def append_editable(box_source, media_source, output, media_root_name, placement, receipt):
    import bpy
    from mathutils import Quaternion
    from source_paths import sanitize_source_paths
    import create_game_boxes as boxes
    bpy.ops.wm.open_mainfile(filepath=str(box_source.resolve()))
    bpy.context.scene.frame_set(1)
    parent_name, translation, rotation = placement
    parent = bpy.data.objects.get(parent_name)
    if parent is None or bpy.data.objects.get('Contents'):
        raise ValueError('Missing insertion parent or source already has contents')
    for change in receipt['descriptiveMetadataOverrides']:
        obj = bpy.data.objects[change['nodeName']]
        if obj.get(change['key']) != change['old']:
            raise ValueError('Native source metadata differs from the print-only GLB baseline')
        obj[change['key']] = change['new']
    before = set(bpy.data.objects)
    with bpy.data.libraries.load(str(media_source.resolve()), link=False) as (source, target):
        target.objects = list(source.objects)
    loaded = [obj for obj in target.objects if obj is not None]
    roots = [obj for obj in loaded if obj.parent is None and
             (obj.name == media_root_name or obj.name.startswith(media_root_name + '.'))]
    if len(roots) != 1:
        raise ValueError('Could not identify the published media root: ' + media_root_name)
    media_root = roots[0]
    keep = {media_root, *media_root.children_recursive}
    for obj in loaded:
        if obj not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)
    contents = bpy.data.objects.new('Contents', None)
    bpy.context.scene.collection.objects.link(contents)
    contents.parent = parent
    contents.location = translation
    contents.rotation_mode = 'QUATERNION'
    contents.rotation_quaternion = Quaternion((rotation[3], *rotation[:3]))
    contents['boxContents'] = True
    contents['removable'] = True
    contents['mediaAssetId'] = receipt['mediaSource']['assetId']
    contents['mediaVersion'] = receipt['mediaSource']['version']
    contents['sourceGlbSha256'] = receipt['mediaSource']['glbSha256']
    for obj in keep:
        if not obj.users_collection:
            bpy.context.scene.collection.objects.link(obj)
        obj.name = PREFIX + obj.name
        obj.animation_data_clear()
    media_root.parent = contents
    bpy.context.view_layer.update()
    blend_bounds = boxes.precise_bounds(contents)
    expected = receipt['poseBounds']['closed']['media']
    for edge in ('min', 'max'):
        if max(abs(x-y) for x,y in zip(blend_bounds[edge], expected[edge])) > .000025:
            raise ValueError('Editable media placement differs from exact published GLB: ' + str(blend_bounds))
    # Published inputs are already packed. Repacking an existing packed image
    # would try its sanitized relative path and produce spurious missing-file
    # errors, even though the correct original bytes are embedded.
    for image in bpy.data.images:
        if image.users and image.type != 'RENDER_RESULT' and not image.packed_file:
            image.pack()
    sanitize_source_paths()
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()))
    return {'nativeMediaObjects': len(keep), 'mediaMeshObjects': sum(o.type == 'MESH' for o in keep),
            'closedMediaBounds': blend_bounds, 'packedImages': sum(bool(i.packed_file) for i in bpy.data.images),
            'preservedBoxObjects': len(before), 'method': 'Appended verified published native media objects; rigid parent transform only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--box-source', type=Path, required=True)
    parser.add_argument('--media-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Existing reproduction output directory')
    parser.add_argument('--catalog', type=Path, default=Path('catalog.json'))
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    box_source = args.box_source.resolve()
    box_glb = box_source.with_suffix('.glb')
    construction = json.loads((box_source.parent / 'construction.json').read_text())
    asset_id, console = construction['assetId'], construction['console']
    if not asset_id.endswith('-box') or asset_id == console + '-box':
        raise ValueError('Only game reproductions may include game contents')
    media_id = asset_id[:-4]
    catalog = json.loads(args.catalog.read_text())
    asset = next(a for a in catalog['assets'] if a['id'] == media_id)
    manifest_path = args.catalog.resolve().parent / asset['manifest']
    manifest = json.loads(manifest_path.read_text())
    media_glb = args.media_directory / (media_id + '.glb')
    media_source = media_glb.with_suffix('.blend')
    for path in (media_glb, media_source):
        if sha(path) != manifest['files'][path.name]['sha256']:
            raise ValueError('Media source does not match its published manifest: ' + path.name)
    box, box_binary = read_glb(box_glb)
    media, media_binary = read_glb(media_glb)
    placement = PLACEMENTS[console]
    document, binary, receipt = compose(box, box_binary, media, media_binary,
        *placement, media_id, manifest['version'])
    receipt.update(schemaVersion=1, assetId=asset_id,
        boxSource={'glbFile': box_glb.name, 'glbSha256': sha(box_glb),
                   'blendFile': box_source.name, 'blendSha256': sha(box_source)},
        mediaSource={'assetId': media_id, 'version': manifest['version'],
                     'manifestSha256': sha(manifest_path), 'archiveSha256': manifest['release']['archive']['sha256'],
                     'releaseUrl': manifest['release']['archive']['url'],
                     'glbFile': media_glb.name, 'glbSha256': sha(media_glb),
                     'blendFile': media_source.name, 'blendSha256': sha(media_source)},
        poseBounds=scene_bounds(document, binary, receipt['offsets']['nodes']),
        placementBasis='Published media at original scale, fitted to the existing cartridge anchor, folded tray, sleeve or disc hub. Dimensions inferred from visualization geometry, not factory tolerances.',
        limitations=['No shrinkwrap or additional pack-in leaflets added.',
                     'Contact placement is an approximate rigid visualization; flexible plastic/paper deformation is not simulated.'])
    # Reject a fit outside the existing closed carton/case before writing files.
    closed = construction['closedBounds']
    media_bounds = receipt['poseBounds']['closed']['media']
    if any(media_bounds['min'][i] < closed['min'][i] - 1e-6 or
           media_bounds['max'][i] > closed['max'][i] + 1e-6 for i in range(3)):
        raise ValueError('Published media does not fit the closed box envelope at scale 1')
    args.output.mkdir(parents=True, exist_ok=True)
    output_glb = args.output / box_glb.name
    if output_glb.resolve() == box_glb.resolve():
        raise ValueError('Use an immutable print-only baseline, not the output directory')
    write_glb(output_glb, document, binary)
    receipt['preservation'] = validate_composition(box_glb, media_glb, output_glb, receipt)
    media_roots = media['scenes'][media.get('scene',0)]['nodes']
    if len(media_roots) != 1:
        raise ValueError('Expected one published native media assembly')
    receipt['editableSource'] = append_editable(box_source, media_source,
        args.output / box_source.name, media['nodes'][media_roots[0]]['name'], placement, receipt)
    receipt['status'] = 'passed'
    receipt['output'] = {'glbSha256': sha(output_glb), 'blendSha256': sha(args.output / box_source.name)}
    evidence = args.output / 'content-source'
    evidence.mkdir(exist_ok=True)
    (evidence / 'release-manifest.json').write_bytes(manifest_path.read_bytes())
    archive = args.catalog.resolve().parent / '.downloads' / media_id / manifest['version'] / manifest['release']['archive']['name']
    if sha(archive) != manifest['release']['archive']['sha256']:
        raise ValueError('Cached published media archive hash differs')
    copied = {'release-manifest.json': sha(manifest_path)}
    with zipfile.ZipFile(archive) as package:
        for name in ('CREDITS.md', 'NOTICE.md', 'LICENSE', 'artwork-provenance.json', 'measurement-evidence.json'):
            if name in manifest['files']:
                payload = package.read(name)
                expected = manifest['files'][name]['sha256']
                if hashlib.sha256(payload).hexdigest() != expected:
                    raise ValueError('Published media attribution differs: ' + name)
                (evidence / name).write_bytes(payload)
                copied[name] = expected
    receipt['pinnedMediaEvidence'] = {'directory': 'content-source', 'files': copied}
    for pose in ('closed', 'open'):
        construction[pose+'Bounds'] = receipt['poseBounds'][pose]['combined']
    construction['contentComposition'] = {'receipt': 'content-composition.json',
        'mediaAssetId': media_id, 'mediaVersion': manifest['version'], 'removableParent': 'Contents',
        'mediaSourceGlbSha256': sha(media_glb), 'originalScalePreserved': True}
    for change in receipt['descriptiveMetadataOverrides']:
        if change['key'] == 'geometryLimitations':
            construction['geometryLimitations'] = change['new']
    (args.output / 'construction.json').write_text(json.dumps(construction, indent=2)+'\n')
    (args.output / 'content-composition.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('CONTENTS_COMPOSED', asset_id, receipt['output']['glbSha256'])


if __name__ == '__main__':
    main()
