# Jira Importer Toolkit - Quick Start Guide

**Convert Excel data for Jira import** 🚀

## ⚠️ Important Notice

**This tool currently supports Jira Cloud only for direct API integration.**

**CSV Export**: The CSV export functionality works with any Jira deployment type (Cloud, Server, Data Center) since it generates CSV files for manual import.

**Direct Cloud Import**: The `--cloud` flag only works with Jira Cloud instances using REST API v3. It does not work with:
- Jira Server (on-premises)
- Jira Data Center
- Legacy Jira instances

**Need Server/Data Center support?** We're happy to help adapt the tool for your specific Jira setup constraints. Please reach out via [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues) with details about your Jira configuration.

## What is this?

A powerful tool that takes your Excel planning data and prepares it for Jira import. You can either:

- **Import directly to Jira Cloud** (with credentials)
- **Generate CSV files** for manual Jira import (works with any Jira deployment)

Perfect for teams who plan in Excel but execute in Jira.

## Quick Start (3 steps)

### 1. Prepare Your Data

- Use the included `ImportTemplate.xlsx` as your starting point
- Fill in your tasks, stories, epics, etc.
- Save your Excel file

### 2. Choose Your Import Method

#### Option A: Direct Jira Cloud Import

```bash
# First time: Set up credentials
jira-importer.exe --credentials run

# Import directly to Jira Cloud
jira-importer.exe your-data.xlsx --cloud
```

#### Option B: Generate CSV for Manual Import

```bash
# Generate CSV file for manual Jira import
jira-importer.exe your-data.xlsx
```

### 3. That's it! 🎉

Your data is now ready for Jira! The tool handles:

- ✅ **Hierarchical issues** (Initiatives → Epics → Stories → Sub-tasks)
- ✅ **Automatic validation** and error fixing
- ✅ **Smart mapping** of assignees, sprints, components
- ✅ **CSV generation** for manual import OR **direct Jira Cloud import**

## Need Help?

### Test Before Importing

```bash
# Check your configuration
jira-importer.exe --show-config

# Test your data without importing
jira-importer.exe your-data.xlsx --dry-run
```

### Common Commands

```bash
# Generate CSV for manual Jira import (default)
jira-importer.exe your-data.xlsx

# Import directly to Jira Cloud
jira-importer.exe your-data.xlsx --cloud

# Import with auto-fix for common issues
jira-importer.exe your-data.xlsx --cloud --auto-fix

# Use Excel file as configuration
jira-importer.exe your-data.xlsx -ce

# Debug mode for troubleshooting
jira-importer.exe your-data.xlsx --debug
```

### Credential Management

```bash
# Set up credentials
jira-importer.exe --credentials run

# View current credentials
jira-importer.exe --credentials show

# Clear credentials
jira-importer.exe --credentials clear
```

## Configuration Options

### Option A: Excel Configuration (Recommended)

- Put your settings in the `Config` sheet of your Excel file
- Use the included template: `ImportTemplate.xlsx`
- Run: `jira-importer.exe your-data.xlsx -ce`

### Option B: JSON Configuration

- Copy `config_importer.json` next to your Excel file
- Fill in your Jira details
- Run: `jira-importer.exe your-data.xlsx -ci`

## What's Included

- `jira-importer.exe` - The main executable
- `ImportTemplate.xlsx` - Excel template with examples
- `config_importer.json` - Configuration template
- `README_EXECUTABLE.md` - This guide

## Output Options

- **CSV Export** (default): Generates CSV files ready for Jira manual import
- **Direct Jira Import** (with `--cloud`): Creates issues directly in Jira Cloud
- **Excel Reports**: Processing reports with metadata written back to Excel files

## Troubleshooting

### Common Issues

- **"File not found"** → Check your Excel file path
- **"Authentication failed"** → Run `--credentials run` to set up
- **"Permission denied"** → Run as administrator if needed
- **Need more details** → Use `--debug` flag

### Get Help

- Use `--show-config` to check your setup
- Use `--dry-run` to test without importing
- Use `--debug` for detailed error information

## Advanced Features

### Hierarchical Issue Types

Custom types and their levels can be configured in the configuration files (JSON recommended).

- **Level 1**: Initiative (can parent all others)
- **Level 2**: Epic (can parent levels 3-4)
- **Level 3**: Story/Task/Bug (can parent level 4)
- **Level 4**: Sub-Task (must have parent)

### Excel Table Configuration

Use structured tables in your Excel `Config` sheet:

- `CfgAssignees` - User mapping
- `CfgSprints` - Sprint configuration
- `CfgComponents` - Component mapping
- `CfgIssueTypes` - Issue type hierarchy
- `CfgPriorities` - Priority mapping

### Row Skipping

Skip rows by setting `RowType = "SKIP"` or using issue types like "comment", "note", "skip".

## Support

For issues or questions:

1. Check the debug logs (use `--debug`)
2. Test your configuration (use `--show-config`)
3. Try dry-run mode (use `--dry-run`)
4. Visit the [GitHub repository](https://github.com/DeerHide/jira-toolkit) for more help

---

**Authors**: Julien (@tom4897), Alain (@Nakool)
**Repository**: https://github.com/DeerHide/jira-toolkit
**License**: MIT
