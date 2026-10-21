import unittest
from unittest.mock import patch

import numpy as np

from apps.backend.core.embedding import embed_texts


class FakeModel:
    max_seq_length = 8192

    def tokenizer(self, texts, **kwargs):
        return {"length": [len(t) for t in texts]}

    def encode(self, texts, **kwargs):
        return np.array([[1.0, 0.0] + [0.0] * 1022 if 'Bún' in t
                         else [0.0, 1.0] + [0.0] * 1022 for t in texts])


class EmbeddingTests(unittest.TestCase):
    def test_vietnamese_accent_views_share_one_normalized_vector(self):
        with patch('apps.backend.core.embedding._model', return_value=FakeModel()):
            vectors = embed_texts(['Bún bò Huế', 'bun bo hue'])
        self.assertAlmostEqual(vectors[0][0], 1 / 2 ** 0.5)
        self.assertAlmostEqual(vectors[0][1], 1 / 2 ** 0.5)
        self.assertEqual(vectors[1][:2], [0.0, 1.0])
        self.assertEqual(len(vectors[0]), 1024)
        self.assertAlmostEqual(sum(v * v for v in vectors[0]), 1.0)

    def test_oversize_input_is_rejected_instead_of_silently_truncated(self):
        with patch('apps.backend.core.embedding._model', return_value=FakeModel()):
            with self.assertRaises(ValueError):
                embed_texts(['x' * 8193])
