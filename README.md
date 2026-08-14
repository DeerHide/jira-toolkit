# Jira Importer Toolkit

**Excel → Jira-ready CSV, or direct Jira Cloud import** — with validation, optional auto-fixes, and a standalone app.

Plan in Excel. Get issues Jira can accept—without hand-fighting CSV rules or cryptic import errors.

## Who should read which doc?

| You want to… | Start here |
| --- | --- |
| **Run the downloaded app** (first successful import) | [**Quick Start (`README_APP.md`)**](README_APP.md) — also shipped with the build |
| **Configure fields, tables, credentials** | [`docs/CONFIG.md`](docs/CONFIG.md) |
| **Understand Cloud import behavior** | [`docs/CLOUD.md`](docs/CLOUD.md) |
| **See the full feature list** | [`docs/FEATURES.md`](docs/FEATURES.md) |
| **Develop or contribute** | [`docs/DEV.md`](docs/DEV.md) · [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) |

## Important notice

**`--cloud` works with Jira Cloud only** (REST API v3).

- **CSV export** works for Cloud, Server, and Data Center (manual upload in Jira).
- **Direct API import** does **not** support Jira Server, Data Center, or legacy Jira.

Interested in Server/Data Center API support? Describe your constraints in [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues) or via [deerhide.run](https://deerhide.run).

## Who is this for?

**Project managers, team leads, producers**, and anyone who plans in Excel and later needs issues in Jira—especially if CSV import has been painful.

## Why it exists

Jira CSV import is strict: columns, IDs, hierarchy, and field formats must match expectations, and failures are often hard to decode. This toolkit validates and cleans Excel data, then either writes a Jira-ready CSV or creates issues in **Jira Cloud**.

## Download

**[Get the latest release](https://github.com/DeerHide/jira-toolkit/releases)** — no install required on Windows or macOS.

| Platform | What you get |
| --- | --- |
| **Windows** | Standalone `jira-importer.exe` (drag & drop Excel onto the EXE for CSV export) |
| **macOS** | Native `jira-importer` binary |
| **From source** | Python 3.12+ (see [`docs/DEV.md`](docs/DEV.md)) |

### Templates

- **`ImportTemplate.xlsx`** — in release bundles and in [`resources/templates/`](resources/templates/) in this repo.
- **`ImportTemplate_with_config.xlsx`** — sample Config sheet; on Releases when published (not always in git).
- **JSON samples** — [`resources/templates/`](resources/templates/) (`config_importer.json`, and related files).

Shipped builds include the app guide: **[`README_APP.md`](README_APP.md)**.

## 60-second path

1. Download the app and **`ImportTemplate.xlsx`** from [Releases](https://github.com/DeerHide/jira-toolkit/releases).
2. Fill the **Dataset** sheet (keep the expected headers).
3. Prefer a dry run, then choose CSV or Cloud:

```bash
# Windows
jira-importer.exe your-data.xlsx --dry-run
jira-importer.exe your-data.xlsx                 # → your-data_jira_ready.csv
jira-importer.exe your-data.xlsx --cloud         # Jira Cloud only

# macOS
./jira-importer your-data.xlsx --dry-run
./jira-importer your-data.xlsx
./jira-importer your-data.xlsx --cloud
```

**Full walkthrough (verify success, credentials, troubleshooting):** see [**README_APP.md**](README_APP.md).

## Choose your import path

| Path | Use when | Prerequisites | You’re done when |
| --- | --- | --- | --- |
| **CSV export** | Any Jira (Cloud / Server / DC); you want to review before upload | Excel in template shape | `*_jira_ready.csv` exists; you upload it via Jira **Bulk create** / CSV import |
| **Cloud import** (`--cloud`) | Jira Cloud; create issues without manual upload | Config (site + project) + credentials (`--credentials run` or env) | Console shows create/submit summary; issues appear in the project |
| **Dry run** (`--dry-run`) | First run or after config changes | Same as above | Processing completes with **no** output write / no Cloud create |

Cloud credentials (interactive): `jira-importer.exe --credentials run` (macOS: `./jira-importer --credentials run`).

## Key capabilities

- Excel (`.xlsx`) → Jira-compatible CSV and/or **Jira Cloud** API create
- Validation for issue types, priorities, components, IDs, hierarchy, and more
- Optional **`--auto-fix`** for safe, common corrections
- Skips junk / note rows when configured
- CLI and standalone binaries (Windows / macOS)
- Rules and mappings via **JSON** or **Excel Config** (`-ci` / `-ce`)
- Custom fields when configured (details in [`docs/CONFIG.md`](docs/CONFIG.md) and [`docs/FEATURES.md`](docs/FEATURES.md))

## CLI at a glance

| Option | Description |
| --- | --- |
| `your-data.xlsx` | Input workbook |
| `-c, --config` | Specific configuration file |
| `-ce, --config-excel` | Excel `Config` sheet + `config*` / `cfg*` tables |
| `-cd, --config-default` | Built-in default configuration |
| `-ci, --config-input` | Config file next to the Excel file (recommended for JSON) |
| `--cloud` | Create issues in Jira Cloud (requires connection config + credentials) |
| `--auto-fix` | Apply safe automatic fixes during validation |
| `--credentials [ACTION]` | `run` / `show` / `clear` / `test` |
| `--data-sheet NAME` | Data tab name (default: **Dataset**) |
| `--dry-run` | Process without writing output / creating issues |
| `--show-config` | Show configuration (no input file required) |
| `-d, --debug` | Verbose troubleshooting output |
| `-v, --version` | Version information |

## Input expectations (summary)

- Prefer **`ImportTemplate.xlsx`**; do not rename headers unless you know the schema.
- Default data sheet: **Dataset** (exact tab name).
- Empty rows are ignored; configurable skip rules can drop note/comment rows.

For examples, custom fields, and row-skipping detail, see [**README_APP.md**](README_APP.md) and [`docs/CONFIG.md`](docs/CONFIG.md).

## Configuration (hub)

| Method | Flag | Best for |
| --- | --- | --- |
| Excel `Config` + tables | `-ce` | Single-file workflows; lookup tables in the workbook |
| JSON next to the Excel file | `-ci` | Shared/team config and automation |
| Explicit file | `-c` | Pointing at a known path |
| Built-in default | `-cd` | Quick experiments |

**Excel tables (when using `-ce`):** required — `CfgAssignees`, `CfgIssueTypes`, `CfgIgnoreList`, `CfgPriorities`, `CfgAutofieldValues`; optional — `CfgSprints`, `CfgFixVersions`, `CfgComponents`, `CfgTeams`, `CfgCustomFields`.

Deep reference: [`docs/CONFIG.md`](docs/CONFIG.md).

## Docs map

| Doc | Audience |
| --- | --- |
| [`README_APP.md`](README_APP.md) | End users (shipped with the build) |
| [`docs/CONFIG.md`](docs/CONFIG.md) | Configuration |
| [`docs/CLOUD.md`](docs/CLOUD.md) | Cloud import |
| [`docs/FEATURES.md`](docs/FEATURES.md) | Feature inventory |
| [`docs/DEV.md`](docs/DEV.md) | Developers |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Contributors |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Maintainers / deep design |

## Roadmap (short)

Planned themes include Linux builds, multi-file imports, richer templates, Server/Data Center API support, and deeper reporting. Track requests and status on [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues).

## Support

- [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues) — bugs and feature requests  
- [GitHub Discussions](https://github.com/DeerHide/jira-toolkit/discussions) — questions  
- App troubleshooting steps — [`README_APP.md`](README_APP.md)  
- Website — [deerhide.run](https://deerhide.run)

**Repository:** [DeerHide/jira-toolkit](https://github.com/DeerHide/jira-toolkit)  
**License:** MIT
