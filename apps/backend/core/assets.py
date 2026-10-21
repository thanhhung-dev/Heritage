"""Cloudflare R2 asset URL policy (Story 4, task 4.6).

The database stores asset references as-is — either full URLs or relative
object keys (see schema.sql comment "URL CDN, KHÔNG lưu blob"). This module
normalizes them at the API boundary:

* relative keys are prefixed with the configured R2 public base URL;
* absolute URLs pass through unchanged, optionally restricted to an allowlist
  of asset hosts when one is configured.

R2 URLs never leak into ORM mappings and the database is untouched — the
policy is only applied while building API responses.
"""
from __future__ import annotations

from urllib.parse import urlsplit

_ABSOLUTE_SCHEMES = frozenset({"http", "https"})


class AssetUrlPolicy:
    """Turn raw DB asset references into browser-usable URLs."""

    def __init__(
        self,
        base_url: str | None = None,
        allowed_hosts: tuple[str, ...] = (),
    ) -> None:
        self.base_url: str | None = base_url.rstrip("/") if base_url else None
        self.allowed_hosts = frozenset(host.lower() for host in allowed_hosts if host)

    def resolve(self, url: str | None) -> str | None:
        if not url:
            return None

        parsed = urlsplit(url)
        if parsed.scheme in _ABSOLUTE_SCHEMES:
            if self.allowed_hosts and parsed.netloc.lower() not in self.allowed_hosts:
                return None
            return url

        if self.base_url is None:
            # No R2 base configured — leave relative references untouched.
            return url

        return f"{self.base_url}/{url.lstrip('/')}"


_policy = AssetUrlPolicy()


def configure_asset_policy(
    base_url: str | None = None,
    allowed_hosts: tuple[str, ...] = (),
) -> AssetUrlPolicy:
    """Install the process-wide asset URL policy during application startup."""
    global _policy
    _policy = AssetUrlPolicy(base_url, allowed_hosts)
    return _policy


def asset_policy() -> AssetUrlPolicy:
    """Return the currently configured asset URL policy."""
    return _policy
