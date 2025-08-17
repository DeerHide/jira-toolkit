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

# Load configuration
def load_config(config_path=None):
    """Load build configuration from JSON file."""
    if config_path is None:
        config_path = os.path.join("rsc", "build-config.json")
    elif not os.path.isabs(config_path):
        # If relative path, assume it's relative to rsc directory
        config_path = os.path.join("rsc", config_path)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        print("Please ensure the configuration file exists")
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
    
    if not os.path.exists(certificate_path):
        conditional_print(f"⚠️  Certificate not found at {certificate_path}", config, "warning")
        conditional_print("Skipping code signing...", config, "warning")
        return False
    
    if not os.path.exists(signtool_path):
        conditional_print(f"⚠️  signtool not found at {signtool_path}", config, "warning")
        conditional_print("Skipping code signing...", config, "warning")
        return False
    
    if not os.path.exists(executable_path):
        conditional_print(f"❌ Executable not found at {executable_path}", config, "warning")
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

def clean_directories(config):
    """Clean build and dist directories."""
    build_dir = config["directories"]["build"]
    dist_dir = config["directories"]["dist"]
    
    for directory in [build_dir, dist_dir]:
        if os.path.isdir(directory):
            conditional_print(f"🧹 Cleaning {directory} directory...", config, "progress")
            shutil.rmtree(directory)
        os.makedirs(directory)
        conditional_print(f"✅ Created {directory} directory", config, "progress")

def build_version_file(config):
    """Build the version file."""
    if config["build_options"]["build_version_file"]:
        rsc_dir = config["directories"]["resources"]
        subprocess.check_call([sys.executable, os.path.join(rsc_dir, "generate_version.py")])
        conditional_print("✅ Version file generated successfully", config, "progress")
    else:
        conditional_print("⏭️  Version file generation disabled in config", config)

def copy_build_files(config):
    """Copy necessary files to build directory."""
    try:
        icon_file = config["files"]["icon"]
        version_file = config["files"]["version"]
        build_dir = config["directories"]["build"]
        src_dir = config["directories"]["source"]
        
        shutil.copy(icon_file, os.path.join(build_dir, "deerhide_default.ico"))
        shutil.copy(version_file, os.path.join(build_dir, "VSVersionInfo"))
        shutil.copytree(src_dir, os.path.join(build_dir, "src"))
        conditional_print("✅ Build files copied successfully", config, "progress")
    except Exception as e:
        conditional_print(f"❌ Error copying build files: {e}", config, "warning")
        sys.exit(1)

def build_executable(config):
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
    
    # Change to build directory for PyInstaller
    build_dir = config["directories"]["build"]
    original_cwd = os.getcwd()
    os.chdir(build_dir)
    
    try:
        pyinstaller_cmd = [
            "pyinstaller",
            "--onedir",  # Explicitly use onedir mode
            "--console" if config["pyinstaller"]["console"] else "--windowed",
            "--icon", config["pyinstaller"]["options"]["icon"],
            "--distpath", config["pyinstaller"]["options"]["distpath"],
            "--workpath", config["pyinstaller"]["options"]["workpath"],
            "--specpath", config["pyinstaller"]["options"]["specpath"],
            "--paths", config["pyinstaller"]["options"]["paths"],
            "--name", config["pyinstaller"]["name"],
            "--version-file", config["pyinstaller"]["options"]["version_file"]
        ]
        
        # Add data files
        for data_file in config["pyinstaller"]["add_data"]:
            pyinstaller_cmd.extend(["--add-data", data_file])
        
        # Add main script - use relative path from build directory
        pyinstaller_cmd.append("../src/jira_importer/main.py")
        
        subprocess.check_call(pyinstaller_cmd)
        conditional_print("✅ Executable built successfully!", config, "progress")
    except subprocess.CalledProcessError as e:
        conditional_print(f"❌ PyInstaller build failed: {e}", config, "warning")
        sys.exit(1)
    finally:
        # Always restore original working directory
        os.chdir(original_cwd)

def copy_documentation(config):
    """Copy documentation files to dist directory."""
    if not config["build_options"]["copy_documentation"]:
        conditional_print("⏭️  Documentation copying disabled in config", config)
        return
        
    try:
        dist_dir = config["directories"]["dist"]
        app_dir_output = config["directories"]["app_output"]
        license_file = config["files"]["license"]
        readme_file = config["files"]["readme"]
        
        # Find the actual dist directory structure
        dist_app_dir = os.path.join(dist_dir, app_dir_output)
        if not os.path.exists(dist_app_dir):
            # Try alternative naming
            dist_app_dir = os.path.join(dist_dir, config["pyinstaller"]["name"])
        
        if os.path.exists(dist_app_dir):
            shutil.copy(license_file, os.path.join(dist_app_dir, f"{config['pyinstaller']['name']}_LICENSE.md"))
            shutil.copy(readme_file, os.path.join(dist_app_dir, f"{config['pyinstaller']['name']}_README.md"))
            conditional_print("✅ Documentation copied successfully", config, "progress")
        else:
            conditional_print(f"⚠️  Warning: Could not find dist app directory at {dist_app_dir}", config, "warning")
    except Exception as e:
        conditional_print(f"⚠️  Warning: Could not copy documentation: {e}", config, "warning")

def main():
    parser = argparse.ArgumentParser(description="Builder for the Jira Importer application.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-c", "--config", 
                       help="Configuration file path (default: build-config.json, dev: build-config-dev.json, shipping: build-config-shipping.json)", 
                       default="build-config.json")
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
    if CONFIG["build_options"]["clean_build"] or CONFIG["build_options"]["clean_dist"]:
        conditional_print("🧹 Preparing build environment...", CONFIG, "progress")
        clean_directories(CONFIG)
    else:
        conditional_print("⏭️  Directory cleaning disabled in config", CONFIG)
    
    # Build version file
    conditional_print("🔨 Building version file...", CONFIG, "progress")
    build_version_file(CONFIG)
    
    # Copy build files
    conditional_print("📁 Copying build files...", CONFIG, "progress")
    copy_build_files(CONFIG)
    
    # Build executable
    conditional_print("🔨 Building executable...", CONFIG, "progress")
    build_executable(CONFIG)
    
    # Code signing (optional)
    dist_dir = CONFIG["directories"]["dist"]
    app_dir_output = CONFIG["directories"]["app_output"]
    executable_path = os.path.join(dist_dir, app_dir_output, f"{CONFIG['pyinstaller']['name']}.exe")
    if not os.path.exists(executable_path):
        # Try alternative naming
        executable_path = os.path.join(dist_dir, CONFIG["pyinstaller"]["name"], f"{CONFIG['pyinstaller']['name']}.exe")
    
    if os.path.exists(executable_path):
        conditional_print("\n" + "="*50, CONFIG)
        conditional_print("🔐 CODE SIGNING", CONFIG, "progress")
        conditional_print("="*50, CONFIG)
        sign_executable(executable_path, CONFIG)
    else:
        conditional_print(f"⚠️  Warning: Expected executable not found at {executable_path}", CONFIG, "warning")
        conditional_print("Checking for executable in dist directory...", CONFIG, "debug")
        # List contents of dist directory to help debug
        if os.path.exists(dist_dir):
            for root, dirs, files in os.walk(dist_dir):
                for file in files:
                    if file.endswith('.exe'):
                        conditional_print(f"Found executable: {os.path.join(root, file)}", CONFIG, "debug")
    
    # Copy documentation
    conditional_print("📚 Copying documentation...", CONFIG, "progress")
    copy_documentation(CONFIG)
    
    conditional_print("\n" + "="*50, CONFIG)
    conditional_print("🎉 Build completed successfully!", CONFIG, "progress")
    conditional_print(f"📦 Executable location: {os.path.join(dist_dir, app_dir_output)}", CONFIG, "progress")
    conditional_print("="*50, CONFIG)

if __name__ == "__main__":
    main()