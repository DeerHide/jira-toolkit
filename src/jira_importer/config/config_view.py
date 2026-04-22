"""description: ConfigView: typed accessor for config (validation lists, skip flags, toggles).

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_MISSING = object()


class ConfigView:
    """Small duck-typed wrapper that supports .get("a.b.c", default).

    Works with:
      - dict-like configs
      - objects exposing get(key, default) or get_value(key, default)
      - objects with attribute paths
    """

    def __init__(self, cfg: Any) -> None:
        """Initialize the ConfigView class."""
        self._cfg = cfg

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Get a value from the configuration."""
        # 1) direct dict lookup with dotted key
        if isinstance(self._cfg, Mapping) and dotted_key in self._cfg:
            return self._cfg.get(dotted_key, default)

        # 2) delegated getters
        for meth in ("get", "get_value"):
            val = self._call_delegated_getter(meth, dotted_key)
            if val is not _MISSING:
                return val

        # 3) walk attributes / nested dicts
        cur: Any = self._cfg
        for part in dotted_key.split("."):
            if isinstance(cur, Mapping):
                if part in cur:
                    cur = cur[part]
                    continue
                return default
            # attribute
            if hasattr(cur, part):
                cur = getattr(cur, part)
            else:
                return default
        return cur

    def _call_delegated_getter(self, method_name: str, dotted_key: str) -> Any:
        """Attempt a delegated getter call and return _MISSING on lookup miss/failure.

        Uses a sentinel default to distinguish "missing key" from a valid falsy value.
        """
        fn = getattr(self._cfg, method_name, None)
        if not callable(fn):
            return _MISSING

        try:
            # Prefer a default-aware call so missing keys can be identified deterministically.
            if method_name == "get_value":
                return fn(dotted_key, default=_MISSING)
            return fn(dotted_key, _MISSING)
        except TypeError:
            # Some getters do not accept a default argument.
            pass
        except Exception:
            return _MISSING

        try:
            val = fn(dotted_key)
            # Historical compatibility: legacy delegated getters that return None for
            # "not found" should continue to fall through to nested traversal/default.
            return _MISSING if val is None else val
        except Exception:
            return _MISSING

    @property
    def version(self) -> str:
        """Get the version from the configuration."""
        # TODO: Delete this property once the version is removed from the configuration
        v = self.get("app.version", "") or getattr(self._cfg, "version", "")
        return str(v) if v is not None else ""
