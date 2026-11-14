---
name: manual-testing
description: Use to run tests — Quick after edits, Single for one Python version, Full via tox for all supported envs.
---

# Skill: Manual Testing - django-api-versioning

Three modes. `tox.ini` is the source of truth for the supported matrix.

## Matrix

`tox.ini` is authoritative. Re-read it before each Full run; the following is the matrix currently configured on this branch:

- `py{310,311,312}-django42` — 3 environments
- `py{310,311,312,313,314}-django52` — 5 environments
- `py{312,313,314}-django60` — 3 environments
- `py{312,313,314,315}-django61` — 4 environments
- `lint` — 1 environment

There are currently 15 test environments plus one lint environment (16 total). This describes configured environments only; it does not establish that they have passed. DRF is not a separate tox matrix dimension.

## Quick — after code or test changes

Run the relevant test file(s) for changed code, or the touched test file when changing tests. Documentation-only changes do not require pytest. Seconds.

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
REPO_ROOT="$(git rev-parse --show-toplevel)"
V=3.15
uv python install "$V"
uv venv "/tmp/env-$V" --python "$V" || { echo "VENV FAIL $V"; exit 1; }
uv pip install --python "/tmp/env-$V/bin/python" \
  -e "$REPO_ROOT" \
  pytest pytest-django pytest-cov djangorestframework \
  || { echo "INSTALL FAIL $V"; exit 2; }

"/tmp/env-$V/bin/python" --version
"/tmp/env-$V/bin/python" -c \
  "import django, rest_framework; print('Django:', django.get_version()); print('DRF:', rest_framework.VERSION)"

"/tmp/env-$V/bin/python" -m pytest "$REPO_ROOT/tests/" \
  -v --tb=short 2>&1 | tee "/tmp/pytest-unit-$V.log"
UNIT_EXIT=${PIPESTATUS[0]}

"/tmp/env-$V/bin/python" -m pytest "$REPO_ROOT/integration_test_project/" \
  -v --tb=short 2>&1 | tee "/tmp/pytest-integ-$V.log"
INTEG_EXIT=${PIPESTATUS[0]}

echo "UNIT_EXIT=$UNIT_EXIT INTEG_EXIT=$INTEG_EXIT"
```

The integration directory has its own `pytest.ini` and `DJANGO_SETTINGS_MODULE`. Run unit and integration tests as separate pytest invocations; the root pytest configuration must not override the integration settings.

## Full — all tox envs

Use for Phase 10 QA and before `/release`.

### Hard prerequisite — fail-fast

tox cannot find Pythons installed by `uv python install` unless
`tox-uv` is installed and `tox.ini` declares `requires = tox-uv`.
Also, tox must run unit and integration as separate pytest
invocations so each uses its own `pytest.ini`. Verify all of this
BEFORE running tox. If any check fails, fix it. Do not proceed to
"run anyway".

```bash
# 1. uv available?
which uv || pip install uv
export PATH="$HOME/.local/bin:$PATH"
uv --version || { echo "UV FAIL"; exit 1; }

# 2. All six Pythons installed?
uv python install 3.10 3.11 3.12 3.13 3.14 3.15
for V in 3.10 3.11 3.12 3.13 3.14 3.15; do
  uv python list 2>/dev/null | grep -q "cpython-$V" \
    || { echo "MISSING PYTHON $V"; exit 1; }
done
echo "All six Python versions required by the current tox matrix are available."

# 3. tox + tox-uv installed?
uv venv /tmp/tox --python 3.15
uv pip install --python /tmp/tox/bin/python tox tox-uv
/tmp/tox/bin/tox --version || { echo "TOX FAIL"; exit 1; }

# 4. tox.ini has tox-uv, DRF, and both test paths?
grep -q 'tox-uv' tox.ini || { echo "TOX.INI MISSING tox-uv"; exit 1; }
grep -q 'djangorestframework' tox.ini || { echo "TOX.INI MISSING DRF"; exit 1; }
grep -q 'integration_test_project' tox.ini || { echo "TOX.INI MISSING INTEGRATION PATH"; exit 1; }

# 5. integration has its own pytest.ini
[ -f integration_test_project/pytest.ini ] \
  || { echo "MISSING integration_test_project/pytest.ini"; exit 1; }

# 6. tox.ini runs unit and integration as separate pytest calls
grep -q 'pytest tests' tox.ini \
  && grep -q 'pytest integration_test_project' tox.ini \
  || { echo "TOX.INI must run pytest on both paths separately"; exit 1; }

echo "Pre-flight OK"
```

If any `FAIL`: STOP. Do not run tox. Report the failing check.
Do not interpret a tox run with NOT-RUN envs as "infrastructure
limitation" — it is a setup failure that this pre-flight prevents.

### Run

```bash
rm -rf .tox
set -o pipefail
PATH="$HOME/.local/bin:$PATH" /tmp/tox/bin/tox 2>&1 | tee /tmp/tox-full.log
TOX_EXIT=${PIPESTATUS[0]}
echo "TOX_EXIT=$TOX_EXIT"
```

### Acceptance checks — mandatory before believing the log

```bash
SUCCEEDED=$(grep -c 'commands succeeded' /tmp/tox-full.log)
NOTRUN=$(grep -c 'interpreter not found' /tmp/tox-full.log || true)
PASSED_LINES=$(grep -c 'passed' /tmp/tox-full.log)
echo "succeeded=$SUCCEEDED not-run=$NOTRUN passed-lines=$PASSED_LINES"
```

For the current matrix, all of these must hold:

- `succeeded == 16` (15 test environments plus lint).
- `not-run == 0`.
- `passed-lines >= 30` (15 test environments × 2 separate pytest invocations).
- Every test environment's log section contains one successful unit-test invocation and one successful integration-test invocation; lint is checked separately.
- `TOX_EXIT == 0`.

If a condition fails, inspect the affected environment sections before classifying the cause. `interpreter not found` or dependency installation failures indicate environment/setup problems; pytest failures indicate test/code failures; missing one of the two pytest invocations indicates a tox configuration problem. Do not label all non-zero results as infrastructure failures.

### Update COMPATIBILITY_REPORT.md only on real results

After all three acceptance conditions hold, regenerate the report
from `/tmp/tox-full.log` per the structure documented in the
"Update COMPATIBILITY_REPORT.md" section below.

If the acceptance checks fail, do NOT touch `COMPATIBILITY_REPORT.md`.
Report the failure instead.

## Never
- Never run Full if the pre-flight check fails.
- Never report `NOT-RUN` as "infrastructure limitation". It is a
  setup failure that the pre-flight check was designed to catch.
- Never claim `succeeded` without `grep -c 'commands succeeded'`
  printing 13.
- Never write `CERTIFIED` or `PRODUCTION READY` if any env is not
  `ok`.

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

After `tox` completes and all three acceptance conditions hold,
update `COMPATIBILITY_REPORT.md` from `/tmp/tox-full.log`. Do not
fabricate — every row must come from the actual tox output.

### Structure

```markdown
# Compatibility Report

**Date**: <date -u +%Y-%m-%d>
**Source**: tox run on <hostname>, envlist from tox.ini
**tox exit code**: <0 or non-zero>

## Supported matrix

| Env | Python | Django | Status | Unit pass | Integ pass | Notes |
|-----|--------|--------|--------|-----------|------------|-------|
| py310-django42 | 3.10.x | 4.2.x | ok / FAIL / NOT-RUN | n | m | from tox log |
| py311-django42 | 3.11.x | 4.2.x | ... | | | |
| py312-django42 | 3.12.x | 4.2.x | ... | | | |
| py310-django52 | 3.10.x | 5.2.x | ... | | | |
| py311-django52 | 3.11.x | 5.2.x | ... | | | |
| py312-django52 | 3.12.x | 5.2.x | ... | | | |
| py313-django52 | 3.13.x | 5.2.x | ... | | | |
| py314-django52 | 3.14.x | 5.2.x | ... | | | |
| py312-django60 | 3.12.x | 6.0.x | ... | | | |
| py313-django60 | 3.13.x | 6.0.x | ... | | | |
| py314-django60 | 3.14.x | 6.0.x | ... | | | |
| py312-django61 | 3.12.x | 6.1.x | ... | | | |
| py313-django61 | 3.13.x | 6.1.x | ... | | | |
| py314-django61 | 3.14.x | 6.1.x | ... | | | |
| py315-django61 | 3.15.x | 6.1.x | ... | | | |
| lint | - | - | ok / FAIL | - | - | flake8 + black + isort |

## Test suite composition

- Unit tests: `tests/` (count parsed from the first `passed` line in
  each env's log section)
- Integration tests: `integration_test_project/` (count parsed from
  the second `passed` line in each env's log section)
- Coverage: enforced by pytest-cov per pyproject addopts

If an env's log section has only one `passed` line, report
`integration: NOT COLLECTED` in the Integ pass column and mark the
env as `FAIL`. Do not fabricate a count.

## Unsupported combinations

`tox.ini` currently includes Django 4.2, 5.2, 6.0, and 6.1. Django 5.0 and 5.1 are not in the configured test matrix. Do not infer test coverage for a version from package classifiers alone.

Do not label any combination "SUPPORTED" without an `ok` row in
the table above.
```

### Rules

- If a tox env is `FAIL`, copy the failing test names from the log
  verbatim into the Notes column.
- If tox was not run in this session, do NOT touch the report.
- Never carry over a previous report's numbers without a new tox run.
- Never label a combination "SUPPORTED" if its row is not `ok`.
- If any env has only one `passed` line, that env's Status is `FAIL`,
  not `ok` — even if the pytest exit code was 0. Two runs are
  required; one run is a setup defect.

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
- Never use an unverified system interpreter for tests; use the active project venv or the explicitly created uv environment.
- Never install without `pytest-cov` — pyproject's addopts requires it.
- Never pipe to `tee` without `set -o pipefail` and `${PIPESTATUS[0]}`.
- Never claim a test passed unless the exit code is 0.
- Never fabricate counts, versions, coverage.
- Never run Full (tox) in Phase 1.
- When changing compatibility declarations, keep `tox.ini`, `pyproject.toml` classifiers, `COMPATIBILITY_REPORT.md`, and user-facing documentation consistent. `tox.ini` defines the configured test matrix; classifiers are metadata and do not prove that a combination was tested.
- Never use `.[dev]` — that extras group does not exist in this
  project's pyproject.toml.
- Never run unit and integration in a single pytest invocation —
  the root `pytest.ini` overrides integration settings.
- Never certify a report if any env has only one `passed` line —
  that means integration did not run.
