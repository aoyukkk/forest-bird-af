import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/training'))
import evaluate_guidance_predictions as replay
from bird_guidance_metrics import assess_guidance


class GuidanceReplayTests(unittest.TestCase):
    def test_reference_mismatch_cannot_silently_change_denominator(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            row = dict(image_id='a', split='community_val', group='g', eyes=[], objects=[],
                       absent=True, eye_complete=False, uncertain=[])
            reference = assess_guidance([dict(row, image_id='b')], {'b': []})
            for name, value in [('dataset', dict(records=[row])), ('predictions', {'a': []}), ('reference', reference)]:
                (root / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
            argv = ['replay', '--dataset', str(root / 'dataset.json'), '--predictions', str(root / 'predictions.json'),
                    '--reference', str(root / 'reference.json'), '--output', str(root / 'out.json')]
            with patch.object(sys, 'argv', argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    replay.main()
            self.assertEqual(error.exception.code, 2)
            self.assertFalse((root / 'out.json').exists())

    def test_cached_replay_needs_no_model_and_retains_unknowns(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            row = dict(image_id='a', split='community_val', group='g', eyes=[],
                       objects=[dict(kind='bird', box=[0, 0, 20, 20])],
                       absent=False, eye_complete=False, uncertain=[])
            pred = {'a': [dict(kind='eye', point_xy=[10, 10], box_xyxy=None, score=.9)]}
            reference = assess_guidance([row], pred)
            for name, value in [('dataset', dict(records=[row])), ('predictions', pred), ('reference', reference)]:
                (root / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
            argv = ['replay', '--dataset', str(root / 'dataset.json'), '--predictions', str(root / 'predictions.json'),
                    '--reference', str(root / 'reference.json'), '--output', str(root / 'out.json')]
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
                replay.main()
            result = json.loads((root / 'out.json').read_text(encoding='utf-8'))
            self.assertEqual(result['selected']['counts']['eye_unassessed_selected'], 1)
            self.assertEqual(result['selected']['counts']['eye_4px'], 0)
            self.assertFalse(result['test_used'])
