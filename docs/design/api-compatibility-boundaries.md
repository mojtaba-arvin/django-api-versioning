# API compatibility boundaries

**Status:** Maintainer guidance for the 1.x routing and contract workflow  
**Runtime dependencies:** None added

## Decision

Treat API compatibility as three related but independent contracts:

| Contract | What must remain stable | Appropriate evidence |
| --- | --- | --- |
| Routing | Which URL exists and which implementation handles each concrete API version | `VersionedRouter`, `VersionedDefaultRouter`, `check_versions`, and `assert_version_matrix()` |
| Representation/schema | Request and response shapes, field types, requiredness, media types, and documented status/error responses | Version-specific OpenAPI documents, reviewed snapshots, schema validation, and `oasdiff` |
| Runtime semantics | Validation outcomes, authorization, business rules, side effects, data meaning, and error behavior | Request-level integration/contract tests against the application and representative persisted state |

A stable route does not prove a stable response. A stable OpenAPI document does not prove stable business behavior. No single check proves all three.

## What this package owns

The package owns deterministic version-to-view routing and route lifecycle behavior:

- A registered route is mapped to the implementation selected for the requested version.
- Unchanged generated routes can be inherited independently.
- Explicit removals create a version boundary instead of silently falling forward.
- Route-matrix checks make additions, removals, and implementation changes reviewable.
- `VersionedDefaultRouter` adds a per-version API root and DRF format-suffix routes without changing the route registry's ownership of effective registrations.

The package does **not** convert serializers, rewrite response payloads, infer whether a business behavior is backward-compatible, or guarantee that every existing client accepts a schema change.

Use version-specific serializers and views when the representation or behavior intentionally differs. Keep compatibility aliases and transitional validation in application-owned serializers when a migration requires them.

## Guardrail 1: route contract

After importing all endpoint modules and building the URL configuration, snapshot the effective route matrix:

```python
from django_api_versioning.testing import assert_version_matrix

assert_version_matrix(
    snapshot=".contracts/version-matrix.json",
    strict=True,
)
```

Create or deliberately refresh a baseline with `update=True` in a developer-controlled change. CI must use `strict=True` without `update=True`.

This catches route drift: a route disappearing, appearing in an unintended version, or resolving to a different registered implementation. It does not inspect serialized response data.

## Guardrail 2: representation contract

Generate an OpenAPI document for every supported version with a schema tool such as drf-spectacular. Keep a reviewed baseline for each version and compare a candidate only with the baseline for that same version.

The package provides `assert_schema_snapshot()` for deterministic JSON snapshots when a consumer already has a schema mapping. The repository's executable consumer example uses drf-spectacular to generate YAML documents and oasdiff to identify structural breaking changes. Neither tool is a package runtime dependency.

Recommended CI sequence:

1. Generate one candidate schema for every supported API version.
2. Validate each document and fail on unresolved schema-generation warnings.
3. Verify that paths and operations belonging to other versions are absent.
4. Compare each candidate with its own released baseline using `oasdiff breaking`.
5. Review additive changes and update a baseline only through an explicit, reviewed change.

An exact snapshot and a semantic OpenAPI diff answer different questions. A byte-for-byte snapshot detects any document drift; oasdiff classifies structural compatibility changes. The latter should not be treated as proof of runtime behavior.

See [Versioned OpenAPI contract integration](versioned-openapi-contract.md) and the executable [OpenAPI consumer example](../../examples/openapi_contract/README.md).

## Guardrail 3: runtime semantics

Keep request-level tests for each supported version. At minimum, test representative cases for:

- Successful response fields, types, nullability, and values.
- Request validation, including required fields and error response bodies.
- Authentication, permissions, tenant isolation, and object-level access.
- Status codes and behavior when records are missing or state transitions fail.
- Side effects, persistence, idempotency, and relevant business invariants.
- Transitional aliases or compatibility behavior while old clients are being migrated.

Tests should use real DRF requests against the application rather than only calling serializers or view methods directly. For database-backed behavior, include the relevant persisted state and transaction boundaries.

A schema diff cannot detect a rule change such as “an order may now be cancelled after shipment” when the request and response schema remain identical. Add explicit tests for those rules.

## Change classification

### Often additive, but still verify client tolerance

- Adding a new endpoint.
- Adding an optional response field.
- Accepting an additional optional request field.
- Adding optional metadata.

An additional response field is not universally compatible: strict decoders or generated clients may reject unknown fields. Confirm the consumer contract before treating it as safe.

### Usually breaking

- Removing a response field or changing its type, format, nullability, or meaning.
- Making an optional request field required.
- Changing validation rules, status codes, or error response structure.
- Changing authorization requirements or observable business behavior.
- Removing an endpoint or changing its URL.
- Changing pagination, ordering, filtering, or side-effect semantics relied on by clients.

When a change is breaking, prefer a new API version with an explicit implementation and contract baseline. If the migration must happen inside an existing version, document the client assumptions, use a bounded compatibility period, and add request-level tests for both old and new client behavior.

## Release rule

Do not describe route inheritance, a green schema diff, or a successful test matrix as an unconditional backward-compatibility guarantee.

A release candidate should provide separate evidence for routing, representation, and runtime semantics. The application owner remains responsible for deciding which clients and behaviors must stay compatible, how long older versions remain supported, and when a version can be retired.
