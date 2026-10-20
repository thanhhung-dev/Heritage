"""Inputs for local knowledge administration; reject unknown fields."""
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class FolderCreate(AdminInput):
    parent_prefix: str = Field(max_length=1024)
    name: str = Field(min_length=1, max_length=255)


class FolderRename(AdminInput):
    prefix: str = Field(max_length=1024)
    name: str = Field(min_length=1, max_length=255)


class UploadCreate(AdminInput):
    parent_prefix: str = Field(max_length=1024)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(max_length=64)
    size_bytes: int = Field(gt=0, strict=True)
    document_id: UUID | None = None


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
