"""Regression checks for portable packaging clips and immutable mesh buffers."""
import copy
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from box_animation import append_open_animation, read_glb, write_glb


class BoxAnimationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'box.glb'
        self.binary = struct.pack('<4f', 0.1, 0.2, 0.3, 1)
        self.document = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength':16}],
                         'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':16}],
                         'nodes':[{'name':'Root','children':[1]}, {'name':'Lid','translation':[0.1,0.2,0]}],
                         'scenes':[{'nodes':[0]}], 'scene':0}
        self.hinge = {'name':'Lid','closedQuaternion':[0,0,0,1],
                       'openQuaternion':[0,math.sin(-math.pi/4),0,math.cos(-math.pi/4)]}
        write_glb(self.path,self.document,self.binary)

    def values(self, document, binary, index, width):
        accessor = document['accessors'][index]
        view = document['bufferViews'][accessor['bufferView']]
        return struct.unpack_from('<' + 'f' * accessor['count'] * width,binary,view['byteOffset'])

    def test_hinge_animation_preserves_model_and_exact_buffer_bytes(self):
        append_open_animation(self.path,[self.hinge])
        doc,binary = read_glb(self.path)
        self.assertEqual(binary[:len(self.binary)],self.binary)
        self.assertEqual(doc['nodes'],self.document['nodes'])
        self.assertEqual(doc['bufferViews'][0],self.document['bufferViews'][0])
        clip = doc['animations'][0]
        self.assertEqual(clip['name'],'Open')
        self.assertEqual(clip['channels'][0]['target'],{'node':1,'path':'rotation'})
        sampler=clip['samplers'][0]
        self.assertEqual(self.values(doc,binary,sampler['input'],1),(0,2))
        vals=self.values(doc,binary,sampler['output'],4)
        for actual,expected in zip(vals,self.hinge['closedQuaternion']+self.hinge['openQuaternion']):
            self.assertAlmostEqual(actual,expected,places=6)

    def test_phased_flap_waits_in_closed_pose(self):
        self.hinge['animationPhase']=0.25
        append_open_animation(self.path,[self.hinge])
        doc,binary=read_glb(self.path)
        sampler=doc['animations'][0]['samplers'][0]
        self.assertEqual(self.values(doc,binary,sampler['input'],1),(0,0.5,2))
        self.assertEqual(self.values(doc,binary,sampler['output'],4)[:8],(0,0,0,1)*2)

    def test_missing_hinge_does_not_rewrite_file(self):
        before=self.path.read_bytes()
        self.hinge['name']='Missing'
        with self.assertRaises(ValueError):append_open_animation(self.path,[self.hinge])
        self.assertEqual(self.path.read_bytes(),before)

    def test_rejects_duplicate_hinge(self):
        with self.assertRaises(ValueError):append_open_animation(self.path,[self.hinge,self.hinge])

    def test_rejects_inconsistent_closed_pose(self):
        self.hinge['closedQuaternion']=self.hinge['openQuaternion']
        with self.assertRaises(ValueError):append_open_animation(self.path,[self.hinge])

    def test_rejects_matrix_animated_node(self):
        self.document['nodes'][1]['matrix']=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
        write_glb(self.path,self.document,self.binary)
        with self.assertRaises(ValueError):append_open_animation(self.path,[self.hinge])

    def test_rejects_invalid_quaternion(self):
        self.hinge['openQuaternion']=[0,0,0,2]
        with self.assertRaises(ValueError):append_open_animation(self.path,[self.hinge])

    def test_rejects_duplicate_clip(self):
        append_open_animation(self.path,[self.hinge])
        with self.assertRaises(ValueError):append_open_animation(self.path,[self.hinge])


if __name__=='__main__':unittest.main()
