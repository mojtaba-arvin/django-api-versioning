# Django API Versioning

[![PyPI version](https://badge.fury.io/py/django-api-versioning.svg)](https://badge.fury.io/py/django-api-versioning)
[![PyPI Downloads](https://img.shields.io/pypi/dm/django-api-versioning.svg)](https://pypi.org/project/django-api-versioning/)
[![Build Status](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/tests.yml/badge.svg)](https://github.com/mojtaba-arvin/django-api-versioning/actions)
[![Python versions](https://img.shields.io/pypi/pyversions/django-api-versioning.svg)](https://pypi.org/project/django-api-versioning/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Django API Versioning** is a Python package for [API versioning in Django](https://github.com/mojtaba-arvin/django-api-versioning) and Django REST Framework (DRF) projects. Stop copy-pasting
`path()` declarations for every API version — declare an endpoint once,
and let the registry handle v1, v2, v3, and beyond.

```python
from django.http import JsonResponse
from django_api_versioning.decorators import endpoint

@endpoint("users", version=2)
def user_list(request):
    return JsonResponse({"users": []})

# With API_MIN_VERSION = 1, API_MAX_VERSION = 3, this single
# decorator registers:
#
#   GET /api/v1/users/   ->  user_list
#   GET /api/v2/users/   ->  user_list
#   GET /api/v3/users/   ->  user_list   (with forward inheritance)‍‍‍
```

It registers versioned URL routes from a simple `@endpoint` decorator, helps preserve backward compatibility, and can optionally inherit unchanged endpoints into newer API versions.

It is especially useful for large APIs where many endpoints stay the same between releases. Instead of creating duplicate views or manually maintaining every route as the API grows, you can declare each endpoint once and control version routing centrally. Use `app_name` to group related resources by a domain or application area, while keeping each `postfix` focused on the resource itself.

- **Package:** [`django-api-versioning`](https://pypi.org/project/django-api-versioning/)
- **Source code:** [mojtaba-arvin/django-api-versioning](https://github.com/mojtaba-arvin/django-api-versioning)
- **License:** MIT

## Why not just use DRF's built-in versioning?

DRF ships with `URLPathVersioning` and friends — and they work. But they
only handle *which* version a request is on. You still write every
`path()` declaration by hand, duplicate unchanged routes, and decide
per-version which view to call.


| Feature | DRF `URLPathVersioning` | `django-api-versioning` |
|---|---|---|
| Route registration | Manual `path()` per version | Automatic via decorator |
| Backward compatibility | Manual | `backward=True` (default) |
| Forward inheritance (new versions reuse old views) | ❌ | ✅ Opt-in |
| Function-based views | ✅ | ✅ |
| Class-based views | ⚠️ DRF only | ✅ Django + DRF |
| `resolve().view_class` preserved | ✅ | ✅ |
| Unversioned routes | Manual | `version=None` |
| Works without DRF | ❌ | ✅ |
| Django `reverse()` support | ✅ | ✅ (highest version wins) |

If you already use DRF, you can keep it — this package handles routing,
not request parsing.

---

## Installation

Install [Django API Versioning](https://pypi.org/project/django-api-versioning/) package from PyPI:

```bash
pip install django-api-versioning
```

Requires **Django >= 5.2** and **Python >= 3.11**.  
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

### 3. Decorate your views

```python
from django.http import JsonResponse
from django_api_versioning.decorators import endpoint


@endpoint(
    "products/",
    app_name="catalog",
    version=2,
    view_name="catalog-products-list",
)
def product_list(request):
    return JsonResponse({"results": []})
```

That's it. You now have:

```text
GET /api/v1/catalog/products/
GET /api/v2/catalog/products/
```

Class-based views, DRF views, and path converters (`<int:pk>`) work
the same way:

```python
from rest_framework.response import Response
from rest_framework.views import APIView


@endpoint("invoices/<int:invoice_id>/", app_name="billing", version=2)
class InvoiceDetailView(APIView):
    def get(self, request, invoice_id):
        return Response({"id": invoice_id})
```

## Before and after

**Without `django-api-versioning`** — you maintain one `path()` per
version, and copy unchanged views when a new version ships:

```python
# urls.py — manual, error-prone, hard to keep in sync
from django.urls import path
from . import views

urlpatterns = [
    path("api/v1/users/", views.user_list_v1),
    path("api/v2/users/", views.user_list_v2),
    path("api/v3/users/", views.user_list_v3),  # same body as v2
    path("api/v1/orders/", views.order_list_v1),
    path("api/v2/orders/", views.order_list_v2),
    # ... × 150 endpoints
]
```

**With `django-api-versioning`** — one declaration, routing handled:

```python
from django_api_versioning.decorators import endpoint

@endpoint("users/", version=2)
def user_list(request):
    ...

@endpoint("orders/", version=2)
def order_list(request):
    ...
```

Add `API_FORWARD_INHERITANCE = True` and the same declarations serve
v3 automatically, without redeclaring anything that hasn't changed.

---

## Forward inheritance (the new feature)

Big APIs change in small increments. Suppose v3 changes only 8 endpoints
out of 150. You don't want to redeclare the other 142.

Enable **forward inheritance** to let unchanged endpoints serve future
versions automatically:

```python
# settings.py
API_FORWARD_INHERITANCE = True
```

Now a single `@endpoint("products/", version=2)` declaration serves
`/api/v1/...`, `/api/v2/...`, and `/api/v3/...` — subject to
`API_MAX_VERSION`.

### Opt one endpoint out


```python
@endpoint("events/", app_name="audit", version=2, forward=False)
def audit_events(request):
    ...
```

The per-endpoint value overrides the global setting, in either
direction.

### Override an inherited endpoint


Keep the v1/v2 implementation, and register a separate view for v3:

```python
@endpoint("reports/", app_name="analytics", version=2, view_name="reports")
def reports_v2(request):
    return JsonResponse({"api_version": 2})


@endpoint(
    "reports/",
    app_name="analytics",
    version=3,
    backward=False,
    forward=False,
    view_name="reports",
)
def reports_v3(request):
    return JsonResponse({"api_version": 3})
```

Result:

```text
/api/v1/analytics/reports/  ->  reports_v2
/api/v2/analytics/reports/  ->  reports_v2
/api/v3/analytics/reports/  ->  reports_v3
```

The registry resolves collisions by **declared-version priority**, so
the override always wins regardless of module import order.

---


## Configuration reference

### Django settings

| Setting | Default | Purpose |
|---|---|---|
| `API_BASE_PATH` | `"api/v{version}/"` | URL prefix template. Must contain `{version}`. |
| `API_MIN_VERSION` | `1` | Lowest API version to register. |
| `API_MAX_VERSION` | `1` | Highest configured API version. |
| `API_FORWARD_INHERITANCE` | `False` | Default for whether endpoints may be inherited into newer versions. |
| `ROOT_URLCONF` | `"django_api_versioning.urls"` | Django URLconf. Use the package one directly, or include its `urlpatterns` in your own. |

### `@endpoint` arguments

| Argument | Default | Purpose |
|---|---|---|
| `postfix` | required | Resource path, e.g. `"products/"` or `"products/<int:pk>/"`. |
| `app_name` | `None` | Optional path segment for grouping (e.g. `"catalog"`). This is a URL path segment, not Django's namespace `app_name`. |
| `version` | `None` | Version where this implementation is declared. `None` → unversioned route. |
| `backward` | `True` | Also register for earlier versions, down to `API_MIN_VERSION`. |
| `forward` | `None` | Per-endpoint override for forward inheritance. `None` → follow `API_FORWARD_INHERITANCE`. |
| `view_name` | `None` | Django URL name for `reverse()`. Use stable, unique names. |

`backward` and `forward` control different directions:

- `backward=True` → expose this view to earlier versions.
- `forward=True` → inherit this view into later versions.
- `backward=False, forward=False` → pin to the specified version only.

Both affect **routing**, not whether the response is semantically
compatible. You remain responsible for API contract design.

---


## URL reversing

Give each route a stable `view_name` and use `reverse()` instead of
hard-coding versioned URLs:

```python
from django.urls import reverse

url = reverse("catalog-products-list")  # -> "/api/v3/catalog/products/"
```

If multiple registrations share a name, the registry orders routes so
Django resolves the **highest registered version**.

---

## FAQ

**Does this work with DRF `APIView`?**  
Yes. Django's `View` is a base class of DRF's `APIView`, so the
decorator handles both. `resolve().func.view_class` is preserved, which
means DRF's authentication, permissions, and schema generation all
continue to work.

**Does this conflict with DRF's `DEFAULT_VERSIONING_CLASS`?**  
No, but they solve different problems: DRF's versioning tells *your
code* which version a request is on; this package decides *which view
is reachable at which URL*. You can use both together.

**What happens with duplicate `view_name`s?**  
`reverse()` returns the highest-version route. Each versioned path is
still uniquely resolvable.

**Can I use this with Django < 5.2?**  
No. Django 5.2 LTS is the minimum supported version. Django 4.2
reached end-of-life in April 2026.

**How do I deprecate a version?**  
Remove the corresponding declarations from your code (or set
`API_MIN_VERSION` upward) and run your test suite. The package does not
manage deprecation policy — that's an API design decision.

**Does the package require DRF?**  
No. DRF is optional. Pure Django projects work out of the box.

**Where do I report a routing issue?**  
Open an issue at [GitHub Issues](https://github.com/mojtaba-arvin/django-api-versioning/issues)
with your settings, endpoint declarations, expected URL patterns, and
actual behavior.

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
3. `git tag v0.2.1 && git push origin v0.2.1` → CI publishes to PyPI

## Reporting issues

Include your Django and package settings, the `@endpoint` declarations
involved, expected vs actual URL patterns, and your Python and Django
versions.

---

## License

Released under the [MIT License](LICENSE).
