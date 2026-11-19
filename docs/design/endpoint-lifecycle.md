# Endpoint-level lifecycle metadata

**Status:** Product semantics decided; registry identity audit completed; schema integration proof and executable consumer tests remain before runtime implementation. No runtime API is committed.
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

The declaration should be metadata-only and must not register, delete, or mutate URL patterns. The exact public API shape is intentionally undecided pending tests and ergonomics review.

Candidate lifecycle fields:

- `deprecated_at`: optional ISO-8601 timestamp/date, consistent with the current version-wide setting.
- `sunset`: optional HTTP-date-compatible timestamp/date, consistent with the current version-wide setting.
- `status`: derived or validated state; avoid allowing contradictory free-form combinations.

Do not duplicate version-wide configuration wholesale. Prefer a narrow per-operation declaration that can be validated and normalized by the registry.

## Precedence and composition

The following rules are proposed for acceptance testing:

1. A matching endpoint-level policy applies only to the actual resolved logical operation and concrete version.
2. Version-wide policy remains authoritative for retiring an entire API version. Endpoint-level metadata must never cancel a version-wide sunset/410.
3. When both scopes provide deprecation metadata, define deterministic merge semantics before implementation. The conservative candidate is the more restrictive/earlier lifecycle boundary, but date ordering and contradictory status need explicit validation rather than implicit dictionary merging.
4. A tombstoned route has no resolved operation and therefore receives no endpoint-level lifecycle headers. The existing version-wide unresolved-path behavior remains governed by the existing middleware contract.
5. An explicit later reintroduction is a new active declaration segment. It must not accidentally inherit stale endpoint lifecycle metadata unless the declaration explicitly opts into that metadata.
6. A request that cannot be mapped to exactly one logical operation must not guess. It may still receive version-wide policy, but no endpoint-specific headers.

## HTTP behavior

For an active, resolved operation:

- Emit RFC 9745 `Deprecation` when a valid deprecation instant is configured.
- Emit RFC 8594 `Sunset` when a valid sunset instant is configured.
- Do not synthesize a 410 merely because the endpoint's sunset date has passed in the first iteration. The route remains registered and the existing route contract remains in effect until the application explicitly removes it in a later version.
- Invalid metadata should fail configuration validation where possible; do not silently turn malformed dates into a different policy.

The precise behavior for a past endpoint sunset (headers only vs configurable enforcement) is a product decision and remains open. The initial safe default is headers only, because automatically returning 410 would introduce a new per-operation runtime behavior and complicate schema/client expectations.

## OpenAPI behavior

- A deprecated active operation should be represented as `deprecated: true` in the matching version's OpenAPI document.
- A future sunset date may be exposed as a documented operation extension only if a stable extension name and semantics are selected.
- Removed operations remain absent due to the existing tombstone behavior.
- Version-wide lifecycle and endpoint-level lifecycle must not cause duplicate or conflicting schema metadata.
- Schema integration must remain optional: core package imports and runtime must not import drf-spectacular.

Before implementation, prove the supported extension point with an executable consumer fixture. Do not post-process arbitrary generated YAML based on regex/path guesses.

## Required acceptance tests before runtime implementation

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

## Rollout plan

1. Complete this ADR and resolve the open product decisions below.
2. Add failing registry, middleware, DRF integration, and OpenAPI consumer tests.
3. Implement registry metadata storage and validation without changing HTTP behavior.
4. Implement resolved-operation lookup in lifecycle middleware using actual route identity.
5. Add optional schema integration and executable consumer contract tests.
6. Update docs and examples only after public API and behavior are stable.
7. Run the full PR gate, compatibility matrix, package install smoke, website checks, and CodeQL before marking the PR ready.

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

### Code-level audit (main, 2026-11-19)

The current implementation provides a useful foundation, but not yet the complete endpoint-operation identity required by this feature:

- Decorator registrations already attach `_django_api_versioning_logical_endpoint` and the concrete route version to each registered `URLPattern`. The logical key is derived from `app_name + postfix`.
- DRF registrations retain the original router-generated `URLPattern` and attach the same metadata. Their logical key is `prefix:pattern.name`; `pattern.name` is generated from the router basename and action route.
- `LifecycleMiddleware.process_view()` runs after Django URL resolution and before the selected view. This is the correct phase for endpoint-specific enforcement because `request.resolver_match` is available and the view has not executed.
- `ResolverMatch.route` contains the resolved route including parent include prefixes. The current registry helper `get_resolved_route_version()` matches registered route-pattern suffixes and returns only a version; it does not return a canonical logical operation record.
- One DRF URLPattern may map multiple HTTP methods to different ViewSet actions (for example, GET/list and POST/create). Therefore `prefix:pattern.name` alone is not enough to distinguish every OpenAPI operation. The normalized DRF identity must include the HTTP method and the router callback's method-to-action mapping.
- A resolved route string alone must not be treated as a globally unique key when namespace or router context can disambiguate it. The resolver's URL name/namespace and the registered pattern metadata must participate in the lookup. Ambiguous matches must fail closed for endpoint-level metadata.

### Required implementation shape

1. Add a registry lookup that returns a normalized immutable operation record (logical endpoint, concrete route version, source version, route name/namespace context, and optional DRF method/action), rather than returning only a version.
2. Resolve that record from `request.resolver_match` plus `request.method` and the selected callback's router action map. Do not parse raw request paths or use callback object identity.
3. Keep decorator endpoint metadata scoped to its existing logical endpoint key; for DRF, bind lifecycle declarations to a specific method/action when the generated route shares a URLPattern with sibling methods.
4. Prove the schema adapter independently. The schema fixture must demonstrate an exact path+method-to-registry mapping for decorator views and DRF actions before any hook is accepted. If drf-spectacular cannot expose enough stable route metadata at the chosen extension point, keep the integration blocked rather than falling back to operationId/path heuristics.
5. Keep registry reset, import-order determinism, and repeated declaration conflict handling consistent with the existing route registry.

This audit confirms that actual Django resolution is available at the correct middleware phase, but also identifies the missing method/action dimension and the need for an explicit schema proof. It is not a claim that endpoint-level metadata is implemented.

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

## Implementation gate

The product semantics above are decided. The remaining work is an implementation-level audit of the existing registry and schema extension points, followed by failing tests for those exact contracts. Keep this PR draft/design-only until that audit and tests are complete. A green documentation-only workflow is not evidence that runtime behavior is implemented or safe.

