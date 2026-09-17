#!/usr/bin/env python3
"""
Tạo data mẫu tự nhiên (không JSON) để smoke-test pipeline training.
Mục tiêu: input tự nhiên → output tự nhiên, có trích dẫn, kể chuyện mượt.

CHỈ để kiểm tra pipeline chạy được. Data thật sinh bằng
training/bootstrap_deep_qa.py (dữ liệu lấy từ corpus Huế - Đà Nẵng đã crawl);
các mẫu ở đây là ví dụ ngoài miền (Bát Tràng, Đường Lâm) nên đừng train thật
bằng file này.

Chạy: python training/make_smoke_data.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

# Một nguồn duy nhất cho SYSTEM. Bản cũ copy chuỗi này với định dạng trích nguồn
# CŨ ([Nguồn: <trích đoạn ngắn>], không có url) - chạy file này sẽ ghi đè data
# thật bằng data sai định dạng mà không có dấu hiệu gì.
from backend.core.prompt import SYSTEM  # noqa: E402

samples = [
    # === Mẫu 1: Kể về nghệ nhân ===
    {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Nguồn: Nghệ nhân Nguyễn Văn A (1912-1985) là người nổi tiếng với nghề làm gốm tại làng Bát Tràng, thường tham gia hội làng đầu xuân hằng năm.\n\nCâu hỏi: Hãy kể về nghệ nhân Nguyễn Văn A"},
            {"role": "assistant", "content": "Nghệ nhân Nguyễn Văn A, sinh năm 1912 và mất năm 1985, là một trong những nghệ nhân làm gốm nổi tiếng của làng Bát Tràng. Vào mỗi dịp đầu xuân, ông thường tham gia hội làng để trình diễn kỹ năng nghề truyền thống, góp phần gìn giữ và phát huy nét đẹp văn hóa của làng gốm cổ. [Nguồn: Nghệ nhân Nguyễn Văn A là người nổi tiếng với nghề làm gốm tại làng Bát Tràng]"},
        ]
    },
    # === Mẫu 2: Hỏi cụ thể ===
    {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Nguồn: Hội thi thổi cơm làng Đường Lâm diễn ra ngày mùng 4 tháng Giêng hằng năm, thu hút hàng nghìn du khách thập phương.\n\nCâu hỏi: Hội thi thổi cơm diễn ra khi nào và ở đâu?"},
            {"role": "assistant", "content": "Theo nguồn, hội thi thổi cơm làng Đường Lâm là một lễ hội truyền thống độc đáo, được tổ chức vào ngày mùng 4 tháng Giêng hằng năm. Sự kiện này thu hút hàng nghìn du khách thập phương về tham dự, tạo nên không khí lễ hội sôi động đầu năm mới. [Nguồn: Hội thi thổi cơm làng Đường Lâm diễn ra ngày mùng 4 tháng Giêng hằng năm]"},
        ]
    },
    # === Mẫu 3: Refusal (ngoài nguồn) ===
    {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Nguồn: (không có)\n\nCâu hỏi: Lễ hội Đền Hùng có nguồn gốc từ thời nào?"},
            {"role": "assistant", "content": "Không tìm thấy thông tin này trong nguồn được cung cấp. Vui lòng cung cấp thêm tài liệu tham khảo để tôi trả lời chính xác hơn về lễ hội Đền Hùng."},
        ]
    },
    # === Mẫu 4: Giải thích thuật ngữ ===
    {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Nguồn: Nghi lễ tế lễ tại đình làng được cử hành vào dịp xuân về, do các bô lão trong làng chủ trì.\n\nCâu hỏi: Giải thích thuật ngữ \"tế lễ\" trong văn cảnh trên"},
            {"role": "assistant", "content": "Trong văn cảnh trên, \"tế lễ\" chỉ nghi thức cúng tế trang trọng được tổ chức tại đình làng vào dịp đầu xuân. Đây là sinh hoạt văn hóa tâm linh quan trọng, do các bô lão trong làng chủ trì, nhằm tưởng nhớ các vị thành hoàng và cầu mong một năm mới mưa thuận gió hòa, mùa màng bội thu. [Nguồn: Nghi lễ tế lễ tại đình làng được cử hành vào dịp xuân về]"},
        ]
    },
    # === Mẫu 5: Kể về làng nghề ===
    {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Nguồn: Làng tranh Đông Hồ thuộc huyện Thuận Thành, tỉnh Bắc Ninh, nổi tiếng với dòng tranh dân gian từ thế kỷ XVII. Hằng năm vào Tết, dân làng mở hội đua thuyền trên sông Đuống.\n\nCâu hỏi: Hãy kể về làng tranh Đông Hồ"},
            {"role": "assistant", "content": "Làng tranh Đông Hồ tọa lạc tại huyện Thuận Thành, tỉnh Bắc Ninh, là cái nôi của dòng tranh dân gian nổi tiếng từ thế kỷ XVII. Trải qua hàng trăm năm, làng vẫn giữ vững nghề làm tranh truyền thống với những bức tranh đặc sắc phản ánh đời sống văn hóa người Việt. Vào mỗi dịp Tết đến, dân làng lại tổ chức hội đua thuyền trên sông Đuống, tạo nên không khí lễ hội sôi động đầu xuân. [Nguồn: Làng tranh Đông Hồ nổi tiếng với dòng tranh dân gian từ thế kỷ XVII]"},
        ]
    },
    # === Mẫu 6: Hỏi về Huế ===
    {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Nguồn: Nhã nhạc cung đình Huế là loại hình âm nhạc hoàng gia được hình thành từ thời nhà Nguyễn. Năm 2003, UNESCO công nhận đây là Di sản Văn hóa Phi vật thể.\n\nCâu hỏi: Nhã nhạc cung đình Huế có gì đặc biệt?"},
            {"role": "assistant", "content": "Nhã nhạc cung đình Huế là một di sản âm nhạc quý báu của dân tộc, có lịch sử hình thành từ thời nhà Nguyễn. Đây là loại hình nghệ thuật hoàng gia, chuyên được sử dụng trong các nghi lễ cung đình quan trọng. Năm 2003, UNESCO đã vinh danh nhã nhạc cung đình là Di sản Văn hóa Phi vật thể của nhân loại, khẳng định giá trị toàn cầu của loại hình nghệ thuật này. [Nguồn: Nhã nhạc cung đình Huế là loại hình âm nhạc hoàng gia được hình thành từ thời nhà Nguyễn]"},
        ]
    },
    # === Mẫu 7: Hỏi về Đà Nẵng ===
    {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Nguồn: Ngũ Hành Sơn là danh thắng nổi tiếng tại Đà Nẵng, gồm 5 ngọn núi đá vôi tượng trưng cho Kim - Mộc - Thủy - Hỏa - Thổ. Khu danh thắng có nhiều hang động, chùa chiền cổ kính.\n\nCâu hỏi: Kể về Ngũ Hành Sơn"},
            {"role": "assistant", "content": "Ngũ Hành Sơn là một danh thắng nổi tiếng tại thành phố Đà Nẵng, bao gồm năm ngọn núi đá vôi tượng trưng cho năm hành Kim - Mộc - Thủy - Hỏa - Thổ theo triết lý phương Đông. Khu danh thắng này sở hữu nhiều hang động kỳ vĩ và các ngôi chùa cổ kính, là điểm đến hấp dẫn du khách thập phương khi tới miền Trung. [Nguồn: Ngũ Hành Sơn là danh thắng nổi tiếng tại Đà Nẵng, gồm 5 ngọn núi đá vôi]"},
        ]
    },
    # === Mẫu 8: Hỏi thời gian ===
    {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Nguồn: Festival Huế là sự kiện văn hóa nghệ thuật quốc tế diễn ra 2 năm một lần vào tháng 4-6 tại thành phố Huế.\n\nCâu hỏi: Festival Huế diễn ra khi nào?"},
            {"role": "assistant", "content": "Theo nguồn, Festival Huế là sự kiện văn hóa nghệ thuật quốc tế được tổ chức hai năm một lần, thường diễn ra vào khoảng tháng 4 đến tháng 6 tại thành phố Huế. Đây là dịp để tôn vinh di sản văn hóa cung đình và quảng bá nghệ thuật truyền thống Việt Nam. [Nguồn: Festival Huế là sự kiện văn hóa nghệ thuật quốc tế diễn ra 2 năm một lần vào tháng 4-6]"},
        ]
    },
    # === Mẫu 9: Hỏi ý nghĩa ===
    {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Nguồn: Lễ hội Cầu Ngư là lễ hội truyền thống của ngư dân miền Trung, thể hiện lòng tôn kính với các vị thần biển và cầu mong mùa biển bội thu.\n\nCâu hỏi: Ý nghĩa của lễ hội Cầu Ngư là gì?"},
            {"role": "assistant", "content": "Lễ hội Cầu Ngư mang ý nghĩa tâm linh sâu sắc đối với ngư dân miền Trung. Đây là dịp để bà con thể hiện lòng tôn kính đối với các vị thần biển, đồng thời cầu mong mùa biển bội thu, sóng yên biển lặng, cuộc sống ấm no. Lễ hội cũng là nét văn hóa đặc sắc gắn liền với nghề biển truyền thống. [Nguồn: Lễ hội Cầu Ngư thể hiện lòng tôn kính với các vị thần biển và cầu mong mùa biển bội thu]"},
        ]
    },
    # === Mẫu 10: Refusal kiểu khác ===
    {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Nguồn: Bài chòi là trò chơi dân gian phổ biến ở miền Trung.\n\nCâu hỏi: Bài chòi có ở Hà Nội không?"},
            {"role": "assistant", "content": "Nguồn cung cấp chỉ đề cập Bài chòi là trò chơi dân gian phổ biến ở miền Trung mà không nói rõ về sự phổ biến ở các vùng miền khác. Để trả lời chính xác, vui lòng cung cấp thêm tài liệu về Bài chòi tại Hà Nội."},
        ]
    },
]

# Ghi vào data/smoke/, KHÔNG ghi vào data/. Bản cũ ghi thẳng data/train.jsonl và
# data/valid.jsonl, tức là chạy file smoke-test một lần là xoá sạch 235 mẫu thật
# do bootstrap_deep_qa.py sinh ra.
SMOKE = DATA / "smoke"
SMOKE.mkdir(parents=True, exist_ok=True)
train_path = SMOKE / "train.jsonl"
valid_path = SMOKE / "valid.jsonl"

with train_path.open("w", encoding="utf-8") as f:
    for s in samples:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")

# Valid: 3 mẫu đầu
with valid_path.open("w", encoding="utf-8") as f:
    for i in range(3):
        f.write(json.dumps(samples[i], ensure_ascii=False) + "\n")

print(f"wrote {len(samples)} train, 3 valid → {SMOKE}")
print("Train thử bằng data này: trỏ train_file/valid_file trong một config YAML riêng.")
print("\nĐặc điểm data:")
print("  - Tất cả output là văn xuôi tự nhiên, KHÔNG có JSON")
print("  - Mỗi mẫu có [Nguồn: ...] ở cuối")
print("  - Có mẫu refusal (2/10)")
print("  - Văn phong trang trọng, kể chuyện")
