"""Selected tour highlights may cite only reviewed, current OpenSearch passages."""
import hashlib
import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.backend.api import admin_highlights
from apps.backend.api.public.chat.schemas import ChatRequest, TourReplyContext
from apps.backend.core.security import create_access_token
from apps.backend.models.interactive_highlight_passage import InteractiveHighlightPassage
from apps.backend.services.tour_chat import answer_in_area
from apps.backend.services.tour_guide import resolve_tour_context


AREA = "lang-tu-duc"
TEXT = "Bia Khiêm Cung Ký ghi chép về Khiêm Lăng."
HASH = hashlib.sha256(TEXT.encode()).hexdigest()
LINK = {"content_hash": HASH, "object_key": "raw/bia.pdf", "bucket": "knowledge"}


class SelectedBadgeTests(unittest.IsolatedAsyncioTestCase):
    def request(self, highlight_id=61, message="Bia này do ai soạn?"):
        return ChatRequest(message=message, active_area_id=AREA, heritage_id=7,
                           tour_context={"scene_id": 31, "mode": "walk", "highlight_id": highlight_id})

    def snapshot(self, highlight_id=61, links=None):
        return TourReplyContext(scene_id=31, scene_key="s3", scene_title="Cảnh bia",
                                mode="walk", highlight_id=highlight_id, highlight_title="Bia Khiêm Cung Ký",
                                passage_links=links or {})

    async def test_unlinked_badge_never_searches_the_area_even_without_a_pronoun(self):
        repo = SimpleNamespace(search_evidence=AsyncMock())
        generate = Mock()
        result = await answer_in_area(self.request(message="Ai soạn văn bia?"), repo, generate,
                                      lambda: SimpleNamespace(truncated=False), reply_context=self.snapshot())
        self.assertEqual(result["answer_type"], "insufficient_evidence")
        self.assertEqual(result["sources"], [])
        repo.search_evidence.assert_not_awaited()
        generate.assert_not_called()

    async def test_unlinked_badge_never_generates_even_for_a_greeting(self):
        repo = SimpleNamespace(search_evidence=AsyncMock())
        generate = Mock()
        result = await answer_in_area(self.request(message="Xin chào"), repo, generate,
                                      lambda: SimpleNamespace(truncated=False), reply_context=self.snapshot())
        self.assertEqual(result["answer_type"], "insufficient_evidence")
        repo.search_evidence.assert_not_awaited()
        generate.assert_not_called()

    async def test_linked_but_over_budget_passage_never_reaches_the_model(self):
        oversized = SimpleNamespace(id="linked", text="x" * 4800, active_area_id=AREA)
        repo = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(
            evidence=[oversized], graph_context=[])))
        generate = Mock()
        result = await answer_in_area(self.request(), repo, generate,
                                      lambda: SimpleNamespace(truncated=False),
                                      reply_context=self.snapshot(links={"linked": LINK}))
        self.assertEqual(result["answer_type"], "insufficient_evidence")
        self.assertEqual(result["sources"], [])
        generate.assert_not_called()

    async def test_selected_badge_only_cites_its_passage_not_a_same_named_neighbour(self):
        evidence = [SimpleNamespace(id=identity, text=TEXT, active_area_id=AREA,
                                    to_source=lambda identity=identity: {"passage_id": identity, "active_area_id": AREA})
                    for identity in ("linked", "other")]
        repo = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(
            evidence=evidence, graph_context=[{"source_passage_ids": ["other"], "title": "forbidden"}])))
        generate = Mock(return_value=json.dumps({"answer_type": "answered", "answer": TEXT, "source_ids": ["linked"]}))
        result = await answer_in_area(self.request(), repo, generate,
                                      lambda: SimpleNamespace(truncated=False),
                                      reply_context=self.snapshot(links={"linked": LINK}))
        self.assertEqual([source["passage_id"] for source in result["sources"]], ["linked"])
        self.assertNotIn("other", generate.call_args.kwargs["context"])
        self.assertNotIn("forbidden", generate.call_args.kwargs["context"])
        self.assertEqual(repo.search_evidence.call_args.kwargs["passage_links"], {"linked": LINK})


class PassageFilterTests(unittest.IsolatedAsyncioTestCase):
    async def test_repository_rejects_stale_provenance_and_wrong_area(self):
        from apps.backend.services import passages

        valid = {"id": "linked", "text": TEXT, "active_area_id": AREA, **LINK}
        altered = (
            {**valid, "text": "Passage reimported with different text"},
            {**valid, "content_hash": "0" * 64},
            {**valid, "object_key": "raw/other.pdf"},
            {**valid, "bucket": "different"},
            {**valid, "active_area_id": "lang-minh-mang"},
            {**valid, "id": "other"},
        )
        for row in altered:
            with self.subTest(row=row):
                store = SimpleNamespace(search=AsyncMock(return_value=[row]))
                repo = passages.PassageRepository(store, embedder=lambda _: [[1.0]])
                with patch.object(passages, "graphrag_enabled", return_value=False):
                    result = await repo.search_evidence("Bia Khiêm Cung Ký", active_area_id=AREA,
                                                        passage_links={"linked": LINK})
                self.assertEqual(result.evidence, [])
                self.assertEqual(store.search.call_args.kwargs["passage_ids"], ["linked"])

    async def test_hybrid_filters_ids_in_both_branches_and_rechecks_returned_hits(self):
        for name in ("apps.backend.core.search", "apps.backend.common.search.opensearch"):
            with self.subTest(name=name):
                from importlib import import_module
                requests = []

                def respond(request):
                    requests.append(json.loads(request.content))
                    return httpx.Response(200, json={"hits": {"hits": [
                        {"_id": identity, "_score": 1, "_source": {
                            "text": TEXT, "embedding": [1.0], "active_area_id": AREA,
                            "content_hash": HASH, "object_key": "raw/bia.pdf", "bucket": "knowledge"}}
                        for identity in ("linked", "other")
                    ]}})

                async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                    store = import_module(name).PassageStore(client=client)
                    rows = await store.search("Bia Khiêm Cung Ký", [1.0], active_area_id=AREA,
                                              passage_ids=["linked"])
                self.assertEqual([row["id"] for row in rows], ["linked"])
                branches = requests[0]["query"]["hybrid"]["queries"]
                ids_filter = {"ids": {"values": ["linked"]}}
                self.assertIn(ids_filter, branches[0]["bool"]["filter"])
                self.assertIn(ids_filter, branches[1]["function_score"]["query"]["knn"]["embedding"]["filter"]["bool"]["filter"])

    async def test_repository_rejects_stale_hash_and_unlinked_graph_sources(self):
        from apps.backend.services.passages import PassageRepository
        row = {"id": "linked", "text": TEXT, "active_area_id": AREA, **LINK}
        wrong = {**row, "id": "other"}
        stale = {**row, "text": "Altered while retaining the indexed content_hash"}
        store = SimpleNamespace(search=AsyncMock(return_value=[wrong, stale]),
                                get_passages=AsyncMock(return_value=[row, wrong]))
        graph = {"active_area_id": AREA, "sources": [
            {"passage_id": identity, **LINK} for identity in ("linked", "other")],
            "graph_context": [{"title": "valid", "source_passage_ids": ["linked"]},
                              {"title": "invalid", "source_passage_ids": ["other"]}]}
        repo = PassageRepository(store, embedder=lambda _: [[1.0]])
        with patch.dict(os.environ, {"GRAPHRAG_ENABLED": "true"}), \
                patch("apps.backend.services.passages.run_global_query", new_callable=AsyncMock, return_value=graph):
            result = await repo.search_evidence("Bia này ghi gì?", active_area_id=AREA,
                                                passage_links={"linked": LINK})
        self.assertEqual([item.id for item in result.evidence], ["linked"])
        self.assertEqual([item["title"] for item in result.graph_context], ["valid"])
        store.search.assert_awaited_once()
        self.assertEqual(store.search.call_args.kwargs["passage_ids"], ["linked"])
        store.get_passages.assert_awaited_once()
        self.assertEqual(store.get_passages.call_args.args[0], ["linked"])


class LinkResolutionTests(unittest.TestCase):
    def test_highlight_identity_owns_links_even_with_duplicate_popup_titles(self):
        meta = MetaData()
        heritage = Table("heritage", meta, Column("id", Integer, primary_key=True),
                         Column("slug", Text), Column("publish_state", Text))
        scene = Table("scene", meta, Column("id", Integer, primary_key=True),
                      Column("heritage_id", Integer), Column("sequence", Integer), Column("title", Text))
        interactive = Table("interactive", meta, Column("id", Integer, primary_key=True),
                            Column("scene_id", Integer), Column("mode", Text))
        highlight = Table("interactive_highlight", meta, Column("id", Integer, primary_key=True),
                          Column("interactive_id", Integer), Column("popup_title", Text))
        links = Table("interactive_highlight_passage", meta,
                      Column("highlight_id", Integer, primary_key=True),
                      Column("passage_id", String, primary_key=True),
                      Column("content_hash", String), Column("object_key", String), Column("bucket", String))
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        meta.create_all(engine)
        with engine.begin() as connection:
            connection.execute(heritage.insert(), [{"id": 7, "slug": AREA, "publish_state": "published"}])
            connection.execute(scene.insert(), [{"id": 31, "heritage_id": 7, "sequence": 2, "title": "Cảnh bia"},
                                                {"id": 32, "heritage_id": 7, "sequence": 3, "title": "Cảnh khác"}])
            connection.execute(interactive.insert(), [{"id": 51, "scene_id": 31, "mode": "free_explore"},
                                                      {"id": 52, "scene_id": 32, "mode": "standard"}])
            connection.execute(highlight.insert(), [{"id": 61, "interactive_id": 51, "popup_title": "Trùng tên"},
                                                    {"id": 62, "interactive_id": 51, "popup_title": "Trùng tên"},
                                                    {"id": 63, "interactive_id": 52, "popup_title": "Trùng tên"}])
            connection.execute(links.insert(), [{"highlight_id": 61, "passage_id": "linked", **LINK},
                                                {"highlight_id": 62, "passage_id": "other", **LINK},
                                                {"highlight_id": 63, "passage_id": "foreign", **LINK}])
        with Session(engine) as session:
            db = SimpleNamespace(execute=AsyncMock(side_effect=lambda stmt: session.execute(stmt)))
            request = ChatRequest(message="Ai soạn?", active_area_id=AREA, heritage_id=7,
                                  tour_context={"scene_id": 31, "mode": "walk", "highlight_id": 61})
            snapshot = asyncio.run(resolve_tour_context(request, db))
            self.assertEqual(snapshot.passage_links, {"linked": LINK})
            self.assertNotIn("passage_links", snapshot.model_dump())
            for wrong in (62, 63):
                with self.subTest(wrong=wrong):
                    changed = request.model_copy(update={"tour_context": request.tour_context.model_copy(
                        update={"highlight_id": wrong})})
                    if wrong == 63:
                        with self.assertRaises(ValueError):
                            asyncio.run(resolve_tour_context(changed, db))
                    else:
                        self.assertEqual(asyncio.run(resolve_tour_context(changed, db)).passage_links,
                                         {"other": LINK})


class AdminLinkTests(unittest.TestCase):
    def test_auth_area_hash_and_unlink(self):
        class Database:
            def __init__(self):
                self.links = {}

            async def execute(self, stmt):
                return SimpleNamespace(scalar_one_or_none=lambda: AREA)

            async def get(self, model, key):
                if model is InteractiveHighlightPassage:
                    return self.links.get(key)
                return SimpleNamespace(id=key)

            async def scalars(self, stmt):
                return SimpleNamespace(all=lambda: list(self.links.values()))

            def add(self, link):
                self.links[(link.highlight_id, link.passage_id)] = link

            async def delete(self, link):
                del self.links[(link.highlight_id, link.passage_id)]

            async def commit(self):
                pass

        db = Database()
        store = AsyncMock()
        store.__aenter__.return_value = store
        store.get_passages.return_value = [{"id": "PSG-a", "text": TEXT, "active_area_id": AREA, **LINK}]
        app = FastAPI()
        app.include_router(admin_highlights.router, prefix="/api")
        app.dependency_overrides[admin_highlights.get_db] = lambda: db
        base = "/api/admin/interactive-highlights/61/passages"
        headers = {"Authorization": f"Bearer {create_access_token({'sub': '1', 'role': 'admin'})}"}
        user = {"Authorization": f"Bearer {create_access_token({'sub': '2', 'role': 'user'})}"}
        with patch.object(admin_highlights, "PassageStore", return_value=store), TestClient(app) as client:
            for method in ("get", "post", "delete"):
                kwargs = {"json": {"passage_id": "PSG-a"}} if method == "post" else (
                    {"params": {"passage_id": "PSG-a"}} if method == "delete" else {})
                self.assertEqual(getattr(client, method)(base, headers=user, **kwargs).status_code, 403)
            self.assertEqual(client.get(base).status_code, 401)
            store.get_passages.return_value = [{"id": "PSG-a", "text": TEXT, "active_area_id": "lang-minh-mang", **LINK}]
            self.assertEqual(client.post(base, headers=headers, json={"passage_id": "PSG-a"}).status_code, 422)
            store.get_passages.return_value = [{"id": "PSG-a", "text": "Modified", "active_area_id": AREA, **LINK}]
            self.assertEqual(client.post(base, headers=headers, json={"passage_id": "PSG-a"}).status_code, 422)
            store.get_passages.return_value = [{"id": "PSG-a", "text": TEXT, "active_area_id": AREA, **LINK}]
            created = client.post(base, headers=headers, json={"passage_id": "PSG-a"})
            self.assertEqual(created.status_code, 201, created.text)
            self.assertEqual(created.json()["content_hash"], HASH)
            self.assertEqual([item["passage_id"] for item in client.get(base, headers=headers).json()], ["PSG-a"])
            db.rollback = AsyncMock()
            db.commit = AsyncMock(side_effect=IntegrityError("duplicate", {}, Exception("duplicate")))
            duplicate = client.post(base, headers=headers, json={"passage_id": "PSG-a"})
            self.assertEqual(duplicate.status_code, 409)
            db.rollback.assert_awaited_once()
            db.commit = AsyncMock()
            self.assertEqual(client.delete(base, headers=headers, params={"passage_id": "PSG-a"}).status_code, 204)
            self.assertEqual(client.get(base, headers=headers).json(), [])
        store.get_passages.assert_awaited()
        self.assertEqual(store.get_passages.call_args.kwargs["active_area_id"], AREA)


class P2RouteTests(unittest.TestCase):
    def setUp(self):
        from apps.backend.tests.test_chat_conversation import ChatConversationTests
        ChatConversationTests.setUp(self)

    def test_transient_and_persisted_chat_use_the_same_highlight_allowlist(self):
        from apps.backend.api import chat

        selected = TourReplyContext(scene_id=100, scene_key="s3", scene_title="Cảnh Thiên Mụ",
                                    mode="walk", highlight_id=61, highlight_title="Tháp Phước Duyên",
                                    passage_links={"42": LINK})
        self.evidence.text = "Chùa Thiên Mụ có tháp Phước Duyên."
        other = SimpleNamespace(id="91", text="Thông tin của badge trùng tên khác.",
                                active_area_id="chua-thien-mu",
                                to_source=lambda: {"passage_id": "91", "active_area_id": "chua-thien-mu"})
        self.retrieval.evidence.append(other)
        self.retrieval.graph_context = [{"title": "forbidden", "source_passage_ids": ["91"]}]
        payload = {"message": "Tháp này có gì?", "heritage_id": 10, "active_area_id": "chua-thien-mu",
                   "tour_context": {"scene_id": 100, "mode": "walk", "highlight_id": 61}}
        with patch.object(chat, "validated_tour_context", AsyncMock(return_value=selected)):
            for path in ("/api/chat", "/api/chat/message"):
                with self.subTest(path=path):
                    response = self.client.post(path, json=payload)
                    self.assertEqual(response.status_code, 201 if path.endswith("message") else 200,
                                     response.text)
                    self.assertEqual([item["passage_id"] for item in response.json()["sources"]], ["42"])
                    self.assertNotIn("passage_links", response.json()["reply_context"])
                    self.assertNotIn("91", self.generate.call_args.kwargs["context"])
                    self.assertNotIn("forbidden", self.generate.call_args.kwargs["context"])
                    self.assertEqual(self.repository.search_evidence.call_args.kwargs["passage_links"],
                                     {"42": LINK})

            self.repository.search_evidence.reset_mock()
            self.generate.reset_mock()
            with patch.object(chat, "validated_tour_context", AsyncMock(return_value=selected.model_copy(
                update={"passage_links": {}}))):
                for path in ("/api/chat", "/api/chat/message"):
                    response = self.client.post(path, json={**payload, "message": "Ai soạn văn bia?"})
                    self.assertEqual(response.status_code, 201 if path.endswith("message") else 200,
                                     response.text)
                    self.assertEqual(response.json()["answer_type"], "insufficient_evidence")
                self.repository.search_evidence.assert_not_awaited()
                self.generate.assert_not_called()
