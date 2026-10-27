import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/training'))
from admit_public_expansion import BKTree,close,split_empty_locations
from prepare_coco_cct import cct_records,coco_records
from prepare_expansion_ranker import targets,label
from train_expansion_ranker import batches,assessment


class ExpansionTests(unittest.TestCase):
    def test_bk_search_matches_exhaustive_hamming(self):
        rng=np.random.default_rng(9);values=[int(v) for v in rng.integers(0,2**62,150)]
        tree=BKTree()
        for i,v in enumerate(values):tree.add(v,i)
        for query in values[:8]+[values[0]^7]:
            self.assertEqual(set(tree.query(query)),{i for i,v in enumerate(values) if (v^query).bit_count()<=4})

    def test_same_phash_is_not_sufficient_for_duplicate(self):
        a=dict(phash=0,pixel_sha256='a',thumb=np.zeros((24,32,3),np.uint8))
        b=dict(phash=0,pixel_sha256='b',thumb=np.full((24,32,3),240,np.uint8))
        self.assertFalse(close(a,b))

    def test_empty_intake_requires_exclusive_upstream_label(self):
        image=dict(id='a',location=1,date_captured='2014-01-01 12:00:00',seq_id='s')
        data=dict(categories=[dict(id=0,name='empty'),dict(id=1,name='bird')],images=[image],annotations=[dict(image_id='a',category_id=0)])
        split=dict(splits=dict(train=['1']))
        self.assertEqual(len(cct_records(data,split,10)),1)
        data['annotations'].append(dict(image_id='a',category_id=1))
        self.assertEqual(cct_records(data,split,10),[])

    def test_coco_intake_rejects_other_classes_and_unapproved_license(self):
        data=dict(categories=[dict(id=16,name='bird')],images=[dict(id=1,license=4),dict(id=2,license=3)],
                  annotations=[dict(image_id=i,category_id=16,segmentation=[[0,0,10,0,10,10]],iscrowd=0) for i in (1,2)])
        self.assertEqual([r[0]['id'] for r in coco_records(data)],[1])

    def test_new_nabirds_has_positive_only_exact_visible_eye_supervision(self):
        row=dict(source='NABirds',eyes=[[40.,50.]])
        self.assertEqual(label(row,{},[40,50],True),(1,'NABirds_visible_human_eye',1.))
        self.assertIsNone(label(row,{},[40,50],False)[0])
        self.assertIsNone(label(row,{},[300,200],True)[0])

    def test_empty_targets_require_verified_source_and_do_not_modify_pixels(self):
        pixels=np.full((256,384,3),120,np.uint8);saved=pixels.copy()
        row=dict(source='CCT',absent=True,label_source='CCT_explicit_empty')
        sample=targets(row,pixels)
        self.assertTrue(sample['known'].all());self.assertEqual(sample['target'].sum(),0)
        self.assertTrue(np.array_equal(pixels,saved))
        row['label_source']='detector_abstention'
        with self.assertRaises(ValueError):targets(row,pixels)

    def test_coco_mask_does_not_establish_whole_scene_absence(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'mask.png';mask=np.zeros((256,384),np.uint8);mask[40:60,40:60]=255;Image.fromarray(mask).save(path)
            row=dict(source='COCO-2017',foreground_mask=str(path),foreground_mask_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),objects=[dict(box=[30,30,70,70])],uncertain=[])
            sample=targets(row,np.zeros((256,384,3),np.uint8))
            self.assertEqual(label(row,sample,[50,50])[0],1)
            self.assertEqual(label(row,sample,[32,32])[0],0)
            self.assertIsNone(label(row,sample,[38,50])[0])
            self.assertIsNone(label(row,sample,[200,200])[0])

    def test_location_calibration_is_disjoint_and_deterministic(self):
        rows=[dict(source='CCT',group='cam'+str(i)) for i in range(20)]
        held=split_empty_locations(rows)
        self.assertEqual(held,split_empty_locations(list(reversed(rows))))
        self.assertEqual(len(held),4)

    def test_empty_quota_preserves_positive_sampling(self):
        def frame(source,group,pos,easy,hard):
            return dict(source=source,group=group,image_id=group,positive=pos,easy_negative=easy,hard_negative=hard)
        old=SimpleNamespace(index=dict(frames=[frame('CUB-200-2011','cub',[0],[1],[1]),frame('community','real',[2],[3],[3])],records=[dict(label_source=x) for x in ['positive','old_negative','positive','old_negative']]))
        new=SimpleNamespace(index=dict(frames=[frame('NABirds','nab',[0],[],[]),frame('COCO-2017','coco',[1],[2],[2]),frame('CCT','cam',[],[3],[3])],records=[dict(label_source=x) for x in ['positive','positive','COCO_negative','CCT_explicit_empty']]))
        a=list(batches(old,new,3,0,False,256));b=list(batches(old,new,3,0,True,256))
        self.assertEqual([x[1] for x in a],[x[1] for x in b])
        self.assertFalse(any('CCT_explicit_empty' in x[2] for x in a))
        self.assertTrue(any('CCT_explicit_empty' in x[2] for x in b))

    def test_empty_gate_uses_actual_proposals_not_injected_random_points(self):
        real=SimpleNamespace(labels=np.array([1,0]),index=dict(frames=[dict(indices=[0,1])]))
        public=SimpleNamespace(labels=np.array([1]),index=dict(frames=[dict(proposed=[0])]))
        new=SimpleNamespace(labels=np.array([0,0,0,1]),index=dict(frames=[dict(source='CCT',proposed=[0],group='a'),dict(source='CCT',proposed=[1],group='b')],records=[dict(index=0,label=0,label_source='CCT_explicit_empty'),dict(index=1,label=0,label_source='CCT_explicit_empty'),dict(index=2,label=0,label_source='CCT_explicit_empty'),dict(index=3,label=1,label_source='NABirds_visible_human_eye')]))
        with patch('train_expansion_ranker.scores',side_effect=[np.array([.99,.1]),np.array([.99]),np.array([.96,.97,.99999,.99])]):
            evaluation=assessment(None,real,public,new)
            result=evaluation['selected']
        self.assertTrue(json.loads(json.dumps(evaluation))['curve'])
        self.assertEqual(result['threshold'],.99);self.assertEqual(result['empty_false_frames'],0)


if __name__=='__main__':unittest.main()
