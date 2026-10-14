#!/usr/bin/env python3
"""Keep immutable releases usable when their catalog folders move."""
import contextlib
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


class RelocatedAssetTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.asset={'id':'example-game','latest':'0.2.0',
                    'manifest':'assets/reproductions/example/game/versions/0.2.0.json',
                    'displayTitle':'Example game','description':'Example reproduction','kind':'EXAMPLE'}
        (self.root/'catalog.json').write_text(json.dumps({'assets':[self.asset]}))
        self.directory=self.root/'assets/reproductions/example/game'
        (self.directory/'versions').mkdir(parents=True)
        (self.directory/'CHANGELOG.md').write_text('# Example game history\n')
        self.manifests={};self.archives={};self.snapshots={}
        for version in ('0.1.0','0.2.0'):
            preview=b'preview '+version.encode()
            preview_file=self.directory/'previews'/version/'hero.png'
            preview_file.parent.mkdir(parents=True);preview_file.write_bytes(preview)
            payload={'model.blend':b'blend','model.glb':b'glb','hero.png':preview}
            files={name:entry(data) for name,data in payload.items()}
            archive=io.BytesIO()
            with zipfile.ZipFile(archive,'w') as package:
                for name,data in payload.items():package.writestr(name,data)
                package.writestr('FILES.json',json.dumps({'assetId':'example-game','version':version,'files':files}))
            archive_bytes=archive.getvalue();name=f'example-game-{version}.zip'
            manifest={'schemaVersion':1,'id':'example-game','version':version,'creator':'Example',
                      'license':'CC-BY-NC-ND-4.0','changes':['Initial release'],
                      'nominalDimensionsMm':[1,2,3],
                      'previews':[{'view':'hero','path':f'assets/example-game/previews/{version}/hero.png',**entry(preview)}],
                      'files':files,'release':{'tag':f'example-game-v{version}',
                      'archive':{'name':name,**entry(archive_bytes),
                      'url':f'https://github.com/lincolnaleixo/retro-cartridge-models/releases/download/example-game-v{version}/{name}'}}}
            path=self.directory/'versions'/f'{version}.json'
            path.write_text(json.dumps(manifest));self.snapshots[path]=path.read_bytes()
            cached=self.root/'.downloads/example-game'/version/name
            cached.parent.mkdir(parents=True);cached.write_bytes(archive_bytes)
            self.manifests[version]=manifest;self.archives[version]=archive_bytes
        self.addCleanup(patch.stopall)
        patch.object(verify,'ROOT',self.root).start()
        patch.object(build_site,'ROOT',self.root).start()

    def assert_snapshots_unchanged(self):
        for path,data in self.snapshots.items():self.assertEqual(path.read_bytes(),data)
        self.assertFalse((self.root/'assets/example-game').exists())

    def test_catalog_verifies_all_versions_after_move(self):
        output=io.StringIO()
        with patch('sys.argv',['verify.py']),contextlib.redirect_stdout(output):verify.main()
        self.assertIn('1 assets, 2 versions',output.getvalue())
        self.assert_snapshots_unchanged()

    def test_download_finds_historical_manifest_by_stable_id(self):
        version='0.1.0';manifest=self.manifests[version]
        with patch('sys.argv',['verify.py','--download','example-game',version]),\
             patch.object(verify.urllib.request,'urlopen',return_value=io.BytesIO(self.archives[version])) as request,\
             contextlib.redirect_stdout(io.StringIO()):
            verify.main()
        request.assert_called_once_with(manifest['release']['archive']['url'],timeout=60)
        self.assert_snapshots_unchanged()

    def test_gallery_preserves_history_and_uses_relocated_previews(self):
        (self.root/'site').mkdir()
        (self.root/'site/index.html').write_text('<!-- ASSET_CARDS -->')
        for name in ('LICENSE','NOTICE.md','CREDITS.md'):(self.root/name).write_text(name)
        with patch.object(build_site.subprocess,'run') as download,contextlib.redirect_stdout(io.StringIO()):
            build_site.main()
        download.assert_not_called()
        gallery=json.loads((self.root/'_site/gallery.json').read_text())
        history_url=gallery['assets'][0]['historyUrl']
        expected='https://github.com/lincolnaleixo/retro-cartridge-models/blob/main/'
        self.assertEqual(history_url,expected+'assets/reproductions/example/game/CHANGELOG.md')
        self.assertTrue((self.root/history_url.removeprefix(expected)).is_file())
        versions=gallery['assets'][0]['versions']
        self.assertEqual([item['version'] for item in versions],['0.2.0','0.1.0'])
        for item in versions:
            self.assertEqual((self.root/'_site'/item['previews'][0]['url']).read_bytes(),
                             b'preview '+item['version'].encode())
        self.assert_snapshots_unchanged()

    def test_new_manifest_can_use_current_preview_location(self):
        manifest=self.manifests['0.2.0']
        preview={'path':'assets/reproductions/example/game/previews/0.2.0/hero.png'}
        self.assertEqual(verify.preview_path(manifest,preview),self.directory/'previews/0.2.0/hero.png')

    def test_preview_cannot_leave_its_own_directory(self):
        manifest=self.manifests['0.2.0']
        for path in ('../hero.png','/tmp/hero.png','assets/other/previews/hero.png',
                     'assets/example-game/previews/../versions/0.2.0.json',
                     'assets/example-game/previews\\hero.png'):
            with self.subTest(path=path),self.assertRaises(ValueError):
                verify.preview_path(manifest,{'path':path})
        outside=self.root/'private.png';outside.write_bytes(b'not a preview')
        (self.directory/'previews/link.png').symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'escapes'):
            verify.preview_path(manifest,{'path':'assets/example-game/previews/link.png'})

    def test_unknown_id_and_escaping_catalog_path_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown'):verify.catalog_asset('missing')
        for path in ('../versions/0.2.0.json','site/versions/0.2.0.json'):
            with self.subTest(path=path),self.assertRaises(ValueError):
                verify.manifest_path({**self.asset,'manifest':path})
        (self.root/'assets/escape').symlink_to(self.root)
        with self.assertRaisesRegex(ValueError,'escapes'):
            verify.manifest_path({**self.asset,'manifest':'assets/escape/versions/0.2.0.json'})


if __name__=='__main__':unittest.main()
