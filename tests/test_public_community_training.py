import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'training'))
from prepare_public_community import build


class PublicCommunityTrainingTests(unittest.TestCase):
    def test_test_labels_and_pixels_remain_quarantined(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs = Path(directory)
            payload = b'fixture bytes for hash validation'
            (inputs / 'train.png').write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            def entry(ident, split):
                return dict(image_id=ident, split=split, png_sha256=digest,
                            input_sha256='chw', preprocess_id='frozen', leakage_group_id=ident)
            labels = {'train': dict(annotation_image={'png_sha256': digest}, confirmed=True,
                                    review_status='confirmed', presence='present',
                                    items=[dict(id='e', kind='eye', point_xy=[10., 20.])]),
                      'test': dict(annotation_image={'png_sha256': digest})}
            split = dict(images=[entry('train', 'train'), entry('test', 'test')], counts={'train': 1, 'test': 1})
            registry = [dict(image_id=ident, original_sha256='source') for ident in labels]
            result = build(labels, split, registry, inputs)
            self.assertEqual(result['images'][0]['document']['items'], labels['train']['items'])
            self.assertIsNone(result['images'][1]['document'])
            self.assertFalse((inputs / 'test.png').exists())


if __name__ == '__main__':
    unittest.main()
