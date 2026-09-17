import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from backend.api.chat import (
    ChatRequest,
    _intro_question_for_bare_entity,
    _try_db_location_answer,
    chat,
)
from backend.core.corpus import load_docs
from backend.core.fuzzy_match import rank_fuzzy_names


class DatabaseChatTests(unittest.IsolatedAsyncioTestCase):
    def test_every_bare_place_name_becomes_an_explicit_intro_question(self) -> None:
        names = [doc["name"] for doc in load_docs()[0]]

        for name in names:
            with self.subTest(place=name):
                self.assertEqual(
                    _intro_question_for_bare_entity(name, [{"doc": name}]),
                    f"Hãy giới thiệu tổng quan và những nét đặc biệt của {name}.",
                )

    def test_partial_bare_place_name_uses_the_retrieved_canonical_name(self) -> None:
        self.assertEqual(
            _intro_question_for_bare_entity(
                "Núi Ngũ Hành", [{"doc": "Ngũ Hành Sơn"}]
            ),
            "Hãy giới thiệu tổng quan và những nét đặc biệt của Ngũ Hành Sơn.",
        )

    def test_real_question_is_not_rewritten_as_a_bare_place_name(self) -> None:
        question = "Ngũ Hành Sơn có gì đặc biệt?"

        self.assertEqual(
            _intro_question_for_bare_entity(
                question, [{"doc": "Ngũ Hành Sơn"}]
            ),
            question,
        )

    async def test_bare_place_name_reretrieves_and_generates_as_a_question(self) -> None:
        source = {"doc": "Ngũ Hành Sơn"}
        with (
            patch("backend.api.chat._try_db_location_answer", AsyncMock(return_value=None)),
            patch(
                "backend.api.chat.retrieve_context",
                side_effect=[
                    ("context ban đầu", [source], []),
                    ("context tổng quan", [source], []),
                ],
            ) as retrieve_context,
            patch(
                "backend.api.chat.generate_response", return_value="Câu trả lời"
            ) as generate_response,
        ):
            response = await chat(ChatRequest(message="Núi Ngũ Hành"), AsyncMock())

        self.assertEqual(response.answer, "Câu trả lời")
        self.assertEqual(
            retrieve_context.call_args_list[1].args[0],
            "Hãy giới thiệu tổng quan và những nét đặc biệt của Ngũ Hành Sơn.",
        )
        generate_response.assert_called_once_with(
            question=(
                "Hãy giới thiệu tổng quan và những nét đặc biệt của Ngũ Hành Sơn."
            ),
            context="context tổng quan",
        )

    async def test_bare_place_name_keeps_original_context_when_reretrieval_fails(self) -> None:
        source = {"doc": "Lăng Dục Đức"}
        with (
            patch("backend.api.chat._try_db_location_answer", AsyncMock(return_value=None)),
            patch(
                "backend.api.chat.retrieve_context",
                side_effect=[("context ban đầu", [source], []), ("", [], [])],
            ),
            patch(
                "backend.api.chat.generate_response", return_value="Câu trả lời"
            ) as generate_response,
        ):
            response = await chat(ChatRequest(message="Lăng Dục Đức"), AsyncMock())

        self.assertEqual(response.answer, "Câu trả lời")
        generate_response.assert_called_once_with(
            question=(
                "Hãy giới thiệu tổng quan và những nét đặc biệt của Lăng Dục Đức."
            ),
            context="context ban đầu",
        )

    def test_database_names_support_alias_typos_and_omitted_location_type(self) -> None:
        names = [
            "Nhà thờ chính tòa Đà Nẵng",
            "Nhà thờ con gà",
            "Cung An Định",
        ]

        cases = {
            "nhà thờ con dê ở đâu": 1,
            "con gà ở đâu": 1,
            "nhà thờ chính toà ở đâu": 0,
        }
        for query, expected_index in cases.items():
            with self.subTest(query=query):
                ranked = rank_fuzzy_names(query, names)
                self.assertTrue(ranked)
                self.assertEqual(ranked[0][0], expected_index)
                self.assertGreaterEqual(ranked[0][1], 0.72)

    def test_short_shared_name_is_ambiguous_instead_of_auto_selected(self) -> None:
        names = ["Làng Thanh Hà", "Thành Điện Hải", "Cung An Định"]

        ranked = rank_fuzzy_names("thanh ở đâu", names)

        self.assertGreaterEqual(len(ranked), 2)
        self.assertLess(ranked[0][1], 0.72)

    def test_irrelevant_query_has_no_fuzzy_candidate(self) -> None:
        names = ["Cung An Định", "Ngũ Hành Sơn"]

        self.assertEqual(rank_fuzzy_names("thời tiết hôm nay", names), [])

    def test_every_imported_place_supports_common_typing_errors(self) -> None:
        location_categories = {"Danh thắng", "Di tích lịch sử", "Làng nghề"}
        names = [
            doc["name"] for doc in load_docs()[0]
            if doc["category"] in location_categories
        ]

        for index, name in enumerate(names):
            variants = {
                "substitution": name[:-1] + "x",
                "deletion": name[:-1],
                "insertion": name + "x",
                "transposition": name[:-2] + name[-1] + name[-2],
                "missing_spaces": name.replace(" ", ""),
            }
            for error_type, typo in variants.items():
                with self.subTest(place=name, error_type=error_type, typo=typo):
                    ranked = rank_fuzzy_names(f"{typo} ở đâu?", names)
                    self.assertTrue(ranked)
                    self.assertEqual(ranked[0][0], index)
                    self.assertGreaterEqual(ranked[0][1], 0.72)

    async def test_location_without_database_candidate_does_not_reach_llm(self) -> None:
        with patch("backend.api.chat.KgRepository") as repository_type:
            repository_type.return_value.resolve_entities = AsyncMock(return_value=[])

            response = await _try_db_location_answer(
                AsyncMock(), "Một địa danh chưa biết ở đâu?"
            )

        self.assertIsNotNone(response)
        self.assertEqual(response.answer_type, "insufficient_evidence")
        self.assertEqual(response.sources, [])
        self.assertIn("không tìm thấy", response.answer.lower())

    async def test_resolved_entity_without_verified_location_does_not_reach_llm(self) -> None:
        entity = SimpleNamespace(
            id=uuid.uuid4(),
            name="Cung An Định",
            normalized_name="cung an dinh",
            type="place",
        )
        candidate = SimpleNamespace(entity=entity)

        with patch("backend.api.chat.KgRepository") as repository_type:
            repository = repository_type.return_value
            repository.resolve_entities = AsyncMock(return_value=[candidate])
            repository.get_verified_locations = AsyncMock(return_value=[])

            response = await _try_db_location_answer(
                AsyncMock(), "Cung An Định ở đâu?"
            )

        self.assertIsNotNone(response)
        self.assertEqual(response.answer_type, "insufficient_evidence")
        self.assertEqual(response.sources, [])
        self.assertIn("chưa có địa chỉ đã được xác minh", response.answer.lower())

    async def test_conflicting_verified_locations_are_not_chosen_arbitrarily(self) -> None:
        entity = SimpleNamespace(
            id=uuid.uuid4(),
            name="Cung An Định",
            normalized_name="cung an dinh",
            type="place",
        )
        candidate = SimpleNamespace(entity=entity)
        locations = [
            SimpleNamespace(address="97 Phan Đình Phùng"),
            SimpleNamespace(address="179 Phan Đình Phùng"),
        ]

        with patch("backend.api.chat.KgRepository") as repository_type:
            repository = repository_type.return_value
            repository.resolve_entities = AsyncMock(return_value=[candidate])
            repository.get_verified_locations = AsyncMock(return_value=locations)

            response = await _try_db_location_answer(
                AsyncMock(), "Cung An Định ở đâu?"
            )

        self.assertEqual(response.answer_type, "insufficient_evidence")
        self.assertEqual(response.resolution_status, "ambiguous")
        self.assertEqual(response.sources, [])
        self.assertIn("nhiều địa chỉ", response.answer.lower())

    async def test_verified_location_answer_is_natural_and_leaves_source_to_ui(self) -> None:
        entity = SimpleNamespace(id=uuid.uuid4(), name="Ngũ Hành Sơn")
        candidate = SimpleNamespace(entity=entity)
        location = SimpleNamespace(
            address="phường Ngũ Hành Sơn",
            ward=None,
            district="Ngũ Hành Sơn",
            province="Đà Nẵng",
            source_title="Cổng thông tin du lịch Đà Nẵng",
            source_url="https://example.com/ngu-hanh-son",
            source_sentence="Ngũ Hành Sơn nằm tại thành phố Đà Nẵng.",
        )

        with patch("backend.api.chat.KgRepository") as repository_type:
            repository = repository_type.return_value
            repository.resolve_entities = AsyncMock(return_value=[candidate])
            repository.get_verified_locations = AsyncMock(return_value=[location])

            response = await _try_db_location_answer(
                AsyncMock(), "ngũ hành sơn ở đâu"
            )

        self.assertEqual(
            response.answer,
            "Ngũ Hành Sơn nằm tại phường Ngũ Hành Sơn, Đà Nẵng.",
        )
        self.assertNotIn("Tên bạn nhập", response.answer)
        self.assertNotIn("Nguồn:", response.answer)
        self.assertEqual(
            response.sources[0]["doc"], "Cổng thông tin du lịch Đà Nẵng"
        )

    async def test_general_question_without_retrieved_evidence_does_not_reach_llm(self) -> None:
        with (
            patch("backend.api.chat._try_db_location_answer", AsyncMock(return_value=None)),
            patch("backend.api.chat.retrieve_context", return_value=("", [], [])),
            patch("backend.api.chat.generate_response") as generate_response,
        ):
            response = await chat(
                ChatRequest(message="Kể cho tôi một điều chưa có trong corpus"),
                AsyncMock(),
            )

        generate_response.assert_not_called()
        self.assertEqual(response.answer_type, "insufficient_evidence")
        self.assertEqual(response.sources, [])
        self.assertIn("không tìm thấy nguồn", response.answer.lower())


if __name__ == "__main__":
    unittest.main()
