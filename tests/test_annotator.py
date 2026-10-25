"""Behavioral checks for data identity, concurrent writes and human/AI review."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import copy
from contextlib import closing
import csv
import hashlib
import io
import json
import sqlite3
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from PIL import Image
from forest_bird_annotator.store import Store,Problem,initial,dumps,validate
from forest_bird_annotator.server import create_server
from forest_bird_annotator.importer import import_runs

HUMAN={'id':'reviewer-a','kind':'human'}
AI={'id':'vision-a','kind':'ai'}


def fixture(root,count=2):
    store=Store(root)
    (Path(root)/'images').mkdir(exist_ok=True)
    stream=io.BytesIO();Image.new('RGB',(384,256),'#52784d').save(stream,'PNG');png=stream.getvalue()
    sha=hashlib.sha256(png).hexdigest()
    with store.connect() as c:
        for i in range(1,count+1):
            ident=f'fb_{i:04d}'
            meta={'image_id':ident,'png_sha256':sha,'input_sha256':'a'*64,'preprocess_id':'test-input',
                  'batch':'test','reference_path':None,'reference_width':384,'reference_height':256}
            c.execute('INSERT INTO images VALUES(?,?,?)',(ident,dumps(meta),'[]'))
            (Path(root)/'images'/(ident+'.png')).write_bytes(png)
    return store


def draft(store,ident='fb_0001'):
    r=store.get(ident);a=r['annotation']
    a.update(annotation_status='draft',presence='absent',instances=[],uncertain_regions=[])
    return {'image_id':ident,'base_revision':r['revision'],'annotation':a}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=fixture(self.temp.name)
    def tearDown(self):self.temp.cleanup()

    def test_pending_is_not_absent_and_not_submitted_export(self):
        a=self.store.get('fb_0001')['annotation']
        self.assertIsNone(a['instances']);self.assertIsNone(a['presence'])
        self.assertEqual(self.store.export('complete'),[])
        r=draft(self.store);r['annotation']['annotation_status']='annotated'
        self.store.save_many([r],HUMAN)
        self.assertEqual(len(self.store.export('complete')),1)

    def test_simultaneous_human_ai_writes_preserve_winner_and_history(self):
        base=draft(self.store);barrier=threading.Barrier(2);out=[]
        def write(who):
            row=copy.deepcopy(base);row['annotation']['notes']=who['kind'];barrier.wait()
            try:out.append(('ok',self.store.save_many([row],who)))
            except Problem as e:out.append((e.status,str(e)))
        ts=[threading.Thread(target=write,args=(a,)) for a in (HUMAN,AI)]
        for t in ts:t.start()
        for t in ts:t.join()
        self.assertEqual(sorted(str(x[0]) for x in out),['409','ok'])
        self.assertEqual(self.store.get('fb_0001')['revision'],1)
        self.assertEqual(len(self.store.history('fb_0001')),1)

    def test_bulk_conflict_rolls_back_every_image(self):
        r1=draft(self.store);r2=draft(self.store,'fb_0002')
        self.store.save_many([r2],HUMAN)
        with self.assertRaises(Problem):self.store.save_many([r1,r2],AI)
        self.assertEqual(self.store.get('fb_0001')['revision'],0)

    def test_ai_cannot_self_approve_and_human_review_records_independence(self):
        r=draft(self.store);r['annotation']['annotation_status']='annotated'
        saved=self.store.save_many([r],AI)[0]
        record={'image_id':saved['image_id'],'base_revision':saved['revision'],'annotation':saved['annotation']}
        record['annotation']['annotation_status']='reviewed'
        with self.assertRaises(Problem):self.store.save_many([record],AI)
        reviewed=self.store.save_many([record],HUMAN)[0]
        self.assertTrue(reviewed['annotation']['review']['independent'])
        self.assertEqual(reviewed['annotation']['provenance']['content_actor'],AI)
        self.assertEqual(len(self.store.history('fb_0001')),2)

    def test_review_cannot_hide_content_edits(self):
        r=draft(self.store);r['annotation']['annotation_status']='annotated'
        saved=self.store.save_many([r],HUMAN)[0]
        saved['annotation']['annotation_status']='reviewed';saved['annotation']['notes']='unsubmitted edit'
        with self.assertRaises(Problem):self.store.save_many([{'image_id':'fb_0001','base_revision':1,'annotation':saved['annotation']}],HUMAN)

    def test_identity_and_geometry_validation(self):
        r=draft(self.store);r['annotation']['annotation_image']['width']=100
        with self.assertRaises(Problem):self.store.save_many([r],AI)
        r=draft(self.store);a=r['annotation'];a['presence']='present'
        b={'instance_id':'b1','bird_bbox_xyxy':[10,10,100,100],'head_bbox_xyxy':None,'eyes':[],
           'af_reference_target_input':'body','af_anchor_input_xy':None,'part_visibility':{'bird':'visible'},
           'occluder_types':[],'occluded_parts':[],'invisibility_reasons':[]}
        a['instances']=[b];a['annotation_status']='annotated'
        with self.assertRaises(Problem) as error:self.store.save_many([r],HUMAN)
        self.assertIn('anchor_required',str(error.exception.details))
        b['af_anchor_input_xy']=[30,40];b['bird_bbox_xyxy']=[0,0,385,256]
        with self.assertRaises(Problem):self.store.save_many([r],HUMAN)
        b['bird_bbox_xyxy']=[0,0,384,256];b['af_anchor_input_xy']=[float('nan'),0]
        with self.assertRaises(Problem):self.store.save_many([r],HUMAN)
        b['bird_bbox_xyxy']=[10,10,100,100];b['af_anchor_input_xy']=[200,100]
        with self.assertRaises(Problem) as error:self.store.save_many([r],HUMAN)
        self.assertIn('anchor_outside_target',str(error.exception.details))

    def test_claims_do_not_assign_same_image_and_backup_contains_history(self):
        first=self.store.claim(AI);second=self.store.claim({'id':'vision-b','kind':'ai'})
        self.assertNotEqual(first['image_id'],second['image_id'])
        self.assertIsNone(self.store.claim(HUMAN))
        self.store.save_many([draft(self.store)],HUMAN)
        backup=self.store.backup()
        with closing(sqlite3.connect(backup)) as c:self.assertEqual(c.execute('SELECT count(*) FROM history').fetchone()[0],1)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=fixture(self.temp.name)
        self.server=create_server(self.temp.name,0);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path,method='GET',value=None,headers=None):
        req=Request(self.url+path,data=json.dumps(value).encode() if value is not None else None,method=method,
                    headers={'Content-Type':'application/json',**(headers or {})})
        return urlopen(req,timeout=5)

    def test_frontend_api_roundtrip_and_conflict(self):
        with self.request('/') as r:self.assertIn(b'canvas',r.read())
        row=draft(self.store)
        with self.request('/api/annotations/fb_0001','PUT',{**row,'actor':AI}) as r:
            saved=json.load(r);self.assertEqual(saved['revision'],1)
        with self.assertRaises(HTTPError) as e:self.request('/api/annotations/fb_0001','PUT',{**row,'actor':HUMAN})
        self.assertEqual(e.exception.code,409)

    def test_origin_guard_and_served_input_hash(self):
        with self.assertRaises(HTTPError) as e:self.request('/api/backup','POST',{},headers={'Origin':'https://example.com'})
        self.assertEqual(e.exception.code,403)
        with self.assertRaises(HTTPError) as e:self.request('/api/dataset',headers={'Host':'evil.invalid'})
        self.assertEqual(e.exception.code,403)
        with self.request('/api/images/fb_0001/png') as r:self.assertEqual(r.headers['Content-Type'],'image/png')
        (Path(self.temp.name)/'images/fb_0001.png').write_bytes(b'modified')
        with self.assertRaises(HTTPError) as e:self.request('/api/images/fb_0001/png')
        self.assertEqual(e.exception.code,409)


class ImportTests(unittest.TestCase):
    def test_exact_chw_pixels_import_and_increment_preserves_labels(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'runs/run_001';(run/'inputs').mkdir(parents=True)
            reference=root/'reference.png';Image.new('RGB',(384,256),'#52784d').save(reference)
            reference_sha=hashlib.sha256(reference.read_bytes()).hexdigest()
            raw=bytes([1])*(384*256)+bytes([100])*(384*256)+bytes([250])*(384*256)
            row={'image_id':'fb_0001','input_sha256':hashlib.sha256(raw).hexdigest(),
                'preprocess_id':'review-EXIF-RGB-bilinear-stretch-384x256-u8-div256-v1',
                'review_relative_path':str(reference),'review_sha256':reference_sha,'width':384,'height':256,'candidates':[]}
            (run/'inputs/fb_0001.bin').write_bytes(raw)
            (run/'predictions.jsonl').write_text(dumps(row)+'\n',encoding='utf-8')
            (run/'summary.json').write_text('{"complete":true,"failed":[]}',encoding='utf-8')
            registry=root/'registry.csv'
            with registry.open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=['image_id','original_sha256','review_sha256','release_tag']);w.writeheader()
                w.writerow({'image_id':'fb_0001','original_sha256':'b'*64,'review_sha256':reference_sha,'release_tag':'test'})
            workspace=root/'workspace'
            self.assertTrue(import_runs(workspace,root/'runs',registry)['passed'])
            with Image.open(workspace/'images/fb_0001.png') as im:self.assertEqual(im.getpixel((100,50)),(1,100,250))
            store=Store(workspace);store.save_many([draft(store)],HUMAN)
            import_runs(workspace,root/'runs',registry)
            self.assertEqual(store.get('fb_0001')['revision'],1)
            (run/'inputs/fb_0001.bin').write_bytes(b'bad')
            with self.assertRaises(Problem):import_runs(workspace,root/'runs',registry)
            self.assertEqual(store.get('fb_0001')['revision'],1)


if __name__=='__main__':unittest.main(verbosity=2)
