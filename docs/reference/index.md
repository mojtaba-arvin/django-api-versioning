# django-api-versioning reference

This page summarizes the public settings, endpoint decorator, DRF VersionedRouter integration, exceptions, and management tools for `django-api-versioning`. For exact route-generation semantics and framework boundaries, see the [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

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
| `API_VERSIONING_CHANNELS` | `["path"]` | Reserved compatibility setting. Values are validated but do not select routes; only URL-path routing is implemented. Non-default values are ignored and produce a warning. |
| `API_EFFECTIVE_VERSION_RESOLVER` | `None` | Reserved compatibility setting. A callable is validated but is not invoked by the current routing or lifecycle implementation; configuring one produces a warning. |

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
- The package's route selection is URL-path based. `API_VERSIONING_CHANNELS` and `API_EFFECTIVE_VERSION_RESOLVER` are reserved compatibility settings only; they are validated but do not alter route selection or request handling. Non-default values are logged so they are not mistaken for active features.

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

The initial integration supports `SimpleRouter`, not `DefaultRouter` API-root or format-suffix behavior. It does not transform serializers or response payloads. A route omitted from a later ViewSet remains inherited; explicit route removal is tracked in [Issue #39](https://github.com/mojtaba-arvin/django-api-versioning/issues/39). See the [Versioned DRF ViewSet guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/025-django-api-versioning-viewset-support-limitations/) for namespace, reversal, path-converter, and lifecycle details.

## Exceptions

| Exception | Raised when |
| --- | --- |
| `VersioningError` | Base exception for package versioning errors. |
| `VersionRangeError` | Endpoint arguments or configured version boundaries define an invalid range. |
| `InvalidVersionError` | A declared version exceeds `API_MAX_VERSION`. |
| `VersionTypeError` | A version value is not an integer; booleans are rejected. |
| `AmbiguousVersionError` | `api_reverse()` has multiple matches and no version was supplied. |
| `VersionMatrixError` | `assert_version_matrix()` detects a route-matrix difference or, with `strict=True`, a missing snapshot path, empty registry, or missing baseline. |

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

The root unit-test configuration and integration project use separate pytest configurations. See [contributing guidelines](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/CONTRIBUTING.md) for repository workflow and verification requirements.
