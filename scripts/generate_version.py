#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates a new VSVersionInfo file for use with PyInstaller builds.

Author: Julien (@tom4897)
Date: June 2025
"""

import os
import subprocess
import sys
import json
from datetime import datetime

def get_version_strings() -> dict[str, str]:
    """Get the version string from the project."""
    ret: dict[str, str] = dict()
    ret["copyright"] = "Copyright (c) 2025 Julien (@tom4897), Alain (@nakool). Licensed under the MIT License."
    ret["author"] = "Julien (@tom4897), Alain (@nakool)"
    ret["comments"] = "Jira Importer is a tool that imports Jira issues into a CSV file."
    ret["company_name"] = "Deerhide.run"
    ret["file_description"] = "Jira Importer"
    ret["internal_name"] = "jira_importer"
    ret["original_filename"] = "jira_importer.exe"
    ret["product_name"] = "Jira Importer"
    ret["legal_trademarks"] = "Jira is a registered trademark of Atlassian Pty Ltd."
    ret["bundle_identifier"] = "com.deerhide.jira-importer"
    print(ret)
    return ret


def _get_project_root() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != os.path.dirname(current_dir):
        if os.path.exists(os.path.join(current_dir, '.git')):
            return current_dir
        current_dir = os.path.dirname(current_dir)

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_git_commit_hash() -> str:
    """Get the short commit hash from Git."""
    try:
        # Get the short commit hash (first 7 characters)
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=_get_project_root()
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
        result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, cwd=_get_project_root())
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Warning: Could not get Git branch: {result.stderr}")
            return "unknown"
    except Exception as e:
        print(f"Warning: Could not execute Git command: {e}")
        return "unknown"

def get_version_numbers() -> tuple[str, str, int, int, int, int]:
    """Read version info from counter file and increment build number."""
    BUILD_COUNTER_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "build", "version", "build-counter.json")

    counter_file = BUILD_COUNTER_FILE_PATH

    try:
        if os.path.exists(BUILD_COUNTER_FILE_PATH):
            with open(BUILD_COUNTER_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                major = data.get('major', 1)
                minor = data.get('minor', 0)
                patch = data.get('patch', 0)
                build_number = data.get('build_number', 0) + 1
        else:
            major, minor, patch, build_number = 0, 1, 0, 0

        # Save the updated version info
        version_data = {
            'major': major,
            'minor': minor,
            'patch': patch,
            'build_number': build_number
        }
        with open(BUILD_COUNTER_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2)

        version_num_short = f"{major}.{minor}.{patch}"
        version_num_full = f"{major}.{minor}.{patch}.{build_number}"

        return version_num_short, version_num_full, major, minor, patch, build_number
    except Exception as e:
        print(f"Warning: Could not manage version info: {e}")
        return "1.0.0", "1.0.0.1", 1, 0, 0, 1

def generate_windows_version_info() -> None:
    version_num_short, version_num_full, major, minor, patch, build_number = get_version_numbers()
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

    VERSION_FILE_PATH =  os.path.join(os.path.dirname(__file__), "..", "build", "version", "VSVersionInfo")

    try:
        with open(VERSION_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(version_info_content)
        print(f"VSVersionInfo file generated successfully at {VERSION_FILE_PATH}")
        print(f"Version: {version_num_short}")
        print(f"Build number: {build_number}")
        print(f"Full version: {version_num_full}")
        print(f"Rev: {special_build}")
        print(f"Branch: {git_branch}")
    except Exception as e:
        print(f"Error generating version file: {e}")
        sys.exit(1)

def generate_macos_version_info() -> None:
    version_num_short, version_num_full, major, minor, patch, build_number = get_version_numbers()
    version_info = get_version_strings()
    special_build = get_git_commit_hash()
    git_branch = get_git_branch()

    VERSION_FILE_PATH =  os.path.join(os.path.dirname(__file__), "..", "build", "version", "Info.plist")
    build_date = datetime.today().strftime("%Y-%m-%d")

    # Minimal Info.plist for a console app, enriched with build metadata
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
        print(f"VSVersionInfo file generated successfully at {VERSION_FILE_PATH}")
        print(f"Version: {version_num_short}")
        print(f"Build number: {build_number}")
        print(f"Full version: {version_num_full}")
        print(f"Rev: {special_build}")
        print(f"Branch: {git_branch}")
    except Exception as e:
        print(f"Error generating macOS Info.plist: {e}")
        sys.exit(1)

def generate_app_version_info() -> None:
    version_num_short, version_num_full, major, minor, patch, build_number = get_version_numbers()
    version_info = get_version_strings()
    special_build = get_git_commit_hash()
    git_branch = get_git_branch()

    print(f"Version info -> {version_info}")
    print(f"Version num short -> {version_num_short}")
    print(f"Version num full -> {version_num_full}")
    print(f"Major -> {major}")
    print(f"Minor -> {minor}")
    print(f"Patch -> {patch}")
    print(f"Build number -> {build_number}")
    print(f"Special build -> {special_build}")
    print(f"Git branch -> {git_branch}")

    build_date = datetime.today().strftime("%Y-%m-%d")

    VERSION_FILE_PATH =  os.path.join(os.path.dirname(__file__), "..", "src", "jira_importer", "version.py")

    version_info_content = f"""\
# DO NOT EDIT THIS FILE, IT IS AUTO-GENERATED BY THE BUILD SCRIPT
__version_info__ = ({major}, {minor}, {patch}, {build_number})
__build_number__ = {build_number}
__git_revision__ = "{special_build}"
__git_branch__ = "{git_branch}"
__build_date__ = "{build_date}"
"""

    try:
        with open(VERSION_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(version_info_content)
        print(f"Version file generated successfully at {VERSION_FILE_PATH}")
    except Exception as e:
        print(f"Error generating version file: {e}")
        sys.exit(1)

def main() -> None:
    generate_windows_version_info()
    generate_macos_version_info()
    generate_app_version_info()

if __name__ == "__main__":
    main()
