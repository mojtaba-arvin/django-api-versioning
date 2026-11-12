---
slug: "004-api-routing-library"
title: "API routing libraries: declarative versioning and automatic inheritance"
description: "Explore declarative endpoint registration, forward route inheritance, and how routing libraries reduce repetitive URL configuration in multi-version Django REST Framework APIs."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "Django API versioning"
  - "DRF API versioning"
  - "declarative API registration"
  - "endpoint registration"
  - "API routing patterns"
  - "forward route inheritance"
---

# API routing libraries: declarative versioning and automatic inheritance

API versioning introduces a routing problem that grows with the number of endpoints and versions.

When an API evolves, some endpoints change while others remain compatible with newer versions. The routing configuration must represent both cases: endpoints with a new implementation and endpoints that can continue using an existing implementation.

Django and Django REST Framework provide the building blocks for versioned APIs. However, maintaining every versioned route explicitly can become repetitive, especially when most endpoints remain unchanged between releases.

A routing library can move that responsibility out of the project's URL configuration. Instead of declaring every route for every version, developers declare where an endpoint implementation becomes active. The library generates the corresponding URL patterns and carries that implementation forward until another declaration takes precedence.

This article explores that design through `django-api-versioning`, including its routing model, Python inheritance, trade-offs, and the situations where declarative registration provides value.

**Package version:** `0.3.5`  
**Technical assessment date:** `2026-11-12`

The examples target Django REST Framework class-based views and use path-based versioning.

## The routing library abstraction

A declarative routing library can encode a specific architectural rule:

**A registration at version N remains active for subsequent versions until another registration takes precedence.**

The library applies this rule during endpoint registration. Each declaration generates concrete URL patterns from its source version through `API_MAX_VERSION`.

When another declaration targets the same route at a higher source version, it replaces the existing registration for the affected versions.

This pattern is expressed declaratively. You register each endpoint implementation at the version where it becomes active. The library generates the versioned URLs from those registrations.

Throughout the examples, the application uses Django's default `django.contrib.auth.models.User` model. If your project uses a custom user model, the model class and its fields will differ, but the registration and inheritance pattern remains the same.

```python
# settings.py

INSTALLED_APPS = [
    # ...
    "django_api_versioning",
]

API_MIN_VERSION = 1
API_MAX_VERSION = 3
```

The package's default URL template is:

```python
API_BASE_PATH = "api/v{version}/"
```

The examples below use that default.

### Registering endpoint implementations

The package exposes `endpoint` from its public top-level namespace:

```python
from django_api_versioning import endpoint
```

First, define serializers for the initial and subsequent API versions:

```python
# serializers.py

from django.contrib.auth.models import User
from rest_framework import serializers


class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "date_joined"]
```

Now register the endpoint implementations:

```python
# views.py

from django.contrib.auth.models import User
from django_api_versioning import endpoint
from rest_framework.generics import ListCreateAPIView

from .serializers import UserSerializerV1, UserSerializerV2


# v1: the base implementation, active from v1 onward.
@endpoint("users/", version=1)
class UserListView(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


# v2: changes the serializer, active from v2 onward.
@endpoint("users/", version=2)
class UserListViewV2(UserListView):
    serializer_class = UserSerializerV2
```

The `version=1` declaration registers the implementation for v1, v2, and v3. The v2 declaration takes precedence for v2 and v3.

The resulting routing is:

| URL | Registered view |
| --- | --- |
| `/api/v1/users/` | `UserListView` |
| `/api/v2/users/` | `UserListViewV2` |
| `/api/v3/users/` | `UserListViewV2` |

The v3 route does not need another declaration. It continues using the v2 implementation because the v2 registration extends through `API_MAX_VERSION`.

This is forward route inheritance: a declaration for a version also covers subsequent configured versions until another declaration takes precedence.

It is a routing behavior, not Python class inheritance. The two concepts can be used together, but they solve different problems.

### Connecting generated routes to Django

The modules containing decorated views must be imported before the package's generated URL patterns are imported.

For example:

```python
# urls.py

from django.urls import include, path

from . import views  # noqa: F401 — import first so decorators register

from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The `views` import executes the decorators and populates the registry. Importing `api_urlpatterns` before the endpoint declarations risks capturing an empty or incomplete pattern list.

Key point: you declare endpoint versions, not individual URLs. The library generates the URL patterns from those declarations.

### Python inheritance and routing inheritance

The previous example uses two different forms of inheritance.

Python inheritance allows a new view class to reuse or extend the behavior of an existing class:

```python
class UserListViewV2(UserListView):
    serializer_class = UserSerializerV2
```

The decorator determines which API versions are registered to use that class:

```python
@endpoint("users/", version=2)
class UserListViewV2(UserListView):
    serializer_class = UserSerializerV2
```

The Python class hierarchy determines the methods and attributes available to `UserListViewV2`.

The decorator determines the versions for which the view is registered.

Neither mechanism guarantees that the resulting API contract is backward-compatible. That remains an application-level responsibility.

For example, if a v2 serializer changes the response structure, the v3 route will also use that serializer unless a separate v3 declaration replaces it.

## What the library generates

For the registrations above, with `API_MAX_VERSION = 3`, the generated routes dispatch as follows:

```text
GET  /api/v1/users/  -> UserListView.get()
POST /api/v1/users/  -> UserListView.post()

GET  /api/v2/users/  -> UserListViewV2.get()
POST /api/v2/users/  -> UserListViewV2.post()

GET  /api/v3/users/  -> UserListViewV2.get()
POST /api/v3/users/  -> UserListViewV2.post()
```

The v3 requests are routed to `UserListViewV2` because no v3 registration exists and the v2 registration extends through `API_MAX_VERSION`.

`UserListViewV2.get()` is inherited from `UserListView` through Python class inheritance. The routing library does not need to know about individual methods to make this work.

### Introducing a v3-specific change

Suppose v3 introduces an additional validation rule for user creation.

The v3 implementation can inherit the existing behavior and override only the method that needs to change:

```python
from rest_framework.exceptions import ValidationError

from django_api_versioning import endpoint


@endpoint("users/", version=3)
class UserListViewV3(UserListViewV2):
    def post(self, request, *args, **kwargs):
        email = request.data.get("email") or ""

        if email and not email.endswith("@example.com"):
            raise ValidationError(
                {"email": "Must use an @example.com email."}
            )

        return super().post(request, *args, **kwargs)
```

This is a simplified domain restriction, not full email validation. It also affects POST only; GET continues to use the inherited implementation.

The routing table now becomes:

```text
GET  /api/v1/users/  -> UserListView.get()
POST /api/v1/users/  -> UserListView.post()

GET  /api/v2/users/  -> UserListViewV2.get()
POST /api/v2/users/  -> UserListViewV2.post()

GET  /api/v3/users/  -> UserListViewV3.get()
POST /api/v3/users/  -> UserListViewV3.post()
```

`UserListViewV3.get()` is inherited from `UserListViewV2`, which inherits it from `UserListView`.

The `post()` method is overridden in `UserListViewV3`. It adds domain validation before delegating to the inherited implementation.

The change affects only POST requests to v3. GET requests to v3 continue to behave as in v2.

No additional URLconf entries are required.

The three URL paths are generated from the endpoint declarations.

## Design patterns in routing libraries

### 1. Declarative registration versus imperative URLconf

A conventional Django URL configuration explicitly maps paths to views:

```python
from django.urls import path

urlpatterns = [
    path("api/v1/users/", UserListViewV1.as_view(), name="v1-users"),
    path("api/v2/users/", UserListViewV2.as_view(), name="v2-users"),
    path("api/v3/users/", UserListViewV3.as_view(), name="v3-users"),
]
```

A declarative routing library expresses the registration intent instead:

```python
@endpoint("users/", version=1)
class UserListView(ListCreateAPIView):
    ...


@endpoint("users/", version=2)
class UserListViewV2(UserListView):
    ...


@endpoint("users/", version=3)
class UserListViewV3(UserListViewV2):
    ...
```

Declarative registration separates what you are versioning—the endpoint and its version range—from how Django routes requests through generated URL patterns.

Django also allows URL patterns and view callables to be reused through shared modules and `include()`. A routing library is therefore not the only way to avoid duplicating URL configuration.

Its specific contribution is the registration and forward-inheritance rule.

### 2. Inheritance by default

The package implements a routing-level rule: a registration at version N is active from N onward until a higher-source-version registration takes precedence for the same route.

Consider a reporting endpoint:

```python
# models.py

from django.db import models


class Post(models.Model):
    title = models.CharField(max_length=200)
    published = models.BooleanField(default=False)
```

```python
# serializers.py

from rest_framework import serializers

from .models import Post


class PostSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["id", "title"]
```

```python
# views.py

from django_api_versioning import endpoint
from rest_framework.generics import ListCreateAPIView

from .models import Post
from .serializers import PostSerializerV1


@endpoint("posts/", version=1)
class PostListView(ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializerV1


# No v2 declaration is needed.
# The v1 registration remains active for v2.


# v3 changes the queryset, but keeps the existing serializer.
@endpoint("posts/", version=3)
class PostListViewV3(PostListView):
    def get_queryset(self):
        return Post.objects.filter(published=True)
```

The resulting routing is:

| URL | Registered view |
| --- | --- |
| `/api/v1/posts/` | `PostListView` |
| `/api/v2/posts/` | `PostListView` |
| `/api/v3/posts/` | `PostListViewV3` |

The v1 implementation remains active for v2 because no v2 or higher-priority declaration replaces it before v3.

### 3. Automatic URL generation

The library derives versioned routes from `API_BASE_PATH` and the endpoint postfix.

For example:

```python
@endpoint("users/", version=1)
class UserListView(ListCreateAPIView):
    ...
```

With `API_MAX_VERSION = 3` and the default `API_BASE_PATH = "api/v{version}/"`, this produces:

- `/api/v1/users/`
- `/api/v2/users/`
- `/api/v3/users/`

The Python class name does not determine the URL path. The path comes from the configured base path, optional `app_name`, and endpoint postfix.

### 4. Explicit version registration

Not every endpoint should necessarily carry forward to every subsequent version.

The package supports explicit version lists:

```python
@endpoint("ranking/", versions=[1, 3])
class RankingView(APIView):
    ...
```

This registers the endpoint for v1 and v3, but not v2.

For an inclusive range, the package also provides `ver_range()`:

```python
from django_api_versioning import endpoint, ver_range


@endpoint("legacy/", versions=ver_range(1, 3))
def legacy(request):
    ...
```

Use segment registration when an implementation should remain active for subsequent versions. Use explicit registration when the endpoint should exist only in selected versions.

## Real-world example: evolving an API

Consider an API that evolves from v1 to v3.

- v1 exposes a minimal user representation.
- v2 adds email and filters the queryset to active users.
- v3 adds more fields and pagination.

The serializers are:

```python
# users/serializers.py

from django.contrib.auth.models import User
from rest_framework import serializers


class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class UserSerializerV3(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_active",
            "date_joined",
        ]
```

The endpoint implementations are:

```python
# users/views.py

from django.contrib.auth.models import User
from django_api_versioning import endpoint
from rest_framework.generics import ListCreateAPIView
from rest_framework.pagination import PageNumberPagination

from .serializers import (
    UserSerializerV1,
    UserSerializerV2,
    UserSerializerV3,
)


class UserPagination(PageNumberPagination):
    page_size = 20


@endpoint("users/", version=1)
class UserListView(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/", version=2)
class UserListViewV2(UserListView):
    serializer_class = UserSerializerV2

    def get_queryset(self):
        return User.objects.filter(is_active=True)


@endpoint("users/", version=3)
class UserListViewV3(UserListViewV2):
    serializer_class = UserSerializerV3
    pagination_class = UserPagination
```

The URL configuration imports the views before the generated patterns:

```python
# urls.py

from django.urls import include, path

from . import views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The resulting behavior is:

- `/api/v1/users/` -> `UserListView`: all users, minimal fields, no pagination.
- `/api/v2/users/` -> `UserListViewV2`: active users only, includes email, no pagination.
- `/api/v3/users/` -> `UserListViewV3`: active users only, expanded fields, paginated with a page size of 20.

Each implementation builds on the previous one through Python inheritance. Routing inheritance separately maps each version to the latest applicable endpoint registration.

The library generates concrete URL patterns during registration. It does not perform backward lookup for every incoming request.

Important: This example demonstrates routing and view reuse, not a guarantee that the v3 response is compatible with v2. The application must test each version's expected contract.

## Comparison: manual routing versus a routing library

Consider an API with:

- 20 endpoints.
- 4 supported versions.
- 3 endpoint registrations changed at each version boundary: v2, v3, and v4.

That gives 9 override registrations across the three version boundaries.

### Fully explicit per-version URLconf

If every endpoint is declared separately in every version:

- 20 endpoints × 4 versions = 80 URLconf entries.

This is one possible Django design, not a requirement. Django can reuse the same view callable across multiple paths, and shared URL configurations can reduce repetition.

### Declarative endpoint registration

With forward route inheritance:

- 20 declarations at version 1.
- 3 declarations at version 2.
- 3 declarations at version 3.
- 3 declarations at version 4.

Total:

- 20 + 3 + 3 + 3 = 29 declarations.

| Approach | Declarations |
| --- | ---: |
| Fully explicit per-version URLconf | 80 |
| Initial registrations plus changed endpoint overrides | 29 |
| Difference in this scenario | 51 fewer declarations |

The comparison counts route declarations, not view implementations. It assumes a fully explicit per-version URLconf, where every endpoint path is written for every version.

The reduction depends on how the API evolves:

- If no endpoints change, the library needs only the 20 initial declarations.
- If 3 endpoints change at each version boundary, it needs 29 declarations.
- If every endpoint changes at every boundary, it needs 80 declarations—the same count as the fully explicit approach.

The library's advantage comes from describing changes rather than repeating unchanged mappings.

## Trade-offs and scope

The table uses the same illustrative scenario: 20 endpoints, 4 versions, and 3 endpoint changes at each version boundary.

| Aspect | Fully explicit URLconf | Declarative routing |
| --- | --- | --- |
| Where routes are defined | Explicit path declarations | Endpoint declarations |
| Unchanged endpoints | Mapped in each version in this scenario | Carried forward automatically |
| Version-specific changes | Added as explicit route mappings | Added as endpoint registrations |
| Routing visibility | Centralized in URL configuration | Distributed across decorated views |
| Declaration count in the example | 80 | 29 |
| Learning curve | Standard Django URL configuration | Package registration and precedence rules |
| Fine-grained control | Full Django URL configuration API | Follows the package's registration model |

### When the benefit is smaller

Manual URL configuration may be preferable when:

- The API has few endpoints and versions.
- Most endpoints have substantially different behavior in every version.
- Routing depends on complex URL composition or custom resolution rules.
- The team prefers Django's built-in URL configuration without an additional dependency.

Declarative registration becomes more valuable when many endpoints remain unchanged across versions and the team wants to keep version-specific routing declarations close to their view implementations.

The deciding factor is not a fixed number of API versions. It is how frequently endpoint routing changes relative to the number of endpoints that remain stable.

### Compatibility and carry-forward risks

Forward route inheritance reduces repeated routing declarations, but it does not establish semantic API compatibility.

When a new API version is introduced, teams should verify the version matrix for:

- Request and response serializers.
- Permissions and authentication behavior.
- Queryset filtering and object visibility.
- Pagination and filtering rules.
- Error response formats.
- Schema generation and API documentation.
- Any behavior that clients depend on.

A view declared at v2 may continue serving v3 automatically. If the v3 contract must differ, register a v3 implementation explicitly.

For endpoints that should exist only in selected versions, use `versions=[...]` rather than relying on a continuous version segment.

The package handles route registration. Application teams remain responsible for defining and testing API contracts.

### Scope: routing only

The package's responsibility is versioned URL registration.

It does not replace DRF's request-version identification mechanisms, automatically make API contracts compatible, or generate a separate schema for every API version.

DRF ViewSet classes are also not directly supported by `@endpoint`. A ViewSet's `as_view()` method requires an action mapping that the decorator does not supply.

Use DRF's `DefaultRouter` or `SimpleRouter` to register ViewSets and mount their generated URLs separately under the desired versioned prefixes. This router setup is separate from the package's endpoint registry; it is not automatic router integration.

For the precise behavior of endpoint declarations, collision precedence, version ranges, and supported view types, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Getting started with django-api-versioning

The package is available on [PyPI](https://pypi.org/project/django-api-versioning/).

The repository contains the integration example and implementation:

- [Integration project's URL configuration](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/integration_test_project/project/urls.py)
- [Endpoint decorator implementation](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/decorators.py)

I maintain this package, and the examples in this article describe its routing model and implementation.

If your API has many endpoints that evolve incrementally, declarative registration can make the routing layer reflect those changes with fewer repeated declarations.

Explore the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning) to review the implementation and decide whether its routing model fits your API.
