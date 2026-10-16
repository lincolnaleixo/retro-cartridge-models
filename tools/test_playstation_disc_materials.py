"""Regression limits for the upstream disc material and hidden-top correction."""
import unittest
import math
import struct
from playstation_disc_materials import patch_document, validate_patch, correct_disc, validate_correction, release_metadata


def source():
    return {'nodes': [{'name': name, 'mesh': i} for i, name in enumerate(
        ('DiscClearHub', 'DiscInnerMatrix', 'DiscOuterRim', 'FrontLabel'))],
        'meshes': [{'primitives': [{'material': material, 'attributes': {'POSITION': i}}]}
                   for i, material in enumerate((0, 1, 1, 2))],
        'materials': [
            {'name': 'Disc transparent clamping substrate', 'pbrMetallicRoughness': {'baseColorFactor': [.38, .36, .43, .19]}, 'extensions': {'KHR_materials_transmission': {'transmissionFactor': 1}}},
            {'name': 'Disc reflective matrix band', 'pbrMetallicRoughness': {'baseColorFactor': [.39, .41, .44, 1], 'metallicFactor': .82}},
            {'name': 'Original ink', 'pbrMetallicRoughness': {'baseColorTexture': {'index': 0}}}],
        'images': [{'bufferView': 7}], 'buffers': [{'byteLength': 16}]}


def source_with_body():
    original = source()
    count = 256
    points = [(radius * math.cos(i*2*math.pi/count), .06 + radius * math.sin(i*2*math.pi/count), z)
              for z in (-.0006, .000595) for radius in (.06, .018) for i in range(count)]
    triangles = []
    for i in range(count):
        nxt = (i+1) % count
        for quad in ((i,nxt,nxt+512,i+512), (i+256,i+768,nxt+768,nxt+256),
                     (i+512,nxt+512,nxt+768,i+768), (i,i+256,nxt+256,nxt)):
            triangles.extend((quad[0],quad[1],quad[2],quad[0],quad[2],quad[3]))
    positions = struct.pack('<'+'f'*len(points)*3, *(x for row in points for x in row))
    indices = struct.pack('<'+'H'*len(triangles), *triangles)
    original['nodes'].append({'name': 'Disc', 'mesh': 4})
    original['meshes'].append({'primitives': [{'material': 2, 'attributes': {'POSITION': 0}, 'indices': 1}]})
    original['bufferViews'] = [{'buffer': 0, 'byteOffset': 0, 'byteLength': len(positions)},
                               {'buffer': 0, 'byteOffset': len(positions), 'byteLength': len(indices)}]
    original['accessors'] = [{'bufferView': 0, 'componentType': 5126, 'count': len(points), 'type': 'VEC3'},
                             {'bufferView': 1, 'componentType': 5123, 'count': len(triangles), 'type': 'SCALAR'}]
    original['buffers'][0]['byteLength'] = len(positions)+len(indices)
    return original, positions+indices


class DiscMaterialTests(unittest.TestCase):
    def test_patch_preserves_geometry_print_and_outer_rim(self):
        original = source()
        result = patch_document(original)
        self.assertEqual(original, source())
        self.assertEqual(result['nodes'], original['nodes'])
        self.assertEqual(result['materials'][1:3], original['materials'][1:3])
        self.assertEqual(result['images'], original['images'])
        self.assertEqual(result['meshes'][2:], original['meshes'][2:])
        self.assertEqual(result['meshes'][1]['primitives'][0]['material'], 3)
        self.assertEqual(validate_patch(original, b'exact geometry', result, b'exact geometry')['status'], 'passed')

    def test_rejects_changed_binary_or_undeclared_nodes(self):
        original = source()
        result = patch_document(original)
        with self.assertRaises(ValueError):
            validate_patch(original, b'A', result, b'B')
        result['nodes'][0]['translation'] = [0, 1, 0]
        with self.assertRaises(ValueError):
            validate_patch(original, b'A', result, b'A')

    def test_rejects_changed_print_and_outer_rim(self):
        original = source()
        for index in (1, 2):
            result = patch_document(original)
            result['materials'][index]['name'] = 'Unexpected'
            with self.assertRaises(ValueError):
                validate_patch(original, b'A', result, b'A')

    def test_rejects_ambiguous_shared_mesh_or_material(self):
        for kind in ('mesh', 'material'):
            original = source()
            if kind == 'mesh':
                original['nodes'].append({'name': 'Unexpected', 'mesh': 0})
            else:
                original['meshes'][3]['primitives'][0]['material'] = 0
            with self.assertRaises(ValueError):
                patch_document(original)

    def test_refuses_double_application(self):
        with self.assertRaises(ValueError):
            patch_document(patch_document(source()))

    def test_only_hidden_body_top_indices_are_removed(self):
        from inspect_glb import Accessors
        original, binary = source_with_body()
        result, after_binary = correct_disc(original, binary)
        self.assertEqual(result['accessors'][1]['count'], 4608)
        self.assertEqual(binary[:12288], after_binary[:12288])
        self.assertEqual(len(binary), len(after_binary))
        reader = Accessors(result, after_binary)
        vertices = reader.read(0)
        indices = [row[0] for row in reader.read(1)]
        self.assertFalse(any(all(abs(vertices[j][2]-.000595)<1e-9 for j in indices[i:i+3]) for i in range(0,len(indices),3)))
        self.assertEqual(validate_correction(original,binary,result,after_binary)['removedHiddenBodyTriangles'],512)
        changed = bytearray(after_binary);changed[0] ^= 1
        with self.assertRaises(ValueError):
            validate_correction(original,binary,result,bytes(changed))

    def test_rejects_shared_body_index_view_and_wrong_plane(self):
        for variant in ('shared', 'plane'):
            original,binary = source_with_body()
            if variant == 'shared':
                original['meshes'][0]['primitives'][0]['indices'] = 1
            else:
                changed = bytearray(binary)
                for index in range(512,1024):
                    struct.pack_into('<f',changed,index*12+8,.001)
                binary=bytes(changed)
            with self.assertRaises(ValueError):
                correct_disc(original,binary)

    def test_release_identification_is_finite_and_explicit(self):
        document={'nodes':[{'name':'PLAYSTATION_1_DISC','extras':{'status':'versioned textured example 0.1.0','assetVersion':'0.1.0','assetId':'playstation-1-crash-bandicoot','unrelated':'keep'}}]}
        changes=release_metadata(document,'playstation-1-crash-bandicoot')
        self.assertEqual({c['key'] for c in changes},{'status','assetVersion'})
        self.assertEqual(document['nodes'][0]['extras']['unrelated'],'keep')
        with self.assertRaises(ValueError):release_metadata(document,'playstation-1-crash-bandicoot')
        with self.assertRaises(ValueError):release_metadata(document,'another-model')


if __name__ == '__main__':
    unittest.main()
