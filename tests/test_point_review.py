import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('build_point_review',ROOT/'scripts/annotator/build_point_review.py')
BUILD=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)
IMPORT_SPEC=importlib.util.spec_from_file_location('import_point_review',ROOT/'scripts/annotator/import_point_review.py')
IMPORT=importlib.util.module_from_spec(IMPORT_SPEC)
IMPORT_SPEC.loader.exec_module(IMPORT)


class PointReviewTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node required for browser state engine test')
    def test_explicit_confirmation_restore_and_edit_semantics(self):
        core=ROOT/'scripts/annotator/point_review_core.js'
        script=r'''
const assert=require('node:assert/strict');
const Review=require(process.argv[1]);
const items=[{image_id:'test_a',candidate_id:'ca',input_sha256:'sa',point_xy:[1,2],human_confirmed:true},
             {image_id:'test_b',candidate_id:'cb',input_sha256:'sb',point_xy:[3,4]}];
const r=new Review(items,'test_dataset');
assert.equal(r.stats().confirmed,0); // AI input cannot create human confirmation.
r.get('test_b');r.export();assert.equal(r.stats().confirmed,0);
r.edit('test_a',{note:'diagnostic'});assert.equal(r.stats().confirmed,0);
r.confirm('test_a','supported');assert.equal(r.stats().supported,1);
assert.equal(r.export().records[0].accepted_for_training,false);
const restored=new Review(items,'test_dataset');restored.restore(r.export());assert.equal(restored.stats().confirmed,1);
restored.edit('test_a',{part:'head'});assert.equal(restored.stats().confirmed,0);
const ai=r.export();ai.records[0].actor_kind='ai';
const blank=new Review(items,'test_dataset');assert.throws(()=>blank.restore(ai));assert.equal(blank.stats().confirmed,0);
const bad=r.export();bad.records[0].point_xy=[999,999];assert.throws(()=>blank.restore(bad));
const different=r.export();different.dataset_id='other';assert.throws(()=>blank.restore(different));
const ordered=r.export();ordered.records=ordered.records.map(x=>Object.fromEntries(Object.entries(x).reverse()));
assert.equal(r.restore(ordered),0); // JSON key order is not a revision conflict.
r.confirm('test_b','unknown');assert.equal(r.stats().unknown,1);assert.equal(r.stats().confirmed,2);
r.unconfirm('test_b');assert.equal(r.stats().confirmed,1);
'''
        result=subprocess.run(['node','-e',script,str(core)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)

    def make_workspace(self,root):
        (root/'drafts').mkdir()
        source=root/'input.png';source.write_bytes(b'fixture input')
        panel=root/'view.png';panel.write_bytes(b'fixture view')
        sha=hashlib.sha256(source.read_bytes()).hexdigest()
        record=dict(image_id='test_a',source_sha256=sha,source_path=str(source),point_xy=[1,2],
                    panel_path=str(panel),panel_sha256=hashlib.sha256(panel.read_bytes()).hexdigest())
        (root/'manifest.json').write_text(json.dumps(dict(records=[record])),encoding='utf-8')
        draft=dict(image_id='test_a',input_sha256=sha,point_xy=[1,2],actor_kind='ai',status='draft',
                   human_confirmed=False,accepted_for_training=False,
                   judgement=dict(capture_hint='unknown',note='</script><script>bad()</script>'))
        (root/'drafts/test_a.json').write_text(json.dumps(draft),encoding='utf-8')
        return panel

    def test_self_contained_page_preserves_ai_draft_and_escapes_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.make_workspace(root)
            output=root/'review.html';result=BUILD.build(root,output)
            html=output.read_text(encoding='utf-8')
            self.assertEqual(result['initial_human_confirmed'],0)
            self.assertIn('data:image/png;base64,',html)
            self.assertNotIn('</script><script>bad()',html)
            seed=json.loads(re.search(r'<script type="application/json" id="seed">(.*?)</script>',html,re.S).group(1))
            self.assertEqual(seed['items'][0]['ai']['note'],'</script><script>bad()</script>')
            self.assertNotIn(str(root),html)
            with self.assertRaises(ValueError):BUILD.build(root,output)

    def test_changed_view_or_confirmed_ai_draft_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);panel=self.make_workspace(root)
            panel.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'View changed'):BUILD.build(root,root/'out.html')
            draft=root/'drafts/test_a.json';d=json.loads(draft.read_text(encoding='utf-8'));d['human_confirmed']=True
            draft.write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'unconfirmed'):BUILD.build(root,root/'out.html')

    def export_fixture(self,root):
        self.make_workspace(root)
        output=root/'review.html';BUILD.build(root,output)
        seed=json.loads(re.search(r'<script type="application/json" id="seed">(.*?)</script>',output.read_text(encoding='utf-8'),re.S).group(1))
        item=seed['items'][0]
        prior={k:item[k] for k in ('image_id','candidate_id','input_sha256','point_xy')}
        prior.update(revision=0,choice=None,eye_localizable_input='unknown',part='unknown',note='',
                     actor_kind='human',status='draft',human_confirmed=False,accepted_for_training=False)
        record=dict(prior,revision=1,choice='supported',status='confirmed',human_confirmed=True,
                    confirmed_at_utc='2026-10-26T09:00:00Z',history=[prior])
        payload=dict(schema='point-surface-human-review-v1',dataset_id=seed['dataset_id'],records=[record],
                     accepted_for_training=False,old_development_data=True)
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        return payload,manifest

    def test_human_import_preserves_exact_export_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);payload,_=self.export_fixture(root)
            source=root/'export.json';raw=json.dumps(payload).encode();source.write_bytes(raw)
            result=IMPORT.import_export(source,root,root/'imported')
            self.assertEqual(result['human_confirmed'],1)
            self.assertEqual(result['counts'],dict(supported=1,unsupported=0,unknown=0))
            self.assertEqual(result['accepted_for_training'],0)
            self.assertEqual((root/'imported/export.json').read_bytes(),raw)
            with self.assertRaises(ValueError):IMPORT.import_export(source,root,root/'imported')

    def test_import_rejects_changed_identity_training_promotion_and_missing_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);payload,manifest=self.export_fixture(root)
            for mutate in (lambda d:d['records'][0]['point_xy'].__setitem__(0,99),
                           lambda d:d['records'][0].__setitem__('accepted_for_training',True),
                           lambda d:d['records'][0].__setitem__('actor_kind','ai'),
                           lambda d:d['records'][0]['history'][0].__setitem__('input_sha256','other'),
                           lambda d:d.__setitem__('records',[]),
                           lambda d:d['records'][0].__setitem__('confirmed_at_utc','bad')):
                bad=json.loads(json.dumps(payload));mutate(bad)
                with self.assertRaises(ValueError):IMPORT.validate_export(bad,manifest)
            (root/'input.png').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Frozen input changed'):IMPORT.validate_export(payload,manifest)

    def test_import_does_not_count_drafts_or_unknown_as_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);payload,manifest=self.export_fixture(root)
            payload['records'][0]['choice']='unknown'
            result=IMPORT.validate_export(payload,manifest)
            self.assertEqual(result['counts']['unknown'],1)
            payload['records'][0].update(status='draft',human_confirmed=False)
            result=IMPORT.validate_export(payload,manifest)
            self.assertEqual(result['human_confirmed'],0)
            self.assertEqual(result['pending_ids'],['test_a'])


if __name__=='__main__':unittest.main()
