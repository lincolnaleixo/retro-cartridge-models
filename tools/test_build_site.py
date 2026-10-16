#!/usr/bin/env python3
"""Exercise gallery generation against the published packaging schema."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import build_site
import verify


def entry(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


class GalleryPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'site').mkdir()
        (self.root/'site/index.html').write_text('<!-- ASSET_CARDS -->')
        for name in ('LICENSE','NOTICE.md','CREDITS.md'):(self.root/name).write_text(name)
        self.animation={'name':'Open','durationSeconds':2.0,'channels':2}
        self.bounds={
            'closed':{'min':[-.064,0,-.013],'max':[.064,.177,.013],'dimensions':[.128,.177,.026]},
            'open':{'min':[-.214,0,-.013],'max':[.064,.177,.002],'dimensions':[.278,.177,.015]},
        }
        self.report={'file':'model.glb','status':'passed','animation':self.animation,
                     'worldVertexBounds':self.bounds}
        self.catalog=[];self.snapshots={};self.manifests={};self.packages={}
        self.add_asset('example-box',True)
        self.add_asset('example-cartridge',False)
        (self.root/'catalog.json').write_text(json.dumps({'assets':self.catalog}))
        for module in (build_site,verify):
            patcher=patch.object(module,'ROOT',self.root);patcher.start();self.addCleanup(patcher.stop)

    def add_asset(self,asset_id,animated):
        directory=self.root/'assets/templates'/asset_id
        (directory/'versions').mkdir(parents=True)
        (directory/'previews/0.1.0').mkdir(parents=True)
        preview=b'preview '+asset_id.encode()
        preview_path=directory/'previews/0.1.0/hero.png';preview_path.write_bytes(preview)
        payload={'model.glb':b'export '+asset_id.encode(),'model.blend':b'editable source','hero.png':preview}
        if animated:
            report={**self.report,'sha256':entry(payload['model.glb'])['sha256']}
            payload['glb-inspection.json']=json.dumps(report).encode()
        files={name:entry(data) for name,data in payload.items()}
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as package:
            for name,data in payload.items():package.writestr(name,data)
            package.writestr('FILES.json',json.dumps({'assetId':asset_id,'version':'0.1.0','files':files}))
        archive=stream.getvalue();archive_name=asset_id+'-0.1.0.zip'
        manifest={'schemaVersion':1,'id':asset_id,'version':'0.1.0','creator':'Example',
                  'license':'CC-BY-NC-ND-4.0','changes':['Initial release'],
                  'nominalDimensionsMm':[128,177,26],
                  'validation':{'animation':self.animation} if animated else {},
                  'previews':[{'view':'hero','path':preview_path.relative_to(self.root).as_posix(),**entry(preview)}],
                  'files':files,'release':{'tag':asset_id+'-v0.1.0',
                  'archive':{'name':archive_name,**entry(archive)}}}
        manifest_path=directory/'versions/0.1.0.json';manifest_path.write_text(json.dumps(manifest))
        cached=self.root/'.downloads'/asset_id/'0.1.0'/archive_name
        cached.parent.mkdir(parents=True);cached.write_bytes(archive)
        self.manifests[asset_id]=manifest;self.packages[asset_id]=archive
        self.snapshots.update({manifest_path:manifest_path.read_bytes(),cached:archive,preview_path:preview})
        self.catalog.append({'id':asset_id,'latest':'0.1.0','manifest':manifest_path.relative_to(self.root).as_posix(),
                             'displayTitle':asset_id,'description':'Example','kind':'TEMPLATE'})

    def test_full_build_publishes_nested_animation_and_verified_world_bounds(self):
        # Released manifests have no top-level animation or bounds. This is the
        # schema mismatch that previously hid every packaging pose control.
        manifest=self.manifests['example-box']
        self.assertNotIn('animation',manifest);self.assertNotIn('closedBounds',manifest)
        with patch.object(build_site.subprocess,'run') as download,contextlib.redirect_stdout(io.StringIO()):
            build_site.main()
        download.assert_not_called()
        assets={a['id']:a for a in json.loads((self.root/'_site/gallery.json').read_text())['assets']}
        box=assets['example-box']['versions'][0]
        self.assertEqual(box['animation'],self.animation)
        self.assertEqual(box['closedBounds'],self.bounds['closed'])
        self.assertEqual(box['openBounds'],self.bounds['open'])
        self.assertGreater(box['openBounds']['dimensions'][0],box['closedBounds']['dimensions'][0])
        self.assertEqual((self.root/'_site'/box['modelUrl']).read_bytes(),b'export example-box')
        cartridge=assets['example-cartridge']['versions'][0]
        for key in ('animation','closedBounds','openBounds'):self.assertNotIn(key,cartridge)
        for path,data in self.snapshots.items():self.assertEqual(path.read_bytes(),data)

    def metadata_with_report(self,report):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as package:package.writestr('glb-inspection.json',json.dumps(report))
        with zipfile.ZipFile(io.BytesIO(stream.getvalue())) as package:
            return build_site.viewer_metadata(self.manifests['example-box'],package,'model.glb')

    def valid_report(self):
        with zipfile.ZipFile(io.BytesIO(self.packages['example-box'])) as package:
            return json.loads(package.read('glb-inspection.json'))

    def test_report_for_another_export_or_animation_is_rejected(self):
        for key,value in [('sha256','0'*64),('file','another.glb'),('status','failed'),
                          ('animation',{'name':'Open','durationSeconds':4.0,'channels':2})]:
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'does not match'):
                report=self.valid_report();report[key]=value;self.metadata_with_report(report)

    def test_missing_nonfinite_or_inconsistent_pose_bounds_fail_the_build(self):
        for change in ('missing','nonfinite','inconsistent'):
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'world bounds'):
                report=copy.deepcopy(self.valid_report())
                if change=='missing':del report['worldVertexBounds']['open']
                if change=='nonfinite':report['worldVertexBounds']['open']['min'][0]=float('nan')
                if change=='inconsistent':report['worldVertexBounds']['open']['dimensions'][0]=278
                self.metadata_with_report(report)


if __name__=='__main__':unittest.main()
