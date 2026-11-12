---
slug: "016-integrate-url-based-versioning-drf-routers-viewsets"
title: "Using DRF Routers with django-api-versioning"
description: "Combine per-version DRF routers for ViewSets with django-api-versioning for APIView endpoints, and understand the package's ViewSet limitation."
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

Django REST Framework's `ModelViewSet` and routers are a natural fit for resource-oriented APIs. But not every endpoint in a project maps cleanly to a resource. Search operations, authentication flows, webhooks, and other custom endpoints may be better implemented with `APIView` or `GenericAPIView`.

When a project uses both patterns, URL-based API versioning needs to accommodate both.

[django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/) provides declarative URL registration for function-based views and Django class-based views, including DRF's `APIView` and `GenericAPIView`. It does not directly register `ModelViewSet` classes.

The practical approach is to use:

- DRF routers for resource-oriented ViewSets.
- `@endpoint` from `django-api-versioning` for non-ViewSet endpoints.

Both registration mechanisms can coexist in one Django URLconf and use the same versioned URL structure.

The package is maintained by the author. Its responsibility is endpoint registration and URL routing; it does not replace DRF routers or perform DRF request-version negotiation.

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
from rest_framework.views import APIView


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

Create one `SimpleRouter` per version for the ViewSets, then include the package-generated URL patterns for the APIView endpoints.

```python
# urls.py

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views  # noqa: F401 — execute endpoint declarations first

from django_api_versioning.urls import urlpatterns as api_urlpatterns


v1_router = SimpleRouter()
v1_router.register(
    r"products",
    views.ProductViewSetV1,
    basename="v1-product",
)

v2_router = SimpleRouter()
v2_router.register(
    r"products",
    views.ProductViewSetV2,
    basename="v2-product",
)


urlpatterns = [
    # Router-generated URLs for ViewSets.
    path("api/v1/", include(v1_router.urls)),
    path("api/v2/", include(v2_router.urls)),

    # Package-generated URLs for APIView endpoints.
    path("", include(api_urlpatterns)),
]
```

The `from . import views` import must execute before `api_urlpatterns` is imported. The `@endpoint` decorators register routes when their modules are imported; the package does not automatically discover view modules.

If the decorated views are in separate modules, import each of those modules before reading the generated URL patterns.

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

- Product list, detail, and custom action routes are generated by DRF routers.
- Search routes are generated by the package's endpoint registry.
- The v1 search implementation carries forward only until a later declaration overrides it.
- The v2 search declaration supplies the implementation for v2.

**Scope: routing only.** The package does not register ViewSet actions, configure DRF's `request.version`, or determine whether a response change is backward-compatible.

For the exact package behavior—including version ranges, collision precedence, and URLconf import order—see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Why @endpoint does not replace ViewSet routers

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

For resource-oriented endpoints, use DRF routers. Use `@endpoint` for the APIView or GenericAPIView endpoints that do not fit the ViewSet model.

## Per-version routers for ViewSet-only APIs

If every endpoint in a project is resource-oriented, per-version routers are sufficient. The package is not required.

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
| Resource-oriented ViewSets | DRF routers | DRF routers | DRF routers |
| Non-resource APIView endpoints | Manual `path()` entries | Manual `path()` entries | `@endpoint` |
| Router registration | Explicit per version | Generated from configuration | Explicit for ViewSets |
| Package dependency | No | No | Yes, for APIView registration |
| Import-order requirement | No package-specific requirement | No package-specific requirement | Required for `@endpoint` declarations |

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

The package adds value when non-ViewSet endpoints also need versioned registration, especially when many of those endpoints remain unchanged across releases.

## Next steps

For projects that combine resource-oriented ViewSets with APIView-based endpoints, keep each endpoint on the registration mechanism that fits its view type. The package complements DRF routers; it does not replace them.

Explore the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning) for the implementation and integration examples.
