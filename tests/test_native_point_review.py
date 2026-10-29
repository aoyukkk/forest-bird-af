import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/training'))
from native_point_review import load_review, annotate_surface
from train_native_guidance import update_masks, quality_loss, selection_key


class NativePointReviewTests(unittest.TestCase):
    def fixture(self, root):
        source = root / 'input.png';source.write_bytes(b'fixed image')
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        point = [12, 34]
        candidate = hashlib.sha256(json.dumps(['fb_1', sha, point], separators=(',', ':')).encode()).hexdigest()
        manifest = dict(records=[dict(image_id='fb_1', source_path=str(source), source_sha256=sha, point_xy=point)])
        record = dict(image_id='fb_1', candidate_id=candidate, input_sha256=sha, point_xy=point,
                      actor_kind='human', status='confirmed', human_confirmed=True, revision=1, history=[],
                      choice='supported', eye_localizable_input='unknown', part='unknown', accepted_for_training=False,
                      confirmed_at_utc='2026-10-29T00:00:00Z')
        payload = dict(schema='point-surface-human-review-v1', dataset_id=hashlib.sha256(json.dumps([candidate]).encode()).hexdigest(),
                       old_development_data=True, accepted_for_training=False, records=[record])
        mp, rp = root/'manifest.json', root/'review.json'
        mp.write_text(json.dumps(manifest));rp.write_text(json.dumps(payload))
        return source, mp, rp, payload

    def test_import_rejects_moved_points_changed_images_and_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            source, mp, rp, payload = self.fixture(Path(d))
            self.assertEqual(len(load_review(mp, rp)[1]), 1)
            changed = copy.deepcopy(payload);changed['records'][0]['point_xy'][0] += 1
            rp.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):load_review(mp, rp)
            changed = copy.deepcopy(payload);changed['records'] *= 2;rp.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):load_review(mp, rp)
            rp.write_text(json.dumps(payload));source.write_bytes(b'changed')
            with self.assertRaises(ValueError):load_review(mp, rp)

    def test_draft_cannot_become_human_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            _, mp, rp, payload = self.fixture(Path(d))
            payload['records'][0]['human_confirmed'] = False;rp.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):load_review(mp, rp)

    def test_surface_support_never_becomes_eye_label_or_transfers_to_moved_point(self):
        report = dict(counts=dict(eye_unassessed_selected=1, eye_4px=0),
                      detail=[dict(image_id='fb_1', eye_known=False, selected=dict(kind='eye', point_xy=[12, 34]))])
        records = {'fb_1':dict(point_xy=[12, 34], choice='supported')}
        same = annotate_surface(copy.deepcopy(report), records)
        self.assertEqual(same['counts'], report['counts'])
        self.assertEqual(same['human_surface']['unreviewed_eye_selections'], 0)
        report['detail'][0]['selected']['point_xy'][0] += 1
        self.assertEqual(annotate_surface(report, records)['human_surface']['unreviewed_eye_selections'], 1)

    def test_expanded_mask_freezes_auxiliary_and_padding(self):
        batches = [89, 90, 91, 112, 113]
        model = SimpleNamespace(events=[dict(batch=b) for b in batches],
                                weights=[torch.zeros(16, 16) for _ in batches],
                                biases={str(i):torch.zeros(16) for i in range(len(batches))})
        masks = update_masks(model, 'bhe-head')
        self.assertTrue(bool(masks['weights.0'][4].all()))
        self.assertFalse(bool(masks['weights.0'][10].any()))
        self.assertTrue(bool(masks['weights.1'][15].all()))
        self.assertFalse(bool(masks['weights.2'].any()))
        self.assertFalse(bool(masks['weights.4'][6:].any()))

    def test_equal_control_uses_same_anchor_and_loss_but_constant_one(self):
        target = dict(kind='eye', head='fine', anchor=0, row=0, col=0, xy=[0., 0.], class_slot=2)
        raw = torch.zeros(1, 22, 16, 24, requires_grad=True)
        quality_loss({'fine':raw}, [dict(targets=[target])], sigma=2, constant_target=True).backward()
        self.assertLess(float(raw.grad[0, 7, 0, 0]), 0)
        self.assertEqual(int(torch.count_nonzero(raw.grad)), 1)

    def test_known_eye_errors_still_fail_despite_human_surface_support(self):
        counts = dict(geometry_supported=54, outside_labelled_geometry=10, explicit_absent_selection=0,
                      eye_unmatched_4px=3, eye_unassessed_selected=1, eye_4px=9)
        original = dict(counts=counts)
        worse = dict(counts=dict(counts, eye_unmatched_4px=4), human_surface=dict(unreviewed_eye_selections=0, unsupported=0))
        self.assertGreater(selection_key(original, original, dict(macro_f1=.5)),
                           selection_key(worse, original, dict(macro_f1=.9)))


if __name__ == '__main__':unittest.main()
