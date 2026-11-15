---
name: package-engineering
description: Safely implement, test, review, and document changes to this Django/Python library. Use when changing package behavior, public APIs, compatibility, packaging, tests, or technical documentation.
---

# Package engineering workflow

## 1. Establish the actual baseline

1. Read the root `AGENTS.md` and the relevant task-specific instructions.
2. Inspect `git status`, the current branch, recent commits, and the complete diff before editing.
3. Read `pyproject.toml`, `tox.ini`, the package modules, relevant tests, and integration project before deciding how a change should work.
4. Record the source commit and package version for any compatibility, benchmark, or behavioral evidence.
5. Treat docs and comments as claims to verify—not as proof of implementation.

## 2. Make the smallest correct design

- Preserve the package's Django-native, lightweight runtime and optional DRF integration.
- Do not introduce an agent framework, LLM SDK, MCP server/client, telemetry SDK, or external service into runtime dependencies for repository automation.
- Prefer standard-library and existing project tooling where practical.
- Keep public API changes explicit. Consider import compatibility, URL behavior, Django lifecycle, supported Python versions, and downstream applications.
- Do not broaden scope to unrelated refactors. Explain rejected alternatives when they materially affect the design.

## 3. Test behavior, not implementation details

- Add regression tests that fail before the fix and pass after it.
- Cover success, invalid input, boundary conditions, error behavior, and interactions with existing public APIs.
- Prefer deterministic tests. Avoid network calls, real credentials, wall-clock dependence, and nondeterministic LLM calls in the core test suite.
- Reuse `tests/` and `integration_test_project/`; do not create a parallel Django test project.
- Run the narrowest relevant tests first, then the appropriate unit and integration suites.
- For compatibility-sensitive changes, read the current `tox.ini` and validate the configured matrix using the repository's matrix-check script before interpreting matrix results.
- Distinguish PASS, FAIL, and NOT RUN. A missing interpreter or unavailable dependency is an environment failure, not a passing test.

## 4. Validate packaging and documentation

When package contents, metadata, dependencies, or build configuration change:

- Build both wheel and source distribution using the repository's documented build workflow.
- Validate metadata and inspect both archives.
- Confirm tests, website assets, local secrets, caches, and unrelated repository content are not accidentally shipped.
- Check the `py.typed` marker and public import paths when relevant.

When behavior changes:

- Update the relevant canonical docs and changelog according to repository policy.
- Verify examples against executable tests or a minimal integration scenario.
- Preserve documented limitations; never convert an unimplemented or partial capability into a product claim.

## 5. Review the final change

Review the full diff—not only the staged diff—for:

- behavioral regressions and backward compatibility;
- security, input validation, path handling, and unsafe dynamic execution;
- dependency and supply-chain impact;
- test coverage and test quality;
- documentation accuracy and contradictory claims;
- packaging inclusion/exclusion;
- CI trigger and matrix drift.

Report findings by severity and include file/line references, concrete impact, and reproduction evidence. Separate verified defects from hypotheses and optional improvements.

## 6. Finish safely

- Stage explicit paths only; follow the repository's commit and push authorization rules.
- Do not force-push, rewrite history, publish a release, or expose credentials.
- Report exact commands executed, exit statuses, skipped checks, and remaining risks.
- Never state that the work is complete while a required gate is failing or unverified.
