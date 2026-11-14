---
slug: "025-django-api-versioning-viewset-support-limitations"
title: "django-api-versioning ViewSet Support and Limitations"
description: "Understand why @endpoint cannot decorate ViewSet classes, and how to register ViewSet routes with DRF routers or configured as_view() callables."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "django-api-versioning"
  - "Django REST Framework"
  - "ViewSets"
  - "API routing"
  - "API versioning"
---

# django-api-versioning ViewSet Support and Limitations

`django-api-versioning` supports versioned registration of configured DRF ViewSet callables, but it does not accept `ModelViewSet` classes directly in `@endpoint`. A ViewSet requires an action mapping when converted into a view callable.

The distinction matters because DRF ViewSets require an explicit action mapping when converted into callable views. The package's decorator does not infer that mapping. However, a configured `ModelViewSet.as_view({...})` callable can be registered through `@endpoint`, allowing ViewSet-based handlers to participate in the package's version registry.

The package is maintained by the author of this article. Its ViewSet integration boundary is specific:

- Register configured ViewSet callables through `@endpoint` when you want those routes to use the package's version-registration behavior.
- Use DRF routers when preserving router-generated routes and router-managed `@action` configuration is required.

The package does not automatically integrate with DRF routers or replace their route-generation behavior.

For installation and the package's public API, see [django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/).

This article covers:

- Which DRF views `@endpoint` can register directly.
- Why ViewSet classes require an action mapping.
- How to register configured ViewSet callables with `@endpoint`.
- When a DRF router is preferable for preserving router-managed behavior.
- How custom actions, URL names, pagination, and filtering behave in each approach.

The examples use a `Product` model with `name`, `sales`, `rating`, `likes`, and `category` fields, plus separate serializers for v1 and v2. Adapt the model, serializers, and test setup to your project.

## Version settings

The package-based pattern uses `@endpoint`, so its version settings must allow both versions:

```python
# settings.py
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

The default value of `API_MAX_VERSION` is `1`. A declaration that registers version 2 requires the maximum to be raised; otherwise, the package raises `InvalidVersionError`.

The package's default `API_BASE_PATH` is:

```python
API_BASE_PATH = "api/v{version}/"
```

The package combines this base path with the `postfix` supplied to `@endpoint`. For example, `version=1` and `postfix="products/"` produce `/api/v1/products/`.

The `postfix` argument is the route suffix, not the complete URL. The complete URL construction and version-registration rules are documented in the [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

The router-based pattern shown later uses explicit URL prefixes. Those router-generated routes are separate from the package's registry, so the package's version settings do not determine which ViewSet callable a router registers.

## What `@endpoint` supports

The decorator registers a class-based view by calling its `as_view()` method without arguments. In DRF, this works with `APIView` and its subclasses, including generic views:

- `APIView`
- `GenericAPIView`
- `ListAPIView`
- `CreateAPIView`
- `ListCreateAPIView`
- `RetrieveAPIView`
- `UpdateAPIView`
- `DestroyAPIView`
- `RetrieveUpdateAPIView`
- `RetrieveDestroyAPIView`
- `RetrieveUpdateDestroyAPIView`

This is a list of relevant examples, not an exhaustive list of every possible generic-view subclass.

It also works with `GenericAPIView` combined with mixins, provided the class defines the HTTP handler methods (`get()`, `post()`, and so on) that invoke the mixin methods.

`ModelViewSet`, `ReadOnlyModelViewSet`, `ViewSet`, and `GenericViewSet` cannot be decorated directly. Their `as_view()` method requires an `actions` argument that maps HTTP methods to ViewSet actions.

Two separate conditions matter:

1. **Registration:** `as_view()` must succeed when called without arguments.
2. **Usability:** the resulting view must implement the HTTP handler methods needed to serve requests.

A class can pass the registration check but still be unusable for a particular HTTP method. For example, `GenericAPIView` alone does not implement `get()`, `post()`, or other HTTP handlers. A GET request to such a view will not automatically invoke a mixin's `list()` method.

A more specific generic view, such as `ListAPIView`, already provides the handler:

```python
# views.py
from django_api_versioning import endpoint
from rest_framework.generics import ListAPIView

from .models import Product
from .serializers import ProductSerializerV1


@endpoint("products/", version=1, view_name="product-list-v1")
class ProductListViewV1(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1
```

Alternatively, define the handler explicitly when combining a mixin with `GenericAPIView`:

```python
# views.py
from django_api_versioning import endpoint
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin

from .models import Product
from .serializers import ProductSerializerV1


@endpoint(
    "products/",
    version=1,
    view_name="product-list-mixin-v1",
)
class ProductListMixinViewV1(ListModelMixin, GenericAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
```

These are alternative implementations of the same route. Use one, not both, in the same URL registry. Both classes can be registered because neither requires an action mapping in `as_view()`.

A direct `ModelViewSet` declaration does not work:

```python
# Does not work: ModelViewSet requires an action mapping.

from rest_framework import viewsets

# @endpoint("products/", version=1, view_name="product-list-v1")
# class ProductViewSetV1(viewsets.ModelViewSet):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializerV1
```

The resulting error is raised by DRF's `ViewSetMixin.as_view()`:

```text
TypeError: The `actions` argument must be provided when calling `.as_view()` on a ViewSet. For example `.as_view({'get': 'list'})`
```

The distinction is important: the package can register a configured ViewSet callable, but it cannot infer the action mapping required by a ViewSet class.

## Registering ViewSets with `@endpoint`

`ModelViewSet.as_view({...})` accepts the action mapping that the decorator cannot provide. It returns a callable view, which `@endpoint` can register.

This approach keeps ViewSet-based endpoints inside the package's URL registry. You declare the HTTP method mapping and route explicitly rather than relying on a router to generate them.

In this pattern, custom action methods are ordinary methods rather than router-managed `@action` methods. The `actions` dictionary maps HTTP methods to method names; it does not generate routes or apply the action metadata normally handled by a router.

The `detail` and `basename` arguments should also be passed explicitly. A router normally supplies these values when it creates the ViewSet's routes. When you call `as_view()` directly, there is no router to provide them.

```python
# views.py
from rest_framework import viewsets
from rest_framework.response import Response

from .models import Product
from .serializers import ProductSerializerV1, ProductSerializerV2


class ProductViewSetV1(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1

    def popular(self, request):
        products = Product.objects.order_by("-sales")[:5]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class ProductViewSetV2(ProductViewSetV1):
    serializer_class = ProductSerializerV2

    def popular(self, request):
        products = Product.objects.order_by("-sales", "-rating")[:10]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    def trending(self, request):
        products = Product.objects.order_by("-likes")[:20]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    def rate(self, request, pk=None):
        product = self.get_object()
        return Response({
            "id": product.id,
            "rating": product.rating,
        })

    def best_sellers(self, request):
        products = Product.objects.order_by("-sales")[:10]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
```

Register the collection and detail routes separately:

```python
# urls.py
from django.urls import include, path

from django_api_versioning import endpoint
from .views import ProductViewSetV1, ProductViewSetV2


# Standard ModelViewSet routes: collection and detail.

@endpoint("products/", version=1, view_name="product-list-v1")(
    ProductViewSetV1.as_view(
        {
            "get": "list",
            "post": "create",
        },
        detail=False,
        basename="product",
    )
)

@endpoint("products/<int:pk>/", version=1, view_name="product-detail-v1")(
    ProductViewSetV1.as_view(
        {
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        },
        detail=True,
        basename="product",
    )
)

@endpoint("products/", version=2, view_name="product-list-v2")(
    ProductViewSetV2.as_view(
        {
            "get": "list",
            "post": "create",
        },
        detail=False,
        basename="product",
    )
)

@endpoint("products/<int:pk>/", version=2, view_name="product-detail-v2")(
    ProductViewSetV2.as_view(
        {
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        },
        detail=True,
        basename="product",
    )
)


# Custom actions are separate endpoint declarations.

@endpoint("products/popular/", version=1, view_name="product-popular-v1")(
    ProductViewSetV1.as_view(
        {"get": "popular"},
        detail=False,
        basename="product",
    )
)

@endpoint("products/popular/", version=2, view_name="product-popular-v2")(
    ProductViewSetV2.as_view(
        {"get": "popular"},
        detail=False,
        basename="product",
    )
)

@endpoint("products/trending/", version=2, view_name="product-trending-v2")(
    ProductViewSetV2.as_view(
        {"get": "trending"},
        detail=False,
        basename="product",
    )
)

@endpoint("products/<int:pk>/rate/", version=2, view_name="product-rate-v2")(
    ProductViewSetV2.as_view(
        {"get": "rate"},
        detail=True,
        basename="product",
    )
)

@endpoint(
    "products/best-sellers/",
    version=2,
    view_name="product-best-sellers-v2",
)(
    ProductViewSetV2.as_view(
        {"get": "best_sellers"},
        detail=False,
        basename="product",
    )
)


# Import package urlpatterns only after all endpoint declarations have run.
from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The import order is intentional. The declarations above execute before `django_api_versioning.urls` is imported. This ensures that the package's shared URL pattern list contains the registered routes when it is included in the URLconf.

With the default `API_BASE_PATH` of `api/v{version}/`:

- `version=1` and `postfix="products/"` register `/api/v1/products/`.
- `version=2` and `postfix="products/"` register `/api/v2/products/`.
- `version=2` and `postfix="products/<int:pk>/"` register `/api/v2/products/<int:pk>/`.

**Scope: routing only.** `django-api-versioning` registers versioned URL patterns. It does not configure DRF's version negotiation, set `request.version`, or replace ViewSet action configuration.

**Now:**

- `GET /api/v1/products/` → `ProductViewSetV1.list`
- `GET /api/v2/products/` → `ProductViewSetV2.list`
- `GET /api/v1/products/popular/` → `ProductViewSetV1.popular`
- `GET /api/v2/products/popular/` → `ProductViewSetV2.popular`
- `GET /api/v2/products/trending/` → `ProductViewSetV2.trending`
- `GET /api/v2/products/<int:pk>/rate/` → `ProductViewSetV2.rate`
- `GET /api/v2/products/best-sellers/` → `ProductViewSetV2.best_sellers`

### How version registration works here

Notice that `version=1` does not register only a v1 route. According to the package contract, `version=N` registers the declaration from version N through `API_MAX_VERSION`.

With `API_MAX_VERSION = 2`, the first collection declaration registers the v1 and v2 routes using `ProductViewSetV1`. The subsequent v2 declaration registers the same v2 route with `ProductViewSetV2`.

The registry prefers the declaration with the higher source version, so the v2 registration replaces the earlier v2 registration.

The final result is:

| Route version | Registered view |
| --- | --- |
| v1 | `ProductViewSetV1` |
| v2 | `ProductViewSetV2` |

The same replacement behavior applies to the detail route and the `popular` action.

This is registration-time version inheritance through range expansion and collision resolution. It is not request-time fallback traversal: the package does not receive a request for v2 and then search v1 for a handler.

The distinction between an unavailable version and an endpoint that is not registered in an existing version also matters.

In this example, v1 exists, but `trending` is not registered for v1. A request to `/api/v1/products/trending/` therefore returns 404. A request to `/api/v3/products/` also returns 404 because `API_MAX_VERSION` is 2 and no v3 route is registered. These are different registration situations even though both requests produce a 404 response.

### What this pattern registers

The example declares:

- Collection and detail routes for v1.
- Collection and detail routes for v2.
- `popular` for both versions.
- `trending` only for v2.
- `rate` only for v2.
- `best_sellers` only for v2.

The package registers each configured callable. It does not infer additional routes from the methods present on the ViewSet class.

A method that exists on a ViewSet but is not included in an `as_view({...})` mapping and has no corresponding endpoint declaration is unreachable through the API.

### Organizing version-specific implementations

For larger projects, version-specific implementations can live in separate modules while the package handles route registration.

For example:

```text
apps/
└── catalog/
    └── api/
        ├── v1/
        │   └── views.py
        ├── v2/
        │   └── views.py
        └── registrations.py

project/
└── urls.py
```

The v1 and v2 modules contain their respective ViewSet classes. The `registrations.py` module imports those classes and applies the configured `as_view()` callables with `@endpoint`.

The project URLconf imports the registration module before importing the package URL patterns:

```python
# project/urls.py
from django.urls import include, path

from apps.catalog.api import registrations as _registrations
from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The intentionally unused `_registrations` import executes the declarations in that module. The package registry then supplies the versioned routes through `api_urlpatterns`.

This organization separates version-specific view implementations from route registration without requiring a separate manually maintained root URLconf for every API version.

### When this pattern fits

Use configured `as_view()` callables with `@endpoint` when:

- You want the URLconf to include the package's `api_urlpatterns`.
- You want configured ViewSet callables to participate in the package's version registration and replacement behavior.
- Your custom actions do not depend on router-managed `@action` configuration.
- You are comfortable declaring each route and HTTP method mapping explicitly.

The cost is additional boilerplate: one `@endpoint` declaration and one configured `as_view()` call per route and version.

## DRF router per version

When preserving router-generated routes and `@action` configuration is a requirement, a router per version is the appropriate DRF approach.

This is a standard DRF routing pattern. It is separate from the package's registry and does not mean that `django-api-versioning` automatically registers router-generated ViewSet routes.

The example below defines two versions of the product API. Version 1 exposes the standard ViewSet routes and a `popular` collection action. Version 2 changes the `popular` behavior and adds `trending`, `rate`, and `best_sellers`.

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


class ProductViewSetV2(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV2

    @action(detail=False, methods=["get"])
    def popular(self, request):
        products = Product.objects.order_by("-sales", "-rating")[:10]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def trending(self, request):
        products = Product.objects.order_by("-likes")[:20]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def rate(self, request, pk=None):
        product = self.get_object()
        return Response({
            "id": product.id,
            "rating": product.rating,
        })

    @action(
        detail=False,
        methods=["get"],
        url_path="best-sellers",
        url_name="best_sellers",
    )
    def best_sellers(self, request):
        products = Product.objects.order_by("-sales")[:10]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
```

Register each ViewSet with a separate `SimpleRouter`:

```python
# urls.py
from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import ProductViewSetV1, ProductViewSetV2


v1_router = SimpleRouter()
v1_router.register("products", ProductViewSetV1, basename="v1-product")

v2_router = SimpleRouter()
v2_router.register("products", ProductViewSetV2, basename="v2-product")

urlpatterns = [
    path("api/v1/", include(v1_router.urls)),
    path("api/v2/", include(v2_router.urls)),
]
```

The routers generate these routes:

| Route | v1 | v2 |
| --- | --- | --- |
| Product collection | `/api/v1/products/` | `/api/v2/products/` |
| Product detail | `/api/v1/products/<pk>/` | `/api/v2/products/<pk>/` |
| Popular products | `/api/v1/products/popular/` | `/api/v2/products/popular/` |
| Trending products | — | `/api/v2/products/trending/` |
| Product rating | — | `/api/v2/products/<pk>/rate/` |
| Best sellers | — | `/api/v2/products/best-sellers/` |

Every standard ViewSet route and every discovered `@action` is registered by the corresponding router.

The separate basenames also produce distinct Django URL names. For example, the v1 `popular` action is named `v1-product-popular`, while the v2 action is named `v2-product-popular`. This avoids registering the same URL name in both version route sets.

Use this pattern when:

- Your API already uses `ModelViewSet` and router-managed `@action` methods.
- You need DRF to generate standard and custom action routes.
- You rely on action-specific router configuration.
- You want to retain the existing DRF routing structure without registering these routes through the package.

This approach preserves DRF's router behavior, but it does not use `django-api-versioning` for these ViewSet routes.

## Route format control

The two approaches also differ in how custom route paths and URL names are configured.

### Router-generated action routes

With a router, `@action` controls a custom route's path and URL name.

For example, the `best_sellers` method in the earlier `ProductViewSetV2` definition uses:

```python
@action(
    detail=False,
    methods=["get"],
    url_path="best-sellers",
    url_name="best_sellers",
)
def best_sellers(self, request):
    products = Product.objects.order_by("-sales")[:10]
    serializer = self.get_serializer(products, many=True)
    return Response(serializer.data)
```

With the v2 router registered using `basename="v2-product"`, the router generates:

```text
/api/v2/products/best-sellers/
```

The URL name is based on the router's basename and the action's `url_name`, producing `v2-product-best_sellers`.

### `@endpoint` controls the route

Without a router, the `@endpoint` declaration defines the path and Django URL name:

```python
@endpoint(
    "products/best-sellers/",
    version=2,
    view_name="product-best-sellers-v2",
)(
    ProductViewSetV2.as_view(
        {"get": "best_sellers"},
        detail=False,
        basename="product",
    )
)
```

There is no `@action` on `best_sellers` in this example. The endpoint declaration is the source of the route and its Django URL name.

The `url_path` and `url_name` arguments of `@action` are therefore not involved.

## What configured `as_view()` does not set up

Calling `as_view()` directly bypasses the router's route-generation and action-configuration process. There are several consequences to understand.

### `self.detail` and `self.basename`

The router normally sets these attributes on the ViewSet instance for each generated route.

When using `as_view()` directly, pass them explicitly:

```python
# Collection-level route
ProductViewSetV2.as_view(
    {"get": "popular"},
    detail=False,
    basename="product",
)

# Detail-level route
ProductViewSetV2.as_view(
    {"get": "rate"},
    detail=True,
    basename="product",
)
```

`detail` distinguishes collection routes from detail routes. It is also available to code that inspects the current ViewSet configuration.

`basename` provides the prefix used by `reverse_action()` to construct action URL names.

DRF's `ViewSetMixin.as_view()` accepts these as initialization keyword arguments and assigns them to the view instance.

### `reverse_action()`

In the router pattern, the router supplies the ViewSet's `basename`, while `@action` supplies the action's URL name.

For the v2 router in this article, the registration uses `basename="v2-product"`. Therefore:

```python
self.reverse_action("popular")
```

resolves the action URL using the name `v2-product-popular`.

The v1 router uses `basename="v1-product"`, so the corresponding name is `v1-product-popular`.

In the configured-callable pattern, there is no router and no `@action` metadata. You must make the `basename`, `view_name`, and `reverse_action()` argument consistent yourself.

Consider this registration:

```python
@endpoint(
    "products/popular/",
    version=2,
    view_name="product-popular-v2",
)(
    ProductViewSetV2.as_view(
        {"get": "popular"},
        detail=False,
        basename="product",
    )
)
```

The Django URL name is `product-popular-v2`.

Therefore, the corresponding call is:

```python
self.reverse_action("popular-v2")
```

DRF prepends the ViewSet's basename to the supplied action URL name, producing `product-popular-v2`.

This call would not resolve the registered route:

```python
self.reverse_action("popular")
```

It would look for `product-popular`, which is not the registered name in this example.

This naming alignment is an application-level convention in the configured-callable pattern. The package does not automatically derive the `reverse_action()` name from `view_name`.

If you prefer the shorter call:

```python
self.reverse_action("popular")
```

then register the route with a matching name:

```python
view_name="product-popular"
```

The important requirement is that the final name constructed by `reverse_action()` matches an existing Django URL pattern.

### Custom actions in the configured-callable pattern

The configured-callable pattern should generally use plain methods rather than methods decorated with `@action`.

The reason is that `@action` carries metadata that DRF's router normally reads when generating routes. This includes configuration such as:

- `permission_classes`
- `serializer_class`
- `filter_backends`
- `url_path`
- `url_name`
- Other action-specific initialization settings

When you map a method directly through `as_view()`, the HTTP method mapping does not reproduce the router's action setup.

A method decorated with `@action` can still be mapped explicitly, but this is not a drop-in replacement for router registration. DRF warns that direct `as_view()` usage for `@action` methods can bypass router configuration, including action-specific permission and serializer settings.

For example, this is the preferred style for the configured-callable pattern:

```python
class ProductViewSetV2(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV2

    def popular(self, request):
        products = Product.objects.order_by("-sales", "-rating")[:10]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
```

If the action needs a different permission policy or serializer, implement that behavior explicitly in the method or in an appropriate ViewSet override.

If you rely on router-managed action configuration, use the router-based pattern instead.

## Pagination and filtering

Pagination and filtering for the standard `list` action work the same way in both patterns. They are DRF view-level behaviors, not features of the package's version registration.

For example, define different pagination classes for each version:

```python
from rest_framework.pagination import PageNumberPagination


class SmallPagination(PageNumberPagination):
    page_size = 20


class LargePagination(PageNumberPagination):
    page_size = 50
```

Add the relevant attributes to the existing ViewSet classes:

```python
ProductViewSetV1.pagination_class = SmallPagination
ProductViewSetV2.pagination_class = LargePagination
```

Alternatively, put `pagination_class` directly in each class definition. These assignments are shown separately to avoid redefining the ViewSet classes and accidentally replacing their earlier methods.

The standard `list` action uses DRF's normal pagination lifecycle.

### Custom actions do not automatically paginate

A custom action returns the response implemented by its method. It does not automatically pass its queryset through the list action's pagination flow.

For example:

```python
def popular(self, request):
    products = Product.objects.order_by("-sales")[:5]
    serializer = self.get_serializer(products, many=True)
    return Response(serializer.data)
```

This returns up to five products without invoking pagination.

To paginate a custom action, call the pagination methods explicitly:

```python
def popular(self, request):
    queryset = Product.objects.order_by("-sales")

    page = self.paginate_queryset(queryset)

    if page is not None:
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    serializer = self.get_serializer(queryset, many=True)
    return Response(serializer.data)
```

This applies to custom actions in both patterns. It is a DRF behavior, not a difference between `@endpoint` and routers.

### Filtering in custom actions

Filtering backends are also not automatically applied to arbitrary custom action querysets.

If a custom action should respect the configured filter backends, call `self.filter_queryset()` explicitly:

```python
def popular(self, request):
    queryset = Product.objects.order_by("-sales")
    queryset = self.filter_queryset(queryset)

    page = self.paginate_queryset(queryset)

    if page is not None:
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    serializer = self.get_serializer(queryset, many=True)
    return Response(serializer.data)
```

The method's behavior is explicit: filter the queryset, paginate it if pagination is configured, then serialize the resulting page or full queryset.

## What you give up with generic views

You can avoid the ViewSet limitation by using generic views directly. This works well when your API is naturally organized around individual views rather than ViewSet actions.

However, converting a ViewSet-based API to generic views changes how the endpoints are organized.

### Custom actions become separate views

A ViewSet can group multiple actions in one class:

```python
class ProductViewSetV1(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1

    @action(detail=False)
    def popular(self, request):
        ...
```

With generic views, `popular` becomes a separate view class with its own `@endpoint` declaration.

### Standard actions are split across views

A typical `ModelViewSet` provides list, create, retrieve, update, partial update, and destroy actions.

With generic views, the collection and detail routes can be separated:

- `ListCreateAPIView` handles collection GET and POST.
- `RetrieveUpdateDestroyAPIView` handles detail GET, PUT, PATCH, and DELETE.

Other combinations can be used when the endpoint needs fewer operations.

### Router-managed action metadata is no longer available

Generic views do not use the ViewSet router's `@action` mechanism. Each endpoint has its own class and configuration.

For a ViewSet-heavy API with many custom actions, converting every action into a separate generic view may create more code than retaining the ViewSets and choosing between configured callables and routers.

## Testing

Test the routes and behavior of each API version independently.

The following tests illustrate route availability and verify that each version resolves to its intended ViewSet class. They assume the `Product` model, serializers, database configuration, and URL configuration already exist in the project. The example values passed to `Product.objects.create()` must match the actual model fields and required constraints.

The tests apply to either routing pattern, provided the selected URLconf exposes the same route surface.

```python
# tests/test_products.py
from django.test import TestCase
from django.urls import resolve
from django.urls.exceptions import Resolver404
from rest_framework.test import APIClient

from .models import Product
from .views import ProductViewSetV1, ProductViewSetV2


class ProductsV1APITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            name="Widget",
            sales=100,
            rating=4.5,
            likes=10,
            category="tools",
        )

    def test_list_route_is_available(self):
        response = self.client.get("/api/v1/products/")
        self.assertEqual(response.status_code, 200)

    def test_v1_route_uses_v1_viewset(self):
        match = resolve("/api/v1/products/")
        self.assertIs(match.func.cls, ProductViewSetV1)

    def test_popular_route_is_available(self):
        response = self.client.get("/api/v1/products/popular/")
        self.assertEqual(response.status_code, 200)

    def test_trending_route_is_not_registered(self):
        response = self.client.get("/api/v1/products/trending/")
        self.assertEqual(response.status_code, 404)


class ProductsV2APITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            name="Widget",
            sales=100,
            rating=4.5,
            likes=10,
            category="tools",
        )

    def test_list_route_is_available(self):
        response = self.client.get("/api/v2/products/")
        self.assertEqual(response.status_code, 200)

    def test_v2_route_uses_v2_viewset(self):
        match = resolve("/api/v2/products/")
        self.assertIs(match.func.cls, ProductViewSetV2)

    def test_popular_route_is_available(self):
        response = self.client.get("/api/v2/products/popular/")
        self.assertEqual(response.status_code, 200)

    def test_trending_route_is_available(self):
        response = self.client.get("/api/v2/products/trending/")
        self.assertEqual(response.status_code, 200)

    def test_rate_route_is_available(self):
        response = self.client.get(
            f"/api/v2/products/{self.product.pk}/rate/"
        )
        self.assertEqual(response.status_code, 200)

    def test_best_sellers_route_is_available(self):
        response = self.client.get("/api/v2/products/best-sellers/")
        self.assertEqual(response.status_code, 200)

    def test_version_above_configured_maximum_is_not_registered(self):
        with self.assertRaises(Resolver404):
            resolve("/api/v3/products/")
```

These tests verify:

- The v1 and v2 collection routes dispatch successfully.
- Each collection route resolves to the intended ViewSet class.
- The v1 `trending` route is not registered.
- The v2 custom routes are available.
- A version above the configured maximum has no matching route.

The `resolve()` assertions are particularly relevant to the package-based pattern: they verify that the v2 registration replaced the earlier v1 segment registration for the v2 route.

These are still route and dispatch smoke tests. They do not verify serializer contracts, ordering semantics, permissions, pagination, or filtering behavior. Those require separate assertions against the API's intended response behavior.

A method's existence on a Python class does not automatically create a URL.

In the router pattern, the router generates routes for the standard ViewSet actions and the `@action` methods it discovers.

In the configured-callable pattern, the routes are created by the explicit `@endpoint` declarations. A method that exists on a ViewSet but is not included in an `as_view({...})` mapping and has no corresponding endpoint declaration is unreachable through the API.

There is another inheritance detail worth considering.

If `ProductViewSetV2` inherits from `ProductViewSetV1`, it also inherits `popular`. In the router pattern, if the v2 router is registered with that subclass, the router can discover the inherited `@action` method and generate its route.

If an action should exist only in v2, define it only on the v2 class or otherwise ensure that it is not inherited by the v1 class. Python inheritance determines which methods a class has; the router determines which methods become routes.

The versioning layer does not automatically remove inherited Python methods or decide which actions should be exposed.

## Trade-offs and scope

The central limitation is specific:

**`@endpoint` cannot decorate a ViewSet class directly.**

It calls `as_view()` without an action mapping, while a ViewSet requires that mapping.

For ViewSet-based APIs, the decision is primarily between registering configured ViewSet callables through the package and preserving DRF's router-managed action configuration.

### Configured `as_view()` callables with `@endpoint`

Use this approach when you want ViewSet-based routes to participate in the package's URL registry.

- `@endpoint` registers the configured callable returned by `as_view()`.
- The package's version registration and replacement behavior applies.
- Every route and HTTP method mapping must be declared explicitly.
- Router-generated `@action` metadata is not applied automatically.
- `detail` and `basename` must be passed explicitly when needed.
- `reverse_action()` requires consistent URL naming.

This approach is useful when the package's version registry is part of the URL configuration and the explicit route declarations are acceptable.

### DRF router per version

Use this approach when preserving router-generated routes and action configuration is a requirement.

- DRF generates standard and custom action routes.
- `@action` metadata is handled by the router.
- `reverse_action()` uses the router-provided basename and generated action names.
- Each version has its own router registration.
- The package's `@endpoint` registry is not involved in these ViewSet routes.

This is the appropriate DRF approach when router-managed behavior is more important than registering those routes through the package.

### Generic views with `@endpoint`

Use this when the API is naturally organized around individual endpoints.

- Generic view classes can be decorated directly.
- The package can register their routes without a ViewSet action mapping.
- Version registration can reuse a declaration across later configured versions.
- ViewSet actions must be represented as separate views.

For an API with many ViewSets and custom actions, converting everything to generic views may introduce unnecessary restructuring.

### When the benefit is smaller

The benefit of registering configured callables through `@endpoint` is smaller when the endpoint-change pattern does not create meaningful URLconf maintenance—for example, when a small number of routes are versioned infrequently and the team already has a clear router arrangement.

The decision should be based on the frequency and scope of endpoint changes and the maintenance cost of route registration, not on a universal version-count threshold.

For a project that wants the package's version registry while retaining ViewSet-based handlers, configured `as_view({...})` callables provide that integration without requiring a conversion to generic views.

## Next steps

For the decorator's implementation, see the [current decorators source](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/decorators.py).

For the integration project's URL configuration and import order, see the [current integration URLconf](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/integration_test_project/project/urls.py).

For the underlying ViewSet behavior, consult the official DRF documentation on [ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/) and [routers](https://www.django-rest-framework.org/api-guide/routers/).

To register configured ViewSet callables with version-aware routing, start with the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning) and apply its documented URL construction and registration rules to your URLconf.
