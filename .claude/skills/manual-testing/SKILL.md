---
name: manual-testing
description: Use to run tests — Quick after edits, Single for one Python version, Full via tox for all supported envs.
---

# Skill: Manual Testing - django-api-versioning

Three modes. `tox.ini` is the source of truth for the supported matrix.

## Matrix

`tox.ini` envlist at the time of this skill:

- py{310,311,312,313,314}-django52
- py{312,313,314}-django60
- py{312,313,314,315}-django61
- lint

13 envs total. Django 5.2, 6.0, 6.1 only. If `pyproject.toml` changes
the minimum Django, update `tox.ini` first, not this skill.

## Quick — after EVERY file change

Run only the touched test file. Seconds.

```bash
set -o pipefail
python -m pytest <touched_test_file> -v --tb=short
echo "exit=$?"
```

If no venv is active, skip Quick and rely on the next Single or Full.

## Single — one Python version, both test suites (baseline)

For Phase 1 baseline. Unit + integration on one Python. No tox.

```bash
set -o pipefail
V=3.15
uv venv /tmp/env-$V --python $V || { echo "VENV FAIL $V"; exit 1; }
uv pip install --python /tmp/env-$V/bin/python \
  -e /home/repl/django-api-versioning \
  pytest pytest-django pytest-cov djangorestframework \
  || { echo "INSTALL FAIL $V"; exit 2; }

/tmp/env-$V/bin/python --version
/tmp/env-$V/bin/python -c \
  "import django, rest_framework; print('Django:', django.get_version()); print('DRF:', rest_framework.VERSION)"

/tmp/env-$V/bin/python -m pytest /home/repl/django-api-versioning/tests/ \
  -v --tb=short 2>&1 | tee /tmp/pytest-unit-$V.log
UNIT_EXIT=${PIPESTATUS[0]}

/tmp/env-$V/bin/python -m pytest /home/repl/django-api-versioning/integration_test_project/ \
  -v --tb=short 2>&1 | tee /tmp/pytest-integ-$V.log
INTEG_EXIT=${PIPESTATUS[0]}

echo "UNIT_EXIT=$UNIT_EXIT INTEG_EXIT=$INTEG_EXIT"
```

Note: the integration file is `integration_test_project/test_integration.py`
— point pytest at the directory `integration_test_project/`, not a
subpath `tests/` that does not exist.

## Full — all tox envs

Use for Phase 10 QA and before `/release`.

### Sandbox setup (once per session)

```bash
uv venv /tmp/tox --python 3.15
uv pip install --python /tmp/tox/bin/python tox
```

### Run

```bash
set -o pipefail
PATH="$HOME/.local/bin:$PATH" /tmp/tox/bin/tox 2>&1 | tee /tmp/tox-full.log
TOX_EXIT=${PIPESTATUS[0]}
echo "TOX_EXIT=$TOX_EXIT"
```

On the user's local machine (tox already installed):

```bash
set -o pipefail
tox 2>&1 | tee /tmp/tox-full.log
TOX_EXIT=${PIPESTATUS[0]}
echo "TOX_EXIT=$TOX_EXIT"
```

`tox` runs every env in the envlist. Each env installs its Django
version, runs pytest across `tests/` and `integration_test_project/`
from repo root, so both suites execute automatically. Lint env runs
flake8, black --check, isort --check-only.

`--maxfail=1` in tox.ini stops within each env on first failure, but
tox continues to the next env. Per-env summary at end of log.

## Reporting rules

From `/tmp/tox-full.log`, parse the summary block:

```
  py310-django52: commands succeeded
  py311-django52: commands succeeded
  ...
  lint: commands succeeded
```

Report each env's status verbatim. Do not merge. Do not fabricate.

`TOX_EXIT=0` means all envs passed. Non-zero means at least one
failed — report the failing env names.

Do not claim a test passed unless the exit code is 0.

## When to run which

| Trigger | Mode |
|---------|------|
| Any file edited | Quick |
| Phase 1 baseline | Single (V=3.15) |
| Phase 10 QA | Full (tox) |
| Before `/release` | Full (tox) |

## Update COMPATIBILITY_REPORT.md after Full

After `tox` completes, update `COMPATIBILITY_REPORT.md` from
`/tmp/tox-full.log`. Do not fabricate — every row must come from
the actual tox output.

### Structure

```markdown
# Compatibility Report

**Date**: <date -u +%Y-%m-%d>
**Source**: tox run on <hostname>, envlist from tox.ini
**tox exit code**: <0 or non-zero>

## Supported matrix

| Env | Python | Django | Status | Notes |
|-----|--------|--------|--------|-------|
| py310-django52 | 3.10.x | 5.2.x | ok / FAIL / not-run | from tox log |
| py311-django52 | 3.11.x | 5.2.x | ... | |
| py312-django52 | 3.12.x | 5.2.x | ... | |
| py313-django52 | 3.13.x | 5.2.x | ... | |
| py314-django52 | 3.14.x | 5.2.x | ... | |
| py312-django60 | 3.12.x | 6.0.x | ... | |
| py313-django60 | 3.13.x | 6.0.x | ... | |
| py314-django60 | 3.14.x | 6.0.x | ... | |
| py312-django61 | 3.12.x | 6.1.x | ... | |
| py313-django61 | 3.13.x | 6.1.x | ... | |
| py314-django61 | 3.14.x | 6.1.x | ... | |
| py315-django61 | 3.15.x | 6.1.x | ... | |
| lint | - | - | ok / FAIL | flake8 + black + isort |

## Test suite composition

- Unit tests: `tests/` (test count parsed from tox log)
- Integration tests: `integration_test_project/test_integration.py`
- Coverage: enforced by pytest-cov per pyproject addopts

## Unsupported combinations

`tox.ini` does not include Django 4.2, 5.0, or 5.1. These versions
are not part of the tested matrix. Do not claim support for them.

Do not label any combination "SUPPORTED" without an `ok` row in
the table above.
```

### Rules

- If a tox env is `FAIL`, copy the failing test names from the log
  verbatim into the Notes column.
- If tox was not run in this session, do NOT touch the report.
- Never carry over a previous report's numbers without a new tox run.
- Never label a combination "SUPPORTED" if its row is not `ok`.

### Commit

```bash
git add COMPATIBILITY_REPORT.md
git commit -m "docs: update compatibility report from tox run on <date>"
.claude/push.sh
```

### Trigger

Update the report after:
- Phase 10 QA (the tox run is required by the spec)
- Any release `/release` pre-check tox run
- Any manual Full run the user explicitly requested

Do NOT update it after Quick or Single mode — those do not cover
the matrix.

## Never
- Never use system `python3` (3.8.10) for Single or Quick.
- Never install without `pytest-cov` — pyproject's addopts requires it.
- Never pipe to `tee` without `set -o pipefail` and `${PIPESTATUS[0]}`.
- Never claim a test passed unless the exit code is 0.
- Never fabricate counts, versions, coverage.
- Never run Full (tox) in Phase 1.
- Never modify `tox.ini` to add Django versions without updating
  `pyproject.toml` first.
- Never use `.[dev]` — that extras group does not exist in this
  project's pyproject.toml.
