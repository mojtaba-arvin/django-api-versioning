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

> **Package disclosure:** The author is the creator, owner, and maintainer of `django-api-versioning`.

When introducing API v2, you usually need to keep v1 available while clients migrate. Both versions need their own runtime routes, but not every endpoint needs a new implementation.

The challenge is avoiding repeated declarations for endpoints whose implementation and contract have not changed.

[`django-api-versioning`](https://pypi.org/project/django-api-versioning/) addresses this at the URL-registration layer. You declare an endpoint at the version where its implementation becomes active. That declaration registers the endpoint from that version through `API_MAX_VERSION`. A later declaration for the same route replaces it from its own version onward.

This means an endpoint introduced in v1 can remain available in v2 without a second declaration. When its implementation changes in v2, you register the new implementation at v2.

The package manages routing, not semantic API compatibility. You still decide whether a response, request schema, permission rule, or other behavior is compatible with older clients.

The examples in this article demonstrate the package's endpoint registration and routing model. For the exact registration and routing rules, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

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

Import the views during URLconf initialization so their decorators register routes before Django first resolves requests:

```python
# project/urls.py

from django.urls import include, path

from api import views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

Importing `api.views` executes the decorators and populates the registry. The package's exported `urlpatterns` references the registry's shared list rather than a copy, so importing that list before the view module does not permanently capture an empty snapshot. Keep imports explicit during URLconf initialization and ensure registration is complete before request resolution.

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

A DRF API test should create its own data and mark database access explicitly. The following example assumes `category` and `likes` are sufficient to create an `Article`; supply any additional required model fields used by your project.

```python
import pytest
from rest_framework.test import APIClient

from articles.models import Article


@pytest.mark.django_db
def test_article_list_contract_by_version():
    Article.objects.create(category="news", likes=100)
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

The routers generate list, detail, and custom-action routes for their respective ViewSets. The v2 ViewSet inherits the v1 recent action and adds the trending action. This is the plain DRF-only approach: the application maintains each version's URL registrations and prefixes.

When you want the package registry to manage version-specific ViewSet routes and carry unchanged generated routes forward independently, register both classes with `VersionedRouter`:

```python
# urls.py
from django_api_versioning.routers import VersionedRouter
from .views_v1 import ArticleViewSetV1
from .views_v2 import ArticleViewSetV2

router = VersionedRouter()
router.register("articles", ArticleViewSetV1, version=1, basename="article")
router.register("articles", ArticleViewSetV2, version=2, basename="article")

urlpatterns = router.urls
```

Configure `VersionedRouterVersioning` as DRF's `DEFAULT_VERSIONING_CLASS` when the ViewSets need `request.version`, `reverse_action()`, or version-aware hyperlinked serializer URLs. The [dedicated ViewSet guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/025-django-api-versioning-viewset-support-limitations/) documents the full integration.

Plain per-version `SimpleRouter` instances remain a valid alternative when you want to manage the version prefixes yourself. `VersionedRouter` integrates with `SimpleRouter`; it does not claim `DefaultRouter` API-root or format-suffix parity.

### The important difference

These approaches operate at different levels:

| Concern | Plain DRF routers | `@endpoint` for generic views | `VersionedRouter` |
| --- | --- | --- | --- |
| Main abstraction | ViewSet and router | Individual endpoint declaration | ViewSet and package registry |
| URL generation | Router-generated routes | Registry-generated patterns | DRF `SimpleRouter` patterns registered in the package registry |
| Reuse unchanged behavior | Python inheritance and manual route registration | Keep the earlier endpoint declaration active | Per-generated-route version inheritance |
| New implementation | Register a version-specific ViewSet | Add a declaration at the new version | Register the new ViewSet at its source version |
| Custom ViewSet actions | Supported by routers | One configured callable per explicit route; not full router generation | Supported through DRF `SimpleRouter` integration |
| Version identification | Configure a DRF versioning scheme separately | Configure a matching DRF scheme if the view needs `request.version` | `VersionedRouterVersioning` supplies `request.version` and namespace-aware reversal |
| Version carry-forward | Must be configured in the URL/router structure | Built into `version=N` registration | Built into per-route registry resolution |

Use `@endpoint` when the API is organized around Django views, DRF `APIView`, or generic views. Use `VersionedRouter` when it is organized around DRF `ModelViewSet` classes and you want the package registry to manage per-route inheritance. Plain DRF routers remain appropriate when the application intentionally manages every version's URL configuration itself.

The `@endpoint` decorator is not a replacement for ViewSet action mapping; `VersionedRouter` is the package's dedicated integration for that use case.

## ViewSet boundary: use routers where they fit

A DRF `ModelViewSet` class cannot be decorated directly with `@endpoint`. The package calls `.as_view()` for class-based views, but a ViewSet requires an action mapping.

For package-managed ViewSet routing, use `VersionedRouter`, which delegates route generation to DRF's `SimpleRouter` and registers those patterns with the package's version registry. Plain `SimpleRouter` or `DefaultRouter` instances mounted under manually managed version prefixes remain valid DRF-only alternatives. The package integration does not provide `DefaultRouter` API-root or format-suffix parity.

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

A mixed project can use `VersionedRouter` for resource-oriented ViewSets and `@endpoint` for independent APIViews or generic views. Plain DRF routers can also coexist when their URL patterns are managed separately. Avoid mounting duplicate generated patterns; independent VersionedRouter instances with the same internal route pattern are rejected with `VersioningError`.

See the [Versioned DRF ViewSet integration guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/025-django-api-versioning-viewset-support-limitations/), the [DRF ViewSets documentation](https://www.django-rest-framework.org/api-guide/viewsets/), and [DRF routers documentation](https://www.django-rest-framework.org/api-guide/routers/) for the complete package and framework contracts.

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

It also provides version-level lifecycle metadata, deprecation headers, and sunset enforcement. Configure the required lifecycle dates deliberately; the middleware does not decide when your clients are ready to migrate.

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
        "deprecated_at": "2026-12-01T00:00:00+00:00",
        "sunset": "2027-06-01",
    },
}
```

For a version configured with `status="deprecated"` and a valid `deprecated_at` date, the middleware adds the date-valued `Deprecation` header. If a `sunset` date is also configured, it adds a `Sunset` header.

A deprecated lifecycle entry must include `deprecated_at` as an ISO 8601 date or datetime. The package emits that date as the RFC 9745 Structured Field value, such as `Deprecation: @1796083200`; it no longer emits the legacy `Deprecation: true` value. The optional `sunset` value is emitted in the HTTP-date format defined by RFC 8594. See the [v1.0.0 lifecycle implementation](https://github.com/mojtaba-arvin/django-api-versioning/blob/v1.0.0/django_api_versioning/lifecycle.py) and [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md#12-version-lifecycle-headers).

The middleware also enforces the configured sunset date:

- A sunset date in the past triggers `410 Gone`.
- A `retired` status without a past sunset date does not, by itself, trigger `410 Gone`.
- A `retired` version with a future sunset date is still served and carries the `Sunset` header, plus `Deprecation` when `deprecated_at` is configured.
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

Plain per-version DRF routers remain a natural choice when:

- You want to own every version's URL prefix and router registration.
- You rely on `DefaultRouter` API-root or format-suffix behavior that `VersionedRouter` does not provide.
- The API has few versions and the URL configuration is already easy to maintain.

For package-managed ViewSet route inheritance, use `VersionedRouter`; DRF's `SimpleRouter` route generation remains the supported integration boundary.

The benefit of the package depends on the endpoint structure and how often endpoints change. There is no universal endpoint-count threshold. If every endpoint changes at every version boundary, the carry-forward advantage is smaller. If many endpoints remain unchanged, avoiding repeated declarations becomes more useful.

**Scope: routing only.** The package determines which implementation is attached to each versioned URL. Your application remains responsible for the compatibility of serializers, permissions, filtering, pagination, and other API behavior.

## Next steps

To explore the implementation and apply declarative versioned routing to your Django project, start with the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
