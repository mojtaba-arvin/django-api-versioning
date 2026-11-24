---
name: routing-architecture
description: Plan or implement structural changes to django-api-versioning route state, immutable snapshots, registry ownership, request-version negotiation, DRF adapters, or route diagnostics. Use for multi-component architecture migrations, not routine isolated bug fixes.
---

# Routing architecture migration

Use this skill for the staged architecture plan tracked by GitHub epic #197 and its child issues. It supplies domain-specific migration rules; it does not replace the repository execution contract.

## Required companion workflows

- First select exactly one eligible GitHub child issue and follow the fresh-session, branch, checkpoint, and exact-head CI rules in [plan-execution](../plan-execution/SKILL.md).
- Follow general package implementation, public compatibility, test, lint, and release-safety rules in [package-engineering](../package-engineering/SKILL.md).
- Read [AGENTS.md](../../../AGENTS.md) and the canonical [routing contract](../../../docs/reference/versioning-contract.md). Load only the relevant design documents, source, callers, and tests named by the child issue.
- Run `python scripts/agent.py context routing-architecture` before broad exploration and `python scripts/agent.py doctor` before editing.

## Architecture invariants

1. **One authoritative state owner.** Map every current registry writer and reader before editing. Do not introduce a shadow registry, duplicate mutable route dictionary, parallel singleton, or second route-matrix cache.
2. **Compatibility facade first.** Preserve `django_api_versioning.registry`, `UrlRegistry`, and the module-level `registry` as compatibility entry points while moving implementation ownership. When introducing `django_api_versioning/registry/`, make `registry/__init__.py` the facade and prove that the import path remains unchanged; do not leave an ambiguous competing `registry.py` module and package.
3. **Characterize before moving.** Extend existing deterministic/property tests before extraction. Model observable behavior with an independent expected-state model; never calculate expected results by calling private implementation helpers.
4. **Immutable means deeply immutable.** Route records and snapshots must not expose mutable nested dictionaries/lists. A published snapshot never changes. Successful transactions atomically publish a new generation; failures publish nothing. Readers holding older snapshots continue to see the old state.
5. **Import/reload behavior is a contract.** Define when repeated URLconf imports or autoreload are idempotent versus a true collision. Test repeated configuration, test isolation, removal/reintroduction, and failed transactions. Never silently clear another app's registrations.
6. **Owner identity is stable and scoped.** Do not expose Python object IDs or memory addresses. A router's tombstones, route identity, lifecycle, and diagnostics must not leak into another router or decorator owner.
7. **One PR, one responsibility.** Extract registration, removal, resolution, lifecycle, and matrix projection in separate reviewable child issues/PRs. Move state once, update callers coherently, and remove obsolete code only after imports/tests prove no references remain.
8. **Keep Django and DRF boundaries explicit.** Django remains the route resolver and URLPattern authority. DRF remains optional and owns route generation. Core package imports must work without DRF. Route/action/namespace/reversal/API-root/suffix capabilities belong behind one narrow optional adapter.
9. **Keep middleware orchestration thin.** One configured transport is selected per deployment. Path, header, query, and hostname negotiators should be small and independently testable; do not create wrapper classes that merely rename one function.
10. **Diagnostics are read-only.** Report active, removed, absent, overridden, and rejected declarations with deterministic fields. Source locations and owner labels are omitted when they cannot be grounded; never invent them. Do not store request bodies, tracebacks, secrets, object reprs, or unbounded event histories.
11. **Public APIs require a lifecycle contract.** Evaluate configure/build_urlpatterns/registry_snapshot only after snapshot semantics are stable. Define timing, idempotency, URLconf integration, mixed legacy/new usage, optional dependencies, and reset behavior before exporting names.
12. **One canonical documentation owner.** Update the routing contract/reference only when behavior changes. Generated website files must use their generator. Never create parallel API inventories, ADR copies, status pages, handoffs, or route-matrix documents.

## Migration sequence

Follow the dependencies in epic #197 rather than improvising the order:

1. Finish cross-owner state-machine characterization.
2. Define immutable route records and effective snapshots.
3. Extract registration/collision precedence behind the facade.
4. Extract removal/tombstone transitions.
5. Extract Django route/operation resolution.
6. Extract endpoint lifecycle metadata and matrix projections.
7. Isolate transport negotiators and optional DRF capabilities.
8. Add provenance-rich diagnostics and evaluate the public integration adapter.
9. Stabilize public import categories, developer workflow, documentation gates, and automation ownership.

Independent issues may run in parallel only when their files and dependencies do not overlap and each has an isolated worktree/branch.

## Verification

For each child issue:

- Map the current state owner, all callers, public import paths, and existing tests before editing.
- Add focused tests for success, invalid input, precedence, ownership, boundaries, rollback, concurrency, and compatibility where applicable.
- Verify old snapshots remain stable after later writes and failed writes publish no partial state.
- Test Django-only imports with DRF absent and optional integration behavior with supported DRF versions.
- Run focused unit/integration tests, then use the current path classifier and PR gate to determine the required CI jobs.
- Run `tox run -e lint` after the final Python edit. Verify all applicable CI results against the exact PR head SHA.
- Report each check as PASS, FAIL, or NOT RUN with command, exit code, tested SHA, and CI URL. A configured or skipped job is not a pass.

## Stop conditions

Stop and update the owning issue instead of guessing when:

- the dependency is not merged or its acceptance evidence is missing;
- the checkout is dirty and ownership of changes is unclear;
- a proposed model cannot be made immutable without duplicating state;
- a component has no distinct state responsibility or real caller;
- a proposed protocol has no concrete capability boundary;
- behavior differs from the canonical routing contract and compatibility impact is unclear;
- CI selection or exact-head evidence cannot be established.

Do not compensate for a failed architectural hypothesis by adding unused abstractions, broad rewrites, duplicate docs, or additional automation frameworks.
