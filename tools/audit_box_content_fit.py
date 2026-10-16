#!/usr/bin/env python3
"""Audit the actual Contents meshes against packaging in composed GLBs.

Run with Blender's Python (mathutils BVH and NumPy are required):
  blender --background --python tools/audit_box_content_fit.py -- \
      --models-root dist/box-polish-20261016/reproductions \
      --output dist/box-polish-20261016/audits/content-surface-fit.json

This checks triangle surface intersections at the closed and fully open hinge
poses. It is not a containment, elastic deformation, insertion-path or factory
tolerance certification. The separate fit record documents cavity clearances.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspect_glb import Accessors, read_glb
from inspect_game_box import transform


def world_meshes(path, opened):
    document, binary, _ = read_glb(path)
    accessors = Accessors(document, binary)
    result = []

    def visit(index, parent, is_content=False):
        node = document['nodes'][index]
        is_content = is_content or node.get('name') == 'Contents'
        extras = node.get('extras', {})
        rotation = extras.get('openQuaternion') if opened and extras.get('boxHinge') else None
        matrix = parent @ np.array(transform(node, rotation))
        if 'mesh' in node:
            vertices, faces = [], []
            for primitive in document['meshes'][node['mesh']]['primitives']:
                assert primitive.get('mode', 4) == 4, 'Expected triangle primitives'
                positions = np.array(accessors.read(primitive['attributes']['POSITION']))
                positions = np.c_[positions, np.ones(len(positions))] @ matrix.T
                indices = np.array(accessors.read(primitive['indices'])).ravel().reshape(-1, 3)
                faces.extend((indices + len(vertices)).tolist())
                vertices.extend(positions[:, :3].tolist())
            vertices = np.array(vertices)
            result.append(dict(name=node.get('name'), vertices=vertices, faces=faces,
                               low=vertices.min(0), high=vertices.max(0), content=is_content))
        for child in node.get('children', []):
            visit(child, matrix, is_content)

    for index in document['scenes'][document.get('scene', 0)]['nodes']:
        visit(index, np.eye(4))
    return result


def bounds(meshes):
    return {'minMm': (np.min([mesh['low'] for mesh in meshes], 0) * 1000).tolist(),
            'maxMm': (np.max([mesh['high'] for mesh in meshes], 0) * 1000).tolist()}


def inspect(path):
    receipt_path = path.parent / 'content-composition.json'
    receipt = json.loads(receipt_path.read_text())
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    assert checksum == receipt['output']['glbSha256'], 'Composition receipt is stale'
    result = {'assetId': path.stem, 'glbSha256': checksum,
              'mediaSource': receipt['mediaSource'], 'contents': receipt['contents'],
              'poses': {}}
    for pose, opened in [('closed', False), ('open', True)]:
        meshes = world_meshes(path, opened)
        media = [mesh for mesh in meshes if mesh['content']]
        packaging = [mesh for mesh in meshes if not mesh['content']]
        assert media and packaging, 'Expected both Contents and packaging geometry'
        pairs = []
        for content in media:
            for case in packaging:
                overlap = np.minimum(content['high'], case['high']) - np.maximum(content['low'], case['low'])
                if np.min(overlap) < -1e-7:
                    continue
                for mesh in (content, case):
                    if 'bvh' not in mesh:
                        mesh['bvh'] = BVHTree.FromPolygons(mesh['vertices'].tolist(), mesh['faces'],
                                                          all_triangles=True, epsilon=0)
                hits = content['bvh'].overlap(case['bvh'])
                if hits:
                    pairs.append({'mediaMesh': content['name'], 'packagingMesh': case['name'],
                                  'intersectingTrianglePairs': len(hits)})
        result['poses'][pose] = {'mediaBounds': bounds(media), 'mediaMeshCount': len(media),
                                 'packagingMeshCount': len(packaging), 'intersectionPairs': pairs}
        print(path.stem, pose, 'intersecting mesh pairs:', len(pairs), flush=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == checksum, 'File changed during audit'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    paths = sorted(args.models_root.glob('*/*-box.glb'))
    assert paths, 'No reproduction box GLBs found'
    rows = [inspect(path) for path in paths]
    report = {'schemaVersion': 1, 'method': 'Decoded GLB world triangles; Blender BVHTree overlap, epsilon=0.',
              'poses': 'Closed node transforms and fully open boxHinge openQuaternion endpoints.',
              'broadPhaseAabbToleranceMeters': 1e-7,
              'limitations': ['Surface crossing test only; cavity dimensions need separate review.',
                              'No insertion path, elastic deformation or factory tolerance certification.'],
              'assets': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    if any(pose['intersectionPairs'] for row in rows for pose in row['poses'].values()):
        raise SystemExit('Content/packaging surface intersections found; inspect the report.')


if __name__ == '__main__':
    main()
