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
  - `CfgCustomFields`: Custom field configuration (name, id, type)
  - `CfgTeams`: Team mapping (name → ID)

### Command Line Interface

#### Available Flags

- **`--credentials [ACTION]`**: Manage Jira API credentials
- **`--auto-fix`**: Enable automatic fixing of validation issues
- **`--fix-cloud-estimates`**: Apply Jira Cloud ×60 estimate quirk
- **`--enable-excel-rules`**: Load validation rules from Excel tables
- **`--data-sheet NAME`**: Excel data sheet tab name (default: **Dataset**; must match the workbook exactly)
- **`--no-report`**: Suppress validation reports (useful for CI/CD)
- **`--dry-run`**: Process data without writing output (new)
- **`--show-config`**: Show configuration without requiring input file (new)

#### Configuration Options

- **`-ce, --config-excel`**: Use Excel file as configuration source
- **`-ci, --config-input`**: Use config file next to input file
- **`-cd, --config-default`**: Use default configuration
- **`-c, --config FILE`**: Use specific configuration file

### Custom Fields Support

#### Supported Field Types

- **Text fields**: Any string value (no validation)
- **Number fields**: Must be parseable as integer or float
- **Date fields**: Must match supported date formats (YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY)
- **Select fields**: Any string value (validation against allowed values coming soon)
- **Any fields**: Any value type (no validation or transformation, passed through as-is)

#### Configuration Methods

- **JSON configuration**: Define custom fields in `jira.custom_fields` array
- **Excel table configuration**: Use `CfgCustomFields` table in Config sheet
- **Automatic validation**: Values are validated based on field type
- **Error reporting**: Clear error messages with field name, expected format, and row number

#### Features

- **Type-based validation**: Automatic validation based on configured field type
- **Flexible configuration**: Support for both JSON and Excel-based configuration
- **Cloud import support**: Custom fields are included in direct Jira Cloud imports
- **CSV export support**: Custom fields are included in CSV exports for manual import

### Auto-Fix System

#### Built-in Fixers

The toolkit includes 6 built-in auto-fixers that automatically resolve common validation issues:

1. **PriorityNormalizeFixer**
   - **Problem codes**: `priority.invalid`, `priority.missing`
   - **Functionality**: Normalizes priority values to canonical labels (case-insensitive matching, numeric mapping)
   - **Configuration**: `jira.priorities` list, `validation.priority.number_map` boolean

2. **EstimateNormalizeFixer**
   - **Problem codes**: `estimate.invalid_format`
   - **Functionality**: Parses human-friendly estimates (e.g., "2h", "1w 2d 3h 30m") and normalizes to seconds or minutes
   - **Configuration**: `validation.estimate.accept_integers_as`, `output.estimate.unit`, `time.h_per_day`, `time.wd_per_week`

3. **ProjectKeyFixer**
   - **Problem codes**: `project_key.missing`, `project_key.mismatch`
   - **Functionality**: Sets or corrects project key from configuration
   - **Configuration**: `jira.project.key`

4. **AssignIssueIdFixer**
   - **Problem codes**: `issueid.missing`, `issueid.invalid`
   - **Functionality**: Assigns unique sequential Issue IDs when missing or invalid
   - **Configuration**: `issueid.prefix`, `issueid.width`

5. **AssigneeResolverFixer**
   - **Problem codes**: `assignee.display_name`, `assignee.empty_with_name`
   - **Functionality**: Resolves assignee display names to Jira account IDs using CfgAssignees table
   - **Configuration**: `CfgAssignees` Excel table with Name → Account ID mapping

6. **TeamResolverFixer**
   - **Problem codes**: `team.display_name`, `team.empty_with_name`
   - **Functionality**: Resolves team display names to Jira account IDs using CfgTeams table
   - **Configuration**: `CfgTeams` Excel table with Name → Team ID mapping

#### Usage

Enable auto-fix with the `--auto-fix` flag:

```bash
jira-importer.exe your-data.xlsx --auto-fix
jira-importer.exe your-data.xlsx --cloud --auto-fix
```

#### Fix Registry

Fixers are registered by problem code in the `FixRegistry`. The system automatically applies fixes when:
- Auto-fix is enabled (`--auto-fix` flag or configuration)
- A problem code has a registered fixer
- The fixer determines the fix is safe to apply

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
