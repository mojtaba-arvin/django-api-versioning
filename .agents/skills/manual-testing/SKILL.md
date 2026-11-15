---
name: manual-testing
description: Run focused unit and integration tests or the full tox compatibility matrix. Use after code or test changes and before a release.
---


# Manual testing

Use the current configuration, not remembered environment counts. `tox.ini` is the source of truth for environments; `scripts/check_tox_workflow_matrix.py` verifies the GitHub Actions matrix.

## Quick: focused tests after a change

Use the active project environment and target only tests exercising changed behavior:

```bash
python -m pytest tests/test_relevant_module.py -v --tb=short
```

For integration behavior, use the integration project's explicit configuration in a separate invocation:

```bash
python -m pytest -c integration_test_project/pytest.ini integration_test_project -v --tb=short
```

Markdown-only changes normally need frontmatter, link, and technical-claim checks—not Python tests—unless executable examples or behavior are affected.

## Single: one selected environment

Select an interpreter configured in the current `tox.ini`. Create an isolated environment with uv if needed; install the package and required test dependencies. Record the resolved Python, Django, and DRF versions. Do not use an arbitrary system interpreter or infer tested support from classifiers.

## Full: configured tox matrix

Use before release and when compatibility coverage is part of the task.

1. Ensure uv is available. If tox is not installed, provision it with the required plugin:

```bash
uv tool install --upgrade tox --with tox-uv
export PATH="$(uv tool dir --bin):$PATH"
```

2. Check the explicit Actions matrix against tox:

```bash
python scripts/check_tox_workflow_matrix.py
```

3. Run every environment declared by the current tox configuration:

```bash
tox run-parallel -p auto > /tmp/tox-full.log 2>&1
TOX_EXIT=$?
cat /tmp/tox-full.log
echo "TOX_EXIT=$TOX_EXIT"
```

`tox-uv` provisions uv-managed interpreters when required. Do not manually install a hard-coded Python version list or copy a historical environment count.

## Acceptance and reporting

- Inspect the summary and logs for every configured environment. Failed, skipped, or NOT-RUN environments are not passes.
- Confirm the real exit status; a summary count alone is insufficient.
- Verify lint separately. For test environments, confirm both unit and integration invocations ran and passed.
- Classify interpreter/plugin/dependency failures as setup failures and pytest failures as test failures.
- Update `COMPATIBILITY_REPORT.md` only after a complete successful Full run. Preserve its format and derive every value from that run. Record source commit, package version, resolved dependency versions, command, timestamp, and exit status.
- Never change compatibility claims based only on configured environments.

## Change-to-check map

| Change | Minimum verification |
| --- | --- |
| Package code or tests | Relevant unit tests; integration tests when framework wiring changes |
| Integration project | Integration pytest invocation with explicit config |
| tox or compatibility workflow | Matrix validator, YAML validation, affected workflow |
| Packaging metadata/build inputs | Build wheel and sdist; validate metadata and inspect both archives |
| Agent instructions/skills | `python scripts/agent.py verify` |
| Website-only source | Website preflight and relevant static-build checks |
