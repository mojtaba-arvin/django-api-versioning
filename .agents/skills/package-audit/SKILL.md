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

1. **Initial Setup**
   - Clone repository
   - Set up development environment
   - Install all dependencies

2. **Documentation Review** (1-2 hours)
   - Read README, CHANGELOG, and documentation
   - Identify claims and features
   - Note any inconsistencies

3. **Code Review** (2-4 hours)
   - Read all core modules
   - Understand architecture
   - Identify issues or concerns
   - Review security-sensitive code

4. **Test Execution** (1-2 hours)
   - Run unit tests
   - Run integration tests
   - Measure coverage
   - Test compatibility matrix

5. **Verification** (1 hour)
   - Verify all findings against source
   - Cross-reference documentation and code
   - Identify verified facts vs suspected issues

6. **Report Generation** (1 hour)
   - Document all findings
   - Create recommendations
   - Prepare release readiness assessment

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
- [ ] DRF ViewSet classes cannot be registered directly without an action map; a specifically configured callable such as `MyViewSet.as_view({"get": "list"})` can be registered, while router-style route generation remains the application's responsibility.

**KNOWN LIMITATIONS**:
- Direct ViewSet class decoration is not supported as a substitute for DRF router/action configuration.
- `API_VERSIONING_CHANNELS` and `extract_version()` do not currently provide end-to-end header/query-based routing through the package registry.
- Python versions below 3.10 are outside the declared package requirement.

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
