---
slug: "009-declarative-registration-versioned-endpoints-django"
title: "Declarative registration of versioned endpoints in Django"
description: "Compare DRF router configuration with decorator-based endpoint registration in Django, including version ranges, explicit versions, and ViewSet limitations."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "API versioning"
  - "declarative"
  - "Django REST Framework"
  - "endpoint registration"
  - "URL routing"
---

# Declarative registration of versioned endpoints in Django

In a versioned Django API, endpoint definitions and URL configuration can be maintained separately or declared together. The difference becomes important as an API evolves: unchanged endpoints should remain available in later versions, while changed endpoints need an explicit replacement.

For DRF projects built around `ModelViewSet`, per-version routers are a natural way to organize resource routes. For class-based views such as `ListAPIView` and `RetrieveUpdateDestroyAPIView`, [`django-api-versioning` on PyPI](https://pypi.org/project/django-api-versioning/) provides decorator-based registration: the version and endpoint path are declared alongside the view.

This article compares three approaches:

1. Imperative URLconf: connect views and paths with `path()`.
2. Manual declarative configuration: store endpoint definitions in a dictionary or dataclass and build routers from that configuration.
3. Decorator-based registration: declare the endpoint version on the view with `@endpoint`.

The focus is route registration, not DRF request-version negotiation or semantic API compatibility.

## Decorator-based registration with `@endpoint`

The package lets you declare the route and its starting version where the view is defined.

Configure the supported version range:

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

Define the views:

```python
# views.py

from django.contrib.auth import get_user_model
from django_api_versioning import endpoint
from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateDestroyAPIView,
)

from .serializers import UserSerializerV1, UserSerializerV2

User = get_user_model()


@endpoint("users/", version=1)
class UserListView(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/<int:pk>/", version=1)
class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


# Only the list endpoint changes in v2.
@endpoint("users/", version=2)
class UserListViewV2(UserListView):
    serializer_class = UserSerializerV2
```

The serializers are assumed to be defined in `serializers.py`. The example uses the default Django user model; adapt the queryset and serializers if the project uses a custom user model.

Import the module containing the decorated views before importing the package's URL patterns:

```python
# urls.py

from django.urls import include, path

from . import views  # noqa: F401 — import first to execute decorators

from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The import order matters. The `@endpoint` decorator registers routes when the module containing the view is imported. The package does not automatically discover application view modules.

With `API_MAX_VERSION = 2` and the default `API_BASE_PATH = "api/v{version}/"`, the declarations produce:

| URL | Registered view |
|---|---|
| `/api/v1/users/` | `UserListView` |
| `/api/v2/users/` | `UserListViewV2` |
| `/api/v1/users/<int:pk>/` | `UserDetailView` |
| `/api/v2/users/<int:pk>/` | `UserDetailView` |

There are three endpoint declarations and four generated URL patterns.

The v1 detail registration remains active in v2 because `version=1` registers the view from v1 through `API_MAX_VERSION`. The v2 list declaration replaces the earlier list registration for v2.

You can therefore release v2 without changing the detail view or adding a second detail declaration.

Now:

- Requests to `/api/v1/users/` resolve to `UserListView`.
- Requests to `/api/v2/users/` resolve to `UserListViewV2`.
- Requests to either version of the detail route resolve to `UserDetailView`.

This is registration-time route inheritance. It does not create a Python subclass, copy methods, merge serializers, or establish that the API contracts are backward compatible.

For the exact version-range, collision, and URL construction rules, see the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Manual declarative registration with a configuration dictionary

A DRF-only alternative is to keep version-specific ViewSet classes in a configuration dictionary and build one router for each version.

This approach makes the configuration explicit, but the builder must register every endpoint in every version where it should be available.

Use integer version identifiers in the configuration and add the `v` prefix when constructing the URL:

```python
# config.py

VERSIONED_ENDPOINTS = {
    "users": {
        "viewsets": {
            1: "myapp.views.UserViewSetV1",
            2: "myapp.views.UserViewSetV2",
        },
        "basename": "users",
    },
    "posts": {
        "viewsets": {
            1: "myapp.views.PostViewSetV1",
            2: "myapp.views.PostViewSetV2",
        },
        "basename": "posts",
    },
}
```

Build the versioned routers:

```python
# urls.py

from django.urls import include, path
from django.utils.module_loading import import_string
from rest_framework.routers import SimpleRouter

from .config import VERSIONED_ENDPOINTS


def build_versioned_urls():
    urlpatterns = []

    versions = sorted({
        version
        for endpoint_config in VERSIONED_ENDPOINTS.values()
        for version in endpoint_config["viewsets"]
    })

    for version in versions:
        router = SimpleRouter()

        for endpoint_name, endpoint_config in VERSIONED_ENDPOINTS.items():
            viewset_path = endpoint_config["viewsets"].get(version)

            if viewset_path is None:
                continue

            viewset_class = import_string(viewset_path)

            router.register(
                endpoint_name,
                viewset_class,
                basename=f"v{version}-{endpoint_config['basename']}",
            )

        urlpatterns.append(
            path(f"api/v{version}/", include(router.urls))
        )

    return urlpatterns


urlpatterns = build_versioned_urls()
```

The version-specific basenames generate distinct URL names. For example:

- `v1-users-list`
- `v2-users-list`

This allows calls such as `reverse("v1-users-list")` and `reverse("v2-users-list")` to refer to different routes.

The version list is derived from the configuration, so adding a version does not require editing a separate hard-coded version list. However, each endpoint still needs an explicit entry for every version in which it should be available.

For example, if the users endpoint remains unchanged in v2, its v2 configuration must still point to `UserViewSetV1`:

```python
"users": {
    "viewsets": {
        1: "myapp.views.UserViewSetV1",
        2: "myapp.views.UserViewSetV1",
    },
    "basename": "users",
}
```

There is no automatic carry-forward rule in this builder. If an endpoint has no v2 entry, no v2 route is generated for it.

The string-based configuration also has a cost: a typo in an import path is discovered when `import_string()` executes during URL configuration construction. The string itself does not provide a class reference that an IDE can navigate to or statically validate.

## Manual declarative registration with dataclasses

A dataclass can replace import strings with direct class references and validate that each configured class is a DRF ViewSet class.

```python
# config.py

from dataclasses import dataclass
from typing import Dict, Type

from rest_framework import viewsets

from .views import (
    UserViewSetV1,
    UserViewSetV2,
    PostViewSetV1,
    PostViewSetV2,
)


@dataclass
class VersionedEndpointConfig:
    prefix: str
    versions: Dict[int, Type[viewsets.ViewSetMixin]]
    basename: str

    def __post_init__(self):
        if not all(
            isinstance(viewset_class, type)
            and issubclass(viewset_class, viewsets.ViewSetMixin)
            for viewset_class in self.versions.values()
        ):
            raise TypeError("All versions must be DRF ViewSet classes")


ENDPOINTS = [
    VersionedEndpointConfig(
        prefix="users",
        versions={
            1: UserViewSetV1,
            2: UserViewSetV2,
        },
        basename="users",
    ),
    VersionedEndpointConfig(
        prefix="posts",
        versions={
            1: PostViewSetV1,
            2: PostViewSetV2,
        },
        basename="posts",
    ),
]
```

`ViewSetMixin` is the common base used by DRF ViewSet variants, including `ViewSet`, `GenericViewSet`, and `ModelViewSet`. Checking against `viewsets.ViewSet` alone would exclude classes such as `ModelViewSet`.

The `__post_init__` check is runtime validation. It does not replace static type checking, and the type annotation alone does not enforce the contents of the dictionary.

The URL builder is similar to the dictionary version:

```python
# urls.py

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .config import ENDPOINTS


def build_versioned_urls():
    urlpatterns = []

    versions = sorted({
        version
        for endpoint_config in ENDPOINTS
        for version in endpoint_config.versions
    })

    for version in versions:
        router = SimpleRouter()

        for endpoint_config in ENDPOINTS:
            viewset_class = endpoint_config.versions.get(version)

            if viewset_class is None:
                continue

            router.register(
                endpoint_config.prefix,
                viewset_class,
                basename=f"v{version}-{endpoint_config.basename}",
            )

        urlpatterns.append(
            path(f"api/v{version}/", include(router.urls))
        )

    return urlpatterns


urlpatterns = build_versioned_urls()
```

This version provides direct class references and a runtime check for ViewSet compatibility. It still requires the application to maintain the builder, discover versions, iterate over endpoints, and explicitly register unchanged ViewSets in each version.

The two manual approaches are useful when the configuration itself carries information that does not naturally belong on a view declaration. Otherwise, the builder introduces another layer of routing code to maintain.

## Explicit version registration with `versions=[...]`

The package also supports endpoints that should exist only in selected versions.

The following example assumes a separate project configuration with `API_MIN_VERSION = 1` and `API_MAX_VERSION = 3`.

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 3
```

```python
# views.py

from django_api_versioning import endpoint
from rest_framework.decorators import api_view
from rest_framework.response import Response


@endpoint("beta/", versions=[1, 3])
@api_view(["GET"])
def beta_view(request):
    return Response({"status": "beta"})
```

Decorator order matters. Python applies decorators from the bottom upward, so `@api_view` converts the function into a DRF view first. The outer `@endpoint` decorator then registers the resulting callable.

The endpoint is registered for v1 and v3, but not v2:

| Version | Route |
| --- | --- |
| v1 | `/api/v1/beta/` |
| v2 | Not registered |
| v3 | `/api/v3/beta/` |

The `versions` argument selects versions inside the configured range; it does not extend that range. A value above `API_MAX_VERSION` raises `InvalidVersionError`. Entries below `API_MIN_VERSION` are skipped with a warning.

For a bounded inclusive range, the package also provides `ver_range()`:

```python
from django_api_versioning import endpoint, ver_range
from django.http import JsonResponse


@endpoint("legacy/", versions=ver_range(1, 3))
def legacy_view(request):
    return JsonResponse({"status": "legacy"})
```

`ver_range(1, 3)` returns `[1, 2, 3]`.

## Group endpoints with `app_name`

The optional `app_name` argument inserts a grouping segment between `API_BASE_PATH` and the endpoint postfix.

For example:

```python
from django_api_versioning import endpoint
from django.http import JsonResponse


@endpoint("reports/", version=1, app_name="admin")
def admin_report_view(request):
    return JsonResponse({"status": "ok"})
```

With the default `API_BASE_PATH = "api/v{version}/"`, the resulting route is:

```text
/api/v1/admin/reports/
```

The `app_name` argument adds one grouping segment. It is not an arbitrary per-endpoint URL template.

## Customize the global URL prefix with `API_BASE_PATH`

The default value is:

```python
API_BASE_PATH = "api/v{version}/"
```

If the project mounts the API under a separate `api/` prefix in its URLconf, the setting can instead contain only the version segment:

```python
# settings.py

API_BASE_PATH = "v{version}/"
```

The URLconf then supplies the outer prefix:

```python
# urls.py

from django.urls import include, path

from . import views  # noqa: F401 — import first to execute decorators

from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("api/", include(api_urlpatterns)),
]
```

The resulting URL remains `/api/v1/users/`.

`API_BASE_PATH` must contain the `{version}` placeholder. It is the package's versioned route prefix, so coordinate it with the URLconf mount point to avoid duplicating path segments.

## What the package does not offer

The decorator-based approach deliberately keeps endpoint registration on the view rather than introducing a separate configuration object.

There is no built-in `VersionedEndpoint(path=..., versions=..., basename=...)` configuration object. The declaration site is the view decorator.

Likewise, `@endpoint` does not provide a per-registration kwargs mechanism. View configuration such as `lookup_field` belongs on the view class itself.

### ViewSet and router boundary

The examples using `ListAPIView` and `RetrieveUpdateDestroyAPIView` work with `@endpoint`. A `ModelViewSet` class cannot be decorated directly because the package calls `.as_view()` without the action mapping required by DRF ViewSets.

There are two alternatives:

1. Register ViewSets with DRF's `SimpleRouter` or `DefaultRouter` and mount the generated URLs under version-specific prefixes.
2. Pass a configured `ModelViewSet.as_view({...})` callable to `@endpoint` for one specific route.

For example, a configured callable can expose the list and create actions:

```python
from django_api_versioning import endpoint

from .views import UserViewSetV1


user_list_view = UserViewSetV1.as_view({
    "get": "list",
    "post": "create",
})

endpoint("users/", version=1)(user_list_view)
```

This callable can be registered as a route, but it does not generate the full set of router routes automatically. Detail routes and custom actions require their own configured callables and registrations.

For resource-oriented ViewSets, use DRF routers. For generic views and individual endpoints, `@endpoint` provides version-based registration without a separate router configuration.

The [integration project's URLconf](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/integration_test_project/project/urls.py) shows router-based ViewSet registration alongside decorator-based endpoint registration. See also the [DRF routers documentation](https://www.django-rest-framework.org/api-guide/routers/).

## Trade-offs and scope

Scope: routing only. These approaches determine which view callable is attached to a versioned URL. They do not decide whether a response change is backward compatible, negotiate a request version, or maintain versioned API schemas.

Manual declarative configuration is useful when the configuration genuinely carries information beyond the endpoint and version—for example, when a project needs a centralized inventory of ViewSets or custom route-generation rules. Its cost is maintaining the builder and explicitly registering unchanged endpoints in each version.

Decorator-based registration is useful when the version, URL postfix, and view naturally belong together. Its costs are the import-order requirement and the inability to decorate `ModelViewSet` classes directly.

When the benefit is smaller: if an API has only one version and there is no plan to introduce another, a plain `urlpatterns` list is simpler and easier to understand.

When declarative registration matters most: when multiple API versions are maintained, endpoint changes are incremental, and keeping unchanged routes available across versions would otherwise require repeated registration entries. The value comes from the actual endpoint-change pattern and the URL configuration it avoids—not from the number of versions alone.

The package's automatic carry-forward behavior also requires care: a v1 implementation registered with `version=1` remains active through `API_MAX_VERSION` unless a later registration replaces it. Review the version matrix whenever endpoint contracts change, and test serializers, permissions, filtering, pagination, and response behavior for every supported version.

Disclosure: I maintain `django-api-versioning`, the package discussed in this article.

## Next steps

To evaluate the registration model against your API's routing requirements, start with the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
