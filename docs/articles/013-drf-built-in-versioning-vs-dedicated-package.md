---
slug: "013-drf-version-negotiation-vs-endpoint-registration"
title: "DRF Version Negotiation vs Endpoint Registration"
description: "Compare DRF version negotiation with declarative endpoint registration, including route inheritance, request.version, URL generation, and ViewSet boundaries."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "Django REST Framework"
  - "API versioning"
  - "Django URL routing"
  - "Endpoint registration"
  - "Python"
---

# DRF Version Negotiation vs Endpoint Registration

Django REST Framework (DRF) provides built-in versioning schemes for determining which API version a request targets. However, identifying the requested version and maintaining the mapping between endpoint implementations and API versions are two different responsibilities.

For the second problem, [django-api-versioning on PyPI](https://pypi.org/project/django-api-versioning/) provides declarative endpoint registration. Instead of manually maintaining the relationship between every versioned URL and its view, developers declare the version from which an endpoint implementation should be registered.

This distinction matters when most endpoints remain unchanged between releases while only a subset receives new implementations.

## Declarative endpoint registration

Consider an API that supports v1 and v2. The user-list endpoint has a different implementation in each version, but other endpoints may remain unchanged.

Configure the supported version range:

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

Declare the endpoint implementations:

```python
# accounts/views.py

from django_api_versioning import endpoint
from rest_framework.response import Response
from rest_framework.views import APIView


@endpoint("users/", version=1)
class UserListV1(APIView):
    def get(self, request):
        return Response({
            "users": [],
        })


@endpoint("users/", version=2)
class UserListV2(APIView):
    def get(self, request):
        return Response({
            "users": [],
            "pagination": {
                "count": 0,
            },
        })
```

With the default `API_BASE_PATH = "api/v{version}/"`, the package derives these routes:

| URL | Registered implementation |
| --- | --- |
| `/api/v1/users/` | `UserListV1` |
| `/api/v2/users/` | `UserListV2` |

The URL is constructed from the configured version prefix and the decorator's `postfix`. The integer `version=1` is represented as `v1` in the generated URL; the package itself uses integer version identifiers.

### Mounting the generated URL patterns

The package registers routes when Python modules containing `@endpoint` declarations are imported. Import those modules before importing the generated URL patterns.

```python
# project/urls.py

from django.urls import include, path

from accounts import views as account_views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The `account_views` import is intentional: it executes the decorators and populates the registry before `api_urlpatterns` is imported.

The package's routing behavior, version validation, registration precedence, and import requirements are defined in its [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

### How registration inheritance works

The package uses segment registration:

- `version=N` registers an implementation from version N through `API_MAX_VERSION`, inclusive.
- A declaration for the same route at a higher source version replaces the earlier implementation from that version onward.
- `versions=[...]` registers an implementation only for the explicitly listed versions.

For the example above, the registration behavior is:

| Route version | Source declaration | Result |
| --- | --- | --- |
| v1 | `version=1` | `UserListV1` |
| v2 | `version=1`, then `version=2` | `UserListV2` |

The registration rule is based on the source version of each declaration. When two declarations collide, the higher integer source version wins; if their source versions are equal, the later registration wins.

This is registration-time route selection, not request-time traversal through older versions. The package does not search backward through view classes when a request arrives.

**Now:**

- `/api/v1/users/` resolves to `UserListV1`.
- `/api/v2/users/` resolves to `UserListV2`.

**Scope: routing only.** This mechanism does not create Python inheritance, merge serializers, or establish semantic backward compatibility.

It is also important to distinguish two situations:

- If a version is outside the configured range, the package does not generate routes for it.
- If a version is within the configured range but an endpoint was not registered for that version, that endpoint has no matching route and resolves to a 404.

For example, an endpoint declared with `versions=[1, 3]` is not registered at v2. The package does not fall back to its v1 implementation for that missing route.

## What DRF built-in versioning does

DRF's versioning schemes determine the requested API version and expose it through `request.version` when versioning is enabled.

The available schemes include URL-path, namespace, query-parameter, hostname, and Accept-header versioning. This article focuses on `AcceptHeaderVersioning` and `URLPathVersioning` because they illustrate two common ways of identifying a requested version.

DRF version negotiation does not prescribe how many view classes or URL configurations an application must maintain. Developers can use shared views, separate views, conditional dispatch, namespaces, or routers according to their API design.

See the official [DRF versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/).

## AcceptHeaderVersioning

`AcceptHeaderVersioning` reads the version from a media-type parameter in the HTTP `Accept` header.

A client can send:

```http
GET /api/users/ HTTP/1.1
Accept: application/json; version=2
```

Configure the versioning scheme:

```python
# settings.py

REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "rest_framework.versioning.AcceptHeaderVersioning"
    ),
    "DEFAULT_VERSION": "1",
    "ALLOWED_VERSIONS": ["1", "2"],
    "VERSION_PARAM": "version",
}
```

A shared view can inspect `request.version` and return the appropriate representation:

```python
# accounts/views.py

from rest_framework.response import Response
from rest_framework.views import APIView


class UserList(APIView):
    def get(self, request):
        if request.version == "1":
            return Response({
                "users": [],
            })

        return Response({
            "users": [],
            "pagination": {
                "count": 0,
            },
        })
```

Both versions use the same URL:

```text
/api/users/
```

The requested version is carried by the `Accept` header rather than the URL path.

This approach is useful when clients can send the required media type and the API benefits from keeping a stable resource URL.

Header-based versioning does not prevent code reuse or inheritance. A shared view can branch on `request.version`, and an application can implement its own version-to-handler mapping. What DRF does not provide through the versioning scheme itself is the package's declarative endpoint-registration model.

### Caching implications

When the response varies according to the `Accept` header, shared caches must distinguish requests with different version parameters.

The response should include an appropriate `Vary: Accept` header, and the CDN or reverse proxy must honor that header or explicitly include `Accept` in its cache key.

A stable URL alone does not make version-specific responses safe to cache under one shared cache key.

## URLPathVersioning

`URLPathVersioning` obtains the requested version from a keyword argument captured by Django's URL pattern.

Configure DRF:

```python
# settings.py

REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "rest_framework.versioning.URLPathVersioning"
    ),
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1", "v2"],
    "VERSION_PARAM": "version",
}
```

The URL pattern must capture the configured parameter:

```python
# project/urls.py

from django.urls import path

from accounts.views import UserList


urlpatterns = [
    path(
        "api/<str:version>/users/",
        UserList.as_view(),
        name="users-list",
    ),
]
```

The view can inspect the resolved version:

```python
# accounts/views.py

from rest_framework.response import Response
from rest_framework.views import APIView


class UserList(APIView):
    def get(self, request):
        if request.version == "v1":
            return Response({
                "users": [],
            })

        return Response({
            "users": [],
            "pagination": {
                "count": 0,
            },
        })
```

The resulting URLs are:

- `/api/v1/users/`
- `/api/v2/users/`

Django passes the captured `version` keyword argument to the view, and DRF uses it to determine `request.version`.

A version-looking URL segment is not sufficient by itself: the URL pattern must capture the value under the configured `VERSION_PARAM` name.

This distinction also matters when evaluating a separate route-registration package. `django-api-versioning` generates concrete versioned paths such as `/api/v2/users/`; those patterns do not capture a `version` keyword argument. Its generated routes therefore do not automatically provide the input expected by DRF's `URLPathVersioning`.

## Comparing the responsibilities

The two mechanisms address different layers:

- DRF versioning determines which version the client requested.
- `django-api-versioning` determines which implementation is registered for each versioned endpoint.

| Concern | DRF built-in versioning | django-api-versioning |
| --- | --- | --- |
| Primary responsibility | Determine the requested version | Register endpoint implementations |
| Version source | Request header, URL, namespace, query parameter, or hostname | Decorator arguments and package settings |
| `request.version` | Populated when DRF versioning is enabled | Not populated by the package itself |
| Route generation | Depends on the application's URL configuration and selected scheme | Generated from endpoint declarations |
| Unchanged endpoint carry-forward | Application-defined through its views and routing design | Supported by `version=N` registration |
| Endpoint replacement | Application-defined | Higher source-version declaration replaces a colliding route |
| ViewSet routing | Supported through DRF routers | Separate from the package's endpoint registry |

These mechanisms should not be treated as interchangeable versioning schemes. One negotiates the requested version; the other manages the registration of endpoint implementations against versioned routes.

## The ViewSet and router boundary

DRF routers remain the normal choice for resource-oriented ViewSets.

For example, a project can define a ViewSet and register it with `SimpleRouter`:

```python
# accounts/views.py

from rest_framework import viewsets
from rest_framework.response import Response


class UserViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({
            "users": [],
        })
```

```python
# accounts/urls.py

from rest_framework.routers import SimpleRouter

from accounts.views import UserViewSet


router = SimpleRouter()
router.register("users", UserViewSet, basename="users")

urlpatterns = router.urls
```

A router generates the list, detail, and applicable action routes from the ViewSet.

`@endpoint` does not directly support decorating a `ModelViewSet` or another ViewSet class. A ViewSet requires an action mapping when converted into a callable, whereas the package's class-based view handling calls `as_view()` without that mapping.

A configured callable can be registered for one explicitly configured route:

```python
# accounts/versioned_routes.py

from django_api_versioning import endpoint
from accounts.views import UserViewSet


user_list_route = endpoint("users/", version=1)(
    UserViewSet.as_view({"get": "list"})
)
```

This registers one route with a fixed action mapping. It is not a replacement for router registration and does not generate the complete ViewSet route set.

For mixed projects, keep the responsibilities explicit:

- Use DRF routers for resource-oriented ViewSets.
- Use `@endpoint` for supported function-based views, `APIView` classes, and generic views.
- Mount router-generated URL patterns under the desired versioned prefixes yourself.

The package does not automatically integrate router-generated URLs into its endpoint registry. See the official [DRF routers documentation](https://www.django-rest-framework.org/api-guide/routers/).

## Versioned project structure

A project may organize its views by API version:

```text
accounts/
    views/
        __init__.py
        users_v1.py
        users_v2.py
        reports_v2.py
```

This structure can make version-specific implementations easier to locate, but it does not itself register routes or determine which implementation handles a request.

With `django-api-versioning`, the version-specific modules can contain the endpoint declarations, while the URLconf imports those modules before including the generated patterns.

The package therefore complements the organization of version-specific code: the directory structure organizes implementations, and endpoint declarations define their route registration.

## Trade-offs and scope

The package is useful when the recurring maintenance burden is the mapping between endpoint implementations and API versions.

Segment registration can reduce repeated URL configuration when many endpoints remain unchanged between releases. It also keeps the version-to-implementation declaration next to the view.

However, automatic carry-forward is a policy with consequences.

A declaration such as `version=1` remains registered through `API_MAX_VERSION` unless a later declaration replaces it. If the endpoint's contract changes but its registration does not, the earlier implementation can continue serving later versions.

The package does not:

- Create Python inheritance between view classes.
- Merge serializers, permissions, or business logic.
- Determine whether a change is backward compatible.
- Populate DRF's `request.version`.
- Automatically register DRF router-generated ViewSet routes.
- Generate or maintain version-specific OpenAPI schemas.

For applications that only need request-time version negotiation, a DRF built-in scheme may be sufficient. When the URL configuration is already small and stable, the benefit of adding another registration abstraction is smaller.

The decision should be based on the actual endpoint-change pattern and the maintenance cost of the existing routing design, not a universal threshold based only on the number of API versions.

## Conclusion

DRF's built-in versioning schemes identify the version requested by a client. `django-api-versioning` manages which endpoint implementation is registered for each supported version.

For projects where endpoint implementations change incrementally across releases, the package's segment registration model makes carry-forward and replacement behavior explicit in the declarations rather than requiring the same mapping to be maintained separately in URL configuration.

**Next step:** review the package's [source code and integration examples](https://github.com/mojtaba-arvin/django-api-versioning) and verify the generated route matrix against the API contracts your clients depend on.
