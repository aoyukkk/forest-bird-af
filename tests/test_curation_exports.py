"""Contract tests for the published curation lists (queue and best images)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'tools'))

import verify_annotations as published  # noqa: E402

DATA = ROOT / 'data' / 'annotations-2026-10-25'


class CurationExportTests(unittest.TestCase):
    def setUp(self):
        self.queue = json.loads((DATA / 'curation' / 'dedupe-queue-v1.json').read_text(encoding='utf-8'))
        self.best = json.loads((DATA / 'curation' / 'best-images-v1.json').read_text(encoding='utf-8'))
        self.labels = {json.loads(line)['image_id']: json.loads(line)
                       for line in (DATA / 'labels' / 'community-corrections-v1.jsonl')
                       .read_text(encoding='utf-8').splitlines() if line.strip()}

    def test_queue_hides_without_inventing(self):
        self.assertEqual(len(self.queue['images']), 694)
        folded = [row for row in self.queue['images'] if row['dedupe_root']]
        self.assertEqual(len(folded), self.queue['summary']['folded'])
        for row in folded:
            self.assertFalse(row['in_queue'], row['image_id'])
            self.assertIn(row['dedupe_root'], self.labels, row['image_id'])
        queue = [row for row in self.queue['images'] if row['in_queue']]
        self.assertEqual(len(queue), self.queue['summary']['queue'])
        self.assertTrue(all(row['dedupe_root'] is None for row in queue))

    def test_folded_groups_never_span_splits(self):
        self.assertEqual(self.queue['summary']['split_mismatch_pairs'], 0)
        by_id = {row['image_id']: row for row in self.queue['images']}
        for group in self.queue['groups']:
            self.assertIn(group['representative'], group['members'])
            member_splits = {by_id[m]['split'] for m in group['members']
                             if by_id[m]['split']}
            self.assertLessEqual(len(member_splits), 1, group['representative'])

    def test_best_images_only_confirmed_queue_frames(self):
        for row in self.best['images']:
            record = self.labels[row['image_id']]
            self.assertEqual(record['review_status'], 'confirmed', row['image_id'])
            self.assertIn(row['image_id'], {r['image_id'] for r in self.queue['images']
                                            if r['in_queue']})
            self.assertTrue(any(row['parts'].values()), row['image_id'])
        self.assertEqual(self.best['listed'], len(self.best['images']))

    def test_checker_rejects_queue_with_split_leak(self):
        with tempfile.TemporaryDirectory() as temp:
            broken = dict(self.queue)
            broken['images'] = [dict(row) for row in self.queue['images']]
            broken['images'][0]['dedupe_root'] = 'fb_0002'
            broken['images'][0]['in_queue'] = False
            path = Path(temp) / 'dedupe-queue-v1.json'
            path.write_text(json.dumps(broken, ensure_ascii=False), encoding='utf-8')
            problems = []
            splits = {'fb_0001': 'train', 'fb_0002': 'test'}
            published.verify_queue(problems, path, set(self.labels), splits)
            self.assertTrue(any('spans published splits' in p for p in problems), problems)


if __name__ == '__main__':
    unittest.main()
