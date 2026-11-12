---
slug: "010-map-endpoint-different-views-per-api-version-django"
title: "Map a logical endpoint to different Django views per API version"
description: "Compare version-aware DRF views with separate per-version views using Django URLconf or django-api-versioning."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaaarvin/"
keywords:
  - "API versioning"
  - "endpoint routing"
  - "DRF"
  - "view dispatch"
  - "django-api-versioning"
---

# Map a logical endpoint to different Django views per API version

A `users` endpoint may need one implementation for v1 and another for v2. There are two fundamentally different routing designs:

- **Stable URL:** both versions use `/api/users/`, and Django REST Framework (DRF) selects the version from a query parameter or request header. A single view can branch on `request.version`.
- **Versioned URLs:** v1 uses `/api/v1/users/` and v2 uses `/api/v2/users/`. Each URL maps to its own view, so version-specific behavior can live in separate classes.

This article focuses first on versioned URLs and separate views, using `django-api-versioning` to generate the routes. It then compares that design with manual URLconf registration and DRF's built-in version negotiation for APIs that must preserve a stable URL.

The examples assume that `UserSerializerV1`, `UserSerializerV2`, and `UserSerializerV3` are already defined in `serializers.py`.

The v2 and v3 examples also assume that the project defines a `Profile` model with a reverse one-to-one relationship accessible through `user.profile`, containing `bio` and `verified` fields. They assume every user returned by those endpoints has an associated `Profile`. Without that guarantee, accessing `user.profile` raises `RelatedObjectDoesNotExist`; adapt the examples if your data model differs.

## Family A: different URLs, separate views

### Approach 1: Register separate views with django-api-versioning

When each API version has its own view, the routing task is to map each versioned URL to the appropriate view without repeating every registration.

`django-api-versioning` generates those URL patterns from endpoint declarations. Install it from [PyPI](https://pypi.org/project/django-api-versioning/).

Configure the supported version range:

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

The package uses integer version identifiers, such as `1` and `2`. The `version` argument identifies the first version for which an endpoint is registered.

Define one view per endpoint and version:

```python
# views.py

from django.contrib.auth import get_user_model
from django_api_versioning import endpoint
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from .serializers import UserSerializerV1, UserSerializerV2

User = get_user_model()


@endpoint("users/", version=1)
class UserListViewV1(ListAPIView):
    serializer_class = UserSerializerV1

    def get_queryset(self):
        return User.objects.filter(is_active=True)


@endpoint("users/<int:pk>/", version=1)
class UserDetailViewV1(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/", version=2)
class UserListViewV2(ListAPIView):
    serializer_class = UserSerializerV2

    def get_queryset(self):
        return User.objects.all().select_related("profile")


@endpoint("users/<int:pk>/", version=2)
class UserDetailViewV2(RetrieveAPIView):
    queryset = User.objects.select_related("profile")
    serializer_class = UserSerializerV2

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        data = self.get_serializer(user).data
        data["profile"] = {
            "bio": user.profile.bio,
            "verified": user.profile.verified,
        }
        return Response(data)
```

The first argument to `endpoint()` is the URL postfix. The package combines it with `API_BASE_PATH`, whose default is `"api/v{version}/"`, to generate the versioned URL.

Import the module containing the declarations before importing the package's URL patterns:

```python
# urls.py

from django.urls import include, path

from . import views  # noqa: F401 — import first so decorators register
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The import order matters. The `@endpoint` decorator registers routes when the module containing the declaration is imported. The package does not automatically discover application view modules. If endpoint declarations are spread across multiple modules, import each of those modules before importing `api_urlpatterns`.

With `API_MAX_VERSION = 2` and the default `API_BASE_PATH = "api/v{version}/"`, the declarations produce these routes:

| Endpoint declaration | v1 route | v2 route |
| --- | --- | --- |
| `users/`, `version=1` | `UserListViewV1` | Replaced by `UserListViewV2` |
| `users/<int:pk>/`, `version=1` | `UserDetailViewV1` | Replaced by `UserDetailViewV2` |

The final URL-to-view mapping is:

| URL | View |
| --- | --- |
| `/api/v1/users/` | `UserListViewV1` |
| `/api/v1/users/<int:pk>/` | `UserDetailViewV1` |
| `/api/v2/users/` | `UserListViewV2` |
| `/api/v2/users/<int:pk>/` | `UserDetailViewV2` |

**Now:**

- Requests to `/api/v1/users/` use `UserListViewV1`.
- Requests to `/api/v2/users/` use `UserListViewV2`.
- Requests to `/api/v1/users/42/` use `UserDetailViewV1`.
- Requests to `/api/v2/users/42/` use `UserDetailViewV2`.

Four endpoint declarations produce four final versioned URL patterns. Each version has its own view, serializer, and query behavior.

#### How registration inheritance works

A declaration with `version=N` registers the endpoint from version N through `API_MAX_VERSION`, inclusive.

For a given route and target version, collision precedence follows the registration rules:

- If both declarations have integer `source_version` values, the higher source version wins.
- If their source versions are equal, the most recently registered declaration wins.
- If either source version is `None`, the most recently registered declaration wins.

This is registration-time route expansion, not request-time fallback traversal.

For example, if the v2 declaration for `users/` is removed, the v1 declaration still covers v2:

| Declaration | v1 | v2 |
| --- | --- | --- |
| `@endpoint("users/", version=1)` | `UserListViewV1` | `UserListViewV1` |

You can therefore release v2 without making any code changes to an unchanged endpoint. Its v1 registration already covers v2.

If a v2 declaration is added later, it replaces the v1 registration for that route in v2. The v1 route remains unchanged.

A version outside the configured range is different from a version that has no separate endpoint declaration. With `API_MAX_VERSION = 2`, the package does not generate a v3 route. A request to `/api/v3/users/` therefore does not match a generated URL pattern and normally results in Django returning 404. Within the configured range, an endpoint can be carried forward from a lower source version.

For the exact decorator signature, version-range behavior, import requirements, and routing rules, see the [versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/v0.3.4/docs/reference/versioning-contract.md).

### Adding v3

Suppose you want to introduce v3.

If neither endpoint needs a new implementation, increase the maximum version:

```python
# settings.py

API_MAX_VERSION = 3
```

The existing v1 and v2 registrations extend through v3. Since the v2 declarations have higher source versions, they handle v3.

If both endpoints need new v3 implementations, add two declarations:

```python
# views.py

from .serializers import UserSerializerV3


@endpoint("users/", version=3)
class UserListViewV3(ListAPIView):
    serializer_class = UserSerializerV3

    def get_queryset(self):
        return User.objects.all().select_related("profile")


@endpoint("users/<int:pk>/", version=3)
class UserDetailViewV3(RetrieveAPIView):
    queryset = User.objects.select_related("profile")
    serializer_class = UserSerializerV3
```

If only one endpoint changes in v3, add a declaration only for that endpoint. The unchanged endpoint continues using the v2 registration.

In all three cases, the URLconf remains unchanged.

### Approach 2: Manual URLconf with separate views

The same URL-to-view mapping can be written directly with Django's `path()` function. This approach makes every registration explicit:

```python
# views.py

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import UserSerializerV1, UserSerializerV2

User = get_user_model()


@api_view(["GET"])
def user_list_v1(request):
    users = User.objects.filter(is_active=True)
    return Response(UserSerializerV1(users, many=True).data)


@api_view(["GET"])
def user_list_v2(request):
    users = User.objects.all().select_related("profile")
    return Response(UserSerializerV2(users, many=True).data)


@api_view(["GET"])
def user_detail_v1(request, pk):
    user = get_object_or_404(User, pk=pk)
    return Response(UserSerializerV1(user).data)


@api_view(["GET"])
def user_detail_v2(request, pk):
    user = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    data = UserSerializerV2(user).data
    data["profile"] = {
        "bio": user.profile.bio,
        "verified": user.profile.verified,
    }
    return Response(data)
```

Register the views explicitly:

```python
# urls.py

from django.urls import path

from .views import (
    user_detail_v1,
    user_detail_v2,
    user_list_v1,
    user_list_v2,
)

urlpatterns = [
    path("api/v1/users/", user_list_v1),
    path("api/v1/users/<int:pk>/", user_detail_v1),
    path("api/v2/users/", user_list_v2),
    path("api/v2/users/<int:pk>/", user_detail_v2),
]
```

This creates the same four URL-to-view mappings as the package example. The difference is how those mappings are declared: here, each `path()` entry is written manually.

Manual registration is reasonable when the route set is small, every mapping is intentionally explicit, and there is no need for version-range carry-forward or higher-version replacement. When those registration rules are useful, `django-api-versioning` expresses them through endpoint declarations instead of requiring a separate URL pattern for every version.

## Family B: same URL, version-aware view

The previous approaches use version-specific URL paths. That is not always possible or desirable. If clients already depend on `/api/users/`, changing the URL to `/api/v1/users/` may break those clients.

DRF provides built-in versioning classes that keep the URL stable and expose the selected version through `request.version`.

The examples in this section use string identifiers such as `"v1"` and `"v2"`. These are DRF version values, not the integer identifiers used by `django-api-versioning`. They are separate versioning configurations and should not be mixed in the same setting or decorator declaration.

See the official [DRF versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/) for the supported schemes and their configuration.

### Query parameter

DRF's `QueryParameterVersioning` reads the version from a query parameter. The default parameter name is `version`.

Configure it in `settings.py`:

```python
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "rest_framework.versioning.QueryParameterVersioning"
    ),
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ("v1", "v2"),
}
```

The view branches on the selected version:

```python
# views.py

from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import UserSerializerV1, UserSerializerV2

User = get_user_model()


@api_view(["GET"])
def user_list(request):
    if request.version == "v1":
        serializer_class = UserSerializerV1
    else:
        serializer_class = UserSerializerV2

    users = User.objects.all()
    return Response(serializer_class(users, many=True).data)
```

Register one URL:

```python
# urls.py

from django.urls import path

from .views import user_list

urlpatterns = [
    path("api/users/", user_list),
]
```

Clients select the version through the query parameter:

```text
GET /api/users/?version=v1
GET /api/users/?version=v2
```

Both requests use the same URL path and the same view function. DRF makes the selected version available as `request.version`. If the client omits the parameter, the configured `DEFAULT_VERSION` (`"v1"`) is used.

If a client requests a version outside `ALLOWED_VERSIONS`, `QueryParameterVersioning` rejects the request with a 404 response rather than silently selecting another serializer.

### Accept header

DRF's `AcceptHeaderVersioning` reads the version from the `Accept` header's version parameter.

Change the versioning class in `settings.py`:

```python
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "rest_framework.versioning.AcceptHeaderVersioning"
    ),
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ("v1", "v2"),
}
```

The view and URLconf are the same as in the query-parameter example. Clients select the version through the request header:

```http
Accept: application/json; version=v1
```

or:

```http
Accept: application/json; version=v2
```

The URL remains `/api/users/` for both versions.

If the header specifies a version outside `ALLOWED_VERSIONS`, `AcceptHeaderVersioning` rejects the request with a 406 Not Acceptable response.

**When this fits:** The URL is a stable resource identifier and clients can set request headers. The version is not visible in the URL, which may keep URLs cleaner but can make manual inspection less convenient.

Both query-parameter and header-based versioning expose the selected version through `request.version`. Neither scheme requires the application to put all version-specific behavior in one view; separate view dispatch can still be implemented if the application needs it. The distinction is how the request communicates its version, not whether the application can separate its implementations.

## ViewSet and Router considerations

The examples using `@endpoint` rely on DRF generic views such as `ListAPIView` and `RetrieveAPIView`. These are supported by the package.

`ModelViewSet` is different. A ViewSet needs an action mapping to turn it into a callable view. Decorating the ViewSet class directly with `@endpoint` does not work because the decorator calls `.as_view()` without that mapping.

For resource-shaped endpoints, use DRF routers and register a router for each API version. This is the standard approach for ViewSets and is independent of the package's generic-view routing.

A configured callable such as `UserViewSetV1.as_view({"get": "list"})` can be registered with `@endpoint` for one explicitly configured route. It is not a replacement for normal router registration when exposing a full resource.

This follows the package's canonical ViewSet/Router position: use routers for resource-shaped ViewSets and `@endpoint` for supported generic views and explicitly configured callables. The [DRF router documentation](https://www.django-rest-framework.org/api-guide/routers/) explains the router registration model.

The [integration project's URLconf](https://github.com/mojtaba-arvin/django-api-versioning/blob/v0.3.4/integration_test_project/project/urls.py) demonstrates router-based and decorator-based routing in the same project.

## Trade-offs and scope

The approaches above solve two different routing problems:

| Approach | URL structure | Version selection | View structure |
| --- | --- | --- | --- |
| Query parameter | Stable | Query parameter | Version-aware view |
| Accept header | Stable | Request header | Version-aware view |
| Manual URLconf | Versioned | URL path | Separate views |
| `django-api-versioning` | Versioned | URL path | Separate views with generated routes |

**Same URL, version-aware view:** Useful when clients already depend on a stable URL. DRF handles request-version negotiation and exposes the selected version through `request.version`. The application remains responsible for deciding how to organize version-specific behavior.

**Different URL, separate views:** Useful when version-specific URLs are part of the API contract and each version has meaningfully different behavior. Separate views make those differences explicit. Manual URLconf registration requires an explicit mapping for each route and version. The package adds registration-time carry-forward and higher-version replacement, reducing that repeated URL configuration.

**Scope: routing only.** `django-api-versioning` generates versioned URL patterns and resolves them to registered views. It does not perform DRF request-version negotiation, select serializers based on headers, or guarantee semantic compatibility between API versions.

When the benefit is smaller: if two versions differ only in a serializer field, a single version-aware view using DRF's built-in versioning may be shorter than separate view classes. For endpoints with substantial version-specific behavior, separate views provide a clearer boundary, while the package handles the versioned route registrations.

Disclosure: I maintain django-api-versioning, the package discussed in this article.

## Next steps

If your API uses separate views for versioned URLs, evaluate whether registration-time carry-forward and higher-version replacement can simplify your URL configuration. Start with the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
