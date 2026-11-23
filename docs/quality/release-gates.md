# Quality and release gates

**Status:** Maintainer contract for changes targeting `main` and package releases.  
**Published baseline:** `django-api-versioning 1.3.0`.  
**Runtime dependencies added by these gates:** None.

This document defines the evidence required to claim that the package meets its release-quality targets. A configured workflow is not proof of a passing result: every result must identify the exact source commit and completed workflow run.

## 1. Quality targets

| Area | Required target | Acceptance rule |
|---|---:|---|
| Mutation testing | 100% in each of five domains | Every generated mutant is accounted for; all are killed. No survivors, skipped, suspicious, timed-out, or incomplete outcomes. |
| Line coverage | >=95% | Enforced independently. |
| Branch coverage | >=95% | Enforced independently. |
| Public API contract | Complete | Public imports, signatures, settings, errors, routing, reversal, and optional-dependency boundaries are tested. |
| Python/Django compatibility | Complete configured matrix | All 15 Python/Django tox combinations plus lint (16 tox environments) pass. |
| Security/adversarial | Active | CodeQL, Atheris, Schemathesis, and applicable property-based tests run through CI. |
| Backward compatibility | Protected | Routing, schema/representation, and runtime semantics are checked as distinct contracts. |
| Real consumer integration | Confirmed | The executable Django consumer project and its API requests/contracts pass. |
| Regression control | Required on every PR | The always-running PR gate evaluates every path-relevant workflow against the exact PR head. |
| Release reproducibility | Verified before publication | Wheel and sdist are built and validated; installed-wheel smoke tests and reproducibility checks pass. |

## 2. Mutation domains

The five domains are independently gated:

1. Decorators
2. Lifecycle
3. Negotiation
4. Registry
5. Routers

Each shard produces a machine-readable summary and detailed mutant report. The combined gate verifies that all expected domain reports exist, there are no duplicate or unexpected reports, every generated mutant has exactly one reconciled outcome, and each domain reaches 100%.

Only genuinely equivalent mutants may be excluded with an inline `# pragma: no mutate` marker. Every exclusion must be documented in [mutation-equivalences.md](mutation-equivalences.md), with the invariant that makes the mutation behaviorally equivalent. An exclusion is not a way to hide an untested behavior or lower the threshold.

## 3. Coverage measurement

Line and branch coverage are independent requirements. A high line score cannot compensate for a branch score below 95%.

The release gate uses coverage from the package tests and real-consumer integration tests. Mutation test contexts are collected separately to map source lines to the tests that exercise them. Do not report coverage from a unit-only run as the combined release result.

## 4. Public API and consumer contracts

The public API contract includes:

- Supported top-level imports and documented optional-module imports.
- Public function/class signatures, settings defaults, validation, and stable exception behavior.
- Route registration, inheritance, removal, precedence, namespace handling, and URL reversal.
- Django-only installation without importing DRF at package runtime.
- The documented boundary between `VersionedRouter` and `VersionedDefaultRouter`.

The executable consumer project is a separate Django application, not a mock of package internals. Its contract suite exercises real request dispatch, route inheritance/removal, serializer selection, versioned API roots, format suffixes, OpenAPI generation, deterministic schema snapshots, and semantic schema comparison with `oasdiff`.

A route matrix proves route-to-view selection; an OpenAPI diff checks documented request/response structure; request-level consumer tests check runtime behavior. None substitutes for the others.

## 5. Compatibility and security

The authoritative configured environment list is [tox.ini](../../tox.ini), and the workflow implementation is [compatibility.yml](../../.github/workflows/compatibility.yml). The matrix currently contains 15 Python/Django combinations plus the lint environment. A smoke subset is useful for fast feedback but is not a full-matrix release result.

Security and adversarial evidence is produced by:

- CodeQL for source analysis.
- Atheris for coverage-guided fuzzing of hostile negotiation inputs.
- Schemathesis for schema-derived positive and negative API requests.
- Hypothesis and focused regression tests for input, state, concurrency, lifecycle, and routing boundaries.

Backwards compatibility is reviewed across three independent dimensions:

- **Routing:** which URL exists and which implementation handles each version.
- **Representation/schema:** request/response fields, types, requiredness, media types, and documented errors.
- **Runtime semantics:** validation, authorization, side effects, persistence, and business invariants.

See [API compatibility boundaries](../design/api-compatibility-boundaries.md) and the [versioned OpenAPI contract](../design/versioned-openapi-contract.md).

## 6. PR and release workflow

Every PR to `main` must pass the always-running [PR gate](../../.github/workflows/pull-request-gate.yml) on its latest head SHA. Applicable child workflows must complete successfully; a skipped child is acceptable only when the path classifier establishes that its scope is unchanged.

A package release additionally requires:

1. A reviewed release PR with a user-visible changelog entry and accurate version-specific documentation.
2. The complete compatibility matrix on the exact candidate/merged commit.
3. Complete mutation and coverage evidence, plus public API and real-consumer contracts.
4. Applicable security/adversarial checks.
5. Validated wheel and sdist, metadata checks, distribution-content checks, and an isolated installed-wheel smoke test.
6. A reproducible-build check for the exact source and pinned build environment. CI runs [`scripts/check_reproducible_build.py`](../../scripts/check_reproducible_build.py) in both the package-artifact PR workflow and the tag-triggered publish workflow. It builds twice from clean Git archives with a fixed source epoch, normalizes only sdist archive metadata (timestamps, ownership, and member order), compares wheel/sdist SHA-256 digests, and copies the verified artifact set into the release output directory.
7. Explicit authorization for a concrete package version before version bump, tag creation, or publication.

The package release procedure is maintained in [the release skill](../../.agents/skills/release/references/release-procedure.md). Never infer a release result from a previous commit, from the configured matrix alone, or from a partial workflow-job listing.

## 7. Evidence records

Dated reports under [reports](../reports/) are immutable snapshots. They identify the exact commit and workflow runs, record observed results, and explicitly list anything not verified. A later passing run does not retroactively change an earlier report; create a new report for the new commit.
