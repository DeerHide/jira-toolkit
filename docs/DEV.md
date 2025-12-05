# Developer Guide

Welcome to the Jira Importer Toolkit! This guide will help you get started with development, understand the codebase, and contribute to the project.

## 📚 Documentation Overview

The documentation is organized into focused files for easy navigation:

- **[DEV.md](DEV.md)** - This file: Development setup and workflow
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and component details
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines and code standards
- **[CONFIG.md](CONFIG.md)** - Configuration system documentation
- **[CLOUD.md](CLOUD.md)** - Jira Cloud API integration details
- **[FEATURES.md](FEATURES.md)** - Comprehensive feature documentation

## 🚀 Let's Get Started

### Prerequisites

- **Python 3.12+** (required for modern features and performance)
- **Git** for version control
- **pip** or **Poetry** for package management
- **Cross-platform** development (Windows, macOS, Linux)
- **Jira Cloud account** (for testing cloud integration features)

### Setup Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/DeerHide/jira-toolkit.git
   cd jira-toolkit
   ```

2. **Set up your environment**

   ```bash
   # Create virtual environment
   python -m venv .venv

   # Activate it
   # On Windows:
   .venv\Scripts\activate

   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**

   The project supports both pip-tools and Poetry for dependency management:

   **Option A: Using pip-tools (recommended)**
   ```bash
   # Install pip-tools for dependency management
   pip install pip-tools

   # Generate/refresh requirements.lock (if needed)
   pip-compile requirements.in

   # Install all dependencies
   pip install -r requirements.lock
   python -m pip install -e .[dev]
   ```

   **Option B: Using Poetry**
   ```bash
   poetry install --with dev
   ```

4. **Verify installation**

   ```bash
   python -m jira_importer --version
   python -m jira_importer --help
   ```

## 📁 Project Layout

## 📁 Project Structure

### Repository Layout

```text
jira-toolkit/                    # Repository root
├── src/                         # Source code
│   └── jira_importer/          # Main application package
├── build/                       # Build assets and working directories
│   ├── configs/                 # Build configuration files
│   ├── icons/                   # Application icons
│   ├── logs/                    # Build logs
│   └── version/                 # Version generation scripts
├── dist/                        # Build output directory
├── resources/                   # Runtime resources and templates
│   ├── Samples/                 # Sample data files
│   └── Templates/               # Excel and JSON templates
├── docs/                        # Documentation
├── scripts/                     # Helper scripts and utilities
├── tests/                       # Test files and data
├── build.py                     # Main build script
├── pyproject.toml              # Poetry configuration
├── requirements.in              # Python dependencies (source)
├── requirements.lock           # Python dependencies (locked)
└── README.md                   # User documentation
```

### Application Architecture

```text
src/jira_importer/               # Main application package
├── __main__.py                  # CLI entry point
├── app.py                       # Application logic and argument parsing
├── config/                      # Configuration management
│   ├── config_factory.py       # Configuration factory
│   ├── config_view.py           # Typed configuration access
│   ├── config_models.py         # Configuration data models
│   ├── config_display.py        # Configuration display utilities
│   ├── excel_config.py         # Excel-based configuration
│   ├── json_config.py          # JSON configuration
│   ├── constants.py            # Configuration constants
│   ├── utils.py                # Configuration utilities
│   └── models/                  # Configuration models
│       └── issuetypes.py        # Issue type hierarchy models
├── excel/                       # Excel processing
│   ├── excel_io.py             # Excel workbook management
│   └── excel_table_reader.py   # Excel table configuration reader
├── import_pipeline/             # Core import processing
│   ├── processor.py             # Main pipeline orchestrator
│   ├── models.py                # Data models and interfaces
│   ├── validator.py             # Validation engine
│   ├── reporting.py             # Problem reporting
│   ├── rules/                   # Validation rules
│   │   ├── registry.py          # Rule registry
│   │   ├── builtin_rules.py     # Built-in validation rules
│   │   └── excel_rule_loader.py # Excel-defined rules
│   ├── fixes/                   # Auto-fix system
│   │   ├── registry.py          # Fix registry
│   │   └── builtin_fixes.py     # Built-in auto-fixes
│   ├── sources/                 # Input readers
│   │   ├── csv_source.py        # CSV file reader
│   │   └── xlsx_source.py       # Excel file reader
│   ├── sinks/                   # Output writers
│   │   ├── csv_sink.py          # CSV output writer
│   │   ├── cloud_sink.py        # Jira Cloud API writer
│   │   └── sink_utils.py        # Sink utilities
│   └── cloud/                   # Cloud integration
│       ├── auth.py              # Authentication providers
│       ├── client.py            # HTTP client wrapper
│       ├── credential_manager.py # Credential management
│       ├── secrets.py           # Secrets resolution
│       ├── mappers.py           # Data mapping to Jira format
│       ├── metadata.py          # Jira metadata caching
│       ├── bulk.py              # Batch processing utilities
│       └── constants.py         # Cloud-specific constants
├── fileops.py                   # File operations
├── artifacts.py                 # Artifact management
├── console.py                   # Rich console UI
├── log.py                       # Logging utilities
├── utils.py                     # Utility functions
└── version.py                   # Version information (auto-generated)
```

## 🏗️ System Architecture

The Jira Importer Toolkit follows a modular, pipeline-based architecture designed for extensibility and maintainability:

### Core Design Principles

- **Modular Pipeline**: Clean separation between input, processing, and output stages
- **Immutable Processing**: Rules and fixes return patches instead of mutating data
- **Extensible Validation**: Built-in rules + framework for custom Excel-defined rules
- **Auto-fix System**: Safe, configurable fixes for common validation issues
- **Rich Reporting**: Comprehensive console output with problem aggregation
- **Cloud Integration**: Direct Jira Cloud API integration with batch processing

### Key Components

- **ImportProcessor** - Main orchestrator handling the entire pipeline flow
- **Validation Engine** - Rule-based validation with auto-fix capabilities
- **Configuration System** - Flexible configuration from JSON, Excel, or defaults
- **Cloud Integration** - Direct Jira Cloud API integration with authentication
- **Rich UI** - Modern console interface with progress indicators and tables

For detailed technical information, see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## 🛠️ Development Workflow

### Running the Application

1. **Basic usage**
   ```bash
   python -m jira_importer path/to/your/file.xlsx
   ```

2. **Debug mode** (detailed logging)
   ```bash
   python -m jira_importer path/to/your/file.xlsx --debug
   ```

3. **Auto-fix enabled** (automatic issue resolution)
   ```bash
   python -m jira_importer path/to/your/file.xlsx --auto-fix
   ```

4. **Cloud import** (direct to Jira Cloud)
   ```bash
   python -m jira_importer path/to/your/file.xlsx --cloud
   ```

5. **Credential management**
   ```bash
   python -m jira_importer --credentials run    # Set up credentials
   python -m jira_importer --credentials show   # View stored credentials
   python -m jira_importer --credentials clear  # Clear credentials
   ```

6. **Excel configuration**
   ```bash
   python -m jira_importer path/to/your/file.xlsx --config-excel
   ```

7. **Dry-run mode** (test without writing output)
   ```bash
   python -m jira_importer path/to/your/file.xlsx --dry-run
   ```

8. **Configuration display** (show config without input file)
   ```bash
   python -m jira_importer --show-config
   ```

### Building the Application

1. **Development build** (for testing)
   ```bash
   python build.py -c dev
   ```

2. **Production build** (for distribution)
   ```bash
   python build.py -c shipping
   ```

3. **Using Poetry** (alternative build method)
   ```bash
   poetry build --format pyinstaller
   ```

### Testing Your Changes

1. **Use sample data**
   - Copy `resources/templates/ImportTemplate.xlsx` to your working directory
   - Modify it with test data
   - Run the importer on your test file

2. **Enable debug mode**
   - Use the `--debug` flag for detailed logging
   - Check console output for information

3. **Test cloud integration**
   - Set up credentials with `--credentials run`
   - Test with `--cloud` flag
   - Verify authentication and API calls

## 🔧 Key Development Components

### Import Pipeline (`import_pipeline/`)

The core processing logic handles validation, fixes, and data transformation:

- **`processor.py`** - Main orchestrator managing the entire pipeline flow
- **`models.py`** - Data structures and interfaces for the pipeline
- **`validator.py`** - Validation engine with rule-based processing
- **`rules/`** - Validation rules (built-in + extensible Excel-defined rules)
- **`fixes/`** - Auto-fix system for common validation issues
- **`sources/`** - Input readers for CSV and XLSX files
- **`sinks/`** - Output writers (CSV, cloud integration)
- **`reporting.py`** - Rich problem reporting with tables and formatting

### Configuration System (`config/`)

Flexible configuration management supporting multiple sources:

- **`config_factory.py`** - Unified configuration loading from multiple sources
- **`config_view.py`** - Typed configuration access with validation
- **`config_models.py`** - Configuration data models and structures
- **`excel_config.py`** - Excel-based configuration handling
- **`json_config.py`** - JSON configuration file processing
- **`models/issuetypes.py`** - Issue type hierarchy models

### Cloud Integration (`import_pipeline/cloud/`)

Direct Jira Cloud API integration with advanced features:

- **`auth.py`** - Authentication providers (Basic Auth fully implemented; OAuth 2.0 scaffolded but not functional)
- **`client.py`** - HTTP client wrapper for Jira Cloud REST API v3
- **`credential_manager.py`** - Advanced credential management with keyring
- **`secrets.py`** - Secrets resolution (keyring → env → config → prompt)
- **`mappers.py`** - Data mapping from normalized rows to Jira issue payloads
- **`metadata.py`** - Jira metadata caching (projects, fields, issue types)
- **`bulk.py`** - Batch processing utilities for efficient imports
- **`constants.py`** - Cloud-specific constants and configuration

### Excel Processing (`excel/`)

Enhanced Excel workbook management and processing:

- **`excel_io.py`** - Excel workbook management with metadata support
- **`excel_table_reader.py`** - Structured table configuration reader
- Direct XLSX processing (no intermediate CSV conversion)
- Metadata writing and processing reports

### Console UI (`console.py`)

Modern console interface with rich formatting:

- Rich console output with tables and formatting
- Progress bars and user interaction
- Consistent theming and styling
- Error reporting with actionable messages

### Key Features

- **Direct XLSX processing** (no intermediate CSV conversion)
- **Rich console UI** with tables and formatting
- **Excel metadata writing** and processing reports
- **Jira Cloud compatibility** with ×60 estimate quirk handling
- **Advanced credential management** with keyring integration
- **Excel table-based configuration** for assignees, sprints, components
- **Hierarchical issue type support** with parent-child relationships
- **OAuth 2.0 authentication** (scaffolded, with Basic Auth fallback)
- **Batch processing** for efficient cloud imports

## 🐛 Debugging and Troubleshooting

### Debug Mode

Enable detailed logging and debugging information:

- Use `--debug` or `-d` command line flag
- Provides detailed logging and extra output
- Shows internal processing steps and validation details

### Common Development Issues

1. **Import errors**: Ensure all dependencies are installed with `pip install -r requirements.lock`
2. **File not found**: Check file paths and permissions
3. **Configuration issues**: Verify JSON syntax in config files
4. **Authentication errors**: Use `--credentials show` to check stored credentials
5. **Cloud import failures**: Verify Jira permissions and project access
6. **Path validation errors**: Ensure file paths don't contain control characters
7. **Sensitive data in logs**: Sensitive information is automatically redacted for security

### Testing Configuration

Before running imports, test your setup:

```bash
# Test configuration without processing data
python -m jira_importer --show-config

# Test data processing without writing output files
python -m jira_importer path/to/test.xlsx --dry-run

# Test with debug information
python -m jira_importer path/to/test.xlsx --debug
```

## 📝 Line Endings (CRLF vs LF)

We use **LF (Line Feed)** line endings for all text files. This keeps things consistent across Windows, macOS, and Linux.

### Why This Matters

- **Cross-platform compatibility** between different OSes
- **Git consistency** - no more line ending conflicts
- **Build reliability** - avoids issues during executable creation

### We Handle It Automatically

- **`.gitattributes`** file sets the rules
- **Pre-commit hooks** fix line endings before commits
- **Mixed-line-ending hook** ensures everything uses LF

### File Type Rules

- **LF endings (Unix style):** Python files, Markdown, JSON, YAML, config files, shell scripts
- **CRLF endings (Windows style):** Batch files (.bat, .cmd), PowerShell scripts (.ps1)
- **Binary files:** Images, executables, libraries, and other binary assets

## 📦 Dependency Management

### Current Dependencies

The project uses dependencies for comprehensive functionality:

**Direct Dependencies:**
- **Data processing**: pandas, openpyxl
- **UI/Console**: rich, rich-argparse, tqdm, colorlog, colorama
- **HTTP/API**: requests
- **Security**: keyring
- **Logging**: structlog, colorlog
- **Configuration**: PyYAML

**Development Dependencies:**
- **Testing**: pytest, pytest-cov
- **Code quality**: black, isort, mypy, ruff, pylint
- **Build tools**: pip-tools, poetry, pyinstaller

### Managing Dependencies

**Using pip-tools (recommended):**
```bash
# Update to latest versions
pip-compile --upgrade requirements.in

# Refresh with current constraints
pip-compile requirements.in

# Install dependencies
pip install -r requirements.lock
```

**Using Poetry:**
```bash
# Install dependencies
poetry install --with dev

# Update dependencies
poetry update
```

### Adding New Dependencies

1. Add to `requirements.in` (for pip-tools) or `pyproject.toml` (for Poetry)
2. Run `pip-compile requirements.in` or `poetry lock`
3. Commit both files

## 🚀 Release Information

### Current Version

- **Version**: 1.0.1 (Build 95)
- **Git Branch**: dev
- **Build Date**: 2025-10-26
- **Git Revision**: 6c5a70a

### Build Configurations

The project supports multiple build configurations:

- **`dev`** - Development build with debug info and temporary files
- **`shipping`** - Production build with code signing and documentation
- **`gh_action`** - GitHub Actions build configuration

### Release Process

1. **Development Build**: `python build.py -c dev`
2. **Production Build**: `python build.py -c shipping`
3. **Poetry Build**: `poetry build --format pyinstaller`

## 🔄 Next Steps

### For Contributors

- **Architecture details** → **[ARCHITECTURE.md](ARCHITECTURE.md)**
- **Contribution guidelines** → **[CONTRIBUTING.md](CONTRIBUTING.md)**
- **Configuration options** → **[CONFIG.md](CONFIG.md)**
- **Cloud integration** → **[CLOUD.md](CLOUD.md)**
- **Feature documentation** → **[FEATURES.md](FEATURES.md)**

### For Users

- **Quick start guide** → **[README.md](../README.md)**
- **Configuration help** → **[CONFIG.md](CONFIG.md)**
- **Feature overview** → **[FEATURES.md](FEATURES.md)**

## 📞 Getting Help

### Development Support

- Check debug logs for detailed error information
- Review the main README.md for user documentation
- Create issues for bugs or feature requests
- Reach out to the development team with questions

### Community

- **GitHub Repository**: https://github.com/DeerHide/jira-toolkit
- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and community support

---

**Happy coding!** 🎉

*This documentation is maintained by the Jira Importer Toolkit development team.*

:_GeneratedFile_
