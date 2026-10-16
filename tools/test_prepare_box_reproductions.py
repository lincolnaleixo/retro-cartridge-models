"""Release guards for versioned box-template dependencies and changelog history."""
import base64
from contextlib import contextmanager, ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import prepare_box_reproductions as release
from prepare_box_reproductions import (changelog_with_history, release_changes,
                                       resolve_template, includes_media)


@contextmanager
def audited_reproduction(version='0.4.0'):
    """Small real hash-bound files with heavyweight geometry checks stubbed out."""
    with tempfile.TemporaryDirectory() as directory, ExitStack() as patches:
        root = Path(directory)
        asset_id = release.identifier('playstation-1')
        folder = root / 'reproductions' / asset_id
        folder.mkdir(parents=True)
        glb, blend = folder / (asset_id + '.glb'), folder / (asset_id + '.blend')
        glb.write_bytes(b'audited composed export')
        blend.write_bytes(b'audited editable source')
        template = root / 'templates/playstation-1-box/playstation-1-box.glb'
        template.parent.mkdir(parents=True)
        template.write_bytes(b'audited neutral template')
        template_manifest = {'id': 'playstation-1-box', 'version': '0.2.0',
                             'files': {template.name: {'sha256': release.sha(template)}}}
        structural = {'file': glb.name, 'sha256': release.sha(glb), 'status': 'passed',
                      'artworkSlots': {}, 'geometryParity': {
                          'status': 'passed', 'templateSha256': release.sha(template),
                          'reproductionSha256': release.sha(glb)}}
        validation = {'assets': [structural], 'godot': {'assets': [
            {'id': asset_id, 'sha256': release.sha(glb), 'namedPartsPresent': True}]}}
        source = {'assets': [{'id': asset_id, 'sha256': release.sha(blend)}]}
        (folder / 'construction.json').write_text(json.dumps({'artworkSlots': {}}))
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVl8AAAAASUVORK5CYII=')
        records = []
        for view in (*release.VIEWS, 'left', 'right', 'hub-close'):
            path = folder / (view + '.png')
            path.write_bytes(png)
            records.append({'view': view, 'file': path.name, 'sha256': release.sha(path),
                            'pixels': [1, 1]})
        render_proof = {'sha256': release.sha(glb), 'renders': records}
        (folder / 'render-proof.json').write_text(json.dumps(render_proof))

        media_id = asset_id[:-4]
        media_files = {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                       for name, data in {'CREDITS.md': b'credit', 'LICENSE': b'license',
                                          'NOTICE.md': b'notice', media_id + '.glb': b'media',
                                          media_id + '.blend': b'media source'}.items()}
        manifest = {'id': media_id, 'version': '0.2.0', 'files': media_files,
                    'release': {'archive': {'sha256': 'a' * 64}}}
        manifest_path = root / 'media-manifest.json'
        manifest_path.write_text(json.dumps(manifest))
        (root / 'catalog.json').write_text(json.dumps({'assets': [
            {'id': media_id, 'latest': '0.2.0', 'manifest': manifest_path.name}]}))
        media = {'assetId': media_id, 'version': '0.2.0',
                 'manifestSha256': release.sha(manifest_path), 'archiveSha256': 'a' * 64,
                 'glbFile': media_id + '.glb', 'glbSha256': media_files[media_id + '.glb']['sha256'],
                 'blendFile': media_id + '.blend', 'blendSha256': media_files[media_id + '.blend']['sha256']}
        content_folder = folder / 'content-source'
        content_folder.mkdir()
        for name, data in [('CREDITS.md', b'credit'), ('LICENSE', b'license'),
                           ('NOTICE.md', b'notice'), ('release-manifest.json', manifest_path.read_bytes())]:
            (content_folder / name).write_bytes(data)
        composition = {'status': 'passed', 'assetId': asset_id, 'mediaSource': media,
                       'output': {'glbSha256': release.sha(glb), 'blendSha256': release.sha(blend)},
                       'contents': {'scale': [1, 1, 1]}, 'boxSource': {'glbSha256': 'b' * 64},
                       'preservation': {'status': 'passed', 'composedGlbSha256': release.sha(glb),
                                        'boxGlbSha256': 'b' * 64, 'mediaGlbSha256': media['glbSha256'],
                                        'mediaScale': [1, 1, 1]},
                       'pinnedMediaEvidence': {'files': {p.name: release.sha(p) for p in content_folder.iterdir()}}}
        (folder / 'content-composition.json').write_text(json.dumps(composition))
        fit = {'assets': [{'assetId': asset_id, 'composedGlbSha256': release.sha(glb),
                           'mediaSource': media, 'contentsLocalTransform': composition['contents'],
                           'surfaceFit': {'status': 'passed', 'poses': {
                               'closed': {'intersectionPairs': []}, 'open': {'intersectionPairs': []}}},
                           'sourceIds': ['specimen']}], 'sources': [{'id': 'specimen'}]}
        (root / 'docs').mkdir()
        fit_path = root / 'docs/box-content-fit.json'
        fit_path.write_text(json.dumps(fit))
        patches.enter_context(patch.object(release, 'ROOT', root))
        patches.enter_context(patch.object(release, 'resolve_template', return_value=(root / 'template.json', template_manifest)))
        patches.enter_context(patch.object(release, 'artwork_inputs', return_value=({}, {}, {}, {})))
        patches.enter_context(patch.object(release, 'selected_artwork_sources', return_value={'selection': {'slots': {}}}))
        patches.enter_context(patch.object(release, 'geometry_evidence', return_value={}))
        yield SimpleNamespace(args=SimpleNamespace(base=root, version=version), folder=folder,
                              validation=validation, source=source, composition=composition,
                              render_proof=render_proof, fit=fit, fit_path=fit_path)


class ReproductionReleaseTests(unittest.TestCase):
    def test_later_releases_cannot_skip_composition_guards(self):
        for version in ('0.3.0', '0.4.0', '0.10.0', '1.0.0'):
            self.assertTrue(includes_media(version), version)
        for version in ('0.1.0', '0.2.0'):
            self.assertFalse(includes_media(version), version)
        with self.assertRaises(ValueError):
            includes_media('unreleased')

    def test_later_release_audits_real_inputs_and_keeps_extra_ps1_views(self):
        with audited_reproduction() as fixture:
            result = release.audit_inputs('playstation-1', fixture.args, fixture.validation,
                                          fixture.source, {})
            self.assertEqual(result['composition'], fixture.composition)
            self.assertEqual(set(result['inspectionViews']), {'left.png', 'right.png', 'hub-close.png'})
            self.assertEqual(result['contentFit']['assets'], fixture.fit['assets'])

    def test_later_release_rejects_stale_export_render_proof(self):
        with audited_reproduction('0.10.0') as fixture:
            fixture.render_proof['sha256'] = '0' * 64
            (fixture.folder / 'render-proof.json').write_text(json.dumps(fixture.render_proof))
            with self.assertRaisesRegex(ValueError, 'rendered from a different export'):
                release.audit_inputs('playstation-1', fixture.args, fixture.validation, fixture.source, {})

    def test_later_release_rejects_invalid_composition_and_stale_fit(self):
        for failure in ('composition', 'fit'):
            with self.subTest(failure=failure), audited_reproduction('1.0.0') as fixture:
                if failure == 'composition':
                    fixture.composition['status'] = 'failed'
                    (fixture.folder / 'content-composition.json').write_text(json.dumps(fixture.composition))
                    message = 'Missing, stale or rescaled media composition'
                else:
                    fixture.fit['assets'][0]['composedGlbSha256'] = '0' * 64
                    fixture.fit_path.write_text(json.dumps(fixture.fit))
                    message = 'Incomplete or stale final media fit audit'
                with self.assertRaisesRegex(ValueError, message):
                    release.audit_inputs('playstation-1', fixture.args, fixture.validation, fixture.source, {})

    def test_preview_proof_cannot_point_to_an_unpackaged_alternative(self):
        with audited_reproduction() as fixture:
            alternate = fixture.folder / 'alternative-hero.png'
            alternate.write_bytes((fixture.folder / 'hero.png').read_bytes())
            record = next(row for row in fixture.render_proof['renders'] if row['view'] == 'hero')
            record['file'] = alternate.name
            (fixture.folder / 'render-proof.json').write_text(json.dumps(fixture.render_proof))
            with self.assertRaisesRegex(ValueError, 'Preview proof must identify its packaged view'):
                release.audit_inputs('playstation-1', fixture.args, fixture.validation, fixture.source, {})

    def test_resolves_catalog_selected_template_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'assets/templates/playstation-1/box/versions/0.2.0.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'id': 'playstation-1-box', 'version': '0.2.0'}))
            (root/'catalog.json').write_text(json.dumps({'assets': [{
                'id': 'playstation-1-box', 'latest': '0.2.0',
                'manifest': path.relative_to(root).as_posix()}]}))
            selected, manifest = resolve_template('playstation-1', root)
            self.assertEqual(selected, path)
            self.assertEqual(manifest['version'], '0.2.0')

    def test_rejects_catalog_manifest_version_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'template.json').write_text(json.dumps({'id': 'nes-box', 'version': '0.1.0'}))
            (root/'catalog.json').write_text(json.dumps({'assets': [{
                'id': 'nes-box', 'latest': '0.2.0', 'manifest': 'template.json'}]}))
            with self.assertRaisesRegex(ValueError, 'disagree'):
                resolve_template('nes', root)

    def test_changelog_retains_published_release_verbatim(self):
        history = '# Changelog — Existing title\n\n## 0.1.0 — 2026-10-16\n\n- Original release.\n'
        result = changelog_with_history('Current title', '0.2.0', '2026-10-16',
                                        ['Cleaned the rear artwork.'], history)
        self.assertIn('## 0.2.0 — 2026-10-16\n\n- Cleaned the rear artwork.', result)
        self.assertTrue(result.endswith(history.split('\n\n', 1)[1]))
        self.assertLess(result.index('## 0.2.0'), result.index('## 0.1.0'))

    def test_rejects_duplicate_release_history(self):
        with self.assertRaisesRegex(ValueError, 'already contains'):
            changelog_with_history('Title', '0.2.0', '2026-10-16', ['Changed'],
                                   '# Changelog\n\n## 0.2.0 — 2026-10-15\n\n- Earlier.\n')

    def test_refinement_notes_do_not_claim_first_release(self):
        notes = release_changes('nes', '0.2.0', '0.1.0')
        self.assertTrue(any('approximate narrow sans-serif' in item for item in notes))
        self.assertTrue(any('v0.1.0' in item for item in notes))
        self.assertFalse(any(item.startswith('Added ') for item in notes))


if __name__ == '__main__':
    unittest.main()
