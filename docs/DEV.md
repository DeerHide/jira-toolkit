# Developer Guide

This guide is the quickest reliable path to run, test, and build the project.
It is concise, but sufficient for both regular and occasional contributors.

## Scope

Use this file for daily developer commands.

<details>
<summary>Show related documentation files</summary>

- Architecture details: `docs/ARCHITECTURE.md`
- Contribution process: `docs/CONTRIBUTING.md`
- Runtime configuration: `docs/CONFIG.md`
- Cloud integration details: `docs/CLOUD.md`
- End-user overview: `README.md`

</details>

## Prerequisites

- Python `>=3.12,<3.14` (from `pyproject.toml`)
- Git
- Poetry (primary workflow)

## Setup

```bash
git clone https://github.com/DeerHide/jira-toolkit.git
cd jira-toolkit
poetry install --extras dev
```

Verify:

```bash
poetry run python -m jira_importer --version
poetry run python -m jira_importer --help
```

<details>
<summary>Alternative setup (venv + pip)</summary>

Use this only when Poetry is unavailable in your environment.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install -e .[dev]
```

</details>

## Run

Core commands:

```bash
poetry run python -m jira_importer path/to/data.xlsx
poetry run python -m jira_importer path/to/data.xlsx --dry-run
poetry run python -m jira_importer path/to/data.xlsx --cloud
poetry run python -m jira_importer --show-config
```

Credential commands:

```bash
poetry run python -m jira_importer --credentials run
poetry run python -m jira_importer --credentials show
poetry run python -m jira_importer --credentials clear
poetry run python -m jira_importer --credentials test
```

<details>
<summary>High-value run variants</summary>

```bash
# Excel config sheet
poetry run python -m jira_importer path/to/data.xlsx --config-excel

# Config next to input file
poetry run python -m jira_importer path/to/data.xlsx --config-input

# Explicit config file
poetry run python -m jira_importer path/to/data.xlsx --config path/to/config.json

# Debug output
poetry run python -m jira_importer path/to/data.xlsx --debug
```

</details>

## Test And Lint

```bash
poetry run pytest
poetry run ruff check src tests
poetry run ruff format src tests
poetry run mypy src
```

## Test Data

- Import template: `resources/templates/ImportTemplate.xlsx`
- Config samples: `resources/templates/config_importer.json` and related templates
- Unit tests: `tests/unit/`

## Common Contributor Tasks

<details>
<summary>Show task-to-file map</summary>

- Add or change a CLI flag: `src/jira_importer/app.py`
- Adjust config loading/precedence: `src/jira_importer/config/`
- Add/modify validation rules: `src/jira_importer/import_pipeline/rules/`
- Add/modify auto-fixes: `src/jira_importer/import_pipeline/fixes/`
- Change CSV output behavior: `src/jira_importer/import_pipeline/sinks/csv_sink.py`
- Change cloud import behavior: `src/jira_importer/import_pipeline/sinks/cloud_sink.py`
- Update credential handling: `src/jira_importer/import_pipeline/cloud/credential_manager.py`

</details>

## Build

Supported build profiles are `debug`, `dev`, `shipping`, and `gh_action` (see `build/configs/profiles.json`).

```bash
python build.py -c dev
python build.py -c shipping
python build.py -p -c shipping
```

<details>
<summary>Build profile intent</summary>

- `debug`: local debugging profile
- `dev`: local development profile
- `shipping`: production distribution profile
- `gh_action`: CI-oriented production profile

</details>

## Troubleshooting

<details>
<summary>Show common issues</summary>

- Config not found or missing keys: run `--show-config` first.
- Auth failures: run `--credentials test` and verify Jira permissions.
- Unexpected output: re-run with `--dry-run --debug`.
- Environment drift: prefer `poetry install --extras dev` from a clean environment.

</details>

## Documentation Ownership

To reduce drift:

<details>
<summary>Show source-of-truth files</summary>

- CLI flags source of truth: `src/jira_importer/app.py`
- Build profiles source of truth: `build/configs/profiles.json`
- Package/runtime constraints source of truth: `pyproject.toml`

</details>
