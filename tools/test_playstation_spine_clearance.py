"""Behavioral regression limits for tray-to-paper left-spine clearance."""
import math
import unittest

from boxes_playstation import left_spine_affine


class PlayStationSpineClearanceTests(unittest.TestCase):
    def test_all_37_parts_clear_paper_and_preserve_opposite_end_or_rail_width(self):
        parts = {'TrayRibbedSpineWeb': (-69.95, -56.05),
                 'TraySpineEdge_-69.65': (-70.0, -69.3)}
        parts.update({f'TraySpineCorrugation_{i:02}': (-69.8, -56.6) for i in range(35)})
        self.assertEqual(len(parts), 37)
        for name, (low, high) in parts.items():
            with self.subTest(name=name):
                scale, offset = left_spine_affine(name, low, high)
                self.assertGreater(scale, 0)
                new_low, new_high = scale * low + offset, scale * high + offset
                self.assertAlmostEqual(new_low, -68.84, places=10)
                self.assertGreaterEqual(new_low - (-68.94), .1 - 1e-10)
                if name == 'TraySpineEdge_-69.65':
                    self.assertEqual(scale, 1)
                    self.assertAlmostEqual(new_high-new_low, high-low, places=10)
                    self.assertAlmostEqual(offset, 1.16, places=10)
                else:
                    self.assertAlmostEqual(new_high, high, places=10)
                    self.assertLess(scale, 1)
                repeated = left_spine_affine(name, new_low, new_high)
                self.assertAlmostEqual(repeated[0], 1, places=10)
                self.assertAlmostEqual(repeated[1], 0, places=10)

    def test_already_clear_parts_are_not_moved(self):
        for name in ('TrayRibbedSpineWeb', 'TraySpineCorrugation_17', 'TraySpineEdge_-69.65'):
            self.assertEqual(left_spine_affine(name, -68.7, -56.6), (1, 0))

    def test_does_not_accept_unrelated_or_out_of_range_names(self):
        for name in ('RearLabel', 'TrayCardInside', 'FrontLid', 'Disc',
                     'TraySpineEdge_-56.5', 'TraySpineCorrugation_35',
                     'TraySpineCorrugation_1', 'TraySpineCorrugation_17.copy'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                left_spine_affine(name, -69.8, -56.6)

    def test_invalid_extent_cannot_collapse_or_invert_a_part(self):
        for low, high in ((math.nan, -56), (-70, math.inf), (-70, -70),
                          (-56, -70), (-70, -68.84), (-70, -69)):
            with self.subTest(low=low, high=high), self.assertRaises(ValueError):
                left_spine_affine('TraySpineCorrugation_00', low, high)


if __name__ == '__main__':
    unittest.main()
