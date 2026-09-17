import hashlib
import tempfile
import unittest
from pathlib import Path

from training.score_gold import adapter_identity, file_identity


class ReproducibilityMetadataTests(unittest.TestCase):
    def test_file_identity_hashes_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.bin"
            path.write_bytes(b"abc")

            self.assertEqual(
                file_identity(path),
                {
                    "sha256": hashlib.sha256(b"abc").hexdigest(),
                    "bytes": 3,
                },
            )

    def test_adapter_identity_uses_served_checkpoint_and_weights(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            adapter = Path(directory)
            (adapter / "CHECKPOINT").write_text("checkpoint-200\n", "utf-8")
            (adapter / "adapter_model.safetensors").write_bytes(b"served")

            identity = adapter_identity(adapter, None)

            self.assertEqual(identity["checkpoint"], "checkpoint-200")
            self.assertEqual(
                identity["weights"]["sha256"],
                hashlib.sha256(b"served").hexdigest(),
            )

    def test_explicit_checkpoint_selects_matching_weights(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            adapter = Path(directory)
            checkpoint = adapter / "checkpoint-300"
            checkpoint.mkdir()
            (checkpoint / "adapter_model.safetensors").write_bytes(b"checkpoint")

            identity = adapter_identity(adapter, "300")

            self.assertEqual(identity["checkpoint"], "checkpoint-300")
            self.assertEqual(
                identity["weights"]["sha256"],
                hashlib.sha256(b"checkpoint").hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
