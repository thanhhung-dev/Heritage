import unittest

from pydantic import ValidationError

from apps.backend.schemas.rag_pipeline import PipelineCreate, PipelineUpdate, ReindexRequest


class PipelineSchemaTests(unittest.TestCase):
    def test_defaults_match_real_chunker_and_model(self):
        config = PipelineCreate(name="Heritage")
        self.assertEqual(config.chunking.max_chars, 2400)
        self.assertEqual(config.embedding.dimensions, 1024)
        self.assertIn("BAAI/bge-m3@", config.embedding.model)

    def test_rejects_unsupported_or_invalid_settings(self):
        for fields in ({"chunking": {"max_chars": 31}}, {"chunking": {"max_chars": 100, "overlap_chars": 50}},
                       {"chunking": {"max_chars": "2400"}}, {"embedding": {"model": "other"}},
                       {"embedding": {"dimensions": 512}}, {"retrieval": {"top_k": 0}},
                       {"retrieval": {"min_similarity": float("nan")}}, {"retrieval": {"strategy": "other"}},
                       {"retrieval": {"min_similarity": 1.1}}, {"unknown": True}, {"name": "  "}):
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                PipelineCreate.model_validate({"name": "Heritage", **fields})
        for body in ({"expected_revision": 1}, {"expected_revision": 1, "chunking": None}):
            with self.assertRaises(ValidationError):
                PipelineUpdate.model_validate(body)

    def test_reindex_scope_is_nonempty_unique_uuids(self):
        for ids in ([], ["invalid"], ["00000000-0000-0000-0000-000000000001"] * 2):
            with self.subTest(ids=ids), self.assertRaises(ValidationError):
                ReindexRequest(document_ids=ids)
