---
slug: "008-api-v2-inherit-override-endpoints-django"
title: "How API v2 can inherit endpoints from v1 and override changed views"
description: "Compare Python view inheritance with version-range routing in Django REST Framework, including endpoint overrides and per-version router trade-offs."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "API versioning"
  - "inheritance"
  - "override"
  - "DRF"
  - "backward compatibility"
---

# How API v2 can inherit endpoints from v1 and override changed views

When releasing API v2, most endpoints often remain unchanged while a smaller set needs new behavior. Two separate mechanisms help manage that transition:

- **Python class inheritance** reuses view methods and shared logic between view classes. This is standard Python and Django REST Framework behavior.
- **Routing inheritance** carries a URL registration forward across a version range until a later registration replaces it. This is what `django-api-versioning` provides.

These mechanisms solve different problems and can be used together. Python inheritance controls how view code is shared; routing inheritance controls which implementation is registered at each API version.

This article uses `GenericAPIView` subclasses with `django-api-versioning` to demonstrate both mechanisms. It then compares that approach with DRF `ModelViewSet` classes and per-version routers.

The examples assume an `Article` model with a `title` field, a relation to a Django `User` model as its `author`, numeric `views` and `likes` fields, and a reverse `comments` relation. The comment model is assumed to have `id` and `text` fields.

The examples also assume that `ArticleSerializerV1` and `ArticleSerializerV2` are defined in the application's `serializers.py`. The router-based example assumes the user model has a many-to-many `bookmarks` relation to `Article`. Adjust model fields, relations, serializers, and the `get_full_name()` call to match your project.

## Routing inheritance with django-api-versioning

The package's `@endpoint` decorator registers a view for a version range. A declaration using `version=N` applies from version N through `API_MAX_VERSION`, inclusive.

For example, with `API_MIN_VERSION = 1` and `API_MAX_VERSION = 2`, a view registered at version 1 is available in both v1 and v2. If another view is registered for the same path at version 2, that registration replaces the v2 route without changing the v1 route.

Install the package from [django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/).

### Define the v1 views

Start with the base implementations:

```python
# settings.py
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

```python
# views.py
from django_api_versioning import endpoint
from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import F

from .models import Article
from .serializers import ArticleSerializerV1, ArticleSerializerV2


@endpoint("articles/", version=1)
class ArticleListView(ListAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializerV1
    permission_classes = [IsAuthenticated]


@endpoint("articles/<int:pk>/", version=1)
class ArticleDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializerV1
    permission_classes = [IsAuthenticated]


@endpoint("articles/trending/", version=1)
class ArticleTrendingView(ListAPIView):
    serializer_class = ArticleSerializerV1
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Article.objects.order_by("-views")[:10]
```

The three declarations register the list, detail, and trending endpoints from v1 onward. With the current maximum version of 2, each declaration initially produces a route for both v1 and v2.

### Override only the endpoints that change in v2

Suppose the detail response needs additional fields and the trending endpoint needs a different ranking formula. The list endpoint remains unchanged.

Use Python inheritance for the detail view, and register new implementations only for the two changed paths:

```python
# views.py — continued

@endpoint("articles/<int:pk>/", version=2)
class ArticleDetailViewV2(ArticleDetailView):
    serializer_class = ArticleSerializerV2

    def retrieve(self, request, *args, **kwargs):
        # Fetch the article once instead of calling super().retrieve(),
        # which would fetch it again.
        article = self.get_object()
        serializer = self.get_serializer(article)
        data = dict(serializer.data)

        data["comments"] = list(
            article.comments.values("id", "text")
        )
        data["author_name"] = article.author.get_full_name()

        return Response(data)


@endpoint("articles/trending/", version=2)
class ArticleTrendingViewV2(ArticleTrendingView):
    serializer_class = ArticleSerializerV2

    def get_queryset(self):
        return (
            Article.objects
            .annotate(engagement=F("views") + 2 * F("likes"))
            .order_by("-engagement")[:20]
        )
```

`ArticleDetailViewV2` inherits the update and delete behavior from `ArticleDetailView`. It changes the serializer and overrides `retrieve()` to add response-specific fields.

`ArticleTrendingViewV2` inherits the base view configuration and overrides only `get_queryset()` and `serializer_class`.

There is no v2 declaration for `ArticleListView`. Its v1 registration remains active through `API_MAX_VERSION`, so the same implementation serves both versions.

### Register the generated URL patterns

Import the modules containing the decorated views before importing the package's URL patterns. The imports execute the decorators and populate the route registry.

```python
# project/urls.py
from django.urls import include, path

from api import views  # noqa: F401 — import first to register endpoints

from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

With the default `API_BASE_PATH = "api/v{version}/"`, the registrations produce:

| URL pattern | View | Registration |
|---|---|---|
| `/api/v1/articles/` | `ArticleListView` | v1 |
| `/api/v2/articles/` | `ArticleListView` | v1, carried forward |
| `/api/v1/articles/<int:pk>/` | `ArticleDetailView` | v1 |
| `/api/v2/articles/<int:pk>/` | `ArticleDetailViewV2` | v2 |
| `/api/v1/articles/trending/` | `ArticleTrendingView` | v1 |
| `/api/v2/articles/trending/` | `ArticleTrendingViewV2` | v2 |

**Now:**

- `GET /api/v1/articles/` → `ArticleListView`
- `GET /api/v2/articles/` → `ArticleListView`
- `GET /api/v1/articles/42/` → `ArticleDetailView`
- `GET /api/v2/articles/42/` → `ArticleDetailViewV2`
- `GET /api/v1/articles/trending/` → `ArticleTrendingView`
- `GET /api/v2/articles/trending/` → `ArticleTrendingViewV2`

Five `@endpoint` declarations produce six versioned URL patterns. The unchanged list endpoint needs only one declaration. The detail and trending endpoints each need a v1 declaration and a v2 override.

Two different forms of inheritance are involved:

- **Python inheritance:** `ArticleDetailViewV2(ArticleDetailView)` and `ArticleTrendingViewV2(ArticleTrendingView)` reuse view configuration and methods.
- **Routing inheritance:** the v1 registration for `articles/` remains active through `API_MAX_VERSION`, so it also serves v2 without another declaration.

**Scope: routing only.** The package selects which view handles each versioned URL. It does not determine whether a response change is backward compatible, merge serializers, or guarantee that an unchanged implementation still satisfies the v2 API contract. Test each supported version's response behavior and contract separately.

For the package's exact registration, collision, and ViewSet behavior, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## DRF ViewSet alternative: Python inheritance with per-version routers

The same view-code inheritance pattern can be implemented using DRF `ModelViewSet` classes and a router for each API version. This approach does not require `django-api-versioning`.

The following is an alternative implementation of the same example. It is not intended to be combined with the decorator-based views above.

```python
# views.py
from django.db.models import F

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Article
from .serializers import ArticleSerializerV1, ArticleSerializerV2


class ArticleViewSetV1(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializerV1
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def trending(self, request):
        # v1: top 10 by views
        articles = Article.objects.order_by("-views")[:10]
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)


class ArticleViewSetV2(ArticleViewSetV1):
    serializer_class = ArticleSerializerV2

    def retrieve(self, request, *args, **kwargs):
        article = self.get_object()
        serializer = self.get_serializer(article)
        data = dict(serializer.data)

        data["comments"] = list(
            article.comments.values("id", "text")
        )
        data["author_name"] = article.author.get_full_name()

        return Response(data)

    @action(detail=False, methods=["get"])
    def trending(self, request):
        # v2: top 20 by engagement score
        articles = (
            Article.objects
            .annotate(engagement=F("views") + 2 * F("likes"))
            .order_by("-engagement")[:20]
        )
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def bookmark(self, request, pk=None):
        article = self.get_object()
        request.user.bookmarks.add(article)

        return Response(
            {"status": "bookmarked"},
            status=status.HTTP_201_CREATED,
        )
```

`ArticleViewSetV2` inherits the list, create, update, and destroy implementations from v1. It overrides `retrieve()` and `trending()`, and adds a new `bookmark` action.

The `bookmark` action adds the article to the requesting user's bookmarks. `IsAuthenticated` ensures the request comes from an authenticated user. Any additional business restrictions, such as preventing users from bookmarking their own articles, must be enforced separately.

The URL configuration needs a router registration for each version:

```python
# urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ArticleViewSetV1, ArticleViewSetV2

v1_router = DefaultRouter()
v1_router.register(
    r"articles",
    ArticleViewSetV1,
    basename="v1-article",
)

v2_router = DefaultRouter()
v2_router.register(
    r"articles",
    ArticleViewSetV2,
    basename="v2-article",
)

urlpatterns = [
    path("api/v1/", include(v1_router.urls)),
    path("api/v2/", include(v2_router.urls)),
]
```

Python inheritance avoids duplicating view methods, but each version still needs its own router registration. In a project with multiple ViewSets, each resource must be registered with the router for every version.

This is a consequence of maintaining separate routers per version, not a requirement that every DRF project must duplicate its entire URL configuration.

For details on router-generated routes and custom ViewSet actions, see the [DRF routers documentation](https://www.django-rest-framework.org/api-guide/routers/).

## ViewSet compatibility and package boundaries

The package's `@endpoint` decorator accepts Django class-based views and DRF generic views, but it does not accept a `ModelViewSet` class directly.

The reason is specific: the package calls `as_view()` without an action mapping, while DRF ViewSets require an action mapping to connect HTTP methods to actions.

If you want to keep a ViewSet, you have two options:

1. **Use per-version routers**, as shown above. DRF handles the ViewSet routes and custom actions.
2. **Register a configured `as_view()` callable** for an individual route:

   ```python
   @endpoint("articles/", version=1)
   ArticleViewSetV1.as_view({
       "get": "list",
       "post": "create",
   })
   ```

   This registers that configured callable for the specified route. It does not automatically register the ViewSet's detail routes or custom `@action` handlers.

The package example uses generic views, not ViewSets. It demonstrates versioned endpoint registration and view inheritance, but it is not a drop-in replacement for all router-generated ViewSet functionality.

The [integration project's URLconf](https://github.com/mojtaba-arvin/django-api-versioning/blob/v0.3.4/integration_test_project/project/urls.py) shows router-based ViewSet routes alongside decorator-based routes.

## Trade-offs and scope

Python inheritance and routing inheritance solve different parts of version maintenance.

| Scenario: 10 resources, two API versions | Per-version router registrations | `@endpoint` declarations |
| --- | ---: | ---: |
| No resources change in v2 | 20 | 10 |
| 5 resources change in v2 | 20 | 15 |
| All 10 resources change in v2 | 20 | 20 |

The counts assume one ViewSet registration per resource in each version router, and one package declaration for each unchanged resource plus a v2 declaration for each changed resource.

The comparison shows the actual registration savings:

- **No resources change:** one declaration per resource covers both versions.
- **Half the resources change:** 15 declarations replace 20 router registrations, a 25% reduction.
- **All resources change:** there is no reduction in registration count, although Python inheritance can still reduce duplicated view code.

**When the benefit is smaller:** If nearly every resource changes at each version boundary, or if the versioned endpoint sets are substantially different, routing inheritance may save little. Per-version routers can be a reasonable fit, particularly when the project relies heavily on `ModelViewSet` and custom router actions.

**When routing inheritance matters most:** When multiple API versions share a meaningful set of unchanged endpoint paths and you want those paths carried forward without maintaining a separate registration for every version.

The important distinction is that route reuse does not prove API contract compatibility. If an endpoint's response, permissions, filtering, or behavior changes, review and test its registration and contract for every supported version.

## Next steps

If your API has several versions and a growing set of unchanged endpoints, compare the registration model with your current routing structure. The package's [decorator implementation](https://github.com/mojtaba-arvin/django-api-versioning/blob/v0.3.4/django_api_versioning/decorators.py) contains the exact signature and version-range registration logic.

Disclosure: I maintain `django-api-versioning`, the package discussed in this article.

To evaluate the package against your own versioning requirements, start with the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
