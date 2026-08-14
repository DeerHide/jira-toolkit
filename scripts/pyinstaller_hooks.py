"""Build script for the Jira Importer application.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, TypeVar

try:
    from scripts.build_utils.build_context import BuildContext
    from scripts.build_utils.build_utils import BuildUtils, load_generate_version_module
except ModuleNotFoundError:
    _HOOK_DIR: Path = Path(__file__).resolve().parent
    if str(_HOOK_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOK_DIR))
    from build_utils.build_context import BuildContext
    from build_utils.build_utils import BuildUtils, load_generate_version_module

T = TypeVar("T")


def norm_abs(path_str: str) -> str:
    """Normalize an absolute path."""
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    return os.fspath(p)


def pre_build(interface) -> None:
    """Pre-build hook for the Jira Importer application."""
    build_context = BuildContext(interface)
    cfg = build_context.cfg
    cfg_files = build_context.files_cfg
    cfg_pyi = build_context.pyinstaller_cfg

    try:
        BuildUtils(build_context).generate_version_file(increment=True)
        interface.write_line("Version file generated successfully")
    except Exception as e:
        interface.write_line(f"FileVersionInfo generation failed: {e}")

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
        version_file = build_context.require_existing_file(cfg_files["version"])
        target["include"].append(version_file)
        plugin_include = pp.get("include")
        if isinstance(plugin_include, list):
            plugin_include.append((version_file, "."))
        elif isinstance(plugin_include, dict):
            plugin_include[version_file] = "."
        elif plugin_include is None:
            pp["include"] = [(version_file, ".")]
    if "add_data" in cfg_pyi:
        target["include"].extend(cfg_pyi["add_data"])


def post_build(interface) -> None:
    """Post-build hook for the Jira Importer application.

    ``pyi-set_version`` is Windows-only. Artifacts are under the Poetry PEP platform
    tag (e.g. ``win_amd64``):
      - onefile: dist/pyinstaller/<pep>/<name>.exe
      - onedir:  dist/pyinstaller/<pep>/<name>/<name>.exe
    """
    try:
        _ = interface.pyproject_data
    except Exception as e:
        interface.write_line(f"  - error: {e}")
        sys.exit(1)

    build_context = BuildContext(interface)
    try:
        target_name = os.getenv("BUILD_SCRIPT", "jira-importer")
        plugin_platform = str(getattr(interface, "platform", "") or build_context.platform_tag)
        is_windows = "win" in plugin_platform.lower()
        dist = Path("dist") / "pyinstaller" / plugin_platform
        exe_name = f"{target_name}.exe" if is_windows else target_name

        onefile_exe = dist / exe_name
        onedir_exe = dist / target_name / exe_name
        build_executable = onefile_exe if onefile_exe.is_file() else onedir_exe
        interface.write_line(f"executable -> {build_executable}")

        if is_windows:
            versioninfo_file = build_context.files_cfg.get("version")
            if versioninfo_file and Path(versioninfo_file).is_file() and build_executable.is_file():
                interface.run("pyi-set_version", str(versioninfo_file), str(build_executable))
                interface.write_line(f"Stamped version info via pyi-set_version for {build_executable.name}")
            else:
                interface.write_line(
                    "Skipping pyi-set_version: missing Windows version file and/or executable"
                )
        else:
            interface.write_line(f"Skipping pyi-set_version on platform '{plugin_platform}'")

        if build_executable.is_file():
            BuildUtils(build_context).sign_executable(str(build_executable))
        else:
            interface.write_line(f"Skipping code signing: executable not found at {build_executable}")
    finally:
        if "BUILD_PROFILE" in os.environ:
            del os.environ["BUILD_PROFILE"]
        load_generate_version_module().clear_version_session()
