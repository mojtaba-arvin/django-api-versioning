# django-api-versioning reference

This page summarizes the public settings, endpoint decorator, DRF `VersionedRouter` and `VersionedDefaultRouter` integrations, request-version negotiation, exceptions, and management tools for `django-api-versioning`. The 1.4.0 release adds `VersionedDefaultRouter` with version-specific API roots and optional DRF format-suffix routes, alongside the existing `VersionedRouter`, multi-transport request negotiation, endpoint lifecycle APIs, and schema snapshot helper. The executable OpenAPI consumer example, its `oasdiff` gate, and the consumer-owned adapter example remain repository-level adoption and validation resources, not package runtime dependencies. For an end-to-end view of startup registration, request negotiation, Django resolution, DRF dispatch, and lifecycle processing, see the [runtime architecture and request-flow diagram](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/runtime-architecture.md). For exact routing semantics and compatibility boundaries, see the [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Installation

~~~bash title="terminal"
pip install django-api-versioning
~~~

Requires Python `>=3.10` and Django `>=4.2`. Django REST Framework is optional; ViewSet projects must install a DRF release compatible with their Django version (3.17.2 for Django 4.2, 3.18.3 for Django 5.2/6.0/6.1). The configured compatibility environments are defined in [`tox.ini`](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/tox.ini); check [commit-specific workflow runs](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/compatibility.yml) for actual results. The matrix does not cover every possible Python/Django combination.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `API_BASE_PATH` | `"api/v{version}/"` | Prefix template for versioned routes. Must contain exactly one plain `{version}` field and must not start with `/`. |
| `API_MIN_VERSION` | `1` | Lowest version that can be registered. Segment declarations below it register no routes; lower explicit versions are skipped with a warning. |
| `API_MAX_VERSION` | `1` | Highest route version. A declaration above it raises `InvalidVersionError`. |
| `API_VERSION_LIFECYCLE` | `{}` | Per-version lifecycle metadata consumed by `LifecycleMiddleware`. |
| `API_VERSIONING_CHANNELS` | `["path"]` | Deprecated/inert compatibility setting. It does not select a transport or act as a fallback list. Use `API_VERSIONING_SCHEME` to select the request-version transport. |
| `API_EFFECTIVE_VERSION_RESOLVER` | `None` | Reserved policy hook. It is not invoked by the current routing or lifecycle implementation; tenant-pinned version policy is not included in the negotiation middleware. |


### Request-version negotiation (available since 1.3.0)

The package provides an optional `VersionNegotiationMiddleware`. It selects one of the following schemes per deployment, then rewrites the internal path before Django resolves the actual registered callback:

| Setting | Default | Description |
| --- | --- | --- |
| `API_VERSIONING_SCHEME` | `"path"` | One of `path`, `header`, `query`, or `hostname`. This is a single choice, not a fallback chain. |
| `API_VERSIONING_HEADER` | `"Accept-Version"` | Header name used in header mode. Also accepts DRF's `Accept: application/json; version=2` parameter. |
| `API_VERSIONING_QUERY_PARAMETER` | `"version"` | Single query parameter used in query mode. Repeated values are rejected. |
| `API_UNVERSIONED_BASE_PATH` | `"api/"` | Relative public path prefix used by non-path schemes. |
| `API_VERSIONING_HOSTS` | `{}` | Exact hostname-to-version map required for hostname mode. Hostnames still pass through Django's `ALLOWED_HOSTS` validation. |
| `API_DEFAULT_VERSION` | `None` | Optional default for header/query requests that omit a version; otherwise omission is 400. |

Install the middleware before middleware that depends on the resolved request path:

~~~python title="settings.py"
MIDDLEWARE = [
    "django_api_versioning.negotiation.VersionNegotiationMiddleware",
    # CommonMiddleware and other path-dependent middleware
    "django_api_versioning.lifecycle.LifecycleMiddleware",
]
~~~

Header/query inputs are ASCII decimal integers without a `v` prefix. Malformed or conflicting values return 400; unsupported versions and unmapped hosts return 406; missing endpoint registrations remain 404. Header mode emits `Vary` for the version header and `Accept`. Query mode requires the configured parameter in shared-cache keys. Header/hostname reversal returns an unversioned path; a URL alone cannot encode the selected header or host.

See the [request-negotiation contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/request-version-negotiation.md) for middleware ordering, dispatch, reversal, cache behavior, security boundaries, and deployment guidance.

Route-registration settings are read when the package settings and endpoint declarations are imported. Configure them before importing modules decorated with `@endpoint`; changing them later does not rebuild the registered URL patterns.

## `@endpoint` arguments

| Argument | Default | Purpose |
| --- | --- | --- |
| `postfix` | required | Relative resource path, for example `"invoices/<int:invoice_id>/"`. |
| `version` | `None` | Start of a forward segment. Registers from this version through `API_MAX_VERSION`. |
| `versions` | `None` | Explicit list of versions, or an inclusive list returned by `ver_range(start, end)`. |
| `app_name` | `None` | Optional path segment prepended to `postfix`; it is not a Django URL namespace. |
| `view_name` | `None` | Django URL pattern name used by `api_reverse()`. |

Use exactly one of `version` and `versions`, or neither for an unversioned route.

~~~python title="views.py"
from django_api_versioning import endpoint, ver_range

# These examples assume API_MAX_VERSION >= 4.
@endpoint("reports/", version=3)
def reports(request):
    ...

@endpoint("ranking/", versions=[2, 4])
def ranking(request):
    ...

@endpoint("legacy/", versions=ver_range(1, 3))
def legacy(request):
    ...

@endpoint("health/")
def health(request):
    ...
~~~

Each declaration above is an independent example. For the same route, a higher source version replaces a lower source version from that route version onward. See [registration semantics](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md#4-registration-semantics) for exact behavior.

## URL reversal

Give an endpoint a `view_name` and use the public `api_reverse()` helper to select a registered URL:

~~~python title="views.py"
from django_api_versioning import endpoint

@endpoint("invoices/<int:invoice_id>/", version=2, view_name="invoice-detail")
def invoice_detail(request, invoice_id):
    ...
~~~

~~~python title="application code"
from django_api_versioning import api_reverse

url = api_reverse("invoice-detail", version=2, invoice_id=42)
~~~

When a name is registered for multiple versions, pass `version`. If multiple routes match and no version is supplied, `AmbiguousVersionError` is raised. `api_reverse()` supports path-converter and regex-backed package routes, but it is not a general replacement for Django's `reverse()`.

## Validation and collisions

- Supplying both `version` and `versions` raises `VersionRangeError`.
- Version values and the configured minimum/maximum must be integers; booleans are rejected.
- A version above `API_MAX_VERSION` raises `InvalidVersionError`.
- A segment declaration below `API_MIN_VERSION` registers no routes after a warning. Explicit versions below the minimum are skipped individually.
- On a route collision, the higher integer `source_version` wins. If source versions are equal, or either is `None`, the last registration wins.
- The `@endpoint` decorator still does not accept DRF ViewSet classes directly. Use `VersionedRouter` for complete version-aware ViewSet route generation; it preserves DRF-generated patterns and provides a `VersionedRouterVersioning` adapter for `request.version` and version-aware reversal. A configured `as_view(actions)` callable remains available for an individual route.
- The package supports path, header, query-parameter, and exact-hostname request-version negotiation through one selected `API_VERSIONING_SCHEME` per deployment. It does not combine schemes or infer tenant policy; `API_VERSIONING_CHANNELS` remains deprecated and inert.

### Register a configured ViewSet callable

A DRF ViewSet class needs an action map. For example, `ItemViewSet.as_view({"get": "list"})` creates a configured callable that can be registered for an individual route:

~~~python title="views.py"
from rest_framework.viewsets import ViewSet

from django_api_versioning import endpoint


class ItemViewSet(ViewSet):
    def list(self, request):
        ...


list_items_v1 = endpoint(
    "items/",
    version=1,
    view_name="item-list",
)(ItemViewSet.as_view({"get": "list"}))
~~~

This registers only the configured route. It does not create the full list/detail/custom-action route set that a DRF router provides. For version-aware ViewSet routing, use the `VersionedRouter` section below.

### VersionedRouter for DRF ViewSets

`VersionedRouter` delegates route generation to DRF's `SimpleRouter`, then registers each generated URLPattern with the package registry:

~~~python title="project/urls.py"
from django_api_versioning.routers import VersionedRouter
from orders.views import OrderViewSetV1, OrderViewSetV2

router = VersionedRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")
router.register("orders", OrderViewSetV2, version=2, basename="order")

urlpatterns = router.urls
~~~

Configure `VersionedRouterVersioning` as DRF's default versioning class before importing ViewSet modules (or set `versioning_class = VersionedRouterVersioning` on selected ViewSets):

~~~python title="settings.py"
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "django_api_versioning.routers.VersionedRouterVersioning"
    ),
}
~~~

A later ViewSet replaces only matching generated routes. A custom action that exists only in V1 remains inherited in V2 and later versions unless replaced. Explicit `versions=[1, 3]` creates a real gap: the route is not registered in V2 and returns 404.

The router constructor's `app_name` is Django URL resolver metadata; it is unrelated to the `app_name` path-segment argument accepted by `@endpoint`. If multiple router instances are mounted in one URLconf, include each under a distinct outer namespace so their per-version namespaces do not collide.

`VersionedRouter` targets DRF's `SimpleRouter` and does not itself add an API root or format-suffix patterns. `VersionedDefaultRouter`, added in 1.4.0, provides a version-specific API root and optional DRF format-suffix routes on top of the same registry. Its API root lists only effective list routes for that version after inheritance and explicit removals. It is not a full drop-in reimplementation of every DRF `DefaultRouter` extension. Neither router transforms serializers or response payloads. A route omitted from a later ViewSet remains inherited; declare removal explicitly with `VersionedRouter.remove()` (or `remove_endpoint()` for decorator endpoints). Removed routes are absent from runtime routing and URL reversal at the removal boundary, while earlier versions remain available; a later source declaration can explicitly reintroduce the route. See the [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md#4-registration-semantics), [Versioned DRF router design](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/versioned-drf-router.md), and [API compatibility boundaries](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/api-compatibility-boundaries.md) for details.

### VersionedDefaultRouter (available since 1.4.0)

When a DRF ViewSet API also needs a browsable API root and `.json` routes, use the new router from the current repository source:

~~~python title="project/urls.py"
from django_api_versioning.routers import VersionedDefaultRouter
from orders.views import OrderViewSetV1, OrderViewSetV2

router = VersionedDefaultRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")
router.register("orders", OrderViewSetV2, version=2, basename="order")
urlpatterns = router.urls
~~~

Each version receives its own root (for example, `/api/v1/` and `/api/v2/`). Its links reflect the effective route set for that version, not raw registrations. Format suffixes are enabled by default; disable the API root with `include_root_view=False` or suffixes with `include_format_suffixes=False`. The suffixed root uses `/api/v2/.json`. DRF passes the suffix as the `format` keyword argument to the action, so custom actions should accept `*args, **kwargs` or an explicit `format` parameter. This integration is available in package version 1.4.0 and later.

## Explicit endpoint removal (available since 1.2.0)

Use `remove_endpoint()` to stop decorator-based forward inheritance at an inclusive version boundary, while keeping earlier versions available:

~~~python title="views.py"
from django_api_versioning import endpoint, remove_endpoint

@endpoint("orders/", version=1, view_name="orders-list")
def orders_v1(request):
    ...

remove_endpoint("orders/", from_version=3)
~~~

For a generated DRF ViewSet action, use `VersionedRouter.remove()` with the route name generated from the registration basename and action:

~~~python title="urls.py"
router.remove("orders", "order-archive", from_version=3)
~~~

The removal boundary is inclusive. Removed routes return 404 and cannot be reversed in removed versions; a later declaration with a strictly higher source version can reintroduce the route. Removal does not emit 410 or lifecycle headers. See the [canonical removal contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md#4-registration-semantics) and [endpoint-removal design](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/endpoint-removal.md).

## Contract snapshots

`assert_schema_snapshot()` is available in the package since `1.3.0`. It is defined in
`django_api_versioning.testing`. It compares a generated OpenAPI mapping with
a deterministic, reviewed JSON snapshot without adding DRF, OpenAPI, YAML, or
oasdiff to package runtime dependencies.

~~~python title="tests/test_api_contract.py"
from django_api_versioning.testing import assert_schema_snapshot

# Generate and validate this mapping with the project's chosen OpenAPI tool.
assert_schema_snapshot(
    generated_schema,
    ".contracts/openapi-v2.json",
    strict=True,
)
~~~

Create or deliberately refresh a reviewed baseline with `update=True`; CI
must use `strict=True` without update mode. Exact snapshots fail on any
schema drift. Pair them with a semantic breaking-change tool such as
`oasdiff breaking` when additive changes should be allowed. Snapshot
comparison does not prove business semantics, authorization, validation, or
error-payload compatibility; keep real request-level tests for those
contracts.

## Public import stability

The supported import surface is intentionally narrower than every importable
module. The package root's `__all__` is the authoritative root-export list.
Documented module-level imports (lifecycle middleware, request negotiation,
exceptions, testing helpers, and the optional DRF/schema integrations) are
classified and checked by the single executable inventory in
[`tests/test_public_api_contracts.py`](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/tests/test_public_api_contracts.py).

The `django_api_versioning.registry` facade and its submodules, route-state
records and snapshots, resolver/projection functions, and other implementation
helpers are internal. Their current importability does not make them stable
consumer APIs. Do not depend on them from application code. A change to a
documented import path requires an explicit compatibility and deprecation
decision; optional integrations remain optional and raise actionable
`ImportError` messages when their dependencies are not installed.

## Exceptions

| Exception | Raised when |
| --- | --- |
| `VersioningError` | Base exception for package versioning errors. |
| `VersionRangeError` | Endpoint arguments or configured version boundaries define an invalid range. |
| `InvalidVersionError` | A declared version exceeds `API_MAX_VERSION`. |
| `VersionTypeError` | A version value is not an integer; booleans are rejected. |
| `AmbiguousVersionError` | `api_reverse()` has multiple matches and no version was supplied. |
| `VersionMatrixError` | `assert_version_matrix()` detects a route-matrix difference or, with `strict=True`, a missing snapshot path, empty registry, or missing baseline. |
| `ContractSnapshotError` | `assert_schema_snapshot()` receives an invalid schema mapping, cannot serialize it deterministically, or detects a missing/unreviewed contract snapshot. |

## Route-matrix tools

### Inspect routes with `check_versions`

`check_versions` loads the project's root URLconf, prints the registered logical endpoint matrix, and warns about missing versions within each endpoint's registered span. Loading the URLconf executes imports of view modules referenced by it, so a forgotten view import can be detected.

Use `--fail-on-empty` in CI to fail when no package endpoints were registered, including routes registered through `VersionedRouter`:

~~~bash
python manage.py check_versions --fail-on-empty
~~~

This catches a completely empty registry; it cannot infer which individual endpoints your application intended to register. The command reports routes that were registered; it does not decide whether a gap violates your API contract.

The following output is generated by the package's executable `website_check_versions` fixture:

~~~text title="check_versions output"
$ python manage.py check_versions
users/:
  v1           → users_list_v1
  v2           → users_list_v2
  v3           → users_list_v2
  v4           → users_list_v2
~~~

### Guard changes with `assert_version_matrix()`

Import endpoint modules before building or comparing the matrix, then add a test such as:

~~~python title="tests/test_versions.py"
from django_api_versioning.testing import assert_version_matrix


def test_version_matrix():
    assert_version_matrix(snapshot=".version_matrix.json", strict=True)
~~~

For backward compatibility, omitting the snapshot keeps the historical no-op behavior, and a missing snapshot is created by default. In CI, use `strict=True` to require a non-empty route matrix and an existing committed snapshot. Create or intentionally refresh the snapshot once with `update=True`, review and commit the generated JSON file, then keep `update=True` out of the committed test. With `strict=True`, an empty registry or missing snapshot fails, preventing accidental loss of imports or the baseline from silently passing CI.

To create the initial snapshot, import the modules that contain your `@endpoint` declarations in the same Django process, then call:

~~~python
from myproject.api import views  # Import the module(s) that register endpoints.
from django_api_versioning.testing import assert_version_matrix

assert_version_matrix(snapshot=".version_matrix.json", update=True)
~~~

Replace `myproject.api.views` with the actual module(s) in your project. Commit the generated JSON file and use the strict assertion shown above in regular CI runs.

## API lifecycle

Add `LifecycleMiddleware` and configure `API_VERSION_LIFECYCLE` to emit deprecation and sunset metadata or reject requests after a sunset date:

~~~python title="settings.py"
API_VERSION_LIFECYCLE = {
    1: {
        "status": "deprecated",
        "deprecated_at": "2026-01-01T00:00:00+00:00",
        "sunset": "2027-06-30",
    },
    2: {"status": "active"},
}

MIDDLEWARE = [
    "django_api_versioning.lifecycle.LifecycleMiddleware",
    # ... your other middleware
]
~~~

For a deprecated version with valid lifecycle dates, the middleware emits the date-valued RFC 9745 `Deprecation` field and the RFC 8594 `Sunset` HTTP date. When both dates are configured, `sunset` must not be earlier than `deprecated_at`. When the configured sunset date is in the past, it returns `410 Gone`. A retired entry must define `sunset`; the sunset date—not the status label by itself—is what triggers the expired-version response. Until that date passes, a retired version is still served and its responses carry the `Sunset` header (plus `Deprecation` when `deprecated_at` is set).

See [API lifecycle behavior in the routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md#12-version-lifecycle-headers) and the [deprecation guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/018-deprecate-django-api-versioning-routes-sunset-headers/).

### Endpoint-level lifecycle and OpenAPI (available since 1.2.0)

Use `set_endpoint_lifecycle()` for a concrete endpoint version, or
`VersionedRouter.set_lifecycle()` for a generated ViewSet route. These
declarations can scope headers to an HTTP method or DRF action without
retiring the whole API version. Endpoint-level past-Sunset metadata is
headers-only; version-wide past-Sunset policy retains its existing 410
behavior.

Projects that use drf-spectacular can opt into
`django_api_versioning.spectacular.EndpointLifecycleAutoSchema` through
`REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"]`. It maps the exact registered
operation to OpenAPI `deprecated: true` and supports both VersionedRouter
and DRF decorator endpoints. drf-spectacular remains an optional dependency;
the adapter fails closed when operation identity is unavailable or ambiguous.

See [endpoint-level lifecycle and OpenAPI](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md#13-endpoint-level-lifecycle-and-openapi)
and the [executable consumer contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/examples/openapi_contract/README.md).

## Management commands

### `check_versions`

Prints the registered logical route matrix and warns about gaps within an endpoint's registered span.

### `migrate_endpoints`

For projects upgrading from the 0.2.0 `forward`/`backward` decorator flags, the command previews supported source edits by default. Use `--diff` to inspect a deterministic unified diff with file-relative paths and line-level context; neither preview mode modifies files.

~~~bash title="migrate_endpoints"
$ python manage.py migrate_endpoints --dry-run
~~~

For a line-level unified diff, use:

~~~bash title="unified diff preview"
python manage.py migrate_endpoints --diff
~~~

Only after reviewing the proposed changes and confirming the migration:

~~~bash title="apply reviewed migration"
python manage.py migrate_endpoints --write
~~~

Writes replace each changed file atomically and preserve its permission bits. Atomicity is per file, not transactional across the directory: if a later replacement fails, earlier files that were successfully replaced remain changed. The command reports the failed file and every earlier file already updated; the failing file remains intact and its temporary file is cleaned up. Preview with `--diff` first, and use a clean version-control state or backup before applying changes.

The command reports unsupported legacy-looking decorator occurrences with their relative path, line number, and reason instead of silently treating them as if no migration were needed. Dynamic expressions, positional legacy versions, duplicate or conflicting flags, keyword expansions, comments inside a decorator, and files that cannot be parsed are not rewritten and require manual migration. This command rewrites Python decorator syntax only: it does not migrate database schemas or prove equivalent routing behavior. Verify the route matrix and representative request behavior after applying it.

## Development

~~~bash title="terminal"
pip install -e ".[dev]"
pre-commit install
python -m pytest tests
python -m pytest integration_test_project
tox run-parallel -p auto
~~~

The root unit-test configuration and integration project use separate pytest configurations. The release quality contract documents the five 100% mutation domains, independent 95% line/branch thresholds, full tox matrix, adversarial checks, consumer contracts, and artifact requirements; see [quality and release gates](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/quality/release-gates.md). See [contributing guidelines](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/CONTRIBUTING.md) for repository workflow and verification requirements.
