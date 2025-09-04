#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build context for the Jira Importer build system.

Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Type, TypeVar

T = TypeVar('T')


class BuildContext:
    def __init__(self, interface, profile: str = ""):
        self.interface = interface
        self.root_path = Path.cwd()
        self.cfg_dir = Path(os.getenv("BUILD_CFG_DIR", self.root_path / "build/configs"))
        self.build_dir = Path(os.getenv("BUILD_DIR", self.root_path / "build/"))

        if profile:
            self.profile = profile
        else:
            self.profile = os.getenv("BUILD_PROFILE", "dev")
        self.platform_tag = self._platform_tag()

        print(f"profile -> {self.profile}")

        self._load_config()

        self.files_cfg = self.cfg.get("files", {})
        self.pyinstaller_cfg = self.cfg.get("pyinstaller", {})

    def get_cfg(self, key: str, default: Optional[T] = None, expected_type: Optional[Type[T]] = None) -> Optional[T]:
        if 'metadata' in self.cfg:
            value: Any = self._get_nested_value(key)
        else:
            value = self.cfg.get(key, default)
        if value is None:
            return default
        if expected_type is not None and not isinstance(value, expected_type):
            raise TypeError(
                f"Config key '{key}' expected {expected_type.__name__}, got {type(value).__name__}"
            )

        return value  # type: ignore[return-value]

    def include_file(self, path: str) -> str:
        if os.path.exists(path):
            return path
        raise FileNotFoundError(f"Missing file: {path}")

    def _load_config(self) -> None:
        base_path      = Path(os.getenv("BUILD_CFG_BASE",      self.cfg_dir / "base.json"))
        profiles_path  = Path(os.getenv("BUILD_CFG_PROFILES",  self.cfg_dir / "profiles.json"))
        platforms_path = Path(os.getenv("BUILD_CFG_PLATFORMS", self.cfg_dir / "platforms.json"))

        base      = self._read_json(base_path)
        profiles  = self._read_json(profiles_path)
        platforms = self._read_json(platforms_path)

        plat_key = self.platform_tag

        # Validate profile exists
        if self.profile not in profiles:
            raise ValueError(f"Unknown profile: {self.profile}. Available profiles: {list(profiles.keys())}")

        cfg = self._deep_merge(base, profiles[self.profile])
        cfg = self._deep_merge(cfg, platforms.get(plat_key, {}))

        # Validate required configuration keys
        self._validate_config(cfg)

        self.cfg = cfg

    def _validate_config(self, cfg: dict) -> None:
        """Validate that required configuration keys exist."""
        required_keys = [
            "directories",
            "files",
            "build_options",
            "pyinstaller"
        ]

        missing_keys = []
        for key in required_keys:
            if key not in cfg:
                missing_keys.append(key)

        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {missing_keys}")

        # Validate nested required keys
        if "directories" in cfg:
            required_dirs = ["dist", "temp", "source"]
            missing_dirs = [d for d in required_dirs if d not in cfg["directories"]]
            if missing_dirs:
                raise ValueError(f"Missing required directory configurations: {missing_dirs}")

        if "pyinstaller" in cfg:
            required_pyi = ["name"]
            missing_pyi = [p for p in required_pyi if p not in cfg["pyinstaller"]]
            if missing_pyi:
                raise ValueError(f"Missing required PyInstaller configurations: {missing_pyi}")

    def _get_nested_value(self, key) -> Any:
        keys = key.split('.')
        current = self.cfg
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current

    def _platform_tag(self) -> str:
        """Detect the current OS platform as one of: windows, macos, linux, other."""
        try:
            platform_key = sys.platform
            if platform_key.startswith("win"):
                return "windows"
            if platform_key == "darwin":
                return "macos"
            if platform_key.startswith("linux"):
                return "linux"
            return platform_key
        except Exception:
            return "other"

    def _read_json(self, path: Path) -> dict:
        if not path.is_file():
            raise FileNotFoundError(f"Missing config: {path}")
        with path.open("r", encoding="utf-8") as f:
            content = f.read()
            content = os.path.expandvars(content)
            return json.loads(content)

    def _deep_merge(self,a: dict, b: Mapping) -> dict:
        """Return a := a U b (b overrides). Shallow lists are overwritten."""
        out = dict(a)
        for k, v in b.items():
            if isinstance(v, Mapping) and isinstance(out.get(k), Mapping):
                out[k] = self._deep_merge(out[k], v)  # type: ignore[arg-type]
            else:
                out[k] = v
        return out
