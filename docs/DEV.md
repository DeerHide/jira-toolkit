# Developer Guide

This guide is the quickest reliable path to run, test, and build the project.
It is concise, but sufficient for both regular and occasional contributors.

## Scope

Use this file for daily developer commands.

- Architecture details: `docs/ARCHITECTURE.md`
- Contribution process: `docs/CONTRIBUTING.md`
- Runtime configuration: `docs/CONFIG.md`
- Cloud integration details: `docs/CLOUD.md`
- End-user overview: `README.md`

## Prerequisites

- Python `>=3.12,<3.14` (from `pyproject.toml`)
- Git
- Poetry (primary workflow)

## Setup

Poetry is the primary install path. The pip lock files remain for the legacy `build.py` path and must stay aligned with `pyproject.toml`.

```bash
git clone https://github.com/DeerHide/jira-toolkit.git
cd jira-toolkit
poetry install --extras dev
# PyInstaller build tooling is included by default (poetry group: pyinstaller)
```

Equivalent helper:

```bash
python scripts/install_requirements.py
```

Verify:

```bash
poetry run python -m jira_importer --version
poetry run python -m jira_importer --help
```

### Dependencies (dual pipeline)

| Path | Source of truth / artifact | Use when |
|---|---|---|
| Poetry (primary) | `pyproject.toml` + `poetry.lock` | Daily work, tests, `poetry build`, `build.py -p` |
| Pip / legacy build | `requirements.in` → `requirements.lock` (+ `requirements.txt` twin) | `build.py -c <profile>` when `install_requirements` is enabled |

- Runtime and version floors are declared in `pyproject.toml`.
- `requirements.in` mirrors those floors plus legacy build tooling (`pyinstaller`, Windows `pefile`, `pre-commit`). Keep it in sync when you change Poetry constraints.
- After editing `requirements.in`, regenerate the lock:

```bash
poetry run pip-compile --output-file=requirements.lock --strip-extras requirements.in
# Keep the twin identical when both files are retained:
cp requirements.lock requirements.txt   # macOS/Linux
# Windows PowerShell: Copy-Item -Force requirements.lock requirements.txt
```

### Pip editable fallback

Use this only when Poetry is unavailable. It installs the PEP `dev` extra only.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install -e .[dev]
```

`pip install -e .[dev]` does **not** install the Poetry `pyinstaller` group. For binary builds, use Poetry (`poetry install --extras dev`) or the pip lock (`pip install -r requirements.lock`).

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

## Test And Lint

Activate `.venv` first (`source .venv/bin/activate` or `.venv\Scripts\activate`). Poetry is the installer, not the runner.

```bash
pytest
ruff check src tests scripts
ruff format src tests scripts
mypy
```

### CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) is a Linux quality gate on Python 3.12. Poetry lock/install creates `.venv`; checks run from `.venv/bin` (`ruff`, `mypy`, `pytest`) on pull requests and pushes to `main` and `dev`.

Executable builds stay local (`build.py` / `poetry build --format pyinstaller`). The `gh_action` profile is not invoked by this workflow. PyPI and GitHub Release stay in [`.github/workflows/publish.yml`](../.github/workflows/publish.yml).

## Test Data

- Import template: `resources/templates/ImportTemplate.xlsx`
- Config samples: `resources/templates/config_importer.json` and related templates
- Unit tests: `tests/unit/`

## Common Contributor Tasks

- Add or change a CLI flag: `src/jira_importer/app.py`
- Adjust config loading/precedence: `src/jira_importer/config/`
- Add/modify validation rules: `src/jira_importer/import_pipeline/rules/`
- Add/modify auto-fixes: `src/jira_importer/import_pipeline/fixes/`
- Change CSV output behavior: `src/jira_importer/import_pipeline/sinks/csv_sink.py`
- Change cloud import behavior: `src/jira_importer/import_pipeline/sinks/cloud_sink.py`
- Update credential handling: `src/jira_importer/import_pipeline/cloud/credential_manager.py`

## Build

Both build entrypoints are supported. Prefer running them from a Poetry-managed environment so the active interpreter matches installed deps:

```bash
poetry run python build.py -c shipping
poetry run python build.py -p -c shipping
# or:
poetry build --format pyinstaller
```

Supported build profiles are `debug`, `dev`, `shipping`, and `gh_action` (see `build/configs/profiles.json`).

```bash
python build.py -c dev
python build.py -c shipping
python build.py -p -c shipping
```

- `debug`: local debugging profile
- `dev`: local development profile
- `shipping`: production distribution profile (`install_requirements` uses `requirements.lock`)
- `gh_action`: CI-oriented production profile (`install_requirements` uses `requirements.lock`)
- `-p` / `poetry build --format pyinstaller`: Poetry PyInstaller plugin path

If dependency checks fail, install via one of:

```bash
poetry install --extras dev
python -m pip install -r requirements.lock
python scripts/install_requirements.py
```

## Troubleshooting

- Config not found or missing keys: run `--show-config` first.
- Auth failures: run `--credentials test` and verify Jira permissions.
- Unexpected output: re-run with `--dry-run --debug`.
- Environment drift: prefer `poetry install --extras dev` from a clean environment (includes PyInstaller).
- Pip/`build.py` drift: regenerate `requirements.lock` from `requirements.in` after changing `pyproject.toml` floors.

## Documentation Ownership

To reduce drift:

- CLI flags source of truth: `src/jira_importer/app.py`
- Build profiles source of truth: `build/configs/profiles.json`
- Package/runtime constraints source of truth: `pyproject.toml` (mirror into `requirements.in` for the pip/legacy path)
