import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'training'))
from z8_training_targets import match_metrics, target_builder, negative_builder, partial_loss, background_eye_masks, protected_eye_regions, local_eye_supervision, head_local_negative_mask


class TrainingTargetsTest(unittest.TestCase):
    def setUp(self):
        self.heads = {'fine': torch.zeros(1, 22, 16, 24), 'coarse': torch.zeros(1, 33, 8, 12)}
        self.tables = {'anchors': [(7, 7), (60, 60), (80, 80), (160, 140), (200, 200)],
                       'allowed_slots': {0: [0, 1, 2, 3, 4, 5], 1: [0, 1, 2, 3, 4, 5], 2: [2, 3, 4], 3: [0, 2, 3, 4], 4: [1, 2, 3, 4, 5]}}

    def row(self, items):
        return {'image_id': 'test', 'leakage_group_id': 'g1', 'baseline': [], 'document': {
            'status': 'confirmed', 'confirmed_by': {'kind': 'human'}, 'presence': 'present', 'items': items}}

    def test_eye_point_no_invented_extent_or_direction(self):
        row = self.row([{'id': 'e', 'kind': 'eye', 'point_xy': [35., 40.], 'box_xyxy': None}])
        target, = target_builder(row, self.heads, self.tables)
        self.assertIsNone(target['log_wh'])
        self.assertEqual(target['operational_union'], [2, 3])

    def test_head_only_does_not_create_body_negative(self):
        row = self.row([{'id': 'h', 'kind': 'head', 'point_xy': None, 'box_xyxy': [10, 10, 50, 50]}])
        row['baseline'] = [{'class_slot': 0, 'box_input_xyxy': [200, 100, 260, 160]}]
        targets = target_builder(row, self.heads, self.tables)
        self.assertEqual(negative_builder(row, self.heads, self.tables, targets), [])

    def test_partial_precision_ignores_unknown_parts(self):
        row = self.row([{'id': 'h', 'kind': 'head', 'point_xy': None, 'box_xyxy': [10, 10, 50, 50]}])
        predictions = {'test': [{'kind': 'bird', 'score': 999, 'box_xyxy': [100, 100, 200, 200], 'point_xy': [150, 150]},
                                 {'kind': 'head', 'score': 900, 'box_xyxy': [10, 10, 50, 50], 'point_xy': [30, 30]}]}
        metric, _ = match_metrics([row], predictions)
        self.assertEqual(metric['head']['tp'], 1)
        self.assertEqual(metric['bird'].get('fp', 0), 0)

    def test_point_matching_is_one_to_one(self):
        row = self.row([{'id': 'e', 'kind': 'eye', 'point_xy': [35, 40], 'box_xyxy': None}])
        p = {'kind': 'eye', 'score': 900, 'point_xy': [35, 40], 'box_xyxy': [32, 37, 38, 43]}
        metric, _ = match_metrics([row], {'test': [p, p]})
        self.assertEqual(metric['eye']['tp'], 1)
        self.assertEqual(metric['eye']['fp'], 1)

    def test_point_does_not_supervise_size(self):
        row = self.row([{'id': 'e', 'kind': 'eye', 'point_xy': [35., 40.], 'box_xyxy': None}])
        targets = target_builder(row, self.heads, self.tables)
        outputs = {k: v.clone().requires_grad_() for k, v in self.heads.items()}
        sample = {**row, 'targets': targets, 'negative_targets': [], 'heads': self.heads}
        loss, _ = partial_loss(outputs, [sample])
        loss.backward()
        t = targets[0]
        grad = outputs[t['head']].grad[0, t['anchor'] * 11:(t['anchor'] + 1) * 11, t['row'], t['col']]
        self.assertEqual(float(grad[2]), 0.)
        self.assertEqual(float(grad[3]), 0.)
        self.assertGreater(abs(float(grad[0])) + abs(float(grad[1])), 0.)

    def test_existing_good_native_anchor_preferred_to_new_duplicate(self):
        import math
        row = self.row([{'id': 'b', 'kind': 'bird', 'box_xyxy': [60, 60, 100, 100], 'point_xy': None}])
        self.heads['coarse'][0, 2:4, 2, 2] = math.log(.5)
        targets = target_builder(row, self.heads, self.tables)
        self.assertEqual(targets[0]['native_anchor'], 2)

    def test_positive_competition_does_not_split_eye_union(self):
        row = self.row([{'id': 'e', 'kind': 'eye', 'point_xy': [35., 40.], 'box_xyxy': None}])
        targets = target_builder(row, self.heads, self.tables)
        outputs = {k: v.clone().requires_grad_() for k, v in self.heads.items()}
        sample = {**row, 'targets': targets, 'negative_targets': [], 'heads': self.heads}
        loss, _ = partial_loss(outputs, [sample], competition=.05)
        loss.backward()
        t = targets[0]
        grad = outputs[t['head']].grad[0, t['anchor'] * 11:(t['anchor'] + 1) * 11, t['row'], t['col']]
        self.assertEqual(float(grad[8]), 0.)  # other unresolved eye slot
        self.assertGreater(float(grad[6]), 0.)  # competing known head
        self.assertEqual(float(grad[10]), 0.)  # auxiliary stays unknown

    def test_head_only_has_no_derived_background(self):
        row = self.row([{'id': 'h', 'kind': 'head', 'box_xyxy': [40, 40, 60, 60], 'point_xy': None}])
        self.assertIsNone(protected_eye_regions(row))
        self.assertFalse(any(mask.any() for mask in background_eye_masks(row).values()))

    def test_background_protects_entire_cells_and_auxiliary(self):
        row = self.row([{'id': 'b', 'kind': 'bird', 'box_xyxy': [100, 100, 130, 130], 'point_xy': None},
                        {'id': 'e', 'kind': 'eye', 'box_xyxy': None, 'point_xy': [108, 108]},
                        {'id': 'u', 'kind': 'auxiliary', 'box_xyxy': [250, 100, 300, 180], 'point_xy': None}])
        masks = background_eye_masks(row, margin=16)
        self.assertTrue(bool(masks['fine'][0, 0, 0]))
        self.assertFalse(bool(masks['fine'][0, 6, 6]))
        self.assertFalse(bool(masks['fine'][0, 6, 15]))  # overlaps auxiliary margin
        self.assertFalse(bool(masks['fine'][0, 5, 5]))  # cell edge touches bird margin

    def test_unknown_presence_never_invents_background(self):
        row = self.row([{'id': 'b', 'kind': 'bird', 'box_xyxy': [100, 100, 130, 130], 'point_xy': None}])
        row['document']['status'] = 'needs_adjudication'
        self.assertFalse(any(mask.any() for mask in background_eye_masks(row).values()))
        row['document']['status'] = 'confirmed'
        row['document']['presence'] = 'uncertain'
        self.assertFalse(any(mask.any() for mask in background_eye_masks(row).values()))

    def test_background_gradients_only_supervise_eye_class_outside_protection(self):
        row = self.row([{'id': 'b', 'kind': 'bird', 'box_xyxy': [100, 100, 130, 130], 'point_xy': None}])
        outputs = {k: v.clone().requires_grad_() for k, v in self.heads.items()}
        sample = {**row, 'targets': [], 'negative_targets': [], 'heads': self.heads, 'background_masks': background_eye_masks(row)}
        loss, _ = partial_loss(outputs, [sample], background_weight=.2, background_topk=1024)
        loss.backward()
        grad = outputs['fine'].grad.reshape(1, 2, 11, 16, 24)[0]
        self.assertGreater(float(grad[:, 7:9].abs().sum()), 0.)
        self.assertEqual(float(grad[:, :7].abs().sum()), 0.)
        self.assertEqual(float(grad[:, 9:].abs().sum()), 0.)
        self.assertEqual(float(grad[:, :, 6, 6].abs().sum()), 0.)

    def test_head_local_requires_unambiguous_explicit_eye_and_head(self):
        h = {'id': 'h', 'kind': 'head', 'box_xyxy': [0, 0, 64, 64], 'point_xy': None}
        e = {'id': 'e', 'kind': 'eye', 'box_xyxy': None, 'point_xy': [8, 8]}
        self.assertIsNone(local_eye_supervision(self.row([h])))
        self.assertIsNone(local_eye_supervision(self.row([h, e, dict(e, id='e2')])))
        self.assertIsNotNone(local_eye_supervision(self.row([h, e])))
        self.assertIsNone(local_eye_supervision(self.row([h, e, {'id': 'u', 'kind': 'uncertain', 'box_xyxy': [0, 0, 64, 64], 'point_xy': None}])))

    def test_head_local_excludes_positive_anchor_and_outside_head(self):
        row = self.row([{'id': 'h', 'kind': 'head', 'box_xyxy': [0, 0, 64, 64], 'point_xy': None},
                        {'id': 'e', 'kind': 'eye', 'box_xyxy': None, 'point_xy': [8, 8]}])
        raw = self.heads['fine'][0].reshape(2, 11, 16, 24)
        targets = [{'kind': 'eye', 'head': 'fine', 'anchor': 0, 'row': 1, 'col': 1}]
        mask = head_local_negative_mask(raw, local_eye_supervision(row), targets, 'fine')
        self.assertFalse(bool(mask[:, 0, 0].any()))
        self.assertFalse(bool(mask[0, 1, 1]))
        self.assertTrue(bool(mask[1, 1, 1]))
        self.assertFalse(bool(mask[:, 8, 8].any()))


if __name__ == '__main__':
    unittest.main()
