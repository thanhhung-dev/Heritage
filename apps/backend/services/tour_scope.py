"""Server-owned tour boundaries. No HTTP, database or model dependencies."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def normalized(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold().replace("đ", "d"))
    text = "".join(char for char in text if unicodedata.category(char) not in {"Mn", "Cf"})
    return " ".join(re.findall(r"[a-z0-9]+", text))


@dataclass(frozen=True)
class TourArea:
    id: str
    title: str
    slugs: tuple[str, ...]
    names: tuple[str, ...]

    def questions(self) -> list[str]:
        return [f"Giới thiệu tổng quan về {self.title}.",
                f"Lịch sử hình thành {self.title} như thế nào?",
                f"Kiến trúc của {self.title} có gì đặc sắc?"]


AREAS = (
    TourArea("lang-tu-duc", "Lăng Tự Đức",
             ("lang-tu-duc", "khiem-lang", "tu-duc-tomb"),
             ("Lăng Tự Đức", "Khiêm Lăng", "Khiêm Cung", "Vạn Niên Cơ", "Tu Duc Tomb")),
    TourArea("lang-minh-mang", "Lăng Minh Mạng",
             ("lang-minh-mang", "minh-mang-tomb"),
             ("Lăng Minh Mạng", "Lăng Minh Mệnh", "Hiếu Lăng", "Minh Mang Tomb")),
    TourArea("dai-noi-hue", "Đại Nội Huế",
             ("dai-noi-hue", "forbidden-city", "imperial-city"),
             ("Đại Nội", "Hoàng thành Huế", "Hoàng thành Nhà Nguyễn", "Hue Imperial City", "Forbidden City")),
    TourArea("lang-khai-dinh", "Lăng Khải Định",
             ("lang-khai-dinh", "khai-dinh-tomb"),
             ("Lăng Khải Định", "Ứng Lăng", "Khai Dinh Tomb")),
    TourArea("chua-thien-mu", "Chùa Thiên Mụ",
             ("chua-thien-mu", "thien-mu-pagoda"),
             ("Chùa Thiên Mụ", "Chùa Linh Mụ", "Thien Mu Pagoda")),
    TourArea("cung-an-dinh", "Cung An Định",
             ("cung-an-dinh",),
             ("Cung An Định", "An Định")),
)

def resolve_area(value: str) -> TourArea:
    if not isinstance(value, str):
        raise ValueError("active_area_id phải là text.")
    key = normalized(value)
    for area in AREAS:
        if key in {normalized(name) for name in (area.id, *area.slugs, *area.names)}:
            return area
    raise ValueError("Khu vực hướng dẫn chưa được hỗ trợ.")


def scoped_refusal(area: TourArea, destination: TourArea | None = None) -> str:
    if destination:
        return (
            f"Mình đang ở {area.title} với bạn, chưa kể được {destination.title}. "
            "Muốn xem nơi đó thì mở tour của nó."
        )
    return (
        f"Câu này mình không có tư liệu để trả lời. "
        f"Mình đang ở {area.title} với bạn. Hỏi một chi tiết của nơi này thì mình kể được."
    )


def scoped_missing(area: TourArea) -> str:
    return f"Mình chưa có tư liệu đủ về {area.title} cho chi tiết này."


def allowed_output(text: str) -> bool:
    return not re.search(
        r"https?://|/content/|/tapestry/|\[[^\]]*\]\s*\(|<a\b", text, re.I,
    )

def referenced_areas(text: str, *, exclude: str | None = None) -> list[TourArea]:
    value = f" {normalized(text)} "
    matches = []
    for area in AREAS:
        if area.id == exclude:
            continue
        if any(f" {normalized(name)} " in value for name in (area.id, *area.slugs, *area.names)):
            matches.append(area)
    return matches


def question_outside_area(text: str, area: TourArea) -> TourArea | None:
    """Return one explicit destination; comparisons remain evidence-gated in-area questions."""
    destinations = referenced_areas(text, exclude=area.id)
    if len(destinations) != 1:
        return None
    value = normalized(text)
    relation = re.search(r"\b(lien quan|quan he|so sanh|khac nhau|giong nhau)\b", value)
    active_named = any(
        f" {normalized(name)} " in f" {value} " for name in (area.id, *area.slugs, *area.names)
    )
    return None if relation or active_named else destinations[0]


def allowed_tour_output(
    text: str, answer_type: str, area: TourArea, *, destination: TourArea | None = None,
) -> bool:
    if (not allowed_output(text)
            or re.search(r"\[?\s*passage\b|\bnguồn\s*:|[\u3400-\u9fff]", text, re.I)):
        return False
    if answer_type != "out_of_scope":
        return True
    value = normalized(text)
    if re.search(r"\b(?:1[0-9]{3}|20[0-9]{2})\b", text) or re.search(r"\d{3,}", value):
        return False
    mentioned = referenced_areas(text, exclude=area.id)
    if any(destination is None or item.id != destination.id for item in mentioned):
        return False
    if re.search(r"\b(xay|thanh lap|tri vi|lang vua|nam sinh|nam mat)\b", value):
        return False
    # "lịch sử/kiến trúc" trong lời mời thì giữ; gắn với nơi khác thì là dữ kiện.
    if mentioned and re.search(r"\b(kien truc|lich su)\b", value):
        return False
    return True


def follow_up_questions(
    values: list[str], area: TourArea, *, fallback: bool = True,
    focus_names: tuple[str, ...] = (), fallback_questions: list[str] | None = None,
) -> list[str]:
    accepted = []
    required_names = focus_names or area.names
    for question in values:
        if (len(question) <= 200 and allowed_output(question)
                and any(f" {normalized(name)} " in f" {normalized(question)} " for name in required_names)
                and question not in accepted):
            accepted.append(question)
    if accepted:
        return accepted[:3]
    defaults = fallback_questions if fallback_questions is not None else area.questions()
    return defaults[:3] if fallback else []


def area_system_policy(area: TourArea, *, artifact_title: str | None = None) -> str:
    policy = (
        f"\n\nPhạm vi do máy chủ ấn định: {area.title} (active_area_id={area.id}). "
        "Tập trung vào địa điểm này. Hỏi rõ sang địa điểm khác thì out_of_scope "
        "và chỉ nhắc tên nơi đó, không kể dữ kiện. "
        "Chủ đề không thuộc di sản này cũng là out_of_scope, dù nguồn có Passage của khu này. "
        "Thiếu Passage không phải out_of_scope."
        "\nChỉ trả answered khi Passage hỗ trợ trực tiếp ít nhất một phần điều đang hỏi, "
        "và trích source_ids tương ứng. Có tư liệu cùng chủ đề không có nghĩa là đủ để trả lời. "
        "Nếu không có bằng chứng cho điều đang hỏi thì insufficient_evidence. "
        "Không tự bổ sung dữ kiện ngoài Passage."
    )
    if artifact_title:
        policy += (
            f"\nCổ vật đang chọn: {artifact_title}. Chỉ kể dữ kiện Passage có về cổ vật này. "
            "Hỏi cổ vật khác thì out_of_scope, không kể dữ kiện về cổ vật đó."
        )
    return policy
