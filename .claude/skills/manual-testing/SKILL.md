# Skill: Manual Testing - django-api-versioning

Three modes — Quick, Single, Full. Never use system `python3` (3.8.10).

`pyproject.toml` sets `addopts = "-ra --cov=django_api_versioning --cov-report=term-missing"`. That means `pytest-cov` is REQUIRED. Every install below includes it.

Reliable exit codes need `set -o pipefail` on every Bash call that uses `tee`. Without it, `tee` masks pytest's exit code.

## Quick — after EVERY file change

Run only the touched test file. Seconds. Uses whatever venv is already in `/tmp/env-*`.

```bash
set -o pipefail
/tmp/env-3.15/bin/python -m pytest <touched_test_file> -v --tb=short
echo "exit=$?"
```

If no `/tmp/env-*` exists, skip Quick and wait for the next Single or Full run.

## Single — one Python version, both test suites

Use for baseline in Phase 1. One version only.

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

/tmp/env-$V/bin/python -m pytest \
  /home/repl/django-api-versioning/tests/ \
  -v --tb=short 2>&1 | tee /tmp/pytest-unit-$V.log
UNIT_EXIT=${PIPESTATUS[0]}

/tmp/env-$V/bin/python -m pytest \
  /home/repl/django-api-versioning/integration_test_project/tests/ \
  -v --tb=short 2>&1 | tee /tmp/pytest-integ-$V.log
INTEG_EXIT=${PIPESTATUS[0]}

echo "UNIT_EXIT=$UNIT_EXIT INTEG_EXIT=$INTEG_EXIT"
```

If `VENV FAIL` or `INSTALL FAIL`: report that separately from test results. Do not attempt to run pytest.

If `UNIT_EXIT` or `INTEG_EXIT` is non-zero: report as test failure with the log path. Do not claim success based on the word "passed" in the log — rely on the exit code.

## Full — every Python version, both test suites

Use only in Phase 10 (final QA) and before `/release`. Never for baseline.

Run the Single block six times with `V=3.10`, `V=3.11`, `V=3.12`, `V=3.13`, `V=3.14`, `V=3.15`. Each iteration is a separate Bash call so that a hang or failure on one version does not block the others.

After all six complete, assemble the report:

| Python | Django | DRF | Unit exit | Unit pass | Unit fail | Integ exit | Integ pass | Integ fail |
|--------|--------|-----|-----------|-----------|-----------|------------|------------|------------|

Parse counts from `/tmp/pytest-unit-$V.log` and `/tmp/pytest-integ-$V.log`. Parse Django/DRF from the version-check output of each run.

If any install failed, mark the row `INSTALL FAIL` and do not fabricate test counts for it.

## Reporting rules

State three separate categories:

1. **Install failures** — `VENV FAIL` or `INSTALL FAIL`. Cannot be tested.
2. **Collection failures** — pytest exit code 2/3/4, typically an import error. Report the traceback head.
3. **Test failures** — pytest exit code 1, one or more assertions failed.

Never merge these. Never claim a version "passed" if its install failed.

## When to run which

| Trigger | Mode |
|---------|------|
| Any file edited | Quick |
| Phase 1 baseline | Single (`V=3.15`) |
| Phase 10 QA | Full (all six) |
| Before `/release` | Full + `/compat-matrix` |

## Never
- Never use system `python3` (3.8.10).
- Never install without `pytest-cov` — pyproject's `addopts` requires it.
- Never pipe to `tee` without `set -o pipefail` and `PIPESTATUS`.
- Never claim a test passed unless the pytest exit code is 0.
- Never fabricate counts, versions, coverage.
- Never skip integration tests in Single or Full.
- Never run Full mode in Phase 1.
