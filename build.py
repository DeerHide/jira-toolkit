#!/usr/bin/env python
"""Build script for the Jira Importer application.

Author:
    Julien (@tom4897)
"""

import argparse
import logging
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from scripts.build_utils.build_context import BuildContext
from scripts.build_utils.build_utils import BuildUtils
from scripts.build_utils.logger_manager import LoggerManager
from scripts.build_utils.safe_file_operations import SafeFileOperations

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
            _logger.info("✅ %s is available", dependency)
        except ImportError:
            _logger.warning("❌ %s not found. Installing...", dependency)
            subprocess.check_call([sys.executable, "-m", "pip", "install", dependency.lower()])


def clean_directories(config, config_name) -> bool:
    """Clean dist directory and prepare temp directory."""
    dist_dir = config["directories"]["dist"]
    temp_dir = config["directories"]["temp"]

    # Clean config-specific dist subdirectory if specified
    config_dist_dir = Path(dist_dir) / config_name
    if not _safe_ops.create_directory(config_dist_dir, "config dist directory", clean_if_exists=True):
        _logger.warning("❌ Failed to prepare config dist directory: %s", config_dist_dir)
        return False

    # Clean temp directory only if clean_temp is enabled
    if config["build_options"]["clean_temp"]:
        if not _safe_ops.create_directory(temp_dir, "temp directory", clean_if_exists=True):
            _logger.warning("❌ Failed to prepare temp directory: %s", temp_dir)
            return False
    # Just ensure temp directory exists
    elif not _safe_ops.create_directory(temp_dir, "temp directory"):
        _logger.warning("❌ Failed to ensure temp directory exists: %s", temp_dir)
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
        _logger.warning("❌ Failed to ensure temp directory exists: %s", temp_dir)
        return False

    # Copy icon file if it exists
    if icon_file:
        icon_filename = Path(icon_file).name
        icon_dest = Path(temp_dir) / icon_filename
        if not _safe_ops.copy_file(icon_file, icon_dest, "icon file"):
            return False
    else:
        _logger.info("⏭️  No icon file specified for this platform")

    # Copy version file if it exists
    if version_file:
        version_filename = Path(version_file).name
        version_dest = Path(temp_dir) / version_filename
        if not _safe_ops.copy_file(version_file, version_dest, "version file"):
            return False
    else:
        _logger.info("⏭️  No version file specified for this platform")

    # Handle src directory - remove if exists, then copy
    temp_src_dir = Path(temp_dir) / "src"
    if not _safe_ops.copy_directory(src_dir, temp_src_dir, "source directory"):
        return False

    # Handle resources directory - copy if it exists
    if Path(resources_dir).exists():
        temp_resources_dir = Path(temp_dir) / "resources"
        if not _safe_ops.copy_directory(resources_dir, temp_resources_dir, "resources directory"):
            return False
    else:
        _logger.warning("⚠️  Resources directory not found: %s", resources_dir)

    _logger.info("✅ Build files copied to temp directory successfully")
    return True


def build_executable(config, config_name) -> bool:
    """Build the executable using PyInstaller."""
    src_dir = config["directories"]["source"]
    # Look for the entry point script first
    main_script = Path(src_dir) / "jira_importer_main.py"
    if not main_script.is_file():
        # Fallback to the package's __main__.py
        main_script = Path(src_dir) / "jira_importer" / "__main__.py"
        if not main_script.is_file():
            # Fallback to other common entry points in the package directory
            for candidate in ["__main__.py", "main.py", "app.py"]:
                candidate_path = Path(src_dir) / "jira_importer" / candidate
                if candidate_path.is_file():
                    main_script = candidate_path
                    break
            else:
                raise FileNotFoundError(f"No entry point script found in {src_dir} for PyInstaller compilation.")

    _logger.info("🔨 Building executable from: %s", main_script)

    # Get absolute paths for better reliability
    temp_dir = Path(config["directories"]["temp"]).resolve()
    base_dist_dir = Path(config["directories"]["dist"]).resolve()
    dist_dir = base_dist_dir / config_name  # Use config-specific subdirectory
    work_dir = temp_dir / "pyinstaller_work"
    spec_dir = temp_dir

    # Change to temp directory for PyInstaller
    original_cwd = Path.cwd()
    os.chdir(str(temp_dir))


    try:
        pyinstaller_cmd = [
            sys.executable,  # Use the current Python interpreter (from venv)
            "-m",
            "PyInstaller",
        ]

        # Choose onefile/onedir based on configuration (default: onefile)
        if config["pyinstaller"].get("onefile", True):
            pyinstaller_cmd.append("--onefile")
        else:
            pyinstaller_cmd.append("--onedir")

        pyinstaller_cmd.extend(
            [
                "--console" if config["pyinstaller"]["console"] else "--windowed",
                "--distpath",
                dist_dir,  # Use config-specific dist directory
                "--workpath",
                str(work_dir),  # Use absolute path
                "--specpath",
                str(spec_dir),  # Use absolute path
                "--paths",
                "src",  # Use local src directory
                "--name",
                config["pyinstaller"]["name"],
            ]
        )

        # Add icon if specified
        if config["files"].get("icon"):
            icon_filename = Path(config["files"]["icon"]).name
            pyinstaller_cmd.extend(["--icon", icon_filename])

        # Add version file if specified
        if config["files"].get("version"):
            version_filename = Path(config["files"]["version"]).name
            pyinstaller_cmd.extend(["--version-file", version_filename])

        # Add hidden imports - simplified to only essential third-party dependencies
        pyinstaller_cmd.extend(
            [
                # Core package
                "--hidden-import",
                "jira_importer",

                # Third-party dependencies that PyInstaller might miss
                "--hidden-import",
                "requests",
                "--hidden-import",
                "urllib3",
                "--hidden-import",
                "certifi",
                "--hidden-import",
                "charset_normalizer",
                "--hidden-import",
                "idna",
                "--hidden-import",
                "keyring",
                "--hidden-import",
                "colorama",
            ]
        )

        # Add data files
        for data_file in config["pyinstaller"]["add_data"]:
            pyinstaller_cmd.extend(["--add-data", data_file])

        # Add main script - use the entry point script
        pyinstaller_cmd.append("src/jira_importer_main.py")

        subprocess.check_call(pyinstaller_cmd)
        _logger.info("✅ Executable built successfully!")
    except subprocess.CalledProcessError as e:
        _logger.error("❌ PyInstaller build failed: %s", e)
        sys.exit(1)
    finally:
        # Always restore original working directory
        os.chdir(str(original_cwd))

    return True


def get_version_string() -> str:
    """Extract version string from src/jira_importer/version.py."""
    try:
        # Import the version module to get version info
        version_path = Path("src/jira_importer/version.py")
        if not version_path.exists():
            _logger.warning("⚠️  Version file not found: %s", version_path)
            return "0.1.0"

        # Read and execute the version file to get __version_info__
        with open(version_path, encoding="utf-8") as f:
            version_content = f.read()

        # Create a temporary namespace to execute the version file
        version_namespace: dict[str, object] = {}
        exec(version_content, version_namespace)  # pylint: disable=exec-used

        # Extract version tuple
        version_info = version_namespace.get("__version_info__", (0, 1, 0, 0))
        MIN_VERSION_TUPLE_LENGTH = 3
        if isinstance(version_info, tuple) and len(version_info) >= MIN_VERSION_TUPLE_LENGTH:
            major, minor, patch = version_info[0], version_info[1], version_info[2]
        else:
            major, minor, patch = 0, 1, 0

        return f"{major}.{minor}.{patch}"
    except Exception as e:
        _logger.warning("⚠️  Could not extract version info: %s", e)
        return "0.1.0"


def copy_resources_to_dist(config, config_name) -> bool:
    """Copy resources folder to dist directory."""
    if not config["build_options"].get("copy_resources_to_dist", True):
        _logger.info("⏭️  Resources copying disabled in config")
        return True

    resources_dir = config["directories"]["resources"]
    dist_dir = config["directories"]["dist"]
    config_dist_dir = Path(dist_dir) / config_name

    if not Path(resources_dir).exists():
        _logger.warning("⚠️  Resources directory not found: %s", resources_dir)
        return False

    if not _safe_ops.directory_exists(config_dist_dir, "config dist directory"):
        _logger.warning("⚠️  Warning: Could not find dist directory at %s", config_dist_dir)
        return False

    resources_dest = config_dist_dir / "resources"
    if not _safe_ops.copy_directory(resources_dir, resources_dest, "resources directory"):
        return False

    _logger.info("✅ Resources copied to dist successfully")
    return True


def copy_documentation(config, config_name) -> bool:
    """Copy documentation files to dist directory."""
    if not config["build_options"]["copy_documentation"]:
        _logger.info("⏭️  Documentation copying disabled in config")
        return True

    dist_dir = config["directories"]["dist"]
    license_file = config["files"]["license"]
    readme_file = config["files"]["readme"]

    # Use config-specific dist directory
    config_dist_dir = Path(dist_dir) / config_name

    if not _safe_ops.directory_exists(config_dist_dir, "config dist directory"):
        _logger.warning("⚠️  Warning: Could not find dist directory at %s", config_dist_dir)
        return False

    license_dest = config_dist_dir / f"{config['pyinstaller']['name']}_LICENSE.md"
    readme_dest = config_dist_dir / f"{config['pyinstaller']['name']}_README.md"

    success = True
    if not _safe_ops.copy_file(license_file, license_dest, "license file"):
        success = False

    if not _safe_ops.copy_file(readme_file, readme_dest, "readme file"):
        success = False

    if success:
        _logger.info("✅ Documentation copied successfully")

    return success


def create_zip_archive(config, config_name, platform_tag) -> bool:
    """Create ZIP archive of the build output."""
    if not config["build_options"].get("create_zip", True):
        _logger.info("⏭️  ZIP creation disabled in config")
        return True

    dist_dir = config["directories"]["dist"]
    config_dist_dir = Path(dist_dir) / config_name

    if not _safe_ops.directory_exists(config_dist_dir, "config dist directory"):
        _logger.warning("⚠️  Warning: Could not find dist directory at %s", config_dist_dir)
        return False

    # Get version string
    version = get_version_string()
    zip_filename = f"jira-importer-{config_name}-{platform_tag}-{version}.zip"
    zip_path = Path(dist_dir) / zip_filename

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Walk through the config dist directory and add all files
            for root, _, files in os.walk(config_dist_dir):
                for file in files:
                    file_path = Path(root) / file
                    # Calculate relative path from config_dist_dir
                    arcname = file_path.relative_to(config_dist_dir)
                    zipf.write(file_path, arcname)
                    _logger.debug("📦 Added to ZIP: %s", arcname)

        _logger.info("✅ ZIP archive created successfully: %s", zip_path)
        return True
    except Exception as e:
        _logger.error("❌ Failed to create ZIP archive: %s", e)
        return False


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
    """Main function for the build script."""
    parser = argparse.ArgumentParser(
        description="Builder for the Jira Importer application.", formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-c", "--config", help="Build configuration name (default: dev)", default="dev")
    parser.add_argument(
        "-p", "--build-poetry", help="Build the solution using Poetry", default=False, action="store_true"
    )
    args = parser.parse_args()

    if args.build_poetry:
        _logger.info("🔨 Building solution using Poetry...")
        os.environ["BUILD_PROFILE"] = args.config
        subprocess.check_call(["poetry", "build", "--format", "pyinstaller"])
        sys.exit(0)

    # Load configuration based on argument
    # CONFIG = load_config(args.config)
    build_context = BuildContext(None, args.config)
    build_utils = BuildUtils(build_context)

    CONFIG = build_context.cfg  # pylint: disable=invalid-name
    CONFIG_FILES = build_context.files_cfg  # pylint: disable=invalid-name
    CONFIG_PYI = build_context.pyinstaller_cfg  # pylint: disable=invalid-name
    CONFIG_BUILD_OPTIONS = build_context.cfg["build_options"]  # pylint: disable=invalid-name

    _logger.info("🖥️  Detected platform: %s", build_context.platform_tag)
    _logger.info("🚀 Starting Jira Importer build process...")
    print("=" * 20)
    _logger.info("📋 Using configuration: %s", args.config)
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
            _logger.error("❌ Failed to install requirements: %s", e)
        except Exception as e:
            _logger.error("❌ Failed to install requirements: %s", e)
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
        _logger.error("❌ Failed to build version file: %s", e)

    _logger.info("📁 Copying build files...")
    if not copy_build_files(CONFIG):
        _logger.warning("❌ Failed to copy build files")

    _logger.info("🔨 Building executable...")
    build_executable(CONFIG, args.config)  # Pass config_name as an argument

    dist_dir = CONFIG["directories"]["dist"]
    config_dist_dir = Path(dist_dir) / args.config  # Use config-specific dist directory

    executable_ext = ".exe" if build_context.platform_tag == "windows" else ""
    executable_path = config_dist_dir / f"{CONFIG_PYI['name']}{executable_ext}"

    if _safe_ops.file_exists(executable_path, "executable"):
        print("\n" + "=" * 50)
        _logger.info("🔐 CODE SIGNING")
        print("=" * 50)
        build_utils = BuildUtils(build_context)
        build_utils.sign_executable(executable_path)
    else:
        _logger.warning("⚠️  Warning: Expected executable not found at %s", executable_path)
        _logger.debug("Checking for executable in dist directory...")
        # List contents of dist directory to help debug
        if _safe_ops.directory_exists(config_dist_dir, "config dist directory"):
            for root, _, files in os.walk(str(config_dist_dir)):
                for file in files:
                    if file.endswith(".exe"):
                        _logger.debug("Found executable: %s", Path(root) / file)

    _logger.info("📁 Copying resources to dist...")
    if not copy_resources_to_dist(CONFIG, args.config):
        _logger.warning("⚠️  Warning: Failed to copy resources to dist")

    _logger.info("📚 Copying documentation...")
    if not copy_documentation(CONFIG, args.config):  # Pass config_name
        _logger.warning("⚠️  Warning: Failed to copy documentation")

    _logger.info("📦 Creating ZIP archive...")
    if not create_zip_archive(CONFIG, args.config, build_context.platform_tag):
        _logger.warning("⚠️  Warning: Failed to create ZIP archive")

    if CONFIG["build_options"]["clean_temp"]:
        if not cleanup_temp_files(CONFIG):
            _logger.warning("⚠️  Warning: Failed to clean up temporary files")
    else:
        _logger.info("💾 Keeping temporary files (clean_temp disabled in config)")
        temp_dir = CONFIG["directories"]["temp"]
        _logger.info("📁 Temp files location: %s", temp_dir)

    print("\n" + "=" * 50)
    _logger.info("🎉 Build completed successfully!")
    _logger.info("📦 Executable location: %s", config_dist_dir)
    print("=" * 50)


if __name__ == "__main__":
    main()
