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
- `-cd, --config-default` - Use config from application location
- `-ci, --config-input` - Use config from input file location (recommended)
- `-d, --debug` - Enable debug mode
- `-v, --version` - Show version information

## Input Format

Use the provided `ImportTemplate.xlsx` as a starting point for your data. The tool will:
- Convert your Excel file to CSV format
- Validate and format data for Jira import
- Generate a properly formatted CSV file ready for Jira

## Output

The tool generates a formatted CSV file in the same directory as your input file, ready for import into Jira.

## Configuration

**Quick setup:**
1. Copy `jira-importer-config.json` to your project
2. Update your Jira instance details
3. Customize validation rules as needed

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