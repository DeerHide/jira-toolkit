# Features Guide

This document covers the current features and capabilities of the Jira Importer Toolkit.

## 🚀 Core Features

### Cloud Integration

#### Credential Management

- **Interactive credential setup**: Use `--credentials run` to set up authentication
- **Credential viewing**: Use `--credentials show` to view current credentials
- **Credential clearing**: Use `--credentials clear` to remove stored credentials
- **Keyring integration**: Secure credential storage using OS keychain
- **Environment variable support**: Use `JIRA_EMAIL` and `JIRA_API_TOKEN` environment variables

#### Authentication Methods

- **Basic Authentication**: Email + API token (fully implemented and currently the only supported method)
- **OAuth 2.0**: Scaffolded for future implementation (not functional - skeleton code only)
- **Credential resolution order**: Keyring → Environment → Config → Prompt

#### Excel Table Configuration

- **Structured configuration tables**: Use Excel tables for assignees, sprints, components
- **Automatic table detection**: Reads configuration from `Config` sheet
- **Table types supported**:
  - `CfgAssignees`: User mapping (name → ID)
  - `CfgSprints`: Sprint configuration
  - `CfgFixVersions`: Fix version mapping
  - `CfgComponents`: Component mapping
  - `CfgIssueTypes`: Issue type hierarchy
  - `CfgIgnoreList`: Row skipping rules
  - `CfgPriorities`: Priority mapping
  - `CfgAutoFieldValues`: Auto-populated field values

### Command Line Interface

#### Available Flags

- **`--credentials [ACTION]`**: Manage Jira API credentials
- **`--auto-fix`**: Enable automatic fixing of validation issues
- **`--fix-cloud-estimates`**: Apply Jira Cloud ×60 estimate quirk
- **`--enable-excel-rules`**: Load validation rules from Excel tables
- **`--data-sheet NAME`**: Specify custom data sheet name
- **`--no-report`**: Suppress validation reports (useful for CI/CD)
- **`--dry-run`**: Process data without writing output (new)
- **`--show-config`**: Show configuration without requiring input file (new)

#### Configuration Options

- **`-ce, --config-excel`**: Use Excel file as configuration source
- **`-ci, --config-input`**: Use config file next to input file
- **`-cd, --config-default`**: Use default configuration
- **`-c, --config FILE`**: Use specific configuration file

### Hierarchical Issue Types

#### Issue Type Levels

- **Level 1 (Initiative)**: Highest level, can parent all others
- **Level 2 (Epic)**: Can parent levels 3 and 4
- **Level 3 (Story/Task/Bug)**: Can parent level 4
- **Level 4 (Sub-Task)**: Cannot parent, must have parent

#### Configuration Format

```json
{
  "jira": {
    "issuetypes": [
      {"name": "Initiative", "level": 1},
      {"name": "Epic", "level": 2},
      {"name": "Story", "level": 3},
      {"name": "Task", "level": 3},
      {"name": "Bug", "level": 3},
      {"name": "Sub-Task", "level": 4}
    ]
  }
}
```

### Batch Processing

#### Cloud Import Features

- **Batch size**: 50 issues per batch (configurable)
- **Processing order**: Epics → Stories/Tasks → Sub-tasks
- **Parent resolution**: Automatic parent-child relationship handling
- **Error handling**: Comprehensive error reporting per batch

#### Performance Optimizations

- **Metadata caching**: Reduced API calls for project/field metadata
- **Batch optimization**: Efficient handling of large imports
- **Rate limiting**: Built-in handling of API rate limits

## 🔒 Security Features

### Path Validation

- **ASCII Control Character Limits**: Prevents paths with control characters (ASCII 0-31)
- **Maximum Path Length**: Enforces 4096 character limit for relative paths
- **Path Sanitization**: Automatic sanitization of file paths to prevent security issues

### Sensitive Data Protection

- **Automatic Redaction**: Sensitive terms are automatically redacted from logs
- **Redacted Terms**: password, api_token, token, secret, client_secret, access_token
- **Log Safety**: Prevents accidental exposure of credentials in log files

### Error Handling

- **Phased Error Handling**: Custom exceptions for better error management
- **Safe Excel Writing**: Safer Excel metadata writing with proper error handling
- **Improved Error Messages**: Better error logging with specific guidance

## 🔧 Development Features

### Architecture

#### Configuration System

- **`config/config_factory.py`**: Unified configuration loading
- **`config/config_models.py`**: Typed configuration models
- **`config/excel_config.py`**: Excel-based configuration
- **`config/models/issuetypes.py`**: Issue type hierarchy models

#### Excel Processing

- **`excel/excel_io.py`**: Enhanced Excel workbook management
- **`excel/excel_table_reader.py`**: Structured table configuration reader

#### Cloud Integration Components

- **`import_pipeline/cloud/auth.py`**: Authentication providers
- **`import_pipeline/cloud/client.py`**: HTTP client wrapper
- **`import_pipeline/cloud/credential_manager.py`**: Credential management
- **`import_pipeline/cloud/secrets.py`**: Secrets resolution
- **`import_pipeline/cloud/mappers.py`**: Data mapping to Jira format
- **`import_pipeline/cloud/metadata.py`**: Jira metadata caching
- **`import_pipeline/cloud/bulk.py`**: Batch processing utilities

### Testing Features

#### Credential Management Testing

```bash
# Test credential setup
python -m jira_importer --credentials run

# Test credential viewing
python -m jira_importer --credentials show

# Test credential clearing
python -m jira_importer --credentials clear
```

#### Excel Table Configuration Testing

```bash
# Test Excel-based configuration
python -m jira_importer your-data.xlsx -ce

# Test with custom data sheet
python -m jira_importer your-data.xlsx --data-sheet "MyData" -ce
```

#### Cloud Integration Testing Examples

```bash
# Test cloud import
python -m jira_importer your-data.xlsx --cloud

# Test with auto-fix
python -m jira_importer your-data.xlsx --cloud --auto-fix

# Test with cloud estimates fix
python -m jira_importer your-data.xlsx --cloud --fix-cloud-estimates
```

#### New Development Testing Features

```bash
# Test dry-run mode (new)
python -m jira_importer your-data.xlsx --dry-run

# Test configuration display (new)
python -m jira_importer --show-config

# Test with enhanced error handling
python -m jira_importer your-data.xlsx --debug
```

## 📚 Documentation

### Available Documentation

- **DEV.md**: Quick start and overview
- **ARCHITECTURE.md**: Technical architecture details
- **CONTRIBUTING.md**: Development workflow and contribution guidelines
- **CONFIG.md**: Configuration options
- **CLOUD.md**: Cloud integration technical details
- **FEATURES.md**: This file - comprehensive feature guide

## 🚀 Getting Started

### For Users

#### Python Version

- **Python 3.12+** required
- Update virtual environment if needed

#### Configuration

- **New issue type format**: Use hierarchical configuration
- **Excel table configuration**: Move to structured tables
- **Credential management**: Use new credential system

#### Command Line

- **New flags**: Familiarize with available command line options
- **Configuration precedence**: Understand config loading order

### For Developers

#### Dependencies

- **Poetry**: Project uses Poetry for dependency management
- **Enhanced cloud libraries**: New authentication and HTTP client libraries

#### Code Structure

- **Modular configuration**: Configuration split into multiple modules
- **Cloud integration**: New cloud-specific modules
- **Excel processing**: Enhanced Excel handling capabilities

## 🔮 Future Roadmap

### Planned Features

- **OAuth 2.0 completion**: Full OAuth 2.0 implementation
- **Advanced Excel rules**: More sophisticated Excel-based validation
- **Import templates**: Ready-made templates for common project types
- **Multi-file processing**: Process multiple Excel files simultaneously

### Architecture Improvements

- **Plugin system**: Extensible authentication and validation plugins
- **Webhook support**: Real-time import status updates
- **Progress tracking**: Enhanced progress reporting for large imports

---

**Note**: This document reflects the current feature set. Check the changelog for specific version details.

:_GeneratedFile_
