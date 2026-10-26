"""Verify that class competition exempts only its actual spatial targets."""
import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'training'))
from z8_training_targets import partial_loss, match_metrics


class CompetitionPreservationTests(unittest.TestCase):
    def evaluate(self, col):
        outputs = {k: torch.zeros(1, 22, h, w, requires_grad=True)
                   for k, h, w in [('fine', 16, 24), ('coarse', 8, 12)]}
        with torch.no_grad():
            outputs['fine'][0, 5, 2, col] = 2
        sample = dict(
            targets=[dict(head='fine', anchor=0, row=2, col=10,
                          xy=[.5, .5], log_wh=None, class_slot=2,
                          kind='eye', allowed_slots=[0, 1, 2, 3, 4, 5])],
            negative_targets=[], document={'presence': 'present'},
            heads={k: torch.zeros_like(v) for k, v in outputs.items()})
        loss, parts = partial_loss(outputs, [sample], preservation=10, competition=.1)
        loss.backward()
        return parts, outputs['fine'].grad[0, 5, 2, col].item()

    def test_actual_competing_logit_has_no_teacher_conflict(self):
        parts, gradient = self.evaluate(10)
        self.assertEqual(parts['preservation'], 0)
        self.assertGreater(gradient, 0)  # gradient descent suppresses competing class

    def test_unrelated_cell_keeps_teacher_constraint(self):
        parts, gradient = self.evaluate(0)
        self.assertGreater(parts['preservation'], 0)
        self.assertGreater(gradient, 0)

    def test_explicit_part_absence_differs_from_unknown(self):
        row = dict(image_id='x', leakage_group_id='g', document=dict(
            presence='present', items=[], known_absent_parts=['eye']))
        predictions = {'x': [dict(kind='eye', point_xy=[10, 10], box_xyxy=None, score=1.)]}
        measured, _ = match_metrics([row], predictions)
        self.assertEqual(measured['eye']['fp'], 1)
        self.assertNotIn('images', measured['head'])


if __name__ == '__main__':
    unittest.main()
