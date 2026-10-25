"""Conversation API tests with real SQLAlchemy persistence and signed JWTs.

Only the retrieval/model boundary is mocked. SQLite is isolated per test; its
small async facade exercises the same service queries, commits and rollbacks
without installing an async SQLite driver or contacting a live database.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Boolean, Column, Integer, MetaData, Table, Text, create_engine, event, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from apps.backend.api import chat as chat_api
from apps.backend.core.security import create_access_token, create_password_reset_token
from apps.backend.models.chat import ChatFeedback, ChatMessage, ChatSession, Conversation, MessageCitation
from apps.backend.services import conversations as conversation_service


class AsyncTestSession:
    """AsyncSession-compatible facade over an actual, transactional test database."""

    def __init__(self, engine):
        self.session = Session(engine, expire_on_commit=False)

    def add(self, entity):
        self.session.add(entity)

    def add_all(self, entities):
        self.session.add_all(entities)

    async def execute(self, statement):
        return self.session.execute(statement)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

    async def delete(self, entity):
        self.session.delete(entity)


class ChatConversationTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"LANGFUSE_ENABLED": "false", "OTEL_TRACING_ENABLED": "false"}))
        metadata = MetaData()
        accounts = Table(
            "account", metadata, Column("id", Integer, primary_key=True),
            Column("is_active", Boolean, nullable=False),
        )
        heritages = Table(
            "heritage", metadata, Column("id", Integer, primary_key=True),
            Column("publish_state", Text, nullable=False),
        )
        for model in (Conversation, ChatSession, ChatMessage, MessageCitation, ChatFeedback):
            table = model.__table__.to_metadata(metadata)
            for column in table.columns:
                # Production UUID defaults are PostgreSQL-specific. All inserted
                # test/service rows explicitly supply UUIDs; constraints stay intact.
                if column.server_default is not None and "gen_random_uuid" in str(column.server_default.arg):
                    column.server_default = None
        self.engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False},
        )
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def configure_sqlite(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.create_function("jsonb_array_length", 1, lambda value: len(json.loads(value)))

        # create_all is restricted to this disposable in-memory test database.
        metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(accounts.insert(), [
                {"id": 1, "is_active": True}, {"id": 2, "is_active": True}, {"id": 3, "is_active": False},
            ])
            connection.execute(heritages.insert(), [
                {"id": 10, "publish_state": "published"}, {"id": 11, "publish_state": "draft"},
            ])

        self.source = {
            "passage_id": "42", "doc": "Chùa Thiên Mụ",
            "url": "https://example.org/thien-mu", "score": 0.91,
        }
        self.query = SimpleNamespace(
            ambiguous=False, corrections=[], intent=frozenset({"general"}), search_text="Câu hỏi đã chuẩn hóa",
        )
        self.evidence = SimpleNamespace(
            id="42", text="Chùa Thiên Mụ được dựng năm 1601.", to_source=lambda: dict(self.source),
        )
        self.retrieval = SimpleNamespace(query=self.query, evidence=[self.evidence], graph_context=[])
        self.repository = SimpleNamespace(search_evidence=AsyncMock(return_value=self.retrieval))
        self.repository_requests = 0

        async def get_db():
            database = AsyncTestSession(self.engine)
            try:
                yield database
            finally:
                database.session.close()

        async def get_repository():
            self.repository_requests += 1
            yield self.repository

        app = FastAPI()
        app.include_router(chat_api.router, prefix="/api")
        app.dependency_overrides[chat_api.get_chat_db] = get_db
        app.dependency_overrides[chat_api.get_repository] = get_repository
        self.generate = self.enterContext(patch.object(
            chat_api, "generate_response", return_value="Chùa Thiên Mụ được dựng năm 1601.",
        ))
        self.enterContext(patch.object(
            chat_api, "get_generation_details", return_value=SimpleNamespace(model="test-model", token_usage=25),
        ))
        self.client = self.enterContext(TestClient(app, raise_server_exceptions=False))

    def headers(self, account_id=1):
        if account_id is None:
            return {}
        return {"Authorization": f"Bearer {create_access_token({'sub': str(account_id), 'role': 'user'})}"}

    def create_conversation(self, account_id=1, message="Chùa Thiên Mụ xây năm nào?", **extra):
        response = self.client.post(
            "/api/chat/message", headers=self.headers(account_id), json={"message": message, **extra},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def counts(self):
        with Session(self.engine) as database:
            return tuple(database.scalar(select(func.count()).select_from(model)) for model in (
                Conversation, ChatMessage, MessageCitation,
            ))

    def history(self, conversation_id, account_id=1, **params):
        return self.client.get(
            f"/api/chat/conversations/{conversation_id}/messages", headers=self.headers(account_id), params=params,
        )

    def test_create_message_persists_conversation_both_turns_and_citations(self):
        result = self.create_conversation()
        self.assertEqual(self.counts(), (1, 2, 1))
        self.assertEqual(result["answer_type"], "answered")
        citation = result["citations"][0]
        self.assertEqual(citation["message_id"], result["message_id"])
        self.assertEqual(citation["source_title"], self.source["doc"])
        self.assertEqual(citation["source_url"], self.source["url"])
        self.assertAlmostEqual(citation["relevance_score"], 0.91)
        with Session(self.engine) as database:
            conversation = database.get(Conversation, UUID(result["conversation_id"]))
            self.assertEqual(conversation.account_id, 1)
            assistant = database.get(ChatMessage, UUID(result["message_id"]))
            self.assertEqual(assistant.citations[0]["passage_id"], "42")

    def test_heritage_and_scene_context_qualify_query_without_becoming_source_evidence(self):
        result = self.create_conversation(
            heritage_id=10, heritage_context={"title": "Chùa Thiên Mụ"}, scene_context="Cổng chính",
        )
        question = self.repository.search_evidence.await_args.args[0]
        self.assertIn("Chùa Thiên Mụ", question)
        self.assertIn("Cổng chính", question)
        self.assertEqual(self.generate.call_args.kwargs["context"], self.evidence.text)
        self.assertEqual(self.history(result["conversation_id"]).json()["heritage_id"], 10)

    def test_continuation_keeps_one_conversation_and_orders_turns(self):
        first = self.create_conversation()
        second = self.create_conversation(message="Còn kiến trúc?", conversation_id=first["conversation_id"])
        self.assertEqual(first["conversation_id"], second["conversation_id"])
        self.assertEqual(self.counts(), (1, 4, 2))
        messages = self.history(first["conversation_id"]).json()["messages"]
        self.assertEqual([item["role"] for item in messages], ["user", "assistant", "user", "assistant"])
        self.assertEqual(messages[2]["content"], "Còn kiến trúc?")

    def test_list_contains_only_authenticated_accounts_own_conversations(self):
        owned = self.create_conversation()
        self.create_conversation(account_id=2)
        self.create_conversation(account_id=None)
        self.repository_requests = 0
        response = self.client.get("/api/chat/conversations", headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in response.json()], [owned["conversation_id"]])
        self.assertEqual(self.repository_requests, 0, "History must work without an AI dependency")

    def test_history_returns_ordered_messages_and_normalized_citations(self):
        created = self.create_conversation()
        response = self.history(created["conversation_id"])
        self.assertEqual(response.status_code, 200, response.text)
        messages = response.json()["messages"]
        self.assertEqual([item["role"] for item in messages], ["user", "assistant"])
        self.assertEqual(messages[0]["citations"], [])
        self.assertEqual(messages[1]["citations"], created["citations"])

    def test_user_b_cannot_read_user_a_messages(self):
        created = self.create_conversation()
        response = self.history(created["conversation_id"], account_id=2)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(set(response.json()), {"detail"})

    def test_user_b_cannot_append_to_user_a_conversation(self):
        created = self.create_conversation()
        self.repository.search_evidence.reset_mock()
        response = self.client.post("/api/chat/message", headers=self.headers(2), json={
            "message": "Unauthorized continuation", "conversation_id": created["conversation_id"],
        })
        self.assertEqual(response.status_code, 403)
        self.repository.search_evidence.assert_not_awaited()
        self.assertEqual(self.counts(), (1, 2, 1))

    def test_user_b_cannot_delete_user_a_conversation(self):
        created = self.create_conversation()
        response = self.client.delete(f"/api/chat/conversations/{created['conversation_id']}", headers=self.headers(2))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.counts(), (1, 2, 1))

    def test_owner_delete_returns_empty_204_and_cascades_messages_citations_feedback(self):
        created = self.create_conversation()
        with Session(self.engine) as database:
            database.add(ChatFeedback(
                id=uuid4(), message_id=UUID(created["message_id"]), rating=1,
                created_at=datetime.now(timezone.utc),
            ))
            database.commit()
        response = self.client.delete(f"/api/chat/conversations/{created['conversation_id']}", headers=self.headers())
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.counts(), (0, 0, 0))
        with Session(self.engine) as database:
            self.assertEqual(database.scalar(select(func.count()).select_from(ChatFeedback)), 0)

    def test_guest_can_create_a_conversation_with_null_account(self):
        created = self.create_conversation(account_id=None)
        with Session(self.engine) as database:
            conversation = database.get(Conversation, UUID(created["conversation_id"]))
            self.assertIsNone(conversation.account_id)

    def test_guest_cannot_use_a_conversation_uuid_as_authentication(self):
        created = self.create_conversation(account_id=None)
        response = self.client.post("/api/chat/message", json={
            "message": "Continue without credentials", "conversation_id": created["conversation_id"],
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn(self.history(created["conversation_id"], account_id=None).status_code, (401, 403))

    def test_authenticated_account_cannot_claim_guest_history(self):
        created = self.create_conversation(account_id=None)
        self.assertEqual(self.history(created["conversation_id"]).status_code, 403)
        response = self.client.delete(f"/api/chat/conversations/{created['conversation_id']}", headers=self.headers())
        self.assertEqual(response.status_code, 403)

    def test_management_requires_jwt(self):
        created = self.create_conversation()
        responses = [
            self.client.get("/api/chat/conversations"),
            self.history(created["conversation_id"], account_id=None),
            self.client.delete(f"/api/chat/conversations/{created['conversation_id']}"),
        ]
        for response in responses:
            self.assertIn(response.status_code, (401, 403))

    def test_invalid_expired_wrong_purpose_and_malformed_authorization_are_not_guests(self):
        expired = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        wrong_purpose = create_password_reset_token("1")
        for authorization in ("Bearer invalid", f"Bearer {expired}", f"Bearer {wrong_purpose}", "Basic invalid", "Bearer"):
            with self.subTest(authorization=authorization.split()[0]):
                response = self.client.post(
                    "/api/chat/message", json={"message": "Hello"}, headers={"Authorization": authorization},
                )
                self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_deleted_and_inactive_accounts_are_rejected(self):
        for account_id in (3, 999):
            response = self.client.post("/api/chat/message", json={"message": "Hello"}, headers=self.headers(account_id))
            self.assertEqual(response.status_code, 401)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_missing_conversation_returns_404_on_read_append_and_delete(self):
        conversation_id = str(uuid4())
        responses = [
            self.history(conversation_id),
            self.client.post("/api/chat/message", headers=self.headers(), json={"message": "Hello", "conversation_id": conversation_id}),
            self.client.delete(f"/api/chat/conversations/{conversation_id}", headers=self.headers()),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 404, response.text)
        self.repository.search_evidence.assert_not_awaited()

    def test_timeout_returns_504_and_does_not_leave_partial_conversation(self):
        self.assertEqual(conversation_service.CHAT_TIMEOUT_SECONDS, 30)

        async def slow_search(_):
            await asyncio.sleep(1)

        self.repository.search_evidence.side_effect = slow_search
        with patch.object(conversation_service, "CHAT_TIMEOUT_SECONDS", 0.01):
            response = self.client.post("/api/chat/message", headers=self.headers(), json={"message": "Hello"})
        self.assertEqual(response.status_code, 504, response.text)
        self.assertIn("30", response.json()["detail"])
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_timeout_on_existing_conversation_preserves_previous_turns(self):
        created = self.create_conversation()
        before = self.history(created["conversation_id"]).json()["updated_at"]

        async def slow_search(_):
            await asyncio.sleep(1)

        self.repository.search_evidence.side_effect = slow_search
        with patch.object(conversation_service, "CHAT_TIMEOUT_SECONDS", 0.01):
            response = self.client.post("/api/chat/message", headers=self.headers(), json={
                "message": "Another question", "conversation_id": created["conversation_id"],
            })
        self.assertEqual(response.status_code, 504)
        self.assertEqual(self.counts(), (1, 2, 1))
        self.assertEqual(self.history(created["conversation_id"]).json()["updated_at"], before)

    def test_inference_timeout_cannot_write_a_late_answer(self):
        finished = threading.Event()

        def slow_generation(**_):
            time.sleep(0.05)
            finished.set()
            return "Late answer"

        self.generate.side_effect = slow_generation
        with patch.object(conversation_service, "CHAT_TIMEOUT_SECONDS", 0.01):
            response = self.client.post("/api/chat/message", headers=self.headers(), json={"message": "Hello"})
        self.assertEqual(response.status_code, 504, response.text)
        self.assertTrue(finished.wait(timeout=1), "The mocked inference thread must finish")
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_model_failure_returns_safe_500_and_rolls_back(self):
        self.generate.side_effect = RuntimeError("private inference configuration")
        response = self.client.post("/api/chat/message", headers=self.headers(), json={"message": "Hello"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private inference", response.text)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_retrieval_failure_returns_safe_500_and_rolls_back(self):
        self.repository.search_evidence.side_effect = RuntimeError("private retrieval configuration")
        response = self.client.post("/api/chat/message", headers=self.headers(), json={"message": "Hello"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private retrieval", response.text)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_commit_failure_rolls_back_messages_and_citations_already_flushed(self):
        with patch.object(AsyncTestSession, "commit", new=AsyncMock(side_effect=SQLAlchemyError("private database failure"))):
            response = self.client.post("/api/chat/message", headers=self.headers(), json={"message": "Hello"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private database", response.text)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_no_evidence_persists_a_refusal_without_invented_citations(self):
        self.retrieval.evidence = []
        created = self.create_conversation()
        self.assertEqual(created["citations"], [])
        self.assertEqual(created["answer_type"], "insufficient_evidence")
        self.generate.assert_not_called()
        self.assertEqual(self.counts(), (1, 2, 0))
        with Session(self.engine) as database:
            self.assertTrue(database.get(ChatMessage, UUID(created["message_id"])).abstained)

    def test_invalid_requests_and_account_spoofing_are_rejected_before_ai(self):
        for body in (
            {"message": "  "}, {"message": "x" * 8001},
            {"message": "Hello", "conversation_id": "invalid"},
            {"message": "Hello", "account_id": 2},
            {"message": "Hello", "heritage_context": "x" * 2001},
            {"message": "Hello", "scene_context": {"text": "x" * 2001}},
        ):
            with self.subTest(fields=list(body)):
                response = self.client.post("/api/chat/message", json=body, headers=self.headers())
                self.assertEqual(response.status_code, 422, response.text)
        self.repository.search_evidence.assert_not_awaited()
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_draft_and_unknown_heritage_are_rejected(self):
        for heritage_id in (11, 999):
            response = self.client.post("/api/chat/message", headers=self.headers(), json={"message": "Hello", "heritage_id": heritage_id})
            self.assertEqual(response.status_code, 404)
        self.repository.search_evidence.assert_not_awaited()

    def test_conversation_cannot_switch_heritage(self):
        created = self.create_conversation(heritage_id=10)
        response = self.client.post("/api/chat/message", headers=self.headers(), json={
            "message": "Hello", "heritage_id": 11, "conversation_id": created["conversation_id"],
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.counts(), (1, 2, 1))

    def test_history_and_list_pagination_are_bounded(self):
        self.create_conversation(message="First")
        second = self.create_conversation(message="Second")
        self.create_conversation(message="Third")
        response = self.client.get("/api/chat/conversations?limit=1&offset=1", headers=self.headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [second["conversation_id"]])
        messages = self.history(second["conversation_id"], limit=1, offset=1).json()["messages"]
        self.assertEqual([item["role"] for item in messages], ["assistant"])
        for params in ({"limit": 0}, {"limit": 501}, {"offset": -1}):
            self.assertEqual(self.history(second["conversation_id"], **params).status_code, 422)

    def test_deleting_conversation_does_not_remove_legacy_session_messages(self):
        session_id = uuid4()
        with Session(self.engine) as database:
            database.add(ChatSession(id=session_id, ip_hash="test-anonymized", created_at=datetime.now(timezone.utc)))
            database.flush()
            database.add(ChatMessage(
                id=uuid4(), session_id=session_id, role="user", content="Legacy message",
                citations=[], abstained=False, created_at=datetime.now(timezone.utc),
            ))
            database.commit()
        created = self.create_conversation()
        response = self.client.delete(f"/api/chat/conversations/{created['conversation_id']}", headers=self.headers())
        self.assertEqual(response.status_code, 204)
        with Session(self.engine) as database:
            self.assertEqual(database.scalar(select(func.count()).select_from(ChatSession)), 1)
            self.assertEqual(database.scalar(select(ChatMessage.content)), "Legacy message")

    def test_database_rejects_a_message_without_a_parent(self):
        with Session(self.engine) as database:
            database.add(ChatMessage(
                id=uuid4(), role="user", content="Orphan", citations=[], abstained=False,
                created_at=datetime.now(timezone.utc),
            ))
            with self.assertRaises(IntegrityError):
                database.flush()
            database.rollback()


if __name__ == "__main__":
    unittest.main()
