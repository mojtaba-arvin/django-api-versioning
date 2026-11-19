---
slug: "016-integrate-url-based-versioning-drf-routers-viewsets"
title: "Using DRF Routers with django-api-versioning"
description: "Combine VersionedRouter for DRF ViewSets with django-api-versioning endpoint declarations for APIView and other Django-native views."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "DRF routers"
  - "ViewSets"
  - "URL versioning"
  - "Django REST Framework"
  - "Endpoint registration"
---

# Using DRF Routers with django-api-versioning

> **Package disclosure:** The author is the creator, owner, and maintainer of `django-api-versioning`.

Django REST Framework's `ModelViewSet` and routers are a natural fit for resource-oriented APIs. But not every endpoint in a project maps cleanly to a resource. Search operations, authentication flows, webhooks, and other custom endpoints may be better implemented with `APIView` or `GenericAPIView`.

When a project uses both patterns, URL-based API versioning needs to accommodate both.

[django-api-versioning](https://pypi.org/project/django-api-versioning/) provides declarative URL registration for Django-native views and an optional `VersionedRouter` integration for DRF `ViewSet` and `ModelViewSet` classes. The router delegates URL generation to DRF's `SimpleRouter` and adds version-aware registration and per-route inheritance.

Use the registration mechanism that matches each view type:

- `VersionedRouter` for resource-oriented DRF ViewSets and their generated actions.
- `@endpoint` from `django-api-versioning` for function-based views, Django class-based views, DRF `APIView`, and `GenericAPIView` endpoints.

Both registration styles can coexist in one Django URLconf. For the complete ViewSet contract, see [Versioned DRF ViewSets with Route-Level Inheritance](https://mojtaba-arvin.github.io/django-api-versioning/articles/025-django-api-versioning-viewset-support-limitations/).

`VersionedRouter` delegates route generation to DRF's `SimpleRouter`; `VersionedRouterVersioning` reads the version namespace and exposes it through DRF's `request.version`. The package does not replace DRF's ViewSet dispatch, serializers, permissions, or other request behavior.

## Combining routers and @endpoint in one project

Assume a `Product` model with `name`, `sales`, and `rating` fields, and a foreign key named `category`. The project exposes two types of endpoints:

- Resource-oriented product endpoints, including CRUD operations and custom actions.
- A search endpoint that accepts query parameters and returns a custom response.

The product endpoints use `ModelViewSet`. The search endpoint uses `APIView`.

### Configure the package's version range

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

The default package URL template is `api/v{version}/`. The generated APIView routes will therefore use `/api/v1/` and `/api/v2/`.

### Define the ViewSets

The v1 ViewSet provides a product list, detail, and popular-products action.

```python
# views.py

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Product
from .serializers import ProductSerializerV1, ProductSerializerV2


class ProductViewSetV1(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1

    @action(detail=False, methods=["get"])
    def popular(self, request):
        products = Product.objects.order_by("-sales")[:5]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
```

The v2 ViewSet inherits the common behavior and changes the serializer and popular-products query. It also adds a detail action for recommendations.

```python
class ProductViewSetV2(ProductViewSetV1):
    serializer_class = ProductSerializerV2

    @action(detail=False, methods=["get"])
    def popular(self, request):
        products = Product.objects.order_by("-sales", "-rating")[:10]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def recommendations(self, request, pk=None):
        product = self.get_object()

        similar = Product.objects.filter(
            category=product.category
        ).exclude(id=pk)[:5]

        serializer = self.get_serializer(similar, many=True)
        return Response(serializer.data)
```

### Define the non-resource endpoint

The search endpoint does not need the CRUD actions provided by `ModelViewSet`. It uses `APIView` and registers each version with `@endpoint`.

```python
from django_api_versioning import endpoint
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product


@endpoint("search/", version=1)
class SearchViewV1(APIView):
    def get(self, request):
        query = request.query_params.get("q", "")
        results = Product.objects.filter(name__icontains=query)

        return Response({
            "count": results.count(),
            "ids": list(
                results.values_list("id", flat=True)
            ),
        })


@endpoint("search/", version=2)
class SearchViewV2(APIView):
    def get(self, request):
        query = request.query_params.get("q", "")
        results = Product.objects.filter(name__icontains=query)

        return Response({
            "count": results.count(),
            "results": [
                {
                    "id": product.id,
                    "name": product.name,
                    "category": product.category_id,
                }
                for product in results[:20]
            ],
        })
```

The v2 search response includes product details instead of returning only IDs. The v2 declaration replaces the v1 implementation for the v2 route.

### Register both URL sources

Register the ViewSets with one `VersionedRouter`, then include the package-generated URL patterns for the APIView endpoints.

```python
# urls.py

from django.urls import include, path
from . import views  # noqa: F401 — import during URLconf initialization

from django_api_versioning.routers import VersionedRouter
from django_api_versioning.urls import urlpatterns as api_urlpatterns


product_router = VersionedRouter()
product_router.register(
    "products",
    views.ProductViewSetV1,
    version=1,
    basename="product",
)
product_router.register(
    "products",
    views.ProductViewSetV2,
    version=2,
    basename="product",
)


urlpatterns = [
    # VersionedRouter-generated URLs for ViewSets.
    *product_router.urls,

    # Package-generated URLs for APIView endpoints.
    path("", include(api_urlpatterns)),
]
```

The `from . import views` import executes the `@endpoint` decorators; the package does not automatically discover view modules. Its exported `urlpatterns` references the registry's shared list rather than a copy, so importing that list before the view module does not permanently capture an empty snapshot. Keep imports explicit during URLconf initialization and ensure registration is complete before request resolution.

If the decorated views are in separate modules, import each of those modules during URLconf initialization.

### Resulting URL structure

The routers generate the product routes, while `@endpoint` generates the search routes.

| URL | Registration source |
| --- | --- |
| `/api/v1/products/` | v1 router |
| `/api/v1/products/<pk>/` | v1 router |
| `/api/v1/products/popular/` | v1 router |
| `/api/v1/search/` | `@endpoint` |
| `/api/v2/products/` | v2 router |
| `/api/v2/products/<pk>/` | v2 router |
| `/api/v2/products/popular/` | v2 router |
| `/api/v2/products/<pk>/recommendations/` | v2 router |
| `/api/v2/search/` | `@endpoint` |

Both registration mechanisms produce URLs under the same `/api/v{version}/` structure.

**Now:**

- Product list, detail, and custom action routes are generated by `VersionedRouter` through DRF's `SimpleRouter`.
- Search routes are generated by the package's endpoint registry.
- The v1 search implementation carries forward only until a later declaration overrides it.
- The v2 search declaration supplies the implementation for v2.

**Scope: routing and version selection only.** `VersionedRouter` registers DRF-generated actions and `VersionedRouterVersioning` exposes the selected URL version through `request.version`. The package does not determine whether a response change is backward-compatible.

For the exact package behavior—including version ranges, collision precedence, and URLconf import behavior—see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Why @endpoint does not replace ViewSet routing

A DRF ViewSet class requires an action mapping when `as_view()` is called. For example:

```python
ProductViewSetV1.as_view({
    "get": "list",
    "post": "create",
})
```

The package's `@endpoint` decorator calls `as_view()` when it receives a class-based view. It does not supply the action mapping required by a ViewSet.

Consequently, decorating a `ModelViewSet` class directly is not supported:

```python
# Not supported

@endpoint("products/", version=1)
class ProductViewSet(viewsets.ModelViewSet):
    ...
```

A configured ViewSet callable can be registered for one explicitly configured route:

```python
@endpoint("products/", version=1)
def product_list(request):
    ...
```

Alternatively, a configured callable can be passed directly to the decorator:

```python
product_list = endpoint(
    "products/",
    version=1,
)(
    ProductViewSetV1.as_view({
        "get": "list",
        "post": "create",
    })
)
```

This registers one route with the specified action mapping. It does not replace a router's responsibility for generating list, detail, and custom-action routes.

For resource-oriented endpoints, use `VersionedRouter` when you want package-managed version inheritance. Use `@endpoint` for APIView or GenericAPIView endpoints that do not fit the ViewSet model.

## Manual per-version routers for ViewSet-only APIs

If every endpoint in a project is resource-oriented, plain DRF `SimpleRouter` instances mounted under manually managed version prefixes are still a valid DRF-only option. The package is not required when you do not need its version registry or route inheritance; use `VersionedRouter` when you do.

```python
# urls.py

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import ProductViewSetV1, ProductViewSetV2


v1_router = SimpleRouter()
v1_router.register(
    "products",
    ProductViewSetV1,
    basename="v1-product",
)

v2_router = SimpleRouter()
v2_router.register(
    "products",
    ProductViewSetV2,
    basename="v2-product",
)


urlpatterns = [
    path("api/v1/", include(v1_router.urls)),
    path("api/v2/", include(v2_router.urls)),
]
```

Distinct basenames such as `v1-product` and `v2-product` avoid URL-name collisions between the two router registrations.

This approach keeps the URL registration explicit and uses DRF's built-in routing behavior. Its trade-off is that every version needs its own router registration and URL include.

## Dynamic router registration

When a project has many ViewSets and versions, router registrations can be built from a configuration structure rather than written individually.

For example, use integer version keys so sorting remains numeric:

```python
# urls.py

from django.urls import include, path
from django.utils.module_loading import import_string
from rest_framework.routers import SimpleRouter


VERSIONED_ENDPOINTS = {
    "products": {
        1: "myapp.views.ProductViewSetV1",
        2: "myapp.views.ProductViewSetV2",
    },
    "categories": {
        1: "myapp.views.CategoryViewSetV1",
        2: "myapp.views.CategoryViewSetV2",
    },
    "reviews": {
        1: "myapp.views.ReviewViewSetV1",
        2: "myapp.views.ReviewViewSetV2",
    },
}


def build_routers_by_version():
    routers = {}

    for endpoint_name, versions in VERSIONED_ENDPOINTS.items():
        for version, viewset_path in versions.items():
            if version not in routers:
                routers[version] = SimpleRouter()

            viewset_class = import_string(viewset_path)

            routers[version].register(
                endpoint_name,
                viewset_class,
                basename=f"v{version}-{endpoint_name}",
            )

    return routers


urlpatterns = [
    path(
        f"api/v{version}/",
        include(router.urls),
    )
    for version, router in sorted(
        build_routers_by_version().items()
    )
]
```

This centralizes the router configuration. Adding a ViewSet or version means updating the configuration instead of adding another `register()` call or manually editing the URL pattern list.

There are trade-offs:

- ViewSet references are strings, so misspelled import paths fail when the URLconf is imported.
- The configuration is less directly connected to the class definitions.
- The implementation is custom project code that the team must maintain.

This is a DRF-only configuration technique. It does not use or extend `django-api-versioning`.

## Choosing the registration pattern

| Aspect | Per-version routers | Dynamic routers | Mixed project |
| --- | --- | --- | --- |
| Resource-oriented ViewSets | DRF `SimpleRouter` | DRF `SimpleRouter` | `VersionedRouter` |
| Non-resource APIView endpoints | Manual `path()` entries | Manual `path()` entries | `@endpoint` |
| Router registration | Explicit per version | Generated from configuration | Explicit for ViewSets |
| Package dependency | No | No | Yes, for APIView registration |
| Import-order requirement | No package-specific requirement | No package-specific requirement | Explicit module imports during URLconf initialization; exported urlpatterns is a shared list, not a frozen copy |

The mixed approach is useful when a project has both resource-oriented and non-resource endpoints. It avoids forcing every endpoint into a ViewSet while retaining DRF's router-generated CRUD routes.

## Trade-offs and scope

**Per-version routers are appropriate when:**

- All or nearly all endpoints map naturally to resources.
- `ModelViewSet` and `@action` cover the required behavior.
- Explicit router registration is manageable for the project's version structure.

**Dynamic router registration is appropriate when:**

- Router registration duplication is a recurring maintenance concern.
- The team prefers a central configuration structure.
- The project is comfortable maintaining string-based ViewSet references.

**A mixed project is appropriate when:**

- Some endpoints are resource-oriented and others require APIView-style handling.
- The project wants consistent versioned URL prefixes across both registration mechanisms.
- The team accepts maintaining two separate URL registration mechanisms.

### When the package's benefit is smaller

If every endpoint is resource-oriented and can be represented by `ModelViewSet`, per-version routers are the direct DRF solution. Adding the package would introduce another registration mechanism without solving a problem the routers do not already handle.

The package adds value when you want per-route version inheritance for ViewSets, when non-ViewSet endpoints also need versioned registration, or when both patterns coexist in one application.

## Next steps

For projects that combine resource-oriented ViewSets with APIView-based endpoints, use `VersionedRouter` for ViewSets and `@endpoint` for individual APIView-style endpoints. See the [dedicated ViewSet integration guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/025-django-api-versioning-viewset-support-limitations/) for version registration, inheritance, reversal, and lifecycle boundaries.

Explore the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning) for the implementation and integration examples.
