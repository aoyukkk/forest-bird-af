from pathlib import Path
import sys
import unittest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/training'))
from train_native_guidance import quality_loss,selection_key


class NativeGuidanceTests(unittest.TestCase):
    def test_quality_gradient_updates_eye_class_without_coordinate_teacher_gradient(self):
        raw=torch.zeros(1,22,16,24,requires_grad=True)
        t=dict(kind='eye',head='fine',anchor=0,row=0,col=0,xy=[.5,.5],class_slot=2)
        loss=quality_loss({'fine':raw},[dict(targets=[t])]);loss.backward()
        self.assertLess(float(raw.grad[0,7,0,0]),0)
        self.assertEqual(int(torch.count_nonzero(raw.grad)),1)

    def test_wrong_location_lowers_class_confidence_at_known_positive_only(self):
        raw=torch.zeros(1,22,16,24,requires_grad=True)
        t=dict(kind='eye',head='fine',anchor=0,row=0,col=0,xy=[0.,0.],class_slot=2)
        loss=quality_loss({'fine':raw},[dict(targets=[t])],sigma=2);loss.backward()
        self.assertGreater(float(raw.grad[0,7,0,0]),0)

    def test_unknown_eye_is_not_a_negative(self):
        raw=torch.randn(1,22,16,24,requires_grad=True)
        loss=quality_loss({'fine':raw},[dict(targets=[])]);loss.backward()
        self.assertEqual(float(loss),0);self.assertEqual(int(torch.count_nonzero(raw.grad)),0)

    def test_more_unknown_eyes_cannot_win_on_more_geometry(self):
        counts=dict(geometry_supported=54,outside_labelled_geometry=10,explicit_absent_selection=0,
                    eye_unmatched_4px=3,eye_unassessed_selected=1,eye_4px=9)
        changed=dict(counts,geometry_supported=56,eye_unassessed_selected=2)
        self.assertGreater(selection_key(dict(counts=counts),dict(counts=counts),{'macro_f1':.5}),
                           selection_key(dict(counts=changed),dict(counts=counts),{'macro_f1':.6}))


if __name__=='__main__':unittest.main()
