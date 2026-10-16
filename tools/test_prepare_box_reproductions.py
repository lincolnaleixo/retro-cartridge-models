"""Release guards for versioned box-template dependencies and changelog history."""
import json
from pathlib import Path
import tempfile
import unittest

from prepare_box_reproductions import (changelog_with_history, release_changes,
                                       resolve_template)


class ReproductionReleaseTests(unittest.TestCase):
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
