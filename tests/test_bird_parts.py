"""Partial-label contracts for the independent eye point branch (CPU only)."""
import sys
import unittest
import math
import tempfile
from unittest.mock import patch
from pathlib import Path

import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/training'))

try:
    from bird_parts_model import eye_loss, classification_validity, derived_community_background, BirdDataset, distillation_loss
except ModuleNotFoundError as exc:
    if exc.name and exc.name.startswith('ultralytics'):
        eye_loss = None
    else:
        raise


@unittest.skipIf(eye_loss is None, 'Optional pinned Ultralytics runtime not installed')
class PartialEyeLossTests(unittest.TestCase):
    def sample(self, **fields):
        return dict(eyes=[], eye_complete=False, absent=False,
                    negative_regions=[], uncertain=[], **fields)

    def test_missing_eyes_have_zero_loss_and_gradient(self):
        values = torch.zeros(1, 32, 48, 2, 3, requires_grad=True)
        loss, _ = eye_loss(values, [self.sample()])
        loss.backward()
        self.assertEqual(loss.item(), 0)
        self.assertEqual(values.grad.abs().sum().item(), 0)

    def test_eye_only_label_needs_no_bird_or_head_box(self):
        values = torch.zeros(1, 32, 48, 2, 3, requires_grad=True)
        sample = self.sample(); sample['eyes'] = [[35., 41.]]
        loss, _ = eye_loss(values, [sample])
        loss.backward()
        self.assertGreater(loss.item(), 0)
        self.assertLess(values.grad[0, 5, 4, :, 2].sum().item(), 0)
        self.assertEqual(values.grad[0, 20, 20].abs().sum().item(), 0)

    def test_two_eyes_can_share_one_cell(self):
        values = torch.zeros(1, 32, 48, 2, 3, requires_grad=True)
        sample = self.sample(); sample['eyes'] = [[33., 41.], [38., 44.]]
        loss, parts = eye_loss(values, [sample]); loss.backward()
        self.assertEqual(parts['overflow'], 0)
        self.assertTrue((values.grad[0, 5, 4, :, 2] < 0).all())

    def test_known_absence_provides_negative_confidence_supervision(self):
        values = torch.zeros(1, 32, 48, 2, 3, requires_grad=True)
        sample = self.sample(); sample['absent'] = True
        loss, _ = eye_loss(values, [sample]); loss.backward()
        self.assertGreater(values.grad[..., 2].sum().item(), 0)
        self.assertEqual(values.grad[..., :2].abs().sum().item(), 0)

    def test_reviewed_body_supplies_background_but_not_missing_head_negatives(self):
        sample = self.sample(); sample.update(source='community',
            objects=[dict(kind='bird', box=[20, 20, 80, 80])], negative_regions=[[20, 20, 80, 80]])
        points = torch.tensor([[50., 50.], [200., 200.]])
        valid = classification_validity([sample], points)
        self.assertFalse(valid[0, 0, 1])  # missing head inside bird remains unknown
        self.assertTrue(valid[0, 1].all())  # clear background can reject B and H

    def test_public_focal_bird_does_not_enable_global_background(self):
        sample = self.sample(); sample.update(source='CUB-200-2011',
            objects=[dict(kind='bird', box=[20, 20, 80, 80])])
        self.assertFalse(derived_community_background(sample, torch.tensor([[200., 200.]])).any())

    def test_head_only_review_does_not_enable_global_background(self):
        sample = self.sample(); sample.update(source='community',
            objects=[dict(kind='head', box=[20, 20, 80, 80])])
        self.assertFalse(derived_community_background(sample, torch.tensor([[200., 200.]])).any())

    def test_uncertain_region_and_eye_are_protected_from_background(self):
        sample = self.sample(); sample.update(source='community', eyes=[[180, 180]],
            objects=[dict(kind='bird', box=[20, 20, 80, 80])], uncertain=[[200, 20, 250, 50]])
        mask = derived_community_background(sample, torch.tensor([[180., 180.], [220., 30.], [350., 230.]]))
        self.assertEqual(mask.tolist(), [False, False, True])

    def test_scale_matching_updates_geometry_and_ignores_unusable_eye(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'input.png'
            Image.new('RGB', (384, 256), 'green').save(path)
            sample = self.sample()
            sample.update(path=str(path), source='CUB-200-2011', eye_complete=True,
                          eyes=[[170, 110]], head_labels_are_weak=True,
                          objects=[dict(kind='bird', box=[100, 80, 300, 200]),
                                   dict(kind='head', box=[150, 90, 210, 150])],
                          negative_regions=[[100, 80, 300, 200]])
            with patch('numpy.random.random', side_effect=[1., 0., 1., 1.]), \
                 patch('numpy.random.randint', return_value=0):
                pixels, transformed = BirdDataset([sample], True, [20.])[0]
            body = next(o['box'] for o in transformed['objects'] if o['kind'] == 'bird')
            self.assertAlmostEqual(max(body[2] - body[0], body[3] - body[1]), 20., delta=1.)
            self.assertEqual(transformed['eyes'], [])
            self.assertFalse(transformed['eye_complete'])
            self.assertEqual(sample['eyes'], [[170, 110]])
            self.assertEqual(tuple(pixels.shape), (3, 256, 384))

    def test_sparse_teacher_cannot_add_uncorroborated_eye(self):
        def raw():
            return {'kpts': torch.zeros(1, 6, 32 * 48), 'feats': [torch.zeros(1, 1, 32, 48)]}
        student, teacher = raw(), raw()
        student['kpts'].requires_grad_(True)
        idx = 5 * 48 + 4
        teacher['kpts'][0, 0, idx] = math.log(.375 / .625)
        teacher['kpts'][0, 1, idx] = math.log(.125 / .875)
        teacher['kpts'][0, 2, idx] = 10.
        loss, count = distillation_loss(student, teacher, [{'eyes': [[35., 41.]]}], .95)
        self.assertEqual(count, 1)
        self.assertGreater(loss.item(), 0)
        teacher['kpts'][0, :2, idx] = 10.  # same confidence, geometrically wrong point
        loss, count = distillation_loss(student, teacher, [{'eyes': [[35., 41.]]}], .95)
        self.assertEqual(count, 0)
        self.assertEqual(loss.item(), 0)

    def test_sparse_teacher_aligns_unordered_student_slots(self):
        student = {'kpts': torch.zeros(1, 6, 32 * 48), 'feats': [torch.zeros(1, 1, 32, 48)]}
        teacher = {'kpts': torch.zeros(1, 6, 32 * 48), 'feats': [torch.zeros(1, 1, 32, 48)]}
        idx = 5 * 48 + 4
        x, y = math.log(.375 / .625), math.log(.125 / .875)
        student['kpts'][0, :2, idx] = 10.
        student['kpts'][0, 3, idx] = x; student['kpts'][0, 4, idx] = y
        teacher['kpts'][0, 0, idx] = x; teacher['kpts'][0, 1, idx] = y
        teacher['kpts'][0, 2, idx] = 10.
        student['kpts'].requires_grad_(True)
        loss, count = distillation_loss(student, teacher, [{'eyes': [[35., 41.]]}], .95)
        loss.backward()
        self.assertEqual(count, 1)
        self.assertEqual(student['kpts'].grad[0, 2, idx].item(), 0)
        self.assertLess(student['kpts'].grad[0, 5, idx].item(), 0)

    def test_teacher_duplicates_do_not_create_two_positives_for_one_eye(self):
        student = {'kpts': torch.zeros(1, 6, 32 * 48), 'feats': [torch.zeros(1, 1, 32, 48)]}
        teacher = {'kpts': torch.zeros(1, 6, 32 * 48), 'feats': [torch.zeros(1, 1, 32, 48)]}
        idx = 5 * 48 + 4
        for offset in (0, 3):
            teacher['kpts'][0, offset, idx] = math.log(.375 / .625)
            teacher['kpts'][0, offset + 1, idx] = math.log(.125 / .875)
            teacher['kpts'][0, offset + 2, idx] = 10.
        _, count = distillation_loss(student, teacher, [{'eyes': [[35., 41.]]}], .95)
        self.assertEqual(count, 1)


if __name__ == '__main__':
    unittest.main()
