"""Regression tests for immutable published-media composition."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from box_contents import NINTENDO_LIMITATIONS, box_only, compose, validate_composition, write_glb


def fixture(name):
    return {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
            'nodes': [{'name': name, 'mesh': 0}],
            'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'indices': 0, 'material': 0}]}],
            'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 1, 'type': 'SCALAR'}],
            'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': 4}],
            'buffers': [{'byteLength': 4}], 'images': [{'bufferView': 0, 'mimeType': 'image/png'}],
            'textures': [{'source': 0, 'sampler': 0}], 'samplers': [{}],
            'materials': [{'pbrMetallicRoughness': {'baseColorTexture': {'index': 0}},
                          'extensions': {'KHR_materials_specular': {'specularTexture': {'index': 0}}}}],
            'extensionsUsed': ['KHR_materials_specular']}


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.box, self.media = fixture('Tray'), fixture('Cartridge')
        self.box_binary, self.media_binary = b'abcd', b'efgh'
        self.result, self.binary, self.receipt = compose(self.box, self.box_binary,
            self.media, self.media_binary, 'Tray', [0, .02, 0], [0, 0, 0, 1], 'game', '1.0.0')

    def test_preserves_both_byte_streams_and_box_document(self):
        self.assertEqual(self.binary, b'abcdefgh')
        recovered, binary = box_only(self.result, self.binary, self.receipt)
        self.assertEqual(recovered, self.box)
        self.assertEqual(binary, self.box_binary)

    def test_remaps_every_texture_and_geometry_reference(self):
        self.assertEqual(self.result['nodes'][1]['mesh'], 1)
        primitive = self.result['meshes'][1]['primitives'][0]
        self.assertEqual(primitive, {'attributes': {'POSITION': 1}, 'indices': 1, 'material': 1})
        self.assertEqual(self.result['accessors'][1]['bufferView'], 1)
        self.assertEqual(self.result['bufferViews'][1]['byteOffset'], 4)
        self.assertEqual(self.result['textures'][1], {'source': 1, 'sampler': 1})
        self.assertEqual(self.result['images'][1]['bufferView'], 1)
        self.assertEqual(self.result['materials'][1]['extensions']['KHR_materials_specular']['specularTexture']['index'], 1)

    def test_rejects_wrong_scale_and_extra_cross_attachment(self):
        for alteration in ('scale', 'child', 'extent'):
            document = deepcopy(self.result)
            if alteration == 'scale': document['nodes'][-1]['scale'] = [.99, 1, 1]
            elif alteration == 'child': document['nodes'][0]['children'].append(1)
            else: document['materials'].append({})
            with self.assertRaises(ValueError): box_only(document, self.binary, self.receipt)

    def test_rejects_media_bytes_or_box_material_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            box, media, output = [Path(tmp) / name for name in ('box.glb', 'media.glb', 'composed.glb')]
            write_glb(box, self.box, self.box_binary)
            write_glb(media, self.media, self.media_binary)
            write_glb(output, self.result, self.binary)
            self.assertEqual(validate_composition(box, media, output, self.receipt)['status'], 'passed')
            write_glb(output, self.result, b'abcdefg!')
            with self.assertRaises(ValueError): validate_composition(box, media, output, self.receipt)
            altered = deepcopy(self.result); altered['materials'][0]['name'] = 'changed'
            write_glb(output, altered, self.binary)
            with self.assertRaises(ValueError): validate_composition(box, media, output, self.receipt)

    def test_rejects_repeated_composition_and_animated_media(self):
        with self.assertRaises(ValueError):
            compose(self.result, self.binary, self.media, self.media_binary, 'Tray', [0, 0, 0], [0, 0, 0, 1], 'game', '1')
        self.media['animations'] = [{'name': 'unexpected'}]
        with self.assertRaises(ValueError):
            compose(self.box, self.box_binary, self.media, self.media_binary, 'Tray', [0, 0, 0], [0, 0, 0, 1], 'game', '1')

    def test_only_whitelisted_descriptive_metadata_can_be_restored(self):
        self.box['nodes'][0].update(name='NesBox', extras={'limitations': NINTENDO_LIMITATIONS, 'containsGameMedia': False})
        result, binary, receipt = compose(self.box, self.box_binary, self.media, self.media_binary,
            'NesBox', [0, .0424, 0], [0, 0, 0, 1], 'nes-super-mario-bros', '0.2.0')
        self.assertIn('Enclosed media: nes-super-mario-bros v0.2.0', result['nodes'][0]['extras']['limitations'])
        self.assertIs(result['nodes'][0]['extras']['containsGameMedia'], True)
        self.assertEqual(box_only(result, binary, receipt)[0], self.box)
        altered = deepcopy(receipt)
        altered['descriptiveMetadataOverrides'][0]['old'] = 'arbitrary original value'
        with self.assertRaises(ValueError): box_only(result, binary, altered)
        altered = deepcopy(receipt)
        altered['descriptiveMetadataOverrides'][0]['key'] = 'unrelatedProperty'
        with self.assertRaises(ValueError): box_only(result, binary, altered)


if __name__ == '__main__':
    unittest.main()
