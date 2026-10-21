"""Folder administration inputs."""
from pydantic import Field

from apps.backend.common.schemas.admin import AdminInput


class FolderCreate(AdminInput):
    parent_prefix: str = Field(max_length=1024)
    name: str = Field(min_length=1, max_length=255)


class FolderRename(AdminInput):
    prefix: str = Field(max_length=1024)
    name: str = Field(min_length=1, max_length=255)
