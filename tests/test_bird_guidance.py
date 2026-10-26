import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/training'))
from bird_guidance_metrics import assess_guidance, guidance_rank, select_candidate
from bird_guidance_fallback import route_candidate


def eye(x, y, score=.9):
    return dict(kind='eye', point_xy=[x, y], box_xyxy=None, score=score)


def head(box, score=.9):
    return dict(kind='head', point_xy=None, box_xyxy=box, score=score)


def row(eyes=(), objects=(), absent=False, complete=False):
    return dict(image_id='x', group='g', eyes=list(eyes), objects=list(objects),
                absent=absent, eye_complete=complete, uncertain=[])


class GuidanceTests(unittest.TestCase):
    def test_unknown_eye_does_not_become_false_eye(self):
        r = assess_guidance([row(objects=[dict(kind='bird', box=[0, 0, 20, 20])])], {'x': [eye(10, 10)]})
        self.assertEqual(r['counts']['eye_unassessed_selected'], 1)
        self.assertEqual(r['counts']['eye_unmatched_4px'], 0)
        self.assertEqual(r['counts']['bird_region'], 1)
        self.assertFalse(r['camera_AF_verified'])

    def test_duplicate_unused_eye_does_not_count_as_wrong_selected_eye(self):
        r = assess_guidance([row(eyes=[[10, 10]])], {'x': [eye(10, 10), eye(100, 100, .85)]})
        self.assertEqual(r['counts']['eye_4px'], 1)
        self.assertEqual(r['counts']['eye_unmatched_4px'], 0)

    def test_head_cue_is_not_precise_eye_and_fallback_is_audited(self):
        r = assess_guidance([row(eyes=[[5, 5]], objects=[dict(kind='head', box=[0, 0, 30, 30])])],
                            {'x': [eye(20, 20), head([0, 0, 30, 30])]})
        self.assertEqual(r['counts']['head_region'], 1)
        self.assertEqual(r['counts']['eye_4px'], 0)
        self.assertEqual(r['counts']['wrong_eye_over_geometric_fallback'], 1)

    def test_unknown_region_and_explicit_absence_are_separate(self):
        a = row(objects=[dict(kind='bird', box=[0, 0, 10, 10])])
        a['uncertain'] = [[15, 15, 25, 25]]
        r = assess_guidance([a], {'x': [eye(20, 20)]})
        self.assertEqual(r['counts']['unknown_geometry'], 1)
        r = assess_guidance([row(absent=True)], {'x': [eye(20, 20)]})
        self.assertEqual(r['counts']['explicit_absent_selection'], 1)

    def test_auxiliary_protection_does_not_erase_positive_geometry(self):
        a = row(objects=[dict(kind='head', box=[0, 0, 30, 30])])
        a['uncertain'] = [[0, 0, 30, 30]]
        r = assess_guidance([a], {'x': [head([0, 0, 30, 30])]})
        self.assertEqual(r['counts']['head_region'], 1)
        self.assertTrue(r['detail'][0]['inside_protected_region'])

    def test_prediction_gate_never_reads_labels(self):
        candidates = [eye(100, 100), head([0, 0, 20, 20])]
        self.assertEqual(select_candidate(candidates, gate='head-or-high')['kind'], 'head')
        candidates[0]['score'] = .96
        self.assertEqual(select_candidate(candidates, gate='head-or-high')['kind'], 'eye')

    def test_reject_everything_does_not_pass_parent_coverage(self):
        rows = [row(eyes=[[10, 10]])]
        reference = assess_guidance(rows, {'x': [eye(10, 10)]})
        empty = assess_guidance(rows, {'x': []})
        self.assertEqual(guidance_rank(empty, reference)[0], 0)

    def test_near_eye_is_coarse_only(self):
        r = assess_guidance([row(eyes=[[10, 10]])], {'x': [eye(16, 10)]})
        self.assertEqual(r['counts']['near_eye_geometry'], 1)
        self.assertEqual(r['counts']['eye_4px'], 0)
        self.assertEqual(r['counts']['eye_8px'], 1)

    def test_coarse_hint_never_replaces_existing_target(self):
        original=head([0,0,20,20])
        chosen,called=route_candidate([original],[eye(100,100,.99)],dict(bird=.4,head=.5,eye=.8))
        self.assertEqual(chosen,original)
        self.assertFalse(called)

    def test_capture_hint_is_not_counted_as_precise_eye(self):
        chosen,called=route_candidate([], [eye(10,10,.3)],dict(bird=.4,head=.5,eye=.8))
        self.assertTrue(called)
        self.assertEqual(chosen['kind'],'capture_hint')
        r=assess_guidance([row(eyes=[[10,10]])],{'x':[]},selected_by_id={'x':chosen})
        self.assertEqual(r['counts']['geometry_supported'],1)
        self.assertEqual(r['counts']['eye_4px'],0)
        self.assertEqual(r['counts']['selected_eye'],0)
