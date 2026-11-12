---
slug: "006-django-api-versioning-without-duplicating-url-patterns"
title: "Django API versioning without duplicating URL configuration"
description: "Compare DRF header and URL-path versioning with declarative endpoint registration: how each approach identifies API versions, organizes views, and manages versioned routes."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "API versioning"
  - "URL patterns"
  - "DRF"
  - "Accept headers"
  - "content negotiation"
---

# Django API versioning without duplicating URL configuration

When an API supports multiple versions, you need a way to identify the requested version and select the corresponding behavior.

One approach is to keep a shared view and let DRF identify the version from the request. Another is to register separate view implementations for versioned URLs.

It is worth clarifying one thing first: DRF does not require a separate `path()` declaration for every endpoint version. Its built-in `URLPathVersioning` can capture the version from a URL parameter in a single route, while a shared view branches on `request.version`.

There are several ways to organize versioned APIs:

- **Header versioning:** the URL stays the same, and the client selects a version through the `Accept` header.
- **URL-path versioning:** the version appears in the URL, and DRF exposes it through `request.version`.
- **Declarative registration:** the version appears in the URL, but separate endpoint implementations are registered through decorators and the package generates the corresponding URL patterns.

The first two approaches use DRF's built-in version identification mechanisms. The third uses `django-api-versioning` to manage route registration and select different view implementations.

This article focuses on the trade-offs between these approaches.

## Strategy 1: Accept header versioning with DRF

`AcceptHeaderVersioning` extracts the version from the media type parameters of the `Accept` header. The URL stays the same across versions.

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.AcceptHeaderVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ('v1', 'v2'),
}
```

The `DEFAULT_VERSION` setting means that clients can omit the version parameter. When it is absent, DRF uses the configured default version.

`ALLOWED_VERSIONS` restricts the accepted versions to `v1` and `v2`.

```python
# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User


class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']
```

The view can select its serializer based on `request.version`:

```python
# views.py
from rest_framework.generics import ListAPIView
from django.contrib.auth.models import User
from .serializers import UserSerializerV1, UserSerializerV2


class UserList(ListAPIView):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.version == 'v1':
            return UserSerializerV1
        return UserSerializerV2
```

The URL configuration contains only one route:

```python
# urls.py
from django.urls import path
from .views import UserList

urlpatterns = [
    path('api/users/', UserList.as_view()),
]
```

Clients select the version through the `Accept` header:

```bash
# v1
curl -H "Accept: application/json; version=v1" \
  http://api.example.com/api/users/

# v2
curl -H "Accept: application/json; version=v2" \
  http://api.example.com/api/users/
```

DRF's content negotiation selects a renderer based on the requested media type. The selected media type is also made available to `AcceptHeaderVersioning`, which extracts the `version` parameter.

The `version` parameter is not part of the standard `application/json` media type definition. DRF nevertheless supports this versioning convention. For a more explicit public API media type contract, you can use a vendor media type.

### Using a vendor media type

A custom renderer can define the vendor media type while retaining JSON rendering behavior:

```python
# renderers.py
from rest_framework.renderers import JSONRenderer


class UserJSONRenderer(JSONRenderer):
    media_type = 'application/vnd.example.user+json'
```

Register it alongside the standard JSON renderer:

```python
# views.py
from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONRenderer
from django.contrib.auth.models import User
from .renderers import UserJSONRenderer
from .serializers import UserSerializerV1, UserSerializerV2


class UserList(ListAPIView):
    renderer_classes = [JSONRenderer, UserJSONRenderer]
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.version == 'v1':
            return UserSerializerV1
        return UserSerializerV2
```

Both media types can now be used:

```bash
# Standard JSON media type
curl -H "Accept: application/json; version=v1" \
  http://api.example.com/api/users/

# Vendor media type
curl -H "Accept: application/vnd.example.user+json; version=v1" \
  http://api.example.com/api/users/
```

The standard renderer handles `application/json`, while the custom renderer handles the vendor media type. If only the custom renderer were registered, requests accepting only `application/json` would not match an available renderer and could receive `406 Not Acceptable`.

Renderer ordering also matters when the client sends an underspecified header such as `Accept: */*`: DRF selects the first renderer in the configured list when the available media types have the same specificity.

**What this eliminates:** Per-version URL declarations. The same `/api/users/` route serves all configured versions.

**What it introduces:** Version-dependent behavior inside the view. As versions diverge, serializer selection and other conditional logic can grow. Tests must exercise each supported version with the appropriate `Accept` header.

**When this fits:** You want one stable URL for a resource and clients can reliably set request headers. This is particularly suitable when version differences are limited to representation changes or a small amount of conditional behavior.

## Strategy 2: Declarative registration with django-api-versioning

Another approach keeps the version in the URL but generates versioned routes from endpoint registrations.

Install the package:

```bash
pip install django-api-versioning
```

Configure the version range:

```python
# settings.py
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

Define separate implementations for endpoints whose behavior differs between versions:

```python
# views.py
from django_api_versioning import endpoint
from rest_framework.generics import ListAPIView
from django.contrib.auth.models import User
from .serializers import UserSerializerV1, UserSerializerV2


@endpoint("users/", version=1)
class UserListV1(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/", version=2)
class UserListV2(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV2
```

Import the module containing the declarations before importing the generated URL patterns:

```python
# urls.py
from django.urls import include, path
from . import views  # noqa: F401 — import first so decorators register

from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

With `API_MAX_VERSION = 2` and the package's default `API_BASE_PATH = "api/v{version}/"`, this produces:

- `/api/v1/users/` → `UserListV1`
- `/api/v2/users/` → `UserListV2`

For this endpoint, there are two endpoint declarations and two runtime URL patterns. That is not fewer declarations than manually writing two `path()` entries for two different implementations.

The difference becomes more significant when endpoints remain unchanged across versions.

For example, if `posts/` has the same implementation in v1 and v2, it needs only one registration:

```python
@endpoint("posts/", version=1)
class PostList(ListAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
```

The package registers this implementation for v1 and v2. You do not need to add another declaration just to expose the unchanged endpoint under the newer versioned URL.

The runtime URL patterns are still generated for each supported version. What changes is where the registration logic lives: each implementation is declared at its starting version, and the registry generates the corresponding routes.

### Understanding segment registration

The meaning of `version=N` is important:

- `version=N` registers the implementation from N through `API_MAX_VERSION`, inclusive.
- A later declaration for the same route at a higher starting version overrides the earlier implementation from that version onward.
- `versions=[...]` registers an implementation only for the explicitly listed versions.

For example:

```python
@endpoint("users/", version=1)
class UserListV1(ListAPIView):
    ...

@endpoint("users/", version=3)
class UserListV3(ListAPIView):
    ...
```

With `API_MAX_VERSION = 4`, the resulting route selection is:

| URL | Implementation |
| --- | --- |
| `/api/v1/users/` | `UserListV1` |
| `/api/v2/users/` | `UserListV1` |
| `/api/v3/users/` | `UserListV3` |
| `/api/v4/users/` | `UserListV3` |

This is route-registration inheritance, not Python class inheritance. The package does not copy methods, merge serializers, or establish that the inherited implementation is semantically compatible with a newer API contract.

That distinction creates an important maintenance responsibility: if an endpoint's contract changes in a new API version, its registration must be updated deliberately. Otherwise, the previous implementation continues to serve later versions through the configured range.

Review the version matrix and test the actual API contract for every supported version, including serializers, permissions, filtering, pagination, and schema behavior where relevant.

**What this eliminates:** Repeated URL declarations for unchanged endpoints. You register an implementation at its starting version instead of manually declaring every endpoint-version pair.

**What it introduces:** An additional dependency and a specific registration model. The version remains visible in the URL, so clients must use the appropriate versioned URL.

**When this fits:** You want version-specific implementations selected through versioned URLs, and endpoint changes occur incrementally rather than requiring every endpoint to be redefined at every release.

## Comparing the approaches

The choice is not simply between one URL declaration and many. DRF already offers URL-path versioning with a shared view. The important distinction is how much version-specific behavior you want to put inside a shared view versus how you want to register separate implementations.

| Aspect | `AcceptHeaderVersioning` | `URLPathVersioning` | `django-api-versioning` |
| --- | --- | --- | --- |
| Version location | `Accept` header | URL path | URL path |
| URL across versions | Same | Version segment changes | Version segment changes |
| Runtime URL patterns | One per endpoint | One per endpoint using a version converter | One per endpoint per registered version |
| View organization | Shared view with conditional behavior | Shared view with conditional behavior | Separate implementations where behavior changes |
| Version selection | DRF content negotiation | DRF URL version extraction | Generated route registration |
| Additional dependency | No | No | Yes |
| Main maintenance concern | Conditional view logic | Conditional view logic and URL configuration | Registration boundaries and carry-forward behavior |

DRF's `URLPathVersioning` is particularly relevant when you want the version in the URL but do not need separate view implementations. It can use one URL pattern containing a version parameter and expose that value through `request.version`.

The package addresses a different organizational preference: registering separate implementations at version boundaries and generating the corresponding routes.

## Trade-offs and scope

Header versioning is a good fit when:

- The URL should remain stable across API versions.
- Clients can set the `Accept` header reliably.
- Version differences are manageable within a shared view.
- You prefer DRF's built-in version negotiation without another dependency.

DRF's `URLPathVersioning` is a good fit when:

- The version should be visible in the URL.
- A shared view can handle version-dependent behavior.
- You want DRF to extract the version from the URL without adding a routing dependency.

Declarative registration is a good fit when:

- You prefer separate view implementations at version boundaries.
- Many endpoints remain unchanged as new versions are introduced.
- You want route registration to reflect the evolution of endpoint implementations.
- The benefit of generated registrations justifies adopting and maintaining the package's registration model.

**When the benefit is smaller:** If every endpoint changes at every version boundary, or if a shared view with DRF's built-in versioning is already straightforward to maintain, declarative registration may not reduce enough complexity to justify another dependency.

### ViewSet note

`ModelViewSet` classes cannot be decorated directly with `@endpoint`. The decorator calls `.as_view()` without the action mapping required by DRF ViewSets.

For resource-shaped endpoints, use DRF routers and mount their generated URL patterns under the appropriate versioned prefixes. This router configuration is separate from the package's endpoint registry; the package does not automatically register or inherit router-generated ViewSet actions.

A manually configured callable such as:

```python
MyViewSet.as_view({"get": "list"})
```

can be registered as a specific route, but this is not a substitute for normal router registration of list, detail, and custom-action routes.

The integration test project's URLconf demonstrates manually mounting router URLs under versioned prefixes. It should be understood as a separate routing configuration, not automatic integration between the router and `@endpoint`.

### Author disclosure

I am the maintainer of `django-api-versioning`. The package's registration behavior and limitations are documented in its canonical versioning contract.

## Next steps

For APIs where the version should be identified from the request, DRF's built-in `AcceptHeaderVersioning` and `URLPathVersioning` are useful starting points.

If you prefer separate endpoint implementations with generated versioned routes, explore [`django-api-versioning` on PyPI](https://pypi.org/project/django-api-versioning/).

The package's [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md) documents the exact registration semantics, version boundaries, import order, and ViewSet limitations.

The key question is not how many versions your API has, but whether shared views or version-specific endpoint registrations are easier to maintain as its contract evolves.
