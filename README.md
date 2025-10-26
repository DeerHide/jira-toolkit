# Jira Importer Toolkit

A powerful utility for batch-importing tasks from Excel into Jira. Transform your Excel planning data into properly structured Jira issues with hierarchical relationships, automatic validation, and direct cloud integration (Jira Cloud only for API integration, CSV export works with any Jira deployment).

## ⚠️ Important Notice

**This tool currently supports Jira Cloud only for direct API integration.**

**CSV Export**: The CSV export functionality works with any Jira deployment type (Cloud, Server, Data Center) since it generates CSV files for manual import.

**Direct Cloud Import**: The `--cloud` flag only works with Jira Cloud instances using REST API v3. It does not work with:

- Jira Server (on-premises)
- Jira Data Center
- Legacy Jira instances

**Need Server/Data Center support?** We're happy to help adapt the tool for your specific Jira setup constraints. Please reach out via [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues) or via our website [deerhide.run](https://deerhide.run) with details about your Jira configuration.

## Why We Built It

Many teams continue to do their planning in Excel, even when their task execution lives in Jira. This tool provides a direct way to transfer those plans into Jira without manual data entry, supporting:

- **Hierarchical issue structures** (Initiatives → Epics → Stories → Sub-tasks)
- **Automatic validation** and error fixing
- **Direct Jira Cloud integration** with batch processing
- **Excel-based configuration** for easy setup
- **Rich console interface** with detailed reporting

## Quick Start

1. **Download** the `jira-importer.exe` file from the [releases page](https://github.com/DeerHide/jira-toolkit/releases)
2. **Prepare** your Excel file using the provided `ImportTemplate.xlsx`
3. **Test your setup** (recommended):

   ```bash
   jira-importer.exe --show-config
   jira-importer.exe your-data.xlsx --dry-run
   ```

4. **Run** the import:

   ```bash
   # For CSV export (manual import)
   jira-importer.exe your-data.xlsx

   # For direct Jira Cloud import
   jira-importer.exe your-data.xlsx --cloud
   ```

## Usage

### Easy Mode

Drag and drop your Excel file on the `jira-importer.exe` file for quick CSV export.

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
| `--data-sheet NAME` | Specify custom data sheet name |
| `--dry-run` | Process data without writing output |
| `--show-config` | Show configuration without requiring input file |
| `-d, --debug` | Show detailed information for troubleshooting |
| `-v, --version` | Show version information |

**Note**: `--cloud` requires `--config-input` or `--config myconfig.json`

## Input Format

Use the provided `ImportTemplate.xlsx` as a starting point for your data. The tool supports:

- **Direct Jira Cloud Import**: Import directly to Jira Cloud (with `--cloud` flag)
- **CSV Export**: Convert your Excel file to CSV format for manual import
- **Smart Validation**: Validate and format data for Jira import
- **Auto-fixing**: Automatically fix common issues (with `--auto-fix` flag)
- **Hierarchical Support**: Handle Initiatives, Epics, Stories, and Sub-tasks with proper relationships
  - Custom types and their levels can be configured in the configuration files (JSON recommended)

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
- **CSV Export**: A formatted CSV file ready for manual Jira import
- **Excel Reports**: Processing reports with metadata written back to Excel files

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

## Key Features

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

## Roadmap

### Planned Features

- **Mac and Linux support** - Native builds for other operating systems
- **Multiple file imports** - Process several Excel files at once
- **Project templates** - Ready-made templates for common project types
- **Jira Server/Data Center support** - Support for on-premises Jira instances
- **Advanced reporting** - More detailed import reports and analytics

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

## Support

### Getting Help

- **Documentation**: Check the [docs](docs/) folder for detailed guides
- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues)
- **Discussions**: Ask questions on [GitHub Discussions](https://github.com/DeerHide/jira-toolkit/discussions)
- **Debug logs**: Use `--debug` flag for detailed error information

### Community

- **GitHub Repository**: https://github.com/DeerHide/jira-toolkit
- **License**: MIT License - feel free to contribute or fork!
