# Jira Importer Toolkit

A simple utility for batch-importing tasks from Excel into Jira Cloud. Prepare your spreadsheet in the required format, run the import, and your tasks are ready to use.

## Why we built it

Many teams continue to do their planning in Excel, even when their task execution lives in Jira. This tool provides a direct way to transfer those plans into Jira without manual data entry.

## Quick Start

1. **Download** the `jira_importer.exe` file
2. **Prepare** your Excel file using the provided template
3. **Run** the executable with your Excel file

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
- `-c, --config` - Custom configuration file (default: `config_importer.json`)
- `-ce, --config-excel` - Use the input Excel file as configuration source (config sheet)
- `-cd, --config-default` - Use config from application location
- `-ci, --config-input` - Use config from input file location (recommended)
- `-d, --debug` - Enable debug mode
- `-v, --version` - Show version information

## Input Format

Use the provided `ImportTemplate.xlsx` as a starting point for your data. The tool will:

- Convert your Excel file to CSV format
- Validate and format data for Jira import
- Generate a properly formatted CSV file ready for Jira

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

See [ROW_SKIPPING.md](docs/ROW_SKIPPING.md) for detailed documentation.

## Output

The tool generates a formatted CSV file in the same directory as your input file, ready for import into Jira.

## Configuration

There are two simple ways to configure the importer. Pick the one that fits you best.

### Option A: Use your Excel file (easiest)

- Put your settings in the `Config` sheet of your Excel file
- Use our template as a starting point: `resources/templates/ImportTemplate_with_config.xlsx`
- Then just run the importer with your Excel file (no extra config file needed)

Tips:

- You can also keep helpful lookup tables (assignees, sprints, components, etc.) in the same Excel, on the `Config` sheet. The tool will read them automatically if present.
- To force using the Excel file as config, add `-ce` when running.

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

### Choosing the config source (flags)

- `-ce, --config-excel`: Use the Excel file itself (its `Config` sheet)
- `-ci, --config-input`: Use `config_importer.json` next to your Excel file
- `-cd, --config-default`: Use the config that ships with the app
- `-c, --config <file>`: Use a specific JSON file

If you’re not sure: just put settings in the Excel `Config` sheet or drop a `config_importer.json` next to your Excel file and use `-ci`.

### Logging (optional)

- File logging can be enabled/disabled with `write_to_file` (on by default)
- Logs are saved next to the app in `jira_importer_logs/`
- For extra details, run with `-d` (debug mode)

## Future Features

The following features are planned for future releases:

- **Cross-Platform Support** - Mac and Linux builds
- **Jira Cloud API Integration** - Direct import to Jira Cloud without manual CSV upload
- **Batch Processing** - Support for multiple Excel files in a single run
- **Import Templates** - Pre-configured templates for common Jira project types

## Troubleshooting

- **File not found**: Ensure your Excel file exists and the path is correct
- **Permission errors**: Run as administrator if needed
- **Debug mode**: Use `-d` flag for detailed logging

## Support

For issues or questions, check the debug logs or contact support.

## Disclaimer

This tool is provided as-is and may not work out of the box for all environments or use cases. Some configuration and adjustments may be required based on your specific Jira setup and data format.

**Feedback and suggestions are welcome!** If you encounter issues or need assistance, please reach out. We're happy to help troubleshoot and improve the tool based on user needs.

## Authors

**Jira Importer Toolkit** is developed by:

- @tom4897
- @nakool

This project is licensed under the MIT License, don't hesitate to contribute or fork!
