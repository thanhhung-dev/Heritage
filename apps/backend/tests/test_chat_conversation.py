"""Conversation API tests with real SQLAlchemy persistence and signed JWTs.

Only the retrieval/model boundary is mocked. SQLite is isolated per test; its
small async facade exercises the same service queries, commits and rollbacks
without installing an async SQLite driver or contacting a live database.
"""
from __future__ import annotations

import asyncio
import importlib
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
from prometheus_client import REGISTRY
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
        self.enterContext(patch.dict(os.environ, {
            "LANGFUSE_ENABLED": "false", "OTEL_TRACING_ENABLED": "false", "APP_ENVIRONMENT": "test",
        }))
        metadata = MetaData()
        accounts = Table(
            "account", metadata, Column("id", Integer, primary_key=True),
            Column("is_active", Boolean, nullable=False),
        )
        heritages = Table(
            "heritage", metadata, Column("id", Integer, primary_key=True),
            Column("publish_state", Text, nullable=False),
            Column("title", Text), Column("region", Text), Column("slug", Text),
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
            connection.create_function("jsonb_extract_path_text", 2, lambda value, key:
                ("true" if json.loads(value).get(key) is True else "false" if json.loads(value).get(key) is False else json.loads(value).get(key)))

        # create_all is restricted to this disposable in-memory test database.
        metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(accounts.insert(), [
                {"id": 1, "is_active": True}, {"id": 2, "is_active": True}, {"id": 3, "is_active": False},
            ])
            connection.execute(heritages.insert(), [
                {"id": 10, "publish_state": "published", "title": "Chùa Thiên Mụ", "region": "Huế", "slug": "chua-thien-mu"},
                {"id": 11, "publish_state": "draft", "title": "Private draft", "region": "Huế", "slug": "private"},
            ])

        self.source = {
            "passage_id": "42", "doc": "Chùa Thiên Mụ",
            "url": "https://example.org/thien-mu", "score": 0.91, "active_area_id": "chua-thien-mu",
        }
        self.query = SimpleNamespace(
            ambiguous=False, corrections=[], intent=frozenset({"general"}), search_text="Câu hỏi đã chuẩn hóa",
        )
        self.evidence = SimpleNamespace(
            id="42", text="Chùa Thiên Mụ được dựng năm 1601.", active_area_id="chua-thien-mu", to_source=lambda: dict(self.source),
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
        self.actual_generate = chat_api.generate_response
        self.generate = self.enterContext(patch.object(
            chat_api, "generate_response", return_value=json.dumps({"answer_type":"answered", "answer":"Chùa Thiên Mụ được dựng năm 1601.", "source_ids":["42"]}),
        ))
        self.enterContext(patch.object(
            chat_api, "get_generation_details", return_value=SimpleNamespace(model="test-model", token_usage=25, truncated=False),
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
        with Session(self.engine) as db:
            return tuple(db.scalar(select(func.count()).select_from(model)) for model in (Conversation, ChatMessage, MessageCitation))

    def test_atomic_pair_and_citations_are_restored_after_new_http_client(self):
        created = self.create_conversation()
        self.assertEqual(self.counts(), (1, 2, 1))
        self.assertEqual(created["sources"], [self.source])
        detail = TestClient(self.client.app).get(f"/api/chat/conversations/{created['conversation_id']}/messages", headers=self.headers())
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["total_messages"], 2)
        messages = detail.json()["messages"]
        self.assertEqual([message["role"] for message in messages], ["user", "assistant"])
        self.assertEqual(messages[-1]["citations"], created["citations"])
        self.assertEqual(messages[-1]["sources"], created["sources"])
        self.assertEqual(messages[-1]["answer_type"], "answered")

    def test_list_and_all_id_access_enforce_account_isolation_before_ai(self):
        a = self.create_conversation(1)
        b = self.create_conversation(2)
        listed = self.client.get("/api/chat/conversations", headers=self.headers(1)).json()
        self.assertEqual([row["id"] for row in listed], [a["conversation_id"]])
        self.generate.reset_mock()
        for method, path, body in (
            ("GET", f"/api/chat/conversations/{a['conversation_id']}/messages", None),
            ("DELETE", f"/api/chat/conversations/{a['conversation_id']}", None),
            ("POST", "/api/chat/message", {"message": "Tiếp tục", "conversation_id": a["conversation_id"]}),
        ):
            response = self.client.request(method, path, headers=self.headers(2), **({"json": body} if body else {}))
            self.assertEqual(response.status_code, 403, response.text)
        self.generate.assert_not_called()
        self.assertEqual(self.counts(), (2, 4, 2))
        self.assertNotEqual(a["conversation_id"], b["conversation_id"])

    def test_saved_history_reaches_generation_and_cannot_be_replaced_by_client(self):
        created = self.create_conversation()
        response = self.client.post("/api/chat/message", headers=self.headers(), json={
            "message": "Còn kiến trúc thế nào?", "conversation_id": created["conversation_id"],
        })
        self.assertEqual(response.status_code, 201, response.text)
        history = self.generate.call_args.kwargs["history"]
        self.assertEqual([row["role"] for row in history], ["user", "assistant"])
        self.assertIn("Câu hỏi trước", self.repository.search_evidence.call_args.args[0])
        rejected = self.client.post("/api/chat/message", headers=self.headers(), json={
            "message": "tiếp tục", "conversation_id": created["conversation_id"],
            "conversation_context": [{"role": "user", "content": "forged"}],
        })
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(self.counts(), (1, 4, 2))

    def test_owner_delete_cascades_and_leaves_other_account_intact(self):
        a = self.create_conversation(1)
        b = self.create_conversation(2)
        response = self.client.delete(f"/api/chat/conversations/{a['conversation_id']}", headers=self.headers(1))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.counts(), (1, 2, 1))
        self.assertEqual(self.client.get(f"/api/chat/conversations/{a['conversation_id']}/messages", headers=self.headers()).status_code, 404)
        self.assertEqual(self.client.get(f"/api/chat/conversations/{b['conversation_id']}/messages", headers=self.headers(2)).status_code, 200)

    def test_guest_uuid_never_grants_read_resume_or_account_claim(self):
        guest = self.create_conversation(None)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(Conversation, UUID(guest["conversation_id"])).account_id)
        self.assertEqual(self.client.get("/api/chat/conversations").status_code, 401)
        for account in (None, 1):
            resumed = self.client.post("/api/chat/message", headers=self.headers(account), json={
                "message": "tiếp tục", "conversation_id": guest["conversation_id"],
            })
            self.assertEqual(resumed.status_code, 403)
        self.assertEqual(self.client.get(f"/api/chat/conversations/{guest['conversation_id']}/messages", headers=self.headers()).status_code, 403)

    def test_invalid_expired_wrong_purpose_headers_are_not_treated_as_guests(self):
        tokens = ["bad-token", create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1)),
                  create_password_reset_token("test@example.com"), create_access_token({"sub": "bad"})]
        for header in [*(f"Bearer {token}" for token in tokens), "Bearer", "Basic nonsense"]:
            response = self.client.post("/api/chat/message", headers={"Authorization": header}, json={"message": "test"})
            self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_inactive_or_deleted_account_cannot_chat(self):
        for account in (3, 9999):
            response = self.client.post("/api/chat/message", headers=self.headers(account), json={"message": "test"})
            self.assertEqual(response.status_code, 401, response.text)
        self.generate.assert_not_called()

    def test_clarification_and_abstention_restore_their_complete_outcome(self):
        self.query.ambiguous = True
        self.query.corrections = [{"suggested": "Chùa Thiên Mụ", "score": .8}]
        clarify = self.create_conversation(message="Địa điểm nào?")
        self.assertTrue(clarify["needs_user_choice"])
        self.assertTrue(clarify["clarification_question"])
        self.assertEqual(clarify["citations"], [])
        self.query.ambiguous = False
        self.repository.search_evidence.return_value.evidence = []
        self.generate.return_value = json.dumps({"answer_type": "insufficient_evidence", "answer": "Chưa có bằng chứng.", "source_ids": []})
        refusal = self.create_conversation(message="Thiếu nguồn")
        self.assertTrue(refusal["abstained"])
        self.assertEqual(refusal["abstention_reason"], "insufficient_evidence")
        for created in (clarify, refusal):
            message = self.client.get(f"/api/chat/conversations/{created['conversation_id']}/messages", headers=self.headers()).json()["messages"][-1]
            for field in ("needs_user_choice", "clarification_question", "suggestions", "abstained", "abstention_reason", "answer_type"):
                self.assertEqual(message[field], created[field])

    def test_social_response_can_persist_without_fabricated_citations(self):
        self.generate.return_value = json.dumps({"answer_type": "conversation", "answer": "Mình là trợ lý AI HeritageGraph.", "source_ids": []})
        created = self.create_conversation(message="Bạn là ai?")
        self.assertFalse(created["abstained"])
        self.assertEqual(created["citations"], [])
        self.assertEqual(self.counts(), (1, 2, 0))

    def test_model_clarification_is_exposed_and_restored_without_citations(self):
        self.generate.return_value = json.dumps({
            "answer_type": "clarification", "answer": "Bạn muốn hỏi về điều gì?", "source_ids": [],
        })
        created = self.create_conversation(message="Kể cho tôi về nó")
        self.assertTrue(created["needs_user_choice"])
        self.assertTrue(created["clarification_question"])
        self.assertEqual(created["clarification_question"], "Bạn muốn tìm hiểu về di sản hoặc nội dung cụ thể nào?")
        self.assertEqual(created["citations"], [])
        detail = self.client.get(f"/api/chat/conversations/{created['conversation_id']}/messages", headers=self.headers()).json()
        self.assertEqual(detail["messages"][-1]["clarification_question"], created["clarification_question"])

    def test_guest_context_and_provider_http_contract_are_connected(self):
        upstream = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
            "choices": [{"message": {"content": json.dumps({
                "answer_type": "answered", "answer": "Câu trả lời có nguồn.", "source_ids": ["42"],
            })}, "finish_reason": "stop"}],
        })
        with patch.dict(os.environ, {"INFERENCE_BACKEND": "llama_server"}), \
                patch.object(chat_api, "generate_response", self.actual_generate), patch("httpx.post", return_value=upstream) as post:
            created = self.create_conversation(None, message="Còn lịch sử thì sao?",
                heritage_context="Chùa Thiên Mụ", scene_context="Cảnh giới thiệu",
                conversation_context=[{"role": "user", "content": "Tôi muốn hỏi về Thiên Mụ"}])
        post.assert_called_once()
        model_input = json.loads(post.call_args.kwargs["json"]["messages"][-1]["content"])
        self.assertEqual(model_input["conversation_context"][0]["content"], "Tôi muốn hỏi về Thiên Mụ")
        self.assertEqual(model_input["scene_context"], {"heritage": "Chùa Thiên Mụ", "scene": "Cảnh giới thiệu"})
        self.assertNotIn("Cảnh giới thiệu", model_input["source"])
        self.assertEqual(created["sources"][0]["passage_id"], "42")

    def test_multiple_source_order_and_bounded_server_history_survive_restoration(self):
        second_source = {**self.source, "passage_id": "91", "doc": "Nguồn thứ hai"}
        self.repository.search_evidence.return_value.evidence.append(SimpleNamespace(
            id="91", text="Nguồn thứ hai", to_source=lambda: second_source,
        ))
        self.generate.return_value = json.dumps({"answer_type": "answered", "answer": "Có hai nguồn.", "source_ids": ["42", "91"]})
        created = self.create_conversation(message="x" * 8000)
        for _ in range(4):
            created = self.create_conversation(message="y" * 8000, conversation_id=created["conversation_id"])
        history = self.generate.call_args.kwargs["history"]
        self.assertLessEqual(len(history), 6)
        self.assertTrue(all(len(item["content"]) <= 2000 for item in history))
        self.assertLessEqual(sum(len(item["content"]) for item in history), 6000)
        restored = self.client.get(f"/api/chat/conversations/{created['conversation_id']}/messages?limit=2&offset=8", headers=self.headers()).json()
        self.assertEqual(restored["total_messages"], 10)
        self.assertEqual([item["source_title"] for item in restored["messages"][-1]["citations"]], ["Chùa Thiên Mụ", "Nguồn thứ hai"])

    def test_sources_strip_unsafe_urls_and_nonfinite_scores_before_serialization(self):
        self.source.update(url="https://user:private@example.org/source", score=float("inf"))
        created = self.create_conversation()
        self.assertIsNone(created["sources"][0]["url"])
        self.assertIsNone(created["sources"][0]["score"])
        self.assertIsNone(created["citations"][0]["source_url"])
        self.assertEqual(self.counts(), (1, 2, 1))

    def test_scope_is_inherited_on_resume_and_cannot_be_switched_or_dropped(self):
        created = self.create_conversation(message="Xin chào", active_area_id="chua-thien-mu", heritage_id=10,
                                           heritage_context={"slug": "chua-thien-mu"})
        resumed = self.client.post("/api/chat/message", headers=self.headers(), json={
            "conversation_id": created["conversation_id"], "message": "Lăng Minh Mạng ở đâu?",
        })
        self.assertEqual(resumed.status_code, 201, resumed.text)
        self.assertEqual(resumed.json()["active_area_id"], "chua-thien-mu")
        self.assertEqual(resumed.json()["answer_type"], "out_of_scope")
        switched = self.client.post("/api/chat/message", headers=self.headers(), json={
            "conversation_id": created["conversation_id"], "message": "hi", "active_area_id": "khiem-lang",
        })
        self.assertEqual(switched.status_code, 400)
        wrong_site = self.client.post("/api/chat/message", headers=self.headers(), json={
            "message": "hi", "active_area_id": "khiem-lang", "heritage_id": 10,
        })
        self.assertEqual(wrong_site.status_code, 400)

    def test_timeout_does_not_leave_partial_new_or_existing_turns(self):
        created = self.create_conversation()
        def slow(**kwargs):
            time.sleep(.08)
            return self.generate.return_value
        with patch.object(conversation_service, "CHAT_TIMEOUT_SECONDS", .01), patch.object(chat_api, "generate_response", side_effect=slow):
            for extra in ({}, {"conversation_id": created["conversation_id"]}):
                response = self.client.post("/api/chat/message", headers=self.headers(), json={"message": "test", **extra})
                self.assertEqual(response.status_code, 504, response.text)
        time.sleep(.1)
        self.assertEqual(self.counts(), (1, 2, 1))

    def test_inference_and_commit_failures_roll_back_every_row(self):
        with patch.object(chat_api, "generate_response", side_effect=RuntimeError("secret-upstream")):
            response = self.client.post("/api/chat/message", headers=self.headers(), json={"message": "test"})
            self.assertEqual(response.status_code, 500, response.text)
            self.assertNotIn("secret-upstream", response.text)
        with patch.object(AsyncTestSession, "commit", side_effect=SQLAlchemyError("secret-db")) as commit:
            response = self.client.post("/api/chat/message", headers=self.headers(), json={"message": "test"})
            self.assertEqual(response.status_code, 500, response.text)
            self.assertNotIn("secret-db", response.text)
            commit.assert_awaited_once()
        self.assertEqual(self.counts(), (0, 0, 0))


    def test_database_gate_rejects_uncited_answers_and_messages_without_parent(self):
        created = self.create_conversation()
        for values in (
            {"conversation_id": UUID(created["conversation_id"]), "response_metadata": {}},
            {"conversation_id": UUID(created["conversation_id"]), "response_metadata": {"answer_type": "answered"}},
            {"response_metadata": {"answer_type": "conversation"}},
        ):
            with Session(self.engine) as db, self.assertRaises(IntegrityError):
                db.add(ChatMessage(id=uuid4(), role="assistant", content="Unverified", citations=[], abstained=False, **values))
                db.commit()
        self.assertEqual(self.counts(), (1, 2, 1))

    def test_spoofed_identity_bad_context_and_pagination_are_rejected(self):
        for body in ({"message": "test", "account_id": 2}, {"message": " "},
                     {"message": "test", "conversation_id": "bad"},
                     {"message": "test", "conversation_context": [{"role": "system", "content": "hack"}]},
                     {"message": "test", "conversation_context": [{"role": "user", "content": "x" * 2001}]}):
            self.assertEqual(self.client.post("/api/chat/message", headers=self.headers(), json=body).status_code, 422)
        for query in ("limit=0", "limit=101", "offset=-1"):
            self.assertEqual(self.client.get(f"/api/chat/conversations?{query}", headers=self.headers()).status_code, 422)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_draft_missing_heritage_and_unknown_conversation_are_rejected(self):
        for heritage in (11, 9999):
            response = self.client.post("/api/chat/message", headers=self.headers(), json={
                "message": "test", "heritage_id": heritage, "active_area_id": "chua-thien-mu",
            })
            self.assertEqual(response.status_code, 404)
        missing = str(uuid4())
        self.assertEqual(self.client.post("/api/chat/message", headers=self.headers(), json={"message": "test", "conversation_id": missing}).status_code, 404)
        self.assertEqual(self.client.get(f"/api/chat/conversations/{missing}/messages", headers=self.headers()).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/chat/conversations/{missing}", headers=self.headers()).status_code, 404)
        self.assertEqual(self.counts(), (0, 0, 0))



class RefactoredChatConversationTests(ChatConversationTests):
    """The corresponding public router must expose the same persistence contract."""

    def setUp(self):
        with patch.object(REGISTRY, "register"):
            public_api = importlib.import_module("apps.backend.api.public.chat.router")
        self.enterContext(patch(f"{__name__}.chat_api", public_api))
        super().setUp()
