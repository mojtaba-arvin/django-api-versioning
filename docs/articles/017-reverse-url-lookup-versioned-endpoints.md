---
slug: "017-reverse-url-lookup-versioned-api-endpoints-django"
title: "Reverse URL Lookup for Versioned Django API Endpoints"
description: "Use django-api-versioning's api_reverse() for @endpoint routes, and compare it with Django and DRF reverse behavior."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "Django URL reverse"
  - "API versioning"
  - "URL lookup"
  - "Django REST Framework"
  - "Endpoint registration"
---

# Reverse URL Lookup for Versioned Django API Endpoints

Reverse URL lookup becomes less straightforward when an API exposes multiple versions of the same endpoint.

A route such as `/api/v1/products/` and its newer counterpart `/api/v2/products/` may share the same logical endpoint name, but they do not necessarily represent the same API contract. When generating links, redirects, or `Location` headers, the application needs to select the intended version explicitly.

For projects using `@endpoint` from [django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/), `api_reverse()` provides a version-aware way to resolve registered endpoints without relying on URL resolver ordering.

This article explains how to use it, where Django's and Django REST Framework's reverse functions fit, and which limitations matter when integrating URL reversal with serializers and HTTP responses.

## The URL reversal problem in versioned APIs

Consider an API that exposes two implementations of a product endpoint:

```python
# products/views.py

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from django_api_versioning import endpoint


@endpoint("products/", version=1, view_name="product-list")
class ProductListV1(ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1


@endpoint("products/", version=2, view_name="product-list")
class ProductListV2(ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV2
```

Assume the application uses this configuration:

```python
# settings.py

INSTALLED_APPS = [
    # ...
    "django_api_versioning",
]

API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

The package registers versioned routes for the decorated views. The resulting paths include:

| Version | URL | Implementation |
| --- | --- | --- |
| v1 | `/api/v1/products/` | `ProductListV1` |
| v2 | `/api/v2/products/` | `ProductListV2` |

Both routes use the same logical URL name, `product-list`, because they represent different versions of the same resource endpoint.

This creates a practical question:

**How can application code generate the URL for a specific version instead of depending on whichever matching route the URL resolver selects?**

The answer depends on which reverse function is used.

## Use `api_reverse()` for version-aware route lookup

`django-api-versioning` provides `api_reverse()` to resolve a registered endpoint by its URL name and, when necessary, its version.

Import it from the package:

```python
from django_api_versioning import api_reverse
```

Then specify both the endpoint name and the intended version:

```python
product_url = api_reverse("product-list", version=2)
```

For the example above, the result is:

```text
/api/v2/products/
```

To resolve the older implementation:

```python
product_url = api_reverse("product-list", version=1)
```

The result is:

```text
/api/v1/products/
```

Unlike a reverse lookup that only receives a URL name, this call makes the target version explicit.

### Why the version argument matters

A versioned URL name can refer to multiple registered patterns:

```text
product-list → /api/v1/products/
product-list → /api/v2/products/
```

The name alone does not identify which version the caller intends to use.

When a version is provided, `api_reverse()` selects a registered pattern whose route version exactly matches the requested version.

When the version is omitted, the function can only resolve the name if exactly one matching registered pattern exists.

For example:

```python
# Explicit version: deterministic selection.
api_reverse("product-list", version=2)

# No version: ambiguous when multiple matching routes exist.
api_reverse("product-list")
```

If multiple registered patterns match the same name and no version is supplied, the package raises `AmbiguousVersionError`.

If no matching route exists for the requested name and version, it raises Django's `NoReverseMatch`.

This makes ambiguity visible rather than silently choosing a route that may not represent the intended API contract.

### Keep URL names unique across logical endpoints

A URL name can be reused across versions of the same logical endpoint:

```python
@endpoint("products/", version=1, view_name="product-list")
class ProductListV1(ListAPIView):
    ...


@endpoint("products/", version=2, view_name="product-list")
class ProductListV2(ListAPIView):
    ...
```

However, avoid using the same `view_name` for different endpoint paths within the same version.

For example, these registrations are problematic:

```python
@endpoint("products/", version=2, view_name="catalog")
class ProductListV2(ListAPIView):
    ...


@endpoint("categories/", version=2, view_name="catalog")
class CategoryListV2(ListAPIView):
    ...
```

`api_reverse()` uses the route name and version to select a registered pattern. If multiple patterns share both values, the version argument cannot distinguish between the different logical endpoints.

A practical naming rule is:

> Reuse a `view_name` across versions of the same logical endpoint, but keep it unique across different endpoint paths.

### Import decorated views before reversing their URLs

The package builds its registered URL patterns from decorated endpoint declarations.

Make sure the modules containing those declarations have been imported before calling `api_reverse()`.

For example, if the application's root URL configuration includes the generated patterns, import the relevant view modules before including them:

```python
# config/urls.py

from django.urls import include, path

# Import modules so their @endpoint declarations are registered.
from products import views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The exact module imports depend on the application's structure. The important requirement is that decorated views must be loaded before code relies on their registered routes.

For more information about the package's registration behavior and public API, see the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).

## Use `api_reverse()` in HTTP responses

A common use case for reverse URL lookup is generating the `Location` header after creating a resource.

For example, a product creation endpoint can return a URL pointing to the newly created product detail endpoint.

First, register the detail endpoints with a stable name:

```python
from rest_framework.generics import RetrieveAPIView

from django_api_versioning import endpoint


@endpoint("products/<int:pk>/", version=1, view_name="product-detail")
class ProductDetailV1(RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV1


@endpoint("products/<int:pk>/", version=2, view_name="product-detail")
class ProductDetailV2(RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV2
```

Then use the requested API version when building the response:

```python
from django_api_versioning import api_reverse
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework import status


@endpoint("products/", version=2, view_name="product-list")
class ProductListV2(ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerV2

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        product_id = response.data["id"]

        relative_url = api_reverse(
            "product-detail",
            version=2,
            pk=product_id,
        )

        response["Location"] = request.build_absolute_uri(relative_url)

        return response
```

The example assumes that the creation serializer exposes the newly created object's `id` in `response.data`.

There are two distinct operations here:

1. `api_reverse()` resolves the registered route and returns a root-relative path.
2. `request.build_absolute_uri()` converts that path into an absolute URL using the current request.

For example:

```text
api_reverse(...)

"/api/v2/products/42/"
```

The HTTP response can then contain:

```text
Location: https://api.example.com/api/v2/products/42/
```

This distinction matters because `api_reverse()` does not return an absolute URL.

### Use the version that matches the intended contract

The version passed to `api_reverse()` should reflect the endpoint contract that the application intends to expose.

For example, if a v1 request creates a resource and the API contract requires the response link to remain within v1, resolve the v1 detail endpoint:

```python
relative_url = api_reverse(
    "product-detail",
    version=1,
    pk=product_id,
)
```

If the application intentionally wants to return a v2 URL, pass `version=2`.

Do not assume that the newest registered version is always the correct target. URL generation is part of the API contract and should follow the behavior expected by the client.

## Using `api_reverse()` with Django REST Framework serializers

Django REST Framework provides hyperlink-related serializer fields, including `HyperlinkedIdentityField` and `HyperlinkedRelatedField`.

These fields use DRF's URL reversal behavior. For example:

```python
from rest_framework import serializers


class ProductSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="product-detail",
    )

    class Meta:
        model = Product
        fields = ["url", "id", "name"]
```

For hyperlinked serializers, DRF generally needs the current request in the serializer context:

```python
serializer = ProductSerializer(
    product,
    context={"request": request},
)
```

This allows DRF to build absolute URLs and apply the configured versioning scheme where applicable.

However, there is an important distinction between DRF's request-aware reverse function and the package's `api_reverse()`.

`api_reverse()` requires an explicit version when a URL name is registered for multiple versions. DRF's reverse function delegates URL transformation to the configured DRF versioning scheme when a request is provided.

Consequently, a `HyperlinkedIdentityField` should not be assumed to provide the same explicit route-version selection as `api_reverse()`.

If a serializer must generate a link to a specific package-registered version, implement that behavior explicitly rather than relying on implicit URL resolver selection.

For example, a custom serializer method can use `api_reverse()` and then build an absolute URL:

```python
from django_api_versioning import api_reverse
from rest_framework import serializers


class ProductSerializerV2(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["url", "id", "name"]

    def get_url(self, obj):
        request = self.context["request"]

        relative_url = api_reverse(
            "product-detail",
            version=2,
            pk=obj.pk,
        )

        return request.build_absolute_uri(relative_url)
```

This approach makes the target version explicit and avoids relying on the serializer's implicit URL reversal behavior.

It is particularly useful when the API needs to guarantee that generated links remain within a specific versioned contract.

## Django's `reverse()` as an alternative

Django provides `django.urls.reverse()` to resolve a URL by its registered name.

For example:

```python
from django.urls import reverse


url = reverse(
    "product-detail",
    kwargs={"pk": 42},
)
```

Django's reverse function is appropriate when a URL name identifies a single route or when the application's URL configuration provides an unambiguous resolution.

The challenge appears when multiple versioned routes share the same name:

```text
product-detail → /api/v1/products/<int:pk>/
product-detail → /api/v2/products/<int:pk>/
```

Django's `reverse()` does not expose the package registry's route-version metadata as an explicit selection argument.

When multiple patterns share a name, the result depends on Django's URL resolver ordering rather than an explicit package version.

That means application code cannot express this requirement directly through Django's standard reverse function:

```python
# Django reverse has no package-version argument.
reverse("product-detail", version=2, kwargs={"pk": 42})
```

Passing a `version` keyword argument does not turn it into a version-aware lookup. It is treated as a route parameter, and it will only work if the selected URL pattern actually defines such a parameter.

For applications that need deterministic selection among `@endpoint` registrations, `api_reverse()` is the more explicit interface.

For details about Django's URL reversing behavior, see the [Django URL dispatcher documentation](https://docs.djangoproject.com/en/stable/topics/http/urls/#reverse-resolution-of-urls).

## DRF's `reverse()` and request-aware URL generation

Django REST Framework provides its own reverse function:

```python
from rest_framework.reverse import reverse
```

It extends Django's URL reversal behavior by integrating with the request and the configured DRF versioning scheme.

For example:

```python
from rest_framework.reverse import reverse


url = reverse(
    "product-detail",
    kwargs={"pk": 42},
    request=request,
)
```

When a request is supplied, DRF can use the configured versioning scheme to transform the URL appropriately.

This is useful when the application uses DRF's built-in versioning mechanisms and wants generated links to follow the incoming request's version.

There are two important differences between this function and `api_reverse()`:

| Behavior | `api_reverse()` | DRF `reverse()` with request |
| --- | --- | --- |
| Selects a package route by explicit version | Yes | Not through a package-version argument |
| Uses DRF's configured versioning scheme | No | Yes |
| Returns a root-relative path | Yes | No, normally returns an absolute URL when a request is supplied |
| Uses the package registry's route-version metadata | Yes | No |
| Supports request-aware URL transformations | No | Yes |

These functions solve related but different problems.

Use DRF's `reverse()` when the application's URL generation should follow the configured DRF versioning scheme. Use `api_reverse()` when code needs to select a specific route version registered through `@endpoint`.

## How DRF versioning schemes affect reverse lookup

Django REST Framework supports several versioning schemes. Their behavior matters when an application combines DRF request versioning with package-generated static versioned routes.

The following distinctions are particularly relevant.

### URLPathVersioning

`URLPathVersioning` expects the version to be represented by a named URL parameter, commonly `version`.

A typical route might look like this:

```python
urlpatterns = [
    path(
        "api/<str:version>/products/",
        ProductListView.as_view(),
        name="product-list",
    ),
]
```

The version is available as part of the resolved request URL, and DRF can use it when reversing URLs.

Routes generated by `django-api-versioning`, on the other hand, use concrete versioned paths such as:

```text
/api/v1/products/
/api/v2/products/
```

The version is part of the static route path. It is not automatically exposed as a `version` URL keyword argument.

Therefore, `URLPathVersioning` cannot be assumed to reverse these package-generated routes by injecting a `version` parameter.

For this routing model, use `api_reverse()` when the target package route must be selected explicitly.

### NamespaceVersioning

`NamespaceVersioning` uses Django URL namespaces to identify the API version.

A conventional configuration might look like this:

```python
urlpatterns = [
    path(
        "v1/",
        include((v1_urlpatterns, "api"), namespace="v1"),
    ),
    path(
        "v2/",
        include((v2_urlpatterns, "api"), namespace="v2"),
    ),
]
```

DRF can then use the request's version to construct a namespaced URL name, such as:

```text
v1:product-detail
```

The package's generated URL patterns do not automatically create these version namespaces.

However, namespace-based routing and the package are not fundamentally incompatible. An application can build a suitable namespaced URL configuration around its own routes if it deliberately needs that structure.

Do not assume that applying `NamespaceVersioning` automatically namespaces the package's generated patterns.

### AcceptHeaderVersioning

`AcceptHeaderVersioning` identifies the requested API version through the `Accept` header rather than a URL path.

For example:

```http
Accept: application/json; version=2.0
```

The version is not encoded in the URL.

This scheme can influence DRF's request-aware URL generation, but it does not independently select among the package's static versioned routes.

If an application uses `@endpoint` to expose multiple concrete paths, it still needs an explicit route-selection strategy when generating links to those paths.

`api_reverse()` provides that explicit selection through its `version` argument.

For the complete list of DRF versioning schemes and their behavior, see the official [Django REST Framework versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/).

## Scope and limitations of `api_reverse()`

`api_reverse()` is designed to resolve URL patterns registered by the package. It should not be treated as a complete replacement for Django's URL reversing engine.

Its behavior has several important boundaries.

### It requires a registered endpoint name

The `view_name` must correspond to a route registered by the package.

For example:

```python
api_reverse(
    "product-detail",
    version=2,
    pk=42,
)
```

If the name or requested version does not match a registered pattern, the function raises `NoReverseMatch`.

### Version matching is explicit

When `version` is supplied, the function selects a route whose registered route version exactly matches that value.

It does not infer the version from the current request.

It also does not automatically choose the newest available version.

### Ambiguous names require an explicit version

If the same name matches multiple registered route versions and the caller omits `version`, the function raises `AmbiguousVersionError`.

This behavior is intentional: the caller must specify which route it wants.

### Route parameters are supplied as keyword arguments

The function accepts route parameters through `**kwargs`:

```python
api_reverse(
    "product-detail",
    version=2,
    pk=42,
)
```

It does not provide positional `args` support.

### Route substitution is not Django's full reverse algorithm

The current implementation reads the registered route's `_route` representation and substitutes supported parameter placeholders using the supplied keyword values.

It does not delegate to Django's reverse resolver.

As a result, it does not provide the full behavior of Django's URL reversing engine, including converter-specific `to_url()` handling and converter validation.

For example, a route containing:

```python
"products/<int:pk>/"
```

can be resolved with:

```python
api_reverse(
    "product-detail",
    version=2,
    pk=42,
)
```

But callers should not assume that every custom Django path converter receives the same validation and formatting behavior it would receive through Django's `reverse()` function.

If an application relies on custom converters or complex route patterns, verify that the route parameters are represented correctly before using the generated URL.

### It is not a ViewSet router replacement

The package's `@endpoint` decorator does not automatically register all actions of a DRF `ViewSet`.

A ViewSet's `.as_view()` requires an `actions` mapping, which is not supplied automatically by the decorator.

DRF routers remain the usual mechanism for registering resource ViewSets and their standard routes.

`api_reverse()` should be used for the URL patterns that the package has actually registered.

## Choosing the appropriate reverse function

The three functions serve different purposes.

| Requirement | Recommended function |
| --- | --- |
| Resolve a single, unambiguous Django URL name | `django.urls.reverse()` |
| Generate request-aware URLs using a DRF versioning scheme | `rest_framework.reverse.reverse()` |
| Select a specific version of a package-registered endpoint | `django_api_versioning.api_reverse()` |
| Generate an absolute URL from a package-registered route | `request.build_absolute_uri(api_reverse(...))` |

The important design decision is whether the caller needs to select a route version explicitly or follow the versioning behavior associated with the current DRF request.

For versioned routes registered through `@endpoint`, explicit selection is preferable when the generated link is part of a version-specific API contract.

## Trade-offs and scope

Using `api_reverse()` makes the target route version explicit and avoids relying on URL resolver ordering when multiple package registrations share a name.

That is useful for:

- Generating `Location` headers after resource creation.
- Building links to version-specific detail endpoints.
- Producing serializer URLs for a known API contract.
- Avoiding accidental route selection when multiple versions are registered.

However, it does not replace Django's complete reverse-resolution functionality or DRF's request-aware URL generation.

The appropriate choice depends on the routing model:

- Use Django's `reverse()` for ordinary Django URL patterns.
- Use DRF's `reverse()` when URL generation should follow a configured DRF versioning scheme.
- Use `api_reverse()` when selecting a concrete version of a package-registered endpoint is the requirement.

**Scope: routing only.** Choosing a URL does not make the underlying response compatible with the selected API version. The application remains responsible for serializers, request handling, response contracts, and backward compatibility.

## Conclusion

Reverse URL lookup in a versioned API should make the intended route explicit.

Django's `reverse()` is suitable for ordinary URL resolution, while DRF's `reverse()` integrates URL generation with its configured request versioning scheme. Neither provides the package registry's explicit route-version selection interface.

For endpoints registered with `@endpoint`, `django-api-versioning` provides `api_reverse()` to resolve a route by its `view_name` and an exact version.

Use an explicit version when multiple registrations share a name, keep names unique across different logical endpoints, and remember that `api_reverse()` returns a root-relative path rather than an absolute URL.

To explore the implementation, configuration options, and versioned endpoint registration patterns, visit the [django-api-versioning repository on GitHub](https://github.com/mojtaba-arvin/django-api-versioning).
