import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/training'))
HAS_YOLO = importlib.util.find_spec('ultralytics') is not None
if HAS_YOLO:
    import numpy as np
    import torch
    from PIL import Image
    from bird_parts_model import eye_loss
    from train_bird_guidance import CaptureBlurDataset


@unittest.skipUnless(HAS_YOLO, 'Optional pinned YOLO runtime required')
class GuidanceLossTests(unittest.TestCase):
    def test_quality_confidence_penalizes_mislocalized_positive(self):
        sample = dict(absent=False, eye_complete=False, negative_regions=[], uncertain=[],
                      source='community', objects=[], eyes=[[4., 4.]])
        values = torch.zeros(1, 1, 1, 2, 3)
        values[..., 2] = 2.
        accurate = values.clone().requires_grad_()
        eye_loss(accurate, [sample], 2.)[0].backward()
        poor = values.clone()
        poor[0, 0, 0, :, :2] = 5.
        poor.requires_grad_()
        eye_loss(poor, [sample], 2.)[0].backward()
        self.assertLess(float(accurate.grad[0, 0, 0, 0, 2]), 0.)
        self.assertGreater(float(poor.grad[0, 0, 0, 0, 2]), 0.)
        self.assertGreater(float(poor.grad[..., :2].abs().sum()), 0.)

    def test_missing_eyes_still_supply_no_implicit_eye_negatives(self):
        sample = dict(absent=False, eye_complete=False, negative_regions=[], uncertain=[],
                      source='community', objects=[], eyes=[])
        values = torch.zeros(1, 1, 1, 2, 3, requires_grad=True)
        loss, _ = eye_loss(values, [sample], 2.)
        loss.backward()
        self.assertEqual(float(values.grad.abs().sum()), 0.)

    def test_blur_copies_labels_and_converts_eyes_to_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'image.png'
            Image.fromarray(np.zeros((256, 384, 3), np.uint8)).save(path)
            row = dict(path=str(path), objects=[dict(kind='bird', box=[20, 20, 100, 100])],
                       eyes=[[40, 40]], negative_regions=[[20, 20, 100, 100]],
                       uncertain=[], eye_complete=True, absent=False, source='CUB-200-2011')
            pixels, derived = CaptureBlurDataset([row], probability=1.)[0]
            self.assertEqual(tuple(pixels.shape), (3, 256, 384))
            self.assertFalse(derived['eye_complete'])
            self.assertEqual(derived['eyes'], [])
            self.assertEqual(derived['objects'], row['objects'])
            self.assertEqual(row['eyes'], [[40, 40]])
            self.assertTrue(derived['uncertain'])
