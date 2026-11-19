---
name: package-audit
description: Audit the Django API versioning package for architecture, compatibility, security, tests, packaging, documentation, and release readiness. Use for broad technical audits, not routine implementation.
---

# Skill: Package Audit - django-api-versioning

Complete package evaluation procedure for assessing technical quality, compatibility, and production readiness.

## Overview

This skill provides a systematic framework for auditing the django-api-versioning package across multiple dimensions. It distinguishes between:
- Verified facts (observed in actual code/tests/output)
- Suspected problems (unverified claims)
- Implemented capabilities (working in code)
- Partial capabilities (partially working)
- Known limitations (documented constraints)
- Proposed improvements (ideas for enhancement)

## Audit Dimensions

## On-demand audit references

Read only the dimensions relevant to the task. These files contain the detailed checklists and technical review focus; this entry point stays small.

| Dimension | Reference |
| --- | --- |
| 1. Architecture Review | [architecture.md](references/architecture.md) |
| 2. Django and DRF Compatibility | [django-drf-compatibility.md](references/django-drf-compatibility.md) |
| 3. Dependency Review | [dependencies.md](references/dependencies.md) |
| 4. Backward Compatibility | [backward-compatibility.md](references/backward-compatibility.md) |
| 5. Security Review | [security-and-ci.md](references/security-and-ci.md) |
| 6. Test Quality | [test-quality.md](references/test-quality.md) |
| 7. Documentation Quality | [documentation.md](references/documentation.md) |
| 8. GitHub Discoverability | [github-discoverability.md](references/github-discoverability.md) |
| 9. PyPI Discoverability | [pypi-discoverability.md](references/pypi-discoverability.md) |
| 10. AI Search Discoverability | [ai-discoverability.md](references/ai-discoverability.md) |
| 11. External Adoption | [external-adoption.md](references/external-adoption.md) |
| 12. Release Readiness | [release-readiness.md](references/release-readiness.md) |

For a comprehensive audit, read all twelve references. For a focused review, load only the applicable reference(s), then follow the execution workflow and output contract below.

## Audit Execution Workflow

1. Define the audit scope and load only the applicable dimension references; use all twelve only for a comprehensive audit.
2. Record the immutable source commit and package version, then inspect implementation, callers, public APIs, and matching tests.
3. Verify documented claims against source and executable behavior. Run focused tests first; use the manual-testing skill when full compatibility evidence is required.
4. Classify each observation as verified, suspected, implemented, partial, a known limitation, or a proposed improvement.
5. Report actionable findings with exact locations, impact, evidence, and the smallest safe recommendation. Record executed commands, exit codes, and unverified areas.

## Output Format

Document audit findings in a clear, structured format. Populate all counts, versions, and coverage from the current source or a specific recorded test run; never reuse historical numbers as current results.

**VERIFIED FACTS**:
- [ ] Unit tests: `<count from the identified run>`; command and exit code recorded
- [ ] Integration tests: `<count from the identified run>`; command and exit code recorded
- [ ] Coverage: `<value from the identified run>`
- [ ] Configured tox matrix: `<environment list read from current tox.ini>`
- [ ] Actual environment results: `<PASS / FAIL / NOT-RUN per environment>`

**SUSPECTED ISSUES** (unverified):
- [ ] State the observation and the evidence still needed.

**IMPLEMENTED CAPABILITIES**:
- [ ] List only behavior verified in current source and tests.

**PARTIAL CAPABILITIES**:
- [ ] Version-channel parsing utility supports `path`, `header`, and `query` in `channels.py`; verify call sites before describing this as end-to-end request routing. In the current source tree, the utility is tested directly, but is not wired into the endpoint registry's request dispatch.
- [ ] `@endpoint` does not decorate a DRF ViewSet class directly because ViewSets require an action map. A configured callable such as `MyViewSet.as_view({"get": "list"})` can be registered for one route. Full version-aware route generation is implemented through the optional `VersionedRouter`, which delegates to DRF's `SimpleRouter`, registers generated patterns in the package registry, and provides `VersionedRouterVersioning` for `request.version` and namespace-aware reversal. `DefaultRouter` API-root and format-suffix parity are not supported.

**KNOWN LIMITATIONS**:
- Direct `@endpoint` decoration of ViewSet classes is not supported; use `VersionedRouter` for the package's supported DRF `SimpleRouter` integration.
- `API_VERSIONING_CHANNELS` and `extract_version()` do not currently provide end-to-end header/query-based routing through the package registry.
- Python versions below 3.10 are outside the declared package requirement.
- Explicit endpoint removal and endpoint-level lifecycle declarations are present on repository `main` but remain under `Unreleased`; verify the release tag and installed artifact before claiming they are available to PyPI consumers.

**RECOMMENDATIONS**:
- If header/query-based request routing is a product goal, trace and test the integration from channel extraction through request dispatch before claiming support.
- Keep ViewSet/router responsibilities explicit in documentation.
- Expand documentation only where it adds verified behavior or clarifies a real limitation.

## When to Use This Skill

- Before major releases
- When planning new features
- When investigating reported issues
- When assessing compatibility changes
- When community asks "is this production-ready?"
- During regular maintenance cycles
