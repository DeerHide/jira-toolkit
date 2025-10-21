# Developer Starter Guide

Hey there! Welcome to the Jira Importer Toolkit Project. This guide will get you up and running with the project.

## 📚 What's Where

We've split the docs into focused files so you can find what you need:

- **[DEV.md](DEV.md)** - This file: Quick start and overview
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - All the architecture diagrams and component details
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute, code style, and dev workflow
- **[CONFIG.md](CONFIG.md)** - Configuration file docs
- **[CLOUD.md](CLOUD.md)** - Jira Cloud integration technical details
- **[FEATURES.md](FEATURES.md)** - Comprehensive feature guide

## 🚀 Let's Get Started

### What You Need

- **Python 3.12+** (updated from 3.10+)
- **Git** for version control
- **pip** for package management
- **Cross-platform** (Windows, macOS, Linux)

### Setup Steps

1. **Grab the code**

   ```bash
   git clone git@github.com:DeerHide/jira-toolkit.git
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

3. **Install stuff**

   ```bash
   pip install -r requirements.lock
   python -m pip install -e .[dev]
   ```

   **Note**: The project now uses Poetry for dependency management. You can also use:

   ```bash
   poetry install --with dev
   ```

4. **Check it works**

   ```bash
   python -m jira_importer -h
   ```

## 📁 Project Layout

### Repository Structure

```text
jira-toolkit/                    # Repository root
├── src/                         # Source code
├── build/                       # Build assets and working dirs
├── dist/                        # Build output
├── resources/                   # Runtime/user resources
├── docs/                        # Documentation
├── scripts/                     # Helper scripts
├── build.py                     # Build script entrypoint
├── requirements.in              # Python dependencies
├── requirements.lock            # Python dependencies with used versions
├── README.md                    # User documentation
└── .venv/                       # Virtual environment
```

### Application Structure

```text
src/jira_importer/               # Main application package
├── __main__.py                  # Entry point
├── app.py                       # Application logic
├── config/                      # Configuration management
│   ├── config_factory.py       # Configuration factory
│   ├── config_view.py           # Typed config access
│   ├── config_models.py         # Configuration data models
│   ├── excel_config.py         # Excel-based configuration
│   ├── json_config.py          # JSON configuration
│   └── models/                  # Configuration models
│       └── issuetypes.py        # Issue type hierarchy models
├── excel/                       # Excel processing
│   ├── excel_io.py             # Excel workbook management
│   └── excel_table_reader.py   # Excel table configuration reader
├── import_pipeline/             # Core import processing
│   ├── processor.py             # Main pipeline orchestrator
│   ├── models.py                # Data models and interfaces
│   ├── validator.py             # Validation engine
│   ├── rules/                   # Validation rules
│   ├── fixes/                   # Auto-fix system
│   ├── sources/                 # Input readers (CSV, XLSX)
│   ├── sinks/                   # Output writers
│   ├── reporting.py             # Problem reporting
│   └── cloud/                   # Cloud integration
│       ├── auth.py              # Authentication providers
│       ├── client.py            # HTTP client wrapper
│       ├── credential_manager.py # Credential management
│       ├── secrets.py           # Secrets resolution
│       ├── mappers.py           # Data mapping to Jira format
│       ├── metadata.py          # Jira metadata caching
│       └── bulk.py              # Batch processing utilities
├── fileops.py                   # File operations
├── artifacts.py                 # Artifact management
├── console.py                   # Rich console UI
├── log.py                       # Logging utilities
└── utils.py                     # Utility functions
```

## 🏗️ Architecture Overview

The Jira Importer Toolkit uses a modular import pipeline:

- **ImportProcessor** - Main orchestrator that handles the entire pipeline flow
- **Immutable Processing** - Rules and fixes return patches instead of mutating data in-place
- **Extensible Validation** - Built-in rules + framework for Excel-defined rules
- **Auto-fix System** - Safe, configurable fixes for common validation issues
- **Rich Reporting** - Console output with problem aggregation and tables

Want the nitty-gritty details? Check out **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## 🛠️ Development Workflow

### Running the App

1. **Basic usage**

   ```bash
   python -m jira_importer path/to/your/file.xlsx
   ```

2. **With debug mode**

   ```bash
   python -m jira_importer path/to/your/file.xlsx -d
   ```

3. **With auto-fix enabled**

   ```bash
   python -m jira_importer path/to/your/file.xlsx --auto-fix
   ```

4. **With cloud import**

   ```bash
   python -m jira_importer path/to/your/file.xlsx --cloud
   ```

5. **With credential management**

   ```bash
   python -m jira_importer --credentials run
   python -m jira_importer --credentials show
   python -m jira_importer --credentials clear
   ```

6. **With Excel table configuration**

   ```bash
   python -m jira_importer path/to/your/file.xlsx -ce
   ```

7. **With dry-run mode (new)**

   ```bash
   python -m jira_importer --dry-run
   ```

8. **Show configuration without input file (new)**

   ```bash
   python -m jira_importer --show-config
   ```

### Building

1. **Development build**

   ```bash
   python build.py -c dev
   ```

2. **Production build**

   ```bash
   python build.py -c shipping
   ```

## 🔧 Key Components

### Import Pipeline (`import_pipeline/`)

The main processing logic - handles validation, fixes, and data transformation:

- **`processor.py`** - Main orchestrator that handles the entire flow
- **`models.py`** - Data structures and interfaces for the pipeline
- **`validator.py`** - Runs validation rules and auto-fixes
- **`rules/`** - Validation rules (built-in + extensible for Excel-defined rules)
- **`fixes/`** - Auto-fix system for common issues
- **`sources/`** - Input readers for CSV and XLSX files
- **`sinks/`** - Output writers (CSV, future cloud integration)
- **`reporting.py`** - Rich problem reporting with emojis and tables

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

## 🐛 Debugging

### Debug Mode

Turn on debug mode with:

- `-d` or `--debug` command line flag
- Gives you detailed logging and extra output

### Common Issues

1. **Import errors**: Make sure all dependencies are installed
2. **File not found**: Check file paths and permissions
3. **Configuration issues**: Verify JSON syntax in config files
4. **Authentication errors**: The importer provides clear error messages for auth issues (see CONFIG.md troubleshooting section)
5. **Configuration loading**: Make sure you're using the correct config flags (`-c`, `-ce`, `-ci`, `-cd`)
6. **Line ending issues**: If builds fail or you get cross-platform problems, check that all text files use LF line endings
7. **Path validation errors**: The toolkit validates file paths for security - ensure paths don't contain control characters or exceed length limits
8. **Sensitive data in logs**: Sensitive information is automatically redacted from logs for security

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

## 🔄 What's Next?

Need more details? Check out:

- **Architecture and components** → **[ARCHITECTURE.md](ARCHITECTURE.md)**
- **Contributing and development** → **[CONTRIBUTING.md](CONTRIBUTING.md)**
- **Configuration options** → **[CONFIG.md](CONFIG.md)**
- **Jira Cloud integration** → **[CLOUD.md](CLOUD.md)**
- **Comprehensive feature guide** → **[FEATURES.md](FEATURES.md)**

## 📞 Need Help?

- Check the debug logs for detailed error info
- Look at the main README.md for user docs
- Create issues for bugs or feature requests
- Reach out to the dev team with questions

---

**Happy coding!** 🎉

:_GeneratedFile_
