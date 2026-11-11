"""Explicit document/passage metadata shared by package building and import."""
from __future__ import annotations

import re

from apps.backend.services.tour_scope import resolve_area

METADATA_FIELDS = (
    'content_type', 'heritage_slug', 'active_area_id', 'scene_id', 'scene_key', 'language',
)
_CONTENT_TYPES = {'tour_script', 'historical_source', 'editorial_note'}


def resolve_metadata(document: dict, passage: dict | None = None, *, text: str = '') -> dict:
    """Inherit explicit fields, reject conflicts, and never infer identity from text."""
    metadata = {}
    for source in (document, passage or {}):
        for field in METADATA_FIELDS:
            if field not in source:
                continue
            value = source[field]
            if field == 'scene_id':
                if type(value) is not int or not 0 < value < 2 ** 63:
                    raise ValueError('scene_id phải là số nguyên dương trong phạm vi int64.')
            elif not isinstance(value, str) or not value or len(value) > 80:
                raise ValueError(f'{field} phải là text không rỗng, tối đa 80 ký tự.')
            elif field == 'active_area_id':
                value = resolve_area(value).id
            elif field == 'content_type' and value not in _CONTENT_TYPES:
                raise ValueError('content_type phải là tour_script, historical_source hoặc editorial_note.')
            elif field == 'heritage_slug' and not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value):
                raise ValueError('heritage_slug không hợp lệ.')
            elif field == 'scene_key' and not re.fullmatch(r's(?:0|[1-9][0-9]*)', value):
                raise ValueError('scene_key phải có dạng s0, s1, ...; không suy ra từ tên audio.')
            elif field == 'language' and not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', value):
                raise ValueError('language phải là mã ngôn ngữ, ví dụ vi hoặc en-US.')
            if field in metadata and metadata[field] != value:
                raise ValueError(f'{field} của passage không khớp document.')
            metadata[field] = value

    # Recognize only a leading transcript declaration; do not parse/trust YAML
    # identities, inspect ordinary prose, or silently turn scripts into evidence.
    header = re.match(r'\A\ufeff?---[^\S\r\n]*\r?\n(.*?)(?:\r?\n---[^\S\r\n]*(?:\r?\n|$)|$)',
                      text, flags=re.S)
    if header and re.search(r'''(?m)^content_type:\s*["']?tour_script["']?\s*(?:\#.*)?$''', header[1]):
        if metadata.get('content_type') != 'tour_script':
            raise ValueError('content_type: tour_script trong header cần metadata JSON tour_script đầy đủ.')
    if metadata.get('content_type') == 'tour_script':
        missing = [field for field in METADATA_FIELDS if field not in metadata]
        if missing:
            raise ValueError('tour_script thiếu metadata JSON: ' + ', '.join(missing))
    if 'heritage_slug' in metadata and 'active_area_id' in metadata:
        if resolve_area(metadata['heritage_slug']).id != metadata['active_area_id']:
            raise ValueError('heritage_slug không thuộc active_area_id đã khai báo.')
    return metadata
