---
slug: "018-deprecate-django-api-versioning-routes-sunset-headers"
title: "Deprecating Django API Versions with django-api-versioning"
description: "Deprecate @endpoint-registered routes with Deprecation and Sunset headers, generate successor links, and control when old API versions return 410 Gone."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "django-api-versioning"
  - "API deprecation"
  - "Sunset header"
  - "Django REST Framework"
  - "API versioning"
---

# Deprecating Django API Versions with django-api-versioning

When an API has multiple versions, retiring an old version requires more than removing its URL patterns. Clients need time to migrate, a clear deadline, and a reliable way to discover the replacement.

The [`django-api-versioning` package](https://pypi.org/project/django-api-versioning/) registers versioned routes through `@endpoint`, but it does not implement a deprecation lifecycle. It has no built-in `sunset_date` configuration, automatic deprecation headers, or removal policy.

That separation is intentional: the package handles route registration, while the application controls response behavior and API lifecycle policies.

This article shows how to deprecate routes registered with `@endpoint`, including:

- `Deprecation` and `Sunset` response headers.
- A `deprecation` link to migration documentation.
- A `successor-version` link to the corresponding resource in the new API version.
- An explicit transition from normal responses to `410 Gone`.

The examples use Django REST Framework generic views and a `Product` model. They assume the package's default URL prefix, `api/v{version}/`.

## 1. Register the old and new versions explicitly

Start with two versions of the same resource:

- v1 is the version being deprecated.
- v2 is its replacement.

Configure the package to register both versions:

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

Use explicit version lists for the two endpoint declarations:

```python
# views.py

from django_api_versioning import endpoint
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from .models import Product
from .serializers import ProductSerializerV1, ProductSerializerV2


@endpoint(
    "products/",
    versions=[1],
    view_name="product-list-v1",
)
class ProductListV1(ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1


@endpoint(
    "products/<int:pk>/",
    versions=[1],
    view_name="product-detail-v1",
)
class ProductDetailV1(RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1


@endpoint(
    "products/",
    versions=[2],
    view_name="product-list-v2",
)
class ProductListV2(ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV2


@endpoint(
    "products/<int:pk>/",
    versions=[2],
    view_name="product-detail-v2",
)
class ProductDetailV2(RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV2
```

The explicit `versions` argument matters here. Unlike `versions=[1]`, `version=1` registers a range beginning at version 1 and extending through `API_MAX_VERSION`. If v1 and v2 have separate implementations, explicit version lists make the intended registration unambiguous.

The resulting routes are:

| Version | Route | Handler |
| --- | --- | --- |
| v1 | `/api/v1/products/` | `ProductListV1` |
| v1 | `/api/v1/products/<pk>/` | `ProductDetailV1` |
| v2 | `/api/v2/products/` | `ProductListV2` |
| v2 | `/api/v2/products/<pk>/` | `ProductDetailV2` |

The `view_name` values are explicit because the package does not infer Django URL names from Python class names.

Make sure the modules containing these declarations are imported before loading the package's URL patterns:

```python
# project/urls.py

import myapp.views

from django.urls import include, path
from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The package registers the routes. It does not decide whether a registered version is deprecated or whether its responses should include lifecycle headers.

## 2. Understand the deprecation headers

Three HTTP mechanisms are useful when announcing an API retirement.

### `Deprecation`

[RFC 9745](https://www.rfc-editor.org/rfc/rfc9745.html) defines the `Deprecation` response header.

Its value is a Structured Field Date, as defined by RFC 9651. The format is `@` followed by an integer Unix timestamp:

```text
Deprecation: @1798761600
```

An RFC 3339 timestamp such as `2027-01-01T00:00:00Z` is not the required syntax.

The header communicates when the resource was or will be deprecated. It does not, by itself, change the resource's behavior.

### `Sunset`

[RFC 8594](https://www.rfc-editor.org/rfc/rfc8594.html) defines the `Sunset` response header.

Unlike `Deprecation`, it uses the HTTP-date format:

```text
Sunset: Wed, 30 Jun 2027 00:00:00 GMT
```

The value identifies when the resource is expected to become unavailable.

A sunset date is a communicated deadline, not an automatic enforcement mechanism. Your application must decide what happens when that deadline arrives.

### `Link`

[RFC 8288](https://www.rfc-editor.org/rfc/rfc8288.html) defines the HTTP `Link` header. Two relations are particularly useful:

- `deprecation`, registered by RFC 9745, points to documentation about the deprecation.
- `successor-version`, defined by [RFC 5829](https://www.rfc-editor.org/rfc/rfc5829.html), points to a resource that replaces the current resource.

For example:

```text
Deprecation: @1798761600
Sunset: Wed, 30 Jun 2027 00:00:00 GMT
Link: <https://docs.example.com/api/migrate-v1-to-v2>; rel="deprecation"
Link: <https://api.example.com/api/v2/products/42/>; rel="successor-version"
```

These links have different purposes. The migration guide can be shared by all deprecated resources, while a successor link should identify the corresponding replacement resource when one exists.

## 3. Store deprecation policy in application settings

Keep the lifecycle configuration separate from the package's route registration.

For a version-wide deprecation policy:

```python
# settings.py

from datetime import datetime, timezone


API_DEPRECATION = {
    1: {
        "deprecation_date": datetime(
            2027, 1, 1, tzinfo=timezone.utc
        ),
        "sunset_date": datetime(
            2027, 6, 30, tzinfo=timezone.utc
        ),
        "migration_url": (
            "https://docs.example.com/api/migrate-v1-to-v2"
        ),
        "removed": False,
    },
}
```

The integer key represents the API version, not the route name.

The `removed` flag is an explicit operational decision. It is deliberately separate from the sunset date: reaching the configured date does not automatically remove a route.

This configuration can be used by middleware to apply the same policy to every route belonging to v1.

## 4. Add version-wide headers with middleware

Middleware is useful when an entire API version shares the same deprecation policy.

With the package's default `API_BASE_PATH` and the URLconf shown earlier, versioned paths look like:

```text
/api/v1/products/
/api/v1/products/42/
```

The following middleware extracts the version from that URL structure and applies the corresponding policy.

```python
# myapp/middleware.py

import re

from django.conf import settings
from django.http import HttpResponseGone
from django.utils.http import http_date


class APIDeprecationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.config = getattr(settings, "API_DEPRECATION", {})

        # Matches the package's default API_BASE_PATH:
        # api/v{version}/
        self.path_re = re.compile(
            r"^/api/v(?P<version>\d+)/"
        )

    def __call__(self, request):
        match = self.path_re.match(request.path_info)

        if not match:
            return self.get_response(request)

        version = int(match.group("version"))
        config = self.config.get(version)

        if not config:
            return self.get_response(request)

        if config.get("removed", False):
            response = HttpResponseGone(
                "This API version has been retired."
            )
        else:
            response = self.get_response(request)

        deprecation_date = config.get("deprecation_date")
        if deprecation_date is not None:
            response["Deprecation"] = (
                f"@{int(deprecation_date.timestamp())}"
            )

        sunset_date = config.get("sunset_date")
        if sunset_date is not None:
            response["Sunset"] = http_date(
                sunset_date.timestamp()
            )

        migration_url = config.get("migration_url")
        if migration_url:
            migration_link = (
                f'<{migration_url}>; rel="deprecation"'
            )
            self.append_link(response, migration_link)

        return response

    @staticmethod
    def append_link(response, link_value):
        existing = response.get("Link")

        if existing:
            response["Link"] = f"{existing}, {link_value}"
        else:
            response["Link"] = link_value
```

Register the middleware:

```python
# settings.py

MIDDLEWARE = [
    # ...
    "myapp.middleware.APIDeprecationMiddleware",
]
```

The middleware uses `request.path_info`, which represents the path inside the Django URL configuration. The regular expression must still match the URL structure produced by your `API_BASE_PATH` and URL mounting configuration.

For example, if you change the package prefix to `api/{version}/`, the expression must be updated to match `/api/1/...` rather than `/api/v1/...`.

This implementation also assumes that the version appears in the URL path. It does not extract versions negotiated through request headers or other DRF versioning schemes.

### What the middleware provides

For a normal v1 response, the middleware adds:

```text
Deprecation: @1798761600
Sunset: Wed, 30 Jun 2027 00:00:00 GMT
Link: <https://docs.example.com/api/migrate-v1-to-v2>; rel="deprecation"
```

When `removed` is set to `True`, the middleware returns `410 Gone` instead of invoking the view.

The headers are added to that response as well, so clients can still discover the migration documentation after removal.

### What the middleware does not provide

The middleware does not generate a per-resource `successor-version` link.

It knows the request path, but it does not know whether the corresponding v2 resource has the same route structure, lookup arguments, or even a direct replacement.

Replacing `/v1/` with `/v2/` in a string is not a reliable substitute for URL reversing. It assumes that every endpoint has an identically structured replacement.

For a resource-specific successor link, use the resolved view's lookup arguments and the package's reverse helper.

## 5. Generate successor links with a view mixin

A view mixin can access the request, the resolved view instance, and its URL lookup arguments.

For routes registered with `@endpoint`, use `api_reverse()` to generate the destination URL from the package's route registry.

```python
# myapp/mixins.py

from datetime import datetime

from django_api_versioning import api_reverse
from django.utils.http import http_date


class DeprecatedVersionMixin:
    deprecation_date: datetime | None = None
    sunset_date: datetime | None = None

    successor_view_name: str | None = None
    successor_version: int | None = None

    migration_url: str | None = None

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)

        if self.deprecation_date is not None:
            response["Deprecation"] = (
                f"@{int(self.deprecation_date.timestamp())}"
            )

        if self.sunset_date is not None:
            response["Sunset"] = http_date(
                self.sunset_date.timestamp()
            )

        links = []

        if (
            self.successor_view_name
            and self.successor_version is not None
        ):
            try:
                successor_path = api_reverse(
                    self.successor_view_name,
                    version=self.successor_version,
                    **self.kwargs,
                )

                successor_url = request.build_absolute_uri(
                    successor_path
                )

                links.append(
                    f'<{successor_url}>; rel="successor-version"'
                )
            except Exception:
                # A missing successor route should not break
                # the deprecated endpoint's normal response.
                pass

        if self.migration_url:
            links.append(
                f'<{self.migration_url}>; rel="deprecation"'
            )

        if links:
            existing = response.get("Link")

            new_links = ", ".join(links)

            response["Link"] = (
                f"{existing}, {new_links}"
                if existing
                else new_links
            )

        return response
```

The mixin uses the package's `api_reverse()` rather than Django's `reverse()` because the destination is a route registered through `@endpoint`.

The explicit `version` argument selects the intended destination version. The helper returns a root-relative path, which `request.build_absolute_uri()` converts into an absolute URL.

The broad exception handler above is intentionally defensive for this illustrative mixin: a missing successor should not make the deprecated endpoint unavailable. In a production implementation, catch the specific exception raised by your installed package version and log the failure so that a missing migration route is not silently ignored.

### Apply the mixin to v1 views

```python
# myapp/views.py

from datetime import datetime, timezone

from django_api_versioning import endpoint
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from .mixins import DeprecatedVersionMixin
from .models import Product
from .serializers import ProductSerializerV1, ProductSerializerV2


DEPRECATION_DATE = datetime(
    2027, 1, 1, tzinfo=timezone.utc
)

SUNSET_DATE = datetime(
    2027, 6, 30, tzinfo=timezone.utc
)

MIGRATION_URL = (
    "https://docs.example.com/api/migrate-v1-to-v2"
)


@endpoint(
    "products/",
    versions=[1],
    view_name="product-list-v1",
)
class ProductListV1(
    DeprecatedVersionMixin,
    ListCreateAPIView,
):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1

    deprecation_date = DEPRECATION_DATE
    sunset_date = SUNSET_DATE

    successor_view_name = "product-list-v2"
    successor_version = 2

    migration_url = MIGRATION_URL


@endpoint(
    "products/<int:pk>/",
    versions=[1],
    view_name="product-detail-v1",
)
class ProductDetailV1(
    DeprecatedVersionMixin,
    RetrieveUpdateDestroyAPIView,
):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1

    deprecation_date = DEPRECATION_DATE
    sunset_date = SUNSET_DATE

    successor_view_name = "product-detail-v2"
    successor_version = 2

    migration_url = MIGRATION_URL


@endpoint(
    "products/",
    versions=[2],
    view_name="product-list-v2",
)
class ProductListV2(ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV2


@endpoint(
    "products/<int:pk>/",
    versions=[2],
    view_name="product-detail-v2",
)
class ProductDetailV2(RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV2
```

The list view has no lookup arguments, so `self.kwargs` is empty. The detail view has a `pk` argument, which is passed to `api_reverse()`.

For a request to:

```text
/api/v1/products/42/
```

the mixin generates a successor URL equivalent to:

```text
/api/v2/products/42/
```

The destination is selected through the package's registry using `version=2`, rather than by modifying the incoming URL string.

The v1 and v2 views have distinct `view_name` values. This also avoids ambiguity when using Django's normal URL reversing elsewhere in the application.

### What the mixin provides

- A resource-specific `successor-version` link.
- A migration-documentation link.
- Deprecation metadata attached directly to selected views.
- No dependency on a particular URL prefix regex.

### What the mixin does not provide

The mixin does not remove routes or return `410 Gone` after the sunset date. It only adds response headers.

It also assumes that the v2 route accepts the same lookup arguments as the v1 route. If v1 uses `pk` and v2 uses `slug`, translate the lookup arguments before calling `api_reverse()`.

The example catches failures to generate a successor link so that a missing v2 route does not break v1 responses. In production, log those failures and monitor them: a missing successor link is a migration defect worth investigating.

## 6. Combine middleware and the mixin

The two patterns can coexist:

- Middleware applies version-wide deprecation headers and enforces removal.
- The mixin adds a resource-specific `successor-version` link.

Django's middleware calls `get_response(request)`, which runs the view. The mixin's `dispatch()` therefore executes before control returns to the middleware.

The middleware must preserve any `Link` header already created by the view. Its `append_link()` method does that rather than replacing the existing header.

A v1 detail response can then contain both relations:

```text
Deprecation: @1798761600
Sunset: Wed, 30 Jun 2027 00:00:00 GMT
Link: <https://api.example.com/api/v2/products/42/>; rel="successor-version", <https://docs.example.com/api/migrate-v1-to-v2>; rel="deprecation"
```

The two links provide different information:

- `successor-version` points to the replacement resource.
- `deprecation` points to documentation describing the migration.

The example appends Link values as a comma-separated list. This is appropriate for the simple links shown here. If your application produces more complex Link fields, use a parser or serializer that correctly handles RFC 8288 syntax rather than relying on substring checks.

## 7. Enforce the sunset explicitly

A deprecation lifecycle has three operational stages.

### Stage 1 — Announce

The old version continues to work. Responses carry `Deprecation`, `Sunset`, and migration links.

### Stage 2 — Monitor

Continue sending the headers and measure usage of the deprecated routes.

Useful information includes:

- Which clients still call v1.
- Which endpoints they use.
- How frequently they call them.
- Whether they have started using v2.

Access logs, API gateway metrics, or application-level request logging can provide this information.

### Stage 3 — Remove

When the retirement decision is approved, set:

```python
API_DEPRECATION = {
    1: {
        "deprecation_date": datetime(
            2027, 1, 1, tzinfo=timezone.utc
        ),
        "sunset_date": datetime(
            2027, 6, 30, tzinfo=timezone.utc
        ),
        "migration_url": (
            "https://docs.example.com/api/migrate-v1-to-v2"
        ),
        "removed": True,
    },
}
```

The middleware now returns `410 Gone` for requests matching the v1 path prefix.

The important distinction is that the sunset date does not automatically trigger this behavior. The application explicitly changes `removed` to `True`.

If you use only the view mixin, you must implement the removal check separately. The mixin does not enforce the sunset date.

## 8. Check the migration policy

A small management command can report the configured retirement policy:

```python
# myapp/management/commands/list_deprecated_versions.py

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "List deprecated API versions and their sunset dates"

    def handle(self, *args, **options):
        config = getattr(settings, "API_DEPRECATION", {})

        for version, entry in config.items():
            self.stdout.write(f"Version {version}")
            self.stdout.write(
                f"  Deprecation: "
                f"{entry.get('deprecation_date', 'n/a')}"
            )
            self.stdout.write(
                f"  Sunset: {entry.get('sunset_date', 'n/a')}"
            )
            self.stdout.write(
                f"  Removed: {entry.get('removed', False)}"
            )
            self.stdout.write(
                f"  Migration: {entry.get('migration_url', 'n/a')}"
            )
```

Run it during releases or documentation builds to check that the configured dates and migration links match the published migration guide.

This command reports application settings; it does not inspect the package registry or verify that every deprecated route has a successor.

## 9. Handle deprecation on the client

Clients should treat these headers as migration signals, not as proof that a replacement is available.

A simple Python client can inspect them:

```python
# example_client.py

import requests


def call_api(endpoint):
    response = requests.get(
        f"https://api.example.com{endpoint}"
    )

    deprecation = response.headers.get("Deprecation")
    sunset = response.headers.get("Sunset")
    links = response.headers.get("Link")

    if deprecation:
        print(f"This resource is deprecated: {deprecation}")

    if sunset:
        print(f"Sunset date: {sunset}")

    if links:
        print(f"Related links: {links}")

    response.raise_for_status()
    return response.json()
```

A production client should parse the `Link` header and identify the relation it needs. It should not assume that the first link is always the successor or that every deprecated resource has a replacement.

Also remember that `Deprecation` and `Sunset` are response headers. If browser-based clients need to read them across origins, configure CORS to expose the relevant headers.

## 10. Trade-offs and scope

| Requirement | Middleware | View mixin |
| --- | --- | --- |
| Version-wide deprecation policy | Yes | Requires applying it to each view |
| Per-endpoint deprecation | Requires additional configuration | Yes |
| `Deprecation` and `Sunset` headers | Yes | Yes |
| Migration documentation link | Yes | Yes |
| Resource-specific successor link | Requires additional routing logic | Yes |
| `410 Gone` enforcement | Yes, with the removal flag | Not included |
| Depends on URL path structure | Yes, in this example | No, uses the package registry |

Use middleware when an entire API version shares one retirement policy and you want a centralized removal switch.

Use a mixin when deprecation is specific to selected endpoints or when clients need a successor URL for the exact resource they requested.

For a version-wide retirement with resource-specific migration links, combining the two is reasonable.

**Scope: routing and response lifecycle.** `django-api-versioning` registers routes; it does not provide deprecation metadata, inject response headers, monitor client usage, or remove old versions automatically. Those responsibilities remain in the application.

The same HTTP headers can be used with other Django routing and DRF versioning approaches, but the package-specific part of this implementation is the explicit registration of old and new routes and the use of `api_reverse()` to resolve a successor route from the package registry.

## Next steps

For the package's route registration behavior, URL construction, and reverse lookup implementation, see the [django-api-versioning source repository](https://github.com/mojtaba-arvin/django-api-versioning).

Deprecation headers announce a lifecycle decision; they do not enforce it. A reliable retirement process combines explicit route registration, migration links, client-usage monitoring, and a deliberate removal step.
