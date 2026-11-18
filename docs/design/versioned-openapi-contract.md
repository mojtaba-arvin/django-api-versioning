# Version-specific OpenAPI contract workflow

**Status:** Accepted integration direction; implementation requires a runnable sample-project spike  
**Tracking:** [Issue #38](https://github.com/mojtaba-arvin/django-api-versioning/issues/38)  
**Depends on:** [VersionedRouter](https://github.com/mojtaba-arvin/django-api-versioning/pull/37)  
**Scope:** Optional development/CI tooling; no new runtime dependency

## Decision

Do not build an OpenAPI generator, serializer introspector, or semantic schema-diff engine in django-api-versioning.

Compose the tools that already own those responsibilities:

- DRF remains responsible for request handling and ViewSet behavior.
- VersionedRouter remains responsible for selecting the concrete route implementation and exposing its path version through the DRF adapter.
- drf-spectacular generates OpenAPI documents.
- oasdiff compares a committed released contract with the candidate contract in CI.
- django-api-versioning provides route-matrix evidence and a tested integration recipe.

The integration is opt-in. Django-only installations must not install DRF, drf-spectacular, or oasdiff as runtime dependencies.

## Why this is worth doing

A route matrix answers: "Does this URL exist for this API version, and which registered view owns it?"

An OpenAPI document answers a different question: "What request and response contract does this operation declare?"

A semantic diff answers: "Did that declared contract change in a way that can break a conforming client?"

None of these alone proves end-to-end compatibility. The product value is a reproducible workflow that connects all three without pretending that route presence proves serializer or response compatibility.

## Proposed consumer workflow

For each supported version, generate a separate, deterministic schema artifact using drf-spectacular's version-aware CLI or schema view. The precise command and settings must be verified in the sample project before this guide is promoted as a stable recipe.

Expected artifact layout:

```text
openapi/
  v1.yaml
  v2.yaml
  v3.yaml
```

A project should commit the schemas corresponding to versions it has released. For a candidate change, CI should:

1. Run `check_versions --fail-on-empty` and the project's strict route-matrix snapshot check.
2. Generate the candidate OpenAPI schema for every supported version.
3. Validate each generated schema and fail on unexpected generator warnings/errors according to the project's documented policy.
4. Compare each candidate schema with the corresponding released baseline using `oasdiff breaking`.
5. Publish the route-matrix diff and schema-diff output as CI artifacts or a PR summary.
6. Require an explicit review decision for accepted breaking changes; never silently rewrite released baselines.

The project must decide whether a new API version is allowed to contain breaking changes relative to the previous version. A reasonable default is to compare each version with its own last released snapshot, not blindly compare v2 against v1. A separate v1-to-v2 comparison can be useful as an intentional migration report, but it is not the same policy as protecting v1 consumers.

## Critical integration proof

The key technical risk is not invoking the CLI. It is ensuring schema generation sees the exact route set and the exact ViewSet implementation for the requested version.

The sample-project spike must prove all of the following:

- A V1-only custom action inherited into V2 appears in both version schemas.
- A V2 replacement of a V1 list/detail action contributes V2's serializer and operation metadata to the V2 schema, while V1's schema remains unchanged.
- Explicit version gaps do not leak operations into schemas for versions where the route is absent.
- Nested namespaces and `VersionedRouterVersioning` do not cause the schema generator to omit or misclassify operations.
- Repeated generation from the same commit and dependency lock produces byte-stable normalized schemas.
- A deliberate breaking request/response change is detected by the CI diff step; an additive change passes under the selected policy.

If drf-spectacular's version-selection mechanism cannot observe the router's namespace-based route selection during offline schema generation, do not patch private internals or mutate global URLconfs as a shortcut. First evaluate a small, documented schema-generation adapter or a separate URLconf per version. Any adapter must be deterministic, isolated between versions, safe for parallel generation, and covered by compatibility tests.

## Breaking-change policy

Use oasdiff's documented severity controls rather than treating every difference as a breaking change.

- Fail CI on definite breaking changes by default.
- Decide explicitly whether ambiguous warnings fail or require manual review.
- Keep an audited severity configuration in source control.
- Do not auto-approve or automatically update released snapshots.
- Explain that schema comparison cannot detect undocumented business semantics, authorization behavior, data migrations, side effects, or runtime response variations absent from the schema.

A breaking change may be intentional in a new API version. The gate should protect already released version contracts, while allowing an explicit, reviewed new-version contract to differ.

## Dependency boundaries

- `drf-spectacular`: optional development/CI dependency in the consumer project, never installed by the core package.
- `oasdiff`: external CLI or pinned CI action, never imported by Python package code.
- The package's runtime dependencies remain unchanged.
- The integration guide must state tested versions of Django, DRF, and drf-spectacular once the matrix is executed.

## Delivery stages

### Stage A — proof of concept

Build a small sample project with two ViewSet versions, one inherited custom action, one replaced action with different serializers, and an explicit version gap. Generate schemas and inspect normalized output.

### Stage B — compatibility and determinism

Run the sample across the supported Django/DRF matrix where drf-spectacular supports it. Test repeated generation, namespaces, warning handling, and route/schema correspondence.

### Stage C — CI reference workflow

Add a minimal reusable workflow example using committed baselines and oasdiff. Include one intentionally breaking fixture and one additive fixture to prove the gate's behavior.

### Stage D — adoption docs

Add a tutorial and troubleshooting section. Document the exact boundary between route-matrix checks, schema diffs, and runtime contract tests.

## Non-goals

- Building a proprietary OpenAPI schema format or generator.
- Adding drf-spectacular or oasdiff to package runtime dependencies.
- Claiming schema diffing proves business-level compatibility.
- Automatically bumping API or package versions based only on detected schema changes.
- Rewriting a released schema baseline without explicit review.

## Sources

- [DRF versioning](https://www.django-rest-framework.org/api-guide/versioning/)
- [drf-spectacular FAQ: versioned schemas](https://drf-spectacular.readthedocs.io/en/latest/faq.html#i-get-an-empty-schema-or-endpoints-are-missing)
- [drf-spectacular schema customization workflow](https://drf-spectacular.readthedocs.io/en/latest/customization.html)
- [oasdiff breaking-change checks](https://github.com/oasdiff/oasdiff/blob/main/docs/BREAKING-CHANGES.md)
