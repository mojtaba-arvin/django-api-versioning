---
name: manual-testing
description: Run focused unit and integration tests or the full tox compatibility matrix. Use after code or test changes and before a release.
---


# Manual testing

Use the current configuration, not remembered environment counts. `tox.ini` is the source of truth for environments; `scripts/check_tox_workflow_matrix.py` verifies the GitHub Actions matrix. For releases, prefer the compatibility workflow result for the exact release-PR head SHA; do not rerun the same full matrix manually when that exact SHA has already passed CI. The tag-triggered publish workflow runs the matrix again as the final publication gate.

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

Use for deliberate full local verification, when CI is unavailable, or when reproducing a compatibility failure. The release procedure uses the exact-commit PR CI result as its pre-merge matrix gate.

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
set +e
tox run-parallel -p auto > /tmp/tox-full.log 2>&1
TOX_EXIT=$?
set -e
cat /tmp/tox-full.log
echo "TOX_EXIT=$TOX_EXIT"
exit "$TOX_EXIT"
```

`tox-uv` provisions uv-managed interpreters when required. Do not manually install a hard-coded Python version list or copy a historical environment count.

## Acceptance and reporting

- Inspect the summary and logs for every configured environment. Failed, skipped, or NOT-RUN environments are not passes.
- Confirm the real exit status; a summary count alone is insufficient.
- Run `tox run -e lint` after the final Python edit and inspect the real exit code; a successful pytest run does not imply formatting or lint success. For test environments, confirm both unit and integration invocations ran and passed.
- Classify interpreter/plugin/dependency failures as setup failures and pytest failures as test failures.
- Do not overwrite historical compatibility reports. `docs/reports/compatibility-0.3.8.md` is immutable release evidence, not a current results file. Report current matrix results against the exact commit and workflow run; create a new versioned report only when the user explicitly requests one.
- Never change compatibility claims based only on configured environments.

## Change-to-check map

| Change | Minimum verification |
| --- | --- |
| Package code or tests | Relevant unit tests; integration tests when framework wiring changes; `tox run -e lint` after the final Python edit |
| Integration project | Integration pytest invocation with explicit config |
| tox or compatibility workflow | Matrix validator, YAML validation, affected workflow |
| Packaging metadata/build inputs | Build wheel and sdist; validate metadata and inspect both archives |
| Agent instructions/skills | `python scripts/agent.py verify` |
| Website-only source | Website preflight and relevant static-build checks |
