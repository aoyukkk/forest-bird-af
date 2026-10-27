from pathlib import Path
import sys
import unittest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/training'))
from bird_parts_model import build_model, as_raw
from train_classification_guard import freeze_except_classification, positive_guard, batches, guarded_rank, fit_document


class ClassificationGuardTests(unittest.TestCase):
    def test_related_group_quarantine_preserves_source_and_evaluation(self):
        document = dict(records=[dict(image_id='fit', split='community_train'), dict(image_id='val', split='community_val')])
        filtered = fit_document(document, ['fit'])
        self.assertEqual([r['image_id'] for r in filtered['records']], ['val'])
        self.assertEqual(len(document['records']), 2)
        with self.assertRaises(ValueError):
            fit_document(document, ['val'])

    def test_actual_step_changes_only_classification_and_keeps_raw_boxes(self):
        torch.set_num_threads(2)
        model = build_model('n'); parameters = freeze_except_classification(model)
        before = {k: v.clone() for k, v in model.state_dict().items()}
        allowed = {k for k, v in model.named_parameters() if v.requires_grad}
        self.assertTrue(allowed); self.assertTrue(all('.cv3.' in k for k in allowed))
        image = torch.randn(1, 3, 256, 384)
        raw = as_raw(model(image)); boxes = raw['boxes'].clone()
        optimizer = torch.optim.SGD(parameters, lr=.001)
        raw['scores'].mean().backward(); optimizer.step()
        after = model.state_dict(); changed = {k for k in before if not torch.equal(before[k], after[k])}
        self.assertTrue(changed); self.assertTrue(changed <= allowed)
        self.assertTrue(torch.equal(boxes, as_raw(model(image))['boxes']))
        self.assertFalse(any(m.training for m in model.modules()))

    def test_guard_uses_decoded_centers_and_only_prevents_positive_decrease(self):
        raw = dict(scores=torch.zeros(2, 2, 3, requires_grad=True), boxes=torch.ones(2, 4, 3), feats=[torch.zeros(2, 4, 1, 3)])
        teacher = dict(scores=torch.ones(2, 2, 3), boxes=torch.ones(2, 4, 3))
        samples = [dict(source='community', image_id='fit', objects=[dict(kind='bird', box=[0, 0, 16, 8])]),
                   dict(source='CCT', image_id='empty', objects=[])]
        loss, count = positive_guard(raw, teacher, samples, torch.tensor([8.]), {'fit'})
        self.assertEqual(count, 2); loss.backward()
        self.assertTrue((raw['scores'].grad[0, 0, :2] < 0).all())
        self.assertEqual(float(raw['scores'].grad[0, 1].abs().sum()), 0.)
        self.assertEqual(float(raw['scores'].grad[1].abs().sum()), 0.)
        raw['scores'] = torch.full((2, 2, 3), 2., requires_grad=True)
        value, _ = positive_guard(raw, teacher, samples, torch.tensor([8.]), set())
        self.assertEqual(float(value), 0.)

    def test_sampling_matches_and_has_four_hard_four_empty_slots(self):
        records = []
        for source in ('community', 'CUB-200-2011', 'NABirds', 'COCO-2017', 'CCT'):
            for i in range(3):
                records.append(dict(source=source, image_id=source+str(i), group=source+str(i),
                                    split='community_train' if source=='community' else 'public_train'))
        doc = dict(records=records); hard = {'community0', 'community1'}
        a = list(batches(doc, hard, 19, 0, 2)); self.assertEqual(a, list(batches(doc, hard, 19, 0, 2)))
        for batch in a:
            self.assertTrue(all(r['image_id'] in hard for r in batch[8:12]))
            self.assertTrue(all(r['source']=='CCT' for r in batch[12:]))

    def test_equal_total_support_cannot_hide_loss_of_a_parent_frame(self):
        counts = dict(geometry_supported=1, outside_labelled_geometry=0, explicit_absent_selection=0,
                      selected_eye=0, eye_4px=0, eye_unmatched_4px=0, eye_unassessed_selected=0)
        box = dict(kind='bird', score=.9, point_xy=None, box_xyxy=[0, 0, 10, 10])
        regions = [dict(image_id=k, group=k, eyes=[], objects=[dict(kind='bird', box=[0,0,10,10])],
                        absent=False, eye_complete=False, uncertain=[]) for k in ('a','b')]
        reference = dict(community=counts, empty_selected=60, predictions=dict(a=[box],b=[]),
                         community_selected=dict(a=box,b=None))
        candidate = dict(community=counts, empty_selected=20, predictions=dict(a=[],b=[box]),
                         community_selected=dict(a=None,b=box))
        key, lost = guarded_rank(candidate, reference, regions)
        self.assertEqual(lost, ['a']); self.assertEqual(key[0], 0)


if __name__ == '__main__':
    unittest.main()
