# Repository evolution audit

**Repository:** https://github.com/mojtaba-arvin/django-api-versioning  
**Reviewed branch and baseline:** `main` at `96b24a13eab7e7c45ffbc4f8d21ae917f5df6fb1`  
**Review date:** 2026-11-16  
**Commit history:** 651 commits reachable from `main`, from the initial commit `e67f57750f2269dfb45403371c875124b111b48d` (2025-02-21) through the baseline above.

## Scope and method

The review enumerated all 651 commits reachable from the current `main` history, grouped the full commit metadata by chronology and development phase, and inspected representative implementation, test, packaging, CI, release, and governance diffs.

The existing [418-commit historical audit](agent-history-audit-418.md) was also reviewed and cross-checked. It covers the bounded interval 2026-11-14 17:54:35 UTC through 2026-11-15 22:06:23 UTC, ending at `6060db59834d77beca8392fb9464b0ae3bd1c5ce`. It is not a substitute for the complete 651-commit chronology.

This is a history-level forensic review, not a claim that every changed line in all 651 commit diffs was manually audited. Commit authorship metadata is not reliable evidence that a human or a particular AI agent authored a change; automated commits previously used the maintainer identity and were later corrected to use `github-actions[bot]`.

## Executive assessment

The project has achieved its central product goal: declarative, path-based registration of Django API endpoints across API versions, including forward segment inheritance and explicit version sets. The package is now published as v0.3.8, has a meaningful Python/Django test matrix, verifies built distributions, and uses provenance-backed PyPI Trusted Publishing.

The repository has also evolved beyond package source into a documentation and evidence system: 25 canonical Markdown articles, an 18-scenario source-pinned Segment Lab, a static Astro website, and reusable engineering/agent workflows.

The remaining gaps are mostly explicit product boundaries and delivery gates, not evidence of a broken core package: header/query version channels are not wired into route dispatch; the package does not automatically set DRF's `request.version`; direct ViewSet-class registration and automatic router generation are not supported; semantic API response compatibility remains an application responsibility; and the website has not passed browser-level acceptance or been deployed.

## Development phases

| Period | Goal and work | Assessment |
| --- | --- | --- |
| 2025-02-21 to 2025-02-22 — v0.1.0 baseline to v0.1.4 | Establish the package, decorator-based URL registration, registry, settings, tests, class-based view support, and first PyPI releases. | **Achieved for the original narrow product.** The initial package targeted an older Python/Django range and had a much smaller test surface. |
| 2026-10-28 — v0.2.0 | Add opt-in forward endpoint inheritance, preserve decorated class-based views as classes, add the PEP 561 marker, and modernize the supported runtime baseline. | **Achieved, with a breaking compatibility change.** Python 3.10+ and a newer Django baseline replaced the original legacy support. |
| 2026-10-31 — v0.3.0 | Replace the earlier forward/backward flag model with segment-based registration: `version=N` for a continuous segment and `versions=[...]` for explicit versions. | **Achieved.** This is the defining API model in the current package. The migration from the old flags is a breaking change and is documented. |
| 2026-11-08 — initial comprehensive audit | Inspect package architecture, settings, decorators, URL reversal, tests, dependencies, and documentation; establish an integration-test environment. | **Mostly achieved after correcting early audit mistakes.** The first static review misdiagnosed a regex issue in `api_reverse`; the attempted `re.escape()` change was reverted after executable testing showed that `re.sub()` with a callable replacement does not interpret the returned value as a replacement template. |
| 2026-11-08 to 2026-11-11 — v0.3.1–v0.3.4 | Expand Django integration coverage, correct package classifiers, detect versions from static URL paths in lifecycle middleware, and fix stale settings reads under `override_settings`. | **Achieved in the released implementation.** Later releases expanded the test evidence and clarified the support matrix. |
| 2026-11-12 to 2026-11-14 — v0.3.5–v0.3.7 | Improve README and canonical contract accuracy, refine DRF boundaries, fix logical endpoint matrix reporting and class-based callback labels, and strengthen `api_reverse` converter behavior. | **Achieved for the documented scope.** The package's public behavior and its limitations became more explicit. |
| 2026-11-14 to 2026-11-15 — v0.3.8 | Harden lifecycle/configuration validation, make endpoint migration syntax-aware and preview-first, verify installed distributions, build source-pinned evidence, create the documentation site, and isolate PyPI publication. | **Achieved for the v0.3.8 release.** The release matrix and publication workflow completed successfully. |
| 2026-11-16 — repository governance | Make `main` the only long-lived branch; require PR-based squash integration and an always-running PR Gate; pin Actions; add CodeQL, dependency review, policy tests, and release-tag protection. | **Implemented and configured.** GitHub reports active `Protect main` and `Protect release tags` rulesets. The branch list contains only `main`. The current publish workflow also verifies annotated release tags and their ancestry on `main`; this safeguard was added after v0.3.8 and is not retroactively claimed for that release. The main ruleset requires a pull request and the PR Gate but does not require a separate human approval (the configured approval count is zero). |

## Product goals: achieved and remaining

### Achieved

1. **Declarative endpoint registration.** The `@endpoint` decorator registers versioned and unversioned URL patterns.
2. **Forward segment inheritance.** A declaration at version N serves N through `API_MAX_VERSION` until a later declaration takes over.
3. **Explicit version sets and bounded ranges.** `versions=[...]` and `ver_range()` cover non-contiguous and bounded registration.
4. **Route precedence and collision handling.** The registry resolves competing declarations according to source-version precedence and registration order.
5. **Version-aware reverse lookup.** `api_reverse()` supports registered route names, validates integer versions and named parameters, uses Django path converters' `to_url()` methods, and checks the generated route against the compiled pattern.
6. **Lifecycle behavior.** `LifecycleMiddleware` handles configured deprecation and sunset behavior, including path-based version extraction when DRF's `request.version` is absent.
7. **Route inspection and regression utilities.** `check_versions` and `assert_version_matrix()` provide visibility and snapshot-based protection for registered routes.
8. **Safer legacy migration.** `migrate_endpoints` uses AST/tokenizer-aware inspection and preview-first behavior; source writes require explicit `--write`.
9. **Package release integrity.** The wheel and sdist are built, checked, inspected for distribution boundaries, and the installed wheel is smoke-tested outside the source checkout.
10. **v0.3.8 publication.** GitHub Actions published the verified artifacts through Trusted Publishing, and PyPI exposes provenance for both release files.
11. **Technical documentation and evidence.** The repository has 25 canonical Markdown articles and an 18-scenario Segment Lab whose generated data is pinned to a source commit and hashed.
12. **Engineering governance.** `main` is the only long-lived branch; the active main ruleset requires PR Gate, pull-request integration, linear history, and squash-only merges. The active release-tag ruleset restricts creation, update, and deletion of `v*` tags to the administrator role.

### Partial or not achieved

| Goal | Current reality | What would count as completion |
| --- | --- | --- |
| Header/query-based routing | `channels.py` has extraction helpers and settings validation, but the registry does not use these channels to select routes. | Define request-time dispatch semantics, wire the resolver into routing, and add end-to-end Django/DRF tests before advertising the feature. |
| Effective-version resolver | `API_EFFECTIVE_VERSION_RESOLVER` is validated but does not select registered routes. | Either implement and test its end-to-end behavior or keep it explicitly documented as reserved/unused configuration. |
| DRF request version | The package selects a view through URL registration but does not automatically populate `request.version`. | Keep this as an explicit application/DRF integration boundary, or implement a separately designed adapter with integration tests. |
| Direct ViewSet/router integration | A ViewSet class requires an action map; a configured `as_view({...})` callable can be registered. Router-generated route creation remains application-owned. | Decide whether automatic router integration is a product requirement. If yes, design and test it separately; do not imply that current support already exists. |
| Semantic backward compatibility | Route matrices can be inspected, but serializer, permission, response-schema, database, and business behavior compatibility are not enforced by the package. | Keep this as an application responsibility and explain it clearly; route snapshots alone are not sufficient. |
| Full lifecycle standards conformance | The middleware emits the legacy `Deprecation: true` value, not the date-valued Structured Field required by RFC 9745. | Decide whether standards-compliant date-valued Deprecation support belongs in a future release and add standards-focused tests. |
| Website delivery | Static builds and project-base-path checks passed, but browser-level accessibility/performance acceptance and external-host smoke testing remain open. The website is not deployed. | Complete keyboard, mobile, reduced-motion, no-JavaScript, WCAG 2.2 AA, layout-stability and performance checks; then obtain explicit approval before production deployment. |
| Cross-platform/database evidence | The compatibility matrix runs on Ubuntu and the test project uses SQLite. | Add other operating systems or database engines only if they become supported product claims or a real user requirement. |
| External adoption | Repository and PyPI discoverability work exists, but the commit history does not establish third-party production adoption or independent endorsements. | Collect real usage, issue, download, and contributor evidence; do not infer adoption from documentation volume or downloads alone. |
| Agent benchmark results | Evaluation scenarios define acceptance criteria, but no controlled comparative accuracy or token-cost measurements are recorded. | Run reproducible baseline/candidate evaluations with identical tasks, models, versions, and exposed usage metrics. |

## Historical mistakes and avoidable work

### Correctly reversed technical mistake

The initial audit incorrectly classified the `re.sub()` callback replacement in `api_reverse` as regex injection. An attempted `re.escape()` fix was reverted after integration testing established the actual Python behavior. The correction was right; the process lesson is to verify language/runtime semantics before changing working code based on a static hypothesis.

### Incomplete early release claims

An early handoff described the package as production-ready while its own record showed an integration-test setup failure (10/11 in one recorded run), a small compatibility sample, and no full platform matrix. Later releases added a much stronger integration suite and a 15-environment matrix. The later evidence is the correct basis for the v0.3.8 claims; the early certification should not be reused.

### Process churn found in the 418-commit interval

The historical 418-commit audit recorded:

- 135 `docs:` commits, 67 `ci:`, 53 `fix:`, 50 `test:`, 38 `style:`, and 31 generated-evidence commits;
- three duplicate tracking documents touched 32 times in total before all three were removed;
- repeated per-file formatting commits, including nine formatter commits in roughly 20 seconds;
- repeated generated-evidence commits, including timestamp-only churn;
- related workflow-trigger changes split across multiple commits;
- automated evidence/lockfile commits attributed to the maintainer rather than `github-actions[bot]`.

The subsequent corrections were appropriate: remove duplicate trackers, batch related edits and formatting, preserve evidence timestamps when payloads are unchanged, use bot identity for automated commits, and test evidence-generation idempotency.

A post-merge review of the PR path classifier found that it did not fully mirror the workflows' own push path filters. For example, `requirements-dev.txt` triggered package-artifact verification on `main` but was classified as not requiring that check on a PR. The same drift affected several workflow-definition and package-support paths. The classifier now maps those inputs to their matching checks, and regression tests cover the workflow files and support inputs.

### Post-release dependency automation failure

The 2026-11-16 Dependabot security-update run for `filelock` failed before creating an update because `requirements-dev.txt` contained adjacent `djangorestframework` and `tomli` requirements on one line. This was a malformed requirements entry, not a `filelock` vulnerability or a package-runtime failure. The requirements were separated, and the Agent tooling workflow now parses/resolves the maintainer requirements file on relevant pull requests and pushes. The path classifier has a regression test ensuring changes to this file invoke that validation.

That syntax correction exposed a separate, actionable development-tooling advisory set. Dependabot's Python 3.10.22 resolver could select only `filelock==4.1.0`, while the first fixed release is 4.2.1 and requires Python 3.11+. The vulnerable range includes multiple reviewed advisories, including [GHSA-crv4-6mhj-j5jh / CVE-2026-112914](https://github.com/advisories/GHSA-crv4-6mhj-j5jh) and [GHSA-2g95-wg33-c5x2 / CVE-2026-112906](https://github.com/advisories/GHSA-2g95-wg33-c5x2); both are fixed from filelock 4.2.1 onward. The PyPI metadata for [filelock 4.2.10](https://pypi.org/project/filelock/4.2.10/) declares Python >=3.11.

`filelock` is not a package runtime dependency; it was pulled into the maintainer-only development toolchain through `pre-commit` → `virtualenv`. The remediation keeps the package's Python 3.10 support intact while scoping the pre-commit CLI to Python 3.11+: `requirements-dev.txt` and the `dev` extra now require `pre-commit>=4.7.0` only when `python_version >= "3.11"`. Python 3.10 maintainers can run pre-commit from a separate Python 3.11+ environment. The lockfile is regenerated by the pinned uv version and the compatibility workflow checks it with `uv lock --check`. This removes the unsupported vulnerable filelock 4.1.0 resolution rather than suppressing advisories or forcing an incompatible package version. The Python 3.10 package test matrix remains unchanged.

### Historical credential-handling incident

The initial audit workspace recorded that a GitHub credential was exposed in command/error output and requested revocation. The repository history does not establish whether that credential was revoked. The value is not reproduced here. If revocation was not already completed, treat that historical credential as compromised and verify its status in GitHub.

## Current release and verification evidence

- Package version: **0.3.8**.
- Release source commit: `a372e2faa3e915d31083f70cb1b6c7e56fdc0372`.
- Release workflow: [#43772378437](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43772378437).
- All 19 release workflow jobs succeeded, including 15 Python/Django environments, lint, matrix validation, artifact verification, and PyPI publication.
- Every test environment reported 247 unit tests, 260 integration tests, and 96% package-source coverage.
- PyPI: [v0.3.8 and its provenance](https://pypi.org/project/django-api-versioning/0.3.8/).
- Website static verification: [run #69](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43761608641); deployment and browser-level acceptance remain open.
- GitHub rulesets: [Protect main](https://github.com/mojtaba-arvin/django-api-versioning/rules/26933420) and [Protect release tags](https://github.com/mojtaba-arvin/django-api-versioning/rules/27356730).

## Recommended next plan

The core package does not need an immediate feature expansion or a new release merely to make the repository look more active. Prioritize evidence and unresolved delivery gates.

### P0 — Keep the repository's evidence current

- Keep `COMPATIBILITY_REPORT.md` tied to the current package version, exact source commit, and inspected workflow run.
- Keep the canonical routing contract pinned to the release source it describes.
- Do not reuse test counts from older releases or infer a pass from a configured tox environment.
- Track the `filelock` Python 3.10 development-tooling advisory separately from package runtime dependencies; do not suppress it or force an incompatible upgrade without reviewing the affected advisories and platform/interpreter scope.

### P1 — Complete or explicitly defer website delivery

- Finish browser-level accessibility and responsive checks.
- Verify reduced motion, keyboard navigation, focus visibility, no-JavaScript fallback, layout stability, and performance.
- Run the external static-host smoke test.
- Deploy only after those gates pass and the maintainer explicitly authorizes production publication.

### P2 — Make deliberate product-scope decisions

- Decide whether header/query channels and the effective-version resolver are future product features or reserved configuration. Until implemented end-to-end, keep them clearly marked as non-routing helpers/configuration.
- Keep the ViewSet/router boundary explicit unless automatic integration is justified by a concrete use case.
- Preserve the distinction between route compatibility and semantic API contract compatibility.
- If RFC 9745 conformance is required, design the lifecycle header change as a separately tested compatibility change.

### P3 — Measure adoption and agent effectiveness only when useful

- Track actual PyPI and repository adoption evidence without treating download counts as proof of production usage.
- Run the agent evaluation scenarios under controlled, repeatable conditions before making accuracy or token-efficiency claims.
- Avoid adding external services, model SDKs, or runtime dependencies without a concrete need.

## Stop conditions

Do not create a new package release, publish a website, broaden supported platform claims, or implement a breaking routing/API change solely to close an item in this audit. Each requires a separate scope decision, tests, and—where relevant—explicit release or deployment authorization.
