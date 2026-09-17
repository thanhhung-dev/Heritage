#!/usr/bin/env python3
"""Extract address candidates từ Wikipedia text cho place entities.

Usage:
    python scripts/extract_address.py

Output:
    corpus/address_candidates.json - danh sách candidates để review thủ công

Sau khi review, dùng scripts/import_address_candidates.py để import vào DB.
"""
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

# Tên thành phố/tỉnh - dùng để tránh bắt nhầm "đường Huế"
PROVINCE_NAMES = frozenset({
    'huế', 'hue', 'thừa thiên huế',
    'đà nẵng', 'da nang',
    'hà nội', 'ha noi',
    'hồ chí minh', 'ho chi minh', 'sài gòn',
    'quảng nam', 'quảng trị', 'quảng bình', 'quảng ngãi',
    'thanh hóa', 'nghệ an', 'khánh hòa', 'bình thuận',
    'lâm đồng', 'gia lai', 'đắk lắk',
})


def _normalize(text: str) -> str:
    """Bỏ dấu + lowercase để so sánh."""
    decomposed = unicodedata.normalize('NFD', unicodedata.normalize('NFC', text).lower())
    return ''.join(c for c in decomposed if not unicodedata.combining(c)).replace('đ', 'd')


# Regex: stop at dấu câu (., ; , ) ( ) và newline
_NAME_RE = r'([A-ZÀ-ỹ][^\s.,;()\n]+(?:\s+[A-ZÀ-ỹ][^\s.,;()\n]+)*)'

STREET_RE = re.compile(
    r'(?:đường|phố)\s+' + _NAME_RE, re.IGNORECASE,
)
NUMBER_STREET_RE = re.compile(
    r'số\s+(\d+)\s+(?:đường|phố)\s+' + _NAME_RE, re.IGNORECASE,
)
WARD_RE = re.compile(
    r'(?:phường|P\.)\s+' + _NAME_RE, re.IGNORECASE,
)
DISTRICT_RE = re.compile(
    r'(?:quận|huyện)\s+' + _NAME_RE, re.IGNORECASE,
)
PROVINCE_RE = re.compile(
    r'(?:thành phố|tỉnh|TP\.?|Tp\.?)\s+' + _NAME_RE, re.IGNORECASE,
)


def _is_province_name(text: str) -> bool:
    """Check nếu text là tên tỉnh/thành phố (không phải tên đường)."""
    norm = _normalize(text)
    return norm in PROVINCE_NAMES or any(norm.startswith(p) for p in PROVINCE_NAMES)


def extract_components(text: str) -> dict[str, str | None]:
    """Parse address components từ text."""
    street = None
    ward = None
    district = None
    province = None

    # Number + street (ưu tiên: "số 156 Trần Phú")
    num_match = NUMBER_STREET_RE.search(text)
    if num_match:
        street_name = num_match.group(2)
        if not _is_province_name(street_name):
            street = f"{num_match.group(1)} {street_name}"

    # Street without number
    if not street:
        street_match = STREET_RE.search(text)
        if street_match:
            street_name = street_match.group(1)
            if not _is_province_name(street_name):
                street = street_name

    # Ward
    ward_match = WARD_RE.search(text)
    if ward_match:
        ward = ward_match.group(1)

    # District
    district_match = DISTRICT_RE.search(text)
    if district_match:
        district = district_match.group(1)

    # Province
    province_match = PROVINCE_RE.search(text)
    if province_match:
        province = province_match.group(1)

    return {
        'street': street,
        'ward': ward,
        'district': district,
        'province': province,
    }


def find_address_segments(text: str) -> list[str]:
    """Tìm các câu có chứa address info (tối đa 3 câu)."""
    # Chia theo câu (dấu . ! ? theo sau bởi space hoặc end of string)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    segments = []

    for sent in sentences:
        # Pattern 1: "phường X" hoặc "P. X" (viết tắt phường)
        if re.search(r'(?:phường|P\.)\s+[A-ZÀ-ỹ]', sent, re.I):
            clean = sent.strip()
            if len(clean) > 20:
                segments.append(clean)
                continue

        # Pattern 2: "đường X" + tên riêng (không phải tên thành phố)
        if re.search(r'(?:đường|phố)\s+[A-ZÀ-ỹ]', sent, re.I):
            clean = sent.strip()
            if len(clean) > 20:
                segments.append(clean)
                continue

        # Pattern 3: "số X đường Y"
        if re.search(r'số\s+\d+\s+(?:đường|phố)', sent, re.I):
            clean = sent.strip()
            if len(clean) > 20:
                segments.append(clean)
                continue

        # Pattern 4: "thuộc phường/xã/thôn Y"
        if re.search(r'thuộc\s+(?:phường|xã|thôn|làng|quận|huyện)\s+[A-ZÀ-ỹ]', sent, re.I):
            clean = sent.strip()
            if len(clean) > 20:
                segments.append(clean)

    return segments[:3]  # Max 3 segments per entity


def calculate_confidence(components: dict[str, str | None]) -> float:
    """Tính confidence score dựa trên số components có được.

    Scale:
    - Street với số nhà (vd: "156 Trần Phú"): +0.45
    - Street không có số (vd: "Trần Phú"): +0.35
    - Ward: +0.30
    - District: +0.15
    - Province: +0.10
    """
    score = 0.0

    # Street
    if components['street']:
        # Check nếu có số nhà
        if re.match(r'\d+\s+', components['street']):
            score += 0.45
        else:
            score += 0.35

    # Ward
    if components['ward']:
        score += 0.30

    # District
    if components['district']:
        score += 0.15

    # Province
    if components['province']:
        score += 0.10

    return min(score, 1.0)


def extract_from_wiki_file(entity_name: str, wiki_path: Path, source_url: str) -> dict[str, Any] | None:
    """Extract address từ 1 wiki file."""
    if not wiki_path.exists():
        return None

    text = wiki_path.read_text(encoding='utf-8')

    # Tìm segments có address
    segments = find_address_segments(text)
    if not segments:
        return None

    # Extract components từ từng segment, ưu tiên segment có nhiều info nhất
    best_components = {'street': None, 'ward': None, 'district': None, 'province': None}
    best_score = 0.0

    for seg in segments:
        components = extract_components(seg)
        score = calculate_confidence(components)
        if score > best_score:
            best_components = components
            best_score = score

    # Cần ít nhất ward để có giá trị (street không đủ vì có thể là đường chung chung)
    if not best_components['ward']:
        return None

    # Build address string
    parts = []
    if best_components['street']:
        if re.match(r'\d+\s+', best_components['street']):
            parts.append(f"số {best_components['street']}")
        else:
            parts.append(f"đường {best_components['street']}")
    if best_components['ward']:
        parts.append(f"phường {best_components['ward']}")

    address = ', '.join(parts)

    # Source sentence (đoạn gốc từ wiki, max 500 chars)
    source_sentence = segments[0][:500]

    return {
        'entity_name': entity_name,
        'address': address,
        'street': best_components['street'],
        'ward': best_components['ward'],
        'district': best_components['district'],
        'province': best_components['province'],
        'source_url': source_url,
        'source_sentence': source_sentence,
        'confidence': best_score,
        'review_status': 'pending',
    }


def main():
    # Load index
    index_path = Path('corpus/locations_index.json')
    data = json.loads(index_path.read_text())
    index = data['success']

    # Filter place entities
    place_entities = [
        e for e in index
        if e['category'] in ('Danh thắng', 'Di tích lịch sử', 'Làng nghề')
    ]

    print(f"Processing {len(place_entities)} place entities...")
    print()

    candidates = []
    wiki_dir = Path('corpus/wiki_by_location')

    for entity in place_entities:
        name = entity['name']
        file = entity['file']
        url = entity.get('url', '')

        wiki_path = wiki_dir / file
        result = extract_from_wiki_file(name, wiki_path, url)

        if result:
            candidates.append(result)
            print(f"✓ {name}")
            print(f"  Address: {result['address']}")
            print(f"  Ward: {result['ward']}, District: {result['district']}, Province: {result['province']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print()
        else:
            print(f"✗ {name} (no address found)")

    # Save candidates
    output_path = Path('corpus/address_candidates.json')
    output_path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2))

    print()
    print(f"Saved {len(candidates)} candidates to {output_path}")
    print()
    print("Next steps:")
    print("1. Review corpus/address_candidates.json")
    print("2. Set review_status to 'approved' for valid entries")
    print("3. Run: python scripts/import_address_candidates.py")


if __name__ == '__main__':
    main()
