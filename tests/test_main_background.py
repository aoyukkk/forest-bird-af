from pathlib import Path
import sys
import unittest
import numpy as np
import torch
from torch import nn
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/training'))
from train_main_background import (supervision,BoxOnlyLoss,preservation,
                                   frozen_bn_train,epoch_batches,rank)
from bird_parts_model import build_model,as_raw


def row(source='CCT',objects=None,absent=True):
    return dict(source=source,objects=objects or [],eyes=[],uncertain=[],negative_regions=[[0,0,384,256]] if absent else [],absent=absent,eye_complete=absent,head_labels_are_weak=False)


class MainBackgroundTests(unittest.TestCase):
    def test_explicit_empty_control_masks_all_detection_classes(self):
        centers=torch.tensor([[4.,4.],[100.,120.]])
        self.assertFalse(supervision([row()],centers,False).any())
        self.assertTrue(supervision([row()],centers,True).all())

    def test_missing_public_head_is_unknown_not_background(self):
        sample=row('COCO-2017',[dict(kind='bird',box=[0,0,30,30])],False)
        sample['negative_regions']=[[0,0,30,30]]
        valid=supervision([sample],torch.tensor([[8.,8.],[100.,100.]]),True)
        self.assertTrue(valid[0,0,0]);self.assertFalse(valid[0,0,1]);self.assertFalse(valid[0,1].any())

    def test_actual_detection_loss_has_empty_gradients_only_when_enabled(self):
        torch.set_num_threads(2);model=build_model('n').eval()
        raw=as_raw(model(torch.zeros(1,3,256,384)))
        raw['scores'].retain_grad();raw['kpts'].retain_grad()
        control=BoxOnlyLoss(model,False)(raw,[row()]);control.backward(retain_graph=True)
        self.assertEqual(float(raw['scores'].grad.abs().sum()),0.)
        raw['scores'].grad.zero_()
        enabled=BoxOnlyLoss(model,True)(raw,[row()]);enabled.backward()
        self.assertGreater(float(raw['scores'].grad.sum()),0.)
        self.assertIsNone(raw['kpts'].grad)

    def test_preservation_only_uses_corresponding_human_positive_regions(self):
        scores=torch.zeros(2,2,3,requires_grad=True);boxes=torch.zeros(2,4,3,requires_grad=True)
        raw=dict(scores=scores,boxes=boxes,feats=[torch.zeros(2,4,1,3)])
        teacher=dict(scores=torch.ones_like(scores),boxes=torch.zeros_like(boxes))
        samples=[row('community',[dict(kind='bird',box=[0,0,16,8])],False),row()]
        loss=preservation(raw,teacher,samples,torch.tensor([8.]));loss.backward()
        self.assertGreater(float(scores.grad[0,0,:2].abs().sum()),0.)
        self.assertEqual(float(scores.grad[0,1].abs().sum()),0.)
        self.assertEqual(float(scores.grad[0,0,2]),0.)
        self.assertEqual(float(scores.grad[1].abs().sum()),0.)

    def test_bn_statistics_frozen_while_convolution_still_trains(self):
        model=nn.Sequential(nn.Conv2d(3,4,3,padding=1),nn.BatchNorm2d(4))
        before=model[1].running_mean.clone();frozen_bn_train(model)
        model(torch.randn(3,3,8,8)).sum().backward()
        self.assertTrue(torch.equal(before,model[1].running_mean))
        self.assertTrue(model[0].training);self.assertFalse(model[1].training)
        self.assertIsNotNone(model[0].weight.grad)

    def test_batches_are_condition_independent_with_fixed_empty_slots(self):
        records=[]
        for source in ['community','CUB-200-2011','NABirds','COCO-2017','CCT']:
            for i in range(3):records.append(dict(source=source,group=source+str(i),image_id=source+str(i),split='community_train' if source=='community' else 'public_train'))
        a=list(epoch_batches(dict(records=records),17,0,3));b=list(epoch_batches(dict(records=records),17,0,3))
        self.assertEqual(a,b)
        for batch in a:
            self.assertEqual(len(batch),16)
            self.assertTrue(all(r['source']=='CCT' for r in batch[12:]))
            self.assertTrue(all(r['source']!='CCT' for r in batch[:12]))

    def test_reject_everything_cannot_win_and_eye_regression_raises(self):
        reference=dict(community=dict(geometry_supported=68,outside_labelled_geometry=1,explicit_absent_selection=0,selected_eye=35,eye_4px=15,eye_unmatched_4px=2,eye_unassessed_selected=18),empty_selected=60)
        candidate=dict(community=dict(reference['community'],geometry_supported=35),empty_selected=7)
        self.assertLess(rank(candidate,reference),rank(reference,reference))
        candidate['community']['eye_4px']=14
        with self.assertRaises(RuntimeError):rank(candidate,reference)


if __name__=='__main__':unittest.main()
