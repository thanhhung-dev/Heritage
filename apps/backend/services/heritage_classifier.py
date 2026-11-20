"""Conservative subject classification, never incidental-mention extraction."""
from dataclasses import dataclass, field
import math
import re
import unicodedata

from apps.backend.services.heritage_taxonomy import validate_categories


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower().replace("đ", "d").replace("Đ", "d"))
    return re.sub(r"\s+", " ", "".join(c for c in value if not unicodedata.combining(c))).strip()


@dataclass(frozen=True)
class ContentInput:
    title: str
    tagline: str = ""
    headline: str = ""
    description: str = ""
    entity_type_hint: str | None = None
    # Only independently reviewed structured data may supply a type hint.
    source_url: str | None = None
    reviewed_context: str = ""


@dataclass(frozen=True)
class Prediction:
    entity_type: str | None = None
    categories: tuple[str, ...] = ()
    primary_category: str | None = None
    confidence: float = 0.0
    reasoning_summary: str = "Insufficient subject evidence; editorial review required."
    classification_source: str = "rules"
    evidence: tuple[str, ...] = field(default_factory=tuple)


# Vocabulary describes kinds, never record IDs or individual site/slug lists.
SUBJECT_RULES = (
    (r"^(?:bao tang|museum)\b", "place", ("museum",)),
    (r"^(?:le hoi|festival|hoi lang)\b", "event", ("festival",)),
    (r"^(?:nghi le|nghi thuc|le te|ritual)\b", "practice", ("ritual",)),
    (r"^(?:nghe nhan|artisan)\b", "person", ("artisan",)),
    (r"^(?:nhan vat lich su|danh nhan|hoang de|vua|historical figure)\b", "person", ("historical_figure",)),
    (r"^(?:bo suu tap|collection)\b", "collection", ("artifact",)),
    (r"^(?:co vat|hien vat|bao vat|tuong dong|trong dong|binh gom|artifact)\b", "artifact", ("artifact",)),
    (r"^(?:nghe|ky thuat) (?:lam |det |gom|moc|duc |che tac|theu)", "practice", ("traditional_craft",)),
    (r"^(?:phong tuc|tap quan|truyen thong|community tradition)\b", "practice", ("community_tradition",)),
    (r"^(?:ca tru|dan ca|hat |mua |nghe thuat trinh dien)", "practice", ("intangible_heritage",)),
    (r"^(?:trai nghiem|cultural experience)\b", "practice", ("cultural_experience",)),
    (r"^(?:chua|den|dinh lang|thanh duong|nha tho|mieu|tu vien|pagoda|temple)\b", "place", ("religious_site", "architecture")),
    (r"^(?:cung|dai noi|hoang thanh|thanh noi|lang tam|lang vua|palace|citadel)\b", "place", ("architecture", "historical_site")),
    (r"^(?:nha guol|nha rong|nha co|cau|cong|thap)\b", "place", ("architecture",)),
    (r"^(?:danh thang|danh lam|quan the nui|quan the danh thang|khu danh thang|nui|hang dong|vuon quoc gia|bai bien|scenic landscape)\b", "place", ("scenic_landscape",)),
    (r"^(?:di tich lich su|chien truong|khu luu niem)\b", "place", ("historical_site",)),
)


def subject_rule(value: str):
    for expression, entity_type, categories in SUBJECT_RULES:
        if re.search(expression, normalize(value)):
            return entity_type, categories
    return None


def classify(content: ContentInput, *, semantic=None) -> Prediction:
    title = content.title.strip()
    evidence = title
    match = subject_rule(title)
    if match is None:
        # Only a definition of this exact subject may establish its nature.
        # "The museum stores artifacts" and subordinate festival references do
        # not become definitions of the containing place.
        for definition_text in (content.description, content.reviewed_context):
            definition = re.match(r"^\s*" + re.escape(title) + r"\s+(?:là|is)\s+(?:(?:một|an?|the)\s+)?([^.!?\n]{1,500})",
                                  definition_text, re.IGNORECASE)
            if definition:
                evidence = definition.group(0)
                match = subject_rule(definition.group(1))
                if match:
                    break
    if match is None:
        # Place descriptors and descriptors compatible with an independently
        # reviewed type hint can clarify an otherwise ambiguous proper name.
        for descriptor in (content.headline, content.tagline):
            proposed = subject_rule(descriptor)
            if proposed and (proposed[0] == "place" or proposed[0] == content.entity_type_hint):
                match, evidence = proposed, descriptor
                break
    if match is None and content.source_url and content.entity_type_hint in {"artifact", "collection"}:
        match, evidence = (content.entity_type_hint, ("artifact",)), "Reviewed artifact identity with explicit source URL"
    if match:
        kind, keys = match
        if content.entity_type_hint and content.entity_type_hint != kind:
            return Prediction(reasoning_summary="Subject evidence conflicts with the reviewed entity type hint.")
        keys = list(keys)
        # A place may also represent community tradition only with a subject
        # statement, not merely because a festival is held there.
        description = normalize(content.description)
        if (kind == "place" and keys == ["architecture"]
                and re.search(r"(?:khong gian|trung tam|bieu tuong) (?:sinh hoat |van hoa )?cong dong", description)):
            keys.append("community_tradition")
        validate_categories(kind, keys, keys[0])
        return Prediction(kind, tuple(keys), keys[0], 0.97, "Subject kind established by: " + evidence[:500],
                          "rules", (evidence[:500],))
    if semantic is not None:
        try:
            proposed = semantic(content)
            kind, keys, primary = proposed["entity_type"], proposed["categories"], proposed["primary_category"]
            validate_categories(kind, keys, primary)
            quoted = proposed["evidence"]
            confidence = proposed["confidence"]
            source = "\n".join((content.title, content.tagline, content.headline, content.description, content.reviewed_context))
            if (not isinstance(quoted, str) or not quoted.strip() or quoted not in source
                    or type(confidence) not in {int, float} or not math.isfinite(confidence)
                    or not 0 <= confidence <= 1):
                raise ValueError("Semantic result lacks valid literal evidence/confidence")
            # A model cannot promote an incidental non-place reference. An
            # independently reviewed hint is required when no subject rule exists.
            if kind != "place" and (not content.source_url or content.entity_type_hint != kind):
                raise ValueError("Non-place semantic result needs reviewed structured identity")
            if content.entity_type_hint and kind != content.entity_type_hint:
                raise ValueError("Conflicting semantic entity type")
            return Prediction(kind, tuple(keys), primary, min(float(confidence), 0.84),
                              "Semantic proposal requires review; evidence: " + quoted[:500], "semantic", (quoted[:500],))
        except (ValueError, TypeError, KeyError, RuntimeError):
            pass
    return Prediction()


def decision(prediction: Prediction, high: float = 0.9, medium: float = 0.55) -> str:
    if not 0 <= medium < high <= 1:
        raise ValueError("Require 0 <= medium < high <= 1")
    if not prediction.categories:
        return "unclassified"
    return "applied" if prediction.confidence >= high else "review" if prediction.confidence >= medium else "unclassified"
