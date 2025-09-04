#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build script for the Jira Importer application.

Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import argparse
import subprocess
import shutil
import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from scripts.build_utils.logger_manager import LoggerManager
from scripts.build_utils.safe_file_operations import SafeFileOperations
from scripts.build_utils.build_context import BuildContext
from scripts.build_utils.build_utils import BuildUtils


BASE_LOG_DIR = "build/logs"
LOG_LEVEL = logging.DEBUG

_logger = LoggerManager(BASE_LOG_DIR).get_logger()

# Create a global instance for file operations
_safe_ops = SafeFileOperations()

def check_dependencies(config) -> None:
    """Check if required dependencies are available."""
    if not config["build_options"]["check_dependencies"]:
        _logger.info("⏭️  Dependency checking disabled in config")
        return

    for dependency in config["dependencies"]["required"]:
        try:
            __import__(dependency.lower())
            _logger.info(f"✅ {dependency} is available")
        except ImportError:
            _logger.warning(f"❌ {dependency} not found. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dependency.lower()])

def clean_directories(config, config_name) -> bool:
    """Clean dist directory and prepare temp directory."""
    dist_dir = config["directories"]["dist"]
    temp_dir = config["directories"]["temp"]

    # Clean config-specific dist subdirectory if specified
    config_dist_dir = os.path.join(dist_dir, config_name)
    if not _safe_ops.create_directory(config_dist_dir, "config dist directory", clean_if_exists=True):
        _logger.warning(f"❌ Failed to prepare config dist directory: {config_dist_dir}")
        return False

    # Clean temp directory only if clean_temp is enabled
    if config["build_options"]["clean_temp"]:
        if not _safe_ops.create_directory(temp_dir, "temp directory", clean_if_exists=True):
            _logger.warning(f"❌ Failed to prepare temp directory: {temp_dir}")
            return False
    else:
        # Just ensure temp directory exists
        if not _safe_ops.create_directory(temp_dir, "temp directory"):
            _logger.warning(f"❌ Failed to ensure temp directory exists: {temp_dir}")
            return False

    return True

def copy_build_files(config) -> bool:
    """Copy necessary files to temp directory."""
    temp_dir = config["directories"]["temp"]
    src_dir = config["directories"]["source"]
    resources_dir = config["directories"]["resources"]

    # Copy icon and version files if they exist
    icon_file = config["files"].get("icon")
    version_file = config["files"].get("version")

    # Ensure temp directory exists (in case clean_directories wasn't called)
    if not _safe_ops.create_directory(temp_dir, "temp directory"):
        _logger.warning(f"❌ Failed to ensure temp directory exists: {temp_dir}")
        return False

    # Copy icon file if it exists
    if icon_file:
        icon_filename = os.path.basename(icon_file)
        icon_dest = os.path.join(temp_dir, icon_filename)
        if not _safe_ops.copy_file(icon_file, icon_dest, "icon file"):
            return False
    else:
        _logger.info("⏭️  No icon file specified for this platform")

    # Copy version file if it exists
    if version_file:
        version_filename = os.path.basename(version_file)
        version_dest = os.path.join(temp_dir, version_filename)
        if not _safe_ops.copy_file(version_file, version_dest, "version file"):
            return False
    else:
        _logger.info("⏭️  No version file specified for this platform")

    # Handle src directory - remove if exists, then copy
    temp_src_dir = os.path.join(temp_dir, "src")
    if not _safe_ops.copy_directory(src_dir, temp_src_dir, "source directory"):
        return False

    # Handle resources directory - copy if it exists
    if os.path.exists(resources_dir):
        temp_resources_dir = os.path.join(temp_dir, "resources")
        if not _safe_ops.copy_directory(resources_dir, temp_resources_dir, "resources directory"):
            return False
    else:
        _logger.warning(f"⚠️  Resources directory not found: {resources_dir}")

    _logger.info("✅ Build files copied to temp directory successfully")
    return True

def build_executable(config, config_name) -> bool:
    """Build the executable using PyInstaller."""
    src_dir = config["directories"]["source"]
    # Look for the entry point script first
    main_script = os.path.join(src_dir, "jira_importer_main.py")
    if not os.path.isfile(main_script):
        # Fallback to the package's __main__.py
        main_script = os.path.join(src_dir, "jira_importer", "__main__.py")
        if not os.path.isfile(main_script):
            # Fallback to other common entry points in the package directory
            for candidate in ["__main__.py", "main.py", "app.py"]:
                candidate_path = os.path.join(src_dir, "jira_importer", candidate)
                if os.path.isfile(candidate_path):
                    main_script = candidate_path
                    break
            else:
                raise FileNotFoundError(f"No entry point script found in {src_dir} for PyInstaller compilation.")

    _logger.info(f"🔨 Building executable from: {main_script}")

    # Get absolute paths for better reliability
    temp_dir = os.path.abspath(config["directories"]["temp"])
    base_dist_dir = os.path.abspath(config["directories"]["dist"])
    dist_dir = os.path.join(base_dist_dir, config_name)  # Use config-specific subdirectory
    work_dir = os.path.join(temp_dir, "pyinstaller_work")
    spec_dir = temp_dir

    # Change to temp directory for PyInstaller
    original_cwd = os.getcwd()
    os.chdir(temp_dir)

    try:
        pyinstaller_cmd = [
            "pyinstaller",
        ]

        # Choose onefile/onedir based on configuration (default: onefile)
        if config["pyinstaller"].get("onefile", True):
            pyinstaller_cmd.append("--onefile")
        else:
            pyinstaller_cmd.append("--onedir")

        pyinstaller_cmd.extend([
            "--console" if config["pyinstaller"]["console"] else "--windowed",
            "--distpath", dist_dir,  # Use config-specific dist directory
            "--workpath", work_dir,  # Use absolute path
            "--specpath", spec_dir,  # Use absolute path
            "--paths", "src",  # Use local src directory
            "--name", config["pyinstaller"]["name"],
        ])

        # Add icon if specified
        if config["files"].get("icon"):
            icon_filename = os.path.basename(config["files"]["icon"])
            pyinstaller_cmd.extend(["--icon", icon_filename])

        # Add version file if specified
        if config["files"].get("version"):
            version_filename = os.path.basename(config["files"]["version"])
            pyinstaller_cmd.extend(["--version-file", version_filename])

        # Add hidden imports
        pyinstaller_cmd.extend([
            "--hidden-import", "jira_importer",
            "--hidden-import", "jira_importer.console",
            "--hidden-import", "jira_importer.excel_io",
            "--hidden-import", "jira_importer.app",
            "--hidden-import", "jira_importer.config",
            "--hidden-import", "jira_importer.artifacts",
            "--hidden-import", "jira_importer.fileops",
            "--hidden-import", "jira_importer.log",
            "--hidden-import", "jira_importer.utils",
            "--hidden-import", "jira_importer.import_pipeline.processor",
            "--hidden-import", "jira_importer.import_pipeline.reporting",
            "--hidden-import", "jira_importer.import_pipeline.sinks.csv_sink"
        ])

        # Add data files
        for data_file in config["pyinstaller"]["add_data"]:
            pyinstaller_cmd.extend(["--add-data", data_file])

        # Add main script - use the entry point script
        pyinstaller_cmd.append("src/jira_importer_main.py")

        subprocess.check_call(pyinstaller_cmd)
        _logger.info("✅ Executable built successfully!")
    except subprocess.CalledProcessError as e:
        _logger.error(f"❌ PyInstaller build failed: {e}")
        sys.exit(1)
    finally:
        # Always restore original working directory
        os.chdir(original_cwd)

def copy_documentation(config, config_name) -> bool:
    """Copy documentation files to dist directory."""
    if not config["build_options"]["copy_documentation"]:
        _logger.info("⏭️  Documentation copying disabled in config")
        return True

    dist_dir = config["directories"]["dist"]
    license_file = config["files"]["license"]
    readme_file = config["files"]["readme"]

    # Use config-specific dist directory
    config_dist_dir = os.path.join(dist_dir, config_name)

    if not _safe_ops.directory_exists(config_dist_dir, "config dist directory"):
        _logger.warning(f"⚠️  Warning: Could not find dist directory at {config_dist_dir}")
        return False

    license_dest = os.path.join(config_dist_dir, f"{config['pyinstaller']['name']}_LICENSE.md")
    readme_dest = os.path.join(config_dist_dir, f"{config['pyinstaller']['name']}_README.md")

    success = True
    if not _safe_ops.copy_file(license_file, license_dest, "license file"):
        success = False

    if not _safe_ops.copy_file(readme_file, readme_dest, "readme file"):
        success = False

    if success:
        _logger.info("✅ Documentation copied successfully")

    return success

def cleanup_temp_files(config) -> bool:
    """Clean up temporary files after build completion."""
    temp_dir = config["directories"]["temp"]

    if _safe_ops.directory_exists(temp_dir, "temp directory"):
        if _safe_ops.remove_directory(temp_dir, "temp directory"):
            _logger.info("✅ Temporary files cleaned up successfully")
        else:
            _logger.warning("⚠️  Warning: Could not clean up temp directory")
    else:
        _logger.debug("⏭️  No temp directory to clean up")

    return True

def main() -> None:
    parser = argparse.ArgumentParser(description="Builder for the Jira Importer application.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-c", "--config",
                       help="Build configuration name (default: dev)",
                       default="dev")
    parser.add_argument("-p", "--build-poetry",
                       help="Build the solution using Poetry",
                       default=False, action="store_true")
    args = parser.parse_args()

    if args.build_poetry:
        _logger.info("🔨 Building solution using Poetry...")
        os.environ["BUILD_PROFILE"] = args.config
        subprocess.check_call(["poetry", "build", "--format", "pyinstaller"])
        sys.exit(0)

    # Load configuration based on argument
    #CONFIG = load_config(args.config)
    build_context = BuildContext(None, args.config)
    build_utils = BuildUtils(build_context)

    CONFIG = build_context.cfg
    CONFIG_FILES = build_context.files_cfg
    CONFIG_PYI = build_context.pyinstaller_cfg
    CONFIG_BUILD_OPTIONS = build_context.cfg["build_options"]

    _logger.info(f"🖥️  Detected platform: {build_context.platform_tag}")
    _logger.info("🚀 Starting Jira Importer build process...")
    print("=" * 20)
    _logger.info(f"📋 Using configuration: {args.config}")
    print("=" * 20)

    _logger.info("📋 Checking dependencies...")
    check_dependencies(CONFIG)

    if CONFIG_BUILD_OPTIONS["install_requirements"]:
        _logger.info("📦 Installing requirements...")
        try:
            requirements_file = CONFIG_FILES["requirements"]
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
            _logger.info("✅ Requirements installed successfully")
        except subprocess.CalledProcessError as e:
            _logger.error(f"❌ Failed to install requirements: {e}")
        except Exception as e:
            _logger.error(f"❌ Failed to install requirements: {e}")
    else:
        _logger.info("⏭️  Requirements installation disabled in config")

    if CONFIG_BUILD_OPTIONS["clean_dist"]:
        _logger.info("🧹 Preparing build environment...")
        if not clean_directories(CONFIG, args.config):
            _logger.warning("❌ Failed to prepare build environment")
            sys.exit(1)
    else:
        _logger.info("⏭️  Directory cleaning disabled in config")

    _logger.info("🔨 Building version file...")
    try:
        build_utils.create_version_file()
    except Exception as e:
        _logger.error(f"❌ Failed to build version file: {e}")

    _logger.info("📁 Copying build files...")
    if not copy_build_files(CONFIG):
        _logger.warning("❌ Failed to copy build files")

    _logger.info("🔨 Building executable...")
    build_executable(CONFIG, args.config) # Pass config_name as an argument

    dist_dir = CONFIG["directories"]["dist"]
    config_dist_dir = os.path.join(dist_dir, args.config)  # Use config-specific dist directory

    executable_ext = ".exe" if build_context.platform_tag == "windows" else ""
    executable_path = os.path.join(config_dist_dir, f"{CONFIG_PYI['name']}{executable_ext}")

    if _safe_ops.file_exists(executable_path, "executable"):
        print("\n" + "="*50)
        _logger.info("🔐 CODE SIGNING")
        print("="*50)
        build_utils = BuildUtils(build_context)
        build_utils.sign_executable(executable_path)
    else:
        _logger.warning(f"⚠️  Warning: Expected executable not found at {executable_path}")
        _logger.debug("Checking for executable in dist directory...")
        # List contents of dist directory to help debug
        if _safe_ops.directory_exists(config_dist_dir, "config dist directory"):
            for root, dirs, files in os.walk(config_dist_dir):
                for file in files:
                    if file.endswith('.exe'):
                        _logger.debug(f"Found executable: {os.path.join(root, file)}")

    _logger.info("📚 Copying documentation...")
    if not copy_documentation(CONFIG, args.config):  # Pass config_name
        _logger.warning("⚠️  Warning: Failed to copy documentation")

    if CONFIG["build_options"]["clean_temp"]:
        if not cleanup_temp_files(CONFIG):
            _logger.warning("⚠️  Warning: Failed to clean up temporary files")
    else:
        _logger.info("💾 Keeping temporary files (clean_temp disabled in config)")
        temp_dir = CONFIG["directories"]["temp"]
        _logger.info(f"📁 Temp files location: {temp_dir}")

    print("\n" + "="*50)
    _logger.info("🎉 Build completed successfully!")
    _logger.info(f"📦 Executable location: {config_dist_dir}")
    print("="*50)

if __name__ == "__main__":
    main()
