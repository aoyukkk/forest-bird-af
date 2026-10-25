"""Acceptance/correction evidence must never be inferred from mere browsing."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import test_annotator as helpers
from forest_bird_annotator import z8_review as z8
from forest_bird_annotator.store import Problem, dumps

fixture,draft,HUMAN,AI=helpers.fixture,helpers.draft,helpers.HUMAN,helpers.AI


class Z8ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=fixture(self.temp.name)
        self.pred=[{'class_slot':0,'box_input_xyxy':[10,20,160,180],'native_integer_score':900},
                   {'class_slot':1,'box_input_xyxy':[30,30,80,70],'native_integer_score':800},
                   {'class_slot':5,'box_input_xyxy':[40,50,90,120],'native_integer_score':700}]
        with self.store.connect() as c:c.execute('UPDATE images SET predictions=? WHERE id=?',(dumps(self.pred),'fb_0001'))

    def tearDown(self):self.temp.cleanup()

    def payload(self,ident='fb_0001',action='confirm',who=HUMAN):
        r=z8.get(self.store,ident);r['review']['presence']='present' if r['review']['items'] else None
        return {'base_revision':r['revision'],'review':r['review'],'actor':who,'action':action}

    def test_browsing_starts_from_z8_not_llm_and_does_not_confirm(self):
        label=draft(self.store);label['annotation']['notes']='old LLM record'
        self.store.save_many([label],AI);before=self.store.get('fb_0001')
        for _ in range(3):
            r=z8.get(self.store,'fb_0001');self.assertEqual(r['revision'],0)
            self.assertEqual(r['review']['items'],r['baseline']['items'])
            self.assertEqual(r['review']['status'],'pending')
        self.assertEqual(z8.export(self.store,'confirmed'),[])
        self.assertEqual(z8.history(self.store,'fb_0001'),[])
        self.assertEqual(self.store.get('fb_0001'),before)
        self.assertEqual(r['review']['items'][-1]['kind'],'auxiliary')

    def test_unchanged_confirmation_preserves_raw_predictions_and_manual_labels(self):
        original=self.store.image('fb_0001')['predictions']
        p=self.payload();p['review']['decision']='error'
        r=z8.save(self.store,'fb_0001',p)
        self.assertEqual(r['review']['decision'],'correct')
        self.assertEqual(r['review']['confirmed_by'],HUMAN)
        self.assertEqual(r['review']['diff']['modified_count'],0)
        self.assertEqual(self.store.get('fb_0001')['revision'],0)
        self.assertEqual(self.store.image('fb_0001')['predictions'],original)

    def test_partial_changes_capture_exact_before_after_parts_and_deletions(self):
        p=self.payload();p['review']['items'][1]['box_xyxy']=[31,30,81,70]
        p['review']['items'].pop();p['review']['items'].append({'id':'n1','kind':'eye','box_xyxy':None,'point_xy':[55,45]});p['review']['next_id']=2
        r=z8.save(self.store,'fb_0001',p)['review'];d=r['diff']
        self.assertEqual(r['decision'],'partial_error')
        self.assertEqual(d['unchanged_ids'],['p0'])
        self.assertEqual(d['changed'][0]['before']['box_xyxy'],[30,30,80,70])
        self.assertEqual(d['changed'][0]['after']['box_xyxy'],[31,30,81,70])
        self.assertEqual(d['removed'][0]['id'],'p2')
        self.assertEqual(set(d['changed_parts']),{'head','eye','auxiliary'})

    def test_all_changed_and_missing_detection_are_errors(self):
        p=self.payload();p['review']['items']=[];p['review']['presence']='absent'
        r=z8.save(self.store,'fb_0001',p);self.assertEqual(r['review']['decision'],'error')
        p=self.payload('fb_0002');p['review'].update(presence='present',next_id=2,items=[{'id':'n1','kind':'bird','box_xyxy':[1,2,90,150],'point_xy':None}])
        self.assertEqual(z8.save(self.store,'fb_0002',p)['review']['decision'],'error')

    def test_zero_candidate_is_not_a_negative_until_explicit_confirmation(self):
        p=self.payload('fb_0002')
        with self.assertRaises(Problem):z8.save(self.store,'fb_0002',p)
        p['review']['presence']='present'
        with self.assertRaises(Problem):z8.save(self.store,'fb_0002',p)
        p['review']['presence']='absent'
        self.assertEqual(z8.save(self.store,'fb_0002',p)['review']['decision'],'correct')

    def test_ai_can_save_draft_but_cannot_approve(self):
        p=self.payload(who=AI)
        with self.assertRaises(Problem):z8.save(self.store,'fb_0001',p)
        p['action']='draft';r=z8.save(self.store,'fb_0001',p)
        self.assertEqual(r['review']['decision'],'unassessed');self.assertIsNone(r['review']['confirmed_by'])
        self.assertEqual(z8.export(self.store,'confirmed'),[])

    def test_stale_revision_conflict_and_immutable_history(self):
        p=self.payload();first=z8.save(self.store,'fb_0001',p)
        with self.assertRaises(Problem) as e:z8.save(self.store,'fb_0001',p)
        self.assertEqual(e.exception.status,409)
        p=self.payload(action='draft');p['review']['items'][0]['box_xyxy'][0]+=1
        r=z8.save(self.store,'fb_0001',p)
        self.assertEqual(r['review']['status'],'draft');self.assertIsNone(r['review']['confirmed_by'])
        self.assertEqual(z8.export(self.store,'confirmed'),[])
        self.assertEqual(z8.history(self.store,'fb_0001')[1]['review'],first['review'])

    def test_tampering_invalid_geometry_and_recycled_ids_are_rejected(self):
        p=self.payload();p['review']['baseline_sha256']='fake'
        with self.assertRaises(Problem):z8.save(self.store,'fb_0001',p)
        p=self.payload();p['review']['items'][0]['box_xyxy'][0]=float('nan')
        with self.assertRaises(Problem):z8.save(self.store,'fb_0001',p)
        p=self.payload();p['review']['items'].append({'id':'p99','kind':'bird','box_xyxy':[1,2,4,5],'point_xy':None})
        with self.assertRaises(Problem):z8.save(self.store,'fb_0001',p)
        p=self.payload(action='draft');p['review']['next_id']=5;z8.save(self.store,'fb_0001',p)
        p=self.payload();p['review']['next_id']=1
        with self.assertRaises(Problem):z8.save(self.store,'fb_0001',p)

    def test_native_edge_boxes_are_not_silently_changed(self):
        self.pred[0]['box_input_xyxy']=[-0.5,20,160,180]
        with self.store.connect() as c:c.execute('UPDATE images SET predictions=? WHERE id=?',(dumps(self.pred),'fb_0001'))
        p=self.payload();r=z8.save(self.store,'fb_0001',p)
        self.assertEqual(r['review']['decision'],'correct');self.assertEqual(r['review']['items'][0]['box_xyxy'][0],-.5)
        p=self.payload();p['review']['items'][0]['box_xyxy'][1]=21
        with self.assertRaises(Problem):z8.save(self.store,'fb_0001',p)

    def test_uncertain_is_not_a_confirmed_correct_label(self):
        p=self.payload(action='uncertain');p['review']['presence']='uncertain'
        r=z8.save(self.store,'fb_0001',p)
        self.assertEqual(r['review']['status'],'needs_adjudication')
        self.assertEqual(r['review']['decision'],'uncertain')
        self.assertEqual(z8.export(self.store,'confirmed'),[])
        self.assertEqual(len(z8.export(self.store,'uncertain')),1)


class Z8HTTPTests(unittest.TestCase):
    setUp=helpers.HTTPTests.setUp
    tearDown=helpers.HTTPTests.tearDown
    request=helpers.HTTPTests.request
    def test_new_default_ui_and_review_api_are_separate(self):
        with self.request('/') as r:self.assertIn('z8-review.js',r.read().decode())
        with self.request('/annotate') as r:self.assertIn('app.js',r.read().decode())
        with self.request('/api/z8-review/schema') as r:self.assertEqual(json.load(r)['schema_version'],z8.SCHEMA)
        with self.request('/api/z8-review/fb_0001') as r:record=json.load(r)
        self.assertEqual(record['revision'],0);record['review']['presence']='absent'
        with self.request('/api/z8-review/fb_0001','PUT',{'base_revision':0,'review':record['review'],'actor':HUMAN,'action':'confirm'}) as r:saved=json.load(r)
        self.assertEqual(saved['review']['decision'],'correct')
        with self.request('/api/z8-review/export?scope=confirmed') as r:lines=r.read().decode().splitlines()
        self.assertEqual(len(lines),1)
        with self.request('/api/z8-review/dataset') as r:queue=json.load(r)['images']
        self.assertEqual(queue[0]['status'],'confirmed')
        self.assertEqual(self.store.get('fb_0001')['revision'],0)


if __name__=='__main__':unittest.main()
