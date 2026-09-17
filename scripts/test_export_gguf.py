import tempfile
import unittest
from pathlib import Path

from scripts.export_gguf import resolve_adapter_path


class ExportGgufTest(unittest.TestCase):
    def test_resolve_adapter_uses_best_adapter_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = Path(directory)
            (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")

            self.assertEqual(resolve_adapter_path(adapter, None), adapter)

    def test_resolve_adapter_accepts_numeric_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = Path(directory)
            checkpoint = adapter / "checkpoint-75"
            checkpoint.mkdir()
            (checkpoint / "adapter_config.json").write_text("{}", encoding="utf-8")

            self.assertEqual(resolve_adapter_path(adapter, "75"), checkpoint)

    def test_resolve_adapter_rejects_missing_peft_config(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "adapter_config.json"):
                resolve_adapter_path(Path(directory), None)


if __name__ == "__main__":
    unittest.main()
