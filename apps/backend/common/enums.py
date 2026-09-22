"""Shared DB enums derived from CHECK constraints in schema.sql.

Dùng Python enum thay vì raw string để mã nguồn tự document ràng buộc,
và để Pydantic validate trước khi query DB.
"""
from __future__ import annotations

from sqlalchemy import Enum


class RegionCode(str, Enum):
    hue = "hue"
    da_nang = "da_nang"


class EntityType(str, Enum):
    person = "person"
    place = "place"
    event = "event"
    artifact = "artifact"


class AliasType(str, Enum):
    official = "official"
    historical = "historical"
    common = "common"
    typo = "typo"


class AssetFormat(str, Enum):
    glb = "glb"
    gltf = "gltf"
    splat = "splat"
    sog = "sog"
    ply = "ply"


class CaptureMethod(str, Enum):
    photogrammetry = "photogrammetry"
    gaussian_splat_source = "gaussian_splat_source"
    drone_video = "drone_video"
    lidar = "lidar"


class SkyMode(str, Enum):
    midday = "midday"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class MediaType(str, Enum):
    image = "image"
    video = "video"
    audio = "audio"
    model = "model"


class VerificationStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    withdrawn = "withdrawn"
