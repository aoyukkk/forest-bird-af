import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'training'))
from prepare_bird_parts import weak_head


class WeakHeadPreparationTests(unittest.TestCase):
    def test_single_landmark_does_not_invent_head_geometry(self):
        self.assertIsNone(weak_head({7: [20, 20, 1]}, 100, 100))

    def test_horizontal_landmarks_do_not_become_eye_band(self):
        x1, y1, x2, y2 = weak_head({2: [20, 50, 1], 7: [40, 50, 1], 10: [60, 50, 1]}, 100, 100)
        self.assertGreaterEqual((y2 - y1) / (x2 - x1), .4)

    def test_vertical_landmarks_do_not_become_thin_column(self):
        x1, y1, x2, y2 = weak_head({2: [50, 20, 1], 7: [50, 40, 1], 10: [50, 60, 1]}, 100, 100)
        self.assertGreaterEqual((x2 - x1) / (y2 - y1), .3)


if __name__ == '__main__':
    unittest.main()
