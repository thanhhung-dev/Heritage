"""Custom SQLAlchemy type decorators matching schema.sql domain definitions."""
from __future__ import annotations

from typing import Any

from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION, JSONB
from sqlalchemy.types import TypeDecorator


class Vec3(TypeDecorator):
    """DOUBLE PRECISION[3] — CHECK (array_length(VALUE,1)=3) (schema.sql DOMAIN vec3).

    Returned as a Python list from DB; bind param validates 3-element length.
    """
    impl = DOUBLE_PRECISION
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(ARRAY(self.impl, dimensions=1))

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if len(value) != 3:
            raise ValueError("vec3 must have exactly 3 elements")
        return list(value)

    def process_result_value(self, value: Any, dialect):
        return value


class JsonB(JSONB):
    """JSONB alias for clarity (scene.transform_7dof, chat_message.citations, ...)."""
    cache_ok = True
