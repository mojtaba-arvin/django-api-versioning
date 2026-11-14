# Engineering Roadmap

> Status: active
> Baseline branch: `main`
> Baseline commit: `8a22a8467d729daa572a751b3ff32fb0f0596038`
> Baseline reviewed: 2026-11-15
> Working branch: `engineering/product-evolution`

This roadmap is a living engineering plan for taking django-api-versioning from its current implementation to a dependable, well-documented, maintainable Django ecosystem package.

It is deliberately evidence-driven. A configured test is not a passing test; a documented capability is not proof of implementation; a source-level test count is not an execution result. Every completion claim must identify the evidence that supports it.

## Operating principles

1. Preserve existing public behavior unless a deliberate, documented compatibility decision says otherwise.
2. Reproduce suspected defects with a focused test before changing implementation.
3. Prefer the smallest coherent change; each commit should have one reviewable purpose.
4. Run the narrowest relevant test first, then the broader required suite.
5. Never claim tests, builds, package installation, publication, or deployment were performed unless their results were observed.
6. Treat Django and DRF documentation, supported Python versions, and packaging standards as primary references.
7. Add features only when a concrete user problem, coherent API design, and maintenance cost justify them.
8. Keep source, tests, public API, examples, documentation, changelog, and compatibility claims synchronized.
9. Do not rewrite history or force-push shared branches as part of routine work.
10. Reassess this roadmap after every phase and add newly discovered work rather than treating the initial plan as exhaustive.

## Verified repository baseline

The following facts were read from the repository at the baseline commit:

- Package version in `pyproject.toml`: 0.3.7.
- Minimum Python version: 3.10.
- Runtime dependency: Django >= 4.2.
- DRF is listed as a development dependency, not a runtime dependency.
- `tox.ini` declares 15 Python/Django test environments and a separate lint environment.
- Each tox test environment runs unit tests under `tests` and the integration project under `integration_test_project`.
- The current `.github/workflows/tests.yml` builds a Docker image and runs its default entrypoint. The entrypoint runs `pytest`; it does not invoke tox.
- The changelog records a v0.3.7 verification claim of 175 unit tests and 245 integration tests in each of 15 environments, plus lint.
- The repository's compatibility report records a historical tox run, but explicitly says raw per-environment logs are not retained.
- The current compatibility report metadata still identifies package version 0.3.6 and the pre-merge audit branch/revision.
- The canonical routing contract still identifies version 0.3.6 and an earlier audit-branch source revision.
- The most recent main commit at baseline is merge commit `8a22a8467d729daa572a751b3ff32fb0f0596038`, which merged PR #5.

These are repository observations, not independent confirmation that the historical test run or a published artifact can currently be reproduced.

## Phase 0 — Baseline integrity and audit recovery

### 0.1 Git and release provenance
- [ ] Record the current default branch head and clean working-branch ancestry.
- [ ] Inventory tags, GitHub Releases, PyPI versions, and their source commits.
- [ ] Verify whether v0.3.7 is published and compare its wheel/sdist metadata with the repository.
- [ ] Inspect PR #5, its complete diff, review discussion, and merge result.
- [ ] Identify release scripts and document the exact release preconditions.
- [ ] Check whether the working branch has diverged before every subsequent write.

### 0.2 Documentation provenance
- [ ] Reconcile stale metadata in `COMPATIBILITY_REPORT.md`.
- [ ] Reconcile stale metadata in `docs/reference/versioning-contract.md`.
- [ ] Recompute source-level test function counts using a reproducible method.
- [ ] Explain the difference between defined test functions and recorded pytest results.
- [ ] Separate historical test evidence from currently reproducible evidence.
- [ ] Review all version, compatibility, and feature claims against current source.

### 0.3 Repository inventory
- [ ] Inventory package modules, tests, integration project, docs, examples, workflows, and release tooling.
- [ ] Build a module dependency map and public-import map.
- [ ] Identify generated files, duplicated guidance, stale references, and undocumented behavior.
- [ ] Create a prioritized issue register with evidence, severity, impact, and proposed verification.

**Exit criteria:** repository state, release provenance, documentation provenance, and known unknowns are recorded without unsupported claims.

## Phase 1 — Reproducible quality gates and CI

- [ ] Establish reproducible local commands for unit, integration, lint, coverage, and full tox runs.
- [ ] Make CI execute the intended tox matrix, or explicitly document and justify a different matrix strategy.
- [ ] Ensure matrix failures cannot be hidden by partial success or shell error handling.
- [ ] Preserve per-environment Python, Django, DRF, pytest, and dependency-resolution information.
- [ ] Publish useful test and coverage artifacts where appropriate.
- [ ] Test the minimum supported Python/Django combination and every declared supported combination.
- [ ] Add a clean-environment build/install/import smoke test.
- [ ] Verify that tests run against the built distribution where practical, not only the checkout.
- [ ] Review workflow permissions, action pinning policy, caching, concurrency, and trigger coverage.
- [ ] Ensure documentation-only changes do not accidentally bypass required checks when they affect generated/API documentation contracts.

**Exit criteria:** CI provides trustworthy, inspectable evidence for the declared support matrix and package build.

## Phase 2 — Core architecture and behavioral contract

Audit each area against implementation, tests, and Django behavior before proposing changes:

- [ ] Public package exports and import side effects.
- [ ] Decorator argument validation and supported callable/view shapes.
- [ ] Registry identity, registration order, collision precedence, replacement, and reset behavior.
- [ ] Version segment expansion and explicit version sets/ranges.
- [ ] URL construction, path converters, namespaces, URLconf inclusion, and import lifecycle.
- [ ] Reverse resolution, duplicate names, kwargs/args, and failure behavior.
- [ ] Settings access, validation, override_settings behavior, and initialization timing.
- [ ] Middleware version extraction, lifecycle metadata, response headers, and sunset enforcement.
- [ ] Management command output and logical endpoint grouping.
- [ ] Thread/process safety assumptions and Django autoreload behavior.
- [ ] Exception taxonomy, diagnostics, and stable public contracts.

**Exit criteria:** each public behavior has a source-backed contract and appropriate regression coverage; unresolved design questions are explicitly recorded.

## Phase 3 — Advanced testing and defect prevention

- [ ] Boundary-value tests for all version ranges and invalid types.
- [ ] Property-based tests for version expansion and registry invariants where they provide meaningful coverage.
- [ ] Collision and registration-order permutation tests.
- [ ] Import-order and multiple-URLconf isolation tests.
- [ ] Reverse URL tests for names, namespaces, converters, args, kwargs, and ambiguity.
- [ ] Middleware tests for active, deprecated, and sunset versions, including timezone boundaries.
- [ ] Django-native FBV/CBV and supported DRF APIView/GenericAPIView/ViewSet integration coverage.
- [ ] Tests for optional DRF absence and supported dependency combinations.
- [ ] Regression tests for every confirmed defect.
- [ ] Mutation-testing trial on critical routing and lifecycle modules if practical.
- [ ] Define coverage expectations based on risk and behavior, not a vanity percentage.

**Exit criteria:** important invariants and failure modes are tested, and test results are reproducible.

## Phase 4 — API design and product capabilities

- [ ] Inventory every setting, helper, exception, decorator argument, middleware, and management command.
- [ ] Classify each as stable public API, internal implementation, experimental, deprecated, or unused.
- [ ] Investigate channel extraction helpers and channel settings: determine whether they are intentionally standalone utilities or incomplete routing features.
- [ ] Investigate the effective-version resolver setting and define its actual contract before considering activation.
- [ ] Evaluate diagnostics, route inspection, and developer tooling based on demonstrated user needs.
- [ ] Evaluate integration boundaries with DRF without duplicating its responsibilities.
- [ ] Write proposals and compatibility analysis before implementing potentially breaking features.
- [ ] Add migration and deprecation policies for any public API changes.

**Exit criteria:** every proposed feature has a problem statement, design, compatibility assessment, tests, and documentation plan.

## Phase 5 — Framework and dependency compatibility

- [ ] Verify the declared Django/Python matrix against official Django support tables.
- [ ] Verify DRF compatibility claims against official DRF support and dependency constraints.
- [ ] Decide whether the tested DRF version should be pinned, bounded, or tested across a matrix.
- [ ] Test with DRF absent from runtime installation.
- [ ] Review Django URL resolver and middleware behavior across supported versions.
- [ ] Review Python typing syntax and runtime compatibility at the minimum Python version.
- [ ] Document unsupported combinations and intentional exclusions precisely.

**Exit criteria:** compatibility claims match both official framework support and observed package test results.

## Phase 6 — Packaging, security, and release engineering

- [ ] Build wheel and sdist in a clean environment.
- [ ] Inspect package contents, metadata, license, typing marker, and included files.
- [ ] Install and import the built wheel in isolated environments.
- [ ] Run Twine checks and verify package metadata.
- [ ] Audit direct and development dependencies for necessity and version policy.
- [ ] Review GitHub Actions permissions, token exposure, and release workflow safety.
- [ ] Make release steps reproducible and ensure publication is gated on successful verification.
- [ ] Define versioning, changelog, tag, provenance, and rollback procedures.
- [ ] Do not publish to PyPI without explicit release authorization.

**Exit criteria:** an independently verifiable release candidate can be built and validated without publishing it.

## Phase 7 — Developer experience and examples

- [ ] Review installation and quick-start flow from a clean Django project.
- [ ] Validate every README and documentation code sample by execution where feasible.
- [ ] Add realistic examples for Django-native views and supported DRF patterns.
- [ ] Improve error messages with actionable context while preserving stable exception types.
- [ ] Review type hints, editor support, docstrings, and public API discoverability.
- [ ] Document URL import ordering, deployment/reload considerations, and troubleshooting.
- [ ] Add upgrade guides for meaningful releases.

**Exit criteria:** a developer can install, configure, integrate, diagnose, and upgrade using verified guidance.

## Phase 8 — Documentation architecture and technical content

- [ ] Establish one authoritative source for each behavioral contract.
- [ ] Remove contradictions among README, reference docs, compatibility report, examples, articles, and changelog.
- [ ] Separate normative API reference from explanatory guides and opinion/editorial articles.
- [ ] Add architecture and decision records for non-obvious design choices.
- [ ] Review HTTP semantics and relevant standards claims against primary sources.
- [ ] Add cross-links and version metadata consistently.
- [ ] Establish a documentation review checklist tied to code changes.

**Exit criteria:** documentation is accurate, navigable, internally consistent, and traceable to implementation.

## Phase 9 — Website and project presentation

- [ ] Audit the current project website and deployment source before redesign.
- [ ] Define information architecture and audience-specific journeys.
- [ ] Build a technically accurate landing page and documentation navigation.
- [ ] Present examples, architecture, compatibility, changelog, and contribution guidance.
- [ ] Review accessibility, responsive behavior, performance, metadata, and search indexing.
- [ ] Ensure website claims are generated from or checked against canonical project data.

**Exit criteria:** website content is accurate and the primary developer journeys work on mobile and desktop.

## Phase 10 — Long-term maintenance and ecosystem readiness

- [ ] Define support windows and compatibility update cadence.
- [ ] Define issue templates, contribution workflow, and review expectations.
- [ ] Establish a security reporting and response policy appropriate to project scale.
- [ ] Track upstream Django, DRF, and Python release changes.
- [ ] Maintain a public roadmap with explicit status and rationale.
- [ ] Periodically reassess architecture, dependency health, documentation drift, and user feedback.
- [ ] Evaluate future major-version opportunities only when supported by real requirements.

**Exit criteria:** the package has a sustainable maintenance process and a transparent evolution policy.

## Work log

Record each completed work unit with:
- Date and commit SHA.
- Problem or objective.
- Files and behavior affected.
- Tests/commands actually executed and their observed results.
- Documentation/changelog impact.
- Remaining risks and follow-up tasks.

Do not mark a phase complete merely because its checklist was drafted. Phase completion requires evidence for its exit criteria.
