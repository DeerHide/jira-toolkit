#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import subprocess
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

class BuildUtils:
    def __init__(self, context: BuildContext = None):
        self.context = context
        self.sign_config = self.context.cfg["code_signing"]
        self._logger = self._setup_logger()

    def _setup_logger(self):
        """Setup a simple logger for consistent output."""
        import logging
        logger = logging.getLogger(f"{__name__}.BuildUtils")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def sign_executable(self, executable_path: str) -> bool:
        """Sign the executable with the certificate if available."""
        if not self.sign_config["enabled"]:
            self._logger.info("Code signing disabled in config")
            return False

        certificate_path = self.sign_config["certificate"]
        signtool_path = self.sign_config["signtool"]
        timestamp_server = self.sign_config["timestamp_server"]
        digest_algorithm = self.sign_config["digest_algorithm"]

        if not os.path.exists(certificate_path):
            self._logger.warning("Certificate not found, skipping code signing...")
            return False

        if not os.path.exists(signtool_path):
            self._logger.warning("Signtool not found, skipping code signing...")
            return False

        if not os.path.exists(executable_path):
            self._logger.error("Executable not found for signing")
            return False

        try:
            # Use signtool to sign the executable
            sign_cmd = [
                signtool_path,
                "sign",
                "/f", certificate_path,
                "/fd", digest_algorithm,
                "/t", timestamp_server,
                "/v",  # Verbose output
                executable_path
            ]

            self._logger.info(f"Signing executable: {executable_path}")
            self._logger.info(f"Using certificate: {certificate_path}")

            result = subprocess.run(sign_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self._logger.info("Executable signed successfully!")
                return True
            else:
                self._logger.error(f"Code signing failed with error code: {result.returncode}")
                self._logger.error(f"Error output: {result.stderr}")
                return False

        except FileNotFoundError:
            self._logger.error(f"{signtool_path} not found. Make sure Windows SDK is installed.")
            self._logger.error("You can install it via Visual Studio Installer or download from Microsoft.")
            return False
        except Exception as e:
            self._logger.error(f"Error during code signing: {e}")
            return False

    def create_version_file(self) -> None:
        """Create version file using the same pattern as post_build."""
        try:
            scripts_dir = os.path.abspath("scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)

            import generate_version
            generate_version.main()
        except Exception as e:
            self._log_error(f"Version file generation failed: {e}")
            raise
        finally:
            if scripts_dir in sys.path:
                sys.path.remove(scripts_dir)

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

    try:
        scripts_dir = os.path.abspath("scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

        import generate_version
        generate_version.main()
        interface.write_line("Version file generated successfully")
    except Exception as e:
        interface.write_line(f"FileVersionInfo generation failed: {e}")
    finally:
        if scripts_dir in sys.path:
            sys.path.remove(scripts_dir)

    dist = Path("dist") / "pyinstaller" / interface.platform
    build_executable = dist / f"{target_name}.exe"
    print (f"executable -> {build_executable}")
    versioninfo_file = build_context.files_cfg["version"]
    interface.run("pyi-set_version", str(versioninfo_file), str(build_executable))
    interface.write_line(f"Stamped version info via pyi-set_version for {build_executable.name}")

    build_utils = BuildUtils(build_context)
    build_utils.sign_executable(build_executable)

    if "BUILD_PROFILE" in os.environ:
        del os.environ["BUILD_PROFILE"]
