# Contributing

This guide covers contribution workflow only. For setup and runtime commands, use `docs/DEV.md`.

## First-Time Contributor Setup

```bash
git clone https://github.com/YOUR_USERNAME/jira-toolkit.git
cd jira-toolkit
git remote add upstream https://github.com/DeerHide/jira-toolkit.git
poetry install --extras dev
# Includes the non-optional pyinstaller group so local binary builds work.
# Pip lock path (requirements.*) is for legacy build.py — keep synced with pyproject.toml.
pre-commit install
pre-commit install --hook-type pre-push
# Make git blame skip known formatting-only commits
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

Keep your branch current:

```bash
git fetch upstream
git checkout main
git pull upstream main
git checkout -b feature/short-description
```

## Before You Open A PR

1. Create a branch from the latest default branch.
2. Keep the change focused and reviewable.
3. Add or update tests for behavior changes.
4. Update docs when user-facing or developer-facing behavior changes.

## Local Checks

Prefer `poetry run` (or activate `.venv`). Match CI before opening a PR:

```bash
poetry run ruff check src tests scripts
poetry run ruff format --check src tests scripts
poetry run mypy
poetry run pytest
```

To auto-format locally:

```bash
poetry run ruff format src tests scripts
```

### What CI runs

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) (Linux, Python 3.12, tools from `.venv/bin`):

1. `ruff check src tests scripts`
2. `ruff format --check src tests scripts`
3. `mypy`
4. `pytest`

**Pylint is not in CI.**

### Pre-commit hooks

| Stage | Hooks (summary) |
| --- | --- |
| **pre-commit** | `ruff format`, `ruff check --fix`, `trailing-whitespace`, `end-of-file-fixer`, `check-json` |
| **pre-push** | `poetry install --extras dev --sync`, `pytest` (with coverage), `mypy`, `pylint`, plus whitespace/EOF fixers |

Install both stages with the commands in First-Time Contributor Setup above.

## Pull Request Expectations

- Use a clear title that explains behavioral intent.
- Describe what changed and why.
- Include test evidence (commands run and outcomes).
- Note any risks, limitations, or follow-up tasks.
- Keep changes focused; avoid bundling unrelated refactors.
- Keep docs aligned with code sources of truth:
  - CLI options: `src/jira_importer/app.py`
  - Build profiles: `build/configs/profiles.json`
  - Runtime/package constraints: `pyproject.toml` (primary); mirror floors into `requirements.in` when they change
  - Setup and dual install/build paths: `docs/DEV.md`

## Blame and formatting commits

This repo keeps formatting-only commits in `.git-blame-ignore-revs`.
After cloning, run:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

When you land a pure formatter/layout commit (e.g. bulk `ruff format`),
add its full SHA to that file with a one-line comment explaining why.
Do not list commits that change behavior.

## Review Notes

- Avoid unrelated refactors in the same PR.
- Prefer explicit, factual wording in docs.
- Do not include time estimates in technical documentation.

## Suggested PR Checklist

- [ ] Scope is clear and limited.
- [ ] Tests added/updated where behavior changed.
- [ ] `pytest` passes.
- [ ] `ruff check src tests scripts` passes.
- [ ] `ruff format --check src tests scripts` passes.
- [ ] `mypy` passes.
- [ ] Docs updated if user-facing or developer-facing behavior changed.

## Help

- Issues: [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues)
- Discussions: [GitHub Discussions](https://github.com/DeerHide/jira-toolkit/discussions)
