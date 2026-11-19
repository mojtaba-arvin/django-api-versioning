# Endpoint-level lifecycle metadata

**Status:** Implemented and merged to `main` in PR #71 (merge commit `1db0358c1600f97eaabb03c2436551c030dc93af`, 2026-11-19). The exact-head PR gate and CodeQL passed before merge. The feature is in the repository mainline; it is not yet represented by a newer PyPI release.
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

## Conceptual model

Treat endpoint lifecycle as metadata attached to a stable logical operation identity and a concrete API version, not as a URL regex or callback identity.

Identity components:

- Decorator endpoint: the existing logical endpoint key (`app_name + postfix`).
- DRF operation: router prefix plus the stable generated route name/action identity already used by endpoint removal.
- Concrete API version: the version whose resolved route is being served.

The declaration should be metadata-only and must not register, delete, or mutate URL patterns. The public API uses adapter-specific declarations over one normalized registry record: set_endpoint_lifecycle() for decorator endpoints and VersionedRouter.set_lifecycle() for DRF routes. Their concrete signatures are recorded in D7 and the canonical reference.

Lifecycle fields:

- `deprecated_at`: optional ISO-8601 timestamp/date, consistent with the current version-wide setting.
- `sunset`: optional HTTP-date-compatible timestamp/date, consistent with the current version-wide setting.

Do not duplicate version-wide configuration wholesale. Prefer a narrow per-operation declaration that can be validated and normalized by the registry.

## Precedence and composition

The following rules define the accepted first-iteration contract:

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
- Do not synthesize a 410 merely because the endpoint's sunset date has passed. The route remains registered and the existing route contract remains in effect until the application explicitly removes it in a later version.
- Invalid metadata should fail configuration validation where possible; do not silently turn malformed dates into a different policy.

The past-endpoint-Sunset behavior is decided: headers only. It does not automatically return 410, unregister a route, or change schema visibility. Version-wide past-Sunset enforcement remains authoritative.

## OpenAPI behavior

- A deprecated active operation should be represented as `deprecated: true` in the matching version's OpenAPI document.
- Do not add a vendor extension for Sunset in the first iteration. Sunset is represented by the HTTP response header and documentation.
- Removed operations remain absent due to the existing tombstone behavior.
- Version-wide lifecycle and endpoint-level lifecycle must not cause duplicate or conflicting schema metadata.
- Schema integration must remain optional: core package imports and runtime must not import drf-spectacular.

The supported extension points are proven by the executable consumer fixture and the optional AutoSchema adapter described below. Do not post-process arbitrary generated YAML based on regex/path guesses.

## Acceptance criteria and implementation coverage

The list below defines the acceptance surface. The merged PR #71 includes executable coverage for resolver identity, action/method isolation, version isolation, headers, version-wide 410 precedence, and both OpenAPI adapter paths. Any criterion not represented by a dedicated test remains a post-merge review item rather than an assumed pass.

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

The implementation was delivered as one cumulative change in [PR #71](https://github.com/mojtaba-arvin/django-api-versioning/pull/71), after component PRs #67–#70 were closed as superseded to avoid overlapping snapshots. The merged change includes resolver-backed operation identity, normalized declarations, response headers, both optional OpenAPI adapter paths, executable consumer coverage, and reference documentation.

The final mainline commit is `1db0358c1600f97eaabb03c2436551c030dc93af`. Exact-head PR gate run [44442100596](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/44442100596) and CodeQL run [44442100571](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/44442100571) succeeded before merge. The next release must still include the usual release notes, full compatibility matrix and artifact verification.

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

Use thin public adapters over one normalized lifecycle record. Preserve each registration API's native identity rather than forcing decorator endpoints and DRF actions into one ambiguous syntax.

The implemented public API is:

- Decorator endpoint: set_endpoint_lifecycle(postfix, *, version, app_name=None, methods=None, deprecated_at=None, sunset=None). Its logical identity is app_name + postfix, matching @endpoint.
- DRF router operation: router.set_lifecycle(prefix, route_name, *, version, action=None, methods=None, deprecated_at=None, sunset=None). Its identity is router prefix + generated route name + concrete version; action/method scopes are validated against the actual callback action map.

Both adapters write to the same registry and validation model. Repeating an identical declaration is idempotent; conflicting values for an exact scope fail. No URL-based fallback or second lifecycle store is permitted.

### Implementation audit (merged mainline, 2026-11-19)

The runtime implementation is present in main after PR #71:

- Decorator and DRF route registrations retain stable logical endpoint identity and concrete route-version metadata on their registered URLPatterns.
- The merged implementation adds immutable normalized operation identity based on the actual Django ResolverMatch, concrete HTTP method, namespace/route metadata, and DRF action map. Ambiguous matches fail closed.
- The merged implementation adds one normalized lifecycle registry and adapter-specific public declarations. The decorator declaration uses the same app_name + postfix identity as @endpoint; the router declaration uses prefix + generated route name + concrete version.
- The merged middleware applies endpoint headers from the resolved operation. It composes version-wide and endpoint-level dates independently, choosing the earliest instant for each header. Version-wide past-Sunset 410 remains authoritative; endpoint-level past Sunset is headers-only.
- The merged optional drf-spectacular AutoSchema integration supports VersionedRouter and decorator-backed DRF views. The adapter does not import drf-spectacular from the package root or add it to runtime dependencies.
- Tests cover method/action separation, version isolation, route ambiguity, actual Django request resolution, headers, past-Sunset precedence, and generated OpenAPI operation flags.

The implementation is merged to main at `1db0358c1600f97eaabb03c2436551c030dc93af`. The successful exact-head checks preceded the merge; use this mainline commit for subsequent regression and release verification.

## Schema-generation implementation (drf-spectacular 0.30.0)

The pinned consumer fixture proves both supported paths against drf-spectacular 0.30.0:

- **VersionedRouter / NamespaceVersioning:** drf-spectacular resolves the version-adjusted path through Django and exposes the actual ResolverMatch on the schema view request. The AutoSchema adapter resolves the registry record with the concrete HTTP method and ViewSet action.
- **Decorator endpoint / URLPathVersioning:** drf-spectacular injects the selected schema version into view.kwargs but does not populate request.resolver_match. The @endpoint decorator therefore attaches its stable logical identity to the generated DRF view class; the adapter resolves identity + concrete version + method through the active registry. Duplicate or missing matches fail closed.

Both paths set only the standard OpenAPI Operation Object field deprecated: true when deprecated_at is present. Sunset-only metadata does not mark the operation deprecated. Existing explicit @extend_schema(deprecated=True) is never cleared. Removed routes remain absent because they are not registered.

The executable consumer contract verifies that a V1-only deprecated VersionedRouter action and a V1-only decorator endpoint are marked in V1 schemas but not in V2 or sibling operations. The adapter does not infer identity from paths, regexes, callback identity, or operation IDs.

## Public declaration API (implemented in main)

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
- Dates are strict ISO 8601 strings normalized to UTC; timezone-naive values are interpreted as UTC. Sunset cannot precede deprecated_at. Sunset may be declared without a Deprecation date; in that case it emits only the Sunset header and does not set OpenAPI deprecated: true.

The public API and runtime behavior are implemented in main by PR #71. The mainline commit `1db0358c1600f97eaabb03c2436551c030dc93af` is the current implementation evidence.

## Implementation gate

The design decisions are resolved and the implementation is merged to main in PR #71 at `1db0358c1600f97eaabb03c2436551c030dc93af`. The exact-head PR gate and CodeQL checks passed, including the executable consumer contract.

The feature is implemented in the repository mainline but is not yet a separately published PyPI release. Before the next release, run the full release compatibility matrix, rebuild and install both wheel and sdist in isolation, verify the changelog and docs, and publish only from the verified mainline tag.
