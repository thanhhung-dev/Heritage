"""Validation policy shared by knowledge administration requests."""
from pydantic import BaseModel, ConfigDict


class AdminInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
