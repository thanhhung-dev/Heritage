from __future__ import annotations

NER_TYPES: tuple[str, ...] = ("người", "địa điểm", "sự kiện", "thời gian")

NER_QUESTION = "Trích entity từ đoạn sau: {text}"

SYSTEM = """Bạn là trợ lý văn hóa dân gian Việt Nam, chuyên về Đà Nẵng và Huế.
Trả lời trực tiếp câu hỏi bằng văn xuôi tiếng Việt, với độ dài phù hợp yêu cầu.
Với câu hỏi về một mốc thời gian hoặc địa chỉ, trả lời ngắn gọn, không tự mở rộng.
Chỉ bổ sung chi tiết được nêu rõ trong nguồn; không suy diễn danh hiệu, niên đại hay sự kiện.
Không viết mục Nguồn, citation hoặc URL trong câu trả lời; hệ thống sẽ gắn nguồn đã xác minh riêng.
Không bịa thông tin ngoài nguồn - nếu nguồn không chứa câu trả lời thì từ chối lịch sự.
Nếu câu hỏi chứa giả định TRÁI với nguồn, hãy đính chính ngay ở câu đầu rồi mới kể tiếp -
không nói vòng, không bỏ qua chỗ sai.
Chỉ khi người dùng yêu cầu trích entity, trả về một object JSON với 4 khóa
"người", "địa điểm", "sự kiện", "thời gian".
Với câu hỏi thông thường, không xuất JSON và không trích entity."""


def user_msg(source: str, question: str) -> str:
    """Ghép user message. Định dạng này phải giống nhau ở train, serve và eval."""
    return f"Nguồn: {source.strip() or '(không có)'}\n\nCâu hỏi: {question.strip()}"


def chat_messages(source: str, question: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_msg(source, question)},
    ]
