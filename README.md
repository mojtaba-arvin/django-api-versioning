<p align="center">
  <a href="https://mojtaba-arvin.github.io/django-api-versioning/">
    <img src="https://raw.githubusercontent.com/mojtaba-arvin/django-api-versioning/main/website/public/favicon.svg" alt="Django API Versioning logo" width="64" height="64">
  </a>
</p>

# Django API Versioning for Django and Django REST Framework

[![PyPI version](https://img.shields.io/pypi/v/django-api-versioning?logo=pypi&logoColor=white)](https://pypi.org/project/django-api-versioning/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-api-versioning.svg)](https://pypi.org/project/django-api-versioning/)
[![Django versions](https://img.shields.io/badge/django-4.2%20%7C%205.2%20%7C%206.0%20%7C%206.1-blue)](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/tox.ini)
[![Python tests](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/tests.yml/badge.svg)](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/LICENSE)

**django-api-versioning** is a Python package for declarative, URL-path-based API versioning in Django and Django REST Framework (DRF).

Register a view with `@endpoint`. The package generates versioned Django URL patterns and carries an implementation forward to later API versions until a newer declaration replaces it. You maintain views at the points where an endpoint's behavior changes instead of repeating URL patterns for every version.

- **Install:** `pip install django-api-versioning`
- **Requires:** Python 3.10+, Django 4.2+
- **DRF:** optional; Django-native views work without it.

[Website and interactive playground](https://mojtaba-arvin.github.io/django-api-versioning/) · [API reference](https://mojtaba-arvin.github.io/django-api-versioning/reference/) · [PyPI](https://pypi.org/project/django-api-versioning/)

## Install

```bash
pip install django-api-versioning
```

The package installs Django as a runtime dependency. Install Django REST Framework separately only when your application uses DRF:

```bash
pip install djangorestframework
```

## Quick start

This complete example uses Django-native views; it does not require Django REST Framework.

### 1. Configure Django

Add the package to `INSTALLED_APPS` and set the highest API version your project serves:

```python
# settings.py

INSTALLED_APPS = [
    # ... your Django apps
    "django_api_versioning",
]

API_MIN_VERSION = 1
API_MAX_VERSION = 3
# API_BASE_PATH defaults to "api/v{version}/"
```

### 2. Declare the endpoint implementations

Put the views in a module such as `orders/views.py`:

```python
from django.http import JsonResponse

from django_api_versioning import endpoint


@endpoint("orders/", version=1, view_name="order-list")
def order_list_v1(request):
    return JsonResponse({"total": "19.99"})


@endpoint("orders/", version=2, view_name="order-list")
def order_list_v2(request):
    return JsonResponse({"total": 1999, "currency": "USD"})
```

A declaration with `version=1` registers that implementation from v1 through `API_MAX_VERSION`. The v2 declaration takes over from v2 onward.

### 3. Include the generated URL patterns

Import every module containing `@endpoint` declarations before importing the package URL patterns:

```python
# project/urls.py

from django.urls import include, path

from orders import views as _order_views  # noqa: F401
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

With the default `API_BASE_PATH`, these requests resolve as follows:

| Request | Registered view |
| --- | --- |
| `GET /api/v1/orders/` | `order_list_v1` |
| `GET /api/v2/orders/` | `order_list_v2` |
| `GET /api/v3/orders/` | `order_list_v2` |

The v2 view is reused for v3 because no later declaration replaces it. This is route-registration inheritance: it does not mean that response schemas or business behavior are automatically backward-compatible.

### 4. Inspect the registered routes

Run the management command after Django has loaded the URL configuration:

```bash
python manage.py check_versions
```

It prints the logical endpoint matrix and warns about gaps between an endpoint's first and last registered versions.

## How version registration works

The `@endpoint` decorator supports three registration modes:

| Declaration | Routes created |
| --- | --- |
| `@endpoint("orders/", version=2)` | v2 through `API_MAX_VERSION` |
| `@endpoint("orders/", versions=[1, 3, 5])` | Only v1, v3, and v5 |
| `@endpoint("health/")` | One unversioned route |

For a bounded inclusive range, use `ver_range()`:

```python
from django_api_versioning import endpoint, ver_range


@endpoint("legacy-reports/", versions=ver_range(1, 3))
def legacy_reports(request):
    ...
```

A later declaration for the same route takes over from its source version. For example, a v3 declaration replaces a v1 implementation for v3 and later versions while leaving v1 and v2 unchanged.

Other capabilities include:

- `app_name` for grouping route paths.
- `view_name` and `api_reverse()` for reversing a registered route by version.
- `assert_version_matrix()` for detecting unintended route-matrix changes in tests.
- `LifecycleMiddleware` for deprecation and sunset response headers and expired-version enforcement.

See the [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md) for exact URL construction, import order, collision precedence, validation rules, and edge cases.

## Django REST Framework integration

DRF is optional. The package can register Django function-based views, Django class-based views, DRF `APIView` classes, and DRF generic views.

The package and DRF's built-in versioning solve different problems:

| Django API Versioning | DRF versioning schemes |
| --- | --- |
| Registers distinct views against generated versioned URL patterns | Determines a request version using a configured scheme |
| Carries a route implementation forward and lets a later declaration replace it | Exposes version information such as `request.version` when configured |
| Does not automatically set `request.version` | Does not generate this package's endpoint registration matrix |

You can use DRF for serializers, authentication, permissions, request parsing, and responses while using this package to register version-specific views. The package does **not** automatically populate `request.version`; configure and test that behavior separately when your application needs it.

### ViewSet boundary

A DRF `ViewSet` or `ModelViewSet` class cannot be passed directly to `@endpoint`, because its `as_view()` method requires an action mapping. You can register a configured callable for a specific route:

```python
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
```

This registers the configured callable for that route; it does not generate the full set of router-managed list, detail, and custom-action routes. Use DRF's `DefaultRouter` or `SimpleRouter` when you need standard ViewSet routing. See [ViewSet support and limitations](https://mojtaba-arvin.github.io/django-api-versioning/articles/025-django-api-versioning-viewset-support-limitations/).

## Requirements and compatibility

The published package declares:

- Python `>=3.10`
- Django `>=4.2`
- No runtime dependency on Django REST Framework

The configured CI matrix contains specific combinations across Python 3.10–3.15 and Django 4.2, 5.2, 6.0, and 6.1. It does not test every possible Python/Django combination. The authoritative environment list is in [`tox.ini`](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/tox.ini); check [GitHub Actions](https://github.com/mojtaba-arvin/django-api-versioning/actions) for results tied to the exact commit you use. A configured environment is not, by itself, evidence that a given commit passed.

## Upgrading to 1.0.0

The 1.0.0 release tightened API lifecycle configuration and changed the `Deprecation` response header format.

When using `API_VERSION_LIFECYCLE`:

- Every entry must have a `status` of `active`, `deprecated`, or `retired`.
- A deprecated version must define `deprecated_at` as an ISO 8601 date or datetime.
- A retired version must define a `sunset` date.
- The `Deprecation` header is now the RFC 9745 date-valued Structured Field (for example, `Deprecation: @1767225600`), not the legacy `Deprecation: true` value. Update clients or tests that expected a boolean string.

For the full migration steps and release history, see the [1.0.0 changelog](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/CHANGELOG.md#100---2026-11-16).

For projects migrating from the older 0.2.0 `forward`/`backward` decorator flags, `migrate_endpoints` defaults to a non-writing preview. Review the output first; use `--write` only after confirming the suggested changes:

```bash
python manage.py migrate_endpoints --dry-run
# Review the proposed edits before applying them.
python manage.py migrate_endpoints --write
```

The command only rewrites supported literal forms. It cannot prove semantic equivalence; inspect the resulting route matrix and test affected requests. See the [routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md) and [changelog](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/CHANGELOG.md).

## Documentation and guides

- **Website:** [Django API Versioning](https://mojtaba-arvin.github.io/django-api-versioning/) — overview, interactive playground, lifecycle demonstration, and guides.
- **Reference:** [online API reference](https://mojtaba-arvin.github.io/django-api-versioning/reference/) · [Markdown source](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/index.md).
- **Routing contract:** [implementation-backed behavior and limitations](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).
- **Getting started:** [what the package does](https://mojtaba-arvin.github.io/django-api-versioning/articles/022-django-api-versioning-how-does-it-work/) · [installation and configuration](https://mojtaba-arvin.github.io/django-api-versioning/articles/023-django-api-versioning-installation-configuration/).
- **DRF integration:** [version negotiation vs. endpoint registration](https://mojtaba-arvin.github.io/django-api-versioning/articles/013-drf-version-negotiation-vs-endpoint-registration/) · [ViewSet support](https://mojtaba-arvin.github.io/django-api-versioning/articles/025-django-api-versioning-viewset-support-limitations/).
- **Routing and API evolution:** [reverse URL lookup](https://mojtaba-arvin.github.io/django-api-versioning/articles/017-reverse-url-lookup-versioned-api-endpoints-django/) · [backward compatibility](https://mojtaba-arvin.github.io/django-api-versioning/articles/019-preserve-backward-compatibility-changing-django-api-endpoints/) · [API lifecycle and sunset](https://mojtaba-arvin.github.io/django-api-versioning/articles/018-deprecate-django-api-versioning-routes-sunset-headers/).
- **Compatibility:** [Python and Django compatibility guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/024-django-api-versioning-supported-django-python-versions/).
- **Documentation map:** [canonical Markdown sources and ownership](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/README.md).

## Contributing

Bug reports, corrections, and pull requests are welcome. Read the [contribution guidelines](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/CONTRIBUTING.md) and [security policy](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/SECURITY.md).

## License

Released under the [MIT License](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/LICENSE).
