"""Admin scene metadata and complete-order contracts; overview stays at -1."""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

SceneId = Annotated[int, Field(gt=0, lt=2**63, strict=True)]


class SceneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=250, pattern=r"^\S(?:.*\S)?$")
    description: str | None = Field(default=None, max_length=20000)
    sequence: int | None = Field(default=None, ge=-1, le=2**31 - 1, strict=True)


class SceneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=250, pattern=r"^\S(?:.*\S)?$")
    description: str | None = Field(default=None, max_length=20000)

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set or ("title" in self.model_fields_set and self.title is None):
            raise ValueError("Provide a non-null title or a description change")
        return self


class SceneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    heritage_id: int
    sequence: int
    title: str
    description: str | None


class SceneList(BaseModel):
    items: list[SceneOut]
    next_after_sequence: int | None


class SceneOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene_ids: list[SceneId] = Field(max_length=1000)
    expected_scene_ids: list[SceneId] = Field(max_length=1000)

    @model_validator(mode="after")
    def unique_ids(self):
        for ids in (self.scene_ids, self.expected_scene_ids):
            if len(ids) != len(set(ids)):
                raise ValueError("Scene IDs must be unique")
        return self
