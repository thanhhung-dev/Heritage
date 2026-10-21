"""Document metadata inputs."""
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator

from apps.backend.common.schemas.admin import AdminInput


class DocumentPatch(AdminInput):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    region: Literal['hue', 'da_nang'] | None = None
    source_type: Literal['official', 'academic', 'management', 'press', 'encyclopedia', 'other'] | None = None
    source_url: str | None = Field(default=None, max_length=2048)

    @field_validator('title')
    @classmethod
    def title_not_null(cls, value):
        if value is None:
            raise ValueError('title không được null.')
        return value

    @field_validator('source_url')
    @classmethod
    def citation_url(cls, value):
        if value is not None:
            parsed = urlsplit(value)
            if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
                    or parsed.username or parsed.password or parsed.query or parsed.fragment):
                raise ValueError('source_url phải là HTTP(S) URL không chứa credentials/query/fragment.')
        return value


class DocumentRegister(DocumentPatch):
    object_key: str = Field(min_length=1, max_length=1024)
