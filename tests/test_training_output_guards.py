"""Relocation must not weaken the prohibition on private outputs in Git."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/training'))
import prepare_z8_training
import probe_z8_finetune
import train_z8_heads


class TrainingOutputGuards(unittest.TestCase):
    def test_prepare_rejects_data_folder_under_repository(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            output = Path(temp) / 'private'
            args = SimpleNamespace(output=output, workspace=Path(temp) / 'annotations', upstream=Path(temp) / 'vendor')
            with self.assertRaisesRegex(ValueError, 'outside'):
                prepare_z8_training.freeze(args)
            self.assertFalse(output.exists())

    def check_main(self, module, extra):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            p = Path(temp)
            output = p / 'private'
            argv = ['script', '--upstream', str(p / 'vendor'), '--workspace', str(p / 'annotations'),
                    '--z8-package', str(p / 'package'), '--output', str(output)] + extra
            with patch.object(sys, 'argv', argv), patch.object(module.torch.cuda, 'is_available', return_value=True), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    module.main()
            self.assertEqual(error.exception.code, 2)
            self.assertFalse(output.exists())

    def test_training_rejects_output_in_repository(self):
        self.check_main(train_z8_heads, ['--dataset', str(ROOT)])

    def test_probe_rejects_output_in_repository(self):
        self.check_main(probe_z8_finetune, ['--frozen-runs', str(ROOT), '--ids', 'fb_0001'])


if __name__ == '__main__':
    unittest.main()
