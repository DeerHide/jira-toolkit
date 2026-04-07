# Jira Importer Toolkit

Excel → Jira importer with automatic validation, auto-fixes, and Jira-ready CSV generation.

A powerful utility for batch-importing tasks from Excel into Jira. Transform your Excel planning data into properly structured Jira issues with hierarchical relationships, automatic validation, and direct cloud integration (Jira Cloud only for API integration, CSV export works with any Jira deployment).

## Quick Navigation

- [Download](#download) | [Quick Start](#quick-start) | [Who Is This For?](#who-is-this-for) | [Common Errors](#common-jira-import-errors) | [Configuration](#configuration) | [Support](#support)

## Key Features

The tool converts Excel files into Jira-compatible CSVs, validates fields like issue types and priorities, automatically fixes common Jira import errors, skips invalid or junk rows, supports both CLI and a standalone EXE, allows custom rules through JSON configuration, and produces a fully Jira-ready CSV ready for bulk import.

- Converts Excel (.xlsx) into Jira-compatible CSV files
- Validates issue types, priorities, components, and IDs
- Auto-fixes common Jira import errors
- Skips junk rows and malformed data
- CLI and standalone EXE available
- Direct import to Jira via API (v3)
- Customizable rules via JSON config
- Generates a fully Jira-ready CSV for bulk import

## Download

➡️ **Get the latest release from the [Releases page](https://github.com/DeerHide/jira-toolkit/releases).**

No install required — on Windows, you can drag & drop your Excel file onto the EXE to start processing (the tool will automatically look for configuration files).

**Platform Support:**

- **Windows**: Standalone EXE available (no installation required)
- **macOS**: Native build available (no installation required)
- **Source**: Python 3.12+ required for running from source

## ⚠️ Important Notice

**This tool currently supports Jira Cloud only for direct API integration.**

**CSV Export**: The CSV export functionality works with any Jira deployment type (Cloud, Server, Data Center) since it generates CSV files for manual import.

**Direct Cloud Import**: The `--cloud` flag only works with Jira Cloud instances using REST API v3. It does not work with:

- Jira Server (on-premises)
- Jira Data Center
- Legacy Jira instances

**Need Server/Data Center support?** We're happy to help adapt the tool for your specific Jira setup constraints. Please reach out via [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues) or via our website [deerhide.run](https://deerhide.run) with details about your Jira configuration.

## Why This Tool Exists

Importing tasks from Excel into Jira is often frustrating because the CSV must be perfectly formatted, fields must match Jira's internal rules, and small issues result in unclear error messages. The purpose of this tool is to automate the conversion, validation, cleanup, and output formatting to avoid these problems.

This toolkit automates the entire process: conversion, validation, fixing, and generating a clean Jira-ready CSV or import to Jira Cloud — eliminating the pain of manual formatting and cryptic error messages.

## Who Is This For?

Perfect for **project managers**, **team leads**, **producers**, and anyone who plans in Excel but later needs to import into Jira. If you've ever struggled with Jira's CSV import requirements or spent hours fixing formatting issues, this tool is for you.

## Quick Start

1. **Download** the `jira-importer.exe` file from the [releases page](https://github.com/DeerHide/jira-toolkit/releases)
2. **Prepare** your Excel file using the provided `ImportTemplate.xlsx` template
3. **Run** the import:

   ```bash
   # For CSV export (manual import)
   # On Windows: drag & drop your Excel file onto jira-importer.exe
   # Or use command line:
   jira-importer.exe your-data.xlsx

   # For direct Jira Cloud import
   jira-importer.exe your-data.xlsx --cloud
   ```

**Optional: Test your setup first** (recommended):

   ```bash
   jira-importer.exe --show-config
   jira-importer.exe your-data.xlsx --dry-run
   ```

## CLI Usage

### Easy Mode

On Windows, you can drag and drop your Excel file onto the `jira-importer.exe` file for quick CSV export. The tool will automatically look for a configuration file next to your Excel file (use `-ci` flag if needed).

### Command Line Options

| Option | Description |
|--------|-------------|
| `your-data.xlsx` | Your Excel file to import |
| `-c, --config` | Use a specific configuration file |
| `-ce, --config-excel` | Use settings from your Excel file's Config sheet |
| `-cd, --config-default` | Use the default configuration |
| `-ci, --config-input` | Use config file next to your Excel file (recommended) |
| `--cloud` | Import directly to Jira Cloud (requires configuration) |
| `--auto-fix` | Enable automatic fixing of validation issues |
| `--credentials [ACTION]` | Manage Jira API credentials (run/show/clear) |
| `--data-sheet NAME` | Data sheet tab name (default: **Dataset**; must match the workbook exactly) |
| `--dry-run` | Process data without writing output |
| `--show-config` | Show configuration without requiring input file |
| `-d, --debug` | Show detailed information for troubleshooting |
| `-v, --version` | Show version information |

**Note**: `--cloud` requires `--config-input` or `--config myconfig.json`

## Input Format

**Important**: Use the provided `ImportTemplate.xlsx` as your starting point. Do not change the column headers — the tool expects specific column names to work correctly.

- **Data Sheet**: Place your tasks on the sheet named **Dataset** (CLI default; the name must match the Excel tab exactly). Use `--data-sheet NAME` if your data is on another sheet
- **Template**: Start with `ImportTemplate.xlsx` to ensure proper column structure
- **Empty Rows**: Empty rows are automatically ignored during processing
- **Notes/Comments**: Rows with Issue Types like "comment", "note", or "skip" are automatically filtered out (configurable)

The tool supports:

- **Direct Jira Cloud Import**: Import directly to Jira Cloud (with `--cloud` flag)
- **CSV Export**: Convert your Excel file to CSV format for manual import
- **Smart Validation**: Validate and format data for Jira import
- **Auto-fixing**: Automatically fix common issues (with `--auto-fix` flag)
- **Hierarchical Support**: Handle Initiatives, Epics, Stories, and Sub-tasks with proper relationships
  - Custom types and their levels can be configured in the configuration files (JSON configuration recommended)
- **Custom Fields Support**: Import and validate custom Jira fields (text, number, date, select, any)
  - Configure custom fields in JSON config or Excel tables
  - Automatic validation based on field type
  - Supports both CSV export and direct cloud import

### Input/Output Example

**Input (Excel):**

```csv
Summary,Priority,Issue Type,Parent,Issue ID,Estimate,Labels
Fix login bug,high,Bug,,,2h,bug critical
Add new feature,Medium,Story,,,,
Implement API endpoint,Low,Sub-Task,Add new feature,,1d,backend
```

**Output (CSV - `your-data_jira_ready.csv`):**

```csv
Summary,Priority,Issue Type,Parent,Issue ID,Estimate,Labels
Fix login bug,High,Bug,,1,7200,bug critical
Add new feature,Medium,Story,,2,,
Implement API endpoint,Low,Sub-Task,Add new feature,3,28800,backend
```

**What the tool fixed:**

- **Issue IDs**: Auto-generated sequential IDs (`1`, `2`, `3`) when missing
- **Priority**: Normalized case (`high` → `High`)
- **Estimates**: Converted to seconds (`2h` → `7200`, `1d` → `28800`)
- **Labels**: Preserved and validated (whitespace trimmed, comma-separated format maintained)
- **Label Columns**: Multiple label columns (`labels0`, `labels1`, `labels89724`, etc.) are automatically merged into a single `labels` column

The tool validates, fixes issues, assigns missing Issue IDs, normalizes formats, and generates a clean CSV file ready for Jira's Bulk Create page.

### Custom Fields

The tool supports importing custom Jira fields from your Excel data. Custom fields are automatically detected and validated based on their configured type.

**Supported Field Types:**

- **Text**: Any string value (no validation)
- **Number**: Must be parseable as integer or float
- **Date**: Must be in format YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY
- **Select**: Any string value (validation against allowed values is planned for future release)
- **Any**: Any value type (no validation or transformation, passed through as-is)

**Configuration:**

You can configure custom fields in two ways:

1. **JSON Configuration** (recommended for programmatic setup):

```json
{
  "jira": {
    "custom_fields": [
      {
        "name": "Custom Text Field",
        "id": "customfield_10125",
        "type": "text"
      },
      {
        "name": "Story Points",
        "id": "customfield_10002",
        "type": "number"
      },
      {
        "name": "Due Date",
        "id": "customfield_10130",
        "type": "date"
      },
      {
        "name": "Priority Level",
        "id": "customfield_10140",
        "type": "select"
      },
      {
        "name": "Custom Any Field",
        "id": "customfield_10150",
        "type": "any"
      }
    ]
  }
}
```

2. **Excel Table Configuration** (recommended for Excel-based workflows):

   - Create a table named `CfgCustomFields` in your `Config` sheet
   - Columns: `Name`, `Id`, `Type`
   - The `Name` column must match your Excel data column header exactly (case-sentitive)

**Excel Example:**

In your data sheet, add columns matching the custom field names:

```csv
Summary,Priority,Issue Type,Custom Text Field,Story Points,Due Date
Fix bug,High,Bug,Important,5,2024-12-31
Add feature,Medium,Story,Urgent,8,2024-11-15
```

**Finding Custom Field IDs:**

To find your custom field IDs in Jira:

1. Go to your Jira project settings
2. Navigate to "Fields" or "Custom Fields"
3. Click on a custom field to view its details
4. The field ID appears in the URL or field details (format: `customfield_XXXXX`)

**Validation:**

Custom fields are automatically validated:

- **Text fields**: No validation (any value accepted)
- **Number fields**: Must be a valid number (integer or decimal)
- **Date fields**: Must match supported date formats
- **Select fields**: Currently accepts any value (validation against allowed values coming soon)
- **Any fields**: No validation or transformation (value passed through as-is)

Validation errors are reported with clear messages indicating the field name, expected format, and row number.

### Row Skipping

The tool supports skipping rows during processing using multiple criteria:

- **RowType column**: Set `RowType = "SKIP"` for rows you want to exclude
- **Issue Type filtering**: Automatically skip rows with Issue Types like "comment", "note", "skip"
- Skipped rows bypass validation and won't appear in the final output
- Configure this feature in your config file with `"skip_rowtype": true` and `"skip_issuetypes": ["comment", "note", "skip"]`

Example:

```csv
Summary,Priority,Issue Type,RowType
Fix login bug,High,Bug,PROCESS
Skip this row,Low,Story,SKIP
Comment row,Low,comment,PROCESS
Update docs,Medium,Task,PROCESS
```

**Configuration:**

```json
{
  "app": {
    "validation": {
      "skip_rowtype": true,
      "skip_issuetypes": ["comment", "note", "skip"]
    }
  }
}
```

## Output Formats

The tool can generate output in multiple formats:

- **Direct Jira Import**: Issues are created directly in Jira Cloud (with `--cloud` flag)
- **CSV Export**: A cleaned and validated CSV file named with a `_jira_ready.csv` suffix, saved next to the original file, and fully compatible with Jira's Bulk Create page
- **Excel Reports**: Processing reports with metadata written back to Excel files

**CSV Output Details:**

- File naming: `your-file_jira_ready.csv` (saved in the same directory as your input file)
- Format: UTF-8 encoded, ready for Jira's CSV import
- Compatibility: Works with Jira Cloud, Server, and Data Center (via manual CSV upload)

## Configuration

Choose the configuration method that works best for your workflow:

### Option A: Excel Configuration (Recommended)

- Put your settings in the `Config` sheet of your Excel file
- Use our template as a starting point: `resources/templates/ImportTemplate_with_config.xlsx`
- Run: `jira-importer.exe your-data.xlsx -ce`

**Benefits:**

- Everything in one file
- Helpful lookup tables (assignees, sprints, components) in the same Excel
- **Excel Table Configuration**: Use structured tables like `CfgAssignees`, `CfgSprints`, `CfgComponents`

### Option B: JSON Configuration

- Copy `resources/templates/config_importer.json` next to your Excel file
- Fill in your Jira details (site address, API token, project key/id)
- Run: `jira-importer.exe your-data.xlsx -ci`

**Configuration Sources:**

- **Excel file** (`-ce`): Put your settings in the Excel file's Config sheet
- **JSON file** (`-ci`): Place `config_importer.json` next to your Excel file
- **Default** (`-cd`): Use the built-in configuration
- **Custom** (`-c`): Point to a specific configuration file

**Recommendation**: Use the Excel Config sheet (`-ce`) for simplicity, or place a JSON config file next to your Excel file and use `-ci`.

### Logging

- File logging can be enabled/disabled with `write_to_file` (on by default)
- Logs are saved next to the app in `jira_importer_logs/`
- For extra details, run with `-d` (debug mode)

## Common Jira Import Errors

The tool helps address these common Jira import problems:

- **Invalid Issue IDs**: Detects and fixes invalid or duplicate Issue ID formats ✅ Auto-fixable
- **Invalid Priorities**: Validates against allowed priority values and normalizes case ✅ Auto-fixable
- **Missing Parent Links**: Ensures Sub-tasks have required parent relationships
- **Invalid Parent Links**: Validates parent-child hierarchy (e.g., Sub-tasks can't parent Epics)
- **Unrecognized Components**: Validates components against your Jira project's component list
- **Incorrect Column Counts**: Handles Excel formatting issues and ensures proper CSV structure
- **Formatting Issues**: Fixes common Excel-to-CSV conversion problems (quotes, commas, encoding)
- **Sprint Problems**: Validates sprint values and formats them correctly for Jira
- **Fix Version Issues**: Ensures fix versions match your project's available versions
- **Estimate Format Errors**: Normalizes time estimates to Jira's expected format (seconds) ✅ Auto-fixable
- **Project Key Mismatches**: Ensures Issue IDs match your configured project key ✅ Auto-fixable
- **Assignee Resolution**: Resolves assignee display names to Jira account IDs ✅ Auto-fixable
- **Team Resolution**: Resolves team display names to Jira account IDs ✅ Auto-fixable

All of these are automatically detected during validation. Issues marked with ✅ can be auto-fixed with the `--auto-fix` flag.

## Advanced Features

### Enhanced Security & Error Handling ✅

The toolkit includes comprehensive security improvements:

- **Path validation** - Automatic validation of file paths to prevent security issues
- **Sensitive data protection** - Automatic redaction of passwords, tokens, and secrets from logs
- **Improved error handling** - Better error messages with specific guidance for troubleshooting
- **Safer file operations** - Enhanced file handling with proper error management

### Better Error Messages ✅

The importer provides clear, actionable error messages:

- **Clear authentication errors** - Know immediately if your token expired or if there's a connection problem
- **Helpful guidance** - Get specific instructions like "Refresh your token at [URL]" instead of cryptic error codes
- **Configuration help** - Better messages when config files are missing or incorrect

### Debug Features ✅

- **Dry-run mode** - Test your configuration and data processing without writing output files
- **Configuration display** - Show your current configuration without requiring an input file
- **Enhanced Excel configuration** - Improved type conversion and fallback logic for better reliability

### Direct Jira Import ✅

- **Import directly to Jira Cloud** - No more manual CSV uploads
- **Hierarchical issue types** - Support for Initiatives, Epics, Stories, and Sub-tasks with proper parent-child relationships
- **Batch processing** - Efficient handling of large imports
- **Credential management** - Secure credential storage with keyring integration
- **Excel table configuration** - Advanced configuration using structured Excel tables

## Cloud Import Workflow

### Quick Start with Cloud Import

1. **Set up credentials**:

   ```bash
   jira-importer.exe --credentials run
   ```

2. **Import directly to Jira**:

   ```bash
   jira-importer.exe your-data.xlsx --cloud
   ```

3. **With auto-fix enabled**:

   ```bash
   jira-importer.exe your-data.xlsx --cloud --auto-fix
   ```

### Credential Management

- **Interactive setup**: `--credentials run` - Set up authentication interactively
- **View credentials**: `--credentials show` - Display current credentials
- **Clear credentials**: `--credentials clear` - Remove stored credentials
- **Environment variables**: Use `JIRA_EMAIL` and `JIRA_API_TOKEN` for automation

### Hierarchical Issue Types

The tool supports proper parent-child relationships:

- **Level 1 (Initiative)**: Can parent all other levels
- **Level 2 (Epic)**: Can parent levels 3 and 4
- **Level 3 (Story/Task/Bug)**: Can parent level 4
- **Level 4 (Sub-Task)**: Must have a parent

### Testing Your Setup

Before importing your data, test your configuration:

```bash
# Test your configuration without processing data
jira-importer.exe -c your-config.json --show-config
jira-importer.exe your-data.xlsx -ce --show-config

# Test data processing without writing output files
jira-importer.exe your-data.xlsx --dry-run

# Test with debug information
jira-importer.exe your-data.xlsx --debug
```

## Troubleshooting

### Common Issues

- **File not found**: Make sure your Excel file exists and the path is correct
- **Permission errors**: Run as administrator if needed
- **Authentication problems**: The importer will tell you exactly what's wrong (see [CONFIG.md](docs/CONFIG.md) for details)
- **Configuration issues**: Check that you're using the right config flags (`-c`, `-ce`, `-ci`, `-cd`)
- **Credential issues**: Use `--credentials show` to check your stored credentials
- **Cloud import failures**: Check your Jira permissions and project access
- **Path validation errors**: Ensure file paths don't contain control characters or exceed length limits
- **Sensitive data in logs**: Sensitive information is automatically redacted for security
- **Need more details**: Use `-d` flag for detailed logging
- **Test your setup**: Use `--show-config` and `--dry-run` to test before importing

## Roadmap

### Planned Features

- **Linux support** - Native builds for Linux operating systems
- **Multiple file imports** - Process several Excel files at once
- **Project templates** - Ready-made templates for common project types
- **Jira Server/Data Center support** - Support for on-premises Jira instances
- **Advanced reporting** - More detailed import reports and analytics

## Support

### Getting Help

- **Documentation**: Check the [docs](docs/) folder for detailed guides
- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues)
- **Discussions**: Ask questions on [GitHub Discussions](https://github.com/DeerHide/jira-toolkit/discussions)
- **Debug logs**: Use `--debug` flag for detailed error information

### Community

- **GitHub Repository**: <https://github.com/DeerHide/jira-toolkit>
- **Contributing**: See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines on how to contribute
- **Developer Documentation**: See [DEV.md](docs/DEV.md) for development setup and workflow
- **License**: MIT License - feel free to contribute or fork!
