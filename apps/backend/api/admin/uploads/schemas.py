"""Upload and file replacement inputs."""
from uuid import UUID

from pydantic import Field

from apps.backend.common.schemas.admin import AdminInput


class UploadCreate(AdminInput):
    parent_prefix: str = Field(max_length=1024)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(max_length=64)
    size_bytes: int = Field(gt=0, strict=True)
    document_id: UUID | None = None
