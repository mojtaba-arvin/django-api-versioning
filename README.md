# Django API Versioning

[![PyPI version](https://badge.fury.io/py/django-api-versioning.svg)](https://badge.fury.io/py/django-api-versioning)
[![PyPI Downloads](https://img.shields.io/pypi/dm/django-api-versioning.svg)](https://pypi.org/project/django-api-versioning/)
[![Build Status](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/tests.yml/badge.svg)](https://github.com/mojtaba-arvin/django-api-versioning/actions)
[![Django versions](https://img.shields.io/badge/django-4.2%20%7C%205.x%20%7C%206.x-blue)](https://www.djangoproject.com/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-api-versioning.svg)](https://pypi.org/project/django-api-versioning/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Django API Versioning** is a Python package for version-aware endpoint registration in Django and Django REST Framework (DRF) projects.

Declare an endpoint with `@endpoint`, and the package generates its versioned URL patterns automatically. You define which view serves each version; the registry handles route registration and forward segment inheritance.

No manually maintained `path()` declarations for every API version. No need to duplicate unchanged endpoint registrations when a new version is introduced.

## "I need to change the response. v1 clients must not break."

You shipped v1 with a string amount. Now the team needs integer cents and an explicit currency code. Changing the existing view would break clients that still depend on the v1 response contract.

With `django-api-versioning`, register a separate implementation for v2:

```python
# apps/orders/views.py

from django.http import JsonResponse
from django_api_versioning import endpoint


@endpoint("orders/", version=1)
def order_list_v1(request):
    return JsonResponse({"total": "19.99"})


@endpoint("orders/", version=2)
def order_list_v2(request):
    return JsonResponse({
        "total": 1999,
        "currency": "USD",
    })
```

Both declarations are registered when `apps.orders.views` is imported. Make sure endpoint modules are imported before the package's URL patterns are loaded (see Quick Start below).

With `API_MAX_VERSION = 5`, the resulting routes are:

```text
GET /api/v1/orders/  →  {"total": "19.99"}
GET /api/v2/orders/  →  {"total": 1999, "currency": "USD"}
GET /api/v3/orders/  →  {"total": 1999, "currency": "USD"}
GET /api/v4/orders/  →  {"total": 1999, "currency": "USD"}
GET /api/v5/orders/  →  {"total": 1999, "currency": "USD"}
```

**Why do v3, v4, and v5 use the v2 implementation?**

Because `version=2` declares a forward segment: the view serves v2 through `API_MAX_VERSION`, unless a later declaration for the same route takes over.

When v4 needs its own response contract, add another declaration:

```python
@endpoint("orders/", version=4)
def order_list_v4(request):
    return JsonResponse({
        "total": 1999,
        "currency": "USD",
        "status": "confirmed",
    })
```

The resulting mapping becomes:

| Route version | Implementation |
| --- | --- |
| v1 | `order_list_v1` |
| v2 | `order_list_v2` |
| v3 | `order_list_v2` |
| v4 | `order_list_v4` |
| v5 | `order_list_v4` |

The v2 implementation continues serving v2 and v3. The v4 implementation serves v4 and v5.

The function name `order_list_v2` is a convention for readers. The segment is defined by `version=2`, not by the function name.

- **Package:** [django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/)
- **Source code:** [mojtaba-arvin/django-api-versioning](https://github.com/mojtaba-arvin/django-api-versioning)
- **License:** MIT

## Why not just use DRF's built-in versioning?

Django REST Framework provides several versioning schemes:

- `URLPathVersioning`
- `NamespaceVersioning`
- `AcceptHeaderVersioning`
- `QueryParameterVersioning`
- `HostNameVersioning`

These mechanisms identify the requested API version according to a configured strategy. They do not, by themselves, define a separate view implementation for every version or generate a complete set of version-specific endpoint registrations.

DRF intentionally leaves the application-specific behavior to the developer.

For example, you can use DRF's version information inside a shared view:

```python
def order_list(request):
    if request.version == "1":
        return ...

    if request.version == "2":
        return ...
```

Or you can maintain separate URL patterns and connect each version to its own view manually.

`django-api-versioning` addresses the endpoint-registration part of that problem: declare the view for a source version, and let the registry generate the corresponding versioned routes.

| Concern | DRF versioning mechanisms | `django-api-versioning` |
| --- | --- | --- |
| Identify a requested version | Yes, according to the configured scheme | Routes requests to the registered version-specific view |
| Register version-specific URL patterns | Application configuration required | Generated from endpoint declarations |
| Map different versions to different views | Application code or URL configuration | `@endpoint` declarations |
| Reuse an implementation for later versions | Application-managed | Forward segment inheritance |
| Register explicit version sets | Application-managed | `versions=[...]` |
| Register bounded version ranges | Application-managed | `ver_range()` |
| Register unversioned endpoints in the same registry | Application-managed | Supported |
| Lifecycle headers and sunset enforcement | Application-managed | `LifecycleMiddleware` |
| Inspect registered route matrix | Application-managed | `check_versions` |
| Guard routing changes with a snapshot | Application-managed | `assert_version_matrix()` |
| Reverse a registered route by API version | Django URL reversal | `api_reverse()` |
| Work without DRF | Django-native schemes and URL configuration | Yes |

The two approaches solve different parts of the problem. You can continue using DRF for serializers, authentication, permissions, request parsing, and response handling while using this package for version-aware endpoint registration.

**Important:** The package does not automatically set `request.version`. Its registry maps generated URL patterns to views. If your application also needs DRF's `request.version`, configure the appropriate DRF versioning scheme separately.

## Installation

Install [Django API Versioning](https://pypi.org/project/django-api-versioning/) from PyPI:

```bash
pip install django-api-versioning
```

Requirements:

- Python >= 3.10
- Django >= 4.2

Django REST Framework is optional. The package can be used with Django-native function-based and class-based views without installing DRF.

## Quick Start

### 1. Configure Django settings

Add the package to `INSTALLED_APPS` and configure the supported version range:

```python
# settings.py

INSTALLED_APPS = [
    # ... your other apps
    "django_api_versioning",
]

API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 3
```

`API_BASE_PATH` must contain the `{version}` placeholder.

The default values for `API_MIN_VERSION` and `API_MAX_VERSION` are both `1`. Set `API_MAX_VERSION` to the highest route version your project intends to register.

### 2. Define your API endpoints

Create a view and decorate it with `@endpoint`.

For example, in your application's `views.py`:

```python
# your_app/views.py

from rest_framework.response import Response
from rest_framework.views import APIView

from django_api_versioning import endpoint


@endpoint(
    "invoices/<int:invoice_id>/",
    version=2,
    view_name="invoice-detail",
)
class InvoiceDetailView(APIView):
    def get(self, request, invoice_id):
        return Response({
            "id": invoice_id,
            "status": "paid",
        })
```

The decorator registers the endpoint when this module is imported.

### 3. Import endpoint modules and include generated URLs

Django does not automatically import every application's `views.py` module.

You must import every module containing `@endpoint` declarations before importing the package's generated URL patterns.

In your project's root URL configuration:

```python
# project/urls.py

from django.urls import include, path

from your_app import views  # noqa: F401


from your_app import views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    # ... your other URL patterns
    path("", include(api_urlpatterns)),
]
```

Replace `your_app` with the actual Python package name of your Django application.

If endpoint declarations are spread across multiple modules, import each module before importing `api_urlpatterns`.

The imported modules do not need to be referenced elsewhere. Their imports execute the decorators and register the endpoints.

**Import order matters:**

1. Import modules containing `@endpoint` declarations.
2. Import `api_urlpatterns`.
3. Include the generated patterns in your root URL configuration.

You do not need to write individual `path()` entries for versioned endpoints. The package generates those patterns from the registered declarations.

With the example above, the endpoint is available for v2 and v3:

```text
GET /api/v1/invoices/42/  →  404
GET /api/v2/invoices/42/  →  {"id": 42, "status": "paid"}
GET /api/v3/invoices/42/  →  {"id": 42, "status": "paid"}
```

The endpoint was introduced in v2, so it is not registered for v1.

Path converters such as `<int:pk>` and `<slug:name>` are supported by the generated Django `path()` patterns.

## Before and after

Consider an API with 150 endpoints and five supported versions.

Some endpoints change their implementation between versions. Others remain unchanged and should continue using their existing implementation.

### Without `django-api-versioning`

You maintain the URL patterns for every endpoint and version manually:

```python
# urls.py

from django.urls import path
from . import views

urlpatterns = [
    path("api/v1/users/", views.user_list_v1),
    path("api/v2/users/", views.user_list_v2),
    path("api/v3/users/", views.user_list_v2),
    path("api/v4/users/", views.user_list_v4),
    path("api/v5/users/", views.user_list_v4),

    path("api/v1/orders/", views.order_list),
    path("api/v2/orders/", views.order_list),
    path("api/v3/orders/", views.order_list),
    path("api/v4/orders/", views.order_list),
    path("api/v5/orders/", views.order_list),

    # Repeat for the remaining endpoints and versions.
]
```

If all 150 endpoints are registered for all five versions, that means 750 manually maintained URL patterns.

Every new API version requires reviewing the URL configuration, even when many endpoints have not changed.

### With `django-api-versioning`

Declare the implementation at each change point:

```python
# apps/users/views.py

from django_api_versioning import endpoint


@endpoint("users/", version=1)
def user_list_v1(request):
    ...


@endpoint("users/", version=2)
def user_list_v2(request):
    ...


@endpoint("users/", version=4)
def user_list_v4(request):
    ...


# apps/orders/views.py

@endpoint("orders/", version=1)
def order_list(request):
    ...
```

The user endpoint has three implementation declarations. The order endpoint has one declaration because its implementation does not change across the configured versions.

With `API_MAX_VERSION = 5`, the package generates the versioned routes from these declarations.

Import the endpoint modules and include the generated patterns once:

```python
# project/urls.py

from django.urls import include, path

from apps.users import views as _user_views  # noqa: F401
from apps.orders import views as _order_views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    # ... your existing URLs
    path("", include(api_urlpatterns)),
]
```

### What changes?

| Concern | Manual URL configuration | `django-api-versioning` |
| --- | --- | --- |
| Add a new endpoint implementation in v2 | Add a view and URL pattern | Add one `@endpoint` declaration |
| Keep an unchanged endpoint available in v3 | Add another URL pattern | No additional declaration |
| Change an endpoint in v4 | Update URL configuration and route mappings | Add a v4 declaration |
| Inspect which view serves a version | Review URL configuration | Run `check_versions` |
| Organize endpoint ownership | Often centralized in `urls.py` | Declarations can live with their views |
| URL configuration | One entry per endpoint/version combination | One generated URL include |

For the example above, the user endpoint has three declarations because its implementation changes at v1, v2, and v4. The order endpoint has one declaration because it remains unchanged.

The package reduces repeated route declarations. It does not eliminate the need to implement and test behavior changes.

### Inspect the generated routes

Run:

```bash
python manage.py check_versions
```

The command prints the registered route matrix and warns about missing versions within the configured range.

For the example above, the mapping is conceptually:

```text
api/v1/users/:
  v1           → user_list_v1

api/v2/users/:
  v2           → user_list_v2

api/v3/users/:
  v3           → user_list_v2

api/v4/users/:
  v4           → user_list_v4

api/v5/users/:
  v5           → user_list_v4

api/v1/orders/:
  v1           → order_list

api/v2/orders/:
  v2           → order_list

api/v3/orders/:
  v3           → order_list

api/v4/orders/:
  v4           → order_list

api/v5/orders/:
  v5           → order_list
```

The command reports registered routes and gaps. A gap warning is a routing observation; whether a missing version is a problem depends on the intended API contract.

### Add a new version without changing unchanged endpoints

Suppose v6 introduces a new users response contract, while orders remain unchanged.

Add a new declaration:

```python
@endpoint("users/", version=6)
def user_list_v6(request):
    ...
```

The v6 implementation serves v6 and subsequent configured versions. Earlier user versions keep their existing mappings. The order endpoint requires no new declaration.

## Four endpoint registration patterns

Each pattern represents a different API evolution requirement.

### 1. Segment — introduce an endpoint in v3

```python
from django.http import JsonResponse
from django_api_versioning import endpoint


@endpoint("reports/", version=3)
def report_list(request):
    return JsonResponse({"reports": []})
```

With `API_MAX_VERSION = 5`:

```text
GET /api/v1/reports/  →  404
GET /api/v2/reports/  →  404
GET /api/v3/reports/  →  {"reports": []}
GET /api/v4/reports/  →  {"reports": []}
GET /api/v5/reports/  →  {"reports": []}
```

The endpoint did not exist in v1 or v2. Its v3 implementation is reused for later versions until another declaration takes over.

### 2. Explicit set — v2 and v4 only

```python
from django.http import JsonResponse
from django_api_versioning import endpoint


@endpoint("ranking/", versions=[2, 4])
def ranking(request):
    return JsonResponse({"algorithm": "new"})
```

The endpoint is registered only for the specified versions:

```text
GET /api/v1/ranking/  →  404
GET /api/v2/ranking/  →  {"algorithm": "new"}
GET /api/v3/ranking/  →  404
GET /api/v4/ranking/  →  {"algorithm": "new"}
GET /api/v5/ranking/  →  404
```

Use explicit versions when an implementation should be registered only for selected, potentially non-contiguous versions.

### 3. Bounded range — v1 through v3

```python
from django.http import JsonResponse
from django_api_versioning import endpoint, ver_range


@endpoint("legacy/", versions=ver_range(1, 3))
def legacy_endpoint(request):
    return JsonResponse({"deprecated": True})
```

```text
GET /api/v1/legacy/  →  {"deprecated": true}
GET /api/v2/legacy/  →  {"deprecated": true}
GET /api/v3/legacy/  →  {"deprecated": true}
GET /api/v4/legacy/  →  404
GET /api/v5/legacy/  →  404
```

`ver_range(start, end)` returns an inclusive list:

```python
ver_range(1, 3) == [1, 2, 3]
```

Use it when an endpoint should stop being registered after a particular version.

### 4. Unversioned — no version prefix

```python
from django.http import JsonResponse
from django_api_versioning import endpoint


@endpoint("health/")
def health_check(request):
    return JsonResponse({"status": "ok"})
```

The endpoint is registered without the versioned `API_BASE_PATH` prefix.

With the root URL include shown in Quick Start:

```text
GET /health/  →  {"status": "ok"}
```

Unversioned routes are registered at the include prefix, not under the versioned base path.

If you need unversioned and versioned routes under a shared `/api/` prefix, configure the base path and URL include accordingly. For example:

```python
# settings.py
API_BASE_PATH = "v{version}/"
```

```python
# project/urls.py
urlpatterns = [
    path("api/", include(api_urlpatterns)),
]
```

This produces versioned paths such as `/api/v1/...` and an unversioned path such as `/api/health/`.

## How segments resolve

Consider two declarations for the same route:

```python
from django.http import JsonResponse
from django_api_versioning import endpoint


@endpoint("orders/", version=1)
def order_list_v1(request):
    return JsonResponse({"version": 1})


@endpoint("orders/", version=3)
def order_list_v3(request):
    return JsonResponse({"version": 3})
```

With `API_MAX_VERSION = 5`, the resulting mapping is:

```text
GET /api/v1/orders/  →  {"version": 1}   # order_list_v1
GET /api/v2/orders/  →  {"version": 1}   # order_list_v1
GET /api/v3/orders/  →  {"version": 3}   # order_list_v3
GET /api/v4/orders/  →  {"version": 3}   # order_list_v3
GET /api/v5/orders/  →  {"version": 3}   # order_list_v3
```

The v3 declaration takes over from v3 onward. The v1 implementation continues serving v1 and v2.

This is route-level implementation inheritance. It does not imply Python class inheritance or automatic serializer compatibility.

## Reliability tools

### `check_versions` — inspect the registered matrix

```bash
python manage.py check_versions
```

Prints registered routes, their route versions, and the associated callback names. It also warns about missing versions in the configured range.

Use it to inspect the routing result after adding or changing endpoint declarations.

### `assert_version_matrix` — guard routing changes in CI

The package provides a snapshot utility for detecting unintended changes to the registered route matrix.

```python
# tests/test_versions.py

from django_api_versioning.testing import assert_version_matrix


def test_version_matrix():
    assert_version_matrix(snapshot=".version_matrix.json")
```

If the current matrix differs from the snapshot, `assert_version_matrix()` raises `VersionMatrixError` with a diff.

To accept an intentional routing change, update the snapshot:

```python
assert_version_matrix(
    snapshot=".version_matrix.json",
    update=True,
)
```

The snapshot is created automatically if it does not exist.

**Import requirement:** Build and compare the matrix only after all modules containing `@endpoint` declarations have been imported. The registry is populated at module import time.

The matrix checks routing structure only. It does not validate response schemas, serializer behavior, business logic, or backward compatibility of API contracts. Keep request-level and contract tests for those guarantees.

### `api_reverse` — reverse a registered route by version

Use `api_reverse()` to reverse a route registered by this package:

```python
from django_api_versioning import api_reverse


url = api_reverse("order-list", version=2)
```

When the same `view_name` is registered for multiple versions, pass the version to select the exact route.

If only one route is registered for the name, the version can be omitted:

```python
url = api_reverse("health-check")
```

If multiple routes match and no version is supplied, the function raises `AmbiguousVersionError` rather than silently selecting one.

To use URL reversal, give the endpoint a `view_name`:

```python
@endpoint(
    "orders/",
    version=2,
    view_name="order-list",
)
def order_list_v2(request):
    ...
```

`api_reverse()` is intended for package-registered routes. It is not a general replacement for Django's `reverse()`.

### Deprecation and sunset headers

Configure lifecycle metadata in Django settings:

```python
# settings.py

API_VERSION_LIFECYCLE = {
    1: {"status": "retired", "sunset": "2025-01-01"},
    2: {"status": "deprecated", "sunset": "2027-06-01"},
    3: {"status": "active"},
}

MIDDLEWARE = [
    "django_api_versioning.lifecycle.LifecycleMiddleware",
    # ... your other middleware
]
```

For a version configured as deprecated with a future sunset date, the middleware adds:

```http
Deprecation: true
Sunset: Tue, 01 Jun 2027 00:00:00 GMT
```

When a configured sunset date is in the past, the middleware returns:

```http
HTTP/1.1 410 Gone
```

The expired sunset date triggers the `410 Gone` response regardless of the lifecycle status string.

The middleware attempts to identify the request version in this order:

1. `request.version`
2. `resolver_match.kwargs["version"]`
3. The version in the request path, extracted using `API_BASE_PATH`

This allows the middleware to identify versions from the package's static versioned URL paths even when `request.version` is not set.

**Standards note:** The current implementation emits the legacy boolean value `Deprecation: true`. It does not implement the date-valued structured field defined by [RFC 9745](https://www.rfc-editor.org/rfc/rfc9745). The `Sunset` header follows the HTTP-date format specified by [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594).

## Configuration reference

### Django settings

| Setting | Default | Description |
| --- | --- | --- |
| `API_BASE_PATH` | `"api/v{version}/"` | Base path template for versioned routes. Must contain `{version}`. |
| `API_MIN_VERSION` | `1` | Lowest valid route version. |
| `API_MAX_VERSION` | `1` | Highest valid route version. |
| `API_VERSION_LIFECYCLE` | `{}` | Per-version lifecycle metadata. |
| `API_VERSIONING_CHANNELS` | `["path"]` | Validated channel configuration; not currently used by the route registry. |
| `API_EFFECTIVE_VERSION_RESOLVER` | `None` | Validated callable configuration; not currently used for route selection. |

`API_BASE_PATH` is normalized to end with `/` if necessary.

`API_MIN_VERSION` and `API_MAX_VERSION` must be integers, and the minimum cannot exceed the maximum. Boolean values are not accepted as version integers.

### `@endpoint` arguments

| Argument | Type | Default | Purpose |
| --- | --- | --- | --- |
| `postfix` (positional) | `str` | Required | Resource path, e.g. `"users/"` or `"users/<int:pk>/"`. |
| `version` | `int \| None` | `None` | Registers a forward segment starting at this version. |
| `versions` | `list[int] \| None` | `None` | Registers only the explicitly specified versions. |
| `app_name` | `str \| None` | `None` | Optional path segment for grouping. |
| `view_name` | `str \| None` | `None` | URL name used by `api_reverse()`. |

Examples:

```python
@endpoint("users/", version=1)
def user_list_v1(request):
    ...


@endpoint("users/", versions=[1, 3])
def user_list_v1_and_v3(request):
    ...


@endpoint("users/", versions=ver_range(1, 3))
def user_list_v1_to_v3(request):
    ...


@endpoint("health/")
def health_check(request):
    ...
```

**Registration rules:**

- `version` and `versions` are mutually exclusive. Providing both raises `VersionRangeError`.
- If neither is provided, the endpoint is registered as unversioned.
- `version=N` registers the endpoint for versions `N` through `API_MAX_VERSION`.
- `versions=[...]` registers the endpoint only for the listed versions.
- `ver_range(start, end)` returns an inclusive list of integer versions.
- Version identifiers must be integers. Boolean values are rejected.
- A version greater than `API_MAX_VERSION` raises `InvalidVersionError`.
- A source version below `API_MIN_VERSION` produces a warning and no routes are registered for that declaration.
- Explicit versions below `API_MIN_VERSION` are warned about and skipped.

**Collision resolution:**

When two declarations produce the same complete route string:

1. The declaration with the higher integer `source_version` takes precedence.
2. If the source versions are equal, the last registration wins.
3. If either source version is `None`, the last registration wins.

Avoid relying on import order as an implicit policy when multiple modules declare the same route and source version.

## Supported views and ViewSets

The package supports Django function-based views and supported class-based views, including Django REST Framework `APIView` and generic views.

For class-based views, the registry calls `as_view()` on the class when creating the URL pattern.

A generic view must implement the HTTP handlers required by its registered route.

### ViewSets

A DRF `ViewSet` class cannot be passed directly to `@endpoint` as a normal class-based view. Its `as_view()` method requires an action mapping, while the package invokes `as_view()` without one.

Use DRF routers for standard ViewSet resource routing.

The package does not automatically generate router-style ViewSet routes.

## Known limitations and scope

`django-api-versioning` focuses on version-aware endpoint registration and routing.

It does not:

- Automatically make response schemas backward-compatible.
- Select serializers based on a request version.
- Replace DRF authentication or permission classes.
- Replace DRF routers for ViewSet resource routing.
- Automatically set `request.version`.
- Use `API_VERSIONING_CHANNELS` to select routes.
- Use `API_EFFECTIVE_VERSION_RESOLVER` for tenant-specific route selection.
- Validate response payload compatibility through route-matrix checks.

Your application remains responsible for API contract design, serializer selection, authentication, permissions, business logic, and request-level compatibility tests.

## Migration from 0.2.0

Version 0.3.0 replaced the previous forward/backward inheritance flags model with segment-based registration.

The current `@endpoint` signature accepts:

```python
endpoint(
    postfix,
    version=None,
    versions=None,
    app_name=None,
    view_name=None,
)
```

The `forward` and `backward` arguments are not part of the current decorator API. The old `API_FORWARD_INHERITANCE` setting is also not part of the current configuration.

### Common migration patterns

| Previous intent | Current declaration |
| --- | --- |
| Start a forward segment at v3 | `@endpoint("x/", version=3)` |
| Register only v3 | `@endpoint("x/", versions=[3])` |
| Register v1 through v3 explicitly | `@endpoint("x/", versions=ver_range(1, 3))` |
| Register only v2 and v4 | `@endpoint("x/", versions=[2, 4])` |

The exact replacement depends on the routing behavior your application relied on before upgrading. In particular, do not assume that every old combination of `forward` and `backward` flags has an identical one-line replacement.

### Automated migration suggestions

The package includes a `migrate_endpoints` management command:

```bash
python manage.py migrate_endpoints --dry-run
python manage.py migrate_endpoints
```

The command scans Python files for `@endpoint` declarations containing legacy `forward` or `backward` arguments and suggests or applies textual replacements.

**Review the output before accepting it.** The command uses source-text matching and rewriting; it is not an AST-based semantic migration tool. It cannot guarantee that every rewritten declaration preserves the application's intended routing behavior.

After migration:

1. Review every changed decorator.
2. Inspect the generated route matrix with `check_versions`.
3. Update routing snapshots intentionally.
4. Run the complete test suite.
5. Add request-level tests for every API version whose behavior changed.

## Requirements and compatibility

The package requires:

- Python >= 3.10
- Django >= 4.2

Django REST Framework is optional.

For the current compatibility and CI verification status, see the [GitHub Actions workflows](https://github.com/mojtaba-arvin/django-api-versioning/actions).

## Contributing

Contributions, bug reports, and documentation improvements are welcome.

### Setup

```bash
python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
pre-commit install
```

### Running tests

```bash
pytest
pre-commit run --all-files
```

### Docker

The `Dockerfile` parameterizes Python via `PYTHON_VERSION` (default: `3.15`)
and delegates execution to `entrypoint.sh`.

```bash
# Build the Docker image
docker build -t dapi .

# Run the test suite
docker run --rm dapi

# Run pre-commit checks followed by the test suite
docker run --rm -e RUN_PRE_COMMIT=true dapi

# Build and run with a specific Python version
docker build --build-arg PYTHON_VERSION=3.15 -t dapi:py315 .
docker run --rm dapi:py315
```

### Releasing

1. Update the `version` in `pyproject.toml` and document the release in `CHANGELOG.md`.
2. Commit and push the release commit to `main`.
3. Create and push a matching version tag:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

Pushing a `v*` tag triggers GitHub Actions to build the package, validate
the distribution with `twine check`, and publish it to PyPI using
the `PYPI_API_TOKEN` repository secret.

### Reporting issues

When reporting an issue, include:

- Python and Django versions.
- The package version and relevant settings.
- The `@endpoint` declarations involved.
- Expected and actual URL patterns.
- A minimal example that reproduces the behavior.

## License

Released under the [MIT License](LICENSE).
