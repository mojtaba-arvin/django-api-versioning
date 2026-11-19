# Endpoint-level lifecycle metadata

**Status:** Product semantics finalized; implementation is present in Draft PRs #67–#71 but is not merged to main. Exact-head PR gates and CodeQL have passed for the runtime/schema stack; revalidate after subsequent changes.
**Related:** [Issue #39](https://github.com/mojtaba-arvin/django-api-versioning/issues/39), [roadmap #36](https://github.com/mojtaba-arvin/django-api-versioning/issues/36)
**Depends on:** the merged endpoint-removal/tombstone contract and version-wide `LifecycleMiddleware`.

## Context

The package now supports two distinct capabilities:

- Version-wide lifecycle policy through `API_VERSION_LIFECYCLE`, applied by `LifecycleMiddleware`.
- Explicit route removal through registry tombstones. A removed route is absent from URL resolution, returns ordinary 404 behavior, and is omitted from the version's OpenAPI schema.

Neither capability expresses that one still-active operation is deprecated while other operations in the same API version remain active. This proposal addresses that gap without changing either existing contract.

## Goals

1. Declare deprecation and optional sunset metadata for one logical endpoint/action in selected API versions.
2. Apply response metadata only when the actual resolved operation matches the declaration.
3. Keep route removal, version retirement, and endpoint deprecation as separate concepts.
4. Make schema output accurately describe endpoint-level deprecation without requiring drf-spectacular as a runtime dependency.
5. Preserve deterministic behavior across import order, router registration order, namespaces, and repeated test setup.
6. Keep existing public APIs and historical route-matrix/snapshot formats backward-compatible when no endpoint lifecycle metadata is declared.

## Non-goals

- Automatically removing routes when a sunset date passes.
- Changing the existing default 404 behavior for tombstoned routes.
- Introducing endpoint-level 410 responses in the first iteration.
- Replacing Django/DRF view dispatch, versioning, or schema generation.
- Tracking per-consumer usage or automatically deciding when an endpoint is safe to remove.

## Proposed conceptual model

Treat endpoint lifecycle as metadata attached to a stable logical operation identity and a concrete API version, not as a URL regex or callback identity.

Candidate identity components:

- Decorator endpoint: the existing logical endpoint key (`app_name + postfix`).
- DRF operation: router prefix plus the stable generated route name/action identity already used by endpoint removal.
- Concrete API version: the version whose resolved route is being served.

The declaration should be metadata-only and must not register, delete, or mutate URL patterns. The public API uses adapter-specific declarations over one normalized registry record: set_endpoint_lifecycle() for decorator endpoints and VersionedRouter.set_lifecycle() for DRF routes. Their concrete signatures are recorded in D7 and the canonical reference.

Candidate lifecycle fields:

- `deprecated_at`: optional ISO-8601 timestamp/date, consistent with the current version-wide setting.
- `sunset`: optional HTTP-date-compatible timestamp/date, consistent with the current version-wide setting.
- `status`: derived or validated state; avoid allowing contradictory free-form combinations.

Do not duplicate version-wide configuration wholesale. Prefer a narrow per-operation declaration that can be validated and normalized by the registry.

## Precedence and composition

The following rules are proposed for acceptance testing:

1. A matching endpoint-level policy applies only to the actual resolved logical operation and concrete version.
2. Version-wide policy remains authoritative for retiring an entire API version. Endpoint-level metadata must never cancel a version-wide sunset/410.
3. When both scopes provide the same date-bearing header, emit the earlier parsed instant. Deprecation and Sunset are composed independently; a narrower declaration cannot postpone a broader one.
4. A tombstoned route has no resolved operation and therefore receives no endpoint-level lifecycle headers. The existing version-wide unresolved-path behavior remains governed by the existing middleware contract.
5. An explicit later reintroduction is a new active declaration segment. It must not accidentally inherit stale endpoint lifecycle metadata unless the declaration explicitly opts into that metadata.
6. A request that cannot be mapped to exactly one logical operation must not guess. It may still receive version-wide policy, but no endpoint-specific headers.

## HTTP behavior

For an active, resolved operation:

- Emit RFC 9745 `Deprecation` when a valid deprecation instant is configured.
- Emit RFC 8594 `Sunset` when a valid sunset instant is configured.
- Do not synthesize a 410 merely because the endpoint's sunset date has passed in the first iteration. The route remains registered and the existing route contract remains in effect until the application explicitly removes it in a later version.
- Invalid metadata should fail configuration validation where possible; do not silently turn malformed dates into a different policy.

The past-endpoint-Sunset behavior is decided: headers only. It does not automatically return 410, unregister a route, or change schema visibility. Version-wide past-Sunset enforcement remains authoritative.

## OpenAPI behavior

- A deprecated active operation should be represented as `deprecated: true` in the matching version's OpenAPI document.
- Do not add a vendor extension for Sunset in the first iteration. Sunset is represented by the HTTP response header and documentation.
- Removed operations remain absent due to the existing tombstone behavior.
- Version-wide lifecycle and endpoint-level lifecycle must not cause duplicate or conflicting schema metadata.
- Schema integration must remain optional: core package imports and runtime must not import drf-spectacular.

Before implementation, prove the supported extension point with an executable consumer fixture. Do not post-process arbitrary generated YAML based on regex/path guesses.

## Acceptance tests implemented in the Draft stack

### Registry and identity
- Decorator endpoint metadata is scoped by logical endpoint and concrete version.
- DRF metadata targets exactly one custom action and does not affect list/detail/sibling actions.
- Namespaces, duplicate route names across routers, converters, trailing slash settings, and nested URL includes do not cause cross-operation matches.
- Declaration-before-registration and declaration-after-registration produce identical metadata.
- Repeated declarations have deterministic precedence or raise a clear configuration error.
- Metadata reset/clear behavior matches registry test isolation.

### Version and lifecycle composition
- Endpoint-level deprecation affects only the selected operation.
- Version-wide deprecation still applies to every operation in that version.
- Version-wide sunset/410 cannot be weakened by endpoint-level configuration.
- Conflicting dates and statuses are validated deterministically.
- Explicit version sets and inherited route segments are handled correctly.
- A tombstone suppresses endpoint metadata for removed versions.
- Reintroduction does not inherit stale lifecycle metadata accidentally.
- Unresolved and ambiguous requests never receive guessed endpoint-level headers.

### HTTP integration
- Real Django client tests exercise middleware order and actual URL resolution.
- Real DRF APIClient tests exercise custom actions and request dispatch.
- Assert exact Deprecation/Sunset headers and behavior for past/future dates using frozen time.
- Verify sync and async middleware paths.

### OpenAPI integration
- Active deprecated endpoint has `deprecated: true` only in the intended version schema.
- Non-deprecated sibling operations remain unchanged.
- Removed endpoint remains absent.
- Reintroduced endpoint has only its newly declared lifecycle metadata.
- Schema generation remains deterministic and optional integration dependencies stay out of runtime requirements.

## Implementation status and rollout

The implementation is split into independently reviewable Draft PRs:

1. [PR #67](https://github.com/mojtaba-arvin/django-api-versioning/pull/67): resolver-backed logical operation identity.
2. [PR #68](https://github.com/mojtaba-arvin/django-api-versioning/pull/68): normalized lifecycle declarations and decorator/DRF adapters.
3. [PR #69](https://github.com/mojtaba-arvin/django-api-versioning/pull/69): response headers and version-wide 410 precedence.
4. [PR #70](https://github.com/mojtaba-arvin/django-api-versioning/pull/70): optional drf-spectacular adapter for VersionedRouter/NamespaceVersioning.
5. [PR #71](https://github.com/mojtaba-arvin/django-api-versioning/pull/71): decorator endpoint adapter for URLPathVersioning.

The implementation stack remains unmerged. Keep the PRs Draft until dependency order, review, and the normal repository merge gates are satisfied. After merge, verify the final mainline SHA and rerun the relevant consumer and compatibility checks.

## Product decisions

The following decisions are the default contract for the first implementation. They intentionally favor additive metadata and predictable compatibility over automatic enforcement.

### D1 — Scope is the concrete resolved API version

Lifecycle metadata is attached to one logical operation in one concrete API version. A declaration for v2 does not implicitly affect v1 or v3, even when the route itself is inherited. If an application wants the same lifecycle policy in multiple versions, it must declare those versions explicitly (or use a future, separately specified shorthand that expands to the same explicit version set).

This avoids coupling endpoint lifecycle to the mechanics of route inheritance and makes the generated schema for each version independently explainable.

### D2 — Operation identity is resolved, never guessed

The request-side key must come from Django's resolved route and the router/endpoint registry's canonical operation record. Path strings, regular expressions, URL substring matching, callback object identity, and an unqualified route name are not acceptable identity sources.

For DRF, the identity must distinguish each HTTP-method/action pair on a ViewSet route, including custom actions. Namespaces and router identity are part of disambiguation. If the current registry cannot provide a stable canonical key for a request before or during DRF dispatch, extend the registry first; do not introduce a second, approximate identity algorithm in middleware.

A request that cannot be mapped to exactly one operation receives no endpoint-level metadata. Version-wide middleware behavior remains independent.

### D3 — Composition is monotonic and version-wide retirement wins

- Version-wide deprecation/sunset headers continue to apply to all requests in their existing scope.
- Endpoint-level metadata may add a header to a matching operation, but may never remove, delay, or weaken version-wide metadata.
- When both scopes provide the same date-bearing header, emit the earlier instant (the more conservative boundary). Normalize and compare parsed instants; reject invalid values and ambiguous timezone handling at configuration time.
- A version-wide retired/sunset policy that currently produces 410 remains authoritative. Endpoint metadata cannot downgrade it.
- Endpoint metadata alone never changes the response status in v1 of this feature.

### D4 — Past endpoint sunset remains headers-only

Passing an endpoint's sunset instant does not automatically return 410, unregister a route, or change schema visibility. The route remains active until the application explicitly removes it through the existing route-removal contract. This prevents a date crossing from silently becoming a breaking runtime change and keeps schema truth aligned with actual routing.

Any future endpoint-specific enforcement mode requires a separate opt-in design and compatibility review; it is not part of this feature.

### D5 — OpenAPI uses the standard operation flag only

For the first implementation, endpoint deprecation maps to the standard OpenAPI Operation Object field `deprecated: true`. Do not add a vendor extension for Sunset yet: there is no agreed cross-tool consumer contract, and a non-standard extension would create a long-lived public schema surface. Sunset remains available through the HTTP response header and documentation.

The integration remains optional and must use the supported drf-spectacular extension points. It must not parse or rewrite arbitrary serialized YAML/JSON.

### D6 — Route matrix remains about route existence

Do not add lifecycle dates or deprecation state to the existing route-matrix snapshot format. The matrix answers whether an operation exists in a version; lifecycle is a separate concern. If lifecycle reporting is later needed, add a separately versioned report/manifest rather than changing existing snapshot semantics.

### D7 — Public declaration API is adapter-specific over one registry contract

Do not force decorator endpoints and DRF actions into a single public syntax if doing so obscures their native identity or ergonomics. The implementation must have one normalized internal lifecycle record and validation model, with thin public adapters that reference the canonical identities already exposed by each registration API.

Before choosing exact names/signatures, audit the current decorator and router registration contracts and demonstrate that each adapter resolves to the same normalized record used by middleware and schema generation. No URL-based fallback is permitted. This is a deliberate API gate, not permission to ship two independent stores.

### Implementation audit (Draft stack, 2026-11-19)

The runtime implementation is now present in the stacked Draft PRs:

- Decorator and DRF route registrations retain stable logical endpoint identity and concrete route-version metadata on their registered URLPatterns.
- PR #67 adds immutable normalized operation identity based on the actual Django ResolverMatch, concrete HTTP method, namespace/route metadata, and DRF action map. Ambiguous matches fail closed.
- PR #68 adds one normalized lifecycle registry and adapter-specific public declarations. The decorator declaration uses the same app_name + postfix identity as @endpoint; the router declaration uses prefix + generated route name + concrete version.
- PR #69 applies endpoint headers from the resolved operation. It composes version-wide and endpoint-level dates independently, choosing the earliest instant for each header. Version-wide past-Sunset 410 remains authoritative; endpoint-level past Sunset is headers-only.
- PR #70 and PR #71 add optional drf-spectacular AutoSchema integration for VersionedRouter and decorator-backed DRF views respectively. The adapter does not import drf-spectacular from the package root or add it to runtime dependencies.
- Tests cover method/action separation, version isolation, route ambiguity, actual Django request resolution, headers, past-Sunset precedence, and generated OpenAPI operation flags.

These PRs are still Draft and not merged. Passing CI on their exact heads is evidence for those branch commits only; it is not evidence that main already contains the implementation.

## Schema-generation audit (drf-spectacular 0.30.0)

The repository's OpenAPI consumer fixture pins drf-spectacular 0.30.0. Inspection of that exact upstream release establishes a supported resolver-aware integration path for `VersionedRouter`:

1. `SchemaGenerator.parse()` creates each schema view and assigns its mock request before calling `modify_for_versioning()`.
2. For `NamespaceVersioning`, `modify_for_versioning()` resolves the version-adjusted path with Django's `get_resolver(...).resolve(path)` and assigns the resulting `ResolverMatch` to `view.request.resolver_match`.
3. `VersionedRouterVersioning` subclasses DRF `NamespaceVersioning`; the schema view therefore has the actual resolved route, URL name, and namespace during operation generation.
4. The schema generator also creates the ViewSet instance with its selected `view.action`, and calls `AutoSchema.get_operation()` with the concrete HTTP method. A supported `AutoSchema` subclass/mixin can therefore resolve the registry operation using `request.resolver_match`, method, and action, then set only the standard operation field `deprecated: true`.

This is a genuine resolver-based mapping, not a path-regex or operationId heuristic. The pinned source path is `drf_spectacular/generators.py` (`SchemaGenerator.parse` / `create_view`), `drf_spectacular/plumbing.py` (`modify_for_versioning`), and `drf_spectacular/openapi.py` (`AutoSchema.get_operation`).

**Remaining schema gap:** the decorator-based adapter may use DRF `URLPathVersioning`. In drf-spectacular 0.30.0 that branch substitutes the version into `view.kwargs` but does not populate `request.resolver_match`. Its schema adapter must therefore use logical endpoint metadata attached by the decorator plus the version kwarg, and resolve that pair against the registry. It must not fall back to matching generated path strings or regexes.

### Updated implementation sequence

1. Add an immutable normalized operation record and a registry resolver that consumes Django's `ResolverMatch`, HTTP method, and DRF action mapping; ambiguity fails closed.
2. Add consumer tests for nested namespaces, route converters, duplicate route names, DRF multi-method actions, and decorator endpoints.
3. Add an optional drf-spectacular `AutoSchema` mixin/class that marks the exact operation deprecated and leaves other operations untouched.
4. Add the decorator adapter using its logical endpoint metadata and URLPathVersioning's version kwarg.
5. Only then expose the public lifecycle declaration API and middleware headers. No automatic endpoint-level 410 behavior is introduced.

## Schema-generation implementation (drf-spectacular 0.30.0)

The pinned consumer fixture proves both supported paths against drf-spectacular 0.30.0:

- **VersionedRouter / NamespaceVersioning:** drf-spectacular resolves the version-adjusted path through Django and exposes the actual ResolverMatch on the schema view request. The AutoSchema adapter resolves the registry record with the concrete HTTP method and ViewSet action.
- **Decorator endpoint / URLPathVersioning:** drf-spectacular injects the selected schema version into view.kwargs but does not populate request.resolver_match. The @endpoint decorator therefore attaches its stable logical identity to the generated DRF view class; the adapter resolves identity + concrete version + method through the active registry. Duplicate or missing matches fail closed.

Both paths set only the standard OpenAPI Operation Object field deprecated: true when deprecated_at is present. Sunset-only metadata does not mark the operation deprecated. Existing explicit @extend_schema(deprecated=True) is never cleared. Removed routes remain absent because they are not registered.

The executable consumer contract verifies that a V1-only deprecated VersionedRouter action and a V1-only decorator endpoint are marked in V1 schemas but not in V2 or sibling operations. The adapter does not infer identity from paths, regexes, callback identity, or operation IDs.

## Public declaration API (implemented in the Draft stack)

The first implementation uses adapter-specific public declarations over the same normalized registry:

~~~python
from django_api_versioning import endpoint, set_endpoint_lifecycle

@endpoint("orders/", version=1, view_name="orders-list")
def orders_v1(request):
    ...

set_endpoint_lifecycle(
    "orders/",
    version=2,
    methods=["GET"],
    deprecated_at="2027-01-01T00:00:00Z",
)
~~~

~~~python
router.set_lifecycle(
    "orders",
    "order-list",
    version=2,
    action="list",
    methods=["GET"],
    deprecated_at="2027-01-01T00:00:00Z",
)
~~~

- The decorator helper identifies the logical endpoint using the same app_name/postfix identity as @endpoint; version is one concrete route version, never a lower-bound inheritance declaration.
- Omitting methods applies to all methods for that logical endpoint/version. Supplying methods creates method-scoped declarations.
- The router adapter identifies a registered route by prefix + generated route name + concrete version, then validates optional action/method scopes against the actual DRF action map.
- Route-wide, action-wide, method-wide, and exact method/action declarations compose monotonically. For each header, the earliest instant wins.
- Repeating an identical declaration is idempotent; conflicting values for the same exact scope fail at registration time.
- Dates are strict ISO 8601 strings normalized to UTC; timezone-naive values are interpreted as UTC. Sunset cannot precede deprecated_at. Sunset may be declared without a Deprecation date; in that case it emits only the Sunset header and does not set O## Implementation gate

The design decisions are resolved and the implementation is available in the Draft PR stack #67–#71. This ADR remains a design record; it does not claim that the feature is present in the currently released package or in main until those PRs are reviewed and merged.

Do not mark the implementation complete based only on a documentation workflow. Completion on main requires the final merged SHA, passing exact-head PR gate and CodeQL evidence for the merged code, and the executable consumer contract passing against that mainline commit.
