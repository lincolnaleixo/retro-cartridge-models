"""Protect published template history when staging a new model version."""
import unittest

from prepare_box_templates import CONFIG, release_changes, versioned_changelog


class TemplateHistoryTests(unittest.TestCase):
    def test_new_release_preserves_prior_sections_verbatim(self):
        history = '## 0.1.0 — 2026-10-16\n\n- Original detail.\n\n## 0.0.1 — 2026-10-01\n\n- Earlier detail.\n'
        actual = versioned_changelog('Case', '0.2.0', '2026-10-16',
                                     ['New material.'], '# Changelog — Case\n\n' + history)
        self.assertTrue(actual.endswith(history))
        self.assertEqual(actual.count('## 0.2.0'), 1)

    def test_repeated_unpublished_stage_does_not_duplicate_sections(self):
        first = versioned_changelog('Case', '0.2.0', '2026-10-16', ['New material.'],
                                    '# Changelog — Case\n\n## 0.1.0 — 2026-10-16\n\n- Original.\n')
        self.assertEqual(first, versioned_changelog('Case', '0.2.0', '2026-10-16',
                                                   ['New material.'], first))

    def test_material_release_does_not_claim_first_release(self):
        changes = release_changes('playstation-1', CONFIG['playstation-1'], '0.2.0')
        self.assertTrue(any('alpha fallback' in change for change in changes))
        self.assertFalse(any('first independent' in change for change in changes))

    def test_unknown_update_requires_explicit_release_notes(self):
        with self.assertRaisesRegex(ValueError, 'Explicit template release notes'):
            release_changes('snes', CONFIG['snes'], '0.2.0')


if __name__ == '__main__':
    unittest.main()
