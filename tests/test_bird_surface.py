import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import torch
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/training'))
from bird_surface import (FrozenSurface,SurfaceHead,batch_samples,decode_surface,dense_targets,
                          make_sample,outside_git,surface_loss,training_samples)


class SurfaceTests(unittest.TestCase):
    def test_explicit_occluder_is_not_positive_and_only_r2_trains_it_negative(self):
        alpha=np.zeros((256,384),np.float32);alpha[40:100,40:100]=1
        occ=np.zeros_like(alpha,np.uint8);occ[50:90,65:73]=1
        target,known,core,support=dense_targets(alpha,occ,np.ones_like(occ))
        self.assertFalse(target[occ>0].any());self.assertFalse(known[core].any())
        self.assertTrue(core.any());self.assertFalse(support[core].any())
        logits=torch.zeros(1,1,64,96,requires_grad=True)
        t={k:torch.from_numpy(v[2::4,2::4][None]) for k,v in
           dict(target=target,known=known,occlusion=core).items()};t['points']=[[]]
        a=surface_loss(logits,t,'R1');b=surface_loss(logits,t,'R2')
        self.assertGreater(float(b),float(a))
        a.backward();self.assertEqual(float(logits.grad[0,0][t['occlusion'][0]].abs().sum()),0)
        logits.grad=None;b.backward()
        self.assertGreater(float(logits.grad[0,0][t['occlusion'][0]].sum()),0)

    def test_missing_community_eyes_and_head_only_do_not_create_dense_truth(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'image.png';Image.new('RGB',(384,256)).save(p)
            row=dict(image_id='fixture',source='community',source_sha256='fixture',split='community_train',
                     path=str(p),objects=[dict(kind='head',box=[40,40,80,80])],eyes=[],uncertain=[],absent=False)
            sample=make_sample(row,{},np.random.default_rng(1))
            self.assertFalse(sample['known'].any());self.assertFalse(sample['target'].any())
            self.assertEqual(sample['points'],[])
            row['eyes']=[[51.3,55.7]]
            sample=make_sample(row,{},np.random.default_rng(1))
            self.assertEqual(sample['points'],row['eyes']);self.assertFalse(sample['target'].any())

    def test_coordinate_decode_is_input_pixel_coarse_cue(self):
        values=torch.full((1,1,64,96),-10.);values[0,0,10,20]=10
        p=decode_surface(values)[0]
        self.assertEqual(p['point_xy'],[82.,42.]);self.assertEqual(p['kind'],'capture_hint')
        self.assertEqual(p['source_kind'],'surface')

    def test_multilevel_official_mask_does_not_turn_whole_bird_into_background(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'image.png';Image.new('RGB',(384,256)).save(p)
            mask=np.zeros((256,384),np.uint8);mask[40:100,40:100]=204
            m=Path(folder)/'mask.png';Image.fromarray(mask).save(m)
            row=dict(image_id='fixture',source='CUB-200-2011',source_sha256='fixture',split='public_train',
                     path=str(p),foreground_mask=str(m),objects=[dict(kind='bird',box=[40,40,100,100])])
            sample=make_sample(row,{},np.random.default_rng(1),'original')
            self.assertTrue(sample['target'][70,70]);self.assertTrue(sample['support'][70,70])
            self.assertTrue(sample['known'][70,70])

    def test_no_valid_supervision_has_zero_gradient_and_sparse_point_has_gradient(self):
        x=torch.zeros(1,1,64,96,requires_grad=True)
        target=dict(target=torch.zeros(1,64,96),known=torch.zeros(1,64,96,dtype=torch.bool),
                    occlusion=torch.zeros(1,64,96,dtype=torch.bool),points=[[]])
        surface_loss(x,target,'R1').backward();self.assertEqual(float(x.grad.abs().sum()),0)
        x.grad=None;target['points']=[[[82.,42.]]]
        surface_loss(x,target,'R1').backward();self.assertLess(float(x.grad[0,0,10,20]),0)

    def test_frozen_base_preserves_parameters_statistics_and_raw_outputs(self):
        torch.set_num_threads(4)
        from bird_parts_model import build_model
        with tempfile.TemporaryDirectory() as folder:
            parent=Path(folder)/'parent.pt';base=build_model('n')
            torch.save(dict(state_dict=base.state_dict()),parent)
            model=FrozenSurface(parent);model.eval()
            images=torch.rand(1,3,256,384)
            state={k:v.clone() for k,v in model.base.state_dict().items()}
            with torch.no_grad():_,before=model(images,True)
            before={k:v.clone() for k,v in before.items() if torch.is_tensor(v)}
            model.train();self.assertFalse(model.base.training)
            optimizer=torch.optim.SGD(model.head.parameters(),lr=.01)
            model(images).square().mean().backward();optimizer.step()
            self.assertTrue(all(p.grad is None for p in model.base.parameters()))
            self.assertTrue(all(torch.equal(v,model.base.state_dict()[k]) for k,v in state.items()))
            model.eval()
            with torch.no_grad():_,after=model(images,True)
            self.assertTrue(all(torch.equal(v,after[k]) for k,v in before.items()))
            ratio=sum(p.numel() for p in model.head.parameters())/sum(p.numel() for p in model.base.parameters())
            self.assertLess(ratio,.1)

    def test_private_output_guard(self):
        with self.assertRaises(ValueError):outside_git(Path(__file__).resolve().parents[1]/'artifacts')


if __name__=='__main__':unittest.main()
