"""Validated writes using the viewer's camera field names and vector formats."""
from typing import Annotated
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from apps.backend.schemas.admin_scene import SceneId
from apps.backend.schemas.heritage import CameraOut, ModelAssetOut, SkyPresetOut

Coordinate = Annotated[float, Field(strict=True, ge=-1_000_000, le=1_000_000, allow_inf_nan=False)]


class VectorObject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: Coordinate
    y: Coordinate
    z: Coordinate


Vector = Annotated[list[Coordinate], Field(min_length=3, max_length=3)] | VectorObject


def safe_asset_reference(value: str) -> str:
    if (not value or value != value.strip() or len(value) > 2048
            or any(ord(c) < 32 or ord(c) == 127 for c in value) or "\\" in value):
        raise ValueError("Invalid asset reference")
    try:
        parsed = urlsplit(value)
        decoded = unquote(parsed.path)
        if (parsed.scheme not in {"", "http", "https"} or parsed.username or parsed.password
                or parsed.query or parsed.fragment or (parsed.scheme and not parsed.hostname)
                or (not parsed.scheme and (parsed.netloc or value.startswith("/")))
                or any(part in {".", "..", ""} for part in decoded.lstrip("/").split("/"))
                or "%" in decoded or "\\" in decoded or any(ord(c) < 32 for c in decoded)):
            raise ValueError("Unsafe asset path or URL")
    except ValueError:
        raise ValueError("Asset references must be safe object keys or HTTP(S) URLs without credentials/query/fragment") from None
    return value


class CameraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_name: str | None = Field(default=None, min_length=1, max_length=255)
    start_position: Vector | None = None
    start_target: Vector | None = None
    zoom_position: Vector | None = None
    zoom_target: Vector | None = None
    path_url: str | None = None
    instant_move: StrictBool = False

    @field_validator("path_url")
    @classmethod
    def safe_path(cls, value):
        return safe_asset_reference(value) if value is not None else None

    @model_validator(mode="after")
    def valid_poses(self):
        def xyz(vector):
            return [vector.x, vector.y, vector.z] if isinstance(vector, VectorObject) else vector
        for position, target in ((self.start_position, self.start_target), (self.zoom_position, self.zoom_target)):
            if (position is None) != (target is None):
                raise ValueError("Camera position and target must be supplied together")
            if position is not None and xyz(position) == xyz(target):
                raise ValueError("Camera position and target must be different")
        return self


class SceneConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    camera: CameraConfig
    sky_preset_id: SceneId | None = None
    model_asset_ids: list[SceneId] | None = Field(default=None, max_length=1000)

    @field_validator("model_asset_ids")
    @classmethod
    def unique_assets(cls, value):
        if value is not None and len(value) != len(set(value)):
            raise ValueError("model_asset_ids must be unique")
        return value


class SceneConfigOut(BaseModel):
    scene_id: int
    heritage_id: int
    camera: CameraOut
    sky_preset_id: int | None
    sky: SkyPresetOut | None
    models: list[ModelAssetOut]
