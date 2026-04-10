# Jira Importer Toolkit - Quick Start Guide

**Excel → Jira importer with automatic validation, auto-fixes, and Jira-ready CSV generation.** 🚀

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

Perfect for **project managers**, **team leads**, **producers**, and anyone who plans in Excel but later needs to import into Jira.

## Platform Support

- **Windows**: Standalone EXE available (no installation required)
- **macOS**: Native build available (no installation required)
- **Source**: Python 3.12+ required for running from source

### Templates

- **Excel**: **`ImportTemplate.xlsx`** is in **`resources/templates/`**. Bundles on **[GitHub Releases](https://github.com/DeerHide/jira-toolkit/releases)** include the app and that workbook; **`ImportTemplate_with_config.xlsx`** is offered there when published (not in git).
- **JSON** (`config_importer.json`, `config_importer_full.json`, …): **`resources/templates/`** in the repo.

## Quick Start (3 steps)

### 1. Prepare Your Data

- Use **`ImportTemplate.xlsx`** from **`resources/templates/`** or your **[release download](https://github.com/DeerHide/jira-toolkit/releases)** (or match its column layout in your own file)
- **Important**: Do not change the column headers — the tool expects specific column names
- Place your tasks on the sheet named **Dataset** (default; must match the Excel tab exactly). Use `--data-sheet NAME` if your data is on another sheet
- Fill in your tasks, stories, epics, etc.
- Save your Excel file

### 2. Choose Your Import Method

#### Option A: Direct Jira Cloud Import

```bash
# First time: Set up credentials
jira-importer.exe --credentials run

# Import directly to Jira Cloud
jira-importer.exe your-data.xlsx --cloud

# With auto-fix enabled
jira-importer.exe your-data.xlsx --cloud --auto-fix
```

#### Option B: Generate CSV for Manual Import

```bash
# Generate CSV file for manual Jira import
# On Windows: drag & drop your Excel file onto jira-importer.exe
# Or use command line:
jira-importer.exe your-data.xlsx
```

### 3. That's it! 🎉

Your data is now ready for Jira! The tool handles:

- ✅ **Hierarchical issues** (Initiatives → Epics → Stories → Sub-tasks)
- ✅ **Automatic validation** and error fixing
- ✅ **Auto-generated Issue IDs** when missing
- ✅ **Format normalization** (priorities, estimates, etc.)
- ✅ **Smart mapping** of assignees, sprints, components
- ✅ **Custom Fields** mapping and validation
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

# Verify credentials / connection to Jira
jira-importer.exe --credentials test
```

## Configuration Options

### Option A: Excel Configuration (Recommended)

- Put your settings in the `Config` sheet of your Excel file
- Use **`ImportTemplate_with_config.xlsx`** from **Releases** when available, or add a `Config` sheet to a workbook based on `ImportTemplate.xlsx`
- Run: `jira-importer.exe your-data.xlsx -ce`

**Benefits:**

- Everything in one file
- Helpful lookup tables (assignees, sprints, components) in the same Excel
- Use structured tables like `CfgAssignees`, `CfgSprints`, `CfgComponents`

### Option B: JSON Configuration

- Copy `config_importer.json` next to your Excel file (from **`resources/templates/`** in the repo or from the release bundle)
- Fill in your Jira details (site address, API token, project key/id)
- Run: `jira-importer.exe your-data.xlsx -ci`

**Benefits:**

- Centralized configuration - Manage settings in version-controlled JSON files
- Best for teams - Share consistent configuration across team members
- Automation-friendly - Perfect for CI/CD pipelines and AI orchestration systems

## Input/Output Example

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
- **Labels**: Preserved and validated
- **Label Columns**: Multiple label columns (`labels0`, `labels1`, `labels89724`, etc.) are automatically merged into a single `labels` column

## What's Included

- `jira-importer.exe` (Windows) or `jira-importer` (macOS) — the main executable
- **`ImportTemplate.xlsx`** — **`resources/templates/`**; mirrored on **[Releases](https://github.com/DeerHide/jira-toolkit/releases)**; optional **`ImportTemplate_with_config.xlsx`** sometimes on Releases only
- **`config_importer.json`** — **`resources/templates/`**; often bundled next to the downloadable app
- `README_APP.md` — this guide

## Output Options

- **CSV Export** (default): Generates CSV files named `your-file_jira_ready.csv` saved next to your input file, ready for Jira's Bulk Create page
- **Direct Jira Import** (with `--cloud`): Creates issues directly in Jira Cloud
- **Excel Reports**: Processing reports with metadata written back to Excel files

## Common Jira Import Errors Fixed

The tool automatically detects and fixes:

- **Invalid/Missing Issue IDs**: Auto-generates sequential IDs when missing
- **Invalid Priorities**: Normalizes case and validates against allowed values
- **Missing Parent Links**: Ensures Sub-tasks have required parent relationships
- **Invalid Parent Links**: Validates parent-child hierarchy
- **Formatting Issues**: Fixes Excel-to-CSV conversion problems
- **Estimate Format Errors**: Normalizes time estimates to Jira's expected format
- **Project Key Mismatches**: Ensures Issue IDs match your configured project key

Many of these can be auto-fixed with the `--auto-fix` flag.

## Troubleshooting

### Common Issues

- **"File not found"** → Check your Excel file path
- **"Authentication failed"** → Run `--credentials run` to set up
- **"Permission denied"** → Run as administrator if needed
- **Configuration issues** → Check that you're using the right config flags (`-c`, `-ce`, `-ci`, `-cd`)
- **Need more details** → Use `--debug` flag

### Get Help

- Use `--show-config` to check your setup
- Use `--dry-run` to test without importing
- Use `--debug` for detailed error information
- Visit the [GitHub repository](https://github.com/DeerHide/jira-toolkit) for more help

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
- `CfgTeams` - Team mapping

### Row Skipping

Skip rows by setting `RowType = "SKIP"` or using issue types like "comment", "note", "skip". In JSON config, enable **`validation.skip_rowtype`** / **`validation.skip_issuetypes`** at the **root** of the file (see **`resources/templates/config_importer.json`** in the repo), not under `app.validation`.

## Support

For issues or questions:

1. Check the debug logs (use `--debug`)
2. Test your configuration (use `--show-config`)
3. Try dry-run mode (use `--dry-run`)
4. Visit the [GitHub repository](https://github.com/DeerHide/jira-toolkit) for more help

### Community

- **GitHub Repository**: <https://github.com/DeerHide/jira-toolkit>
- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues)
- **Discussions**: Ask questions on [GitHub Discussions](https://github.com/DeerHide/jira-toolkit/discussions)

---

**Repository**: <https://github.com/DeerHide/jira-toolkit>
**License**: MIT License - feel free to contribute or fork!
