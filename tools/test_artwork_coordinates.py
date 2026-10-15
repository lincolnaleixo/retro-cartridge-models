"""Check source-photo orientation independently of Blender."""
import unittest

from artwork_coordinates import photo_uv


class PhotoCoordinatesTests(unittest.TestCase):
    def test_rotated_label_keeps_all_four_photo_corners_and_center(self):
        corners = (.22, .18, .80, .22, .76, .87, .18, .83)
        for uv, expected in [((0, 0), (.22, .18)), ((1, 0), (.80, .22)),
                             ((1, 1), (.76, .87)), ((0, 1), (.18, .83)),
                             ((.5, .5), (.49, .525))]:
            with self.subTest(uv=uv):
                for actual, value in zip(photo_uv(*uv, quadrilateral=corners), expected):
                    self.assertAlmostEqual(actual, value)

    def test_existing_crop_and_flip_contract_is_preserved(self):
        self.assertEqual(photo_uv(0, 0, (.9, .2, .1, .8)), (.9, .2))
        self.assertAlmostEqual(photo_uv(1, 1, (.9, .2, .1, .8))[0], .1)
        self.assertEqual(photo_uv(.5, .5), (.5, .5))

    def test_invalid_photo_corners_fail_instead_of_clamping_silently(self):
        for corners in [(0, 0, 1, 1), (0, 0, 1, 0, 1, 2, 0, 1)]:
            with self.assertRaises(ValueError):
                photo_uv(.5, .5, quadrilateral=corners)


if __name__ == '__main__':
    unittest.main()
