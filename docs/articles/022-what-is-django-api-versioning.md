---
slug: "022-what-is-django-api-versioning-how-does-it-work"
title: "What Is django-api-versioning and How Does It Work?"
description: "Understand how django-api-versioning registers versioned Django URLs, carries unchanged endpoints forward, resolves route conflicts, and integrates with DRF."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "django-api-versioning"
  - "Django API versioning"
  - "Django REST Framework"
  - "API routing"
  - "Endpoint registration"
---

# What Is django-api-versioning and How Does It Work?

[django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/) is a Django package that registers URL patterns from view declarations. Instead of manually repeating URL registrations for unchanged endpoints across API versions, you declare an endpoint at the version where its implementation becomes active.

The package uses a registry to turn those declarations into concrete URL patterns. A declaration with `version=1`, for example, covers version 1 through `API_MAX_VERSION` unless another declaration takes over at a later version.

This is the central idea behind `django-api-versioning`: **declare an implementation once, then let the registration layer carry it forward across the configured version range.**

The package is maintained by the author of this article; implementation details below refer to version 0.3.4.

This article explains the registration model, shows how to use it in a Django REST Framework project, and identifies the boundaries between package behavior and framework behavior.

**Scope: routing only.** The package registers versioned URL patterns and provides version-aware reverse lookup. It does not decide whether an API change is backward compatible, implement DRF version negotiation, or generate version-specific API schemas.

## The problem: repeating unchanged route registrations

A common approach to URL-based API versioning is to maintain a separate DRF router for each API version.

For example, a project with three versions might register its existing ViewSets like this:

```python
# urls.py
from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    UserViewSetV1,
    UserViewSetV2,
    UserViewSetV3,
    PostViewSet,
    CommentViewSet,
)

v1_router = SimpleRouter()
v1_router.register("users", UserViewSetV1, basename="v1-user")
v1_router.register("posts", PostViewSet, basename="v1-post")
v1_router.register("comments", CommentViewSet, basename="v1-comment")

v2_router = SimpleRouter()
v2_router.register("users", UserViewSetV2, basename="v2-user")
v2_router.register("posts", PostViewSet, basename="v2-post")
v2_router.register("comments", CommentViewSet, basename="v2-comment")

v3_router = SimpleRouter()
v3_router.register("users", UserViewSetV3, basename="v3-user")
v3_router.register("posts", PostViewSet, basename="v3-post")
v3_router.register("comments", CommentViewSet, basename="v3-comment")

urlpatterns = [
    path("api/v1/", include(v1_router.urls)),
    path("api/v2/", include(v2_router.urls)),
    path("api/v3/", include(v3_router.urls)),
]
```

Here, `PostViewSet` and `CommentViewSet` are unchanged, but they are registered with each version's router. Each router generates routes under its own prefix.

This is a valid DRF approach. However, `SimpleRouter.register()` registers a ViewSet, which can generate several URL patterns for its actions. It is not necessarily a one-call-per-HTTP-endpoint mechanism.

`django-api-versioning` uses a different registration model. It registers individual view implementations through `@endpoint` and carries a declaration forward through the configured version range.

The two approaches organize URL registration differently. They should not be compared by counting router registrations against decorator declarations unless the examples expose exactly the same API surface.

For the router behavior and generated routes, see the [DRF routers documentation](https://www.django-rest-framework.org/api-guide/routers/).

## The registration model

The package's public decorator is imported from the top-level namespace:

```python
from django_api_versioning import endpoint
```

Its signature in v0.3.4 is:

```python
from typing import Callable, TypeVar

ViewT = TypeVar("ViewT", bound=Callable)


def endpoint(
    postfix: str,
    version: int | None = None,
    versions: list[int] | None = None,
    app_name: str | None = None,
    view_name: str | None = None,
) -> Callable[[ViewT], ViewT]:
    ...
```

The arguments control the route being registered:

- `postfix`: The endpoint path after the version prefix, such as `"users/"` or `"users/<int:pk>/"`.
- `version`: The starting version for a forward-extending segment.
- `versions`: An explicit list of versions in which the endpoint should be registered.
- `app_name`: An optional grouping segment inserted between the version prefix and the postfix.
- `view_name`: An optional Django URL pattern name.

`version` and `versions` are mutually exclusive. If neither is supplied, the endpoint is registered as an unversioned route.

For example:

```python
from django_api_versioning import endpoint
from rest_framework.generics import ListAPIView


@endpoint("users/", version=1, view_name="user-list")
class UserListView(ListAPIView):
    ...
```

With `API_MAX_VERSION = 3`, this declaration registers the view for versions 1, 2, and 3.

### Version segments

A declaration using `version=N` starts a segment at version N and extends it through `API_MAX_VERSION`.

For example, with:

```python
API_MIN_VERSION = 1
API_MAX_VERSION = 4
```

this declaration:

```python
@endpoint("posts/", version=1)
class PostListViewV1(ListAPIView):
    ...
```

registers the view for:

```text
/api/v1/posts/
/api/v2/posts/
/api/v3/posts/
/api/v4/posts/
```

If a new implementation is declared at version 3:

```python
@endpoint("posts/", version=3)
class PostListViewV3(ListAPIView):
    ...
```

the resulting route ownership is:

| Requested version | Implementation |
| --- | --- |
| v1 | `PostListViewV1` |
| v2 | `PostListViewV1` |
| v3 | `PostListViewV3` |
| v4 | `PostListViewV3` |

The v3 declaration takes over from version 3 onward. The earlier implementation continues to serve versions 1 and 2.

This is registration-time behavior. The package generates concrete URL patterns from the registry; it does not search through earlier implementations every time a request arrives.

### How route conflicts are resolved

Multiple declarations can target the same route. The registry uses each declaration's `source_version` to determine which implementation owns a version.

When two registrations collide on the same route:

1. If both declarations have integer `source_version` values, the higher source version wins.
2. If their source versions are equal, the last registered declaration wins.
3. If either source version is `None`, the last registered declaration wins.

For example:

```python
@endpoint("orders/", version=1)
class OrderListViewV1(ListAPIView):
    ...


@endpoint("orders/", version=3)
class OrderListViewV3(ListAPIView):
    ...
```

The v3 declaration owns versions 3 and 4, while the v1 declaration remains active for versions 1 and 2.

This is distinct from Python class inheritance. The package's segment behavior determines which view is registered for each URL; Python inheritance determines which implementation details a class reuses from its parent.

For the complete registration and collision contract, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Explicit version selection

Not every endpoint should necessarily remain available in every later version.

For non-contiguous version selection, use `versions`:

```python
from django.http import JsonResponse

from django_api_versioning import endpoint


@endpoint("ranking/", versions=[2, 4])
def ranking(request):
    return JsonResponse({"algorithm": "new"})
```

With a configured maximum version of 5, the route exists in v2 and v4 only.

| Requested version | Result |
| --- | --- |
| v1 | No matching route |
| v2 | `ranking` |
| v3 | No matching route |
| v4 | `ranking` |
| v5 | No matching route |

For a contiguous, bounded set, use `ver_range()`:

```python
from django.http import JsonResponse

from django_api_versioning import endpoint, ver_range


@endpoint("legacy/", versions=ver_range(1, 3))
def legacy_endpoint(request):
    return JsonResponse({"deprecated": True})
```

`ver_range(1, 3)` returns `[1, 2, 3]`. The route is not registered for v4 or later.

This is useful when an endpoint is intentionally available only in a defined set of API versions.

## Settings

The version range is controlled by Django settings:

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 3
```

`API_MIN_VERSION` defines the minimum supported route version, and `API_MAX_VERSION` defines the upper boundary for forward-extending declarations.

The default `API_MAX_VERSION` is 1. A project that declares version 2 or higher must increase it.

The package distinguishes between versions below the configured minimum and versions above the configured maximum:

- A declaration starting below `API_MIN_VERSION` produces a warning and registers no route.
- A declaration above `API_MAX_VERSION` raises `InvalidVersionError`.
- Supplying both `version` and `versions` raises `VersionRangeError`.
- For explicit `versions`, values below the minimum are skipped with a warning; values above the maximum are invalid.

The exception classes are defined in `django_api_versioning.exceptions`:

```python
from django_api_versioning.exceptions import (
    InvalidVersionError,
    VersionRangeError,
)
```

The package uses integer version identifiers. For example, use `version=2`, not `version="v2"`.

## URL prefix

The default `API_BASE_PATH` is:

```python
API_BASE_PATH = "api/v{version}/"
```

The `{version}` placeholder is required. The package substitutes the version number when generating each versioned URL.

For example:

```python
@endpoint("users/", version=1)
class UserListView(ListAPIView):
    ...
```

generates:

```text
/api/v1/users/
/api/v2/users/
/api/v3/users/
```

You can move the common `api/` prefix into the project's URLconf instead:

```python
# settings.py
API_BASE_PATH = "v{version}/"
```

```python
# urls.py
from django.urls import include, path

# Import endpoint modules before reading the registry.
from . import views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("api/", include(api_urlpatterns)),
]
```

The resulting versioned URLs still begin with `/api/`.

The `app_name` argument inserts one additional path segment:

```python
@endpoint("reports/", version=1, app_name="internal")
class InternalReportView(ListAPIView):
    ...
```

With the default prefix, the generated path is:

```text
/api/v1/internal/reports/
```

`app_name` is a grouping segment, not an arbitrary URL template.

## A complete DRF example

The following example shows a project where the product list response changes in v2, but the detail endpoint remains unchanged.

### Step 1: Configure the package

```python
# settings.py

INSTALLED_APPS = [
    # Other installed apps
    "django_api_versioning",
]

API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

### Step 2: Organize and declare the views

A project can keep version-specific implementations in separate modules while placing shared endpoints in a common module. This directory structure is an organizational choice; it does not determine the URL path. The `@endpoint` arguments and `API_BASE_PATH` determine the generated routes.

For example:

```text
products/
    models.py
    serializers.py
    views/
        __init__.py
        common.py
        v1.py
        v2.py
```

The common detail view can live in `common.py`:

```python
# products/views/common.py

from django_api_versioning import endpoint
from rest_framework.generics import RetrieveUpdateDestroyAPIView

from ..models import Product
from ..serializers import ProductSerializerV1


@endpoint(
    "products/<int:pk>/",
    version=1,
    view_name="product-detail",
)
class ProductDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1
```

The v1 list implementation:

```python
# products/views/v1.py

from django_api_versioning import endpoint
from rest_framework.generics import ListCreateAPIView

from ..models import Product
from ..serializers import ProductSerializerV1


@endpoint("products/", version=1, view_name="product-list")
class ProductListViewV1(ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1
```

The v2 list implementation:

```python
# products/views/v2.py

from django_api_versioning import endpoint
from rest_framework.generics import ListCreateAPIView

from ..models import Product
from ..serializers import ProductSerializerV2
from .v1 import ProductListViewV1


@endpoint("products/", version=2, view_name="product-list")
class ProductListViewV2(ProductListViewV1):
    serializer_class = ProductSerializerV2

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")

        if category:
            queryset = queryset.filter(category=category)

        return queryset
```

The v2 list implementation inherits from the v1 class, but overrides its serializer and queryset behavior.

The detail endpoint has only a v1 declaration. Its route therefore remains available in v2 and continues to use `ProductDetailView`.

The resulting route ownership is:

| URL | Registered view |
| --- | --- |
| `/api/v1/products/` | `ProductListViewV1` |
| `/api/v2/products/` | `ProductListViewV2` |
| `/api/v1/products/<int:pk>/` | `ProductDetailView` |
| `/api/v2/products/<int:pk>/` | `ProductDetailView` |

The package carries the detail route forward. It does not create a new Python subclass or copy the view implementation.

### Step 3: Include the generated URL patterns

```python
# project/urls.py

from django.urls import include, path

# Import every module containing @endpoint declarations first.
from products.views import common, v1, v2  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

Importing the modules containing `@endpoint` declarations is important. The decorators register their views when Python imports those modules. The package does not automatically discover every application view module.

Import all relevant declaration modules before importing the package's `urlpatterns`. Otherwise, the registry may be incomplete when the URL patterns are read.

### Step 4: Check the routes

```bash
curl http://localhost:8000/api/v1/products/
curl "http://localhost:8000/api/v2/products/?category=electronics"
curl http://localhost:8000/api/v2/products/42/
```

The v1 and v2 list URLs resolve to different view implementations. The v2 detail URL still resolves to the shared detail implementation because no later declaration replaces it.

The actual response bodies depend on the serializers, queryset, and view behavior defined by the application.

## Reverse URL lookup

The package exports `api_reverse()` for reverse lookup with an explicit API version:

```python
from django_api_versioning import api_reverse

url = api_reverse(
    "product-detail",
    version=2,
    pk=42,
)
```

The result is:

```text
/api/v2/products/42/
```

When a URL name is registered in multiple versions, an explicit version avoids ambiguity.

If a name is registered in exactly one version, `api_reverse()` can resolve it without a version argument. If it is registered in multiple versions and no version is supplied, the package raises `AmbiguousVersionError`.

The exception is defined in `django_api_versioning.exceptions`:

```python
from django_api_versioning.exceptions import AmbiguousVersionError
```

If no matching name/version exists, or required route parameters are missing, reverse lookup raises Django's `NoReverseMatch`:

```python
from django.urls import NoReverseMatch

try:
    url = api_reverse("product-detail", version=3, pk=42)
except NoReverseMatch:
    # No route with this name is registered for v3.
    ...
```

A declaration without `view_name` does not provide a named URL for reverse lookup.

Because the same name can exist in multiple generated version patterns, use `api_reverse()` with an explicit version rather than relying on plain Django `reverse()` to select the intended version.

## What happens when a request arrives?

The package's registration model can be summarized as follows:

1. Django imports the modules containing `@endpoint` declarations.
2. Each decorator registers the route and its view implementation in the package registry.
3. The registry resolves collisions according to source-version precedence.
4. The package exposes the resulting URL patterns through `django_api_versioning.urls`.
5. Django resolves an incoming request against those generated patterns and dispatches it to the registered view.

**Now:**

- A request to `/api/v1/products/` resolves to `ProductListViewV1`.
- A request to `/api/v2/products/` resolves to `ProductListViewV2`.
- A request to `/api/v2/products/42/` resolves to `ProductDetailView`, carried forward from its v1 declaration.

These paths are derived from `API_BASE_PATH`, the decorator's `postfix`, and the configured version range. The package does not dynamically traverse Python classes during request dispatch.

This distinction matters when reviewing a versioned API: route ownership is determined during registration, while response behavior is determined by the selected view and the application code it uses.

## What the package provides

In v0.3.4, the package provides a focused routing and URL-registration layer:

- **Declarative registration:** Views register their URL patterns through `@endpoint`.
- **Forward-extending segments:** A declaration at version N covers N through `API_MAX_VERSION`, unless a later segment takes over.
- **Explicit version sets:** `versions` and `ver_range()` support non-contiguous and bounded version selection.
- **URL prefix configuration:** `API_BASE_PATH` and `app_name` control the generated route structure.
- **Version-aware reverse lookup:** `api_reverse()` resolves a named route for a specified API version.
- **Lifecycle middleware:** `LifecycleMiddleware` can add deprecation-related headers and enforce a configured sunset date.

These features change how the project declares and generates versioned URLs. They do not replace the application behavior implemented by Django or DRF views.

## API lifecycle behavior

Version 0.3.4 includes `LifecycleMiddleware`, configured through `API_VERSION_LIFECYCLE`.

Add the middleware to Django's middleware settings:

```python
MIDDLEWARE = [
    # Other middleware
    "django_api_versioning.lifecycle.LifecycleMiddleware",
]
```

Then configure lifecycle metadata:

```python
API_VERSION_LIFECYCLE = {
    1: {
        "status": "deprecated",
        "sunset": "2030-01-01",
    },
    2: {
        "status": "active",
    },
}
```

The example sunset date is in the future relative to this article's publication context. Replace it with the actual retirement date before deploying the configuration.

For a request whose version is 1, the middleware:

- Adds `Deprecation: true` when the configured status is `deprecated`.
- Adds a `Sunset` header when the status is `deprecated` and a sunset date is configured.
- Returns `410 Gone` when the configured sunset date is in the past.

There are important distinctions:

- A status of `retired` alone does not cause a `410 Gone` response.
- A past `sunset` date causes `410 Gone` regardless of whether the status is `deprecated` or `retired`.
- `Deprecation` and `Sunset` response headers are added only when the status is `deprecated`.
- The middleware does not automatically add a `Link` header.

The middleware attempts to identify the version from `request.version`, then from `request.resolver_match.kwargs`, and finally from the request path using `API_BASE_PATH`.

In ordinary DRF request processing, middleware runs before the APIView has initialized its DRF request. Therefore, do not assume that a version selected later through DRF header negotiation is already available as `request.version` when this middleware executes. The path-based extraction is particularly relevant for the package's URL-segment routing.

There is also a standards consideration. The package currently emits `Deprecation: true`, which is a legacy draft-style value. [RFC 9745](https://www.rfc-editor.org/rfc/rfc9745.html) defines the `Deprecation` response header using a date value represented as a Structured Field Date. The package's current value should not be described as a complete RFC 9745 implementation.

The `Sunset` header uses an HTTP-date value. Its meaning and format are defined by [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594.html). The package converts a valid configured ISO date into an HTTP-date value. Use a valid date and verify the resulting value before relying on it in a production response.

The v0.3.4 lifecycle configuration does not define a separate deprecation-date field or validate the ordering between a deprecation date and a sunset date. The application must coordinate its deprecation announcement and retirement schedule. The sunset date should not precede the announced deprecation date.

## What the package does not provide

The package should not be treated as a complete API compatibility or documentation framework.

In v0.3.4, it does not provide:

- **A version-discovery endpoint:** It does not generate an endpoint such as `/api/versions/`.
- **Automatic OpenAPI schema generation:** Version-specific schemas remain the responsibility of documentation tools such as [drf-spectacular](https://drf-spectacular.readthedocs.io/).
- **Direct `ModelViewSet` registration:** A `ModelViewSet` class cannot be passed directly to `@endpoint`, because its `as_view()` method requires an action mapping. A configured `ModelViewSet.as_view({...})` callable can be registered for a specific route, but this does not replace DRF router registration.
- **DRF version negotiation:** The package does not configure a DRF versioning class or independently populate `request.version`.
- **Semantic backward-compatibility checks:** Carrying a route forward does not prove that its response contract remains compatible with earlier clients.

If a view needs `request.version`, configure DRF versioning separately and ensure that its configuration matches the URL structure. See the [DRF versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/).

URL registration and request-version identification are different responsibilities.

## Integration with existing Django projects

For projects using `APIView` or generic class-based views, migration can involve moving route declarations from per-version URLconfs into the view modules.

A version-oriented directory structure can help keep implementations discoverable:

```text
products/
    views/
        common.py
        v1.py
        v2.py
        v3.py
```

The directory structure is an organizational convention, not a routing rule. The package generates paths from `API_BASE_PATH`, `app_name`, and `postfix`, regardless of where the Python modules live.

The URLconf then includes the package-generated patterns once, after importing the modules containing the declarations.

Projects using `ModelViewSet` and `@action` need a more deliberate decision. The package does not automatically convert router actions into separately registered endpoints.

There are three practical choices:

1. Keep DRF routers for ViewSets and use `@endpoint` for other views.
2. Register a configured `ModelViewSet.as_view({...})` callable for an explicitly mapped route.
3. Refactor a ViewSet into APIView or generic views when individual endpoint implementations are a better fit.

The first option is often the least disruptive for an existing router-heavy project. The package and DRF routers can coexist, provided their URL patterns do not overlap.

For the exact ViewSet boundary and the configured-callable limitation, follow the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Trade-offs and scope

### What the package reduces

The package reduces repeated URL-registration declarations for endpoints that remain unchanged across API versions. A declaration at its starting version can cover later versions without another URL registration.

This is useful when endpoints evolve at different version boundaries and the team wants route ownership declared near the corresponding view implementation.

### What the package does not reduce

The number of runtime URL patterns does not decrease. If an endpoint must be available under three version prefixes, Django still needs the corresponding three URL patterns.

The package changes how those patterns are declared and generated, not the number of URLs exposed by the API.

It also does not eliminate the need to maintain version-specific serializers, permissions, querysets, or business logic when those behaviors change.

### When the benefit is smaller

For a small API with one version, a conventional URLconf may be simpler.

The benefit is also smaller when nearly every endpoint changes at every version boundary, because each version still needs its own implementation declaration.

### When the benefit matters most

The registration model is most useful when:

- The API has several supported versions.
- Most endpoints remain unchanged between releases.
- Different endpoints evolve at different version boundaries.
- The team wants route ownership to be explicit near each view implementation.
- The team is prepared to review the version matrix and test the behavior of carried-forward implementations.

The key decision is not simply how many API versions exist. It is whether the project's endpoint-change pattern justifies adopting a separate declarative registration model.

## Next steps

For a practical migration from per-version routing to declarative endpoint registration, see [How to migrate a Django REST API from v1 to v2 with fewer declarations](/migrate-django-rest-api-v1-v2-without-duplicating-routes/).

For deprecation headers and retirement behavior, see [How to deprecate old Django API versions with Sunset headers](/deprecate-old-django-api-versions-sunset-headers/).

For version-aware reverse lookup, see [Reverse URL lookup for versioned Django API endpoints](/reverse-url-lookup-versioned-api-endpoints-django/).

`django-api-versioning` focuses on URL registration and reverse lookup. To evaluate its implementation and adopt the declarative registration model, start with the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
