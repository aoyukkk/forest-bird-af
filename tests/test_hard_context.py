import sys
import unittest
import importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/training'))
HAS_YOLO=importlib.util.find_spec('ultralytics') is not None
if HAS_YOLO:
    from hard_bird_context import outside_regions
    from train_bird_parts import budget_eye_threshold,selection_value


@unittest.skipUnless(HAS_YOLO,'Optional pinned YOLO runtime required')
class HardContextTests(unittest.TestCase):
    def test_derived_background_protects_entire_subject_margin(self):
        regions=outside_regions([100,80,180,150])
        for x,y in [(100,80),(140,115),(180,150),(95,76),(185,155)]:
            self.assertFalse(any(a<=x<c and b<=y<d for a,b,c,d in regions))
        for x,y in [(0,0),(383,255)]:
            self.assertTrue(any(a<=x<c and b<=y<d for a,b,c,d in regions))

    def test_budget_rejects_high_recall_with_excess_candidates(self):
        rows=[dict(threshold=.5,metrics={'eye':dict(tp=20,fp=4)}),dict(threshold=.8,metrics={'eye':dict(tp=16,fp=2)}),dict(threshold=.95,metrics={'eye':dict(tp=8,fp=0)})]
        self.assertEqual(budget_eye_threshold(rows,3),.8)
        self.assertEqual(budget_eye_threshold(rows,0),.95)

    def test_part_regression_cannot_beat_a_passing_candidate(self):
        def metric(tp,hf):return dict(bird={'f1':.6},head={'f1':hf},eye=dict(tp=tp,fp=2,labels=25),macro_f1=.7)
        self.assertLess(selection_value(metric(24,.3),3,.55,.65),selection_value(metric(12,.7),3,.55,.65))
        self.assertLess(selection_value(metric(12,.7),3,.55,.65),selection_value(metric(13,.7),3,.55,.65))
