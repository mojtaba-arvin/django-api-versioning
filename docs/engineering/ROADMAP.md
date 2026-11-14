# Project Engineering Roadmap

> **Project:** django-api-versioning  
> **Working branch:** `audit/comprehensive-package-review`  
> **Package baseline:** `0.3.7`  
> **Roadmap status:** Active; phases are evidence-gated and continuously refined.

This is the project-level roadmap. The more detailed website delivery gates remain in [implementation status](../website/implementation-status.md), and the workflow-specific policy remains in [CI strategy](../development/ci-strategy.md).

The goal is not to maximize commit count. The goal is to turn the package, its developer experience, technical content, evidence, and public project presence into a dependable product that experienced Django developers can evaluate and adopt with confidence.

## Engineering principles

1. **Source before claims.** Verify behavior in the current package implementation before documenting or promising it.
2. **Tests before fixes.** Reproduce suspected defects with focused regression coverage before changing behavior.
3. **Evidence has levels.** Distinguish source inspection, direct test coverage, an observed test execution, compatibility evidence, and production behavior.
4. **Compatibility is deliberate.** Do not silently change public behavior, accepted settings, imports, decorator signatures, exceptions, or URL semantics.
5. **No speculative features.** A feature needs a concrete developer problem, a written contract, a compatibility assessment, and a maintenance justification.
6. **Small coherent commits.** Each commit should have one reviewable purpose; no filler commits or arbitrary commit targets.
7. **Validate the distribution.** A passing checkout test is not a substitute for building and installing the wheel/sdist.
8. **Keep evidence reproducible.** Pin source revisions and record the exact commands and dependency versions actually used.
9. **Preserve canonical ownership.** `docs/articles/` is the editable article source; generated website mirrors and evidence must be regenerated, not hand-edited.
10. **Never imply background execution.** Work advances through explicit, verifiable sessions and commits.

## Verified baseline

The repository records these observed checkpoints:

| Area | Evidence | Qualification |
| --- | --- | --- |
| Package metadata | Version 0.3.7; Python >=3.10; Django >=4.2 | Read from `pyproject.toml` |
| Focused Python suites | 211 unit + 249 integration tests; 96% coverage | GitHub Actions run at source `9b09d66c931f6e99687664da7442ddf9198595cb` |
| Compatibility | 15 tox environments + lint passed | GitHub Actions run at the same source revision |
| Package artifacts | Wheel, sdist, Twine, and distribution-content checks passed | Run at source `14f19b3ccce511af04621597b944c2f9e61162b2` |
| Source-pinned evidence | 18 Segment Lab scenarios regenerated and checked | Run at source `01462339a958c268bb15de50955c664cca05f69c` |
| Website | Node tests, Astro checks, dependency audit, root and GitHub Pages builds passed | Latest recorded checkpoint `330a9553310ae4c9d44fb9787f607ac2ba0c114a` |
| Article corpus | 25 canonical Markdown articles | Full A–MM review remains open |
| Hosting | Static site builds exist | No actual deployment; browser/accessibility/performance gates remain open |

These are historical observed checkpoints, not proof that later commits have passed. The current working tree's latest changes must be validated separately.

## Phase 0 — Repository state, provenance, and governance

- [ ] Reconcile the active audit branch with the three commits by which `main` had advanced at the last branch comparison.
- [ ] Preserve all work already on `audit/comprehensive-package-review`; do not reset, force-push, or rebase without a reviewed migration plan.
- [ ] Keep one canonical work branch and avoid parallel PRs that duplicate its changes.
- [ ] Inventory all commits after the last merged checkpoint and classify package, tests, docs, website, CI, and release changes.
- [ ] Maintain a work log with commit SHA, objective, files, observed checks, and unresolved risks.
- [ ] Keep credentials, tokens, and private configuration out of source, logs, generated evidence, and commits.

**Exit criteria:** branch ancestry and outstanding work are understood, no existing work is discarded, and all project claims are traceable.

## Phase 1 — Package architecture and public contract

Audit the full package, not just the modules that currently look suspicious.

- [ ] Public exports, import side effects, and package initialization.
- [ ] Decorator signatures, validation, class/function support, and error taxonomy.
- [ ] Version-range expansion, explicit version lists, and integer/bool edge cases.
- [ ] Registry identity, precedence, collision behavior, registration order, and shared state.
- [ ] URL generation, converters, namespaces, root URLconf composition, and import lifecycle.
- [ ] Reverse helpers, duplicate route names, namespaces, args/kwargs, and ambiguity.
- [ ] Lifecycle settings, middleware ordering, timezone semantics, HTTP headers, and sunset behavior.
- [ ] Management commands, deterministic output, and migration safety.
- [ ] Typing, Python minimum-version syntax, and optional dependency boundaries.
- [ ] Thread/process safety, autoreload, test isolation, and multiple URLconf behavior.

For each public behavior, record:
- source location;
- direct test coverage;
- execution evidence and source revision;
- documented contract;
- unsupported or intentionally excluded behavior.

**Exit criteria:** every public contract has source and test references; every confirmed defect is fixed or explicitly accepted.

## Phase 2 — Reliability, regression depth, and test design

- [ ] Add boundary and malformed-input tests for public APIs and settings.
- [ ] Add property-based tests where they verify meaningful invariants such as version expansion and registry precedence.
- [ ] Test registration-order permutations, collisions, and repeated imports.
- [ ] Test Django URL resolution and reverse behavior with names, namespaces, converters, args, and kwargs.
- [ ] Test FBV, Django CBV, DRF APIView/GenericAPIView, and configured ViewSet callables.
- [ ] Test optional DRF absence from runtime installation.
- [ ] Add lifecycle tests for naive and offset-aware timestamps, exact expiry boundaries, malformed values, and middleware behavior.
- [ ] Add integration tests for real URLconf initialization and multiple endpoint modules.
- [ ] Evaluate mutation testing for critical routing and lifecycle logic.
- [ ] Define risk-based coverage expectations; do not optimize for a vanity percentage.

**Exit criteria:** important invariants and failure modes have direct regression tests, and tests execute in reproducible environments.

## Phase 3 — CI, compatibility, and supply-chain confidence

- [ ] Keep focused unit/integration tests separate from the full tox compatibility matrix.
- [ ] Verify that the declared matrix matches official Python/Django support policy.
- [ ] Retain inspectable logs and source SHAs for each compatibility checkpoint.
- [ ] Verify DRF's tested/resolved version policy and decide whether bounds or a matrix are needed.
- [ ] Keep lint, package artifact validation, website checks, and evidence generation scoped but connected to the files they validate.
- [ ] Ensure every relevant long-lived branch receives a deliberate final-SHA validation checkpoint.
- [ ] Review workflow permissions, third-party action pinning, token scope, concurrency, cancellation, and path filters.
- [ ] Test failure behavior: missing interpreter, dependency resolution, test failure, artifact failure, and generated-output drift.

**Exit criteria:** no release or merge decision relies on stale or unrelated green checks.

## Phase 4 — Packaging, installation, and release engineering

- [ ] Build wheel and sdist in clean environments.
- [ ] Validate metadata, package contents, typing marker, license, and README inclusion.
- [ ] Install the built wheel in isolated Python/Django environments and import the documented public API.
- [ ] Run Twine checks and package-content verification.
- [ ] Check dependency declarations for necessity, lower bounds, upper bounds, and optional extras.
- [ ] Verify that website, articles, integration projects, and development tooling do not leak into PyPI artifacts.
- [ ] Define reproducible version bump, changelog, tag, artifact, provenance, and rollback steps.
- [ ] Keep publication gated; do not publish to PyPI without explicit release authorization.

**Exit criteria:** an independently verifiable release candidate can be built, installed, and tested from immutable artifacts.

## Phase 5 — Full documentation and article corpus A–MM

Review articles 001–025 in order. A metadata pass is not a technical approval.

For each article:
1. Validate canonical front matter and article identity.
2. Identify every package-specific claim and map it to current source.
3. Map examples to direct tests; distinguish coverage from execution.
4. Verify Django/DRF/HTTP claims against primary documentation and standards.
5. Check imports, settings, URLconf initialization, version types, decorators, and expected routes.
6. Verify negative claims by searching the complete package source.
7. Check the exact ViewSet/router boundary and DRF request-version behavior.
8. Verify lifecycle, deprecation, sunset, reverse, inheritance, and cache claims where relevant.
9. Check package-first positioning, author disclosure, PyPI/repository links, CTA placement, and reader intent.
10. Review article overlap, internal links, canonical slugs, and cross-article consistency.
11. Correct the complete Markdown when needed, then repeat the review.

**Review disposition must distinguish:**
- blocking technical/editorial violations;
- non-blocking improvements;
- justified omissions;
- claims that are source-inspected but not directly tested;
- examples not yet executed end-to-end.

**Exit criteria:** all 25 articles pass the complete editorial and technical gate, not merely metadata checks.

## Phase 6 — Developer experience and product usability

- [ ] Validate installation and first-use flow in a clean Django project.
- [ ] Make the smallest useful example runnable end-to-end.
- [ ] Ensure every README/reference example matches the current package API.
- [ ] Improve actionable diagnostics without changing stable exception contracts unnecessarily.
- [ ] Review type hints, editor completion, docstrings, and public API discoverability.
- [ ] Document import order, URLconf lifecycle, autoreload, testing, troubleshooting, and migration paths.
- [ ] Evaluate management-command ergonomics and route inspection output.
- [ ] Add an upgrade guide for each release with meaningful behavior/API changes.
- [ ] Evaluate whether the package needs a formal deprecation policy and support window.

**Exit criteria:** a senior Django developer can install, integrate, debug, test, and upgrade without relying on undocumented assumptions.

## Phase 7 — Website, evidence, accessibility, and discovery

- [ ] Keep canonical articles and generated evidence source-pinned.
- [ ] Ensure metadata validation runs before generated mirrors are replaced.
- [ ] Keep search indexes, article IDs, slugs, and canonical links deterministic.
- [ ] Verify browser behavior at root and GitHub Pages base paths.
- [ ] Test keyboard navigation, focus visibility, semantic landmarks, search, code copy, anchors, theme controls, reduced motion, and no-JavaScript fallbacks.
- [ ] Run automated accessibility checks and manual WCAG 2.2 AA review.
- [ ] Measure performance and layout stability; tie claims to recorded measurements.
- [ ] Test static output with a generic server, nested routes, 404s, assets, traversal, and base-path behavior.
- [ ] Deploy only after article, browser, accessibility, performance, and artifact gates are accepted.

**Exit criteria:** the site is accurate, accessible, responsive, fast by measured criteria, and deployed from a verified immutable artifact.

## Phase 8 — Feature discovery and API evolution

This phase is deliberately proposal-first. Do not add features merely because they are technically possible.

Candidate investigations:
- [ ] Clarify whether `API_VERSIONING_CHANNELS` and `API_EFFECTIVE_VERSION_RESOLVER` should remain validated-but-unused extension points, be deprecated, or gain a separately designed runtime contract.
- [ ] Evaluate route inspection/diagnostic APIs for real developer workflows.
- [ ] Evaluate safer registration introspection and duplicate-name diagnostics.
- [ ] Evaluate explicit route metadata and lifecycle inspection tooling.
- [ ] Evaluate typed decorator overloads and static-analysis ergonomics.
- [ ] Evaluate async view compatibility and Django resolver behavior where relevant.
- [ ] Evaluate OpenAPI integration only if it can preserve clear boundaries and avoid implying schema/version behavior the package does not own.
- [ ] Write a short design decision record and compatibility assessment before implementation.

Every feature proposal must state: user problem, current workaround, API surface, failure modes, compatibility impact, test plan, documentation plan, and maintenance cost.

**Exit criteria:** only evidence-backed features are accepted, and each accepted feature has a tested public contract.

## Phase 9 — Long-term maintenance and ecosystem

- [ ] Define support windows and update cadence for Python, Django, and DRF.
- [ ] Track upstream framework releases and deprecations.
- [ ] Establish issue templates, contribution guidance, review standards, and security reporting.
- [ ] Keep dependencies and GitHub Actions current without introducing unreviewed supply-chain risk.
- [ ] Maintain release notes, migration guidance, and a public roadmap.
- [ ] Reassess architecture and feature priorities using actual user feedback and issue patterns.
- [ ] Periodically rerun compatibility, package, documentation, and website audits.

**Exit criteria:** the package can evolve without relying on one large audit or one-time release effort.

## Current execution queue

1. The new article metadata gate is validated by website CI at source `ee71279c929bd5e4d8765e67ed3ed6238d05bb88`: 31 Node tests passed, all 25 canonical articles synchronized, Astro check was clean, and both static builds passed. Continue monitoring the source-evidence workflow's concurrency-safe commit step.
2. Continue the A–MM review in article order; articles 024 and 025 have received targeted corrections, and article 025's configured ViewSet pattern now has request-level integration tests. Neither article is fully approved yet.
3. Audit the remaining website article-sync and navigation behavior, then complete browser/accessibility/performance verification.
4. Continue the package source audit with the remaining public APIs and edge cases, adding regression tests only for confirmed gaps.
5. Re-run focused Python tests, the compatibility matrix, and artifact validation at a final immutable source SHA before any release decision.

## Work log format

Every meaningful milestone must record:

- Date and commit SHA.
- Scope and reason for the change.
- Confirmed finding and evidence.
- Files and public behavior affected.
- Tests/commands actually executed and their results.
- CI run URL and exact source SHA, if available.
- Remaining risks and the next concrete task.

Do not mark a phase complete because its checklist was written. Phase completion requires its exit criteria to be demonstrated.
