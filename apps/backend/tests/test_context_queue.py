"""Context worker prepares the same bound the request path already enforces."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import uuid4

from apps.backend.services.context_store import history_if_fresh, reset_client, snapshot_document
from apps.backend.workers.context import refresh


class Result:
    def __init__(self, scalar=None, rows=()):
        self._scalar = scalar
        self._rows = rows

    def scalar_one_or_none(self):
        return self._scalar

    def all(self):
        return list(self._rows)


class Session:
    def __init__(self, exists, rows=()):
        self.exists = exists
        self.rows = rows
        self.calls = 0

    async def execute(self, _statement):
        self.calls += 1
        if self.calls == 1:
            return Result(scalar=self.exists)
        return Result(rows=self.rows)


class Store:
    def __init__(self):
        self.saved = None
        self.deleted = []

    async def save(self, conversation_id, newest_id, history):
        self.saved = (conversation_id, newest_id, [(item.role, item.content) for item in history])

    async def delete(self, conversation_id):
        self.deleted.append(conversation_id)


class ContextSnapshotTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        reset_client()

    def test_stale_or_corrupt_snapshot_is_not_history(self):
        latest = uuid4()
        fresh = {"through_message_id": str(latest), "history": [{"role": "user", "content": "Bia bằng gì?"}]}
        self.assertEqual(history_if_fresh(fresh, latest)[0].content, "Bia bằng gì?")
        self.assertIsNone(history_if_fresh(fresh, uuid4()))
        self.assertIsNone(history_if_fresh({"through_message_id": str(latest), "history": [{"role": "system", "content": "x"}]}, latest))
        self.assertIsNone(history_if_fresh({"through_message_id": str(latest), "history": "nope"}, latest))
        self.assertIsNone(history_if_fresh(None, latest))

    def test_snapshot_document_records_the_newest_message(self):
        conversation_id, message_id = uuid4(), uuid4()
        text = snapshot_document(conversation_id, message_id, history_if_fresh(
            {"through_message_id": str(message_id), "history": [{"role": "user", "content": "Khiêm Lăng"}]},
            message_id,
        ))
        self.assertIn(str(message_id), text)
        self.assertNotIn("system", text)

    async def test_refresh_stores_bounded_history_and_drops_missing_conversations(self):
        conversation_id = uuid4()
        newest, older = uuid4(), uuid4()
        rows = [
            SimpleNamespace(id=newest, role="assistant", content="Không phải bằng chứng."),
            SimpleNamespace(id=older, role="user", content="  Hỏi về bia  "),
        ]
        store = Store()
        await refresh(Session(conversation_id, rows), store, conversation_id)
        self.assertEqual(store.saved[0], conversation_id)
        self.assertEqual(store.saved[1], newest)
        self.assertEqual(store.saved[2], [("user", "Hỏi về bia"), ("assistant", "Không phải bằng chứng.")])
        self.assertEqual(store.deleted, [])

        missing = Store()
        await refresh(Session(None), missing, conversation_id)
        self.assertEqual(missing.deleted, [conversation_id])
        self.assertIsNone(missing.saved)

        empty = Store()
        await refresh(Session(conversation_id, ()), empty, conversation_id)
        self.assertEqual(empty.deleted, [conversation_id])


if __name__ == "__main__":
    unittest.main()
