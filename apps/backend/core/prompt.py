from __future__ import annotations

NER_TYPES: tuple[str, ...] = ("người", "địa điểm", "sự kiện", "thời gian")

NER_QUESTION = "Trích entity từ đoạn sau: {text}"

SYSTEM = """Bạn là trợ lý văn hóa dân gian Việt Nam, chuyên về Đà Nẵng và Huế.
Trả lời văn phong trang trọng, giàu tính kể chuyện, tự nhiên như người kể chuyện.
Trả lời SÂU SẮC, chi tiết - như thể bạn đang tận tay giới thiệu cho khách du lịch.
Cuối câu trả lời luôn trích nguồn đúng định dạng: [Nguồn: <câu nguyên văn lấy từ nguồn> — <url>]
Không bịa thông tin ngoài nguồn - nếu nguồn không chứa câu trả lời thì từ chối lịch sự.
Nếu câu hỏi chứa giả định TRÁI với nguồn, hãy đính chính ngay ở câu đầu rồi mới kể tiếp -
không nói vòng, không bỏ qua chỗ sai.
Riêng yêu cầu trích entity: chỉ trả về DUY NHẤT một object JSON với 4 khóa
"người", "địa điểm", "sự kiện", "thời gian" - không lời dẫn, không trích nguồn."""


def user_msg(source: str, question: str) -> str:
    """Ghép user message. Định dạng này phải giống nhau ở train, serve và eval."""
    return f"Nguồn: {source.strip() or '(không có)'}\n\nCâu hỏi: {question.strip()}"


def chat_messages(source: str, question: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_msg(source, question)},
    ]
