---
slug: "020-migrate-django-rest-api-v1-v2-without-duplicating-routes"
title: "Migrate a Django REST API from v1 to v2 with Fewer Declarations"
description: "Use django-api-versioning to carry unchanged endpoints into later API versions while registering new implementations only where contracts change."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "Django API versioning"
  - "Django REST Framework"
  - "API migration"
  - "Endpoint registration"
  - "Backward compatibility"
---

# Migrate a Django REST API from v1 to v2 with Fewer Declarations

When introducing API v2, you usually need to keep v1 available while clients migrate. Both versions need their own runtime routes, but not every endpoint needs a new implementation.

The challenge is avoiding repeated declarations for endpoints whose implementation and contract have not changed.

[`django-api-versioning`](https://pypi.org/project/django-api-versioning/) addresses this at the URL-registration layer. You declare an endpoint at the version where its implementation becomes active. That declaration registers the endpoint from that version through `API_MAX_VERSION`. A later declaration for the same route replaces it from its own version onward.

This means an endpoint introduced in v1 can remain available in v2 without a second declaration. When its implementation changes in v2, you register the new implementation at v2.

The package manages routing, not semantic API compatibility. You still decide whether a response, request schema, permission rule, or other behavior is compatible with older clients.

I maintain `django-api-versioning`. The examples in this article demonstrate its endpoint registration and routing model. For the exact registration and routing rules, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Register unchanged endpoints once

Assume an existing `Article` model with `created_at`, `category`, and `likes` fields. The API exposes:

- `GET /articles/` and `POST /articles/`
- `GET`, `PUT`, `PATCH`, and `DELETE /articles/<pk>/`
- `GET /articles/recent/`

In v2:

- The list endpoint changes its response serializer and supports category filtering.
- The detail endpoint uses the new serializer.
- The recent endpoint remains unchanged.
- A new trending endpoint is introduced.

The following serializers make the response-contract difference explicit:

```python
# serializers.py

from rest_framework import serializers

from .models import Article


class ArticleSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ("id", "created_at", "category", "likes")


class ArticleSerializerV2(ArticleSerializerV1):
    is_popular = serializers.SerializerMethodField()

    class Meta(ArticleSerializerV1.Meta):
        fields = (*ArticleSerializerV1.Meta.fields, "is_popular")

    def get_is_popular(self, obj):
        return obj.likes >= 100
```

Configure the supported version range:

```python
# settings.py

API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

The default URL template is `api/v{version}/`. With this configuration, the package generates paths under `/api/v1/` and `/api/v2/`.

Declare the v1 implementations:

```python
# views.py

from django_api_versioning import endpoint
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from .models import Article
from .serializers import ArticleSerializerV1, ArticleSerializerV2


@endpoint("articles/", version=1, view_name="article-list-v1")
class ArticleListViewV1(ListCreateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializerV1


@endpoint(
    "articles/<int:pk>/",
    version=1,
    view_name="article-detail-v1",
)
class ArticleDetailViewV1(RetrieveUpdateDestroyAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializerV1


@endpoint(
    "articles/recent/",
    version=1,
    view_name="article-recent",
)
class ArticleRecentViewV1(ListAPIView):
    serializer_class = ArticleSerializerV1

    def get_queryset(self):
        return Article.objects.order_by("-created_at")[:10]
```

Each `version=1` declaration registers its route for v1 and every subsequent version up to `API_MAX_VERSION`.

With the current configuration, all three endpoints already have v1 and v2 routes. No separate v2 declaration is needed for `recent/`.

Now register only the implementations that change in v2:

```python
# views.py

@endpoint("articles/", version=2, view_name="article-list-v2")
class ArticleListViewV2(ArticleListViewV1):
    serializer_class = ArticleSerializerV2

    def get_queryset(self):
        queryset = Article.objects.all()
        category = self.request.query_params.get("category")

        if category:
            queryset = queryset.filter(category=category)

        return queryset


@endpoint(
    "articles/<int:pk>/",
    version=2,
    view_name="article-detail-v2",
)
class ArticleDetailViewV2(ArticleDetailViewV1):
    serializer_class = ArticleSerializerV2


@endpoint(
    "articles/trending/",
    version=2,
    view_name="article-trending",
)
class ArticleTrendingViewV2(ListAPIView):
    serializer_class = ArticleSerializerV2

    def get_queryset(self):
        return Article.objects.order_by("-likes")[:20]
```

The Python inheritance in `ArticleListViewV2` and `ArticleDetailViewV2` reuses view behavior. It is separate from the package's route-registration inheritance, which determines which implementation is attached to each versioned URL.

Import the views before importing the generated URL patterns:

```python
# project/urls.py

from django.urls import include, path

from api import views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

Importing `api.views` executes the decorators and populates the registry. Importing `api_urlpatterns` before the endpoint declarations have executed can leave the generated URL list incomplete.

## Understand the generated version matrix

With `API_MIN_VERSION = 1` and `API_MAX_VERSION = 2`, the six declarations produce seven final URL patterns.

| Endpoint | v1 handler | v2 handler |
| --- | --- | --- |
| `articles/` | `ArticleListViewV1` | `ArticleListViewV2` |
| `articles/<int:pk>/` | `ArticleDetailViewV1` | `ArticleDetailViewV2` |
| `articles/recent/` | `ArticleRecentViewV1` | `ArticleRecentViewV1` |
| `articles/trending/` | No package route | `ArticleTrendingViewV2` |

The final row means that this article's package declarations do not register a trending route in v1. A request to that path therefore has no matching package route; it returns 404 unless another URL pattern in the project matches it.

The four rows represent endpoint templates, not four concrete URL patterns.

The resulting package URL patterns are:

```text
/api/v1/articles/
/api/v1/articles/<int:pk>/
/api/v1/articles/recent/

/api/v2/articles/
/api/v2/articles/<int:pk>/
/api/v2/articles/recent/
/api/v2/articles/trending/
```

There are:

- **6 `@endpoint` declarations:** three for v1 and three for v2.
- **7 final URL patterns:** three under v1 and four under v2.
- **1 unchanged endpoint carried forward:** `articles/recent/`.
- **1 endpoint introduced in v2:** `articles/trending/`.

The v2 declarations for `articles/` and `articles/<int:pk>/` replace the implementations generated by their v1 declarations for the v2 routes. The v1 declaration for `articles/recent/` remains active in both versions because no later declaration replaces it.

### How registration precedence works

For a requested route, the registry resolves collisions using the declaration's `source_version`.

The rule is:

1. A declaration with a higher `source_version` takes precedence over one with a lower `source_version`.
2. If two declarations have the same `source_version`, the last registered declaration wins.
3. For a `version=N` declaration, the source version is N, even though the declaration registers routes for N through `API_MAX_VERSION`.

For example, the v1 list declaration initially registers both v1 and v2. The v2 list declaration then replaces the v2 route because its source version is higher. The v1 route remains unchanged.

This is a registration-precedence rule, not Python method inheritance or a runtime search through view classes.

### What happens when another version is added?

Suppose you later set:

```python
API_MAX_VERSION = 3
```

The existing segment declarations extend to v3 automatically:

- The v1 recent endpoint remains available in v3.
- The v2 list and detail implementations remain available in v3.
- The v2 trending endpoint also remains available in v3.

If the list endpoint changes again in v3, add a declaration with `version=3` for that route. It will replace the earlier implementation from v3 onward.

This behavior is route-registration inheritance. It does not create Python subclasses, merge view methods, or establish that an API contract is backward-compatible.

**Now:**

- `/api/v1/articles/` resolves to `ArticleListViewV1`.
- `/api/v2/articles/` resolves to `ArticleListViewV2`.
- `/api/v3/articles/` also resolves to `ArticleListViewV2`, unless a v3 declaration replaces it.
- `/api/v1/articles/recent/`, `/api/v2/articles/recent/`, and `/api/v3/articles/recent/` resolve to `ArticleRecentViewV1`.
- `/api/v1/articles/trending/` has no route from these declarations; v2 and v3 resolve to `ArticleTrendingViewV2`.

This is why the version matrix must be reviewed whenever `API_MAX_VERSION` changes or a new API contract is introduced.

### Reverse lookup for carried-forward endpoints

A single declaration can generate multiple URL patterns with the same `view_name`. Do not rely on Django's plain `reverse()` to select a particular API version when a name is shared across versioned routes.

Use the package's version-aware helper:

```python
from django_api_versioning import api_reverse

recent_v1_url = api_reverse("article-recent", version=1)
recent_v2_url = api_reverse("article-recent", version=2)
```

Passing the version makes the intended route explicit. If multiple matching versions exist and no version is supplied, `api_reverse()` raises `AmbiguousVersionError`.

## Verify the response contract, not only the route

A route resolving successfully does not prove that the correct response contract is being served.

Assuming the test database contains at least one `Article`, a DRF API test can check the fields returned by each version:

```python
from rest_framework.test import APIClient


def test_article_list_contract_by_version():
    client = APIClient()

    response_v1 = client.get("/api/v1/articles/")
    response_v2 = client.get("/api/v2/articles/")

    assert response_v1.status_code == 200
    assert response_v2.status_code == 200

    assert set(response_v1.data[0]) == {
        "id",
        "created_at",
        "category",
        "likes",
    }

    assert set(response_v2.data[0]) == {
        "id",
        "created_at",
        "category",
        "likes",
        "is_popular",
    }
```

This checks the response contract, not just whether both URLs return a successful status code. The test data and expected fields should reflect the actual serializers and application contract.

The package determines which view handles each route. The application tests whether that view returns the intended data.

## How this differs from per-version DRF routers

The closest DRF-only alternative for resource-oriented APIs is to use a `ModelViewSet` with a router for each version.

For example, the v1 ViewSet can define the resource routes and its recent action:

```python
# views_v1.py

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Article
from .serializers import ArticleSerializerV1


class ArticleViewSetV1(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializerV1

    @action(detail=False, methods=["get"])
    def recent(self, request):
        queryset = Article.objects.order_by("-created_at")[:10]
        serializer = ArticleSerializerV1(queryset, many=True)
        return Response(serializer.data)
```

The v2 ViewSet inherits the v1 action and adds the new behavior:

```python
# views_v2.py

from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Article
from .serializers import ArticleSerializerV1, ArticleSerializerV2
from .views_v1 import ArticleViewSetV1


class ArticleViewSetV2(ArticleViewSetV1):
    serializer_class = ArticleSerializerV2

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == "list":
            category = self.request.query_params.get("category")
            if category:
                queryset = queryset.filter(category=category)

        return queryset

    @action(detail=False, methods=["get"])
    def trending(self, request):
        queryset = Article.objects.order_by("-likes")[:20]
        serializer = ArticleSerializerV2(queryset, many=True)
        return Response(serializer.data)
```

The inherited `recent` action explicitly uses `ArticleSerializerV1`, so its response contract remains unchanged in v2. The v2 list and detail actions use `ArticleSerializerV2`, while the new trending action also uses the v2 serializer.

Register each version's ViewSet with its own router:

```python
# urls.py

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views_v1 import ArticleViewSetV1
from .views_v2 import ArticleViewSetV2

v1_router = SimpleRouter()
v1_router.register("articles", ArticleViewSetV1, basename="v1-article")

v2_router = SimpleRouter()
v2_router.register("articles", ArticleViewSetV2, basename="v2-article")

urlpatterns = [
    path("api/v1/", include(v1_router.urls)),
    path("api/v2/", include(v2_router.urls)),
]
```

The routers generate list, detail, and custom-action routes for their respective ViewSets. The v2 ViewSet inherits the v1 recent action and adds the trending action.

This is a good fit when your API is organized around resource-oriented ViewSets and uses DRF actions extensively.

However, the router configuration still explicitly registers each ViewSet under its version prefix. Python inheritance shares implementation; it does not make the v1 router's URLs appear under v2.

### The important difference

These approaches operate at different levels:

| Concern | DRF routers | `django-api-versioning` |
| --- | --- | --- |
| Main abstraction | ViewSet and router | Individual endpoint declaration |
| URL generation | Router-generated routes | Registry-generated patterns |
| Reuse unchanged behavior | Python inheritance or shared base classes | Keep the earlier route declaration active |
| New implementation | Register a version-specific ViewSet | Add a declaration at the new version |
| Custom ViewSet actions | Supported by routers | Not registered directly by `@endpoint` |
| Version carry-forward | Must be configured in the URL/router structure | Built into `version=N` registration |

The package is most useful when endpoints are naturally represented as separate Django or DRF generic views and the set of changed endpoints is smaller than the set of endpoints that remain unchanged.

It is not a replacement for DRF routers when your API is primarily built around `ModelViewSet`.

## ViewSet boundary: use routers where they fit

A DRF `ModelViewSet` class cannot be decorated directly with `@endpoint`. The package calls `.as_view()` for class-based views, but a ViewSet requires an action mapping.

For resource-shaped APIs, keep using `SimpleRouter` or `DefaultRouter` and mount the router URLs under the appropriate version prefix.

For a single explicitly configured route, you can pass a configured `as_view()` callable to the decorator:

```python
from django_api_versioning import endpoint

article_list_view = ArticleViewSetV1.as_view({
    "get": "list",
    "post": "create",
})

endpoint(
    "articles/",
    version=1,
    view_name="article-list-v1",
)(article_list_view)
```

This registers that particular callable for that route. It does not register the ViewSet's detail route or its custom actions automatically.

A project can use both approaches: routers for resource-oriented ViewSets and `@endpoint` for independent APIViews or generic views. They remain separate URL-registration mechanisms, so avoid mounting conflicting route patterns under the same prefix.

See the [DRF ViewSets documentation](https://www.django-rest-framework.org/api-guide/viewsets/) and [DRF routers documentation](https://www.django-rest-framework.org/api-guide/routers/) for the framework-side behavior.

## What the package does not decide

The package selects which view handles a URL. It does not decide whether a change is backward-compatible.

For example:

- Adding an optional response field may be compatible with clients that ignore unknown fields, but strict client schemas may reject it.
- Renaming or removing a response field is generally a breaking change.
- Changing a field's type can break clients even if the field name remains the same.
- Changing filtering, permissions, pagination, or status-code behavior can also change the API contract.

If an endpoint changes in a way that breaks existing clients, register a new implementation at the new version. Keep the old implementation available for clients that still use the previous version.

Also remember that `version=N` carries an implementation forward automatically. If an endpoint's contract should not carry forward unchanged, add a later declaration or use explicit `versions=[...]` registration to select the versions where it should exist.

The package does not provide:

- Automatic response or serializer versioning.
- Automatic OpenAPI schema separation.
- A built-in version-discovery endpoint.
- Client migration tracking.
- A decision about whether a particular API change is backward-compatible.

It does provide lifecycle middleware, but its current `Deprecation` header value has an important standards limitation, described below.

## Rolling out v2 without breaking v1 clients

Route registration is only one part of a safe migration. A practical rollout is:

1. **Deploy v2 alongside v1.** Keep both sets of routes available. Do not change the behavior of the v1 handlers while introducing v2.
2. **Publish the v2 contract.** Document changed request and response fields, validation behavior, and any changes to filtering or permissions.
3. **Announce the migration.** Give clients a migration guide and a planned support window.
4. **Monitor usage by version.** Use request logs, gateway metrics, or application-level counters to identify clients still using v1.
5. **Configure v1 deprecation deliberately.** Use the package's lifecycle middleware where its behavior meets the application's requirements.
6. **Retire v1 after the migration window.** Remove its routes and implementation only after the announced support period and client migration requirements have been addressed.

### Lifecycle middleware

`django-api-versioning` provides `LifecycleMiddleware` and `API_VERSION_LIFECYCLE`.

Add `django_api_versioning.lifecycle.LifecycleMiddleware` to the project's `MIDDLEWARE` setting and configure the lifecycle of the relevant version.

For example, this configuration uses an illustrative future sunset date. Replace it with the date approved for the actual API rollout:

```python
# settings.py

API_VERSION_LIFECYCLE = {
    1: {
        "status": "deprecated",
        "sunset": "2027-06-01",
    },
}
```

For a version configured with `status="deprecated"`, the middleware adds a `Deprecation` header. If a sunset date is configured, it also adds a `Sunset` header.

There is an important standards limitation: the package's lifecycle middleware currently emits `Deprecation: true`. RFC 9745 specifies a Structured Field Date value for this header, for example `Deprecation: @1688169599`. The emitted `true` value is not the RFC 9745 date format. Applications requiring RFC 9745 compliance need to provide the appropriate date-valued header themselves or use an implementation that supports it. Check the [current lifecycle implementation](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/lifecycle.py) for the exact behavior.

The middleware also enforces the configured sunset date:

- A sunset date in the past triggers `410 Gone`.
- A `retired` status without a past sunset date does not, by itself, trigger `410 Gone`.
- A future sunset date with `retired` status does not produce the same deprecation headers as `deprecated` status.
- The middleware does not generate a `Link` header pointing to migration documentation.

If the application emits an RFC 9745 deprecation date separately, ensure that the `Sunset` date is not earlier than the deprecation date.

The middleware implements part of the technical lifecycle behavior. The application team remains responsible for defining lifecycle dates, communicating with clients, monitoring usage, and planning migrations.

For the HTTP standard, see [RFC 9745: The Deprecation HTTP Response Header Field](https://www.rfc-editor.org/rfc/rfc9745.html).

A versioned URL structure does not guarantee zero downtime. Database migrations, deployment sequencing, and application health remain separate operational concerns.

## Trade-offs and scope

`django-api-versioning` is useful when:

- You represent endpoints as independent Django views or DRF generic views.
- Many endpoints remain unchanged between API versions.
- You want the version matrix to be derived from endpoint declarations rather than repeated URL registration.
- You are comfortable reviewing the carry-forward behavior when increasing `API_MAX_VERSION`.

Per-version DRF routers remain a natural choice when:

- Your API is primarily built around `ModelViewSet`.
- You rely heavily on `@action`.
- You prefer router-managed resource routes and explicit router configuration.
- The API has few versions and the URL configuration is already easy to maintain.

The benefit of the package depends on the endpoint structure and how often endpoints change. There is no universal endpoint-count threshold. If every endpoint changes at every version boundary, the carry-forward advantage is smaller. If many endpoints remain unchanged, avoiding repeated declarations becomes more useful.

**Scope: routing only.** The package determines which implementation is attached to each versioned URL. Your application remains responsible for the compatibility of serializers, permissions, filtering, pagination, and other API behavior.

## Next steps

To explore the implementation and apply declarative versioned routing to your Django project, start with the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
