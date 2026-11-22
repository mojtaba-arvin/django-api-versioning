---
name: package-engineering
description: Implement or change django-api-versioning package behavior, public APIs, tests, compatibility, or technical documentation.
---


# Package engineering

Use for package behavior, public APIs, Django/DRF integration, dependencies, tests, compatibility, or package-facing documentation. Do not use for website-only or editorial-only tasks.

## Workflow

0. Start on a short-lived task branch based on the latest `origin/main`; never implement or commit directly on `main`. Follow [CONTRIBUTING.md](../../../CONTRIBUTING.md) for branch, commit, and pull-request conventions. Before every commit, produce one Conventional Commit subject (lowercase imperative, optional scope, no trailing period, at most 100 characters), validate it with `python scripts/check_commit_message.py --message 'type(scope): summary'`, and use the same valid subject as the PR title because squash merge copies the PR title to `main`. Never create generic or progress-style commit messages.
1. Run `python scripts/agent.py context implementation`. Read `pyproject.toml` and `docs/reference/versioning-contract.md`; inspect only relevant modules, callers, and tests.
2. Establish current behavior before editing. Trace public entry points and framework lifecycle; distinguish import-time registration from request-time behavior.
3. Choose the smallest correct design. Preserve Django-native behavior, optional DRF integration, supported Python versions, and a lightweight runtime. Avoid unrelated refactors and new runtime dependencies. Before changing a public CLI flag, default, or write behavior, record the existing contract and add tests for default and explicit modes; make destructive writes opt-in unless the established contract explicitly requires otherwise.
4. Add regression tests for observable behavior: success, invalid input, boundaries, errors, and interactions with public APIs. Reuse `tests/` and `integration_test_project/`; do not create a second Django project. For expected failures, satisfy every earlier precondition and assert the intended error (`match=` when stable); a test that fails earlier does not cover the target branch.
5. Run focused tests first. For integration behavior, use its own pytest configuration. Use the manual-testing skill for full-matrix execution and acceptance criteria.
6. Update canonical references, README, changelog, or articles only when the user-visible contract changes. `docs/articles/` remains the only editable article corpus.
7. Run Black/isort once over all changed Python files after implementation, not as per-file commits. Then run `tox run -e lint` on the final Python tree before committing. Do not commit or push while lint is pending or failing; any later Python edit requires rerunning lint. Configure `git config commit.template .gitmessage` and, when pre-commit is installed, install the commit-message, commit, and push hooks (`pre-commit install --hook-type commit-msg`, `pre-commit install`, and `pre-commit install --hook-type pre-push`). The commit-message hook and required PR gate enforce Conventional Commit subjects; the pre-push hook is a final local guard, not a replacement for running lint and checking CI. Review the complete diff for compatibility, security, public API changes, packaging, CI triggers, and unsupported claims. Use safe-checkpoint only after validation; batch the logical change into one commit.

## Evidence

Report exact commands and exit codes. Separate verified behavior from assumptions. A configured tox environment is not a passing environment. Do not infer DRF compatibility beyond the combinations actually tested.
