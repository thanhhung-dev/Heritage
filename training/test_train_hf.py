from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from training.train_hf import find_last_checkpoint, load_config, tokenize_conversation


class FakeTokenizer:
    def apply_chat_template(
        self,
        messages,
        *,
        tokenize,
        add_generation_prompt,
        return_dict,
        truncation,
        max_length,
        **kwargs,
    ):
        call = {
            "tokenize": tokenize,
            "add_generation_prompt": add_generation_prompt,
            "return_dict": return_dict,
            "truncation": truncation,
            "max_length": max_length,
            **kwargs,
        }
        self.calls = getattr(self, "calls", []) + [call]
        length = len(messages) * 2 + int(add_generation_prompt)
        input_ids = list(range(1, length + 1))[:max_length]
        return {
            "input_ids": input_ids,
            "attention_mask": [1] * len(input_ids),
        }


class TrainHfTest(unittest.TestCase):
    def test_tokenize_conversation_masks_non_assistant_tokens(self):
        tokenizer = FakeTokenizer()
        messages = [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "question"},
            {"role": "assistant", "content": "answer"},
        ]

        encoded = tokenize_conversation(tokenizer, messages, max_seq_length=32)

        self.assertEqual(encoded["input_ids"], [1, 2, 3, 4, 5, 6])
        self.assertEqual(encoded["labels"], [-100, -100, -100, -100, -100, 6])
        self.assertTrue(
            all(call["enable_thinking"] is False for call in tokenizer.calls)
        )

    def test_tokenize_conversation_rejects_sample_without_trainable_tokens(self):
        tokenizer = FakeTokenizer()

        with self.assertRaisesRegex(ValueError, "assistant"):
            tokenize_conversation(
                tokenizer,
                [{"role": "user", "content": "question only"}],
                max_seq_length=32,
            )

    def test_find_last_checkpoint_uses_numeric_step_order(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "checkpoint-9").mkdir()
            (output / "checkpoint-100").mkdir()
            (output / "checkpoint-invalid").mkdir()

            self.assertEqual(find_last_checkpoint(output), output / "checkpoint-100")

    def test_load_config_resolves_project_relative_paths(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            config_path = Path(directory) / "config.yaml"
            config_path.write_text(
                "model_id: Qwen/Qwen2.5-3B-Instruct\n"
                "train_file: data/train.jsonl\n"
                "valid_file: data/valid.jsonl\n"
                "output_dir: models/peft-adapter\n",
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config["model_id"], "Qwen/Qwen2.5-3B-Instruct")
        self.assertEqual(config["train_file"], Path.cwd() / "data/train.jsonl")
        self.assertEqual(config["output_dir"], Path.cwd() / "models/peft-adapter")

    def test_default_workflow_is_lora_without_four_bit_quantization(self):
        config = load_config(Path("training/lora_config.yaml"))
        requirements = Path("training/requirements.txt").read_text(encoding="utf-8")

        self.assertNotIn("quant_type", config)
        self.assertNotIn("double_quant", config)
        self.assertEqual(config["optimizer"], "adamw_torch")
        self.assertNotIn("bitsandbytes", requirements.lower())


if __name__ == "__main__":
    unittest.main()
