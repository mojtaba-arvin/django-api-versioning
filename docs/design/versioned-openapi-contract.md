# Versioned OpenAPI contract integration

**Status:** Executable consumer integration and CI validation are maintained in the repository mainline.  
**Runtime dependencies:** None added

## Decision

Use drf-spectacular to generate one OpenAPI document per concrete API version.
Use oasdiff as an optional CI tool to compare a candidate document with the
released contract for that same version.

The package owns route-to-view selection. drf-spectacular owns OpenAPI
introspection. oasdiff owns semantic comparison. The package will not build
a competing schema generator or schema-diff engine.

## Interoperability requirement

drf-spectacular's version filtering recognizes DRF's URLPathVersioning,
NamespaceVersioning, and AcceptHeaderVersioning families. It does not treat
an arbitrary BaseVersioning subclass as a supported versioning scheme.

VersionedRouterVersioning obtains the active version from the resolver
namespace created by VersionedRouter. It therefore subclasses
NamespaceVersioning while preserving package-specific namespace parsing and
URL reversal overrides. This exposes the existing namespace contract to schema
tooling without changing runtime URL structure.

## Executable consumer example

The example in `examples/openapi_contract/` registers two ViewSets
through the public `VersionedDefaultRouter` API. V2 replaces list/detail
implementations and serializers, while a V1-only custom action remains
inherited into V2. Runtime verification also covers each version's API root,
the `.json` resource and root suffixes, and explicit removal.

Its verifier exercises real API requests and generates each schema in a fresh
process. It checks route isolation, serializer fields, custom-action visibility,
root/suffix routing, schema validation, byte-for-byte determinism, and equality
with committed per-version baselines. CI runs oasdiff against each matching
baseline. The API root is intentionally excluded from OpenAPI; format-suffix
routes resolve to the same operations and do not define separate contracts.

## Released contract workflow

After reviewing generated output, consumers should keep immutable snapshots per
stable API version (for example, schemas/v1/openapi.yaml and
schemas/v2/openapi.yaml). Candidate generation must never overwrite a released
baseline during pull-request validation. The executable sample commits its
reviewed V1 and V2 baselines under examples/openapi_contract/schemas/.

The CI sequence is:

1. Run route-matrix and request-level API tests.
2. Generate one schema for each supported API version.
3. Validate schemas and fail on unresolved introspection warnings.
4. Compare each candidate only with the matching released version baseline.
5. Run oasdiff breaking with `--fail-on WARN`; both definite breaking changes (`ERR`) and potential breaking changes (`WARN`) block the contract gate. Review and justify any exception with a narrowly scoped severity override.
6. Review additive changes and update migration/release notes deliberately.

A new API version starts with its own baseline. A breaking change to an existing
stable version must not be accepted merely because a new version was also added.

## Limits

Route compatibility, representation compatibility, and runtime semantic
compatibility are separate evidence categories:

- The route matrix proves which registered view handles each URL/version.
- OpenAPI snapshots and oasdiff detect documented request/response contract drift.
- Request-level application tests verify validation, authorization, error bodies,
  persistence, side effects, and business invariants.

A schema diff cannot prove business semantics, authorization behavior, database
invariants, or runtime response conformance. A route-matrix snapshot cannot prove
that the selected view returns the expected representation. Keep request-level
tests for representative responses, permissions, errors, and edge cases.

The package intentionally does not infer semantic compatibility or transform
serializers and responses. Consumers should follow the [API compatibility
boundaries](api-compatibility-boundaries.md) guidance and retain a reviewed
runtime contract suite.

Neither drf-spectacular nor oasdiff is a package runtime dependency.
