# Skill: Manual Testing - django-api-versioning

Two modes — Quick and Full. Never use system `python3` (3.8.10).

## Quick — after EVERY file change

Run only the touched test file. Seconds.

```bash
pytest <touched_test_file> -v
```

Examples:

```bash
pytest tests/test_decorators.py -v
pytest tests/test_settings.py -v
pytest integration_test_project/tests/test_drf_viewset.py -v
```

If no venv is active, use the closest recent one:

```bash
/tmp/env-3.12/bin/python -m pytest <file> -v
```

If unsure which test covers the change:

```bash
pytest tests/ -k "<keyword>" -v
```

If nothing matches, skip Quick and rely on the next Full run.

Do NOT install a full matrix for Quick.

## Full — after a logical batch, before any release

Runs BOTH `tests/` (unit) and `integration_test_project/tests/`
(integration) across Python 3.10–3.15.

### 1. Install Pythons (idempotent)

```bash
for v in 3.10 3.11 3.12 3.13 3.14 3.15; do uv python install "$v"; done
```

### 2. Test each version — one Bash call per version

```bash
V=3.10
uv venv /tmp/env-$V --python $V
uv pip install --python /tmp/env-$V/bin/python \
  -e /home/repl/django-api-versioning \
  pytest pytest-django djangorestframework

/tmp/env-$V/bin/python --version

/tmp/env-$V/bin/python -m pytest \
  /home/repl/django-api-versioning/tests/ \
  -v --tb=short 2>&1 | tee /tmp/pytest-unit-$V.log

/tmp/env-$V/bin/python -m pytest \
  /home/repl/django-api-versioning/integration_test_project/tests/ \
  -v --tb=short 2>&1 | tee /tmp/pytest-integ-$V.log

rm -rf /tmp/env-$V
```

Repeat for 3.11, 3.12, 3.13, 3.14, 3.15.

If `pip install -e .` fails with build isolation, prepend
`PYTHONPATH=/home/repl/django-api-versioning` to the pytest commands.

### 3. Report

| Python | Django | Unit pass | Unit fail | Integ pass | Integ fail |
|--------|--------|-----------|-----------|------------|------------|

Parse counts from `/tmp/pytest-unit-$V.log` and
`/tmp/pytest-integ-$V.log`. Do not fabricate.

If any unit or integration test fails, include the traceback
filename in a Notes column (verbatim, not paraphrased).

## When to run which

| Trigger | Mode |
|---------|------|
| Any file edited | Quick |
| Test file added | Quick |
| Bug fixed | Quick (target file) |
| All bugs of a batch fixed | Full |
| All tests of a batch written | Full |
| Before tagging a release | Full + `/compat-matrix` |

## Never
- Never use system `python3` (3.8.10).
- Never rely on `source` persisting across Bash calls.
- Never claim a test passed unless pytest printed `PASSED`.
- Never fabricate counts, versions, coverage.
- Never skip integration tests in Full mode.
- Never run Full mode after every file change.
