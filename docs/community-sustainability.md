# Community adoption and maintenance plan

**Status:** Practical plan; adoption and succession are not yet established facts.  
**Last reviewed:** 2026-11-28

This plan turns the invitation in [Issue #151](https://github.com/mojtaba-arvin/django-api-versioning/issues/151) into bounded, verifiable work for independent Django and Django REST Framework users. It supplements, but does not replace, the technical contracts in the routing and negotiation references or the ownership rules in [GOVERNANCE.md](../GOVERNANCE.md).

## 1. Current position and honest reporting

The project has one primary maintainer. No second project owner or named successor is designated, and there is no guaranteed response or security-remediation SLA. A contributor invitation, passing repository CI, an example application, or a GitHub star is not evidence of independent production adoption or external review.

Report community progress using these distinct states:

| State | Evidence required | What it does not prove |
| --- | --- | --- |
| Repository example | Example code and its CI pass | Independent use |
| Reproducible external evaluation | A person outside the maintainer team supplies a minimal reproducer, environment versions, commands, and results | Production deployment |
| Independent review | A reviewer outside the maintainer team records specific findings against a commit or release | Endorsement or ongoing maintenance |
| Confirmed adoption | A downstream project maintainer voluntarily identifies a project and release/commit, describes the integration, and permits public attribution | Broad popularity or long-term commitment |
| Ongoing maintenance participation | Repeated, substantive triage/review/implementation across time | Authority to release or administer accounts |
| Successor commitment | Explicit, voluntary agreement on responsibilities and a completed access/release handover | Something that can be inferred from contributions |

When evidence is private or attribution is not authorized, publish only an anonymized aggregate with permission. Otherwise state **not yet evidenced**. Never invent adopters, reviewers, endorsements, response-time guarantees, or successor names.

## 2. Adoption work: prove the integration in a real project

The existing `integration_test_project/` is the package's canonical Django integration/evidence project. Extend it for package regressions; do not create a second in-repository integration project. The existing `examples/openapi_contract/` is the executable DRF/OpenAPI consumer example. It is a reference implementation, not an independent adopter.

Invite external evaluators to use a small branch or disposable test deployment in their own application. Ask them to report the exact package version or source SHA, Python/Django/DRF versions, database/cache/proxy context where relevant, configuration, commands, expected and actual behavior, and sanitized logs. A minimal failing test is more useful than a general statement that something did not work.

### Integration checklist

- [ ] **Reproducibility:** pin the package and framework versions; provide a minimal settings module, URLconf, views/ViewSets, and exact run commands. Record whether the test used a released wheel or editable source.
- [ ] **Registration and resolver:** import endpoint declaration modules before including generated URL patterns; verify actual Django callback selection, route inheritance/removal, namespacing, `reverse()`, `reverse_action()`, and 404 behavior for a valid version with no route.
- [ ] **Middleware ordering:** for non-path transports, put `VersionNegotiationMiddleware` before middleware that depends on `request.path_info`, including `CommonMiddleware` and `LifecycleMiddleware`. Test the effective order in the consuming project's real `MIDDLEWARE` setting, not only an isolated middleware unit test.
- [ ] **Transport behavior:** exercise path, header, query, and hostname as separate deployment configurations; the package supports one `API_VERSIONING_SCHEME` per deployment, not a fallback chain. Test missing, malformed, repeated, conflicting, unsupported, defaulted, and valid-but-unregistered versions.
- [ ] **Cache correctness:** for header negotiation, verify `Vary: Accept-Version, Accept` survives the complete middleware/proxy path and both fields participate in shared-cache keys. For query negotiation, include the configured version parameter in cache keys. For hostname negotiation, partition cache keys by the validated host. Test that responses for two versions cannot cross-contaminate.
- [ ] **Trusted host boundary:** test exact `API_VERSIONING_HOSTS` mappings with Django `ALLOWED_HOSTS`; unknown hosts must not select a version. Wildcards, arbitrary subdomains, and client-controlled tenant headers are not version maps. If behind a reverse proxy, document and test the trusted forwarded-host configuration.
- [ ] **DRF adapter:** test `VersionedRouter` and `VersionedRouterVersioning` with real ViewSets, custom actions, route inheritance/removal, `request.version`, reverse actions, and hyperlinked serializers. Confirm Django-only projects can install/use the package without DRF.
- [ ] **Lifecycle:** test deprecation and sunset headers for the effective version after negotiation, including cache behavior and the actual response path.
- [ ] **OpenAPI:** generate a schema for each concrete version in a fresh process, validate it, compare it with a reviewed version-specific snapshot, and run a semantic breaking-change check where appropriate. Keep route-matrix, schema, and request-level semantic tests separate.
- [ ] **Application semantics:** use real requests to check permissions, validation, error bodies, persistence, side effects, and business invariants. A route matrix or schema diff cannot prove these.

The canonical details and status codes are in [request version negotiation](design/request-version-negotiation.md), [DRF router design](design/versioned-drf-router.md), [OpenAPI contract integration](design/versioned-openapi-contract.md), and [API compatibility boundaries](design/api-compatibility-boundaries.md).

### Consumer-owned adapter pattern

Keep package imports in one consumer-owned module, such as `project/api_versioning.py`. Expose a stable `get_urlpatterns()` function from that module and make the root URLconf depend only on it. Business views should not import package internals. This keeps replacement practical: a consumer can replace the adapter with ordinary Django `path()` declarations or DRF routers without rewriting business views or the root URLconf.

Start from [examples/openapi_contract/](../examples/openapi_contract/). Its `contract_app/versioning.py` is the concrete adapter example. Preserve the consumer's own chosen route and schema contracts during replacement; do not imply that a replacement must reproduce package-specific lifecycle or inheritance behavior.

### Consumer OpenAPI snapshot workflow

1. Generate one schema per stable API version using the consumer's schema generator.
2. Review warnings and validate the generated document.
3. Compare only against that version's committed baseline.
4. Keep pull-request generation separate from baseline updates; CI must not silently rewrite released snapshots.
5. Use exact snapshots for intentional contract locking and a semantic diff such as `oasdiff breaking` when additive changes should be allowed.
6. Keep request-level tests for permissions, validation, error responses, persistence, and business semantics.

Use `assert_version_matrix(..., strict=True)` for route selection and `assert_schema_snapshot(..., strict=True)` for exact schema checks. Refresh snapshots only in a deliberate, reviewed change. Neither helper establishes application-level semantic compatibility.

## 3. Contribution path: small, reviewable, useful

Contributors do not need repository write access. Work from a fork and submit a focused pull request against `main`.

### Good first contributions

1. Reproduce one documented integration scenario in a real project and report versions, commands, and observed results.
2. Improve an example or correct a documentation step with a verified reproduction.
3. Add a regression test for middleware ordering, resolver behavior, cache variation, or trusted-host validation.
4. Extend DRF adapter coverage for a concrete ViewSet, custom action, reverse, or serializer case.
5. Add or improve a consumer OpenAPI snapshot workflow without weakening the existing contract gates.
6. Review a focused PR against the public routing contract and report actionable findings.
7. Triage an issue by confirming whether it reproduces on a supported dependency combination.

Avoid broad refactors, speculative public APIs, duplicate integration projects, generated website edits, and changes that weaken coverage, mutation, compatibility, security, or release requirements.

### Before opening a pull request

From a clean clone, use Python 3.12 for the default development path:

```bash
python -m pip install -e ".[dev]"
make test-unit
make test-integration
tox run -e lint
```

For changes affecting framework behavior, run the focused tests and relevant integration tests. The configured compatibility matrix in `tox.ini` is authoritative; a local default test run does not prove that every Python/Django/DRF combination passes. The required GitHub `PR gate` is the merge authority.

Follow [CONTRIBUTING.md](../CONTRIBUTING.md) for branch creation, Conventional Commit subjects, PR expectations, security reporting, and cleanup. Follow [AGENTS.md](../AGENTS.md) for evidence and repository invariants. Never include secrets or production customer data in a reproducer.

### Minimum useful issue report

Include:

- Package version or full source commit SHA.
- Python, Django, DRF, and relevant schema/cache/proxy versions.
- Negotiation scheme and sanitized relevant settings.
- Middleware order and URLconf/adapter shape.
- Exact request (method, path, headers, query) with secrets removed.
- Expected result, actual status/body/headers, and reproducible commands.
- Whether the issue reproduces against the latest release and current `main`.

Use GitHub's private vulnerability reporting flow for security issues; do not post exploit details publicly.

## 4. Staged contributor-to-maintainer path

This is a pathway, not a promise of promotion or a recruitment quota. Progress depends on mutual interest, demonstrated judgment, availability, and explicit agreement.

| Stage | Typical evidence | Appropriate access |
| --- | --- | --- |
| Contributor | Reproducible issue, documentation/test fix, or focused PR | Fork; no repository write access |
| Regular reviewer | Repeated constructive reviews; accurate understanding of routing, compatibility, and security contracts | Requested review; no privileged account access required |
| Project maintainer | Sustained triage/review/implementation; can diagnose regressions and operate the PR gate | Least-privileged repository role needed for agreed duties |
| Release maintainer | Completes a supervised release-readiness exercise and can verify exact-commit evidence, artifacts, and interrupted-release recovery | PyPI Maintainer upload role; no PyPI Owner by default |
| Project owner / successor | Explicit handover agreement; verified repository administration, Trusted Publishing, release, and recovery capability | GitHub administration and PyPI Owner only after full trust and handover |

A contributor may remain at any stage or leave at any time. No one should be pressured to accept on-call duties, a response SLA, security responsibility, or ownership. Access follows responsibility and is increased only when needed.

### Practical progression checkpoints

- **First contribution:** agree on a bounded issue, provide a minimal reproducer or focused patch, and pass the relevant checks.
- **Repeated contribution:** independently review related changes, explain compatibility impact, and help close the loop on reported regressions.
- **Maintainer trial:** shadow issue triage, review a compatibility failure, inspect release evidence, and document a proposed fix. Do not grant admin access as a test.
- **Release rehearsal:** under supervision, follow the documented release preflight, inspect exact-commit CI, validate wheel/sdist and installed-artifact checks, and explain rollback/resume steps. Do not publish a test release just to prove access.
- **Shared stewardship:** agree explicitly on responsibilities, availability, escalation boundaries, and access. Keep at least two people familiar with routing, middleware, DRF integration, compatibility, and release operations before describing shared maintenance as established.
- **Succession:** follow the handover stages in [GOVERNANCE.md](../GOVERNANCE.md), including separate GitHub, PyPI, and Trusted Publisher checks. Never exchange passwords, recovery codes, or long-lived personal tokens.

## 5. A staged 90-day operating plan

The dates below are suggested checkpoints, not commitments or a guaranteed response schedule.

### Days 0–30: make evaluation reproducible

- Keep the existing consumer integration project and OpenAPI example green; fix drift before inviting more evaluators.
- Publish a short “run this in your project” checklist with pinned versions, exact commands, and expected outputs.
- Invite specific, bounded feedback on middleware order, resolver behavior, cache keys, trusted hosts, DRF reversal, and OpenAPI snapshots.
- Triage every report into reproducible, needs-information, unsupported-combination, or not-reproduced states.
- Record external feedback only with permission and distinguish it from repository-owned fixtures.

### Days 31–60: turn feedback into durable contracts

- Convert confirmed external findings into focused regression tests in the existing integration project.
- Ask an independent reviewer to inspect one bounded area (for example cache variation or the consumer adapter); record review scope, commit, findings, and disposition only if the review occurs.
- Improve the relevant example/docs from observed friction, not hypothetical user journeys.
- Identify recurring contributor interests without promising access or assigning responsibilities.

### Days 61–90: test maintenance sharing, not just code contribution

- Invite willing regular contributors to shadow triage and review.
- Run a supervised release-readiness rehearsal with a qualified volunteer only if one has explicitly agreed.
- Review governance, access, release instructions, and operational knowledge gaps.
- Report actual outcomes: reproducible external reports, independent reviews completed, contributions merged, people who explicitly accepted recurring duties, and unresolved single-maintainer risk.
- If no suitable volunteer emerges, state that plainly and continue the documented single-maintainer risk controls; do not manufacture a succession milestone.

## 6. Lightweight community reporting

Maintain a short public update in Issue #151 or a linked discussion. Update only when there is new evidence. A useful format is:

- **External evaluations:** number of reproducible reports; link to public reports where attribution is permitted.
- **Independent reviews:** scope, reviewed commit/release, and findings/disposition.
- **Adoption:** confirmed downstream projects only, with permission to identify them; otherwise “not yet evidenced.”
- **Contributions:** merged external contributions and the areas they improved.
- **Maintenance capacity:** people who explicitly agreed to recurring duties; otherwise “no additional maintainer commitment.”
- **Risks:** unsupported combinations, open high-impact bugs, release/response constraints, and remaining single-maintainer risk.

Do not use stars, downloads, repository CI, or the existence of sample code as proxies for independent production use.

## 7. Outreach copy (draft only)

The following text is prepared for maintainers to adapt for a GitHub Discussion, Django Forum post, or direct invitation. It has not been sent. Do not imply that a community organization, downstream project, or individual has endorsed or agreed to participate.

> **Help evaluate Django API Versioning in a real project**
>
> We are looking for Django and Django REST Framework developers willing to try the package in an existing application and share concrete technical feedback.
>
> The most useful areas to evaluate are request negotiation (path/header/query/hostname), middleware ordering and Django resolver behavior, cache keys and `Vary`, trusted-host validation, DRF ViewSet routing/reversal, and the consumer-owned adapter plus per-version OpenAPI snapshots.
>
> You do not need to become a maintainer. A small reproducible test, a documentation correction, or a focused review is valuable. Please include your package/framework versions, configuration, exact request and commands, and expected versus actual behavior. Do not share secrets or production customer data.
>
> Start with the [consumer OpenAPI example](../examples/openapi_contract/README.md), the [contribution guide](../CONTRIBUTING.md), and [Issue #151](https://github.com/mojtaba-arvin/django-api-versioning/issues/151). Feedback is welcome; independent adoption and external review will be reported only when supported by evidence and permission.

## 8. Success criteria

The plan is working when a new evaluator can reproduce the example without private maintainer guidance; a real downstream integration report can be converted into a regression test; a reviewer can independently understand and assess the public contract; contributors can make progress without privileged access; and a willing contributor can learn release operations without being rushed into ownership.

The project remains single-maintainer until a second person explicitly accepts and performs an agreed role. Documentation, CI, and invitations reduce risk; they do not eliminate it.
