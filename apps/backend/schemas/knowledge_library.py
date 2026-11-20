"""Stable admin library HTTP DTOs; never expose SDK/ORM responses."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class UploadRequest(RequestDTO):
    folder: str = Field(max_length=1024)
    filename: str = Field(min_length=1, max_length=255)
    contentType: str = Field(max_length=64)
    size: int = Field(gt=0)


class KeyRequest(RequestDTO):
    key: str = Field(min_length=1, max_length=1024)


class FolderRequest(RequestDTO):
    parentPrefix: str = Field(max_length=1024)
    folderName: str = Field(min_length=1, max_length=255)


class FolderOut(BaseModel):
    name: str
    prefix: str


class ListedFile(BaseModel):
    name: str
    key: str
    size: int
    lastModified: datetime


class ListingOut(BaseModel):
    bucket: Literal["knowledge-heritage"]
    prefix: str
    folders: list[FolderOut]
    files: list[ListedFile]
    nextContinuationToken: str | None


class ObjectOut(ListedFile):
    bucket: Literal["knowledge-heritage"]
    contentType: str
    etag: str
    metadata: dict[str, str]


class UploadOut(BaseModel):
    uploadId: str
    objectKey: str
    uploadUrl: str
    method: Literal["PUT"] = "PUT"
    expiresIn: int
    sessionExpiresAt: datetime
    requiredHeaders: dict[str, str]


class CompleteOut(BaseModel):
    uploadId: str
    status: Literal["stored"] = "stored"
    object: ObjectOut


class DownloadOut(BaseModel):
    key: str
    downloadUrl: str
    expiresIn: int


class PreviewOut(BaseModel):
    key: str
    content: str
    contentType: Literal["text/plain; charset=utf-8"] = "text/plain; charset=utf-8"
    size: int
    etag: str
