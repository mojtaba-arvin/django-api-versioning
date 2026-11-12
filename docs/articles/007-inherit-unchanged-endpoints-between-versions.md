---
slug: "007-inherit-unchanged-endpoints-between-api-versions-django"
title: "How to inherit unchanged endpoints between API versions in Django"
description: "Compare DRF's shared URLconf with django-api-versioning's version-based registrations, overrides, and routing inheritance."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "API versioning"
  - "Django REST Framework"
  - "Python inheritance"
  - "endpoint registration"
  - "URL routing"
---

# How to inherit unchanged endpoints between API versions in Django

When an API evolves from v1 to v2, not every endpoint necessarily needs a new implementation. Some endpoints change their response contract, while others can continue using their existing behavior.

The challenge is deciding how to represent that relationship in the URL configuration.

[django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/) provides routing inheritance: register an endpoint at its starting version, and its registration remains available in subsequent versions until a newer registration replaces it.

This is different from Python class inheritance. Python inheritance reuses view implementations; routing inheritance carries endpoint registrations across API versions.

This article examines both mechanisms, compares the package with DRF's built-in versioning capabilities, and explains when routing inheritance reduces the declarations you maintain.

## Routing inheritance with django-api-versioning

Consider an API with two user endpoints:

- v1 returns a user's ID and username.
- v2 adds email and registration date to the response.

The posts endpoint does not change between versions.

The package lets you register the two user implementations at their respective starting versions and register the unchanged posts endpoint only once.

### Define the serializers

The examples assume the project has a `Post` model with `id` and `title` fields. The user serializers use the active Django user model.

```python
# serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Post

User = get_user_model()


class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "date_joined"]


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["id", "title"]
```

If the project uses a custom user model, adjust the serializer fields to match its actual fields.

### Register version-specific and unchanged endpoints

Install the package and configure the supported version range:

```bash
pip install django-api-versioning
```

```python
# settings.py
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

Now register the view implementations:

```python
# api/views.py
from django.contrib.auth import get_user_model
from rest_framework.generics import ListAPIView

from django_api_versioning import endpoint

from .models import Post
from .serializers import (
    PostSerializer,
    UserSerializerV1,
    UserSerializerV2,
)

User = get_user_model()


@endpoint("users/", version=1)
class UserListV1(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/", version=2)
class UserListV2(UserListV1):
    serializer_class = UserSerializerV2


@endpoint("posts/", version=1)
class PostListView(ListAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
```

Two different forms of reuse are involved:

- `UserListV2` uses Python inheritance to reuse the implementation of `UserListV1`, changing only its serializer.
- `PostListView` uses routing inheritance. Its registration starts at v1 and remains active in v2 because no later registration replaces it.

The package does not create subclasses or copy view methods. It generates versioned URL patterns from the endpoint registrations.

### Mount the generated URL patterns

The application modules containing `@endpoint` declarations must be imported before the package's URL patterns are imported.

```python
# project/urls.py
from django.urls import include, path

from api import views  # noqa: F401 — import first so decorators register

from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The import of `api.views` executes the decorators and registers the endpoints. The package does not automatically discover application view modules.

If endpoint declarations are spread across multiple modules, import each module containing those declarations before importing `api_urlpatterns`.

With `API_MAX_VERSION = 2` and the default `API_BASE_PATH = "api/v{version}/"`, the registrations generate these URL patterns:

| Request path | Registered handler |
|---|---|
| `/api/v1/users/` | `UserListV1` |
| `/api/v2/users/` | `UserListV2` |
| `/api/v1/posts/` | `PostListView` |
| `/api/v2/posts/` | `PostListView` |

**Now:**

- A request to `/api/v1/users/` is handled by `UserListV1`.
- A request to `/api/v2/users/` is handled by `UserListV2`.
- A request to `/api/v1/posts/` is handled by `PostListView`.
- A request to `/api/v2/posts/` is also handled by `PostListView`.

Three endpoint declarations generate four versioned URL patterns. The unchanged posts endpoint requires no second registration.

**Scope: routing only.** The package determines which registered view handles each versioned URL. It does not guarantee that the response contracts, permissions, filtering, pagination, or other API behavior are compatible across versions.

## How routing inheritance and overrides work

The key rule is that `version=N` registers an endpoint for every version from N through `API_MAX_VERSION`, inclusive.

A registration at a higher starting version can replace the implementation for that version and subsequent versions without changing earlier registrations.

For example, with `API_MAX_VERSION = 2`, this declaration:

```python
@endpoint("posts/", version=1)
class PostListViewV1(ListAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
```

generates:

```text
/api/v1/posts/ → PostListViewV1
/api/v2/posts/ → PostListViewV1
```

Now register a new implementation at v2:

```python
@endpoint("posts/", version=2)
class PostListViewV2(PostListViewV1):
    queryset = Post.objects.order_by("-id")
```

The resulting routes are:

```text
/api/v1/posts/ → PostListViewV1
/api/v2/posts/ → PostListViewV2
```

The v2 registration replaces the v2 route. The v1 route continues using `PostListViewV1`.

You can release v2 without changing `PostListViewV1` or adding another posts endpoint declaration: the existing v1 registration already covers v2. When the posts implementation needs to change, add a v2 registration.

The rule can be expressed as a version range:

- A registration beginning at v1 covers v1 and later supported versions.
- A registration beginning at v2 replaces the earlier registration from v2 onward.
- A registration beginning at v3 does not create routes for v1 or v2.

An endpoint first registered at v3 is therefore not available in v1 or v2. This is different from an endpoint that exists in an earlier version but has no new registration in a later version: the latter continues to use its earlier registration.

This is routing inheritance, not Python inheritance. The registry stores endpoint registrations and their source and route versions; it does not create Python subclasses or determine whether an API change is backward compatible.

For the exact registration contract, including version-range behavior and collision resolution, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Python inheritance and DRF's built-in versioning

Python inheritance and routing inheritance solve separate problems.

Python inheritance is useful when two view implementations share behavior:

```python
class UserListV1(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


class UserListV2(UserListV1):
    serializer_class = UserSerializerV2
```

This reuses the queryset and inherited generic-view behavior. It does not register versioned URLs or decide which implementation handles a request.

DRF also provides built-in versioning schemes. In particular, `NamespaceVersioning` can mount the same URLconf under different version namespaces. A shared view can inspect `request.version` when its behavior needs to vary.

For example, define views that select the serializer according to the resolved namespace version:

```python
# api/views.py
from django.contrib.auth import get_user_model
from rest_framework.generics import ListAPIView

from .models import Post
from .serializers import (
    PostSerializer,
    UserSerializerV1,
    UserSerializerV2,
)

User = get_user_model()


class UserListDRF(ListAPIView):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.version == "v2":
            return UserSerializerV2
        return UserSerializerV1


class PostListViewDRF(ListAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
```

Configure the DRF versioning scheme:

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "rest_framework.versioning.NamespaceVersioning"
    ),
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1", "v2"],
}
```

Define the shared endpoint patterns once:

```python
# api/urls.py
from django.urls import path

from .views import PostListViewDRF, UserListDRF

app_name = "api"

urlpatterns = [
    path("users/", UserListDRF.as_view(), name="user-list"),
    path("posts/", PostListViewDRF.as_view(), name="post-list"),
]
```

Mount the same URLconf under both namespaces:

```python
# project/urls.py
from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("api.urls", namespace="v1")),
    path("api/v2/", include("api.urls", namespace="v2")),
]
```

The resulting paths are:

```text
/api/v1/users/ → UserListDRF
/api/v2/users/ → UserListDRF
/api/v1/posts/ → PostListViewDRF
/api/v2/posts/ → PostListViewDRF
```

The same URL patterns and view classes serve both versions. `UserListDRF` selects its serializer based on `request.version`, while `PostListViewDRF` uses the same behavior in both versions.

This is a valid DRF-only design. It is useful when a shared URLconf and version-dependent behavior within shared views fit the application's architecture.

The distinction is that this design does not automatically register separate view implementations at their starting versions. When an endpoint needs a different view class from a particular version onward, the application must represent that change through its own routing and view configuration.

See the [DRF versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/) for the available schemes and their behavior.

## Explicit per-version URLconfs

A project can also define separate URL patterns for each version and point unchanged endpoints to the same view class.

For an independent manual-routing example, define views without the package decorator:

```python
# api/manual_views.py
from django.contrib.auth import get_user_model
from rest_framework.generics import ListAPIView

from .models import Post
from .serializers import (
    PostSerializer,
    UserSerializerV1,
    UserSerializerV2,
)

User = get_user_model()


class UserListV1Manual(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


class UserListV2Manual(UserListV1Manual):
    serializer_class = UserSerializerV2


class PostListViewManual(ListAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
```

Register these views explicitly:

```python
# project/urls.py
from django.urls import include, path

from api.manual_views import (
    PostListViewManual,
    UserListV1Manual,
    UserListV2Manual,
)

urlpatterns = [
    path(
        "api/v1/",
        include([
            path(
                "users/",
                UserListV1Manual.as_view(),
                name="v1-user-list",
            ),
            path(
                "posts/",
                PostListViewManual.as_view(),
                name="v1-post-list",
            ),
        ]),
    ),
    path(
        "api/v2/",
        include([
            path(
                "users/",
                UserListV2Manual.as_view(),
                name="v2-user-list",
            ),
            path(
                "posts/",
                PostListViewManual.as_view(),
                name="v2-post-list",
            ),
        ]),
    ),
]
```

Here, the posts endpoint uses the same `PostListViewManual` in both versions, while the users endpoint uses a different view implementation in v2.

This explicit mapping is valid and makes each version's URL configuration visible. However, it repeats the `posts/` route declaration.

That distinction matters when comparing approaches: the duplication in this example comes from explicitly declaring each version's routes. It is not a requirement of every DRF-only versioning design, because shared URLconfs can also avoid repeated endpoint patterns.

`django-api-versioning` addresses this specific registration problem by carrying unchanged endpoint registrations forward automatically.

## Counting declarations and generated URL patterns

Consider an API with 10 endpoints and three supported versions:

- All 10 endpoints are registered in v1.
- Two endpoints receive new implementations in v2.
- No endpoints change in v3.

With explicit per-version URL declarations, each endpoint needs a route entry in every version:

```text
10 endpoints × 3 versions = 30 path() declarations
```

With `django-api-versioning`:

```text
10 declarations at version=1
 2 additional declarations at version=2
 0 additional declarations at version=3
----------------------------------------
12 endpoint declarations
```

The 12 declarations generate the same 30 versioned URL patterns.

The reduction is in the declarations developers maintain, not in the number of URLs exposed by the API.

This comparison is specifically against explicit per-version route declarations. It does not imply that every DRF-only design requires 30 separate `path()` entries; DRF's shared URLconf approach can also avoid that repetition.

## ViewSet and Router considerations

The examples above use DRF generic views such as `ListAPIView`.

The package does not accept `ModelViewSet` classes directly with `@endpoint`. The decorator calls `as_view()` without the action mapping required by a ViewSet.

For resource-oriented APIs built with `ModelViewSet`, use DRF routers and mount their generated URL patterns under the desired versioned prefixes.

Router-generated routes and decorator-registered endpoints can coexist in the same project URLconf, but they are separate registration mechanisms. The package does not automatically register or inherit ViewSet actions.

A manually configured callable such as:

```python
MyViewSet.as_view({"get": "list"})
```

can be registered with `@endpoint` for a specific route. It is not a replacement for normal router registration when the ViewSet needs its list, detail, and custom-action routes.

DRF's `@action` decorator is intended for ViewSets and relies on router-based action mapping. It does not provide the same mechanism for `GenericAPIView` subclasses. For additional generic-view endpoints, define separate view classes and register each at its starting version.

The [integration project's URLconf](https://github.com/mojtaba-arvin/django-api-versioning/blob/v0.3.4/integration_test_project/project/urls.py) demonstrates router-generated ViewSet URLs and decorator-registered endpoints coexisting in one project URLconf. Router URLs are mounted explicitly; they are not automatically registered by `@endpoint`.

This follows the package's canonical ViewSet and Router boundary described earlier.

## Trade-offs and scope

Python inheritance is useful whenever multiple view classes share implementation details. It works independently of the routing strategy.

DRF's built-in versioning schemes are sufficient when a shared URLconf and version-dependent view behavior fit the application's design. `NamespaceVersioning`, for example, can reuse the same endpoint patterns under multiple version namespaces.

`django-api-versioning` provides a different registration model: separate view implementations can become active from specific versions onward, while unchanged endpoint registrations automatically carry forward through the configured version range.

The declaration-count benefit depends on how often endpoints change.

| Scenario | Explicit per-version declarations | Package declarations |
| --- | ---: | ---: |
| 10 endpoints, 2 versions, 2 changed in v2 | 20 | 12 |
| 10 endpoints, 3 versions, 2 changed in v2 and none in v3 | 30 | 12 |
| 10 endpoints, 2 versions, all 10 changed in v2 | 20 | 20 |
| 10 endpoints, 3 versions, all 10 changed at both version boundaries | 30 | 30 |

The package provides the greatest reduction when most endpoints retain their implementation across version boundaries and only a smaller subset needs a new registration.

The trade-off is that a `version=N` registration continues through `API_MAX_VERSION` until a later registration replaces it. If an endpoint's contract changes but its registration is not updated, the earlier implementation will continue serving later versions.

Review the generated version matrix and test each supported version's behavior, including serializers, permissions, filtering, pagination, and schema output where relevant. Routing inheritance does not guarantee semantic API compatibility.

**When the benefit is smaller:** if nearly every endpoint changes at every version boundary, the number of package declarations approaches the number of explicit per-version route declarations. The package's value is then less about reducing declarations and more about expressing the starting version of each implementation consistently.

## Next steps

Disclosure: I maintain `django-api-versioning`, the package discussed in this article.

Explore the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning) to evaluate the registration model and integrate it into your versioned Django API.
