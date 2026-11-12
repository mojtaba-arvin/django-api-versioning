---
slug: "005-support-v1-v2-endpoints-django-rest-api"
title: "How to support v1 and v2 endpoints in a Django REST API"
description: "Learn how to register versioned DRF endpoints declaratively and compare the approach with explicit Django URL routing."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - Django REST Framework
  - API Versioning
  - Django URL Routing
  - Endpoint Registration
---

# How to support v1 and v2 endpoints in a Django REST API

When an API evolves, existing clients may need to continue using `/api/v1/` while newer clients use `/api/v2/`. The challenge is deciding which implementation serves each version and maintaining the corresponding URL routes.

[Django API Versioning](https://pypi.org/project/django-api-versioning/) provides declarative endpoint registration for Django and Django REST Framework (DRF). Instead of writing a separate `path()` declaration for every version, you define endpoint availability alongside the view implementation.

This article demonstrates the package's approach and compares it with explicit Django URL routing. The examples use integer version identifiers such as `1` and `2`; the default URL configuration renders them as `v1` and `v2`.

The examples target `django-api-versioning` 0.3.4. The package is maintained by the author of this article.

## 1. Declarative versioned endpoints

Consider an API that exposes a list and detail endpoint for books. Version 1 returns a basic representation, while version 2 adds author and publication information to the list response.

### Configuration

Define the supported version range in Django settings:

```python
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

The package's default `API_BASE_PATH` is `"api/v{version}/"`, so integer version identifiers produce URL prefixes such as `/api/v1/` and `/api/v2/`.

### Serializers

```python
from rest_framework import serializers

from .models import Book


class BookV1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title"]


class BookV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title", "author", "published_at"]
```

### Versioned views

Use `@endpoint` to register each view for the versions in which it should be available.

```python
from rest_framework.generics import ListAPIView, RetrieveAPIView

from django_api_versioning import endpoint

from .models import Book
from .serializers import BookV1Serializer, BookV2Serializer


@endpoint("books/", versions=[1])
class BookListV1View(ListAPIView):
    queryset = Book.objects.all()
    serializer_class = BookV1Serializer


@endpoint("books/", versions=[2])
class BookListV2View(BookListV1View):
    serializer_class = BookV2Serializer


@endpoint("books/<int:pk>/", versions=[1, 2])
class BookDetailView(RetrieveAPIView):
    queryset = Book.objects.all()
    serializer_class = BookV1Serializer
```

The list endpoint has separate implementations for versions 1 and 2. The detail endpoint uses the same implementation in both versions because its response contract remains unchanged.

The `versions` argument explicitly lists the versions for which a declaration is registered. It does not create a forward-inheritance segment.

### Including generated URL patterns

Import the modules containing endpoint declarations before importing the package's generated URL patterns. Importing those modules executes the decorators and registers the endpoints.

```python
from django.urls import include, path

# Import modules containing @endpoint declarations first.
from api import views as _api_views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The declarations above produce the following routes:

| Request | Registered view |
| --- | --- |
| `/api/v1/books/` | `BookListV1View` |
| `/api/v2/books/` | `BookListV2View` |
| `/api/v1/books/42/` | `BookDetailView` |
| `/api/v2/books/42/` | `BookDetailView` |

**Now:**

- A v1 list request is handled by `BookListV1View`.
- A v2 list request is handled by `BookListV2View`.
- Both v1 and v2 detail requests are handled by `BookDetailView`.

The package generates standard Django URL patterns from the endpoint declarations. It does not change the view's business logic or automatically determine whether two API contracts are compatible.

For the complete behavior of `version`, `versions`, URL construction, registration precedence, and import order, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## 2. The explicit URL routing alternative

Django's standard `path()` API can also register versioned routes explicitly. This approach is valid, particularly when an application has a small and stable set of routes.

For example, the same views can be wired to different version prefixes:

```python
from django.urls import path

from .views import BookDetailView, BookListV1View, BookListV2View


urlpatterns = [
    path("api/v1/books/", BookListV1View.as_view(), name="book-list-v1"),
    path("api/v2/books/", BookListV2View.as_view(), name="book-list-v2"),
    path("api/v1/books/<int:pk>/", BookDetailView.as_view(), name="book-detail-v1"),
    path("api/v2/books/<int:pk>/", BookDetailView.as_view(), name="book-detail-v2"),
]
```

Notice that the detail view is reused. Explicit routing does not require a separate view implementation for every version, and DRF does not require a separate serializer when the response contract is unchanged.

The difference is that each URL pattern still needs to be declared and maintained explicitly.

As the number of endpoints and supported versions grows, those declarations can become a separate maintenance concern.

## 3. Endpoint availability and inheritance

It is important to distinguish Python class inheritance from the package's endpoint registration behavior.

Subclassing a view does not register that subclass for another API version. The `@endpoint` declaration determines which versioned routes are generated.

For example, the following declarations use Python inheritance to reuse the queryset and other behavior while changing the list serializer:

```python
@endpoint("books/", versions=[1])
class BookListV1View(ListAPIView):
    queryset = Book.objects.all()
    serializer_class = BookV1Serializer


@endpoint("books/", versions=[2])
class BookListV2View(BookListV1View):
    serializer_class = BookV2Serializer
```

Here, Python inheritance reuses implementation details. The explicit `versions` arguments determine route availability.

The package also supports segment registration through `version=N`. A declaration using `version=2` registers that implementation from version 2 through `API_MAX_VERSION`, inclusive. A later declaration for the same route at a higher source version overrides the earlier implementation from that version onward.

For example, with `API_MAX_VERSION = 3`:

```python
@endpoint("books/", version=1)
class BookListV1View(ListAPIView):
    queryset = Book.objects.all()
    serializer_class = BookV1Serializer


@endpoint("books/", version=2)
class BookListV2View(BookListV1View):
    serializer_class = BookV2Serializer
```

The resulting routing is:

| Requested version | Selected implementation |
| --- | --- |
| v1 | `BookListV1View` |
| v2 | `BookListV2View` |
| v3 | `BookListV2View` |

The v2 declaration overrides the v1 segment from v2 onward. The v1 implementation remains active for v1.

This is route-registration inheritance, not automatic Python inheritance or semantic API compatibility. If a newer API contract requires a different implementation, the corresponding endpoint declaration must be updated deliberately.

## 4. What about ViewSets?

DRF ViewSets require an action mapping when converted into a view callable. A ViewSet class cannot be passed directly to `@endpoint` as if it were a generic view.

For example, this is not a valid direct registration:

```python
@endpoint("books/", versions=[1, 2])
class BookViewSet(ModelViewSet):
    ...
```

The package's registry calls `as_view()` for class-based views, while DRF ViewSets require an action mapping for that call.

Use DRF's `DefaultRouter` or `SimpleRouter` to register ViewSets and configure their generated URLs under the required version prefixes. This router configuration is separate from the package's endpoint registry; the package does not automatically register or inherit ViewSet actions.

See the DRF documentation for [ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/) and [Routers](https://www.django-rest-framework.org/api-guide/routers/).

## 5. Comparing the approaches

Both approaches can expose the same runtime URL patterns. The difference is how those patterns are declared and maintained.

| Aspect | Explicit URL routing | Declarative endpoint registration |
| --- | --- | --- |
| URL declarations | Written with `path()` | Generated from endpoint declarations |
| Version availability | Expressed in URL patterns | Expressed with `@endpoint` |
| Reusing an unchanged view | Register the same callable in multiple patterns | Register the endpoint for multiple versions |
| Python inheritance | Supported by Python | Supported by Python |
| Runtime URL patterns | Standard Django URL patterns | Standard Django URL patterns |
| Route generation | Maintained in URL configuration | Generated from the registry |

### Declaration count example

Consider an API with 10 endpoints and 3 supported versions.

If all 10 endpoints are explicitly registered in all 3 versions, the URL configuration contains:

`10 endpoints × 3 versions = 30 path() declarations`

With declarative registration, the number of endpoint declarations depends on how many endpoints need a new registration at each version boundary.

For example, assume all 10 endpoints are introduced in version 1, and only 2 endpoints need new implementations in versions 2 and 3:

- 10 declarations for version 1.
- 2 additional declarations for version 2.
- 2 additional declarations for version 3.

That gives:

`10 + 2 + 2 = 14 endpoint declarations`

The comparison is 14 endpoint declarations versus 30 explicit URL declarations.

This is a reduction in source-code registration declarations, not in the number of runtime routes. If all 10 endpoints must be available in all 3 versions, the application still exposes 30 versioned URL patterns.

The exact reduction depends on the endpoint-change pattern. It does not imply that the package eliminates view implementations, serializer changes, or business-logic work.

## 6. Trade-offs and scope

Explicit URL routing is straightforward and uses standard Django APIs. It also keeps the route mapping visible in the URL configuration. For a small, stable API, the additional declarations may be easy to maintain.

Declarative registration moves version availability closer to the view implementation and generates the corresponding URL patterns. This can be useful when many endpoints remain unchanged across versions and only a smaller subset requires new implementations.

There are also trade-offs to consider:

- The package introduces a dependency and a registration model that developers must understand.
- Segment registration carries an implementation forward through `API_MAX_VERSION` unless a later declaration overrides it.
- Explicit `versions=[...]` declarations require maintaining the intended version set.
- The package does not validate semantic compatibility between response contracts.
- DRF ViewSet router registration remains a separate routing concern.

**Scope: routing only.** The package manages endpoint registration and URL generation. It does not decide whether a serializer change is backward compatible, automatically version business logic, or generate a separate API schema for every version.

The benefit is smaller when an API has few endpoints, few version boundaries, and little repeated route-registration work. In that situation, explicit `path()` declarations may be simpler than adopting another dependency.

## Conclusion

For a versioned DRF API, the important distinction is not whether Django can expose multiple URL prefixes—it can. The distinction is where version availability is maintained.

With `django-api-versioning`, endpoint declarations define the versions served by each implementation, while the package generates the corresponding URL patterns. Its segment registration can also carry an implementation forward until a later declaration overrides it.

The next step is to review the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning), compare its registration model with your endpoint-change pattern, and verify that its routing behavior fits your API's versioning contract.
