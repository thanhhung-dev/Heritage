import os
import unittest

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from apps.backend.db.import_structured import (
    PackageValidationError,
    import_package,
)
from apps.backend.models.kg import Document, Entity, EntityAlias, Passage
from apps.backend.services.kg import KgRepository
from apps.backend.tests.test_structured_import import valid_package


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "TEST_DATABASE_URL is required")
class DatabaseRetrievalIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_import_is_atomic_idempotent_and_retrievable(self) -> None:
        engine = create_async_engine(TEST_DATABASE_URL)
        connection = await engine.connect()
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            package = valid_package()
            first = await import_package(session, package)
            second = await import_package(session, package)
            self.assertEqual(first, second)

            for model, expected in (
                (Document, 1),
                (Passage, 1),
                (Entity, 1),
                (EntityAlias, 1),
            ):
                count = await session.scalar(select(func.count()).select_from(model))
                self.assertEqual(count, expected)

            repository = KgRepository(session)
            for query in (
                "Cung An Định",
                "cung an dinh",
                "Cung An Dinh o dau",
                "Cung An Định có gì đặc biệt?",
                "An Dinh Palace",
            ):
                evidence = await repository.search_evidence(query, corpus_version=2)
                self.assertEqual(len(evidence), 1, query)
                self.assertEqual(evidence[0].content, package["passages"][0]["text"])
                self.assertEqual(evidence[0].source_url, package["documents"][0]["source_url"])

            evidence = await repository.search_evidence(
                "tọa lạc bên bờ sông An Cựu", corpus_version=2
            )
            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0].content, package["passages"][0]["text"])

            self.assertEqual(
                await repository.search_evidence("Cung An Định", corpus_version=99),
                [],
            )

            before = await session.scalar(select(func.count()).select_from(Document))
            invalid = valid_package()
            invalid["passages"][0]["char_end"] -= 1
            with self.assertRaises(PackageValidationError):
                await import_package(session, invalid)
            after = await session.scalar(select(func.count()).select_from(Document))
            self.assertEqual(after, before)

            await session.execute(update(Document).values(withdrawn_at=func.now()))
            self.assertEqual(
                await repository.search_evidence("Cung An Định", corpus_version=2),
                [],
            )
        finally:
            await session.close()
            await transaction.rollback()
            await connection.close()
            await engine.dispose()


if __name__ == "__main__":
    unittest.main()
