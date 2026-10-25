"""Deduplication may change queue membership, never images or saved labels."""
from pathlib import Path
import copy
import hashlib
import json
import tempfile
import unittest
from PIL import Image,ImageFilter,ImageDraw
import test_annotator as helpers
from forest_bird_annotator import dedupe,z8_review
from forest_bird_annotator.store import Problem,dumps


class DedupeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=helpers.fixture(self.temp.name,5)
        # A textured image and exact copies, a blurred variant and an unrelated scene.
        import random
        rng=random.Random(19);im=Image.new('RGB',(384,256));im.putdata([(rng.randrange(256),rng.randrange(256),rng.randrange(256)) for _ in range(384*256)])
        for ident,image in [('fb_0001',im),('fb_0002',im),('fb_0003',im.filter(ImageFilter.GaussianBlur(5))),('fb_0004',Image.new('RGB',(384,256),'red')),('fb_0005',im)]:
            path=self.store.root/'images'/(ident+'.png');image.save(path)
            with self.store.connect() as c:
                meta=json.loads(c.execute('SELECT metadata FROM images WHERE id=?',(ident,)).fetchone()[0]);meta['png_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                c.execute('UPDATE images SET metadata=? WHERE id=?',(dumps(meta),ident))
        record=z8_review.get(self.store,'fb_0002');record['review']['presence']='absent'
        z8_review.save(self.store,'fb_0002',{'base_revision':0,'review':record['review'],'actor':helpers.HUMAN,'action':'confirm'})

    def tearDown(self):self.temp.cleanup()

    def snapshot(self):
        with self.store.connect() as c:return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t+' ORDER BY 1,2')] for t in ('images','annotations','history','z8_reviews','z8_review_history')}

    def test_scan_retains_annotations_and_prefers_confirmed(self):
        before=self.snapshot();result=dedupe.scan(self.store)
        self.assertEqual(result['hidden'],{'fb_0001':'fb_0002','fb_0005':'fb_0002'})
        self.assertNotIn('fb_0003',result['hidden']);self.assertNotIn('fb_0004',result['hidden'])
        self.assertEqual(before,self.snapshot());self.assertTrue((self.store.root/'backups'/result['annotation_backup']).exists())
        self.assertEqual(dedupe.scan(self.store)['hidden'],result['hidden'])
        self.assertEqual(before,self.snapshot())

    def test_keep_and_manual_hide_survive_rescan_and_reject_cycles(self):
        dedupe.scan(self.store);before=self.snapshot()
        r=dedupe.decide(self.store,{'action':'keep','image_id':'fb_0001'});self.assertNotIn('fb_0001',r['hidden'])
        self.assertNotIn('fb_0001',dedupe.scan(self.store)['hidden'])
        r=dedupe.decide(self.store,{'action':'hide','image_id':'fb_0003','representative':'fb_0002'})
        self.assertEqual(r['hidden']['fb_0003'],'fb_0002')
        with self.assertRaises(Problem):dedupe.decide(self.store,{'action':'hide','image_id':'fb_0002','representative':'fb_0003'})
        with self.assertRaises(Problem):dedupe.decide(self.store,{'action':'hide','image_id':'fb_0004','representative':'../../bad'})
        self.assertEqual(dedupe.scan(self.store)['hidden']['fb_0003'],'fb_0002');self.assertEqual(before,self.snapshot())

    def test_stale_fingerprint_disables_hiding(self):
        dedupe.scan(self.store)
        with self.store.connect() as c:
            meta=json.loads(c.execute('SELECT metadata FROM images WHERE id=?',('fb_0001',)).fetchone()[0]);meta['png_sha256']='b'*64
            c.execute('UPDATE images SET metadata=? WHERE id=?',(dumps(meta),'fb_0001'))
        r=dedupe.read(self.store);self.assertTrue(r['stale']);self.assertEqual(r['hidden'],{})
        with self.assertRaises(Problem):dedupe.scan(self.store)

    def test_no_transitive_collapse(self):
        # Direct-neighbor star grouping is checked against recorded pair evidence.
        r=dedupe.scan(self.store)
        direct={frozenset((p['a'],p['b'])) for p in r['pairs'] if p['collapse']}
        for member,representative in r['hidden'].items():self.assertIn(frozenset((member,representative)),direct)

    def test_one_click_uses_numbered_previous_and_reverses_automatic_root(self):
        dedupe.scan(self.store);before=self.snapshot()
        # The confirmed current image was automatically selected as the root.
        self.assertEqual(dedupe.read(self.store)['hidden']['fb_0001'],'fb_0002')
        r=dedupe.decide(self.store,{'action':'previous','image_id':'fb_0002'})
        self.assertEqual(r['hidden']['fb_0002'],'fb_0001');self.assertNotIn('fb_0001',r['hidden'])
        self.assertEqual(r['last_decision']['previous_image_id'],'fb_0001')
        self.assertEqual(dedupe.scan(self.store)['hidden']['fb_0002'],'fb_0001')
        dedupe.decide(self.store,{'action':'hide','image_id':'fb_0004','representative':'fb_0003'})
        r=dedupe.decide(self.store,{'action':'previous','image_id':'fb_0005'})
        self.assertEqual(r['last_decision']['previous_image_id'],'fb_0004')
        self.assertEqual(r['hidden']['fb_0005'],'fb_0003','follow hidden previous to its root')
        with self.assertRaises(Problem):dedupe.decide(self.store,{'action':'previous','image_id':'fb_0001'})
        self.assertEqual(self.snapshot(),before)

    def test_one_click_needs_no_prior_scan(self):
        before=self.snapshot();r=dedupe.decide(self.store,{'action':'previous','image_id':'fb_0002'})
        self.assertEqual(r['hidden'],{'fb_0002':'fb_0001'});self.assertEqual(before,self.snapshot())

    def test_restore_returns_image_to_queue_without_touching_labels(self):
        before=self.snapshot()
        r=dedupe.decide(self.store,{'action':'previous','image_id':'fb_0002'})
        self.assertEqual(r['hidden'],{'fb_0002':'fb_0001'})
        restored=dedupe.decide(self.store,{'action':'restore','image_id':'fb_0002'})
        self.assertNotIn('fb_0002',restored['hidden'])
        self.assertNotIn('fb_0002',restored['manual_hidden'])
        self.assertEqual(restored['summary']['manual_hidden'],0)
        self.assertEqual(restored['summary']['visible'],5)
        self.assertEqual(restored['last_decision']['action'],'restore')
        self.assertEqual(before,self.snapshot())
        # Restoring an image that was never excluded is a no-op, not an error.
        again=dedupe.decide(self.store,{'action':'restore','image_id':'fb_0002'})
        self.assertEqual(again['hidden'],{})
        with self.assertRaises(Problem):dedupe.decide(self.store,{'action':'restore','image_id':'fb_9999'})
        self.assertEqual(before,self.snapshot())

    def test_api_does_not_expose_private_backup_paths(self):
        import threading
        from urllib.request import Request,urlopen
        from forest_bird_annotator.server import create_server
        server=create_server(self.temp.name,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url=f'http://127.0.0.1:{server.server_port}/api/z8-review/dedupe'
            request=Request(url,data=b'{"action":"scan"}',headers={'Content-Type':'application/json'},method='POST')
            with urlopen(request) as response:r=json.load(response)
            self.assertEqual(r['summary']['images'],5);self.assertNotIn('annotation_backup',r);self.assertNotIn('pairs',r)
            with urlopen(url) as response:self.assertEqual(json.load(response)['hidden'],r['hidden'])
            request=Request(url,data=b'{"action":"previous","image_id":"fb_0002"}',headers={'Content-Type':'application/json'},method='POST')
            with urlopen(request) as response:self.assertEqual(json.load(response)['hidden']['fb_0002'],'fb_0001')
            with urlopen(url.replace('/dedupe','/export?scope=usable')) as response:self.assertEqual(response.read(),b'')
            with urlopen(url.replace('/dedupe','/export?scope=confirmed')) as response:self.assertIn(b'fb_0002',response.read())
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
