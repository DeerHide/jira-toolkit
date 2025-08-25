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

# File/Directory operation utilities with failsafe mechanisms
def safe_remove_directory(directory_path, config, description="directory"):
    """Safely remove a directory with retry logic and proper error handling."""
    if not os.path.exists(directory_path):
        conditional_print(f"⏭️  {description.capitalize()} does not exist: {directory_path}", config, "debug")
        return True
    
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            conditional_print(f"🧹 Removing {description}: {directory_path}", config, "progress")
            shutil.rmtree(directory_path)
            conditional_print(f"✅ Successfully removed {description}: {directory_path}", config, "progress")
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                conditional_print(f"⚠️  Permission error removing {description} (attempt {attempt + 1}/{max_retries}): {e}", config, "warning")
                conditional_print(f"⏳ Waiting {retry_delay} seconds before retry...", config, "debug")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                conditional_print(f"❌ Failed to remove {description} after {max_retries} attempts: {e}", config, "warning")
                return False
        except OSError as e:
            if attempt < max_retries - 1:
                conditional_print(f"⚠️  OS error removing {description} (attempt {attempt + 1}/{max_retries}): {e}", config, "warning")
                conditional_print(f"⏳ Waiting {retry_delay} seconds before retry...", config, "debug")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                conditional_print(f"❌ Failed to remove {description} after {max_retries} attempts: {e}", config, "warning")
                return False
        except Exception as e:
            conditional_print(f"❌ Unexpected error removing {description}: {e}", config, "warning")
            return False
    
    return False

def safe_create_directory(directory_path, config, description="directory", clean_if_exists=False):
    """Safely create a directory with optional cleaning and proper error handling."""
    try:
        if clean_if_exists and os.path.exists(directory_path):
            if not safe_remove_directory(directory_path, config, description):
                return False
        
        os.makedirs(directory_path, exist_ok=True)
        conditional_print(f"✅ Created/ensured {description}: {directory_path}", config, "progress")
        return True
    except PermissionError as e:
        conditional_print(f"❌ Permission error creating {description}: {e}", config, "warning")
        return False
    except OSError as e:
        conditional_print(f"❌ OS error creating {description}: {e}", config, "warning")
        return False
    except Exception as e:
        conditional_print(f"❌ Unexpected error creating {description}: {e}", config, "warning")
        return False

def safe_copy_file(source_path, dest_path, config, description="file"):
    """Safely copy a file with proper error handling."""
    try:
        # Ensure destination directory exists
        dest_dir = os.path.dirname(dest_path)
        if dest_dir and not os.path.exists(dest_dir):
            if not safe_create_directory(dest_dir, config, "destination directory"):
                return False
        
        shutil.copy2(source_path, dest_path)
        conditional_print(f"✅ Successfully copied {description}: {source_path} → {dest_path}", config, "progress")
        return True
    except FileNotFoundError as e:
        conditional_print(f"❌ Source {description} not found: {source_path}", config, "warning")
        return False
    except PermissionError as e:
        conditional_print(f"❌ Permission error copying {description}: {e}", config, "warning")
        return False
    except OSError as e:
        conditional_print(f"❌ OS error copying {description}: {e}", config, "warning")
        return False
    except Exception as e:
        conditional_print(f"❌ Unexpected error copying {description}: {e}", config, "warning")
        return False

def safe_copy_directory(source_path, dest_path, config, description="directory"):
    """Safely copy a directory with proper error handling."""
    try:
        # Remove destination if it exists
        if os.path.exists(dest_path):
            conditional_print(f"🗑️  Removing existing {description}: {dest_path}", config, "progress")
            if not safe_remove_directory(dest_path, config, description):
                return False
        
        shutil.copytree(source_path, dest_path)
        conditional_print(f"✅ Successfully copied {description}: {source_path} → {dest_path}", config, "progress")
        return True
    except FileNotFoundError as e:
        conditional_print(f"❌ Source {description} not found: {source_path}", config, "warning")
        return False
    except PermissionError as e:
        conditional_print(f"❌ Permission error copying {description}: {e}", config, "warning")
        return False
    except OSError as e:
        conditional_print(f"❌ OS error copying {description}: {e}", config, "warning")
        return False
    except Exception as e:
        conditional_print(f"❌ Unexpected error copying {description}: {e}", config, "warning")
        return False

def safe_file_exists(file_path, config, description="file"):
    """Safely check if a file exists with proper error handling."""
    try:
        exists = os.path.isfile(file_path)
        if not exists:
            conditional_print(f"⚠️  {description.capitalize()} not found: {file_path}", config, "debug")
        return exists
    except Exception as e:
        conditional_print(f"❌ Error checking {description}: {e}", config, "debug")
        return False

def safe_directory_exists(directory_path, config, description="directory"):
    """Safely check if a directory exists with proper error handling."""
    try:
        exists = os.path.isdir(directory_path)
        if not exists:
            conditional_print(f"⚠️  {description.capitalize()} not found: {directory_path}", config, "debug")
        return exists
    except Exception as e:
        conditional_print(f"❌ Error checking {description}: {e}", config, "debug")
        return False

# Load configuration
def load_config(config_path=None):
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

def conditional_print(message, config, message_type="info"):
    """Print message based on configuration settings."""
    if not config.get("output_control", {}).get("verbose", True):
        return
    
    # Check specific message type controls
    if message_type == "warning" and not config.get("output_control", {}).get("show_warnings", True):
        return
    elif message_type == "debug" and not config.get("output_control", {}).get("show_debug_info", False):
        return
    elif message_type == "progress" and not config.get("output_control", {}).get("show_progress", True):
        return
    
    print(message)

def check_dependencies(config):
    """Check if required dependencies are available."""
    if not config["build_options"]["check_dependencies"]:
        conditional_print("⏭️  Dependency checking disabled in config", config)
        return
        
    for dependency in config["dependencies"]["required"]:
        try:
            __import__(dependency.lower())
            conditional_print(f"✅ {dependency} is available", config, "progress")
        except ImportError:
            conditional_print(f"❌ {dependency} not found. Installing...", config, "warning")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dependency.lower()])

def sign_executable(executable_path, config):
    """Sign the executable with the certificate if available."""
    if not config["code_signing"]["enabled"]:
        conditional_print("⏭️  Code signing disabled in config", config)
        return False
        
    certificate_path = config["code_signing"]["certificate"]
    signtool_path = config["code_signing"]["signtool"]
    timestamp_server = config["code_signing"]["timestamp_server"]
    digest_algorithm = config["code_signing"]["digest_algorithm"]
    
    if not safe_file_exists(certificate_path, config, "certificate"):
        conditional_print("Skipping code signing...", config, "warning")
        return False
    
    if not safe_file_exists(signtool_path, config, "signtool"):
        conditional_print("Skipping code signing...", config, "warning")
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
        
        conditional_print(f"🔐 Signing executable: {executable_path}", config, "progress")
        conditional_print(f"Using certificate: {certificate_path}", config, "debug")
        
        result = subprocess.run(sign_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            conditional_print("✅ Executable signed successfully!", config, "progress")
            return True
        else:
            conditional_print(f"❌ Code signing failed with error code: {result.returncode}", config, "warning")
            conditional_print(f"Error output: {result.stderr}", config, "debug")
            return False
            
    except FileNotFoundError:
        conditional_print(f"❌ {signtool_path} not found. Make sure Windows SDK is installed.", config, "warning")
        conditional_print("You can install it via Visual Studio Installer or download from Microsoft.", config, "warning")
        return False
    except Exception as e:
        conditional_print(f"❌ Error during code signing: {e}", config, "warning")
        return False

def clean_directories(config, config_name):
    """Clean dist directory and prepare temp directory."""
    dist_dir = config["directories"]["dist"]
    temp_dir = config["directories"]["temp"]
    
    # Clean config-specific dist subdirectory if specified
    config_dist_dir = os.path.join(dist_dir, config_name)
    if not safe_create_directory(config_dist_dir, config, "config dist directory", clean_if_exists=True):
        conditional_print(f"❌ Failed to prepare config dist directory: {config_dist_dir}", config, "warning")
        return False
    
    # Clean temp directory only if clean_temp is enabled
    if config["build_options"]["clean_temp"]:
        if not safe_create_directory(temp_dir, config, "temp directory", clean_if_exists=True):
            conditional_print(f"❌ Failed to prepare temp directory: {temp_dir}", config, "warning")
            return False
    else:
        # Just ensure temp directory exists
        if not safe_create_directory(temp_dir, config, "temp directory"):
            conditional_print(f"❌ Failed to ensure temp directory exists: {temp_dir}", config, "warning")
            return False
    
    return True

def build_version_file(config):
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
            conditional_print("✅ Version file generated successfully", config, "progress")
        except ImportError as e:
            conditional_print(f"❌ Failed to import generate_version.py: {e}", config, "warning")
            sys.exit(1)
        finally:
            # Clean up the path
            sys.path.pop(0)
    else:
        conditional_print("⏭️  Version file generation disabled in config", config)

def copy_build_files(config):
    """Copy necessary files to temp directory."""
    icon_file = config["files"]["icon"]
    version_file = config["files"]["version"]
    temp_dir = config["directories"]["temp"]
    src_dir = config["directories"]["source"]
    
    # Ensure temp directory exists (in case clean_directories wasn't called)
    if not safe_create_directory(temp_dir, config, "temp directory"):
        conditional_print(f"❌ Failed to ensure temp directory exists: {temp_dir}", config, "warning")
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
    
    conditional_print("✅ Build files copied to temp directory successfully", config, "progress")
    return True

def build_executable(config, config_name):
    """Build the executable using PyInstaller."""
    src_dir = config["directories"]["source"]
    main_script = os.path.join(src_dir, "main.py")
    if not os.path.isfile(main_script):
        for candidate in ["main.py", "app.py"]:
            candidate_path = os.path.join(src_dir, candidate)
            if os.path.isfile(candidate_path):
                main_script = candidate_path
                break
        else:
            raise FileNotFoundError(f"No main.py or app.py found in {src_dir} for PyInstaller compilation.")

    conditional_print(f"🔨 Building executable from: {main_script}", config, "progress")
    
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
            "--onefile",  
            "--console" if config["pyinstaller"]["console"] else "--windowed",
            "--icon", config["pyinstaller"]["options"]["icon"],
            "--distpath", dist_dir,  # Use config-specific dist directory
            "--workpath", work_dir,  # Use absolute path
            "--specpath", spec_dir,  # Use absolute path
            "--paths", "src",  # Use local src directory
            "--name", config["pyinstaller"]["name"],
            "--version-file", config["pyinstaller"]["options"]["version_file"]
        ]
        
        # Add data files
        for data_file in config["pyinstaller"]["add_data"]:
            pyinstaller_cmd.extend(["--add-data", data_file])
        
        # Add main script - use local src directory
        pyinstaller_cmd.append("src/main.py")
        
        subprocess.check_call(pyinstaller_cmd)
        conditional_print("✅ Executable built successfully!", config, "progress")
    except subprocess.CalledProcessError as e:
        conditional_print(f"❌ PyInstaller build failed: {e}", config, "warning")
        sys.exit(1)
    finally:
        # Always restore original working directory
        os.chdir(original_cwd)

def copy_documentation(config, config_name):
    """Copy documentation files to dist directory."""
    if not config["build_options"]["copy_documentation"]:
        conditional_print("⏭️  Documentation copying disabled in config", config)
        return True
        
    dist_dir = config["directories"]["dist"]
    license_file = config["files"]["license"]
    readme_file = config["files"]["readme"]
    
    # Use config-specific dist directory (single file structure)
    config_dist_dir = os.path.join(dist_dir, config_name)
    
    if not safe_directory_exists(config_dist_dir, config, "config dist directory"):
        conditional_print(f"⚠️  Warning: Could not find dist directory at {config_dist_dir}", config, "warning")
        return False
    
    license_dest = os.path.join(config_dist_dir, f"{config['pyinstaller']['name']}_LICENSE.md")
    readme_dest = os.path.join(config_dist_dir, f"{config['pyinstaller']['name']}_README.md")
    
    success = True
    if not safe_copy_file(license_file, license_dest, config, "license file"):
        success = False
    
    if not safe_copy_file(readme_file, readme_dest, config, "readme file"):
        success = False
    
    if success:
        conditional_print("✅ Documentation copied successfully", config, "progress")
    
    return success

def cleanup_temp_files(config):
    """Clean up temporary files after build completion."""
    temp_dir = config["directories"]["temp"]
    
    if safe_directory_exists(temp_dir, config, "temp directory"):
        if safe_remove_directory(temp_dir, config, "temp directory"):
            conditional_print("✅ Temporary files cleaned up successfully", config, "progress")
        else:
            conditional_print("⚠️  Warning: Could not clean up temp directory", config, "warning")
    else:
        conditional_print("⏭️  No temp directory to clean up", config, "debug")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Builder for the Jira Importer application.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-c", "--config", 
                       help="Build configuration name (default: shipping)\n"
                            "Configurations are stored in build/configs/BUILDNAME.json\n"
                            "Examples: shipping, dev, debug, release", 
                       default="shipping")
    args = parser.parse_args()

    # Load configuration based on argument
    CONFIG = load_config(args.config)

    conditional_print("🚀 Starting Jira Importer build process...", CONFIG, "progress")
    conditional_print("=" * 50, CONFIG)
    conditional_print(f"📋 Using configuration: {args.config}", CONFIG, "progress")
    conditional_print("=" * 50, CONFIG)
    
    # Check dependencies
    conditional_print("📋 Checking dependencies...", CONFIG, "progress")
    check_dependencies(CONFIG)
    
    # Install requirements
    if CONFIG["build_options"]["install_requirements"]:
        conditional_print("📦 Installing requirements...", CONFIG, "progress")
        try:
            requirements_file = CONFIG["files"]["requirements"]
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
            conditional_print("✅ Requirements installed successfully", CONFIG, "progress")
        except subprocess.CalledProcessError as e:
            conditional_print(f"❌ Failed to install requirements: {e}", CONFIG, "warning")
            sys.exit(1)
    else:
        conditional_print("⏭️  Requirements installation disabled in config", CONFIG)
    
    # Clean and prepare directories
    if CONFIG["build_options"]["clean_dist"]:
        conditional_print("🧹 Preparing build environment...", CONFIG, "progress")
        if not clean_directories(CONFIG, args.config):
            conditional_print("❌ Failed to prepare build environment", CONFIG, "warning")
            sys.exit(1)
    else:
        conditional_print("⏭️  Directory cleaning disabled in config", CONFIG)
    
    # Build version file
    conditional_print("🔨 Building version file...", CONFIG, "progress")
    build_version_file(CONFIG)
    
    # Copy build files
    conditional_print("📁 Copying build files...", CONFIG, "progress")
    if not copy_build_files(CONFIG):
        conditional_print("❌ Failed to copy build files", CONFIG, "warning")
        sys.exit(1)
    
    # Build executable
    conditional_print("🔨 Building executable...", CONFIG, "progress")
    build_executable(CONFIG, args.config) # Pass config_name as an argument
    
    # Code signing (optional)
    dist_dir = CONFIG["directories"]["dist"]
    config_dist_dir = os.path.join(dist_dir, args.config)  # Use config-specific dist directory
    executable_path = os.path.join(config_dist_dir, f"{CONFIG['pyinstaller']['name']}.exe")
    
    if safe_file_exists(executable_path, CONFIG, "executable"):
        conditional_print("\n" + "="*50, CONFIG)
        conditional_print("🔐 CODE SIGNING", CONFIG, "progress")
        conditional_print("="*50, CONFIG)
        sign_executable(executable_path, CONFIG)
    else:
        conditional_print(f"⚠️  Warning: Expected executable not found at {executable_path}", CONFIG, "warning")
        conditional_print("Checking for executable in dist directory...", CONFIG, "debug")
        # List contents of dist directory to help debug
        if safe_directory_exists(config_dist_dir, CONFIG, "config dist directory"):
            for root, dirs, files in os.walk(config_dist_dir):
                for file in files:
                    if file.endswith('.exe'):
                        conditional_print(f"Found executable: {os.path.join(root, file)}", CONFIG, "debug")
    
    # Copy documentation
    conditional_print("📚 Copying documentation...", CONFIG, "progress")
    if not copy_documentation(CONFIG, args.config):  # Pass config_name
        conditional_print("⚠️  Warning: Failed to copy documentation", CONFIG, "warning")
    
    # Clean up temporary files based on config setting
    if CONFIG["build_options"]["clean_temp"]:
        if not cleanup_temp_files(CONFIG):
            conditional_print("⚠️  Warning: Failed to clean up temporary files", CONFIG, "warning")
    else:
        conditional_print("💾 Keeping temporary files (clean_temp disabled in config)", CONFIG, "progress")
        temp_dir = CONFIG["directories"]["temp"]
        conditional_print(f"📁 Temp files location: {temp_dir}", CONFIG, "progress")
    
    conditional_print("\n" + "="*50, CONFIG)
    conditional_print("🎉 Build completed successfully!", CONFIG, "progress")
    conditional_print(f"📦 Executable location: {config_dist_dir}", CONFIG, "progress")
    conditional_print("="*50, CONFIG)

if __name__ == "__main__":
    main()