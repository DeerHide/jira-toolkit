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

VERSION_FILE_NAME = "VSVersionInfo"
BUILD_COUNTER_FILE = "build-counter.json"

def get_git_commit_hash():
    """Get the short commit hash from Git."""
    try:
        # Get the short commit hash (first 7 characters)
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go to project root
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Warning: Could not get Git commit hash: {result.stderr}")
            return "unknown"
    except Exception as e:
        print(f"Warning: Could not execute Git command: {e}")
        return "unknown"

def get_version_info():
    """Read version info from counter file and increment build number."""
    counter_file = os.path.join(os.path.dirname(__file__), BUILD_COUNTER_FILE)
    
    try:
        if os.path.exists(counter_file):
            with open(counter_file, 'r', encoding='utf-8') as f:
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
        with open(counter_file, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2)
        
        version_string = f"{major}.{minor}.{patch}"
        full_version = f"{major}.{minor}.{patch}.{build_number}"
        
        return version_string, full_version, major, minor, patch, build_number
    except Exception as e:
        print(f"Warning: Could not manage version info: {e}")
        return "1.0.0", "1.0.0.1", 1, 0, 0, 1

def main():
    version_string, full_version, major, minor, patch, build_number = get_version_info()
    special_build = get_git_commit_hash()

    prod_version = f"{major}.{minor}.{patch}.{build_number}"
    file_version = f"{major}.{minor}.{patch}.{build_number}"
    
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
        StringStruct('CompanyName', 'Deerhide.run'),
        StringStruct('FileDescription', 'Jira Importer'),
        StringStruct('FileVersion', '{file_version}'),
        StringStruct('InternalName', 'jira_importer'),
        StringStruct('LegalCopyright', 'Copyright (c) 2025 Julien (@tom4897), Alain (@nakool). Licensed under the MIT License.'),
        StringStruct('OriginalFilename', 'jira_importer.exe @rev {special_build}'),
        StringStruct('ProductName', 'Jira Importer'),
        StringStruct('ProductVersion', '{prod_version}'),
        StringStruct('Author', 'Julien (@tom4897), Alain (@nakool)'),
        StringStruct('BuildDate', '{datetime.today().strftime("%Y-%m-%d")}'),
        StringStruct('Comments', 'Jira Importer is a tool that imports Jira issues into a CSV file.'),
        StringStruct('LegalTrademarks', 'Jira is a registered trademark of Atlassian Pty Ltd.'),
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

    version_file = os.path.join(os.path.dirname(__file__), VERSION_FILE_NAME)
    try:
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(version_info_content)
        print(f"{VERSION_FILE_NAME} file generated successfully at {version_file}")
        print(f"Version: {version_string}")
        print(f"Build number: {build_number}")
        print(f"Full version: {full_version}")
        print(f"Rev: {special_build}")
    except Exception as e:
        print(f"Error generating version file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()