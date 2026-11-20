# Versioned OpenAPI contract example

This executable consumer project uses the public VersionedDefaultRouter API and
the same URLconf for runtime requests and drf-spectacular schema generation.
It verifies a per-version API root and DRF format-suffix URLs in addition to
the inherited route behavior.

The V1-only `legacy/export/` action is explicitly removed from V2. The verifier checks that it remains available and present in the V1 schema, while returning 404 and disappearing from the V2 schema.

Version lifecycle is separate from route removal: V1 is marked deprecated and emits RFC 9745 `Deprecation` plus RFC 8594 `Sunset` headers, while V2 remains active. To roll back the V2 endpoint removal before release, revert the `router.remove()` declaration; the V1 registration remains unchanged.

It deliberately tests:
- V1 and V2 implementations for the same list/detail routes.
- Different serializer contracts for the two versions.
- A V1-only custom action inherited by V2 because V2 does not redeclare it.
- API-root links scoped to the effective route set for each version.
- Unsuffixed and `.json` resource routes plus the suffixed API root.
- Explicit action removal reflected in runtime routes and the matching schema.

## Consumer-owned adapter boundary

All imports from django-api-versioning are isolated in
`contract_app/versioning.py`. Application ViewSets and function views do not
import the package, and the root URLconf calls only
`contract_app.versioning.get_urlpatterns()`.

This is the intended dependency boundary for a real consumer project. To
replace the package later, replace that adapter implementation with ordinary
Django `path()`/URLconf declarations or DRF `SimpleRouter` registrations.
The application view modules and root URLconf keep the same imports. The
fallback implementation must preserve the route contracts that the application
chooses to keep; it does not need to reproduce package-specific lifecycle or
route-inheritance behavior.

Do not import `django_api_versioning.registry` or package decorators from
business views. Keep package-specific registration, reversal, and lifecycle
integration inside the adapter.

## Package-level contract snapshots

The package also supplies dependency-free test helpers:

```python
from django_api_versioning.testing import (
    assert_schema_snapshot,
    assert_version_matrix,
)

# After importing the application's endpoint modules:
assert_version_matrix(
    snapshot=".contracts/route-matrix.json",
    strict=True,
)

# Generate and validate the document with drf-spectacular (or another tool),
# then compare one schema per API version:
assert_schema_snapshot(
    generated_openapi_schema,
    ".contracts/openapi-v1.json",
    strict=True,
)
```

Create or deliberately refresh a reviewed snapshot with `update=True` in a
developer-controlled workflow. CI must run with `strict=True` and without
`update=True`. Exact snapshots detect any schema drift; pair them with a
semantic breaking-change check such as `oasdiff breaking` when additive
changes should be allowed. These helpers do not replace request-level tests
for authorization, validation, business semantics, or error payloads.

## Install

From the repository root:

~~~bash
python -m pip install -e ".[dev]"
python -m pip install -r examples/openapi_contract/requirements.txt
~~~

The consumer example pins Django 5.2.19 (the current 5.2 LTS patch),
Django REST framework 3.18.3, and drf-spectacular 0.30.0. Upgrade these
versions deliberately and review regenerated schemas before changing the pins.

## Verify

~~~bash
cd examples/openapi_contract
python verify.py
~~~

The verifier makes real API requests, generates each schema in a fresh Django
process, validates OpenAPI, fails on schema warnings, checks version isolation,
checks serializer fields, compares two generations byte-for-byte, and requires
the output to match the committed per-version snapshots. CI then runs oasdiff
against each matching baseline. A deliberate fixture check confirms that an
optional response field is accepted while removing an operation is rejected.

You can also generate a schema directly:

~~~bash
python manage.py spectacular --api-version 1 --validate --file /tmp/openapi-v1.yaml
python manage.py spectacular --api-version 2 --validate --file /tmp/openapi-v2.yaml
~~~

To deliberately propose a new contract baseline after reviewing the generated
diff, run this from the example directory:

~~~bash
python generate_schemas.py --output-dir schemas
git diff -- schemas/
python verify.py
~~~

Do not refresh a baseline merely to make CI green. Review the API change,
classify it as additive or breaking, and update the migration/release notes
before committing the snapshot.

## Why VersionedRouterVersioning subclasses NamespaceVersioning

drf-spectacular explicitly recognizes DRF URLPathVersioning, NamespaceVersioning,
and AcceptHeaderVersioning when filtering operations by API version. A custom
class that only subclasses BaseVersioning is not recognized by that logic.

VersionedRouterVersioning obtains the active version from the resolver namespace
created by VersionedRouter. Subclassing NamespaceVersioning makes that contract
visible to schema tooling while preserving the package's namespace parsing and
reversal behavior. It does not change the public URL format or add a runtime
dependency on drf-spectacular.

## Released contract and breaking-change CI

The committed schemas under schemas/v1/ and schemas/v2/ are the example's
reviewed contract baselines. The verifier refuses unreviewed drift. Pull
requests generate candidate schemas in a temporary directory and compare each
version with its matching baseline using oasdiff breaking.

Schema diffs, route-matrix checks, and request-level behavior tests are separate
gates. The API root is excluded from OpenAPI; format-suffix URLs are alternate
forms of the same operations and do not create a second schema contract.
Neither drf-spectacular nor oasdiff is a runtime dependency.

## Endpoint-level OpenAPI deprecation

Configure the optional schema adapter in your DRF settings:

```python
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": (
        "django_api_versioning.spectacular.EndpointLifecycleAutoSchema"
    ),
}
```

The adapter requires drf-spectacular, which is already pinned by this consumer
example. It is not imported by the package root and is not a runtime dependency.
For a `VersionedRouter` operation, it uses Django's actual `ResolverMatch`,
the concrete HTTP method, and the router action map to locate the declaration.
If route identity is missing or ambiguous, the schema operation is left
unchanged.

For example, `router.set_lifecycle("products", "product-list", version=1,
action="list", deprecated_at="2030-01-01T00:00:00Z")` marks only the V1 list
operation as deprecated. Sibling actions and other API versions remain
unchanged. The executable verifier runs this isolated scenario in addition
to the unchanged committed baseline checks.

The adapter also supports DRF function/class views registered through
`@endpoint` when they use `URLPathVersioning`. The decorator attaches its
logical endpoint identity to the view class; drf-spectacular supplies the
concrete schema version in `view.kwargs`, and the adapter resolves that pair
against the active registry. This path is used only when no
`ResolverMatch` exists and never falls back to generated path or operation ID
matching. The verifier covers a decorator endpoint deprecated in V1 but not
V2, alongside the VersionedRouter action-scope case.
