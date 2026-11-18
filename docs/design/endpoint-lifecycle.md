# Endpoint-level lifecycle metadata

**Status:** Proposed — design review required; no runtime API is committed.
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

## Decisions still required

- Public declaration shape and whether one common API can cover decorator endpoints and DRF actions cleanly.
- Whether lifecycle dates are per concrete API version, source declaration segment, or both.
- Exact precedence when endpoint and version-wide dates conflict.
- Whether a past endpoint sunset is headers-only (recommended default) or can opt into endpoint-specific 410.
- Whether to expose a vendor OpenAPI extension for sunset dates and, if so, its stable name.
- Whether endpoint lifecycle state belongs in route-matrix snapshots or should remain a separate lifecycle report.

No implementation should begin until these decisions are captured in an accepted ADR and the acceptance tests make the intended semantics executable.
