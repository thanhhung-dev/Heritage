"""
Danh sách địa điểm văn hóa Huế - Đà Nẵng.
Mỗi địa điểm sẽ được crawl từ Wikipedia và sinh training data.

TÊN Ở ĐÂY PHẢI LÀ TÊN BÀI vi.wikipedia CÓ THẬT.
pipelines/ingestion/crawl_by_location.py gọi wiki.page(name) đúng tên, không tìm kiếm,
không đoán. Cố ý như vậy: đã kiểm thử tìm kiếm theo tên mô tả và nó trả về bài
sai chủ đề - "Làng chiếu Cẩm Nê" cho ra "Sự kiện Cẩm Nê" (một sự kiện chiến
tranh), "Lễ hội Quan Thế Âm" cho ra "Quán Thế Âm" (bài về Bồ Tát). Đưa những
bài đó vào corpus còn tệ hơn thiếu dữ liệu, vì model sẽ học trả lời sai chủ đề
mà cổng trung thực không phát hiện được.

Danh sách cũ có 24/49 tên fail. Đã tra vi.wikipedia từng tên:
  - 6 tên chỉ sai chính tả/cách gọi, đã sửa ở dưới (xem RENAMED).
  - 18 tên KHÔNG có bài Wikipedia nào, đã chuyển sang NO_WIKI.
Bù lại, đã thêm các bài CÓ THẬT (đã kiểm dung lượng) mà danh sách cũ bỏ sót.
"""

# Tên cũ -> tên bài thật. Giữ lại để biết vì sao danh sách đổi.
RENAMED = {
    "Làng đá Non Nước": "Làng Non Nước",
    "Làng gốm Thanh Hà": "Làng Thanh Hà",
    "Bài chòi miền Trung": "Bài chòi",
    "Lễ hội Cầu Ngư": "Lễ Cầu ngư",
    "Bún chả cá Đà Nẵng": "Bún chả cá",
}

# Không có bài trên vi.wikipedia (tra ngày 2026-08-31, cả exact title lẫn
# search đều không ra bài đúng chủ đề). Muốn có dữ liệu cho nhóm này phải lấy
# nguồn khác (cổng thông tin tỉnh/thành, hồ sơ di sản, sách) - KHÔNG dùng
# search Wikipedia làm fallback.
NO_WIKI = [
    "Làng nghề đúc đồng Phường Đúc",
    "Làng nghề làm lụa Mỹ Xuyên",
    "Làng nghề hoa giấy Thanh Tiên",
    "Làng nghề làm hương Thủy Xuân",
    "Làng nghề đan nón Phú Cam",
    "Lễ hội đua thuyền sông Hương",
    "Lễ hội đền Huyền Trân",
    "Múa bóng",
    "Chè bắp Huế",
    "Làng La Hường",
    "Làng chiếu Cẩm Nê",
    "Làng nghề nước mắm Nam Ô",
    "Lễ hội Quan Thế Âm",
    "Lễ hội đua thuyền sông Hàn",
    "Lễ hội đình làng Cẩm Lệ",
    "Múa xứ Dừa",
    "Bánh tráng cuốn thịt heo",
    "Bún chả cá Đà Nẵng",  # bài "Bún chả cá" có nhưng ngắn, xem Ẩm thực Đà Nẵng
]

HUE_LOCATIONS = {
    "Di tích lịch sử": [
        "Hoàng thành Huế",
        "Kinh thành Huế",
        "Lăng Tự Đức",
        "Lăng Minh Mạng",
        "Lăng Khải Định",
        "Lăng Gia Long",
        "Lăng Thiệu Trị",
        "Lăng Đồng Khánh",
        "Lăng Dục Đức",
        "Chùa Thiên Mụ",
        "Chùa Từ Đàm",
        "Chùa Từ Hiếu",
        "Điện Hòn Chén",
        "Cầu Trường Tiền",
        "Đàn Nam Giao",
        "Hổ Quyền",
        "Cung An Định",
        "Chợ Đông Ba",
        "Bảo tàng Cổ vật Cung đình Huế",
    ],
    "Danh thắng": [
        "Sông Hương",
    ],
    "Lễ hội": [
        "Festival Huế",
        "Lễ Cầu ngư",
    ],
    "Nghệ thuật": [
        "Nhã nhạc cung đình Huế",
        "Ca Huế",
        "Hát tuồng",
    ],
    "Ẩm thực": [
        "Cơm hến",
        "Bún bò Huế",
        "Bánh khoái",
        "Bánh bèo",
        "Bánh bột lọc",
        "Mè xửng",
    ],
}

DANANG_LOCATIONS = {
    "Danh thắng": [
        "Ngũ Hành Sơn",
        "Sông Hàn",
        "Cầu Rồng",
    ],
    "Di tích lịch sử": [
        "Thành Điện Hải",
        "Bảo tàng Điêu khắc Chăm Đà Nẵng",
        "Nhà thờ chính tòa Đà Nẵng",
        "Chùa Linh Ứng",
    ],
    "Làng nghề": [
        "Làng Non Nước",
        "Làng Thanh Hà",
    ],
    "Nghệ thuật": [
        "Bài chòi",
    ],
    "Ẩm thực": [
        "Mì Quảng",
        "Bún chả cá",
        "Bánh xèo",
        "Cao lầu",
    ],
}


def get_all_locations():
    """Trả về list tất cả địa điểm kèm region."""
    all_locs = []
    for category, items in HUE_LOCATIONS.items():
        for item in items:
            all_locs.append({
                "region": "Huế",
                "category": category,
                "name": item,
            })
    for category, items in DANANG_LOCATIONS.items():
        for item in items:
            all_locs.append({
                "region": "Đà Nẵng",
                "category": category,
                "name": item,
            })
    return all_locs


if __name__ == "__main__":
    from collections import Counter

    locs = get_all_locations()
    print(f"Total: {len(locs)} địa điểm")
    print(f"  Huế: {sum(1 for l in locs if l['region'] == 'Huế')}")
    print(f"  Đà Nẵng: {sum(1 for l in locs if l['region'] == 'Đà Nẵng')}")
    print("  theo category:", dict(Counter(l["category"] for l in locs)))
    print(f"  chưa có nguồn Wikipedia: {len(NO_WIKI)} (xem NO_WIKI)")
