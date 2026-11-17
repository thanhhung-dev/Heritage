"""Compatibility exports; all routers share the active security implementation."""
from apps.backend.core.security import (  # noqa: F401
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    bearer_scheme,
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    ph,
    require_admin,
    verify_password,
)
