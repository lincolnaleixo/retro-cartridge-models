"""Protect published geometry during artwork-only replacements."""
import copy
from pathlib import Path
import struct
import tempfile
import unittest

from update_packed_artwork import (
    accessor_values, find_image_by_packed_hash, patch_glb, read_glb,
    remap_uv, validate_remaps, view_bytes, write_glb,
)


PNG = b'\x89PNG\r\n\x1a\noriginal-test-payload'
JPEG = b'\xff\xd8\xffreplacement-test-payload'


def fixture():
    # Artwork is between geometry views. Index data is shared across meshes,
    # like the PS1/SNES exports; each material has its own UV accessor.
    payloads = [struct.pack('<9f', 0, 0, 0, 1, 0, 0, 0, 1, 0), PNG,
                struct.pack('<6f', .2, .7, .6, .7, .2, .1), struct.pack('<3H', 0, 1, 2),
                b'\x89PNG\r\n\x1a\nother-image', struct.pack('<6f', 0, 0, 1, 0, 0, 1)]
    binary, views = bytearray(), []
    for payload in payloads:
        binary.extend(b'\0' * (-len(binary) % 4))
        views.append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(payload)})
        binary.extend(payload)
    views[0]['target'] = 34962
    accessors = [
        {'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3', 'min': [0, 0, 0], 'max': [1, 1, 0]},
        {'bufferView': 2, 'componentType': 5126, 'count': 3, 'type': 'VEC2'},
        {'bufferView': 3, 'componentType': 5123, 'count': 3, 'type': 'SCALAR'},
        {'bufferView': 5, 'componentType': 5126, 'count': 3, 'type': 'VEC2'},
    ]
    document = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength': len(binary)}],
                'bufferViews': views, 'accessors': accessors,
                'images': [{'name': 'ExportedFront', 'bufferView': 1, 'mimeType': 'image/png'},
                           {'name': 'ExportedTop', 'bufferView': 4, 'mimeType': 'image/png'}],
                'materials': [{'name': 'Front paper'}, {'name': 'Fold paper'}],
                'meshes': [{'primitives': [
                    {'attributes': {'POSITION': 0, 'TEXCOORD_0': 1}, 'indices': 2, 'material': 0},
                    {'attributes': {'POSITION': 0, 'TEXCOORD_0': 3}, 'indices': 2, 'material': 1}]}],
                'nodes': [{'name': 'FrontLabel', 'mesh': 0, 'translation': [0, 1, 0]}],
                'scenes': [{'nodes': [0]}], 'scene': 0}
    return document, bytes(binary)


class ArtworkPatchTests(unittest.TestCase):
    def test_long_short_and_odd_replacements_preserve_every_geometry_byte(self):
        document, binary = fixture()
        for replacement in (JPEG, JPEG + b'x' * 200, b'\xff\xd8\xffa'):
            with self.subTest(size=len(replacement)):
                result, output, report = patch_glb(document, binary, {0: replacement})
                for index in (0, 2, 3, 4, 5):
                    self.assertEqual(view_bytes(document, binary, index), view_bytes(result, output, index))
                for key in ('accessors', 'meshes', 'nodes', 'materials', 'scenes'):
                    self.assertEqual(document[key], result[key])
                self.assertEqual(view_bytes(result, output, 1), replacement)
                self.assertEqual(result['images'][0]['mimeType'], 'image/jpeg')
                self.assertTrue(report['allUvBytesUnchanged'])
                self.assertTrue(all(view['byteOffset'] % 4 == 0 for view in result['bufferViews']))
                self.assertEqual(document, fixture()[0], 'Input metadata mutated')

    def test_glb_roundtrip_keeps_payloads_and_chunk_alignment(self):
        document, binary = fixture()
        result, output, _ = patch_glb(document, binary, {0: JPEG + b'1'})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'asset.glb'
            write_glb(path, result, output)
            decoded, decoded_bytes = read_glb(path)
            self.assertEqual(decoded, result)
            self.assertEqual(decoded_bytes[:len(output)], output)

    def test_compressed_geometry_offsets_are_not_repacked(self):
        for extension in ('EXT_meshopt_compression', 'KHR_draco_mesh_compression'):
            document, binary = fixture()
            document['extensionsUsed'] = [extension]
            with self.subTest(extension=extension), self.assertRaisesRegex(ValueError, 'uncompressed'):
                patch_glb(document, binary, {0: JPEG})

    def test_image_matching_uses_bytes_not_unrelated_names(self):
        document, binary = fixture()
        self.assertEqual(find_image_by_packed_hash(document, binary, PNG), 0)
        with self.assertRaisesRegex(ValueError, 'found 0'):
            find_image_by_packed_hash(document, binary, b'absent')
        document['images'].append(copy.deepcopy(document['images'][0]))
        with self.assertRaisesRegex(ValueError, 'found 2'):
            find_image_by_packed_hash(document, binary, PNG)

    def test_shared_image_accessor_or_overlapping_views_fail_closed(self):
        for failure in ('shared-image', 'image-accessor', 'sparse-image', 'overlap'):
            document, binary = fixture()
            if failure == 'shared-image':
                document['images'][1]['bufferView'] = 1
            elif failure == 'image-accessor':
                document['accessors'][0]['bufferView'] = 1
            elif failure == 'sparse-image':
                document['accessors'][0]['sparse'] = {'count': 1, 'indices': {'bufferView': 3, 'componentType': 5123}, 'values': {'bufferView': 1}}
            else:
                document['bufferViews'][2]['byteOffset'] = document['bufferViews'][1]['byteOffset'] + 1
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                patch_glb(document, binary, {0: JPEG})

    def test_explicit_front_remap_preserves_fold_uv_and_position_indices(self):
        document, binary = fixture()
        remap = {'object': 'FrontLabel', 'material': 'Front paper', 'layer': 'ArtworkUV',
                 'fromRect': [.2, .3, .6, .9], 'toRect': [.1, .2, .9, .7],
                 'framingEvidence': 'Reviewed source bounds differ from replacement frame.'}
        result, output, report = patch_glb(document, binary, {0: JPEG}, [remap])
        self.assertFalse(report['allUvBytesUnchanged'])
        self.assertEqual(report['remappedUvAccessors'], [1])
        for index in (0, 3, 5):
            self.assertEqual(view_bytes(document, binary, index), view_bytes(result, output, index))
        views = [view_bytes(result, output, i) for i in range(len(result['bufferViews']))]
        values = accessor_values(result, views, 1)
        for actual, expected in zip(values, [(.1, .8), (.9, .8), (.1, .3)]):
            for a, e in zip(actual, expected):
                self.assertAlmostEqual(a, e, places=6)
        self.assertEqual(remap_uv((.2, .3), remap), (.1, .2))

    def test_unjustified_duplicate_and_aliased_remaps_are_rejected(self):
        document, binary = fixture()
        remap = {'object': 'FrontLabel', 'material': 'Front paper', 'layer': 'ArtworkUV',
                 'fromRect': [0, 0, 1, 1], 'toRect': [.1, .2, .9, .8], 'framingEvidence': 'Reviewed'}
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            validate_remaps([remap, remap])
        missing = dict(remap, framingEvidence='')
        with self.assertRaisesRegex(ValueError, 'framingEvidence'):
            validate_remaps([missing])
        document['meshes'][0]['primitives'][1]['attributes']['TEXCOORD_0'] = 1
        with self.assertRaisesRegex(ValueError, 'unselected'):
            patch_glb(document, binary, {0: JPEG}, [remap])

    def test_uv_aliases_in_other_semantics_sparse_data_or_animation_fail(self):
        remap = {'object': 'FrontLabel', 'material': 'Front paper', 'layer': 'ArtworkUV',
                 'fromRect': [0, 0, 1, 1], 'toRect': [.1, .2, .9, .8], 'framingEvidence': 'Reviewed'}
        for failure in ('other-semantic', 'sparse-values', 'animation'):
            document, binary = fixture()
            if failure == 'other-semantic':
                document['meshes'][0]['primitives'][1]['attributes']['TEXCOORD_1'] = 1
            elif failure == 'sparse-values':
                document['accessors'][0]['sparse'] = {'count': 1, 'indices': {'bufferView': 3, 'componentType': 5123}, 'values': {'bufferView': 2}}
            else:
                document['animations'] = [{'samplers': [{'input': 2, 'output': 1}]}]
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                patch_glb(document, binary, {0: JPEG}, [remap])


if __name__ == '__main__':
    unittest.main()
