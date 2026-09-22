import tempfile
import unittest
from pathlib import Path

from pipelines.training.score_gold import adapter_identity, file_identity


class ScoreGoldMetadataTests(unittest.TestCase):
    def test_file_identity_records_content_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.jsonl"
            path.write_text("sample\n", encoding="utf-8")

            identity = file_identity(path)

        self.assertEqual(
            identity["sha256"],
            "aaf9ff488e0767da5ea1d56118e6f65a16c5633b0cefc1fa089bd3ab1810613d",
        )
        self.assertEqual(identity["bytes"], 7)

    def test_adapter_identity_reads_serving_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = Path(directory)
            (adapter / "CHECKPOINT").write_text("0000200\n", encoding="utf-8")
            (adapter / "adapters.safetensors").write_bytes(b"adapter weights")

            identity = adapter_identity(adapter, explicit_checkpoint=None)

        self.assertEqual(identity["checkpoint"], "0000200")
        self.assertEqual(identity["weights"]["bytes"], 15)
        self.assertIn("sha256", identity["weights"])


if __name__ == "__main__":
    unittest.main()
