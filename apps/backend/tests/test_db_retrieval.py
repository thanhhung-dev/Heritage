import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from apps.backend.services.kg import KgRepository


class DatabaseRetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_passage_backed_citation_fields(self) -> None:
        passage_id = uuid.uuid4()
        entity_id = uuid.uuid4()
        row = SimpleNamespace(
            passage_id=passage_id, entity_id=entity_id,
            content="Cung An Định được xây dựng đầu thế kỷ XX.",
            title="Trung tâm Bảo tồn Di tích Cố đô Huế",
            source_url="https://example.org/an-dinh", tier=1,
            observed_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
            score=0.8, entity_boost=0.2,
        )
        database = AsyncMock()
        database.execute.return_value = [row]

        evidence = await KgRepository(database).search_evidence("cung an dinh")

        self.assertEqual(evidence[0].evidence_id, str(passage_id))
        self.assertEqual(evidence[0].entity_id, str(entity_id))
        self.assertEqual(evidence[0].source_title, row.title)
        self.assertEqual(evidence[0].source_url, row.source_url)
        self.assertEqual(evidence[0].content, row.content)

    async def test_empty_query_does_not_access_database(self) -> None:
        database = AsyncMock()
        self.assertEqual(await KgRepository(database).search_evidence("  "), [])
        database.execute.assert_not_called()

    async def test_query_contract_excludes_withdrawn_sources_and_normalizes_accents(self) -> None:
        database = AsyncMock()
        database.execute.return_value = []

        self.assertEqual(await KgRepository(database).search_evidence("Cung An Định"), [])

        statement, parameters = database.execute.call_args.args
        self.assertIn("d.withdrawn_at IS NULL", str(statement))
        self.assertIn("cr.status = 'published'", str(statement))
        self.assertEqual(parameters["normalized"], "cung an dinh")


if __name__ == "__main__":
    unittest.main()
