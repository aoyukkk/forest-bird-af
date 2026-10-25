"""Contract tests for the published annotation exports.

Standard library only, so the checks run without the training stack, CUDA or the
vendor package::

    python -m unittest tests.test_published_exports -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import verify_annotations as published  # noqa: E402


class PublishedExportTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'data' / 'annotations-2026-10-25'
        self.labels = self.root / 'labels' / 'community-corrections-v1.jsonl'
        self.manifest = self.root / 'evaluation-split-v1.json'
        self.records = [json.loads(line) for line in
                        self.labels.read_text(encoding='utf-8').splitlines() if line.strip()]

    def test_published_files_are_clean(self):
        problems = []
        published.verify_labels(problems, self.labels)
        known = {row['image_id'] for row in self.records}
        published.verify_split(problems, self.manifest, known)
        self.assertEqual(problems, [])

    def test_every_registry_id_is_present_once(self):
        registry = (ROOT / 'data' / 'registry.csv').read_text(encoding='utf-8').splitlines()
        ids = [line.split(',')[0] for line in registry[1:] if line.strip()]
        published_ids = [row['image_id'] for row in self.records]
        self.assertEqual(len(published_ids), len(set(published_ids)))
        self.assertEqual(sorted(published_ids), sorted(ids))

    def test_coordinates_and_parts_agree(self):
        for row in self.records:
            items = row['items']
            for kind in ('bird', 'head', 'eye'):
                self.assertEqual(row['parts'][kind],
                                 sum(1 for item in items if item['kind'] == kind),
                                 row['image_id'])
            for item in items:
                if item['kind'] == 'eye':
                    # An eye always carries the locatable centre; an eye box is
                    # only present when the boundary is actually visible.
                    has_point = item.get('point_xy') is not None
                    has_box = item.get('box_xyxy') is not None
                    self.assertTrue(has_point or has_box, row['image_id'])

    def test_unconfirmed_rows_are_never_negatives(self):
        for row in self.records:
            if row['review_status'] in ('draft', 'needs_adjudication'):
                self.assertFalse(row['confirmed'], row['image_id'])
        self.assertEqual(len([row for row in self.records
                              if row['review_status'] == 'needs_adjudication']), 1)
        confirmed_absent = [row['image_id'] for row in self.records
                            if row['review_status'] == 'confirmed' and row['presence'] == 'absent']
        self.assertEqual(len(confirmed_absent), 2)

    def test_split_groups_never_cross(self):
        manifest = json.loads(self.manifest.read_text(encoding='utf-8'))
        groups = {}
        for row in manifest['images']:
            groups.setdefault(row['leakage_group_id'], set()).add(row['split'])
        self.assertTrue(all(len(splits) == 1 for splits in groups.values()))
        self.assertEqual(manifest['counts'], {'train': 375, 'val': 80, 'test': 80})

    def test_checker_rejects_leaked_path_and_bad_box(self):
        with tempfile.TemporaryDirectory() as temp:
            labels = Path(temp) / 'labels.jsonl'
            bad = dict(self.records[0])
            bad['annotation_image'] = dict(bad['annotation_image'])
            bad['reference_path'] = 'E:\\private\\image.jpg'
            bad['items'] = [{'id': 'x', 'kind': 'bird', 'box_xyxy': [10, 10, 5, 20]}]
            labels.write_text(json.dumps(bad) + '\n', encoding='utf-8')
            problems = []
            published.verify_labels(problems, labels)
            joined = ' '.join(problems)
            self.assertIn('reference_path', joined)
            self.assertIn('not positive-area', joined)


if __name__ == '__main__':
    unittest.main()
