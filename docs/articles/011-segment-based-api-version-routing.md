---
slug: "011-segment-based-api-version-routing-django"
title: "Segment-based API version routing in Django"
description: "Compare DRF routers and django-api-versioning for segment-based URLs, including version carry-forward and selective endpoint overrides."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "API versioning"
  - "URL segments"
  - "Django REST Framework"
  - "API routing"
  - "django-api-versioning"
---

# Segment-based API version routing in Django

Segment-based API versioning puts the version directly in the URL path:

```text
/api/v1/users/
/api/v2/users/
```

The version is visible to clients and forms part of Django's route matching. When different API versions need different implementations, the application must map each versioned URL to the appropriate view.

For applications with separate views per version, [django-api-versioning](https://pypi.org/project/django-api-versioning/) provides declarative endpoint registration. A declaration can cover multiple versions, while a higher-version declaration can selectively replace its implementation.

This article uses the package as the primary approach, then compares it with two DRF-only alternatives: one router per version and dynamic router construction from a configuration list.

The examples assume:

- `User` has `is_active`, `last_login`, and a `followers` relation.
- `Post` has a foreign key to `User` using Django's default reverse relation, `user.post_set`, and an integer `likes` field representing the number of likes.
- `UserSerializerV1`, `UserSerializerV2`, `UserSerializerV3`, `PostSerializerV1`, and `PostSerializerV2` are defined in the application's `serializers.py`.
- The examples import the project's `User` model from `.models`. If the application uses Django's configured user model, use `from django.contrib.auth import get_user_model` and assign `User = get_user_model()` instead.

The package examples use read-oriented generic views and `APIView` classes. The manual router examples use `ModelViewSet`, which exposes CRUD operations. Therefore, the examples demonstrate comparable route mappings for the endpoints shown, not identical HTTP method surfaces.

## Register versioned endpoints with django-api-versioning

The package uses integer version identifiers in Python configuration and decorator arguments. The `v` prefix belongs to the generated URL, not to the version value passed to `endpoint()`.

Configure the supported version range:

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

With this configuration, an endpoint registered using `version=1` is registered for v1 and v2. A declaration using `version=2` applies from v2 onward, within the configured range.

### Define the versioned views

```python
# views.py

from django.shortcuts import get_object_or_404
from django_api_versioning import endpoint
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, Post
from .serializers import (
    UserSerializerV1,
    UserSerializerV2,
    PostSerializerV1,
    PostSerializerV2,
)


# v1: base endpoints, registered from v1 onward.

@endpoint("users/", version=1)
class UserListViewV1(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/<int:pk>/", version=1)
class UserDetailViewV1(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/<int:pk>/status/", version=1)
class UserStatusViewV1(APIView):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return Response({
            "status": "active" if user.is_active else "inactive",
        })


@endpoint("posts/", version=1)
class PostListViewV1(ListAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializerV1


@endpoint("posts/<int:pk>/", version=1)
class PostDetailViewV1(RetrieveAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializerV1


# v2: redeclare only endpoints whose implementation changes.

@endpoint("users/", version=2)
class UserListViewV2(UserListViewV1):
    serializer_class = UserSerializerV2


@endpoint("users/<int:pk>/", version=2)
class UserDetailViewV2(UserDetailViewV1):
    serializer_class = UserSerializerV2


@endpoint("users/<int:pk>/status/", version=2)
class UserStatusViewV2(APIView):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return Response({
            "status": "active" if user.is_active else "inactive",
            "last_login": user.last_login,
        })


@endpoint("users/<int:pk>/activity/", version=2)
class UserActivityViewV2(APIView):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return Response({
            "posts_count": user.post_set.count(),
            "followers": user.followers.count(),
        })


@endpoint("posts/trending/", version=2)
class PostTrendingViewV2(ListAPIView):
    serializer_class = PostSerializerV2

    def get_queryset(self):
        return Post.objects.order_by("-likes")[:10]
```

The first argument to `endpoint()` is the endpoint postfix. The package combines it with `API_BASE_PATH` and the optional `app_name` segment to construct the final URL.

With the default `API_BASE_PATH = "api/v{version}/"`, this declaration:

```python
@endpoint("users/<int:pk>/", version=1)
class UserDetailViewV1(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1
```

generates routes equivalent to:

```text
/api/v1/users/<int:pk>/
/api/v2/users/<int:pk>/
```

The version range is expanded when the endpoint declaration is registered. It is not resolved by searching for another version's view when a request arrives.

### Mount the generated URL patterns

Import the modules containing the endpoint declarations before importing the package's URL patterns:

```python
# urls.py

from django.urls import include, path

from . import views  # noqa: F401 — import first so decorators register
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The import order matters. The `@endpoint` decorators register routes when their Python modules are imported. The package does not automatically discover application view modules.

If endpoint declarations are split across multiple modules, import all of them before importing `api_urlpatterns`.

For example:

```text
api/
    views/
        __init__.py
        v1.py
        v2.py
    urls.py
```

The URLconf must import both view modules before reading the package's URL patterns:

```python
# api/urls.py

from django.urls import include, path

from .views import v1, v2  # noqa: F401
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The directory structure organizes the Python implementations. The package controls how their endpoint declarations are expanded across API versions.

### Resulting route map

With `API_MIN_VERSION = 1` and `API_MAX_VERSION = 2`, the ten declarations above produce twelve URL patterns: five in v1 and seven in v2.

| Endpoint | v1 | v2 |
| --- | --- | --- |
| `users/` | `UserListViewV1` | Explicitly replaced by `UserListViewV2` |
| `users/{pk}/` | `UserDetailViewV1` | Explicitly replaced by `UserDetailViewV2` |
| `users/{pk}/status/` | `UserStatusViewV1` | Explicitly replaced by `UserStatusViewV2` |
| `users/{pk}/activity/` | Not registered | `UserActivityViewV2` |
| `posts/` | `PostListViewV1` | Carried forward from v1 |
| `posts/{pk}/` | `PostDetailViewV1` | Carried forward from v1 |
| `posts/trending/` | Not registered | `PostTrendingViewV2` |

Here, `{pk}` is a documentation placeholder for the URL parameter, not literal Django path syntax.

The resulting URL-to-view mapping is:

| URL | View |
| --- | --- |
| `/api/v1/users/` | `UserListViewV1` |
| `/api/v2/users/` | `UserListViewV2` |
| `/api/v1/users/{pk}/` | `UserDetailViewV1` |
| `/api/v2/users/{pk}/` | `UserDetailViewV2` |
| `/api/v1/users/{pk}/status/` | `UserStatusViewV1` |
| `/api/v2/users/{pk}/status/` | `UserStatusViewV2` |
| `/api/v2/users/{pk}/activity/` | `UserActivityViewV2` |
| `/api/v1/posts/` | `PostListViewV1` |
| `/api/v2/posts/` | `PostListViewV1` |
| `/api/v1/posts/{pk}/` | `PostDetailViewV1` |
| `/api/v2/posts/{pk}/` | `PostDetailViewV1` |
| `/api/v2/posts/trending/` | `PostTrendingViewV2` |

**Now:**

- Requests to `/api/v1/users/` use `UserListViewV1`.
- Requests to `/api/v2/users/` use `UserListViewV2`.
- Requests to `/api/v1/posts/` and `/api/v2/posts/` both use `PostListViewV1`.
- Requests to `/api/v2/posts/trending/` use `PostTrendingViewV2`.
- The activity endpoint exists only in v2; it is not inherited from v1.

A URL pattern is counted once regardless of how many HTTP methods its view supports.

### How registration inheritance works

The package implements registration-time route inheritance, not request-time fallback traversal.

For `version=N`, the package registers the endpoint from N through `API_MAX_VERSION`, inclusive.

When multiple declarations target the same route, the declaration with the higher integer `source_version` takes precedence. If their source versions are equal, the most recently registered declaration wins.

For example:

```python
@endpoint("posts/", version=1)
class PostListViewV1(ListAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializerV1
```

covers both v1 and v2 when `API_MAX_VERSION = 2`.

There is no need to declare the unchanged posts list endpoint again in v2. You can release v2 without changing the posts list/detail views: their v1 registrations already cover v2.

If a v2 declaration is added for the same route, it replaces the v1 implementation for v2. The v1 route remains mapped to the v1 implementation.

These cases should be distinguished:

- **Carried forward:** a lower-version declaration supplies the implementation for a later version because no higher-version declaration replaces it.
- **Overridden:** a higher-version declaration replaces the implementation for that route from its source version onward.
- **Not registered:** no declaration covers that route in the target version.

A version outside the configured range is different from an endpoint that has no separate declaration for that version. For example, with `API_MAX_VERSION = 2`, no v3 route is generated. A request to `/api/v3/posts/` therefore does not match a generated route and normally receives a 404.

There is also an important contract risk: increasing `API_MAX_VERSION` can carry an older implementation into a newer version. That implementation may not satisfy the newer API contract. The package does not determine semantic compatibility. Review and test each supported version's response contract, serializers, permissions, filtering, and pagination.

For the exact decorator signature, URL construction, precedence rules, and supported view types, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

### Adding v3

To support v3, increase the maximum version:

```python
# settings.py

API_MAX_VERSION = 3
```

Existing declarations now extend through v3. Since the v2 declarations have higher source versions than the v1 declarations, the v2 implementations remain active in v3 unless new v3 declarations replace them.

If only the users list changes in v3, add a declaration for that endpoint:

```python
@endpoint("users/", version=3)
class UserListViewV3(UserListViewV2):
    serializer_class = UserSerializerV3
```

This example assumes `UserSerializerV3` is defined in the application's serializers module.

The v3 registration replaces the users list implementation for v3. Other endpoints continue to use the most recent registration that covers v3.

The project URLconf does not need a new router or another `path()` entry.

## Manual alternative: one router per version

If the application relies heavily on `ModelViewSet` and DRF's `@action`, a router per version preserves that programming model.

Define separate ViewSet classes:

```python
# views.py

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import User, Post
from .serializers import (
    UserSerializerV1,
    UserSerializerV2,
    PostSerializerV1,
    PostSerializerV2,
)


class UserViewSetV1(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        user = self.get_object()
        return Response({
            "status": "active" if user.is_active else "inactive",
        })


class UserViewSetV2(UserViewSetV1):
    serializer_class = UserSerializerV2

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        user = self.get_object()
        return Response({
            "status": "active" if user.is_active else "inactive",
            "last_login": user.last_login,
        })

    @action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        user = self.get_object()
        return Response({
            "posts_count": user.post_set.count(),
            "followers": user.followers.count(),
        })


class PostViewSetV1(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializerV1


class PostViewSetV2(PostViewSetV1):
    serializer_class = PostSerializerV2

    @action(detail=False, methods=["get"])
    def trending(self, request):
        posts = Post.objects.order_by("-likes")[:10]
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
```

Register each version's ViewSets with its own router:

```python
# urls.py

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    UserViewSetV1,
    UserViewSetV2,
    PostViewSetV1,
    PostViewSetV2,
)

v1_router = SimpleRouter()
v1_router.register("users", UserViewSetV1, basename="v1-user")
v1_router.register("posts", PostViewSetV1, basename="v1-post")

v2_router = SimpleRouter()
v2_router.register("users", UserViewSetV2, basename="v2-user")
v2_router.register("posts", PostViewSetV2, basename="v2-post")

urlpatterns = [
    path("api/v1/", include(v1_router.urls)),
    path("api/v2/", include(v2_router.urls)),
]
```

Distinct basenames prevent the two routers from registering identical URL names. When using `reverse()`, select the version-specific basename.

The routers generate five URL patterns in v1 and seven in v2:

| Route type | v1 | v2 |
| --- | ---: | ---: |
| Users list and detail | 2 | 2 |
| Users status | 1 | 1 |
| Users activity | Not registered | 1 |
| Posts list and detail | 2 | 2 |
| Posts trending | Not registered | 1 |
| **Total** | **5** | **7** |

The `{pk}` notation in a route description is a placeholder for the lookup value. It is not the literal Django path-converter syntax generated by `SimpleRouter`.

The router creates custom action URLs from the `@action` declarations. CRUD methods share the list and detail URL patterns; they do not each create a separate URL pattern.

Python inheritance shares CRUD behavior between the ViewSet classes. The v2 classes override the serializer or action implementation and add actions that exist only in v2.

The registration cost remains explicit: every resource needs a `register()` call in every version's router, even when the same ViewSet implementation is reused.

For the router registration model and generated routes, see the official [DRF routers documentation](https://www.django-rest-framework.org/api-guide/routers/).

## Manual alternative: dynamic router registration

A configuration list can reduce URLconf repetition by moving router registrations into data:

```python
# urls.py

from django.urls import include, path
from django.utils.module_loading import import_string
from rest_framework.routers import SimpleRouter

ENDPOINTS = [
    (1, "users", "myapp.views.UserViewSetV1"),
    (2, "users", "myapp.views.UserViewSetV2"),
    (1, "posts", "myapp.views.PostViewSetV1"),
    (2, "posts", "myapp.views.PostViewSetV2"),
]


def build_versioned_routers():
    routers_by_version = {}

    for version, endpoint_name, viewset_path in ENDPOINTS:
        if version not in routers_by_version:
            routers_by_version[version] = SimpleRouter()

        viewset_class = import_string(viewset_path)
        routers_by_version[version].register(
            endpoint_name,
            viewset_class,
            basename=f"v{version}-{endpoint_name}",
        )

    return [
        (f"api/v{version}/", router)
        for version, router in sorted(routers_by_version.items())
    ]


urlpatterns = [
    path(route, include(router.urls))
    for route, router in build_versioned_routers()
]
```

Replace `myapp` with the actual Python import path of the application.

The configuration uses integer version identifiers and sorts them numerically. The `v` prefix is added only when constructing the URL and basename.

This approach centralizes router construction, but it does not remove per-version endpoint registrations. Each endpoint/version pair still needs a configuration entry.

It also introduces string-based imports. A typo in an import path is detected at runtime when `import_string()` executes, rather than when an IDE or static analysis resolves a direct class reference.

The package takes a different approach: instead of maintaining a separate registration entry for every endpoint/version pair, declare the endpoint at its view and let the package expand the version range and apply higher-version replacements.

## ViewSet and Router boundary

The manual approaches use `ModelViewSet` with DRF routers and `@action`. This is supported directly by DRF.

The package approach uses Django class-based views and DRF `APIView` or generic views. A `ModelViewSet` class cannot be decorated directly with `@endpoint`, because the package calls `.as_view()` without the action mapping required by a ViewSet.

There are two ways to keep a ViewSet:

1. Use a DRF router per version, as in the manual approach.
2. Pass a configured callable such as `UserViewSetV1.as_view({"get": "list"})` to `@endpoint` for one explicitly configured route.

The second option registers one configured route. It is not a replacement for router-generated list, detail, and custom-action routes.

The practical boundary is:

- Use `ModelViewSet` and DRF routers for resource-shaped endpoints.
- Use `APIView` or generic views with `@endpoint` for non-resource endpoints and supported class-based views.
- Use a configured `ModelViewSet.as_view({...})` callable only when one explicitly configured route is appropriate.

The package does not automatically integrate with or inherit DRF router registrations.

The [integration project's URLconf](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/integration_test_project/project/urls.py) demonstrates router-based and decorator-based routing in the same project.

## Trade-offs and scope

**Scope: routing only.** `django-api-versioning` generates versioned URL patterns and selects the registered view for each route. It does not perform DRF request-version negotiation, automatically integrate ViewSets with routers, or guarantee semantic compatibility between API versions.

| Approach | Registration model | View structure | Main maintenance cost |
| --- | --- | --- | --- |
| Per-version routers | Explicit `register()` calls | `ModelViewSet` | Repeated registrations |
| Dynamic router configuration | Configuration list | `ModelViewSet` | String imports and configuration maintenance |
| `django-api-versioning` | Decorator declarations with version carry-forward and replacement | `APIView`, generic views, or configured callables | Import order and deliberate version-contract review |

**Manual per-version routers:** useful when the application relies on `ModelViewSet`, CRUD actions, and `@action`. The cost is one router registration per resource per version.

**Dynamic router registration:** useful when the registration list is easier to maintain as data than as repeated URLconf code. It centralizes construction but still requires a mapping for each endpoint/version pair.

**Decorator registration:** useful when separate versioned views are preferred and many endpoint registrations remain unchanged between versions. The package carries those registrations forward and allows changed endpoints to be redeclared at a higher version.

Segment-based routing is not the only way to expose the selected version to a view. DRF's header-based versioning schemes also make the selected version available through `request.version`. A URL segment makes the version explicit in the URL; it does not uniquely enable version-aware view behavior or inheritance.

The trade-off is not only import order or view type. Carry-forward can expose an older implementation under a newer version if the team forgets to review the endpoint's contract. Version-specific behavior must still be tested deliberately.

**When the benefit is smaller:** for a single version or a small set of endpoints with no repeated registrations, the package's version-range behavior may provide little maintenance benefit over explicit URL patterns.

Disclosure: I maintain django-api-versioning, the package discussed in this article.

## Next steps

If your API uses versioned URL segments and separate views, evaluate whether registration-time carry-forward and selective overrides fit your endpoint change pattern. Start with the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
