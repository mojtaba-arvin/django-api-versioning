---
slug: "015-version-drf-apiview-using-url-prefixes"
title: "Versioning DRF APIView Endpoints with URL Prefixes"
description: "Register version-specific DRF APIView classes with django-api-versioning, understand automatic route carry-forward, and compare manual URLconf alternatives."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "DRF versioning"
  - "APIView"
  - "URL prefixes"
  - "Django"
  - "Endpoint registration"
---

# Versioning DRF APIView Endpoints with URL Prefixes

Not every Django REST Framework project uses `ViewSet` classes and routers. Some APIs use `APIView` or `GenericAPIView` directly because their endpoints do not map naturally to resources or require custom handling for individual HTTP methods.

For these projects, [django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/) provides declarative registration of version-specific views. You attach `@endpoint` to each view class, and the package generates the corresponding URL patterns.

This is useful when most endpoints remain unchanged between releases and only a subset needs a new implementation. Instead of adding another set of `path()` entries for every API version, you declare the endpoints that change.

This article uses `APIView` subclasses and compares package-based registration with two DRF-only alternatives: separate view classes with manually maintained URL patterns, and shared base classes with version-specific subclasses.

The package is maintained by the author. Its responsibility is URL registration and routing—not DRF request-version negotiation or API contract compatibility.

## Registering APIView endpoints with django-api-versioning

Assume an `Article` model with these fields:

- `category`
- `views`
- `likes`
- `shares`

It also has a reverse `comments` relation. The related model exposes `id`, `text`, and `author` fields. The examples assume the corresponding `ArticleSerializerV1` and `ArticleSerializerV2` serializers already exist.

The v1 and v2 list endpoints share their basic CRUD behavior. In v2, the list endpoint additionally supports filtering by category. The v2 detail endpoint includes comments and article statistics in its response.

### Configure the supported versions

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

With the default `API_BASE_PATH`, the package generates URLs under `api/v{version}/`.

### Define shared view behavior

Use base classes for behavior that remains unchanged between versions. Version-specific subclasses can override the serializer or the methods whose behavior changes.

```python
# views.py

from django.shortcuts import get_object_or_404
from django_api_versioning import endpoint
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Article
from .serializers import ArticleSerializerV1, ArticleSerializerV2


class BaseArticleListView(APIView):
    serializer_class = None

    def get(self, request):
        articles = self.get_queryset(request)
        serializer = self.serializer_class(articles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get_queryset(self, request):
        return Article.objects.all()


class BaseArticleDetailView(APIView):
    serializer_class = None

    def get(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        return self.serialize_detail(request, article)

    def serialize_detail(self, request, article):
        return Response(self.serializer_class(article).data)

    def put(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        serializer = self.serializer_class(
            article,
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

### Register version-specific views

The v1 views use the v1 serializer. Their registrations extend through the configured maximum version.

```python
@endpoint("articles/", version=1)
class ArticleListV1(BaseArticleListView):
    serializer_class = ArticleSerializerV1


@endpoint("articles/<int:pk>/", version=1)
class ArticleDetailV1(BaseArticleDetailView):
    serializer_class = ArticleSerializerV1
```

The v2 views override the corresponding v2 routes. The list view adds category filtering, while the detail view extends its response with comments and statistics.

```python
@endpoint("articles/", version=2)
class ArticleListV2(BaseArticleListView):
    serializer_class = ArticleSerializerV2

    def get_queryset(self, request):
        queryset = Article.objects.all()
        category = request.query_params.get("category")

        if category:
            queryset = queryset.filter(category=category)

        return queryset


@endpoint("articles/<int:pk>/", version=2)
class ArticleDetailV2(BaseArticleDetailView):
    serializer_class = ArticleSerializerV2

    def serialize_detail(self, request, article):
        data = self.serializer_class(article).data

        data["comments"] = list(
            article.comments.values("id", "text", "author")
        )

        data["stats"] = {
            "views": article.views,
            "likes": article.likes,
            "shares": article.shares,
        }

        return Response(data)
```

### Include the generated URL patterns

Import the modules containing the endpoint declarations before importing the package's URL patterns.

```python
# urls.py

from django.urls import include, path

from . import views  # noqa: F401 — execute endpoint declarations first

from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The import of `views` is significant. The decorators register routes when their modules are imported. The package does not automatically discover application view modules.

If endpoint declarations are distributed across multiple modules, import all of them before reading `api_urlpatterns`.

### Resulting URL patterns

With `API_MIN_VERSION = 1` and `API_MAX_VERSION = 2`, the registrations produce four URL patterns:

| URL | View |
| --- | --- |
| `/api/v1/articles/` | `ArticleListV1` |
| `/api/v2/articles/` | `ArticleListV2` |
| `/api/v1/articles/<int:pk>/` | `ArticleDetailV1` |
| `/api/v2/articles/<int:pk>/` | `ArticleDetailV2` |

**Now:**

- `GET /api/v1/articles/` and `POST /api/v1/articles/` use `ArticleListV1`.
- `GET /api/v2/articles/` and `POST /api/v2/articles/` use `ArticleListV2`, including its category filter.
- Detail requests under v1 use `ArticleDetailV1`.
- Detail requests under v2 use `ArticleDetailV2`, including comments and statistics.

**Scope: routing only.** The package chooses which view callable is attached to each URL. It does not negotiate `request.version`, decide whether a response change is backward-compatible, or generate version-specific serializers and schemas.

### How route carry-forward works

The package's `version=N` argument registers an implementation from version N through `API_MAX_VERSION`, inclusive.

For example:

```python
@endpoint("articles/", version=1)
class ArticleListV1(APIView):
    ...


@endpoint("articles/", version=2)
class ArticleListV2(APIView):
    ...
```

With `API_MAX_VERSION = 3`, the first declaration initially covers v1, v2, and v3. The second declaration replaces the v2 and v3 registrations for the same route.

The resulting mapping is:

| API version | Registered implementation |
| --- | --- |
| v1 | `ArticleListV1` |
| v2 | `ArticleListV2` |
| v3 | `ArticleListV2` |

This is route-registration inheritance, not Python class inheritance. The registry does not create subclasses, merge methods, or combine serializers. It selects the view callable registered for each versioned route.

This behavior is useful when an implementation remains valid across later API releases. It also creates a responsibility: when an endpoint's contract changes, register a new implementation or deliberately choose an explicit version set. Otherwise, the previous implementation continues to serve later versions.

For package-specific details—including collision precedence, version boundaries, URL construction, and import order—see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## DRF-only alternative 1: Separate APIView classes per version

A project can implement version-specific views without an additional package. Define a separate `APIView` subclass for each endpoint and version, then register every route manually.

For example:

```python
# views.py

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Article
from .serializers import ArticleSerializerV1, ArticleSerializerV2


class ArticleListV1(APIView):
    def get(self, request):
        articles = Article.objects.all()
        serializer = ArticleSerializerV1(articles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ArticleSerializerV1(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class ArticleListV2(APIView):
    def get(self, request):
        articles = Article.objects.all()
        category = request.query_params.get("category")

        if category:
            articles = articles.filter(category=category)

        serializer = ArticleSerializerV2(articles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ArticleSerializerV2(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class ArticleDetailV1(APIView):
    def get(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        return Response(ArticleSerializerV1(article).data)


class ArticleDetailV2(APIView):
    def get(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        data = ArticleSerializerV2(article).data

        data["comments"] = list(
            article.comments.values("id", "text", "author")
        )
        data["stats"] = {
            "views": article.views,
            "likes": article.likes,
            "shares": article.shares,
        }

        return Response(data)
```

The URLconf registers each version explicitly:

```python
# urls.py

from django.urls import path

from .views import (
    ArticleListV1,
    ArticleListV2,
    ArticleDetailV1,
    ArticleDetailV2,
)


urlpatterns = [
    path(
        "api/v1/articles/",
        ArticleListV1.as_view(),
        name="article-list-v1",
    ),
    path(
        "api/v2/articles/",
        ArticleListV2.as_view(),
        name="article-list-v2",
    ),
    path(
        "api/v1/articles/<int:pk>/",
        ArticleDetailV1.as_view(),
        name="article-detail-v1",
    ),
    path(
        "api/v2/articles/<int:pk>/",
        ArticleDetailV2.as_view(),
        name="article-detail-v2",
    ),
]
```

**What this approach does well:** Each view is self-contained. The implementation for a version is visible without tracing a base class or understanding a registration rule.

**What it costs:** Shared behavior is repeated. Changes to common operations—such as validation, object retrieval, or response handling—may need to be applied to multiple classes. The URLconf also needs a separate entry for each endpoint and version.

This approach remains reasonable when implementations are substantially different and explicit URL declarations are preferable to shared registration logic.

## DRF-only alternative 2: Base classes with version-specific subclasses

A second option is to share common behavior through Python inheritance while keeping URL registration manual.

This is the same view structure used in the package-based example, but without `@endpoint`.

```python
# views.py

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Article
from .serializers import ArticleSerializerV1, ArticleSerializerV2


class BaseArticleListView(APIView):
    serializer_class = None

    def get(self, request):
        articles = self.get_queryset(request)
        return Response(
            self.serializer_class(articles, many=True).data
        )

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get_queryset(self, request):
        return Article.objects.all()


class ArticleListV1(BaseArticleListView):
    serializer_class = ArticleSerializerV1


class ArticleListV2(BaseArticleListView):
    serializer_class = ArticleSerializerV2

    def get_queryset(self, request):
        queryset = Article.objects.all()
        category = request.query_params.get("category")

        if category:
            queryset = queryset.filter(category=category)

        return queryset


class BaseArticleDetailView(APIView):
    serializer_class = None

    def get(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        return self.serialize_detail(request, article)

    def serialize_detail(self, request, article):
        return Response(self.serializer_class(article).data)

    def put(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        serializer = self.serializer_class(
            article,
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ArticleDetailV1(BaseArticleDetailView):
    serializer_class = ArticleSerializerV1


class ArticleDetailV2(BaseArticleDetailView):
    serializer_class = ArticleSerializerV2

    def serialize_detail(self, request, article):
        data = self.serializer_class(article).data

        data["comments"] = list(
            article.comments.values("id", "text", "author")
        )
        data["stats"] = {
            "views": article.views,
            "likes": article.likes,
            "shares": article.shares,
        }

        return Response(data)
```

The URLconf still requires an entry for each endpoint and version:

```python
# urls.py

from django.urls import path

from .views import (
    ArticleListV1,
    ArticleListV2,
    ArticleDetailV1,
    ArticleDetailV2,
)


urlpatterns = [
    path(
        "api/v1/articles/",
        ArticleListV1.as_view(),
        name="article-list-v1",
    ),
    path(
        "api/v2/articles/",
        ArticleListV2.as_view(),
        name="article-list-v2",
    ),
    path(
        "api/v1/articles/<int:pk>/",
        ArticleDetailV1.as_view(),
        name="article-detail-v1",
    ),
    path(
        "api/v2/articles/<int:pk>/",
        ArticleDetailV2.as_view(),
        name="article-detail-v2",
    ),
]
```

**What this approach does well:** Common HTTP method implementations are defined once. Each version overrides only the serializer or the methods whose behavior differs.

**What it costs:** Python inheritance reduces duplicated view logic, but it does not reduce the number of URL declarations. Every new version still requires explicit URLconf entries for the endpoints exposed by that version.

The base classes can also accumulate version-specific hooks. Keep those extension points focused on genuine shared behavior rather than turning the base class into a collection of unrelated version conditions.

## Comparing the approaches

The distinction is where shared view logic lives and how versioned URLs are registered.

| Aspect | Separate APIViews | Base classes | `django-api-versioning` |
| --- | --- | --- | --- |
| Shared view logic | Repeated per version | Python inheritance | Python inheritance |
| URL registration | Manual `path()` entries | Manual `path()` entries | Generated from declarations |
| Adding a version | Add views and URL entries | Add subclasses and URL entries | Increase `API_MAX_VERSION`; add declarations for changed endpoints |
| Unchanged endpoint behavior | Must be registered explicitly | Must be registered explicitly | Carries forward from its latest applicable declaration |
| Import-order requirement | No package-specific requirement | No package-specific requirement | Import declaration modules before reading generated patterns |

The first two approaches are valid DRF-only solutions. The package-based approach keeps the same Python inheritance model as the second approach, but moves versioned URL registration from a growing set of manual `path()` declarations to the endpoint declarations themselves.

The package is most useful when the project has a recurring pattern of endpoints remaining unchanged across releases while only selected endpoints receive new implementations.

## ViewSet and router boundary

If an endpoint maps naturally to a resource, DRF's `ModelViewSet` and routers are often a better fit than manually implementing CRUD methods with `APIView`.

A `ModelViewSet` provides list, create, retrieve, update, partial update, and destroy actions. Routers generate the corresponding URL patterns and can also expose custom actions declared with `@action`.

The examples in this article focus on `APIView` because they illustrate endpoints where direct method handling and custom response behavior are useful.

There is an important package boundary: `@endpoint` cannot decorate a `ModelViewSet` class directly. A ViewSet requires an action mapping when `as_view()` is called.

For resource-oriented endpoints, use a DRF router per API version and mount its URLs under the appropriate version prefix. That is a separate routing pattern; the package does not automatically integrate with or register router-generated ViewSet routes.

A configured callable such as:

```python
ArticleViewSet.as_view({"get": "list"})
```

can be registered as one explicitly configured route, but it is not a replacement for a router when the ViewSet exposes list, detail, and custom-action routes.

## Trade-offs and scope

**Separate APIView classes are appropriate when:**

- Each version has substantially different request or response behavior.
- Keeping every version's implementation self-contained is more important than sharing common code.
- The URLconf is intentionally maintained explicitly.

**Base classes with subclasses are appropriate when:**

- Most HTTP method behavior is identical between versions.
- Differences can be isolated in serializers and a small number of override methods.
- Manual URL registration is acceptable.

**Decorator registration is appropriate when:**

- The project uses `APIView` or `GenericAPIView` and has several versioned endpoints.
- Most endpoints remain unchanged between releases.
- The team wants route registration to live alongside the view declarations.
- The team is comfortable with the package's import-order requirement and automatic carry-forward behavior.

### When the benefit of the package is smaller

For a small API with only a few versioned routes, manually maintained URL patterns may be easier to understand and maintain.

The package also may not be necessary for a project already using DRF ViewSets and routers effectively. In that case, per-version router registration is the more direct DRF-native approach.

The important distinction is not a fixed number of endpoints. It is whether the project's release pattern makes automatic route carry-forward and centralized endpoint registration worth adopting.

## Next steps

For `APIView`-based projects where endpoint implementations evolve incrementally between API versions, `django-api-versioning` provides a declarative way to maintain the routing table without manually adding a `path()` entry for every version of every endpoint.

Review the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning) for the implementation and integration examples.
