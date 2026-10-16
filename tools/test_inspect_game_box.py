"""Reject packaging exports with broken artwork, pivots or opening animation."""
import copy
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

from inspect_game_box import compare_geometry, inspect
from inspect_glb import ValidationError, inspect as inspect_cartridge
from test_inspect_glb import encode, fixture as geometry_fixture
from box_contents import compose


def fixture():
    document, raw = geometry_fixture()
    binary = bytearray(raw)
    # glTF image V grows downward, opposite the outward-facing XY triangle.
    for offset in (16, 36, 56):
        value, = struct.unpack_from('<f', binary, offset)
        struct.pack_into('<f', binary, offset, 1.0 - value)
    binary.extend(b'\0' * (-len(binary) % 4))

    def accessor(rows, kind):
        start = len(binary)
        flat = [number for row in rows for number in row]
        binary.extend(struct.pack('<' + 'f' * len(flat), *flat))
        document['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': len(binary) - start})
        document['accessors'].append({'bufferView': len(document['bufferViews']) - 1,
                                      'componentType': 5126, 'count': len(rows), 'type': kind})
        return len(document['accessors']) - 1

    closed = [0, 0, 0, 1]
    opened = [0, -math.sqrt(.5), 0, math.sqrt(.5)]
    time_input = accessor([(0,), (2,)], 'SCALAR')
    rotation_output = accessor([closed, opened], 'VEC4')
    document['buffers'][0]['byteLength'] = len(binary)
    document['nodes'] = [
        {'name': 'FrontPrint', 'mesh': 0, 'extras': {'artworkSlot': 'Front'}},
        {'name': 'BackPrint', 'mesh': 0, 'extras': {'artworkSlot': 'Back'}},
        {'name': 'Lid', 'children': [0], 'extras': {'boxHinge': True, 'hingeAxis': 'Y',
          'closedAngleDegrees': 0, 'openAngleDegrees': -90,
          'closedQuaternion': closed, 'openQuaternion': opened}},
        {'name': 'Box', 'children': [1, 2]},
    ]
    document['scenes'][0]['nodes'] = [3]
    document['animations'] = [{'name': 'Open', 'samplers': [
        {'input': time_input, 'output': rotation_output, 'interpolation': 'LINEAR'}],
        'channels': [{'sampler': 0, 'target': {'node': 2, 'path': 'rotation'}}]}]
    return document, bytes(binary)


def replace_accessor(document, binary, accessor_index, values):
    item = document['accessors'][accessor_index]
    view = document['bufferViews'][item['bufferView']]
    start = view.get('byteOffset', 0) + item.get('byteOffset', 0)
    update = struct.pack('<' + 'f' * len(values), *values)
    return binary[:start] + update + binary[start + len(update):]


class PackagingContractTests(unittest.TestCase):
    def check_model(self, document, binary, inspector=inspect):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.glb'
            path.write_bytes(encode(document, binary))
            return inspector(path)

    def invalid(self, document, binary, message):
        with self.assertRaisesRegex(ValidationError, message):
            self.check_model(document, binary)

    def test_valid_packaging_has_world_bounds_and_open_clip(self):
        result = self.check_model(*fixture())
        self.assertEqual(result['artworkSlots'], {'FrontPrint': 'Front', 'BackPrint': 'Back'})
        self.assertEqual(result['animation']['durationSeconds'], 2)
        self.assertAlmostEqual(result['worldVertexBounds']['open']['max'][2], 2)

    def test_cartridge_contract_remains_strict(self):
        with self.assertRaisesRegex(ValidationError, 'missing front label'):
            self.check_model(*fixture(), inspector=inspect_cartridge)

    def test_missing_slot_and_uv_fail(self):
        document, binary = fixture()
        del document['nodes'][0]['extras']['artworkSlot']
        self.invalid(document, binary, 'missing Front artwork')
        document, binary = fixture()
        del document['meshes'][0]['primitives'][0]['attributes']['TEXCOORD_0']
        self.invalid(document, binary, 'artwork missing TEXCOORD_0')

    def test_wrap_back_is_supported(self):
        document, binary = fixture()
        document['nodes'][1]['extras']['artworkSlot'] = 'WrapBack'
        self.assertEqual(self.check_model(document, binary)['status'], 'passed')

    def test_mirrored_print_is_rejected_even_with_normalized_uvs(self):
        document, raw = fixture()
        binary = bytearray(raw)
        for offset in (12, 32, 52):
            value, = struct.unpack_from('<f', binary, offset)
            struct.pack_into('<f', binary, offset, 1.0 - value)
        self.invalid(document, bytes(binary), 'mirrored artwork UV orientation')

    def test_rotated_print_keeps_readable_handedness(self):
        document, raw = fixture()
        binary = bytearray(raw)
        for offset in (12, 32, 52):
            u, v = struct.unpack_from('<2f', binary, offset)
            struct.pack_into('<2f', binary, offset, v, 1.0 - u)
        self.assertEqual(self.check_model(document, bytes(binary))['status'], 'passed')

    def test_out_of_range_and_nonfinite_uvs_fail(self):
        for value, message in [(1.25, 'outside normalized'), (float('nan'), 'non-finite')]:
            document, binary = fixture()
            binary = binary[:12] + struct.pack('<f', value) + binary[16:]
            self.invalid(document, binary, message)

    def test_missing_duplicate_and_wrong_animation_targets_fail(self):
        document, binary = fixture()
        del document['animations']
        self.invalid(document, binary, 'named Open animation')
        document, binary = fixture()
        document['animations'][0]['channels'][0]['target']['node'] = 0
        self.invalid(document, binary, 'unique hinge rotation')
        document, binary = fixture()
        document['animations'][0]['channels'].append(copy.deepcopy(document['animations'][0]['channels'][0]))
        self.invalid(document, binary, 'every hinge exactly once')

    def test_wrong_duration_and_key_order_fail(self):
        document, binary = fixture()
        time_input = document['animations'][0]['samplers'][0]['input']
        self.invalid(document, replace_accessor(document, binary, time_input, [0, 3]), '0 to 2 seconds')
        document, binary = fixture()
        item = document['accessors'][time_input]
        old_view = document['bufferViews'][item['bufferView']]
        document['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': 12})
        document['accessors'][time_input] = {**item, 'bufferView': len(document['bufferViews']) - 1, 'count': 3}
        binary += struct.pack('<3f', 0, -1, 2)
        output = document['animations'][0]['samplers'][0]['output']
        document['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': 48})
        document['accessors'][output] = {**document['accessors'][output], 'bufferView': len(document['bufferViews']) - 1, 'count': 3}
        binary += struct.pack('<12f', 0, 0, 0, 1, 0, 0, 0, 1, 0, -math.sqrt(.5), 0, math.sqrt(.5))
        document['buffers'][0]['byteLength'] = len(binary)
        self.invalid(document, binary, 'increase strictly')

    def test_nonunit_quaternion_fails(self):
        document, binary = fixture()
        document['nodes'][2]['extras']['openQuaternion'] = [0, 0, 0, 2]
        self.invalid(document, binary, 'normalized')
        document, binary = fixture()
        output = document['animations'][0]['samplers'][0]['output']
        self.invalid(document, replace_accessor(document, binary, output, [0, 0, 0, 2]), 'normalized')

    def test_default_closed_pose_and_endpoints_are_verified(self):
        document, binary = fixture()
        document['nodes'][2]['rotation'] = document['nodes'][2]['extras']['openQuaternion']
        self.invalid(document, binary, 'default node transform is not closed')
        document, binary = fixture()
        output = document['animations'][0]['samplers'][0]['output']
        binary = replace_accessor(document, binary, output, [0, 0, 0, 1, 0, 0, 0, 1])
        self.invalid(document, binary, 'endpoints differ')

    def test_antipodal_quaternion_is_the_same_rotation(self):
        document, binary = fixture()
        document['nodes'][2]['rotation'] = [0, 0, 0, -1]
        self.assertEqual(self.check_model(document, binary)['status'], 'passed')

    def test_cycle_duplicate_parent_and_unreachable_node_fail(self):
        document, binary = fixture()
        document['nodes'][0]['children'] = [3]
        self.invalid(document, binary, 'cycle')
        document, binary = fixture()
        document['nodes'][3]['children'].append(0)
        self.invalid(document, binary, 'multiple parents')
        document, binary = fixture()
        document['nodes'].append({'name': 'Unreachable'})
        self.invalid(document, binary, 'unreachable')

    def test_duplicate_part_names_and_matrix_hinge_fail(self):
        document, binary = fixture()
        document['nodes'][1]['name'] = 'FrontPrint'
        self.invalid(document, binary, 'unique name')
        document, binary = fixture()
        document['nodes'][2]['matrix'] = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        self.invalid(document, binary, 'cannot use matrix')

    def test_external_resource_and_invalid_embedded_image_fail(self):
        document, binary = fixture()
        document['images'] = [{'uri': 'cover.png'}]
        self.invalid(document, binary, 'embedded')
        document, binary = fixture()
        document['images'] = [{'bufferView': 0, 'mimeType': 'image/png'}]
        self.invalid(document, binary, 'do not match image/png')

    def test_missing_texture_source_fails(self):
        document, binary = fixture()
        document['textures'] = [{'source': 3}]
        self.invalid(document, binary, 'out of range')


class ComposedPackagingTests(unittest.TestCase):
    def make_files(self, directory, parent='Lid'):
        box, raw = fixture()
        media, media_raw = geometry_fixture()
        media_raw += b'\0' * (-len(media_raw) % 4)
        model, binary, receipt = compose(box, raw, media, media_raw, parent,
            [0, 0, .2], [0, 0, 0, 1], 'test-cartridge', '1.0.0')
        receipt.update(schemaVersion=1, status='passed',
                       mediaSource={'assetId': 'test-cartridge', 'version': '1.0.0'})
        template = Path(directory) / 'template' / 'box.glb'
        output = Path(directory) / 'composed' / 'box.glb'
        template.parent.mkdir(); output.parent.mkdir()
        template.write_bytes(encode(box, raw))
        output.write_bytes(encode(model, binary))
        output.with_name('content-composition.json').write_text(json.dumps(receipt))
        return template, output, model, binary, receipt

    def test_full_scene_bounds_and_contents_follow_their_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            _, output, _, _, _ = self.make_files(directory)
            result = inspect(output)
            self.assertEqual(result['contents']['mediaAssetId'], 'test-cartridge')
            self.assertEqual(result['contents']['meshNodes'], 2)
            self.assertEqual(result['artworkSlots'], {'FrontPrint': 'Front', 'BackPrint': 'Back'})
            self.assertEqual(result['hinges'], ['Lid'])
            bounds = result['contents']['worldVertexBounds']
            self.assertNotEqual(bounds['closed'], bounds['open'])
            self.assertLess(bounds['open']['min'][0], -.19)
            self.assertEqual(compare_geometry(Path(directory) / 'template' / 'box.glb', output)['scope'], 'packaging-only')

    def test_composition_needs_a_valid_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            _, output, _, _, _ = self.make_files(directory)
            output.with_name('content-composition.json').unlink()
            with self.assertRaisesRegex(ValidationError, 'adjacent receipt'):
                inspect(output)

    def test_box_geometry_changes_are_not_hidden_by_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            template, output, model, binary, _ = self.make_files(directory)
            binary = struct.pack('<f', .25) + binary[4:]
            output.write_bytes(encode(model, binary))
            with self.assertRaisesRegex(ValidationError, 'POSITION values changed'):
                compare_geometry(template, output)

    def test_media_resources_are_still_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            _, output, model, binary, _ = self.make_files(directory)
            model['images'] = [{'uri': 'missing-media.png'}]
            output.write_bytes(encode(model, binary))
            with self.assertRaisesRegex(ValidationError, 'embedded'):
                inspect(output)


class TemplateParityTests(unittest.TestCase):
    def compare(self, before, after, allowed_uv_mirrors=()):
        with tempfile.TemporaryDirectory() as directory:
            template, reproduction = Path(directory) / 'template.glb', Path(directory) / 'reproduction.glb'
            template.write_bytes(encode(*before))
            reproduction.write_bytes(encode(*after))
            return compare_geometry(template, reproduction, allowed_uv_mirrors)

    def test_declared_u_migration_is_exact_and_required(self):
        before = fixture()
        document, raw = copy.deepcopy(before)
        binary = bytearray(raw)
        for offset in (12, 32, 52):
            value, = struct.unpack_from('<f', binary, offset)
            struct.pack_into('<f', binary, offset, 1.0 - value)
        names = ('FrontPrint', 'BackPrint')  # This fixture shares one mesh.
        result = self.compare(before, (document, bytes(binary)), names)
        self.assertFalse(result['artworkUvsIdentical'])
        self.assertTrue(result['positionsNormalsIndicesIdentical'])
        self.assertEqual({item['node'] for item in result['declaredArtworkUvMirrors']}, set(names))
        with self.assertRaisesRegex(ValidationError, 'TEXCOORD_0 values changed'):
            self.compare(before, (document, bytes(binary)), ('FrontPrint',))
        with self.assertRaisesRegex(ValidationError, 'not applied exactly once'):
            self.compare(before, before, names)
        struct.pack_into('<f', binary, 16, .5)
        with self.assertRaisesRegex(ValidationError, 'targeted U reflection'):
            self.compare(before, (document, bytes(binary)), names)

    def test_print_material_changes_preserve_geometry(self):
        before = fixture()
        document, binary = copy.deepcopy(before)
        document['materials'][0]['pbrMetallicRoughness'] = {'baseColorFactor': [.1, .2, .3, 1]}
        result = self.compare(before, (document, binary))
        self.assertTrue(result['positionsNormalsUvsIndicesIdentical'])
        self.assertTrue(result['animationKeysIdentical'])

    def test_changed_position_or_uv_is_rejected(self):
        for offset, message in [(0, 'POSITION values changed'), (12, 'TEXCOORD_0 values changed')]:
            before = fixture()
            document, binary = copy.deepcopy(before)
            binary = binary[:offset] + struct.pack('<f', .25) + binary[offset + 4:]
            with self.assertRaisesRegex(ValidationError, message):
                self.compare(before, (document, binary))

    def test_changed_triangle_winding_is_rejected(self):
        before = fixture()
        document, binary = copy.deepcopy(before)
        binary = binary[:60] + struct.pack('<3H', 0, 2, 1) + binary[66:]
        with self.assertRaisesRegex(ValidationError, 'triangle indices changed'):
            self.compare(before, (document, binary))

    def test_changed_pivot_and_animation_are_rejected(self):
        before = fixture()
        document, binary = copy.deepcopy(before)
        document['nodes'][2]['translation'] = [.01, 0, 0]
        with self.assertRaisesRegex(ValidationError, 'default transform changed'):
            self.compare(before, (document, binary))
        document, binary = copy.deepcopy(before)
        time = document['animations'][0]['samplers'][0]['input']
        binary = replace_accessor(document, binary, time, [0, 1.5])
        with self.assertRaisesRegex(ValidationError, 'animation key data changed'):
            self.compare(before, (document, binary))

    def test_only_unambiguous_static_mesh_names_can_change(self):
        document, binary = fixture()
        document['nodes'].append({'name': 'Lid paper group', 'mesh': 0})
        document['nodes'][2]['children'].append(4)
        after = copy.deepcopy(document)
        after['nodes'][4]['name'] = 'BookletPages'
        result = self.compare((document, binary), (after, binary))
        self.assertEqual(result['staticMeshNameAliases'], {'BookletPages': 'Lid paper group'})
        after['nodes'][0]['name'] = 'RenamedFrontPrint'
        with self.assertRaisesRegex(ValidationError, 'named scene parts changed'):
            self.compare((document, binary), (after, binary))

    def test_float_rounding_only_allowed_on_unprinted_uvs(self):
        document, binary = fixture()
        for node in document['nodes'][:2]:
            node['extras'] = {}
        modified = binary[:32] + struct.pack('<f', 1.0 - 5.960464477539063e-8) + binary[36:]
        result = self.compare((document, binary), (document, modified))
        self.assertTrue(result['positionsNormalsIndicesIdentical'])
        self.assertFalse(result['positionsNormalsUvsIndicesIdentical'])
        self.assertEqual(result['nonArtworkUvFloat32Rounding'][0]['maximumDelta'], 5.960464477539063e-8)
        modified = binary[:32] + struct.pack('<f', .9999) + binary[36:]
        with self.assertRaisesRegex(ValidationError, 'TEXCOORD_0 values changed'):
            self.compare((document, binary), (document, modified))


if __name__ == '__main__':
    unittest.main()
