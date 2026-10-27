import unittest
from pathlib import Path
import sys
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/training'))
from bird_residual import community_label,patches,proposal_pool,PointRanker,ranking_loss


class ResidualTests(unittest.TestCase):
    def test_partial_real_labels_do_not_turn_body_or_missing_eye_into_truth(self):
        row=dict(eyes=[[50.,50.]],objects=[dict(kind='bird',box=[20,20,100,100])],uncertain=[],absent=False)
        self.assertEqual(community_label(row,[50,50],True)[0],1)
        self.assertIsNone(community_label(row,[50,50],False)[0])
        self.assertIsNone(community_label(row,[70,70])[0])
        self.assertEqual(community_label(row,[250,180])[0],0)
        row['objects']=[dict(kind='head',box=[40,40,60,60])]
        self.assertIsNone(community_label(row,[250,180])[0])
        row['absent']=True
        self.assertEqual(community_label(row,[250,180])[1],'human_frame_absence')

    def test_candidate_pool_is_prediction_only_and_points_in_input_coordinates(self):
        logits=torch.full((1,1,64,96),-20.);logits[0,0,10,20]=10
        pool=proposal_pool([],logits)
        self.assertEqual(pool[0]['point_xy'],[82.,42.])
        self.assertLessEqual(len(pool),24)
        self.assertFalse(any(p.get('injected') for p in pool))

    def test_two_point_centred_views_do_not_modify_source(self):
        pixels=np.full((256,384,3),40,np.uint8);before=pixels.copy()
        result=patches(pixels,[[100,100],[1,1]])
        self.assertEqual(result.shape,(2,6,64,64))
        self.assertTrue(np.array_equal(pixels,before));self.assertTrue((result==40).all())

    def test_larger_ranker_stays_below_doubled_n_budget(self):
        small=PointRanker(False);large=PointRanker(True)
        small_count=sum(p.numel() for p in small.parameters());large_count=sum(p.numel() for p in large.parameters())
        self.assertGreater(large_count,small_count*2)
        self.assertLess(2455728+6945+large_count,2455728*2)
        out=large(torch.zeros(2,6,64,64,dtype=torch.uint8),torch.zeros(2,133))
        self.assertEqual(out.shape,(2,))

    def test_pairwise_loss_pushes_positive_above_negative(self):
        logits=torch.zeros(2,requires_grad=True)
        loss=ranking_loss(logits,torch.tensor([1.,0.]),torch.ones(2),[(0,1)])
        loss.backward()
        self.assertLess(float(logits.grad[0]),0);self.assertGreater(float(logits.grad[1]),0)


if __name__=='__main__':unittest.main()
