"""description: ConfigView: typed accessor for config (validation lists, skip flags, toggles).

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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
            fn = getattr(self._cfg, meth, None)
            if callable(fn):
                try:
                    val = fn(dotted_key, default=default) if meth == "get_value" else fn(dotted_key, default)
                    if val is not None:
                        return val
                except TypeError:
                    # some get() may not accept default kwarg
                    try:
                        val = fn(dotted_key)
                        return val if val is not None else default
                    except Exception:
                        pass
                except Exception:
                    pass

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

    @property
    def version(self) -> str:
        """Get the version from the configuration."""
        # TODO: Delete this property once the version is removed from the configuration
        v = self.get("app.version", "") or getattr(self._cfg, "version", "")
        return str(v) if v is not None else ""
