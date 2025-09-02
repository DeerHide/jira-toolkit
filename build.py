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


BASE_LOG_DIR = "build/logs"
LOG_LEVEL = logging.DEBUG

def _detect_tty() -> bool:
    """Detect if stderr supports TTY (colors)."""
    return hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()

class LoggerManager:
    def __init__(self, base_dir: str = BASE_LOG_DIR) -> None:
        self.base_dir = base_dir
        self.logger = None
        self.setup()

    @property
    def level(self) -> int:
        """Get the resolved log level with proper priority."""
        if self._resolved_level is None:
            self._resolved_level = self._resolve_level()
        return self._resolved_level

    @property
    def is_tty(self) -> bool:
        """Check if terminal supports colors."""
        if self._is_tty is None:
            self._is_tty = _detect_tty()
        return self._is_tty

    def setup(self) -> logging.Logger:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")

        os.makedirs(self.base_dir, exist_ok=True)
        log_file = os.path.join(self.base_dir, f"{date_str}_build_jira_importer.log")

        root_logger = logging.getLogger()
        root_logger.setLevel(LOG_LEVEL)

        if root_logger.handlers:
            root_logger.handlers.clear()

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(LOG_LEVEL)
        file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d %(message)s")
        file_handler.setFormatter(file_formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_LEVEL)
        console_formatter = logging.Formatter("%(asctime)s %(message)s")
        console_handler.setFormatter(console_formatter)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        self.logger = logging.getLogger(__name__)
        return self.logger

    def get_logger(self) -> logging.Logger:
        if self.logger is None:
            return self.setup()
        return self.logger

_logger = LoggerManager(BASE_LOG_DIR).get_logger()

def safe_remove_directory(directory_path, config, description="directory") -> bool:
    """Safely remove a directory with retry logic and proper error handling."""
    if not os.path.exists(directory_path):
        _logger.info(f"⏭️  {description.capitalize()} does not exist: {directory_path}")
        return True

    max_retries = 3
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            _logger.info(f"🧹 Removing {description}: {directory_path}")
            shutil.rmtree(directory_path)
            _logger.info(f"✅ Successfully removed {description}: {directory_path}")
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                _logger.warning(f"⚠️  Permission error removing {description} (attempt {attempt + 1}/{max_retries}): {e}")
                _logger.warning(f"⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                _logger.error(f"❌ Failed to remove {description} after {max_retries} attempts: {e}")
                return False
        except OSError as e:
            if attempt < max_retries - 1:
                _logger.warning(f"⚠️  OS error removing {description} (attempt {attempt + 1}/{max_retries}): {e}")
                _logger.warning(f"⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                _logger.error(f"❌ Failed to remove {description} after {max_retries} attempts: {e}")
                return False
        except Exception as e:
            _logger.error(f"❌ Unexpected error removing {description}: {e}")
            return False

    return False

def safe_create_directory(directory_path, config, description="directory", clean_if_exists=False) -> bool:
    """Safely create a directory with optional cleaning and proper error handling."""
    try:
        if clean_if_exists and os.path.exists(directory_path):
            if not safe_remove_directory(directory_path, config, description):
                return False

        os.makedirs(directory_path, exist_ok=True)
        _logger.info(f"✅ Created/ensured {description}: {directory_path}")
        return True
    except PermissionError as e:
        _logger.error(f"❌ Permission error creating {description}: {e}")
        return False
    except OSError as e:
        _logger.error(f"❌ OS error creating {description}: {e}")
        return False
    except Exception as e:
        _logger.error(f"❌ Unexpected error creating {description}: {e}")
        return False

def safe_copy_file(source_path, dest_path, config, description="file") -> bool:
    """Safely copy a file with proper error handling."""
    try:
        # Ensure destination directory exists
        dest_dir = os.path.dirname(dest_path)
        if dest_dir and not os.path.exists(dest_dir):
            if not safe_create_directory(dest_dir, config, "destination directory"):
                return False

        shutil.copy2(source_path, dest_path)
        _logger.info(f"✅ Successfully copied {description}: {source_path} → {dest_path}")
        return True
    except FileNotFoundError as e:
        _logger.error(f"❌ Source {description} not found: {source_path}")
        return False
    except PermissionError as e:
        _logger.error(f"❌ Permission error copying {description}: {e}")
        return False
    except OSError as e:
        _logger.error(f"❌ OS error copying {description}: {e}")
        return False
    except Exception as e:
        _logger.error(f"❌ Unexpected error copying {description}: {e}")
        return False

def safe_copy_directory(source_path, dest_path, config, description="directory") -> bool:
    """Safely copy a directory with proper error handling."""
    try:
        # Remove destination if it exists
        if os.path.exists(dest_path):
            _logger.info(f"🗑️  Removing existing {description}: {dest_path}")
            if not safe_remove_directory(dest_path, config, description):
                return False

        shutil.copytree(source_path, dest_path)
        _logger.info(f"✅ Successfully copied {description}: {source_path} → {dest_path}")
        return True
    except FileNotFoundError as e:
        _logger.error(f"❌ Source {description} not found: {source_path}")
        return False
    except PermissionError as e:
        _logger.error(f"❌ Permission error copying {description}: {e}")
        return False
    except OSError as e:
        _logger.error(f"❌ OS error copying {description}: {e}")
        return False
    except Exception as e:
        _logger.error(f"❌ Unexpected error copying {description}: {e}")
        return False

def safe_file_exists(file_path, config, description="file") -> bool:
    """Safely check if a file exists with proper error handling."""
    try:
        exists = os.path.isfile(file_path)
        if not exists:
            _logger.warning(f"⚠️  {description.capitalize()} not found: {file_path}")
        return exists
    except Exception as e:
        _logger.debug(f"❌ Error checking {description}: {e}")
        return False

def safe_directory_exists(directory_path, config, description="directory") -> bool:
    """Safely check if a directory exists with proper error handling."""
    try:
        exists = os.path.isdir(directory_path)
        if not exists:
            _logger.debug(f"⚠️  {description.capitalize()} not found: {directory_path}")
        return exists
    except Exception as e:
        _logger.debug(f"❌ Error checking {description}: {e}")
        return False

# Load configuration
def load_config(config_path=None) -> dict:
    """Load build configuration from JSON file."""
    if config_path is None:
        # Default to shipping config
        config_path = "shipping"
    elif not os.path.isabs(config_path):
        # If relative path, assume it's a build name (without .json extension)
        config_path = config_path

    # Construct the full path to the config file
    if not config_path.endswith('.json'):
        config_file = f"{config_path}.json"
    else:
        config_file = config_path

    config_dir = "build/configs"
    full_config_path = os.path.join(config_dir, config_file)

    try:
        with open(full_config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {full_config_path}")
        print(f"Available configurations in {config_dir}:")
        if os.path.exists(config_dir):
            for file in os.listdir(config_dir):
                if file.endswith('.json'):
                    print(f"  - {file[:-5]}")  # Remove .json extension
        else:
            print(f"  Directory {config_dir} does not exist")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in configuration file: {e}")
        sys.exit(1)

# Global CONFIG variable (will be set in main function)
CONFIG = None

def detect_platform() -> str:
    """Detect the current OS platform as one of: windows, macos, linux, other."""
    try:
        platform_key = sys.platform
        if platform_key.startswith("win"):
            return "Windows"
        if platform_key == "darwin":
            return "MacOs"
        if platform_key.startswith("linux"):
            return "Linux"
        return platform_key
    except Exception:
        return "other"

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

def sign_executable(executable_path, config) -> bool:
    """Sign the executable with the certificate if available."""
    if not config["code_signing"]["enabled"]:
        _logger.info("⏭️  Code signing disabled in config")
        return False

    certificate_path = config["code_signing"]["certificate"]
    signtool_path = config["code_signing"]["signtool"]
    timestamp_server = config["code_signing"]["timestamp_server"]
    digest_algorithm = config["code_signing"]["digest_algorithm"]

    if not safe_file_exists(certificate_path, config, "certificate"):
        _logger.warning("Skipping code signing...")
        return False

    if not safe_file_exists(signtool_path, config, "signtool"):
        _logger.warning("Skipping code signing...")
        return False

    if not safe_file_exists(executable_path, config, "executable"):
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

        _logger.info(f"🔐 Signing executable: {executable_path}")
        _logger.debug(f"Using certificate: {certificate_path}")

        result = subprocess.run(sign_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            _logger.info("✅ Executable signed successfully!")
            return True
        else:
            _logger.warning(f"❌ Code signing failed with error code: {result.returncode}")
            _logger.debug(f"Error output: {result.stderr}")
            return False

    except FileNotFoundError:
        _logger.warning(f"❌ {signtool_path} not found. Make sure Windows SDK is installed.")
        _logger.warning("You can install it via Visual Studio Installer or download from Microsoft.")
        return False
    except Exception as e:
        _logger.error(f"❌ Error during code signing: {e}")
        return False

def clean_directories(config, config_name) -> bool:
    """Clean dist directory and prepare temp directory."""
    dist_dir = config["directories"]["dist"]
    temp_dir = config["directories"]["temp"]

    # Clean config-specific dist subdirectory if specified
    config_dist_dir = os.path.join(dist_dir, config_name)
    if not safe_create_directory(config_dist_dir, config, "config dist directory", clean_if_exists=True):
        _logger.warning(f"❌ Failed to prepare config dist directory: {config_dist_dir}")
        return False

    # Clean temp directory only if clean_temp is enabled
    if config["build_options"]["clean_temp"]:
        if not safe_create_directory(temp_dir, config, "temp directory", clean_if_exists=True):
            _logger.warning(f"❌ Failed to prepare temp directory: {temp_dir}")
            return False
    else:
        # Just ensure temp directory exists
        if not safe_create_directory(temp_dir, config, "temp directory"):
            _logger.warning(f"❌ Failed to ensure temp directory exists: {temp_dir}")
            return False

    return True

def build_version_file(config) -> None:
    """Build the version file."""
    if config["build_options"]["build_version_file"]:
        # Import and run the version generation script directly
        import sys
        import os

        # Add the version directory to the path so we can import the script
        version_dir = os.path.abspath("build/version")
        sys.path.insert(0, version_dir)

        try:
            import generate_version  # type: ignore # noqa: F401
            # The script should run its main logic when imported
            generate_version.main()
            _logger.info("✅ Version file generated successfully")
        except ImportError as e:
            _logger.error(f"❌ Failed to import generate_version.py: {e}")
            sys.exit(1)
        finally:
            # Clean up the path
            sys.path.pop(0)
    else:
        _logger.info("⏭️  Version file generation disabled in config")

def copy_build_files(config) -> bool:
    """Copy necessary files to temp directory."""
    icon_file = config["files"]["icon"]
    version_file = config["files"]["version"]
    temp_dir = config["directories"]["temp"]
    src_dir = config["directories"]["source"]
    resources_dir = config["directories"]["resources"]

    # Ensure temp directory exists (in case clean_directories wasn't called)
    if not safe_create_directory(temp_dir, config, "temp directory"):
        _logger.warning(f"❌ Failed to ensure temp directory exists: {temp_dir}")
        return False

    # Copy icon and version files (these will overwrite existing files)
    icon_dest = os.path.join(temp_dir, "deerhide_default.ico")
    version_dest = os.path.join(temp_dir, "VSVersionInfo")

    if not safe_copy_file(icon_file, icon_dest, config, "icon file"):
        return False

    if not safe_copy_file(version_file, version_dest, config, "version file"):
        return False

    # Handle src directory - remove if exists, then copy
    temp_src_dir = os.path.join(temp_dir, "src")
    if not safe_copy_directory(src_dir, temp_src_dir, config, "source directory"):
        return False

    # Handle resources directory - copy if it exists
    if os.path.exists(resources_dir):
        temp_resources_dir = os.path.join(temp_dir, "resources")
        if not safe_copy_directory(resources_dir, temp_resources_dir, config, "resources directory"):
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
            "--icon", config["pyinstaller"]["options"]["icon"],
            "--distpath", dist_dir,  # Use config-specific dist directory
            "--workpath", work_dir,  # Use absolute path
            "--specpath", spec_dir,  # Use absolute path
            "--paths", "src",  # Use local src directory
            "--name", config["pyinstaller"]["name"],
            "--version-file", config["pyinstaller"]["options"]["version_file"],
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

    # Use config-specific dist directory (single file structure)
    config_dist_dir = os.path.join(dist_dir, config_name)

    if not safe_directory_exists(config_dist_dir, config, "config dist directory"):
        _logger.warning(f"⚠️  Warning: Could not find dist directory at {config_dist_dir}")
        return False

    license_dest = os.path.join(config_dist_dir, f"{config['pyinstaller']['name']}_LICENSE.md")
    readme_dest = os.path.join(config_dist_dir, f"{config['pyinstaller']['name']}_README.md")

    success = True
    if not safe_copy_file(license_file, license_dest, config, "license file"):
        success = False

    if not safe_copy_file(readme_file, readme_dest, config, "readme file"):
        success = False

    if success:
        _logger.info("✅ Documentation copied successfully")

    return success

def cleanup_temp_files(config) -> bool:
    """Clean up temporary files after build completion."""
    temp_dir = config["directories"]["temp"]

    if safe_directory_exists(temp_dir, config, "temp directory"):
        if safe_remove_directory(temp_dir, config, "temp directory"):
            _logger.info("✅ Temporary files cleaned up successfully")
        else:
            _logger.warning("⚠️  Warning: Could not clean up temp directory")
    else:
        _logger.debug("⏭️  No temp directory to clean up")

    return True

def main() -> None:
    parser = argparse.ArgumentParser(description="Builder for the Jira Importer application.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-c", "--config",
                       help="Build configuration name (default: shipping)\n"
                            "Configurations are stored in build/configs/BUILDNAME.json\n"
                            "Examples: shipping, dev, debug, release",
                       default="shipping")
    args = parser.parse_args()

    # Load configuration based on argument
    CONFIG = load_config(args.config)

    # Detect and display platform
    current_platform = detect_platform()
    _logger.info(f"🖥️  Detected platform: {current_platform}")

    _logger.info("🚀 Starting Jira Importer build process...")
    print("=" * 20)
    _logger.info(f"📋 Using configuration: {args.config}")
    print("=" * 20)

    # Check dependencies
    _logger.info("📋 Checking dependencies...")
    check_dependencies(CONFIG)

    # Install requirements
    if CONFIG["build_options"]["install_requirements"]:
        _logger.info("📦 Installing requirements...")
        try:
            requirements_file = CONFIG["files"]["requirements"]
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
            _logger.info("✅ Requirements installed successfully")
        except subprocess.CalledProcessError as e:
            _logger.error(f"❌ Failed to install requirements: {e}")
            sys.exit(1)
    else:
        _logger.info("⏭️  Requirements installation disabled in config")

    # Clean and prepare directories
    if CONFIG["build_options"]["clean_dist"]:
        _logger.info("🧹 Preparing build environment...")
        if not clean_directories(CONFIG, args.config):
            _logger.warning("❌ Failed to prepare build environment")
            sys.exit(1)
    else:
        _logger.info("⏭️  Directory cleaning disabled in config")

    # Build version file
    _logger.info("🔨 Building version file...")
    build_version_file(CONFIG)

    # Copy build files
    _logger.info("📁 Copying build files...")
    if not copy_build_files(CONFIG):
        _logger.warning("❌ Failed to copy build files")
        sys.exit(1)

    # Build executable
    _logger.info("🔨 Building executable...")
    build_executable(CONFIG, args.config) # Pass config_name as an argument


    # Code signing (optional)
    dist_dir = CONFIG["directories"]["dist"]
    config_dist_dir = os.path.join(dist_dir, args.config)  # Use config-specific dist directory
    executable_path = os.path.join(config_dist_dir, f"{CONFIG['pyinstaller']['name']}.exe")

    if safe_file_exists(executable_path, CONFIG, "executable"):
        print("\n" + "="*50)
        _logger.info("🔐 CODE SIGNING")
        print("="*50)
        sign_executable(executable_path, CONFIG)
    else:
        _logger.warning(f"⚠️  Warning: Expected executable not found at {executable_path}")
        _logger.debug("Checking for executable in dist directory...")
        # List contents of dist directory to help debug
        if safe_directory_exists(config_dist_dir, CONFIG, "config dist directory"):
            for root, dirs, files in os.walk(config_dist_dir):
                for file in files:
                    if file.endswith('.exe'):
                        _logger.debug(f"Found executable: {os.path.join(root, file)}")

    # Copy documentation
    _logger.info("📚 Copying documentation...")
    if not copy_documentation(CONFIG, args.config):  # Pass config_name
        _logger.warning("⚠️  Warning: Failed to copy documentation")

    # Clean up temporary files based on config setting
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
