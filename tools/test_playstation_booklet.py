"""Regression limits for deleting only concealed booklet page caps."""
import copy
import math
import unittest

from playstation_booklet import hidden_cap_indices


def original_caps():
    vertices, faces = [], []
    for leaf in range(8):
        width = 119.726 - .018 * (leaf % 3)
        height = 119.706 - .014 * (leaf % 2)
        for z in (3.3005 + leaf * .125, 3.4225 + leaf * .125):
            start = len(vertices)
            vertices.extend([(6.08 - width / 2, 62.375 - height / 2, z),
                             (6.08 + width / 2, 62.375 - height / 2, z),
                             (6.08 + width / 2, 62.375 + height / 2, z),
                             (6.08 - width / 2, 62.375 + height / 2, z)])
            faces.append(list(range(start, start + 4)))
        # A representative narrow side face must remain, despite using the
        # same vertices and cap depths as the selected broad surfaces.
        faces.append([start - 4, start - 3, start + 1, start])
    return vertices, faces


class PlayStationBookletTests(unittest.TestCase):
    def test_removes_all_sixteen_caps_but_keeps_edge_bands(self):
        vertices, faces = original_caps()
        before = copy.deepcopy((vertices, faces))
        selected = hidden_cap_indices(vertices, faces)
        self.assertEqual(selected, [i for i in range(24) if i % 3 != 2])
        self.assertEqual((vertices, faces), before)
        remaining = [f for i, f in enumerate(faces) if i not in selected]
        self.assertEqual(len(remaining), 8)
        self.assertEqual(hidden_cap_indices(vertices, remaining), [])

    def test_rejects_partial_or_duplicate_cap_deletion(self):
        vertices, faces = original_caps()
        for invalid in (faces[1:], faces + [faces[0]]):
            with self.assertRaises(ValueError):
                hidden_cap_indices(vertices, invalid)

    def test_rejects_wrong_depth_or_nonplanar_cap(self):
        for whole in (False, True):
            vertices, faces = original_caps()
            for index in faces[0] if whole else faces[0][:1]:
                x, y, z = vertices[index]
                vertices[index] = (x, y, z + .01)
            with self.assertRaises(ValueError):
                hidden_cap_indices(vertices, faces)

    def test_rejects_changed_print_footprint(self):
        vertices, faces = original_caps()
        vertices = [(x + .5, y, z) for x, y, z in vertices]
        with self.assertRaises(ValueError):
            hidden_cap_indices(vertices, faces)

    def test_rejects_nonfinite_coordinates_and_invalid_polygons(self):
        vertices, faces = original_caps()
        for coordinate in (math.nan, math.inf):
            changed = list(vertices)
            changed[0] = (coordinate, 0, 0)
            with self.assertRaises(ValueError):
                hidden_cap_indices(changed, faces)
        for face in ([0, 1], [0, 1, 10000], [0, 1, 2.5]):
            with self.assertRaises(ValueError):
                hidden_cap_indices(vertices, faces + [face])


if __name__ == '__main__':
    unittest.main()
