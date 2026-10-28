from pathlib import Path
import sys
import unittest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/training'))
from bird_parts_model import decode
from diagnose_bird_information import transform, proposal_regions, paired


class InformationDiagnosticTests(unittest.TestCase):
    def test_native_center_and_box_use_same_crop_transform(self):
        p=dict(kind='bird',score=.8,point_xy=[192,128],box_xyxy=[96,64,288,192])
        q=transform([p],[100,50,292,178])[0]
        self.assertEqual(q['point_xy'],[196,114])
        self.assertEqual(q['box_xyxy'],[148,82,244,146])
        self.assertEqual(p['point_xy'],[192,128])

    def test_high_resolution_decode_does_not_clip_at_historical_width(self):
        # A stride-8 cell at x=600 is valid in a 768-wide input.
        raw=dict(feats=[torch.zeros(1,4,1,96)],boxes=torch.ones(1,4,96),
                 scores=torch.full((1,2,96),-20.),kpts=torch.full((1,6,96),-20.))
        raw['scores'][0,0,75]=10
        old=decode(raw,torch.tensor([8.]))[0]
        explicit=decode(raw,torch.tensor([8.]),input_size=(384,256))[0]
        high=decode(raw,torch.tensor([8.]),input_size=(768,512),eye_nms_radius=8)[0]
        self.assertEqual(old,explicit)
        self.assertGreater(high[0]['box_xyxy'][0],384)
        q=transform(high,size=(768,512))[0]
        self.assertGreater(q['box_xyxy'][0],290)
        self.assertLess(q['box_xyxy'][2],310)

    def test_proposal_crop_has_no_truth_dependency_and_is_bounded(self):
        predictions=[dict(kind='bird',score=.9,box_xyxy=[10,20,20,30]),
                     dict(kind='head',score=.09,box_xyxy=[200,100,220,120])]
        regions=proposal_regions(predictions)
        self.assertEqual(len(regions),1)
        self.assertTrue(all(0<=r[0]<r[2]<=384 and 0<=r[1]<r[3]<=256 for r in regions))
        self.assertEqual(proposal_regions([]),[])

    def test_paired_changes_do_not_hide_offsets_or_frame_group_imbalance(self):
        rows=[dict(image_id=k,group=g) for k,g in [('a','x'),('b','x'),('c','y')]]
        old=dict(detail=[dict(image_id=k,category='bird_region' if k=='a' else 'abstain') for k in 'abc'])
        new=dict(detail=[dict(image_id=k,category='bird_region' if k=='c' else 'abstain') for k in 'abc'])
        result=paired(rows,old,new)
        self.assertEqual(result['gained'],['c']);self.assertEqual(result['lost'],['a'])
        self.assertEqual(result['macro_group_delta'],.25)


if __name__=='__main__':unittest.main()
