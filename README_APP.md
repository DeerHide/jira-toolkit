# Jira Importer Toolkit — Quick Start

**Excel → Jira-ready CSV, or direct Jira Cloud import** — with validation and optional auto-fixes.

This guide ships with the build. Follow it for your first successful run.

## Important notice

**Direct API import (`--cloud`) supports Jira Cloud only** (REST API v3).

| Path | Works with |
| --- | --- |
| **CSV export** (default) | Jira Cloud, Server, and Data Center (manual upload) |
| **Direct Cloud import** (`--cloud`) | Jira Cloud only — not Server, Data Center, or legacy Jira |

Need Server/Data Center API support? Open a [GitHub Issue](https://github.com/DeerHide/jira-toolkit/issues) with your setup details.

## What’s in this folder

- **`jira-importer.exe`** (Windows) or **`jira-importer`** (macOS) — the app
- **`ImportTemplate.xlsx`** — expected column layout (also under `resources/templates/` in the repo)
- **`config_importer.json`** (when bundled) — sample JSON config
- **`README_APP.md`** — this guide

Optional on [GitHub Releases](https://github.com/DeerHide/jira-toolkit/releases): **`ImportTemplate_with_config.xlsx`** (sample `Config` sheet and tables).

## Before you start

1. Open **`ImportTemplate.xlsx`** (or match its column headers in your own workbook).
2. Put tasks on the sheet named **Dataset** (name must match the tab exactly). Use `--data-sheet NAME` if your data is on another sheet.
3. Do **not** rename column headers unless you know the schema.
4. Save the file.

**Recommended before any real import:**

```bash
# Windows
jira-importer.exe --show-config
jira-importer.exe your-data.xlsx --dry-run

# macOS
./jira-importer --show-config
./jira-importer your-data.xlsx --dry-run
```

## Path A — CSV for manual Jira import

Best when you use any Jira deployment, or you want to review the file before upload.

1. Run the app on your workbook:

   ```bash
   # Windows — drag & drop your Excel file onto jira-importer.exe, or:
   jira-importer.exe your-data.xlsx

   # macOS
   ./jira-importer your-data.xlsx
   ```

2. Find **`your-data_jira_ready.csv`** next to your Excel file.
3. In Jira, open **Bulk create issues** (or your site’s CSV import flow) and upload that CSV.

**You’re done when:** the CSV opens cleanly and Jira accepts the upload (or shows field mapping you can complete).

## Path B — Direct Jira Cloud import

Best when you use **Jira Cloud** and want issues created without a manual CSV upload.

**Prerequisites:** Jira Cloud site URL and project in config, permission to create issues, and credentials.

1. Set up credentials (first time):

   ```bash
   # Windows
   jira-importer.exe --credentials run

   # macOS
   ./jira-importer --credentials run
   ```

2. Import:

   ```bash
   # Windows
   jira-importer.exe your-data.xlsx --cloud

   # macOS
   ./jira-importer your-data.xlsx --cloud
   ```

3. Optional — enable safe auto-fixes for common issues:

   ```bash
   jira-importer.exe your-data.xlsx --cloud --auto-fix
   ./jira-importer your-data.xlsx --cloud --auto-fix
   ```

**You’re done when:** the tool reports created issues (or a cloud submit summary) and you can see them in the project.

For Cloud behavior details, see [`docs/CLOUD.md`](docs/CLOUD.md) in the repository.

## Verify success

| Mode | Success looks like |
| --- | --- |
| **CSV** | `your-file_jira_ready.csv` next to the input file |
| **Cloud** | Created-issue report / submit summary in the console |
| **Unsure** | Run `--show-config`, then `--dry-run`, then retry |

## What the tool does for you

- Hierarchical issues (Initiatives → Epics → Stories → Sub-tasks)
- Validation and clear problem reporting
- Optional auto-fix for common issues (`--auto-fix`)
- Missing Issue IDs when needed
- Format normalization (priorities, estimates, and related fields)
- Mapping helpers for assignees, sprints, components (via config)
- Custom fields when configured
- CSV export **or** direct Jira Cloud import

### Mini example

**Input (Excel / conceptual):**

```csv
Summary,Priority,Issue Type,Parent,Issue ID,Estimate,Labels
Fix login bug,high,Bug,,,2h,bug critical
Add new feature,Medium,Story,,,,
Implement API endpoint,Low,Sub-Task,Add new feature,,1d,backend
```

**Output (`your-data_jira_ready.csv`):**

```csv
Summary,Priority,Issue Type,Parent,Issue ID,Estimate,Labels
Fix login bug,High,Bug,,1,7200,bug critical
Add new feature,Medium,Story,,2,,
Implement API endpoint,Low,Sub-Task,Add new feature,3,28800,backend
```

**What changed:** Issue IDs filled in, priority case normalized, estimates converted to seconds, labels preserved. Multiple label columns (`labels0`, `labels1`, …) merge into one `labels` column when present.

## Configuration for a first success

### Option A: Excel configuration (recommended)

1. Put settings in a **`Config`** sheet (prefer **`ImportTemplate_with_config.xlsx`** from Releases when available).
2. Run with Excel config:

   ```bash
   jira-importer.exe your-data.xlsx -ce
   ./jira-importer your-data.xlsx -ce
   ```

**Benefits:** one file; lookup tables for assignees, sprints, components; structured `Cfg*` tables on sheets named `config*` / `cfg*` (case-insensitive). Missing **required** tables fail fast before dataset processing.

**Required tables:** `CfgAssignees`, `CfgIssueTypes`, `CfgIgnoreList`, `CfgPriorities`, `CfgAutofieldValues`  
**Optional tables:** `CfgSprints`, `CfgFixVersions`, `CfgComponents`, `CfgTeams`, `CfgCustomFields`

### Option B: JSON configuration

1. Copy `config_importer.json` next to your Excel file (from this bundle or `resources/templates/` in the repo).
2. Fill in site address and project key/id.
3. Prefer `jira-importer --credentials run` (or `JIRA_EMAIL` / `JIRA_API_TOKEN` for automation).
4. Run:

   ```bash
   jira-importer.exe your-data.xlsx -ci
   ./jira-importer your-data.xlsx -ci
   ```

**Benefits:** shareable, version-controllable, friendly to automation.

Full reference: [`docs/CONFIG.md`](docs/CONFIG.md).

### Row skipping (optional)

Skip rows with `RowType = SKIP`, or issue types such as `comment`, `note`, `skip`. In JSON, set **`validation.skip_rowtype`** / **`validation.skip_issuetypes`** at the **root** of the file (see sample config)—not under `app.validation`.

## Common commands

```bash
# CSV export (default)
jira-importer.exe your-data.xlsx
./jira-importer your-data.xlsx

# Jira Cloud import
jira-importer.exe your-data.xlsx --cloud
./jira-importer your-data.xlsx --cloud

# Auto-fix common issues
jira-importer.exe your-data.xlsx --auto-fix
./jira-importer your-data.xlsx --cloud --auto-fix

# Excel or sidecar JSON config
jira-importer.exe your-data.xlsx -ce
jira-importer.exe your-data.xlsx -ci

# Credentials
jira-importer.exe --credentials run
jira-importer.exe --credentials show
jira-importer.exe --credentials test
jira-importer.exe --credentials clear

# Troubleshoot
jira-importer.exe --show-config
jira-importer.exe your-data.xlsx --dry-run
jira-importer.exe your-data.xlsx --debug
```

## Troubleshooting

| Symptom | What to try |
| --- | --- |
| File not found | Check the Excel path and current directory |
| Authentication failed | Run `--credentials run`, then `--credentials test` |
| Permission denied writing output | Save/run from a folder you can write to (avoid protected system folders). Elevate only if your environment requires it |
| Wrong or missing config | Confirm flags: `-c`, `-ce`, `-ci`, `-cd` |
| Cloud import failed | Confirm Cloud site, project access, and create-issue permission |
| Need more detail | Add `--debug`; re-test with `--dry-run` |

### Auto-fix expectations

With `--auto-fix`, the tool can correct many **safe** issues (for example priority case, missing Issue IDs, some estimate formats). It does **not** invent missing business data (for example a required parent that does not exist). Always review `--dry-run` output when unsure.

## Support

1. Run with `--debug` and check logs (often under `jira_importer_logs/` next to the app).
2. Use `--show-config` and `--dry-run`.
3. [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues) · [Discussions](https://github.com/DeerHide/jira-toolkit/discussions) · [Repository](https://github.com/DeerHide/jira-toolkit)

**License:** MIT
