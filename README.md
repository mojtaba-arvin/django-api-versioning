# Django API Versioning

[![PyPI version](https://badge.fury.io/py/django-api-versioning.svg)](https://badge.fury.io/py/django-api-versioning)
[![PyPI Downloads](https://img.shields.io/pypi/dm/django-api-versioning.svg)](https://pypi.org/project/django-api-versioning/)
[![Build Status](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/tests.yml/badge.svg)](https://github.com/mojtaba-arvin/django-api-versioning/actions)
[![Django versions](https://img.shields.io/badge/django-5.2%20%7C%206.0%20%7C%206.1-blue)](https://www.djangoproject.com/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-api-versioning.svg)](https://pypi.org/project/django-api-versioning/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


**Django API Versioning** is a Python package for [API versioning in Django](https://github.com/mojtaba-arvin/django-api-versioning) and Django REST Framework (DRF) projects. Declare an endpoint once with `@endpoint`, and the registry registers every versioned URL for you — no manual `path()` in `urls.py`, no `if request.version` in views.

## "I need to change the response. v1 clients must not break."

You shipped v1 with a string amount. Now the team needs integer cents and an explicit currency code. Changing the view breaks every v1 client in production.

Two contracts, two decorators, **zero changes to `urls.py`**:

```python
# apps/orders/views.py
from django.http import JsonResponse
from django_api_versioning.decorators import endpoint

@endpoint("orders/", version=1)
def order_list_v1(request):
    return JsonResponse({"total": "19.99"})

@endpoint("orders/", version=2)
def order_list_v2(request):
    return JsonResponse({"total": 1999, "currency": "USD"})
```

That is the entire change. **Nothing goes in** `urls.py`. The package's URLconf — which you include once during setup — picks both routes up automatically.

```text
GET /api/v1/orders/  →  {"total": "19.99"}
GET /api/v2/orders/  →  {"total": 1999, "currency": "USD"}
GET /api/v3/orders/  →  {"total": 1999, "currency": "USD"}
GET /api/v4/orders/  →  {"total": 1999, "currency": "USD"}
GET /api/v5/orders/  →  {"total": 1999, "currency": "USD"}
```

**Why do v3, v4, v5 return the v2 body?** Because `version=2` declares a **segment**: the view serves v2 through `API_MAX_VERSION`, until you add another `@endpoint` for the same route. When v4 needs its own contract, add `@endpoint("orders/", version=4)`; until then, unchanged endpoints inherit automatically.

The function name `order_list_v2` is a convention for readers. The version range is defined by `version=2`, not by the name.

- **Package:** [`django-api-versioning`](https://pypi.org/project/django-api-versioning/)
- **Source code:** [mojtaba-arvin/django-api-versioning](https://github.com/mojtaba-arvin/django-api-versioning)
- **License:** MIT

## Why not just use DRF's built-in versioning?

DRF ships with `URLPathVersioning`, `NamespaceVersioning`, `AcceptHeaderVersioning`, `QueryParameterVersioning`, and `HostNameVersioning`. Every one of them does the same thing: extract the version from the request and set `request.version`. **None of them decide which view serves which version, and none of them register your URLs.** DRF documents this explicitly: *"How you vary the API behavior is up to you."*

| Feature | DRF `URLPathVersioning` | `django-api-versioning` |
| --- | --- | --- |
| Extract version from request | ✅ | ✅ (reads request.version) |
| Register URL routes automatically | ❌ — you write path() per version | ✅ — decorator registers |
| Different view per version | ❌ — you write if request.version | ✅ — @endpoint decorator |
| Segment inheritance (version=2 serves v3+) | ❌ | ✅ — default behavior |
| Explicit version sets (versions=[2, 4]) | ❌ — manual if | ✅ — decorator argument |
| Bounded ranges (ver_range(1, 3)) | ❌ — manual if | ✅ — decorator argument |
| Unversioned routes in same registry | ❌ | ✅ — omit version |
| Deprecation / Sunset headers | ❌ | ✅ — LifecycleMiddleware |
| Version matrix inspection | ❌ | ✅ — check_versions |
| CI snapshot guard | ❌ | ✅ — assert_version_matrix |
| Deterministic URL reversal | ⚠️ — reverse() picks first match | ✅ — api_reverse() requires version |
| Works without DRF | ❌ | ✅ |
| Function-based and class-based views | ✅ | ✅ |

If you already use DRF, keep it. This package doesn't replace DRF's versioning classes — it adds the layer DRF deliberately left to you.

## Installation

Install [Django API Versioning](https://pypi.org/project/django-api-versioning/) package from PyPI:

```bash
pip install django-api-versioning
```

Requires **Django >= 5.2** and **Python >= 3.10**.  
Django REST Framework is optional and auto-detected.

## Quick Start

### 1. Configure Django settings

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

`API_BASE_PATH` **must** contain the `{version}` placeholder.

### 2. Include the generated URL patterns

If your project doesn't have a root URLconf yet:

```python
# settings.py
ROOT_URLCONF = "django_api_versioning.urls"
```

If it does, include them:

```python
# project/urls.py
from django.urls import include, path
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    # ... your other URL patterns
    path("", include(api_urlpatterns)),
]
```

After this one-time setup, you never touch urls.py again. Every @endpoint registers its own routes.

### 3. Decorate your views

Example for DRF's APIView:

```python
from rest_framework.response import Response
from rest_framework.views import APIView
from django_api_versioning.decorators import endpoint

@endpoint("invoices/<int:invoice_id>/", version=2, view_name="invoice-detail")
class InvoiceDetailView(APIView):
    def get(self, request, invoice_id):
        return Response({"id": invoice_id, "status": "paid"}
```

That's it. You now have:

```text
GET /api/v1/invoices/42/  →  404    # endpoint introduced in v2
GET /api/v2/invoices/42/  →  {"id": 42, "status": "paid"}
GET /api/v3/invoices/42/  →  {"id": 42, "status": "paid"}
GET /api/v4/invoices/42/  →  {"id": 42, "status": "paid"}
GET /api/v5/invoices/42/  →  {"id": 42, "status": "paid"}
```

path() converters (<int:pk>, <slug:name>) work as expected.

## Before and after

**Without `django-api-versioning`** — you maintain one `path()` per
version, and copy unchanged views when a new version ships:

```python
# urls.py — manual, error-prone, hard to keep in sync
from django.urls import path
from . import views

urlpatterns = [
    path("api/v1/users/", views.user_list_alpha),
    path("api/v2/users/", views.user_list_beta),
    path("api/v3/users/", views.user_list_beta),   # same view, new path — must remember to add
    path("api/v1/orders/", views.order_list),
    path("api/v2/orders/", views.order_list),      # unchanged — but new path required
    path("api/v3/orders/", views.order_list),      # unchanged — but new path required
    # ... × 150 endpoints
]
```

**With `django-api-versioning`** — one declaration, routing handled. `API_MAX_VERSION = 3‍` in this example.

```python
# apps/users/views.py
from django_api_versioning.decorators import endpoint

@endpoint("users/", version=1)
def user_list_alpha(request):
    ...

@endpoint("users/", version=2)
def user_list_beta(request):
    ...    # covers v2 and v3 — segment extends to API_MAX_VERSION

# apps/orders/views.py
@endpoint("orders/", version=1)
def order_list(request):
    ...    # covers v1, v2, v3 — segment extends to API_MAX_VERSION
```

```python
# project/urls.py — written once, never edited when a version is added
from django.urls import include, path
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    # ... your existing URLs
    path("", include(api_urlpatterns)),
]
```

The two `urls.py` blocks above produce the same routing. The difference is what the next version costs:

| | **Without** | **With** |
| --- | --- | --- |
| Add a new endpoint in v2 | New `path()`, new view | One `@endpoint` |
| Unchanged endpoint in v3 | New `path()`, new view function | Nothing — segment extends |
| Find which view serves v3 | Search three files | `python manage.py check_versions` |
| Two teams add routes | Merge conflict in `urls.py` | Each team edits its own `views.py` |
| File size after 5 versions × 150 endpoints | ~750 `path()` entries | 3-line `urls.py` |

Verify the routing:

```bash
python manage.py check_versions
```

Example output:

```text
api/v1/users/:   v1  → user_list_alpha
api/v2/users/:   v2  → user_list_beta
api/v3/users/:   v3  → user_list_beta     # v3 not declared — inherits from v2 segment

api/v1/orders/:   v1  → order_list
api/v2/orders/:  v2  → order_list         # v2 not declared — inherits from v1 segment
api/v3/orders/:  v3  → order_list         # v3 not declared — inherits from v1 segment
```

The HTTP responses match the manual-routing version exactly:

```text
GET /api/v1/users/  →  (user_list_alpha response)
GET /api/v2/users/  →  (user_list_beta response)
GET /api/v3/users/   →  (user_list_beta response)    # inherited from v2
GET /api/v1/orders/  →  (order_list response)   
GET /api/v2/orders/  →  (order_list response)        # inherited from v1
GET /api/v3/orders/  →  (order_list response)        # inherited from v1
```

Now suppose v4 changes the users response. Add one declaration:

```python
@endpoint("users/", version=4)
def user_list_gamma(request):
    ...    # covers v4 — v2 segment shrinks to [2, 3] automatically
```

`user_list_beta` still serves v2 and v3. `user_list_gamma` serves v4. No other route changes. In the manual setup, the same change would require editing `urls.py`, writing `user_list_gamma`, and re-checking three places to confirm `/api/v2/users/` and `/api/v3/users/` still point at user_list_beta.

## Four syntaxes

Each example below uses a real API evolution pattern. The 404s are not the package's default — they are the declared contract for that specific endpoint.

### 1. Segment — a new endpoint starting in v3

```python
@endpoint("reports/", version=3)
def report_list(request):
    return JsonResponse({"reports": []})
```

```text
GET /api/v1/reports/  →  404    # route not declared for v1
GET /api/v2/reports/  →  404    # route not declared for v2
GET /api/v3/reports/  →  {"reports": []}
GET /api/v4/reports/  →  {"reports": []}
GET /api/v5/reports/  →  {"reports": []}
```

The v1 and v2 404s mean "this endpoint did not exist in those versions." Other routes in v1 and v2 are unaffected.

### 2. Explicit set — v2 and v4 only (rolled back in v3)

```python
@endpoint("ranking/", versions=[2, 4])
def ranking(request):
    return JsonResponse({"algorithm": "new"})
```

```text
GET /api/v1/ranking/  →  404    # not yet shipped
GET /api/v2/ranking/  →  {"algorithm": "new"}
GET /api/v3/ranking/  →  404    # rolled back in v3
GET /api/v4/ranking/  →  {"algorithm": "new"}
GET /api/v5/ranking/  →  404    # removed in v5
```

Use this when an endpoint exists in non-contiguous versions — an experiment rolled back and re-shipped, or a feature gated to specific releases.

### 3. Bounded range — v1 through v3, then removed

```python
from django_api_versioning.decorators import endpoint, ver_range

@endpoint("legacy/", versions=ver_range(1, 3))
def legacy_endpoint(request):
    return JsonResponse({"deprecated": True})
```

```text
GET /api/v1/legacy/  →  {"deprecated": true}
GET /api/v2/legacy/  →  {"deprecated": true}
GET /api/v3/legacy/  →  {"deprecated": true}
GET /api/v4/legacy/  →  404    # removed in v4
GET /api/v5/legacy/  →  404
```

ver_range(a, b) is inclusive: ver_range(1, 3) == [1, 2, 3].

### 4. Unversioned — no v{n} prefix

```python
@endpoint("health/")
def health_check(request):
    return JsonResponse({"status": "ok"})
```

```text
GET /health/  →  {"status": "ok"}
```

Unversioned routes are registered at the include prefix, not under API_BASE_PATH. With the setup above (path("", include(...))), the URL is /health/. If you need it under /api/, set API_BASE_PATH = "v{version}/" and include at path("api/", include(...)) — then both versioned and unversioned routes live under /api/.

## How segments resolve

Two declarations for the same route:

```python
@endpoint("orders/", version=1)
def order_list_v1(request):
    return JsonResponse({"version": 1})

@endpoint("orders/", version=3)
def order_list_v3(request):
    return JsonResponse({"version": 3})
```

```text
GET /api/v1/orders/  →  {"version": 1}   # order_list_v1
GET /api/v2/orders/  →  {"version": 1}   # order_list_v1 — v2 is inside the v1 segment
GET /api/v3/orders/  →  {"version": 3}   # order_list_v3
GET /api/v4/orders/  →  {"version": 3}   # order_list_v3 — v3 segment extends forward
GET /api/v5/orders/  →  {"version": 3}   # order_list_v3 — up to API_MAX_VERSION
```

The v3 declaration shrinks the v1 segment to [1, 2]. Editing order_list_v1 changes v1 and v2. It cannot change v3.

## Reliability tools

### `check_versions` — inspect the registered matrix

```bash
python manage.py check_versions
```

Prints every registered URL with the version it serves, and warns about gaps in the declared range.

### `assert_version_matrix` — guard in CI

```python
# tests/test_versions.py
from django_api_versioning.testing import assert_version_matrix

def test_version_matrix():
    assert_version_matrix(snapshot=".version_matrix.json")
```

If the matrix has changed, `assert_version_matrix` raises `VersionMatrixError` with a diff:

```text
Version matrix changed. Diff:
  api/v5/orders/:
    v5: order_list_v3 -> order_list_v5
```

Run with `update=True` to accept the new matrix.
A PR that re-routes v5 from `order_list_v3` to `order_list_v5` now produces a visible line in CI. No silent version drift.

### `api_reverse` — deterministic links

```python
from django_api_versioning.reverse import api_reverse

api_reverse("order-list", version=2)   # "/api/v2/orders/"
api_reverse("order-list")              # AmbiguousVersionError
```

Django's reverse() returns whichever URL pattern registered first for a name — adding a new version can silently change that target. api_reverse requires an explicit version.

### Deprecation and sunset headers

```python
# settings.py
API_VERSION_LIFECYCLE = {
    1: {"status": "retired", "sunset": "2025-01-01"},
    2: {"status": "deprecated", "sunset": "2027-06-01"},
    3: {"status": "active"},
}

MIDDLEWARE = [
    "django_api_versioning.lifecycle.LifecycleMiddleware",
]
```

Every /api/v2/* response carries:

```http
Deprecation: true
Sunset: Tue, 01 Jun 2027 00:00:00 GMT
```

Every /api/v1/* request returns:

```http
HTTP/1.1 410 Gone
```

The middleware reads request.version (set by DRF) or `resolver_match.kwargs["version"]`. Path-based versioning is fully supported.

## Configuration reference

### Django settings

| Setting | Default | Description |
| --- | --- | --- |
| `API_BASE_PATH` | `"api/v{version}/"` | `Prefix template. Must contain {version}.` |
| `API_MIN_VERSION` | `1` | `Lowest valid version.` |
| `API_MAX_VERSION` | `1` | `Highest valid version.` |
| `ROOT_URLCONF` | `"django_api_versioning.urls"` | `Points Django at the registry (only if you don't use include()).` |
| `API_VERSION_LIFECYCLE` | `{}` | `Per-version status and sunset.` |
| `API_VERSIONING_CHANNELS` | `["path"]` | `Reserved. Only path is currently honored.` |
| `API_EFFECTIVE_VERSION_RESOLVER` | `None` | `Reserved. Not yet wired into routing.` |

### `@endpoint` arguments

| **Argument** | **Type** | **Default** | **Purpose** |
| :--- | :--- | :--- | :--- |
| `postfix` | `str` | Required | Resource path, e.g. `"users/"` or `"users/<int:pk>/"`. |
| `version` | `int \| None` | `None` | Declares a version segment starting at `N` and extending through `API_MAX_VERSION`. |
| `versions` | `list[int] \| None` | `None` | Explicitly specifies the versions served, e.g. `[1, 3, 5]` or `ver_range(1, 3)`. |
| `app_name` | `str \| None` | `None` | Optional path segment for grouping, e.g. `"shop"` → `/api/v1/shop/users/`. |
| `view_name` | `str \| None` | `None` | Django URL name for `reverse()`. Use stable, unique names. |

**Rules:**

- `version` and `versions` are mutually exclusive. Providing both raises `VersionRangeError`.
- If neither is provided, the endpoint is registered as an unversioned route (without the `/api/vN/` prefix).
- `version=N` registers the endpoint for versions `N` through `API_MAX_VERSION`, with `N` as its `source_version`.
- `versions=[...]` registers the endpoint for each listed version, with each version serving as its own `source_version`.
- **Collision resolution:** The declaration with the higher `source_version` takes precedence. If multiple declarations have the same `source_version`, the last registered declaration wins.
- If `version < API_MIN_VERSION`, a warning is issued and no route is registered.

**Helper:** `ver_range(start, end)` returns an inclusive range of versions. For example, `ver_range(1, 3)` is equivalent to `[1, 2, 3]`.

## Known limitations

These are acknowledged gaps in the current release, tracked as issues:

Multi-channel versioning (API_VERSIONING_CHANNELS) is defined in settings but not yet consulted by the routing layer. Only path-based versioning is active.

Per-tenant pinning (API_EFFECTIVE_VERSION_RESOLVER) is validated but not yet used by the registry.

DRF ViewSet classes cannot be passed directly to @endpoint — ViewSet.as_view() requires an actions argument the decorator does not supply. Use APIView or @api_view.

Unversioned routes do not receive the API_BASE_PATH prefix. They are registered at the include prefix (see syntax #4 for the two valid setup combinations).

check_versions gap warnings are under revision.

Each will be addressed in a future release. This README documents only what works today.

## Migration from 0.2.0

| 0.2.0 | 0.3.0 |
| --- | --- |
| `version=3` | `unchanged` |
| `version=3, forward=False` | `versions=[3]` |
| `version=5, backward=True` | `version=1` |
| `version=3, backward=False, forward=False` | `versions=[3]` |
| `version=3, backward=True, forward=False` | `versions=ver_range(1, 3)` |

```bash
python manage.py migrate_endpoints --dry-run
python manage.py migrate_endpoints
```

## Requirements

| Django | Python |
| --- | --- |
| 5.2 (LTS, until April 2028) | 3.10+ |
| 6.0 | 3.10+ |
| 6.1 | 3.10+ |
Django 5.2 is the minimum supported release; Django 4.2 reached end-of-life in April 2026. DRF is optional. The package reads `request.version`, which is what DRF's `URLPathVersioning`, `AcceptHeaderVersioning`, `NamespaceVersioning`, and `QueryParameterVersioning` set.

---

## Contributing

### Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && pip install -e .
pre-commit install
```

### Running tests

```bash
pytest
pre-commit run --all-files
```

### Docker

The `Dockerfile` parameterizes Python via `PYTHON_VERSION` and delegates
to `entrypoint.sh`:

```bash
docker build -t dapi .
docker run --rm dapi                                          # tests
docker run --rm -e RUN_PRE_COMMIT=true dapi                   # + lint
docker build --build-arg PYTHON_VERSION=3.15 -t dapi:py315 .  # other Python
docker run --rm dapi:py311
```

### Releasing

1. Bump `version` in `pyproject.toml` and update `CHANGELOG.md`
2. Commit, push to `main`
3. `git tag v0.3.1 && git push origin v0.3.1` → CI publishes to PyPI

## Reporting issues

Include your Django and package settings, the `@endpoint` declarations
involved, expected vs actual URL patterns, and your Python and Django
versions.

---

## License

Released under the [MIT License](LICENSE).
