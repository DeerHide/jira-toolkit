"""
Build script for the Jira Importer application.

Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Type, TypeVar

T = TypeVar('T')

class BuildContext:
    def __init__(self, interface):
        self.interface = interface
        self.root_path = Path.cwd()
        self.cfg_dir = Path(os.getenv("BUILD_CFG_DIR", self.root_path / "build/configs"))
        self.build_dir = Path(os.getenv("BUILD_DIR", self.root_path / "build/"))

        self.profile = os.getenv("BUILD_PROFILE", "dev")

        self.platform_tag = self._platform_tag(interface.platform)
        self._load_config()

        self.files_cfg = self.cfg.get("files", {})
        self.pyinstaller_cfg = self.cfg.get("pyinstaller", {})

    def _load_config(self) -> None:
        base_path      = Path(os.getenv("BUILD_CFG_BASE",      self.cfg_dir / "base.json"))
        profiles_path  = Path(os.getenv("BUILD_CFG_PROFILES",  self.cfg_dir / "profiles.json"))
        platforms_path = Path(os.getenv("BUILD_CFG_PLATFORMS", self.cfg_dir / "platforms.json"))

        base      = self._read_json(base_path)
        profiles  = self._read_json(profiles_path)
        platforms = self._read_json(platforms_path)

        plat_key = self.platform_tag

        cfg = self._deep_merge(base, profiles[self.profile])
        cfg = self._deep_merge(cfg, platforms.get(plat_key, {}))
        self.cfg = cfg

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

    def _get_nested_value(self, key) -> Any:
        keys = key.split('.')
        current = self.cfg
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current

    def _platform_tag(self,s: str) -> str:
        s = s.lower()
        if "win" in s: return "windows"
        if "mac" in s or "darwin" in s: return "macos"
        return "linux"

    def _read_json(self, path: Path) -> dict:
        if not path.is_file():
            raise FileNotFoundError(f"Missing config: {path}")
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _deep_merge(self,a: dict, b: Mapping) -> dict:
        """Return a := a U b (b overrides). Shallow lists are overwritten."""
        out = dict(a)
        for k, v in b.items():
            if isinstance(v, Mapping) and isinstance(out.get(k), Mapping):
                out[k] = self._deep_merge(out[k], v)  # type: ignore[arg-type]
            else:
                out[k] = v
        return out

def norm_abs(path_str: str) -> str:
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    return os.fspath(p)

def pre_build(interface) -> None:
    build_context = BuildContext(interface)
    cfg = build_context.cfg
    cfg_files = build_context.files_cfg
    cfg_pyi    = build_context.pyinstaller_cfg

    data: dict[str, Any] = interface.pyproject_data
    pp = data.setdefault("tool", {}).setdefault("poetry-pyinstaller-plugin", {})
    scripts = pp.setdefault("scripts", {})

    target_name = os.getenv("BUILD_SCRIPT", "jira-importer")
    target = scripts.get(target_name)
    if isinstance(target, str):
        target = {"source": target}
        scripts[target_name] = target
    elif not isinstance(target, dict):
        raise TypeError(f"Unexpected scripts.{target_name} type: {type(target).__name__}")

    if "include" not in target:
        target["include"] = []

    target["type"] = "onefile" if cfg_pyi.get("onefile", False) else "onedir"
    if "console" in cfg_pyi:
        target["console"] = bool(cfg_pyi["console"])
    if "name" in cfg_pyi:
        target["name"] = cfg_pyi["name"]
    if isinstance(cfg.get("hiddenimport"), list):
        target["hiddenimport"] = cfg["hiddenimport"]
    if "icon" in cfg_files:
        target["icon"] = cfg_files["icon"]
    if "version" in cfg_files:
        target["include"].append(build_context.include_file(cfg_files['version']))
        pp["include"].append(build_context.include_file(cfg_files['version']), ".")
    if "add_data" in cfg_pyi:
        target["include"].extend(cfg_pyi["add_data"])

def post_build(interface) -> None:
    try:
        data: dict[str, Any] = interface.pyproject_data
    except Exception as e:
        interface.write_line(f"  - error: {e}")
        sys.exit(1)
    build_context = BuildContext(interface)

    target_name = os.getenv("BUILD_SCRIPT", "jira-importer")

    dist = Path("dist") / "pyinstaller" / interface.platform
    build_executable = dist / f"{target_name}.exe"
    print (f"executable -> {build_executable}")
    versioninfo_file = build_context.files_cfg["version"]
    interface.run("pyi-set_version", str(versioninfo_file), str(build_executable))
    interface.write_line(f" - Stamped version info via pyi-set_version for {build_executable.name}")
