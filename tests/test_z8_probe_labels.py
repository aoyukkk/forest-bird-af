"""Partial labels must not invent native classes, eye sizes or negatives."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'training'))
from z8_probe_labels import adapt, assign

TABLES = {'anchors': [(7, 7), (60, 60), (80, 80), (160, 140), (200, 200)],
          'allowed_slots': {0: [0, 1, 2, 3, 4, 5], 1: [0, 1, 2, 3, 4, 5],
                            2: [2, 3, 4], 3: [0, 2, 3, 4], 4: [1, 2, 3, 4, 5]}}


class PartialLabelTests(unittest.TestCase):
    def document(self):
        return {'schema_version': 'forest-bird-input-manual-v1', 'image_id': 'fb_0001',
                'annotation_status': 'annotated', 'instances': [{'instance_id': 'b1',
                'bird_bbox_xyxy': [1, 2, 100, 140], 'head_bbox_xyxy': [20, 20, 50, 50],
                'eyes': [{'eye_id': 'e1', 'center_xy': [35, 30], 'bbox_xyxy': None, 'side': 'unknown'}]}]}

    def test_unreviewed_labels_require_explicit_engineering_mode(self):
        with self.assertRaises(ValueError):
            adapt(self.document())
        a = adapt(self.document(), True)
        self.assertTrue(a['engineering_only']); self.assertFalse(a['human_confirmed'])

    def test_eye_point_does_not_invent_box_or_direction(self):
        targets = assign(adapt(self.document(), True), TABLES)
        eye = next(t for t in targets if t['kind'] == 'eye')
        self.assertIsNone(eye['target_log_wh'])
        self.assertEqual(eye['class_slots'], [2, 3])
        self.assertEqual(eye['supervised_fields'], ['x', 'y'])
        self.assertEqual(eye['instance_id'], 'b1')

    def test_whole_bird_is_not_silently_mapped_to_native_body_or_auxiliary(self):
        a = adapt(self.document(), True)
        self.assertEqual(len(a['ignored']), 1)
        self.assertEqual([t['kind'] for t in a['targets']], ['head', 'eye'])
        self.assertTrue(a['positive_only'])

    def test_new_correction_schema_preserves_missing_instance_information(self):
        d = {'schema_version': 'forest-bird-z8-correction-v1', 'image_id': 'fb_0001',
             'status': 'confirmed', 'items': [
                 {'id': 'p0', 'kind': 'auxiliary', 'box_xyxy': [1, 1, 100, 100], 'point_xy': None},
                 {'id': 'n1', 'kind': 'eye', 'box_xyxy': None, 'point_xy': [30, 30]}]}
        a = adapt(d)
        self.assertIsNone(a['targets'][0]['instance_id'])
        self.assertTrue(any('associations' in x for x in a['warnings']))
        self.assertEqual(a['ignored'][0]['source_id'], 'p0')

    def test_empty_review_does_not_generate_background_training_targets(self):
        d = {'schema_version': 'forest-bird-z8-correction-v1', 'image_id': 'fb_0001',
             'status': 'confirmed', 'presence': 'absent', 'items': []}
        self.assertEqual(assign(adapt(d), TABLES), [])

    def test_invalid_geometry_rejected_and_native_anchor_restrictions_honored(self):
        d = self.document(); d['instances'][0]['head_bbox_xyxy'][0] = -1
        with self.assertRaises(ValueError):
            adapt(d, True)
        d = self.document(); d['instances'][0]['head_bbox_xyxy'] = [10, 10, 100, 100]
        targets = assign(adapt(d, True), TABLES)
        head = next(t for t in targets if t['kind'] == 'head')
        self.assertIn(head['native_anchor'], [0, 1, 4])

    def test_collisions_never_silently_replace_an_eye(self):
        d = self.document(); d['instances'][0]['head_bbox_xyxy'] = None
        eye = d['instances'][0]['eyes'][0]
        d['instances'][0]['eyes'] = [dict(copy.deepcopy(eye), eye_id=f'e{i}') for i in range(6)]
        with self.assertRaisesRegex(ValueError, 'collision'):
            assign(adapt(d, True), TABLES)


if __name__ == '__main__':
    unittest.main()
