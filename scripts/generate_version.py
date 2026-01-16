#!/usr/bin/env python
"""Creates a new VSVersionInfo file for use with PyInstaller builds.

Author:
    Julien (@tom4897)
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any

# TODO: refactor into a class in the build_utils package

DEFAULT_BUILD_NUMBER = 0
EXPECTED_VERSION_PARTS = 3  # Semantic version format: major.minor.patch


# TODO: Move to utils
def _get_project_root() -> str:
    """Get the project root directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != os.path.dirname(current_dir):
        if os.path.exists(os.path.join(current_dir, ".git")):
            return current_dir
        current_dir = os.path.dirname(current_dir)

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# TODO: Use these strings in the build_utils package
def get_version_strings() -> dict[str, str]:
    """Get the version string from the project."""
    ret: dict[str, str] = dict()
    ret["copyright"] = "Copyright (c) 2025 Julien (@tom4897), Alain (@nakool). Licensed under the MIT License."
    ret["author"] = "Julien (@tom4897), Alain (@nakool)"
    ret["comments"] = "Jira Importer is a tool that imports Jira issues into a CSV file."
    ret["company_name"] = "Deerhide.run"
    ret["file_description"] = "Jira Importer"
    ret["internal_name"] = "jira_importer"
    ret["original_filename"] = "jira-importer.exe"
    ret["product_name"] = "Jira Importer"
    ret["legal_trademarks"] = "Jira is a registered trademark of Atlassian Pty Ltd."
    ret["bundle_identifier"] = "com.deerhide.jira-importer"
    return ret


def get_git_commit_hash() -> str:
    """Get the short commit hash from Git."""
    try:
        # Get the short commit hash (first 7 characters)
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=_get_project_root(),
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Warning: Could not get Git commit hash: {result.stderr}")
            return "unknown"
    except Exception as e:
        print(f"Warning: Could not execute Git command: {e}")
        return "unknown"


def get_git_branch() -> str:
    """Get the Git branch from Git."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"], check=False, capture_output=True, text=True, cwd=_get_project_root()
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Warning: Could not get Git branch: {result.stderr}")
            return "unknown"
    except Exception as e:
        print(f"Warning: Could not execute Git command: {e}")
        return "unknown"


def _read_base_config() -> dict[str, Any]:
    """Read the base.json configuration file."""
    project_root = _get_project_root()
    base_config_path = os.path.join(project_root, "build", "configs", "base.json")

    if not os.path.exists(base_config_path):
        raise FileNotFoundError(f"Base configuration file not found: {base_config_path}")

    with open(base_config_path, encoding="utf-8") as f:
        content = f.read()
        # Expand environment variables if present
        content = os.path.expandvars(content)
        return json.loads(content)


def _parse_version_string(version_str: str) -> tuple[int, int, int]:
    """Parse a semantic version string into major, minor, patch components."""
    parts = version_str.strip().split(".")
    if len(parts) != EXPECTED_VERSION_PARTS:
        raise ValueError(f"Invalid version format: expected 'major.minor.patch', got '{version_str}'")

    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2])
    except ValueError as e:
        raise ValueError(f"Invalid version format: non-numeric component in '{version_str}'") from e

    if major < 0 or minor < 0 or patch < 0:
        raise ValueError(f"Invalid version format: negative component in '{version_str}'")

    return major, minor, patch


def _get_default_version_from_config() -> tuple[int, int, int]:
    """Get default version numbers from base.json configuration."""
    config = _read_base_config()
    version_str = config.get("metadata", {}).get("version")
    if not version_str:
        raise ValueError("'metadata.version' not found in base.json")

    return _parse_version_string(version_str)


def get_version_numbers() -> tuple[str, str, int, int, int, int]:
    """Read version info from counter file and increment build number."""
    # TODO: Refactor the logic around the build number
    counter_file = os.path.join(os.path.dirname(__file__), "..", "build", "version", "build-counter.json")

    # Get default version from base.json config
    default_major, default_minor, default_patch = _get_default_version_from_config()

    if os.path.exists(counter_file):
        with open(counter_file, encoding="utf-8") as f:
            data = json.load(f)
            major = max(data.get("major", default_major), default_major)
            minor = max(data.get("minor", default_minor), default_minor)
            patch = max(data.get("patch", default_patch), default_patch)
            current_build = max(data.get("build_number", DEFAULT_BUILD_NUMBER), DEFAULT_BUILD_NUMBER)
            build_number = current_build + 1
    else:
        major, minor, patch, build_number = default_major, default_minor, default_patch, DEFAULT_BUILD_NUMBER + 1

    version_data = {"major": major, "minor": minor, "patch": patch, "build_number": build_number}
    with open(counter_file, "w", encoding="utf-8") as f:
        json.dump(version_data, f, indent=2)

    version_num_short = f"{major}.{minor}.{patch}"
    version_num_full = f"{major}.{minor}.{patch}.{build_number}"

    return version_num_short, version_num_full, major, minor, patch, build_number


def generate_windows_version_info(current_version: tuple[str, str, int, int, int, int]) -> None:
    """Generate the Windows VSVersionInfo file."""
    _, _, major, minor, patch, build_number = current_version
    special_build = get_git_commit_hash()

    prod_version = f"{major}.{minor}.{patch}.{build_number}"
    file_version = f"{major}.{minor}.{patch}.{build_number}"
    git_branch = get_git_branch()

    version_info = get_version_strings()

    version_info_content = f"""\
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build_number}),
    prodvers=({major}, {minor}, {patch}, {build_number}),
    mask=0x3f,
    flags=0x0,
    OS=0x4,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [
        StringStruct('CompanyName', '{version_info["company_name"]}'),
        StringStruct('FileDescription', '{version_info["file_description"]}'),
        StringStruct('FileVersion', '{file_version}'),
        StringStruct('InternalName', '{version_info["internal_name"]}'),
        StringStruct('LegalCopyright', '{version_info["copyright"]}'),
        StringStruct('OriginalFilename', '{version_info["original_filename"]} @branch {git_branch} @rev {special_build}'),
        StringStruct('ProductName', '{version_info["product_name"]}'),
        StringStruct('ProductVersion', '{prod_version}'),
        StringStruct('Author', '{version_info["author"]}'),
        StringStruct('BuildDate', '{datetime.today().strftime("%Y-%m-%d")}'),
        StringStruct('Comments', '{version_info["comments"]}'),
        StringStruct('LegalTrademarks', '{version_info["legal_trademarks"]}'),
        StringStruct('PrivateBuild', ''),
        StringStruct('SpecialBuild', '')
        ]
      )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

    VERSION_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "build", "version", "VSVersionInfo")  # pylint: disable=invalid-name

    try:
        with open(VERSION_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(version_info_content)
        print(f"Windows VSVersionInfo file generated successfully at {VERSION_FILE_PATH}")
    except Exception as e:
        print(f"Error generating Windows VSVersionInfo file: {e}")
        sys.exit(1)


def generate_macos_version_info(current_version: tuple[str, str, int, int, int, int]) -> None:
    """Generate the macOS Info.plist file."""
    version_num_short, version_num_full, _, _, _, build_number = current_version
    version_info = get_version_strings()
    special_build = get_git_commit_hash()
    git_branch = get_git_branch()

    VERSION_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "build", "version", "Info.plist")  # pylint: disable=invalid-name
    build_date = datetime.today().strftime("%Y-%m-%d")

    # TODO: Minimal Info.plist for a console app, enriched with build metadata
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>{version_info["product_name"]}</string>
    <key>CFBundleDisplayName</key>
    <string>{version_info["product_name"]}</string>
    <key>CFBundleIconFile</key>
    <string>deerhide_default.icns</string>
    <key>CFBundleIdentifier</key>
    <string>{version_info["bundle_identifier"]}</string>
    <key>CFBundleVersion</key>
    <string>{build_number}</string>
    <key>CFBundleShortVersionString</key>
    <string>{version_num_short}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHumanReadableCopyright</key>
    <string>{version_info["copyright"]}</string>

    <!-- Build metadata -->
    <key>DHProductVersion</key>
    <string>{version_num_full}</string>
    <key>DHGitRevision</key>
    <string>{special_build}</string>
    <key>DHGitBranch</key>
    <string>{git_branch}</string>
    <key>DHBuildDate</key>
    <string>{build_date}</string>
</dict>
</plist>
"""

    try:
        out_dir = os.path.dirname(VERSION_FILE_PATH)
        os.makedirs(out_dir, exist_ok=True)
        with open(VERSION_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(plist_content)
        print(f"macOS Info.plist file generated successfully at {VERSION_FILE_PATH}")
    except Exception as e:
        print(f"Error generating macOS Info.plist: {e}")
        sys.exit(1)


def generate_app_version_info(current_version: tuple[str, str, int, int, int, int]) -> None:
    """Generate the Python version file."""
    _, _, major, minor, patch, build_number = current_version
    special_build = get_git_commit_hash()
    git_branch = get_git_branch()

    build_date = datetime.today().strftime("%Y-%m-%d")

    VERSION_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "jira_importer", "version.py")  # pylint: disable=invalid-name

    version_info_content = f"""\
\"\"\"DO NOT EDIT THIS FILE, IT IS AUTO-GENERATED BY THE BUILD SCRIPT.\"\"\"

__version_info__ = ({major}, {minor}, {patch}, {build_number})
__build_number__ = {build_number}
__git_revision__ = "{special_build}"
__git_branch__ = "{git_branch}"
__build_date__ = "{build_date}"
"""

    try:
        with open(VERSION_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(version_info_content)
        print(f"Python version file generated successfully at {VERSION_FILE_PATH}")
    except Exception as e:
        print(f"Error generating Python version file: {e}")
        sys.exit(1)


def main() -> None:
    """Main function."""
    current_version = get_version_numbers()
    generate_windows_version_info(current_version)
    generate_macos_version_info(current_version)
    generate_app_version_info(current_version)


if __name__ == "__main__":
    main()
