"""Contract tests for the human-confirmed label package."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'tools'))

import verify_annotations as published  # noqa: E402

DATA = ROOT / 'data' / 'annotations-2026-10-25'
CONFIRMED = DATA / 'confirmed'


class ConfirmedPackageTests(unittest.TestCase):
    def setUp(self):
        self.records = [json.loads(line) for line in
                        (CONFIRMED / 'confirmed.jsonl').read_text(encoding='utf-8').splitlines()
                        if line.strip()]
        self.summary = json.loads((CONFIRMED / 'summary.json').read_text(encoding='utf-8'))
        self.labels = {json.loads(line)['image_id']: json.loads(line)
                       for line in (DATA / 'labels' / 'community-corrections-v1.jsonl')
                       .read_text(encoding='utf-8').splitlines() if line.strip()}

    def test_every_confirmed_label_is_exported(self):
        expected = {i for i, row in self.labels.items()
                    if row['review_status'] == 'confirmed'}
        exported = {row['image_id'] for row in self.records}
        self.assertEqual(expected, exported)
        self.assertEqual(len(self.records), self.summary['confirmed_images'])
        self.assertFalse(any(self.labels[r['image_id']]['review_status'] != 'confirmed'
                             for r in self.records))

    def test_geometry_and_counts_match_source_labels(self):
        parts = {'bird': 0, 'head': 0, 'eye': 0}
        for row in self.records:
            source = self.labels[row['image_id']]
            self.assertEqual(row['parts'], source['parts'], row['image_id'])
            for kind in parts:
                parts[kind] += sum(1 for item in row['items'] if item['kind'] == kind)
            for item in row['items']:
                x1, y1, x2, y2 = item['box_xyxy']
                self.assertLess(x1, x2, row['image_id'])
                self.assertLess(y1, y2, row['image_id'])
                self.assertGreaterEqual(x1, -.5, row['image_id'])
                self.assertGreaterEqual(y1, -.5, row['image_id'])
                self.assertLessEqual(x2, 384, row['image_id'])
                self.assertLessEqual(y2, 256, row['image_id'])
        self.assertEqual(parts, self.summary['parts'])

    def test_coco_and_yolo_agree_with_records(self):
        coco = json.loads((CONFIRMED / 'coco' / 'confirmed.coco.json').read_text(encoding='utf-8'))
        self.assertEqual(len(coco['images']), len(self.records))
        self.assertEqual(len(coco['annotations']), self.summary['objects_in_coco'])
        self.assertEqual(len(coco['annotations']),
                         sum(len(row['items']) for row in self.records))
        import zipfile
        archive = zipfile.ZipFile(CONFIRMED / 'yolo-labels.zip')
        self.assertIn('yolo/classes.txt', archive.namelist())
        for row in self.records:
            lines = archive.read('yolo/' + row['image_id'] + '.txt').decode('utf-8')
            rows = [line for line in lines.splitlines() if line.strip()]
            self.assertEqual(len(rows), len(row['items']), row['image_id'])
            for line in rows:
                index, cx, cy, w, h = line.split()
                self.assertIn(int(index), (0, 1, 2), row['image_id'])
                for value in (cx, cy, w, h):
                    self.assertTrue(0.0 <= float(value) <= 1.0, row['image_id'])

    def test_queue_membership_is_reported_not_dropped(self):
        self.assertEqual(self.summary['in_queue'] + self.summary['folded_by_similarity'],
                         self.summary['confirmed_images'])
        for row in self.records:
            if not row['in_queue']:
                self.assertIsNotNone(row['dedupe_root'], row['image_id'])

    def test_no_private_fields_in_confirmed_export(self):
        problems = []
        for row in self.records:
            published.scan_for_private_text(problems, row['image_id'], row)
        self.assertEqual(problems, [])


if __name__ == '__main__':
    unittest.main()
