# Jira Importer Toolkit

A simple utility for batch-importing tasks from Excel into Jira Cloud. Prepare your spreadsheet in the required format, run the import, and your tasks are ready to use.

## Why we built it

Many teams continue to do their planning in Excel, even when their task execution lives in Jira. This tool provides a direct way to transfer those plans into Jira without manual data entry.

## Quick Start

1. **Download** the `jira_importer.exe` file
2. **Prepare** your Excel file using the provided template
3. **Test your setup** (optional but recommended):

   ```bash
   jira_importer.exe --show-config
   jira_importer.exe your-data.xlsx --dry-run
   ```

4. **Run** the executable with your Excel file

## Usage

### Easy Mode

Drag and drop your excel file on the exe

### Basic Usage

```bash
jira_importer.exe your-data.xlsx
```

### With Custom Configuration

```bash
jira_importer.exe your-data.xlsx -c config.json
```

### Command Line Options

- `your-data.xlsx` - Your Excel file to import
- `-c, --config` - Use a specific configuration file
- `-ce, --config-excel` - Use settings from your Excel file's Config sheet
- `-cd, --config-default` - Use the default configuration
- `-ci, --config-input` - Use config file next to your Excel file (recommended)
- `--cloud` - Import directly to Jira Cloud (requires configuration)
- `--auto-fix` - Enable automatic fixing of validation issues
- `--credentials [ACTION]` - Manage Jira API credentials (run/show/clear)
- `--data-sheet NAME` - Specify custom data sheet name
- `--dry-run` - Process data without writing output (new)
- `--show-config` - Show configuration without requiring input file (new)
- `-d, --debug` - Show detailed information for troubleshooting
- `-v, --version` - Show version information

Note: `--cloud` requires `--config-input` or `--config myconfig.json`

## Input Format

Use the provided `ImportTemplate.xlsx` as a starting point for your data. The tool will:

- **Direct Jira Cloud Import**: Import directly to Jira Cloud (with `--cloud` flag)
- **CSV Export**: Convert your Excel file to CSV format for manual import
- **Smart Validation**: Validate and format data for Jira import
- **Auto-fixing**: Automatically fix common issues (with `--auto-fix` flag)
- **Hierarchical Support**: Handle Initiatives, Epics, Stories, and Sub-tasks with proper relationships

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

## Output

The tool can generate output in multiple formats:

- **Direct Jira Import**: Issues are created directly in Jira Cloud (with `--cloud` flag)
- **CSV Export**: A formatted CSV file ready for manual Jira import
- **Excel Reports**: Processing reports with metadata written back to Excel files

## Configuration

There are two simple ways to configure the importer. Pick the one that fits you best.

### Option A: Use your Excel file (easiest)

- Put your settings in the `Config` sheet of your Excel file
- Use our template as a starting point: `resources/templates/ImportTemplate_with_config.xlsx`
- Then just run the importer with your Excel file (no extra config file needed)

Tips:

- You can also keep helpful lookup tables (assignees, sprints, components, etc.) in the same Excel, on the `Config` sheet. The tool will read them automatically if present.
- To force using the Excel file as config, add `-ce` when running.
- **Excel Table Configuration**: Use structured tables like `CfgAssignees`, `CfgSprints`, `CfgComponents` for advanced configuration.

### Option B: Use a JSON file

- Copy `resources/templates/config_importer.json` next to your Excel file
- Fill in your Jira details (site address, API token, project key/id)
- Run:

```bash
jira_importer.exe your-data.xlsx -ci
```

Notes:

- `-ci` tells the tool to look for `config_importer.json` next to your Excel file
- You can also specify a path with `-c path/to/config.json`

### Choosing the config source

- **Excel file** (`-ce`): Put your settings in the Excel file's Config sheet
- **JSON file** (`-ci`): Place `config_importer.json` next to your Excel file
- **Default** (`-cd`): Use the built-in configuration
- **Custom** (`-c`): Point to a specific configuration file

**Recommendation**: Use the Excel Config sheet (`-ce`) for simplicity, or place a JSON config file next to your Excel file and use `-ci`.

### Logging (optional)

- File logging can be enabled/disabled with `write_to_file` (on by default)
- Logs are saved next to the app in `jira_importer_logs/`
- For extra details, run with `-d` (debug mode)

## Recent Improvements

### Enhanced Security & Error Handling ✅

The toolkit now includes comprehensive security improvements:

- **Path validation** - Automatic validation of file paths to prevent security issues
- **Sensitive data protection** - Automatic redaction of passwords, tokens, and secrets from logs
- **Improved error handling** - Better error messages with specific guidance for troubleshooting
- **Safer file operations** - Enhanced file handling with proper error management

### Better Error Messages ✅

The importer now tells you exactly what's wrong and how to fix it:

- **Clear authentication errors** - Know immediately if your token expired or if there's a connection problem
- **Helpful guidance** - Get specific instructions like "Refresh your token at [URL]" instead of cryptic error codes
- **Configuration help** - Better messages when config files are missing or incorrect

### New Debug Features ✅

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
   jira_importer.exe --credentials run
   ```

2. **Import directly to Jira**:

   ```bash
   jira_importer.exe your-data.xlsx --cloud
   ```

3. **With auto-fix enabled**:

   ```bash
   jira_importer.exe your-data.xlsx --cloud --auto-fix
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

Before importing your data, you can test your configuration:

```bash
# Test your configuration without processing data
jira_importer.exe -c your-config.json --show-config
jira_importer.exe your-data.xlsx -ce --show-config

# Test data processing without writing output files
jira_importer.exe your-data.xlsx --dry-run

# Test with debug information
jira_importer.exe your-data.xlsx --debug
```

## Future Features

- **Mac and Linux support** - Native builds for other operating systems
- **Multiple file imports** - Process several Excel files at once
- **Project templates** - Ready-made templates for common project types

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

For issues or questions, check the debug logs or contact support.

## Disclaimer

This tool is provided as-is and may not work out of the box for all environments or use cases. Some configuration and adjustments may be required based on your specific Jira setup and data format.

**Feedback and suggestions are welcome!** If you encounter issues or need assistance, please reach out. We're happy to help troubleshoot and improve the tool based on user needs.

## Authors

**Jira Importer Toolkit** is developed by:

- @tom4897
- @nakool

This project is licensed under the [MIT License](LICENSE), don't hesitate to contribute or fork!
