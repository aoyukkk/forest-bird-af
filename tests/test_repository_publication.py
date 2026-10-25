"""Publication contracts: points, reproducibility, links and archive boundaries."""
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'tools'))
sys.path.insert(0, str(ROOT / 'scripts' / 'publish'))
import verify_links
import verify_repo
from export_label_formats import to_coco, to_yolo


class PublicationTests(unittest.TestCase):
    def test_point_does_not_become_a_box(self):
        row = {'image_id': 'fb_0001', 'review_status': 'confirmed',
               'annotation_image': {'input_chw_u8_sha256': '0' * 64},
               'items': [{'id': 'e', 'kind': 'eye', 'point_xy': [12.25, 30.5], 'box_xyxy': None}]}
        coco = to_coco(row)
        self.assertEqual(coco['annotations'], [])
        self.assertEqual(coco['point_annotations'][0]['point_xy'], [12.25, 30.5])
        self.assertNotIn('bbox', coco['point_annotations'][0])
        self.assertEqual(to_yolo(row), '')

    def test_export_rebuild_is_byte_identical(self):
        data = ROOT / 'data' / 'annotations-2026-10-25'
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run([sys.executable, str(ROOT / 'scripts/publish/export_confirmed_labels.py'),
                            '--labels', str(data / 'labels/community-corrections-v1.jsonl'),
                            '--dedupe', str(data / 'curation/dedupe-queue-v1.json'),
                            '--split', str(data / 'splits/evaluation-split-v1.json'),
                            '--output', temp], check=True, capture_output=True)
            for name in ['confirmed.jsonl', 'confirmed.csv', 'summary.json', 'yolo-labels.zip', 'coco/confirmed.coco.json']:
                self.assertEqual((Path(temp) / name).read_bytes(), (data / 'confirmed' / name).read_bytes(), name)

    def test_checksums_cover_published_bytes(self):
        root = ROOT / 'data/annotations-2026-10-25'
        metadata = json.loads((root / 'confirmed/summary.json').read_text(encoding='utf-8'))
        for key, name in [('confirmed_sha256', 'confirmed/confirmed.jsonl'), ('yolo_archive_sha256', 'confirmed/yolo-labels.zip')]:
            self.assertEqual(metadata[key], hashlib.sha256((root / name).read_bytes()).hexdigest())
        normalized = (root / 'labels/community-corrections-v1.jsonl').read_text(encoding='utf-8').encode('utf-8')
        self.assertEqual(metadata['source_labels_sha256'], hashlib.sha256(normalized).hexdigest())
        source_meta = json.loads((root / 'labels/community-corrections-v1.json').read_text(encoding='utf-8'))
        self.assertEqual(source_meta['labels_sha256'], hashlib.sha256(normalized).hexdigest())

    def test_all_markdown_targets_exist(self):
        self.assertEqual(verify_links.broken_links(ROOT), [])

    def test_link_check_ignores_examples_and_accepts_unicode_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '有 空格.md').write_text('# Target', encoding='utf-8')
            (root / 'README.md').write_text('[ok](<有 空格.md>)\n```md\n[example](missing.md)\n```\n[bad](lost.md)', encoding='utf-8')
            problems = verify_links.broken_links(root)
            self.assertEqual([p['target'] for p in problems], ['lost.md'])

    def test_archive_allowance_cannot_hide_weights(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / verify_repo.LABEL_ARCHIVE
            path.parent.mkdir(parents=True)
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('vendor/model.bin', b'not a label')
            with patch.object(sys, 'argv', ['verify_repo.py', temp]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(verify_repo.main(), 1)

    def test_release_catalog_has_all_images_and_publication(self):
        catalog = json.loads((ROOT / 'data/releases.json').read_text(encoding='utf-8'))
        self.assertEqual(sum(r['files'] for r in catalog['releases']), 694)
        self.assertEqual(len(catalog['releases']), 5)
        self.assertEqual(len({r['tag'] for r in catalog['releases']}), 5)


if __name__ == '__main__':
    unittest.main()
