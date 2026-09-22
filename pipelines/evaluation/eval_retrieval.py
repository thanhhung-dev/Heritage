#!/usr/bin/env python3
"""Bộ ca kiểm thử retrieval — tách khỏi harness để harness còn đọc được.

  from eval.questions import IN_DOMAIN, OUT_OF_DOMAIN, EVIDENCE, SUBJECT, SCOPE, WARD, PARAPHRASE

QUY ƯỚC NHÃN
  # ?doc   nhãn vàng trỏ vào bài CHƯA CHẮC có trong corpus 45 bài. Preflight của
           eval_attribution.py sẽ cách ly. Danh sách bị cách ly = danh sách crawl.
  # trap   ca có bẫy đã biết, comment nói rõ bẫy là gì. Đừng "sửa" bằng cách nới
           nhãn — nới nhãn là làm thước đo mù.

PHÂN BỔ (215 ca)
  IN_DOMAIN 68 | PARAPHRASE 40 | OUT_OF_DOMAIN 36 | EVIDENCE 33
  SUBJECT 18 | SCOPE 15 | WARD 20  (mở rộng đúng nhóm khó, không phồng nhóm dễ)

Trong IN_DOMAIN, tỷ lệ có chủ đích: ~40% không dấu, ~25% tên gọi khác hoặc sai
chính tả. Nếu nhồi câu viết chuẩn gọi đúng tên thì recall sẽ đẹp mà vô nghĩa, vì
đó là ca BM25 không bao giờ trượt.
"""
from __future__ import annotations

# ─────────────────────────────────────────────────────────── TRONG PHẠM VI (68)
# Đo đúng một thứ: câu hỏi hợp lệ có chọn đúng BÀI không.

IN_DOMAIN: list[tuple[str, str]] = [
    # -- viết chuẩn, gọi đúng tên (đường cơ sở dễ nhất) ---------------------
    ("Lăng Minh Mạng được xây dựng năm nào?", "Lăng Minh Mạng"),
    ("Kiến trúc lăng Khải Định có gì đặc biệt?", "Lăng Khải Định"),
    ("Lăng Tự Đức còn có tên gọi khác là gì?", "Lăng Tự Đức"),
    ("Lăng Gia Long nằm ở đâu?", "Lăng Gia Long"),
    ("Hoàng thành Huế có mấy cửa?", "Hoàng thành Huế"),
    ("Nhã nhạc cung đình Huế được UNESCO công nhận năm nào?", "Nhã nhạc cung đình Huế"),
    ("Chùa Thiên Mụ do ai cho xây?", "Chùa Thiên Mụ"),
    ("Điện Hòn Chén thờ vị thần nào?", "Điện Hòn Chén"),
    ("Cầu Trường Tiền do ai thiết kế?", "Cầu Trường Tiền"),
    ("Đèo Hải Vân dài bao nhiêu km?", "Đèo Hải Vân"),
    ("Ngũ Hành Sơn gồm những ngọn núi nào?", "Ngũ Hành Sơn"),
    ("Bán đảo Sơn Trà có loài vật quý nào?", "Bán đảo Sơn Trà"),
    ("Mì Quảng nấu bằng sợi mì gì?", "Mì Quảng"),
    ("Bún bò Huế có nguồn gốc từ đâu?", "Bún bò Huế"),
    ("Cơm hến gồm những nguyên liệu nào?", "Cơm hến"),
    ("Ca Huế được biểu diễn ở đâu?", "Ca Huế"),
    ("Festival Huế tổ chức mấy năm một lần?", "Festival Huế"),
    ("Hát tuồng khác gì với cải lương?", "Hát tuồng"),
    ("Kinh thành Huế xây dưới triều vua nào?", "Kinh thành Huế"),          # ?doc
    ("Thành Điện Hải bị Pháp tấn công năm nào?", "Thành Điện Hải"),        # ?doc
    ("Hổ Quyền dùng để làm gì?", "Hổ Quyền"),                             # ?doc
    ("Chợ Đông Ba bán những gì?", "Chợ Đông Ba"),                          # ?doc
    ("Làng Non Nước làm nghề gì?", "Làng Non Nước"),                       # ?doc
    ("Cầu Rồng phun lửa vào ngày nào?", "Cầu Rồng"),                       # ?doc
    ("Chùa Linh Ứng có tượng gì lớn?", "Chùa Linh Ứng"),
    ("Chùa Từ Hiếu gắn với nhân vật nào?", "Chùa Từ Hiếu"),                # ?doc
    ("Sông Hàn chảy qua những nơi nào?", "Sông Hàn"),                      # ?doc

    # -- không dấu (kênh n-gram tồn tại để giải chính nhóm này) ------------
    ("lang minh mang o dau", "Lăng Minh Mạng"),
    ("lang khai dinh xay bao lau", "Lăng Khải Định"),
    ("lang tu duc rong bao nhieu", "Lăng Tự Đức"),
    ("lang gia long o dau", "Lăng Gia Long"),
    ("hoang thanh hue co may cua", "Hoàng thành Huế"),
    ("nha nhac cung dinh hue la gi", "Nhã nhạc cung đình Huế"),
    ("chua thien mu xay nam nao", "Chùa Thiên Mụ"),
    ("dien hon chen tho ai", "Điện Hòn Chén"),
    ("cau truong tien dai bao nhieu", "Cầu Trường Tiền"),
    ("deo hai van cao bao nhieu met", "Đèo Hải Vân"),
    ("ngu hanh son co hang dong nao", "Ngũ Hành Sơn"),
    ("ban dao son tra co gi", "Bán đảo Sơn Trà"),
    ("cao lau la mon gi", "Cao lầu"),
    ("mi quang an kem voi gi", "Mì Quảng"),
    ("me xung lam tu gi", "Mè xửng"),
    ("bun bo hue nau the nao", "Bún bò Huế"),
    ("com hen an nong hay lanh", "Cơm hến"),
    ("bao tang co vat cung dinh hue trung bay gi", "Bảo tàng Cổ vật Cung đình Huế"),
    ("ca hue hat tren thuyen phai khong", "Ca Huế"),
    ("hat tuong o da nang the nao", "Hát tuồng"),
    ("nha tho con ga xay nam nao", "Nhà thờ chính tòa Đà Nẵng"),
    ("thanh dien hai o dau", "Thành Điện Hải"),                            # ?doc
    ("ho quyen dung de lam gi", "Hổ Quyền"),                               # ?doc
    ("lang da non nuoc o dau", "Làng Non Nước"),                           # ?doc
    ("cau rong dai bao nhieu met", "Cầu Rồng"),                            # ?doc
    ("chua linh ung bai but o dau", "Chùa Linh Ứng"),
    ("cho dong ba o dau", "Chợ Đông Ba"),                                  # ?doc
    ("song han dai bao nhieu", "Sông Hàn"),                                # ?doc

    # -- tên gọi khác (đo bảng alias, không đo BM25) ------------------------
    ("nhà thờ con gà ở đâu?", "Nhà thờ chính tòa Đà Nẵng"),
    ("Đại nội Huế là gì?", "Hoàng thành Huế"),
    ("Khiêm Lăng là lăng của ai?", "Lăng Tự Đức"),
    ("Hiếu Lăng là lăng của vua nào?", "Lăng Minh Mạng"),
    ("Ứng Lăng là tên gọi khác của lăng nào?", "Lăng Khải Định"),
    ("Thiên Thọ Lăng thuộc vua nào?", "Lăng Gia Long"),
    ("điện Huệ Nam thờ ai?", "Điện Hòn Chén"),
    ("Tháp Phước Duyên nằm ở chùa nào?", "Chùa Thiên Mụ"),
    ("Ngọ Môn là cửa của công trình nào?", "Hoàng thành Huế"),             # trap: dễ về Kinh thành
    ("Điện Long An hiện nay là bảo tàng nào?", "Bảo tàng Cổ vật Cung đình Huế"),

    # -- sai chính tả / gõ nhanh (fuzzy_match phải bắt, KHÔNG được nới cổng) -
    ("chùa Linh Mụ ở đâu?", "Chùa Thiên Mụ"),
    ("cầu Tràng Tiền dài bao nhiêu?", "Cầu Trường Tiền"),
    ("kẹo mè xửng làm từ gì?", "Mè xửng"),
    ("lăng Khãi Định ở đâu?", "Lăng Khải Định"),                           # dấu sai
    ("ngủ hành sơn có mấy núi?", "Ngũ Hành Sơn"),                          # dấu sai
]

# ──────────────────────────────────────────────────────────── PARAPHRASE (40)
# KHÔNG dùng tên riêng của bài. Đây là nhóm NFR04 đòi ≥95% mà chưa có bằng chứng,
# và là nhóm duy nhất biện minh được kênh vector. Nếu baseline ở đây đã cao thì
# ghi vào báo cáo như một kết quả và tiết kiệm cả một sprint.

PARAPHRASE: list[tuple[str, str]] = [
    ("vua Tự Đức được chôn ở chỗ nào?", "Lăng Tự Đức"),
    ("vua Khải Định được chôn ở chỗ nào?", "Lăng Khải Định"),
    ("vua Minh Mạng an nghỉ ở đâu?", "Lăng Minh Mạng"),
    ("vị vua đầu tiên nhà Nguyễn nằm ở lăng nào?", "Lăng Gia Long"),
    ("lăng nào pha trộn kiến trúc Á và Âu?", "Lăng Khải Định"),
    ("lăng nào có hồ nước và nhà thủy tạ để vua làm thơ?", "Lăng Tự Đức"),
    ("khu vua ở và làm việc trong thành cổ Huế", "Hoàng thành Huế"),
    ("vòng thành ngoài cùng của cố đô", "Kinh thành Huế"),                 # ?doc
    ("ngôi chùa cổ nhất xứ Huế", "Chùa Thiên Mụ"),
    ("ngôi chùa nổi tiếng bên sông Hương", "Chùa Thiên Mụ"),
    ("ngôi chùa nơi thiền sư Nhất Hạnh xuất gia", "Chùa Từ Hiếu"),         # ?doc
    ("nơi thờ nữ thần trên núi bên bờ sông ở Huế", "Điện Hòn Chén"),
    ("cây cầu sắt sáu vài do người Pháp dựng ở cố đô", "Cầu Trường Tiền"),
    ("cây cầu biểu tượng phun lửa cuối tuần", "Cầu Rồng"),                 # ?doc
    ("con đèo ngăn cách hai địa phương miền Trung", "Đèo Hải Vân"),
    ("dãy núi mang tên năm nguyên tố", "Ngũ Hành Sơn"),
    ("nơi sinh sống của loài linh trưởng chân nâu quý hiếm", "Bán đảo Sơn Trà"),
    ("tượng Phật Bà rất cao nhìn ra biển", "Chùa Linh Ứng"),
    ("pháo đài chống hạm đội phương Tây năm 1858", "Thành Điện Hải"),       # ?doc
    ("đấu trường cho voi và hổ thời phong kiến", "Hổ Quyền"),               # ?doc
    ("khu chợ lâu đời bên bờ sông Hương", "Chợ Đông Ba"),                   # ?doc
    ("nơi lưu giữ đồ dùng của vua chúa nhà Nguyễn", "Bảo tàng Cổ vật Cung đình Huế"),
    ("nhà thờ có tượng con gà trên nóc", "Nhà thờ chính tòa Đà Nẵng"),
    ("con sông chia đôi thành phố biển miền Trung", "Sông Hàn"),            # ?doc
    ("nghề tạc tượng bằng đá dưới chân núi", "Làng Non Nước"),              # ?doc
    ("món mì nào của phố cổ Hội An", "Cao lầu"),
    ("món sợi vàng ăn với thịt xá xíu ở phố cổ", "Cao lầu"),
    ("món ăn dân dã làm từ loài nhuyễn thể sông Hương", "Cơm hến"),
    ("món bún có nguồn gốc từ vùng đất cố đô", "Bún bò Huế"),
    ("món nước lèo cay nồng ăn với chả và giò heo", "Bún bò Huế"),
    ("bánh ngọt làm từ đường mạch nha và hạt vừng", "Mè xửng"),
    ("món sợi vàng nghệ ăn với đậu phụng rang", "Mì Quảng"),
    ("nhạc cổ truyền được UNESCO công nhận ở Huế", "Nhã nhạc cung đình Huế"),
    ("loại nhạc thính phòng hát trên thuyền ở cố đô", "Ca Huế"),
    ("loại hình sân khấu cổ có mặt nạ vẽ", "Hát tuồng"),
    ("kỳ lễ hội văn hóa lớn nhất của cố đô", "Festival Huế"),
    ("nơi thờ tự có tháp bảy tầng bên bờ sông", "Chùa Thiên Mụ"),
    ("bãi biển và núi có khỉ ở thành phố biển", "Bán đảo Sơn Trà"),
    ("làng làm đồ mỹ nghệ từ đá cẩm thạch", "Làng Non Nước"),               # ?doc
]

# ───────────────────────────────────────────────────────── NGOÀI PHẠM VI (36)
# Bốn lớp bẫy khác nhau, và chúng KHÔNG thay thế được nhau:
#   (a) khác miền hoàn toàn        — cổng nào cũng chặn được
#   (b) đúng loại, sai vùng        — chỉ scope/anchor chặn được
#   (c) có node trong graph, KHÔNG có bài — lớp lỗi của ca Đàn Nam Giao
#   (d) phường/xã ngoài địa bàn    — chỉ edge ward chặn được
# Lớp (c) là lớp nguy hiểm nhất và hiện chỉ có 1 ca; tôi thêm 5.

OUT_OF_DOMAIN: list[str] = [
    # (a) khác miền
    "Giá bitcoin hôm nay bao nhiêu?",
    "Cách học tiếng Nhật nhanh nhất",
    "Giải phương trình bậc hai x^2 - 5x + 6 = 0",
    "Thời tiết Hà Nội ngày mai thế nào?",
    "Công thức làm bánh mì bơ tỏi",
    "Đội tuyển Việt Nam đá với ai tối nay?",
    "Cho tôi xin số điện thoại của bạn",
    "Viết cho tôi một đoạn code Python đọc file CSV",
    "Dịch câu này sang tiếng Anh: tôi rất thích Huế",
    "Tỷ giá đô la hôm nay bao nhiêu?",
    "Vé máy bay Hà Nội Đà Nẵng giá bao nhiêu?",
    "Khách sạn nào ở Huế giá rẻ nhất?",
    "Số điện thoại taxi ở Đà Nẵng",
    "Ai là chủ tịch nước hiện nay?",

    # (b) đúng loại, sai vùng — di sản và ẩm thực nơi khác
    "Vịnh Hạ Long có bao nhiêu hòn đảo?",
    "Cố đô Hoa Lư ở tỉnh nào?",
    "Thành nhà Hồ được xây năm nào?",
    "Chùa Một Cột ở đâu?",
    "Nhà thờ Lớn Hà Nội xây năm nào?",
    "Nhà hát lớn Hà Nội do ai thiết kế?",
    "Đền Hùng thờ ai?",
    "Chợ Bến Thành ở đâu?",
    "Phở Hà Nội nấu thế nào?",
    "Cơm tấm Sài Gòn ăn với gì?",
    "Bún chả cá Nha Trang có gì đặc biệt?",
    "Nem chua Thanh Hóa làm từ gì?",
    "Cồng chiêng Tây Nguyên được công nhận năm nào?",
    "Dân ca ví giặm Nghệ Tĩnh là gì?",

    # (c) CÓ node trong graph, KHÔNG có bài riêng — lớp lỗi Đàn Nam Giao.
    #     Đây là các thực thể được NHẮC trong bài khác. Nếu cổng bằng chứng chấp
    #     nhận nhánh "có nhắc tên" thì cả sáu ca này rò, không riêng ca đầu.
    "Đàn Nam Giao thờ ai?",
    "Cửu Đỉnh được đúc năm nào?",
    "Thế Miếu thờ những vị vua nào?",
    "Điện Thái Hòa dùng để làm gì?",
    "Cửu vị thần công nặng bao nhiêu?",
    "Trường Quốc Học Huế thành lập năm nào?",

    # (d) phường/xã ngoài địa bàn
    "phường Cầu Giấy có di tích gì?",
    "quận Ba Đình có lăng nào?",
    "phường Bến Nghé có món ăn nào?",
    "xã Đông Anh có lễ hội gì?",
]

# ───────────────────────────────────────────────── BẰNG CHỨNG TRONG CONTEXT (33)
# Không đo chọn đúng bài mà đo chọn đúng CHUNK: chuỗi needle phải nằm trong context.
# needle ngắn (tên vùng/phường) là có chủ đích — needle là dữ kiện, không phải câu.

EVIDENCE: list[tuple[str, str]] = [
    # -- tiền đề sai/đúng về vùng, có dấu ----------------------------------
    ("Chùa Thiên Mụ ở Đà Nẵng đúng không?", "Huế"),
    ("Chùa Thiên Mụ ở Huế đúng không?", "Huế"),
    ("chùa Linh Ứng ở Huế phải không?", "Đà Nẵng"),
    ("Chùa Linh Ứng ở Đà Nẵng phải không?", "Đà Nẵng"),
    ("Mì Quảng là món của Huế đúng không?", "Đà Nẵng"),
    ("Cầu Rồng ở Huế đúng không?", "Đà Nẵng"),
    ("Cơm hến là món của Huế đúng không?", "Huế"),
    ("Lăng Tự Đức ở Đà Nẵng có phải không?", "Huế"),
    ("Hổ Quyền ở Đà Nẵng đúng không?", "Huế"),                             # ?doc
    ("Thành Điện Hải ở Huế phải không?", "Đà Nẵng"),                       # ?doc
    ("Chợ Đông Ba ở Đà Nẵng đúng không?", "Huế"),                          # ?doc
    ("Làng Non Nước ở Huế phải không?", "Đà Nẵng"),                        # ?doc
    ("Sông Hàn chảy qua Huế đúng không?", "Đà Nẵng"),                      # ?doc
    ("Ngũ Hành Sơn ở Huế đúng không?", "Đà Nẵng"),
    ("Chùa Từ Hiếu ở Đà Nẵng phải không?", "Huế"),                         # ?doc
    ("nhà thờ con gà ở đâu?", "Đà Nẵng"),
    ("Lăng Minh Mạng xây năm nào?", "1840"),   # needle CHÍNH XÁC, không phải "184"

    # -- scope trong câu NGƯỢC với thực tế: tên riêng phải thắng scope ------
    ("Cơm hến là món ăn của Đà Nẵng đúng không?", "Huế"),
    ("Cao lầu là món Huế phải không?", "Đà Nẵng"),

    # -- giả định LÀ MỘT BÀI KHÁC trong corpus (bẫy nặng nhất) -------------
    ("Lăng Tự Đức ở phường Ngũ Hành Sơn đúng không?", "Thủy Xuân"),
    ("Chùa Thiên Mụ ở Ngũ Hành Sơn đúng không?", "Huế"),
    ("Cầu Rồng ở sông Hương đúng không?", "Đà Nẵng"),                      # ?doc
    ("Lăng Khải Định nằm ở làng Non Nước phải không?", "Huế"),
    ("Chùa Linh Ứng ở Bán đảo Sơn Trà đúng không?", "Sơn Trà"),
    ("Hổ Quyền ở Ngũ Hành Sơn phải không?", "Huế"),                        # ?doc
    ("Chợ Đông Ba gần Cầu Rồng đúng không?", "Huế"),                       # ?doc

    # -- KHÔNG DẤU + kiểm chứng: chunk #0 (nơi duy nhất ghi tỉnh) hay tụt hạng
    ("lang khai dinh o da nang dung khong", "Huế"),
    ("lang tu duc o da nang dung khong", "Huế"),
    ("com hen la mon da nang phai khong", "Huế"),
    ("chua linh ung o hue phai khong", "Đà Nẵng"),
    ("mi quang la mon hue dung khong", "Đà Nẵng"),
    ("ho quyen o da nang dung khong", "Huế"),                              # ?doc
    ("thanh dien hai o hue phai khong", "Đà Nẵng"),                        # ?doc
    ("cho dong ba o da nang dung khong", "Huế"),                           # ?doc
]

# ──────────────────────────────────────────── CHỦ ĐỀ vs GIẢ ĐỊNH (18)
# "" = câu KHÔNG có cấu trúc chủ đề/giả định, hệ phải KHÔNG thu hẹp.

SUBJECT: list[tuple[str, str]] = [
    ("Lăng Tự Đức ở phường Ngũ Hành Sơn đúng không?", "Lăng Tự Đức"),
    ("Lăng Tự Đức Ở Phường Ngũ Hành Sơn Đúng Không", "Lăng Tự Đức"),
    ("lang tu duc o phuong ngu hanh son dung khong", "Lăng Tự Đức"),
    ("Chùa Thiên Mụ ở Ngũ Hành Sơn đúng không?", "Chùa Thiên Mụ"),
    ("Cầu Rồng ở sông Hương đúng không?", "Cầu Rồng"),                     # ?doc
    ("Lăng Khải Định nằm ở làng Non Nước phải không?", "Lăng Khải Định"),
    ("Lăng Minh Mạng gần Lăng Gia Long phải không?", "Lăng Minh Mạng"),
    ("Chùa Linh Ứng ở Ngũ Hành Sơn có gì đặc biệt?", "Chùa Linh Ứng"),
    ("Cầu Trường Tiền trên sông Hương dài bao nhiêu?", "Cầu Trường Tiền"),
    ("Hổ Quyền ở phường Thủy Xuân đúng không?", "Hổ Quyền"),               # ?doc
    ("Thành Điện Hải ở phường Hòa Hải phải không?", "Thành Điện Hải"),     # ?doc
    ("Làng Non Nước ở Ngũ Hành Sơn đúng không?", "Làng Non Nước"),         # ?doc
    ("chua linh ung o ngu hanh son co gi dac biet", "Chùa Linh Ứng"),
    ("cau truong tien tren song huong dai bao nhieu", "Cầu Trường Tiền"),

    # -- SO SÁNH: hai tên NGANG HÀNG, không tên nào là giả định ------------
    ("Lăng Tự Đức và Lăng Khải Định khác nhau thế nào?", ""),
    ("So sánh Mì Quảng và Cao lầu", ""),
    ("Nhã nhạc cung đình và Ca Huế khác nhau ra sao?", ""),
    ("Cao lầu và Mì Quảng món nào sợi dày hơn?", ""),
]

# ──────────────────────────────────────────────────────────────── SCOPE (15)
# Câu KHÔNG nêu tên riêng: hệ phải thu hẹp đúng vùng + loại rồi tìm sâu.

SCOPE: list[tuple[str, str, str]] = [
    ("Đà Nẵng có món ăn gì đặc trưng?", "Đà Nẵng", "Ẩm thực"),
    ("Huế có món ăn đặc sản nào?", "Huế", "Ẩm thực"),
    ("kể tôi nghe về ẩm thực Huế", "Huế", "Ẩm thực"),
    ("Huế có lễ hội nào?", "Huế", "Lễ hội"),
    ("Đà Nẵng có làng nghề gì?", "Đà Nẵng", "Làng nghề"),
    ("Đà Nẵng có danh thắng nào?", "Đà Nẵng", "Danh thắng"),
    ("Huế có nghệ thuật gì?", "Huế", "Nghệ thuật"),
    ("di tích lịch sử ở Đà Nẵng", "Đà Nẵng", "Di tích lịch sử"),
    ("Huế có di tích lịch sử nào?", "Huế", "Di tích lịch sử"),
    ("danh thắng ở Huế", "Huế", "Danh thắng"),
    ("nghệ thuật diễn xướng ở Đà Nẵng", "Đà Nẵng", "Nghệ thuật"),          # trap: corpus mỏng
    ("mon an dac san hue", "Huế", "Ẩm thực"),
    ("da nang co danh thang nao", "Đà Nẵng", "Danh thắng"),
    ("hue co le hoi gi", "Huế", "Lễ hội"),
    ("di tich o da nang", "Đà Nẵng", "Di tích lịch sử"),
]

# ─────────────────────────────────────────── QUAN HỆ CẤP HÀNH CHÍNH (20)
# Nhóm đo THẲNG vào giá trị lớp graph: BM25 không có khái niệm "phường này chứa gì".
# Tập bài, không phải một bài — nhưng tập phải khớp LOẠI được hỏi.

WARD: list[tuple[str, set[str]]] = [
    ("lăng nào ở phường Thủy Xuân?",
     {"Lăng Tự Đức", "Lăng Khải Định", "Lăng Đồng Khánh"}),   # bỏ Chùa Từ Hiếu: hỏi LĂNG
    ("phường Thủy Xuân có di tích gì?",
     {"Lăng Tự Đức", "Lăng Khải Định", "Lăng Đồng Khánh", "Chùa Từ Hiếu"}),
    ("phuong thuy xuan co lang nao",
     {"Lăng Tự Đức", "Lăng Khải Định", "Lăng Đồng Khánh"}),
    ("di sản nào ở phường Long Hồ?", {"Lăng Minh Mạng", "Điện Hòn Chén"}),
    ("phường Hòa Hải có gì?", {"Ngũ Hành Sơn", "Làng Non Nước"}),
    ("phường Sơn Trà có danh thắng nào?", {"Bán đảo Sơn Trà"}),
    ("phường Thủy Biều có gì?", {"Hổ Quyền"}),                             # ?doc
    ("quận Sơn Trà có chùa nào?", {"Chùa Linh Ứng"}),   # trap cũ: nhãn từng nhận Sông Hàn
    ("phường Đông Ba có gì?", {"Chợ Đông Ba", "Kinh thành Huế"}),          # ?doc
    ("phường Thạch Thang có di tích gì?", {"Thành Điện Hải"}),             # ?doc
    ("phuong hoa hai co gi", {"Ngũ Hành Sơn", "Làng Non Nước"}),
    ("phuong son tra co danh thang nao", {"Bán đảo Sơn Trà"}),

    # -- chiều NGƯỢC: từ di sản suy ra phường ------------------------------
    ("Thành Điện Hải thuộc phường nào?", {"Thành Điện Hải"}),              # ?doc
    ("Lăng Tự Đức ở phường nào?", {"Lăng Tự Đức"}),
    ("Chùa Từ Hiếu thuộc phường nào?", {"Chùa Từ Hiếu"}),                  # ?doc
    ("Cầu Trường Tiền ở phường nào?", {"Cầu Trường Tiền"}),
    ("Lăng Gia Long thuộc phường nào?", {"Lăng Gia Long"}),
    ("Hổ Quyền thuộc phường nào?", {"Hổ Quyền"}),                          # ?doc
    ("Làng Non Nước thuộc phường nào?", {"Làng Non Nước"}),                # ?doc
    ("chua linh ung o phuong nao", {"Chùa Linh Ứng"}),
]
