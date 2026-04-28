# Contributing

This guide covers contribution workflow only. For setup and runtime commands, use `docs/DEV.md`.

## First-Time Contributor Setup

<details>
<summary>Show first-time setup steps</summary>

```bash
git clone https://github.com/YOUR_USERNAME/jira-toolkit.git
cd jira-toolkit
git remote add upstream https://github.com/DeerHide/jira-toolkit.git
poetry install --extras dev
```

Keep your branch current:

```bash
git fetch upstream
git checkout main
git pull upstream main
git checkout -b feature/short-description
```

</details>

## Before You Open A PR

1. Create a branch from the latest default branch.
2. Keep the change focused and reviewable.
3. Add or update tests for behavior changes.
4. Update docs when user-facing or developer-facing behavior changes.

## Local Checks

Run these before pushing:

```bash
poetry run pytest
poetry run ruff check src tests
poetry run mypy src
```

If formatting is needed:

```bash
poetry run ruff format src tests
```

## Pull Request Expectations

- Use a clear title that explains behavioral intent.
- Describe what changed and why.
- Include test evidence (commands run and outcomes).
- Note any risks, limitations, or follow-up tasks.
- Keep changes focused; avoid bundling unrelated refactors.
- Keep docs aligned with code sources of truth:
  - CLI options: `src/jira_importer/app.py`
  - Build profiles: `build/configs/profiles.json`
  - Runtime/package constraints: `pyproject.toml`

## Review Notes

- Avoid unrelated refactors in the same PR.
- Prefer explicit, factual wording in docs.
- Do not include time estimates in technical documentation.

## Suggested PR Checklist

<details>
<summary>Show checklist</summary>

- [ ] Scope is clear and limited.
- [ ] Tests added/updated where behavior changed.
- [ ] `poetry run pytest` passes.
- [ ] `poetry run ruff check src tests` passes.
- [ ] `poetry run mypy src` passes.
- [ ] Docs updated if user-facing or developer-facing behavior changed.

</details>

## Help

- Issues: [GitHub Issues](https://github.com/DeerHide/jira-toolkit/issues)
- Discussions: [GitHub Discussions](https://github.com/DeerHide/jira-toolkit/discussions)
