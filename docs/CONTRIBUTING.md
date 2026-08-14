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

Activate `.venv` (`source .venv/bin/activate` or `.venv\Scripts\activate`), then run:

```bash
pytest
ruff check src tests scripts
mypy
```

If formatting is needed:

```bash
ruff format src tests scripts
```

GitHub Actions runs these same tools from `.venv/bin` on every PR (Linux, Python 3.12). Local pre-commit stays format-on-commit; pytest, mypy, and pylint run on push.

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
- [ ] `mypy` passes.
- [ ] Docs updated if user-facing or developer-facing behavior changed.

## Help

- Issues: [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues)
- Discussions: [GitHub Discussions](https://github.com/DeerHide/jira-toolkit/discussions)
