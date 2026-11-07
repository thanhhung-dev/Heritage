"""Seed 30 heritage places (Huế / Đà Nẵng / Quảng Nam) for HeritageGraph.

Curated Vietnamese content, OpenStreetMap coordinates and Unsplash photography.
Scene skeletons for places that have none are added by
``seed_heritage_scenes.py`` (run this script first).

Run from the project root:
    apps/backend/.venv/bin/python apps/backend/db/seed_heritage_places.py

Idempotent: rows are upserted by ``slug``. The existing ``lang-tu-duc`` row is
left untouched (it already carries R2 media and 5 scenes).

Notes
-----
* Images are Unsplash CDN URLs (``images.unsplash.com``) served through the
  standard ``auto=format&fit=crop`` transform: 800x600 for the card,
  1600x900 for the splash. They are *thematically* matched (Huế imperial
  architecture, Đà Nẵng bridges/coast, Hội An old town) rather than
  documentary shots of each individual monument.
* ``lat``/``lng`` come from OpenStreetMap (via Photon geocoding).
* The festival linkage from the source catalogue has no dedicated column in
  the schema, so it is folded into ``description`` as a factual sentence.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import psycopg

DB_HOST = os.environ.get("SEED_DB_HOST", "127.0.0.1")
DB_PORT = os.environ.get("SEED_DB_PORT", "5433")
DB_NAME = os.environ.get("SEED_DB_NAME", "heritagegraph")
DB_USER = os.environ.get("SEED_DB_USER", "heritagegraph")


def load_env() -> dict[str, str]:
    """Read POSTGRES_* from the repo .env so the password is never hardcoded."""
    env: dict[str, str] = {}
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def img(photo_id: str, width: int, height: int) -> str:
    return (
        f"https://images.unsplash.com/{photo_id}"
        f"?auto=format&fit=crop&w={width}&h={height}&q=80"
    )


# (slug, title, tagline, headline, description, region, lat, lng,
#  duration_seconds, map_zoom, unsplash photo id)
PLACES = [
    # ── HUẾ ────────────────────────────────────────────────────────────
    (
        "lang-minh-mang", "Lăng Minh Mạng",
        "Sự cân bằng tuyệt đối giữa kiến trúc và phong thủy",
        "Bước vào Hiếu Lăng, nơi đối xứng và thiên nhiên gặp nhau",
        "Lăng của vua Minh Mạng (trị vì 1820–1841), khởi công năm 1840 và hoàn thành năm 1843. "
        "Quần thể gồm khoảng 40 công trình bố cục đối xứng trên ba trục, nối liền bởi hồ sen, "
        "đại trụ biểu và những cây cầu đá, được xem là lăng tẩm hài hòa nhất của triều Nguyễn.",
        "Huế", 16.38775, 107.56778, 2100, 15.0, "photo-1616486410185-81af2d32a2af",
    ),
    (
        "lang-gia-long", "Lăng Gia Long",
        "Lăng mộ của người mở nghiệp triều Nguyễn",
        "Tìm về Thiên Thọ Lăng giữa rừng núi tĩnh mịch",
        "Thiên Thọ Lăng của vua Gia Long (trị vì 1802–1820) nằm biệt lập giữa rừng núi phía "
        "tây nam Huế, bên dòng sông Hương. Quần thể rộng lớn gồm khu tẩm điện, sân chầu và mộ "
        "phần, mang vẻ hoang sơ và tĩnh mịch đặc trưng.",
        "Huế", 16.36319, 107.59648, 2100, 14.0, "photo-1701218408839-7f7a6dcd092a",
    ),
    (
        "lang-khai-dinh", "Lăng Khải Định",
        "Nơi Đông và Tây gặp nhau trong từng mảnh sành",
        "Chiêm ngưỡng Ứng Lăng – lăng tẩm giàu chi tiết nhất",
        "Ứng Lăng của vua Khải Định (trị vì 1916–1925) được xây dựng từ năm 1920 đến 1931, "
        "nổi bật với kiến trúc pha trộn Á – Âu và nội thất khảm sành sứ, thủy tinh màu. Đây là "
        "lăng tẩm có diện tích khiêm tốn nhưng giàu chi tiết bậc nhất của triều Nguyễn.",
        "Huế", 16.39902, 107.59034, 1800, 15.5, "photo-1743999898066-cdfd5a1a7d22",
    ),
    (
        "cung-an-dinh", "Cung An Định",
        "Cung điện của vị vua cuối cùng triều Nguyễn",
        "Bước vào không gian cung đình đầu thế kỷ 20",
        "Cung An Định được vua Khải Định cho xây dựng đầu thế kỷ 20 bên bờ sông An Cựu, mang "
        "kiến trúc cung đình kết hợp phong cách châu Âu. Sau này cung gắn với cuộc đời Nam "
        "Phương hoàng hậu – vị hoàng hậu cuối cùng của Việt Nam.",
        "Huế", 16.45663, 107.59831, 900, 16.0, "photo-1696147861445-9fdebe294c6b",
    ),
    (
        "cong-ngo-mon", "Cổng Ngọ Môn",
        "Cửa chính phía nam của Hoàng thành",
        "Đứng dưới lầu Ngũ Phụng nhìn về kinh đô cũ",
        "Ngọ Môn là cổng chính phía nam Hoàng thành Huế, được xây dựng dưới thời vua Minh Mạng. "
        "Công trình có năm lối đi, phía trên là lầu Ngũ Phụng – nơi diễn ra nhiều nghi lễ quan "
        "trọng của triều đình.",
        "Huế", 16.46773, 107.57915, 600, 16.0, "photo-1653279594700-832fe2310a82",
    ),
    (
        "dai-noi-hue", "Đại Nội Huế",
        "Trái tim của kinh đô triều Nguyễn",
        "Đi qua Hoàng thành vào Tử Cấm Thành",
        "Đại Nội gồm Hoàng thành và Tử Cấm Thành – nơi làm việc và sinh sống của các vua Nguyễn. "
        "Quần thể được UNESCO công nhận là Di sản Văn hóa Thế giới năm 1993, hiện là không gian "
        "diễn ra nhiều nghi lễ và sự kiện văn hóa của Huế.",
        "Huế", 16.46897, 107.57813, 3600, 15.0, "photo-1692449452966-661371c6def1",
    ),
    (
        "chua-thien-mu", "Chùa Thiên Mụ",
        "Ngôi chùa cổ nhất bên dòng Hương Giang",
        "Lắng nghe tiếng chuông chùa bên tháp Phước Duyên",
        "Chùa Thiên Mụ được chúa Nguyễn Hoàng cho dựng năm 1601, là ngôi chùa cổ nhất của Huế. "
        "Tháp Phước Duyên bảy tầng phía trước chùa đã trở thành biểu tượng của cố đô.",
        "Huế", 16.45372, 107.54458, 1500, 15.5, "photo-1732158606217-734125ae947d",
    ),
    (
        "chua-huyen-khong-son-thuong", "Chùa Huyền Không Sơn Thượng",
        "Ngôi chùa ẩn mình giữa rừng thông",
        "Tìm sự tĩnh lặng trên vùng đồi Hương Trà",
        "Chùa Huyền Không Sơn Thượng tọa lạc trên vùng đồi thông thuộc Hương Trà, cách trung tâm "
        "Huế khoảng 10 km. Không gian chùa hòa vào thiên nhiên với vườn tháp, hồ nước và những "
        "câu thơ Thiền khắc trên đá.",
        "Huế", 16.45083, 107.49381, 1200, 15.0, "photo-1701218408965-2740ec326aa9",
    ),
    (
        "dien-hon-chen", "Điện Hòn Chén",
        "Không gian tín ngưỡng bên sông Hương",
        "Theo thuyền ngược dòng tìm Điện Huệ Nam",
        "Điện Hòn Chén (Điện Huệ Nam) nằm trên núi Ngọc Hồ bên bờ sông Hương, thờ Thánh Mẫu "
        "Thiên Y A Na. Hằng năm nơi đây diễn ra lễ hội Điện Huệ Nam với các nghi lễ rước và hầu "
        "đồng, thu hút đông người dân và du khách.",
        "Huế", 16.42196, 107.56292, 1500, 15.0, "photo-1557750255-c76072a7aad1",
    ),
    (
        "lang-sinh", "Làng Sình",
        "Hội vật làng Sình mùng 10 tháng Giêng",
        "Xem các đô vật tranh tài bên bờ sông Hương",
        "Làng Sình (phường Hương Sơ, Huế) nổi tiếng với hội vật tổ chức vào mùng 10 tháng Giêng "
        "âm lịch, thu hút đô vật từ nhiều nơi trong vùng. Làng còn được biết đến với tranh dân "
        "gian Làng Sình – một di sản nghề truyền thống.",
        "Huế", 16.52176, 107.57748, 900, 15.0, "photo-1508305253994-348e8237adc0",
    ),
    (
        "cau-ngoi-thanh-toan", "Cầu ngói Thanh Toàn",
        "Cây cầu ngói hơn hai thế kỷ",
        "Bước qua nhịp cầu gỗ có mái che cổ nhất còn lại",
        "Cầu ngói Thanh Toàn bắc qua dòng kênh Như Ý, được xây dựng năm 1776 theo hình thức cầu "
        "gỗ có mái che. Cầu gắn với các hoạt động văn hóa dân gian và lễ hội của cư dân vùng "
        "Thanh Thủy.",
        "Huế", 16.46679, 107.64270, 900, 16.0, "photo-1716795311009-c8858984acf5",
    ),
    (
        "lang-thieu-tri", "Lăng Thiệu Trị",
        "Lăng tẩm của vị vua thi sĩ",
        "Ghé Xương Lăng trên đường tới lăng Tự Đức",
        "Xương Lăng của vua Thiệu Trị (trị vì 1841–1847) nằm bên bờ sông Hương, gần lăng Tự Đức. "
        "Quần thể có bố cục chặt chẽ, hài hòa giữa kiến trúc và cảnh quan đồi núi.",
        "Huế", 16.41626, 107.57322, 1500, 15.0, "photo-1597821137116-0e51f93572f4",
    ),
    (
        "lang-dong-khanh", "Lăng Đồng Khánh",
        "Sự chuyển tiếp giữa hai thời đại",
        "Khám phá Tư Lăng – lăng tẩm giao thời",
        "Tư Lăng của vua Đồng Khánh (trị vì 1885–1889) mang kiến trúc giao thời, kết hợp yếu tố "
        "truyền thống và ảnh hưởng phương Tây. Lăng nằm trong khu vực lăng tẩm phía nam Huế.",
        "Huế", 16.42964, 107.56852, 1200, 15.0, "photo-1568775791746-bcc117bcb312",
    ),
    (
        "cuu-dinh", "Cửu Đỉnh",
        "Chín đỉnh đồng trước Thế Tổ Miếu",
        "Đọc phong cảnh đất nước trên chín đỉnh đồng",
        "Cửu Đỉnh gồm chín đỉnh đồng được vua Minh Mạng cho đúc trong hai năm 1835–1837, đặt "
        "trước Thế Tổ Miếu trong Đại Nội. Mỗi đỉnh khắc họa phong cảnh, sản vật và biểu tượng "
        "của đất nước thời Nguyễn.",
        "Huế", 16.46760, 107.57810, 900, 16.5, "photo-1610913811870-77ecc2f3c1f1",
    ),
    (
        "cau-truong-tien", "Cầu Trường Tiền",
        "Sáu nhịp cầu bên sông Hương",
        "Ngắm cầu Trường Tiền lên đèn bên bờ sông Hương",
        "Cầu Trường Tiền được xây dựng năm 1899, là cây cầu sắt sáu nhịp bắc qua sông Hương. "
        "Trải qua nhiều lần trùng tu, cầu vẫn là hình ảnh gắn bó với Huế.",
        "Huế", 16.46890, 107.58886, 600, 15.5, "photo-1603054561323-09f79d5df183",
    ),
    (
        "cho-dong-ba", "Chợ Đông Ba",
        "Ngôi chợ lớn nhất của cố đô",
        "Hòa vào nhịp sống chợ Đông Ba",
        "Chợ Đông Ba được xây dựng năm 1899 bên bờ sông Hương, là ngôi chợ lớn nhất Huế. Chợ bán "
        "đủ đặc sản, nón lá, đồ thủ công và phản ánh nhịp sống thường nhật của thành phố.",
        "Huế", 16.47245, 107.58865, 1500, 16.0, "photo-1508075679049-7e5dc384e98b",
    ),
    # ── ĐÀ NẴNG ────────────────────────────────────────────────────────
    (
        "cau-rong", "Cầu Rồng",
        "Biểu tượng mới của thành phố Đà Nẵng",
        "Xem rồng phun lửa trên sông Hàn",
        "Cầu Rồng dài 666 m bắc qua sông Hàn, khánh thành năm 2013 với tạo hình rồng uốn lượn. "
        "Vào cuối tuần, cầu phun lửa và nước – sự kiện đô thị thu hút đông đảo người xem.",
        "Đà Nẵng", 16.06117, 108.22790, 600, 15.5, "photo-1716903197952-440ea3233ba3",
    ),
    (
        "cau-song-han", "Cầu Sông Hàn",
        "Cây cầu quay đầu tiên do người Việt thiết kế",
        "Đứng trên cầu Sông Hàn ngắm thành phố lên đèn",
        "Cầu Sông Hàn khánh thành năm 2000, là cây cầu quay đầu tiên ở Việt Nam do kỹ sư trong "
        "nước thiết kế và thi công. Ban đêm cầu rực sáng, trở thành điểm ngắm cảnh quen thuộc "
        "của Đà Nẵng.",
        "Đà Nẵng", 16.07199, 108.22555, 720, 15.5, "photo-1440694997168-8ae4033554c7",
    ),
    (
        "chua-linh-ung-son-tra", "Chùa Linh Ứng – Sơn Trà",
        "Tượng Phật Quán Thế Âm giữa bán đảo",
        "Đứng dưới tượng Phật nhìn ra biển Đông",
        "Chùa Linh Ứng tọa lạc trên bán đảo Sơn Trà, nổi bật với tượng Phật Quán Thế Âm cao "
        "67 m hướng ra biển. Đây là một trong những không gian Phật giáo – cảnh quan tiêu biểu "
        "của Đà Nẵng.",
        "Đà Nẵng", 16.10016, 108.27841, 1800, 15.0, "photo-1696215104974-92eaf194049f",
    ),
    (
        "bao-tang-dieu-khac-cham", "Bảo tàng Điêu khắc Chăm",
        "Bộ sưu tập điêu khắc Chăm lớn nhất",
        "Đọc lịch sử Champa qua từng pho tượng",
        "Bảo tàng Điêu khắc Chăm Đà Nẵng được người Pháp khởi công năm 1915, lưu giữ bộ sưu tập "
        "hiện vật điêu khắc Chăm lớn nhất Việt Nam, gắn với lịch sử vương quốc Champa.",
        "Đà Nẵng", 16.06012, 108.22308, 1500, 16.0, "photo-1665658455567-f5841c70e352",
    ),
    (
        "ngu-hanh-son", "Ngũ Hành Sơn",
        "Lễ hội Quán Thế Âm giữa núi đá cẩm thạch",
        "Vào động Huyền Không giữa năm ngọn núi đá",
        "Ngũ Hành Sơn gồm năm ngọn núi đá cẩm thạch với hệ thống động, chùa và am miếu. Hằng "
        "năm, lễ hội Quán Thế Âm diễn ra tại chùa Quán Thế Âm vào ngày 19 tháng 2 âm lịch, thu "
        "hút đông đảo Phật tử và du khách.",
        "Đà Nẵng", 16.01080, 108.25318, 2700, 14.5, "photo-1464809142576-df63ca4ed7f0",
    ),
    (
        "dinh-lang-tuy-loan", "Đình làng Túy Loan",
        "Ngôi đình cổ của làng Việt",
        "Về Túy Loan nghe chuyện khai khẩn làng xưa",
        "Đình làng Túy Loan (xã Hòa Phong, Đà Nẵng) là ngôi đình cổ gắn với lịch sử khai khẩn "
        "vùng đất Hòa Vang. Lễ hội đình diễn ra mùng 9–10 tháng Giêng với tế Xuân, tế Thu, rước "
        "sắc và cầu an.",
        "Đà Nẵng", 15.99757, 108.13645, 900, 15.0, "photo-1571842533456-9b0d746c5a9b",
    ),
    (
        "dinh-lang-nam-o", "Đình làng Nam Ô",
        "Lễ Cầu Ngư của làng chài",
        "Nghe chuyện biển của cư dân Nam Ô",
        "Đình làng Nam Ô gắn với đời sống cư dân biển và nghề làm nước mắm truyền thống. Lễ Cầu "
        "Ngư cùng các nghi lễ tín ngưỡng biển được tổ chức hằng năm, cầu cho mùa cá bội thu.",
        "Đà Nẵng", 16.11050, 108.12300, 900, 15.0, "photo-1690038718228-fbfd02d30984",
    ),
    (
        "ban-dao-son-tra", "Bán đảo Sơn Trà",
        "Rừng nguyên sinh giữa thành phố biển",
        "Đi men theo cung đường ven biển Sơn Trà",
        "Bán đảo Sơn Trà là khu bảo tồn thiên nhiên với rừng, suối và đường bờ biển đẹp, nơi "
        "sinh sống của nhiều loài động vật quý. Đây cũng là điểm ngắm toàn cảnh vịnh Đà Nẵng.",
        "Đà Nẵng", 16.12049, 108.26471, 2400, 13.5, "photo-1686766219304-5e2fb0df9d2d",
    ),
    (
        "ba-na-hills", "Bà Nà Hills",
        "Làng Pháp trên đỉnh núi",
        "Đi cáp treo lên Bà Nà và bước trên Cầu Vàng",
        "Bà Nà Hills là khu du lịch trên núi Bà Nà, nổi tiếng với hệ thống cáp treo và Cầu Vàng "
        "– cây cầu bộ hành được nâng đỡ bởi đôi bàn tay đá khổng lồ.",
        "Đà Nẵng", 15.99586, 107.98907, 3600, 14.0, "photo-1602646993875-70bc0ba52c87",
    ),
    (
        "lang-da-non-nuoc", "Làng đá Non Nước",
        "Làng nghề điêu khắc đá dưới chân Ngũ Hành Sơn",
        "Xem đá cẩm thạch thành hình dưới tay nghệ nhân",
        "Làng đá Non Nước có lịch sử hơn 400 năm, nổi tiếng với nghề điêu khắc đá mỹ nghệ. Các "
        "sản phẩm từ đá cẩm thạch của làng được bày bán dọc tuyến đường Huyền Trân Công Chúa.",
        "Đà Nẵng", 15.98947, 108.24993, 1200, 15.0, "photo-1627105735288-bf4bd9b62538",
    ),
    # ── QUẢNG NAM ──────────────────────────────────────────────────────
    (
        "pho-co-hoi-an", "Phố cổ Hội An",
        "Đô thị cổ bên dòng sông Hoài",
        "Đi giữa phố đèn lồng khi Hội An lên đèn",
        "Phố cổ Hội An là thương cảng sầm uất thế kỷ 16–18, được UNESCO công nhận là Di sản Văn "
        "hóa Thế giới năm 1999. Nơi đây diễn ra Tết Nguyên Tiêu, Tết Trung Thu cùng nhiều lễ "
        "hội, nghi lễ truyền thống tại các hội quán, đình, miếu.",
        "Quảng Nam", 15.87713, 108.32866, 3600, 15.5, "photo-1722706202511-8743d7b34794",
    ),
    (
        "lang-gom-thanh-ha", "Làng gốm Thanh Hà",
        "Làng gốm hơn 500 năm bên sông Thu Bồn",
        "Xoay bàn xoay gốm cùng nghệ nhân Thanh Hà",
        "Làng gốm Thanh Hà hình thành từ thế kỷ 16, nổi tiếng với gốm mộc nung bằng củi. Hằng "
        "năm, làng tổ chức lễ Giỗ Tổ nghề gốm để tưởng nhớ những người khai sinh nghề.",
        "Quảng Nam", 15.88326, 108.33147, 1200, 15.0, "photo-1617593012528-f3e46fb01f28",
    ),
    (
        "thanh-dia-my-son", "Thánh địa Mỹ Sơn",
        "Đền tháp của vương quốc Champa",
        "Lạc vào thung lũng đền tháp Chăm giữa núi rừng",
        "Thánh địa Mỹ Sơn là quần thể đền tháp Ấn Độ giáo của vương quốc Champa, được xây dựng "
        "từ thế kỷ 4 đến thế kỷ 14. Di tích được UNESCO công nhận là Di sản Văn hóa Thế giới "
        "năm 1999.",
        "Quảng Nam", 15.76552, 108.12345, 3000, 14.0, "photo-1692470909373-a1e957c0c575",
    ),
]

# The source catalogue groups places by festival linkage; kept for traceability.
FESTIVAL_NOTES = {
    "dien-hon-chen": "Lễ hội Điện Huệ Nam; các lễ rước và nghi lễ tín ngưỡng gắn với điện",
    "lang-sinh": "Hội vật Làng Sình (tranh dân gian Làng Sình là di sản nghề, không phải lễ hội)",
    "cau-ngoi-thanh-toan": "Hoạt động lễ hội, văn hóa dân gian tại không gian Thanh Toàn",
    "ngu-hanh-son": "Lễ hội Quán Thế Âm – Ngũ Hành Sơn",
    "dinh-lang-tuy-loan": "Lễ hội đình làng Túy Loan; tế Xuân; tế Thu; rước sắc; cầu an",
    "dinh-lang-nam-o": "Lễ Cầu Ngư Nam Ô và các nghi lễ tín ngưỡng biển",
    "pho-co-hoi-an": "Tết Nguyên Tiêu; Tết Trung Thu; hoạt động đêm phố cổ và lễ hội tại hội quán, đình, miếu",
    "lang-gom-thanh-ha": "Giỗ Tổ nghề gốm Thanh Hà",
}


def main() -> None:
    env = load_env()
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=env.get("POSTGRES_DB", DB_NAME),
        user=env.get("POSTGRES_USER", DB_USER),
        password=env.get("POSTGRES_PASSWORD", ""),
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT code, id FROM language WHERE code IN ('vi', 'en')")
    langs = dict(cur.fetchall())
    if "vi" not in langs or "en" not in langs:
        raise RuntimeError("language table must contain 'vi' and 'en' rows")

    inserted = updated = 0
    for row in PLACES:
        (slug, title, tagline, headline, description, region,
         lat, lng, duration, zoom, photo) = row
        card = img(photo, 800, 600)
        splash = img(photo, 1600, 900)

        cur.execute("SELECT id FROM heritage WHERE slug = %s", (slug,))
        found = cur.fetchone()
        if found:
            cur.execute(
                """
                UPDATE heritage SET title=%s, tagline=%s, headline=%s, description=%s,
                       region=%s, lat=%s, lng=%s, duration_seconds=%s, map_zoom=%s,
                       card_image_url=%s, splash_image_url=%s, display_map=true,
                       publish_state='published',
                       publish_date=COALESCE(publish_date, CURRENT_DATE),
                       updated_at=now()
                WHERE id=%s
                """,
                (title, tagline, headline, description, region, lat, lng, duration, zoom,
                 card, splash, found[0]),
            )
            updated += 1
        else:
            cur.execute(
                """
                INSERT INTO heritage
                    (slug, title, tagline, headline, description, region, lat, lng,
                     map_zoom, duration_seconds, launch_date, publish_state, publish_date,
                     card_image_url, splash_image_url, hover_video_url,
                     community_made, display_map, presented_by_logo_url,
                     language1_id, language2_id, created_at, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, 'published',
                     CURRENT_DATE, %s, %s, NULL, false, true, NULL, %s, %s, now(), now())
                """,
                (slug, title, tagline, headline, description, region, lat, lng, zoom,
                 duration, card, splash, langs["vi"], langs["en"]),
            )
            inserted += 1

    conn.commit()

    cur.execute("SELECT count(*) FROM heritage WHERE publish_state = 'published'")
    published = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM heritage")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()

    print(f"Seed complete: +{inserted} inserted, {updated} updated")
    print(f"heritage total={total}, published={published}")
    print(f"festival-linked places documented: {len(FESTIVAL_NOTES)}")


if __name__ == "__main__":
    main()
