# JIRA Toolkit - Quick Start Guide

**Convert Excel data for JIRA import** 🚀

## What is this?

A simple tool that takes your Excel planning data and prepares it for JIRA import. You can either:

- **Import directly to JIRA Cloud** (with credentials)
- **Generate CSV files** for manual JIRA import

Perfect for teams who plan in Excel but execute in JIRA.

## Quick Start (3 steps)

### 1. Prepare Your Data

- Use the included `ImportTemplate.xlsx` as your starting point
- Fill in your tasks, stories, epics, etc.
- Save your Excel file

### 2. Choose Your Import Method

#### Option A: Direct JIRA Cloud Import

> ⚠️ **Note**: The Cloud implementation is still in development. It's recommended to test in a JIRA sandbox environment before using in production.

```bash
# First time: Set up credentials
jira_importer.exe --credentials run

# Import directly to JIRA
jira_importer.exe your-data.xlsx --cloud
```

#### Option B: Generate CSV for Manual Import

```bash
# Generate CSV file for manual JIRA import
jira_importer.exe your-data.xlsx
```

### 3. That's it! 🎉

Your data is now ready for JIRA! The tool handles:

- ✅ **Hierarchical issues** (Initiatives → Epics → Stories → Sub-tasks)
- ✅ **Automatic validation** and error fixing
- ✅ **Smart mapping** of assignees, sprints, components
- ✅ **CSV generation** for manual import OR **direct JIRA Cloud import**

## Need Help?

### Test Before Importing

```bash
# Check your configuration
jira_importer.exe --show-config

# Test your data without importing
jira_importer.exe your-data.xlsx --dry-run
```

### Common Commands

```bash
# Generate CSV for manual JIRA import (default)
jira_importer.exe your-data.xlsx

# Import directly to JIRA Cloud
jira_importer.exe your-data.xlsx --cloud

# Import with auto-fix for common issues
jira_importer.exe your-data.xlsx --cloud --auto-fix

# Use Excel file as configuration
jira_importer.exe your-data.xlsx -ce

# Debug mode for troubleshooting
jira_importer.exe your-data.xlsx --debug
```

### Credential Management

```bash
# Set up credentials
jira_importer.exe --credentials run

# View current credentials
jira_importer.exe --credentials show

# Clear credentials
jira_importer.exe --credentials clear
```

## Configuration Options

### Option A: Excel Configuration (Recommended)

- Put your settings in the `Config` sheet of your Excel file
- Use the included template: `ImportTemplate.xlsx`
- Run: `jira_importer.exe your-data.xlsx -ce`

### Option B: JSON Configuration

- Copy `config_importer.json` next to your Excel file
- Fill in your JIRA details
- Run: `jira_importer.exe your-data.xlsx -ci`

## What's Included

- `jira_importer.exe` - The main executable
- `ImportTemplate.xlsx` - Excel template with examples
- `config_importer.json` - Configuration template
- `README_EXECUTABLE.md` - This guide

## Output Options

- **CSV Export** (default): Generates CSV files ready for JIRA manual import
- **Direct JIRA Import** (with `--cloud`): Creates issues directly in JIRA Cloud
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

---

**Authors**: Julien (@tom4897), Alain (@Nakool)
**Repository**: https://github.com/deerhide/jira-toolkit
**License**: MIT
