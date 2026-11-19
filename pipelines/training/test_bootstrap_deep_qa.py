from __future__ import annotations

import json
import random
import unittest

from pipelines.training.bootstrap_deep_qa import (
    attach_passage_ids,
    generate_for_doc,
    load_package_docs,
    make_false_premise_samples,
    make_no_source_samples,
    make_wrong_doc_samples,
)


def _doc() -> dict:
    return {
        "name": "Chùa Thiên Mụ",
        "category": "Di tích lịch sử",
        "url": "https://example.test/thien-mu",
        "chunks": [
            {
                "heading": "Tổng quan",
                "text": (
                    "Chùa Thiên Mụ nằm trên đồi Hà Khê, tả ngạn sông Hương, "
                    "cách trung tâm thành phố Huế khoảng 5 km. "
                    "Chùa khởi lập năm 1601 đời chúa Nguyễn Hoàng. "
                    "Tháp Phước Duyên được xây thêm năm 1844."
                ),
            },
            {
                "heading": "Kiến trúc",
                "text": (
                    "Tháp Phước Duyên là ngôi tháp bát giác bảy tầng, "
                    "nét kiến trúc người ta nhớ nhất của chùa."
                ),
            },
        ],
    }


class BootstrapConversationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.docs = [_doc()]
        attach_passage_ids(self.docs)
        self.rng = random.Random(0)

    def test_qa_samples_use_conversation_json(self) -> None:
        rows, _skipped = generate_for_doc(self.docs[0], self.rng, teacher=None, stats={})
        self.assertGreater(len(rows), 0)
        row = rows[0]
        self.assertEqual(row["messages"][0]["content"], CONVERSATION_SYSTEM)
        user = row["messages"][1]["content"]
        self.assertIn("[Passage https://example.test/thien-mu]", user)
        payload = json.loads(row["messages"][2]["content"])
        self.assertIn("answer", payload)
        self.assertEqual(payload["source_ids"], ["https://example.test/thien-mu"])
        self.assertNotIn("[Nguồn:", payload["answer"])
        self.assertGreaterEqual(len(payload["follow_up_questions"]), 2)

    def test_refusal_has_empty_source_ids(self) -> None:
        row = make_no_source_samples(self.rng, ["Chợ Bến Thành ở quận nào?"])[0]
        payload = json.loads(row["messages"][2]["content"])
        self.assertEqual(payload["source_ids"], [])
        self.assertNotIn("[Nguồn:", payload["answer"])

    def test_wrong_doc_does_not_cite_foreign_passage(self) -> None:
        other = {
            "name": "Cơm hến",
            "category": "Ẩm thực",
            "url": "https://example.test/com-hen",
            "chunks": [{"heading": "Món", "text": "Cơm hến là đặc sản ẩm thực Huế với hến xào."}],
        }
        docs = [self.docs[0], other]
        attach_passage_ids(docs)
        rows = make_wrong_doc_samples(self.rng, docs, per_doc=1)
        self.assertTrue(rows)
        payload = json.loads(rows[0]["messages"][2]["content"])
        self.assertEqual(payload["source_ids"], [])

    def test_false_premise_cites_true_passage(self) -> None:
        rows = make_false_premise_samples(self.rng, self.docs, per_doc=1)
        self.assertTrue(rows)
        payload = json.loads(rows[0]["messages"][2]["content"])
        self.assertTrue(payload["source_ids"])
        self.assertIn("không", payload["answer"].lower())

    def test_package_loader_uses_document_source_url(self) -> None:
        import tempfile
        from pathlib import Path

        payload = {
            "documents": [{
                "key": "DOC-1",
                "title": "Overview",
                "object_key": "tour-context/vi/lang-tu-duc/overview.md",
                "source_url": "https://example.test/tu-duc",
                "region": "hue",
            }],
            "passages": [{
                "key": "PSG-1",
                "document_key": "DOC-1",
                "text": "Lăng Tự Đức nằm ở Huế. " * 10,
            }],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "package.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            docs, skipped = load_package_docs(path)
        self.assertEqual(skipped, [])
        self.assertEqual(docs[0]["name"], "Lăng Tự Đức")
        self.assertEqual(docs[0]["url"], "https://example.test/tu-duc")


if __name__ == "__main__":
    unittest.main()
