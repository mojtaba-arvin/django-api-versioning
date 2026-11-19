<p align="center">
  <a href="https://mojtaba-arvin.github.io/django-api-versioning/">
    <img src="https://raw.githubusercontent.com/mojtaba-arvin/django-api-versioning/main/website/public/favicon.svg" alt="Django API Versioning logo" width="64" height="64">
  </a>
</p>

# Django API Versioning

[![PyPI version](https://img.shields.io/pypi/v/django-api-versioning?logo=pypi&logoColor=white)](https://pypi.org/project/django-api-versioning/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-api-versioning.svg)](https://pypi.org/project/django-api-versioning/)
[![Django versions](https://img.shields.io/badge/django-4.2%20%7C%205.2%20%7C%206.0%20%7C%206.1-blue)](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/tox.ini)
[![Python tests](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/tests.yml/badge.svg)](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/LICENSE)

**Version your Django API by endpoint, not by duplicating URL patterns.** Register a view once; unchanged routes carry forward to later API versions, and a newer declaration replaces the implementation from that version onward.

[Explore Django API Versioning — documentation, examples, and interactive playground](https://mojtaba-arvin.github.io/django-api-versioning/) · [Install django-api-versioning from PyPI](https://pypi.org/project/django-api-versioning/)

## See how it works

Install the package and Django REST Framework:

```bash
pip install django-api-versioning djangorestframework
```

Declare only the versions where an endpoint's behavior changes:

```python
from rest_framework.response import Response
from rest_framework.views import APIView

from django_api_versioning import endpoint


@endpoint("orders/", version=1, view_name="order-list")
class OrderListV1(APIView):
    def get(self, request):
        return Response({"total": "19.99"})


@endpoint("orders/", version=2, view_name="order-list")
class OrderListV2(APIView):
    def get(self, request):
        return Response({"total": 1999, "currency": "USD"})
```

With `API_MAX_VERSION = 3`, the generated routes are:

| Request | View |
| --- | --- |
| `GET /api/v1/orders/` | `OrderListV1` |
| `GET /api/v2/orders/` | `OrderListV2` |
| `GET /api/v3/orders/` | `OrderListV2` |

The v1 view serves v1 until another declaration replaces it. The v2 view then serves v2 and v3. **You write a new view when the endpoint changes—not another copy of every unchanged route.**

For the complete setup, including Django settings and URL configuration, see the [Django API Versioning getting-started guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/022-django-api-versioning-how-does-it-work/).

## What problem does it solve?

In a growing API, only some endpoints change between releases. Manually maintaining a separate URL configuration for every version can repeat registrations and obscure which implementation handles each version.

Django API Versioning makes that mapping explicit with `@endpoint`:

- **Forward route inheritance:** `version=1` registers the endpoint from v1 through `API_MAX_VERSION`.
- **Version-specific replacement:** a v2 declaration takes over from v2 onward; earlier versions retain the v1 implementation.
- **Explicit registration:** use `versions=[...]` or `ver_range(...)` when an endpoint should exist only in selected versions.
- **Visibility:** inspect the generated route matrix with `python manage.py check_versions --fail-on-empty` and guard it with `assert_version_matrix(snapshot=".version_matrix.json", strict=True)`.

This is inheritance of route registrations, not automatic backward compatibility. Your application remains responsible for response schemas, business behavior, and compatibility tests.

**Current main (unreleased on PyPI):** Explicit endpoint removal is implemented in the repository but is not included in the published `1.1.0` artifact. Use `remove_endpoint("orders/", from_version=3)` for decorator endpoints or `VersionedRouter.remove(prefix, route_name, from_version=...)` for one generated DRF action. Earlier versions retain the route, removed versions return 404, and a later source declaration can explicitly reintroduce it. These APIs are documented in the [endpoint-removal contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/endpoint-removal.md).

## Why use it with Django REST Framework?

DRF already provides request-version identification and ViewSet route generation. Django API Versioning adds the missing connection between those capabilities: **mapping each concrete API version to the correct ViewSet implementation while inheriting unchanged routes independently**.

For Django-native function-based and class-based views, use `@endpoint`. For DRF `ViewSet` and `ModelViewSet` classes, use the optional `VersionedRouter`. It delegates route generation to DRF's `SimpleRouter`, preserving standard actions, custom `@action` routes, lookup behavior, and action-level configuration.

The optional `VersionedRouterVersioning` adapter exposes the selected version as DRF's `request.version` and keeps `reverse_action()` and hyperlinked serializers version-aware. DRF remains optional for projects that use only Django-native views. For those projects, install just:

```bash
pip install django-api-versioning
```

## Quick configuration

Add the package (and DRF, if used) to `INSTALLED_APPS` and configure the supported version range:

```python
# settings.py
INSTALLED_APPS = [
    "rest_framework",  # omit when using Django-native views only
    "django_api_versioning",
]

API_MIN_VERSION = 1
API_MAX_VERSION = 3
# API_BASE_PATH defaults to "api/v{version}/"
```

Import modules containing endpoint declarations before including the generated patterns:

```python
# project/urls.py
from django.urls import include, path

from orders import views as _order_views  # noqa: F401
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

Run the route-matrix check:

```bash
python manage.py check_versions
```

## Registration options

| Declaration | Routes created |
| --- | --- |
| `@endpoint("orders/", version=2)` | v2 through `API_MAX_VERSION` |
| `@endpoint("orders/", versions=[1, 3, 5])` | Only v1, v3, and v5 |
| `@endpoint("health/")` | One unversioned route |

For an inclusive range, use `ver_range(1, 3)`. Other APIs include `api_reverse()` for version-aware URL reversal and `assert_version_matrix()` for regression tests.

See the [versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md) for exact URL construction, import order, collision precedence, validation, and edge cases.

## Versioned DRF ViewSets

Use `VersionedRouter` when you want DRF's normal ViewSet workflow with version-aware implementation dispatch:

```python
# settings.py — configure before importing ViewSet modules
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "django_api_versioning.routers.VersionedRouterVersioning"
    ),
}
```

```python
# project/urls.py
from django_api_versioning.routers import VersionedRouter
from orders.views import OrderViewSetV1, OrderViewSetV2

router = VersionedRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")
router.register("orders", OrderViewSetV2, version=2, basename="order")

urlpatterns = router.urls
```

With `API_MAX_VERSION = 3`, the routes are served at `/api/v1/orders/`, `/api/v2/orders/`, and `/api/v3/orders/`. V2 replaces only the generated routes it declares. If a custom action exists in V1 but is not redeclared in V2, that action remains inherited in v2 and v3 while list/detail can use V2.

For endpoints that should exist only in selected versions, pass `versions=[1, 3]`; v2 remains a 404. The router also supports `trailing_slash=False` and `use_regex_path=False` for Django path converters.

The adapter is required when ViewSets need `request.version`, `reverse_action()`, or hyperlinked serializer support. You can configure it globally through `REST_FRAMEWORK` as shown above, or set `versioning_class = VersionedRouterVersioning` on selected ViewSets.

**Scope:** the initial integration supports DRF `SimpleRouter`; it does not claim `DefaultRouter` API-root or format-suffix parity. It does not transform serializers or response payloads. A route omitted from a later ViewSet remains inherited; remove it explicitly with `VersionedRouter.remove()` (available on current main, not in the published `1.1.0` artifact). Header/query/tenant negotiation is not enabled by the reserved settings and remains a separate design decision.

For DRF installation, use a version compatible with your Django release:
```bash
# Django 4.2 compatibility
pip install "djangorestframework>=3.17.2,<3.18"

# Django 5.2, 6.0, or 6.1
pip install "djangorestframework>=3.18.3,<3.19"
```

See the [Versioned DRF ViewSet guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/025-django-api-versioning-viewset-support-limitations/) for route inheritance, reversal, namespaces, and the exact integration boundary.

For the repository's executable OpenAPI workflow, see the [versioned OpenAPI contract example](https://github.com/mojtaba-arvin/django-api-versioning/tree/main/examples/openapi_contract). This consumer example and its `oasdiff` CI gate were added after the published release; they are repository-level tooling, not part of the package wheel, and do not make drf-spectacular or oasdiff runtime dependencies.

## Requirements

- Python 3.10+
- Django 4.2+ (retained for compatibility with existing 1.x installations)
- Django REST Framework is optional.

**For new deployments, use a currently supported Django release, preferably Django 5.2 LTS or later.** Django 4.2 reached the end of extended support on 7 April 2026. It remains in this package's compatibility matrix for existing projects, but no longer receives Django security fixes. See [Django's supported versions](https://www.djangoproject.com/download/#supported-versions).

The configured CI matrix covers selected combinations of Python 3.10–3.15 and Django 4.2, 5.2, 6.0, and 6.1. DRF is tested against versions supported by each upstream combination: DRF 3.17.2 on Django 4.2, and DRF 3.18.x on Django 5.2, 6.0, and 6.1. DRF 3.18 dropped Django 4.2, so these lines are deliberately pinned separately rather than relying on an unbounded latest version.

See [tox.ini](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/tox.ini) for configured environments and [GitHub Actions](https://github.com/mojtaba-arvin/django-api-versioning/actions) for results tied to a specific commit.

## Upgrading to 1.0.0

Version 1.0.0 tightened API lifecycle configuration and changed the `Deprecation` response header format. If you use `API_VERSION_LIFECYCLE`:

- Every entry must have a `status` of `active`, `deprecated`, or `retired`.
- A deprecated version must define `deprecated_at` as an ISO 8601 date or datetime.
- A retired version must define a `sunset` date.
- The `Deprecation` header now uses the RFC 9745 date-valued Structured Field (for example, `Deprecation: @1767225600`), not the legacy `Deprecation: true` value.

For migration steps, see the [1.0.0 changelog](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/CHANGELOG.md#100---2026-11-16).

## Documentation

- [Django API Versioning documentation and interactive playground](https://mojtaba-arvin.github.io/django-api-versioning/) — overview, examples, lifecycle demonstration, and guides.
- [API reference](https://mojtaba-arvin.github.io/django-api-versioning/reference/) — settings, decorators, URL reversal, validation, and management commands.
- [Routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md) — implementation-backed behavior and limitations.
- [DRF integration guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/013-drf-version-negotiation-vs-endpoint-registration/).
- [Python and Django compatibility guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/024-django-api-versioning-supported-django-python-versions/).
- [Documentation source map](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/README.md).
- [Request version resolution decision](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/request-version-resolution.md) — why path-based handler selection remains the current contract and what a safe future negotiation design requires.

## Contributing

Bug reports, corrections, and pull requests are welcome. Read the [contribution guidelines](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/CONTRIBUTING.md) and [security policy](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/SECURITY.md).

## License

Released under the [MIT License](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/LICENSE).
