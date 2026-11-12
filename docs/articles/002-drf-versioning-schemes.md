---
slug: "002-drf-versioning-schemes"
title: "DRF versioning schemes: design tradeoffs when scaling APIs"
description: "Compare AcceptHeaderVersioning, URLPathVersioning, and NamespaceVersioning. Understand how each scheme detects the requested version, and how view organization is an independent decision."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "DRF versioning schemes"
  - "AcceptHeaderVersioning vs URLPathVersioning"
  - "version branching patterns"
  - "NamespaceVersioning"
---

# DRF versioning schemes: design tradeoffs when scaling APIs

## What DRF versioning schemes actually decide

Django REST Framework provides several versioning strategies. Three are commonly compared: `AcceptHeaderVersioning`, `URLPathVersioning`, and `NamespaceVersioning`. DRF also ships `HostNameVersioning` and `QueryParameterVersioning`—they solve the same problem in different ways and follow the same pattern described below.

Every versioning scheme answers one question: **"How does the API know which version the client requested?"** The scheme's job is to determine the version and expose it as `request.version`. It does not decide how your application organizes the views that handle each version. That second decision is yours, and it is independent of the scheme you pick.

This distinction matters because most of the tradeoffs people attribute to DRF schemes are actually tradeoffs of view organization. Once you separate the two, the comparison becomes clearer.

## Header-based versioning: AcceptHeaderVersioning

Clients send the version in the HTTP `Accept` header:

```http
GET /api/users/ HTTP/1.1
Accept: application/json; version=1.0
```

DRF parses the header and stores the version in `request.version`. Your application then decides how to use that value.

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.AcceptHeaderVersioning',
    'DEFAULT_VERSION': '1.0',
    'ALLOWED_VERSIONS': ('1.0', '2.0'),
}
```

```python
# views.py
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from rest_framework import serializers

class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']

# One possible organization: branch inside a shared view.
class UserList(APIView):
    def get(self, request):
        users = User.objects.all()

        if request.version == '1.0':
            serializer = UserSerializerV1(users, many=True)
        else:
            serializer = UserSerializerV2(users, many=True)

        return Response(serializer.data)
```

**URL:** A single path, `/api/users/`, serves all versions.

**How version is detected:** From the `Accept` header's version parameter. The version value is a string in the form DRF produces from the header (e.g. `'1.0'`), not a URL path segment.

**What the scheme decides:** Only that `request.version` is populated from the header.

**What your application decides:** Whether a single view branches on `request.version`, or whether separate views handle each version. Both are valid with `AcceptHeaderVersioning`. Note that with header-based versioning, the URL path is identical across versions, so URLconf alone cannot route to separate views by version. If you want separate views per version, the dispatch must happen somewhere in the request pipeline—typically branching inside a single view, or a shared view that reads `request.version` and delegates to a version-specific handler class.

## URL-path versioning: URLPathVersioning

The version lives in the URL path:

```http
GET /api/v1/users/ HTTP/1.1
```

DRF extracts the version from the URL:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ('v1', 'v2'),
}
```

```python
# views.py
from rest_framework.generics import ListAPIView
from django.contrib.auth.models import User
from rest_framework import serializers

class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']

# One possible organization: branch inside a shared view.
class UserList(ListAPIView):
    def get_serializer_class(self):
        if self.request.version == 'v1':
            return UserSerializerV1
        return UserSerializerV2

    def get_queryset(self):
        return User.objects.all()
```

```python
# urls.py
from django.urls import path

urlpatterns = [
    path('api/<str:version>/users/', UserList.as_view()),
]
```

**URL:** A single path template, `/api/<version>/users/`, serves all versions.

**How version is detected:** From the URL keyword argument named by `VERSION_PARAM` (default: `version`).

**What the scheme decides:** Only that `request.version` is populated from that URL keyword argument.

**What your application decides:** Whether to use a shared view with branching (as above), or separate URL patterns per version—each pointing to its own view:

```python
# Alternative organization: separate URL patterns per version.
from django.urls import path
from .views import UserListV1, UserListV2

urlpatterns = [
    path('api/v1/users/', UserListV1.as_view(), name='v1-user-list'),
    path('api/v2/users/', UserListV2.as_view(), name='v2-user-list'),
]
```

`URLPathVersioning` does not automatically extract the version from static URL segments such as `v1` and `v2`. It requires a URL keyword argument named by `VERSION_PARAM` (default: `version`). With static paths like `api/v1/users/` and `api/v2/users/`, there is no version keyword argument, so `URLPathVersioning` returns the `DEFAULT_VERSION` value for every request—even `UserListV2` will see `request.version == 'v1'` in this organization. The URLconf still dispatches to the correct view by URL path, but `request.version` does not reflect the version in the URL. If you need `request.version` to reflect the URL version, use a dynamic version parameter (as in the first example above) or a scheme that reads version from the URL structure, such as `NamespaceVersioning`.

## Namespace-based versioning: NamespaceVersioning

Each version is identified by a Django URL namespace:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
}
```

```python
# v1/views.py
from rest_framework.generics import ListAPIView
from django.contrib.auth.models import User
from rest_framework import serializers

class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class UserListV1(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1
```

```python
# v2/views.py
from v1.views import UserListV1
from rest_framework import serializers

class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']

class UserListV2(UserListV1):
    serializer_class = UserSerializerV2
```

```python
# urls.py
from django.urls import path, include
from v1 import views as v1_views
from v2 import views as v2_views

urlpatterns = [
    path('api/v1/', include(([
        path('users/', v1_views.UserListV1.as_view(), name='user-list'),
    ], 'versioned_routes'), namespace='v1')),
    path('api/v2/', include(([
        path('users/', v2_views.UserListV2.as_view(), name='user-list'),
    ], 'versioned_routes'), namespace='v2')),
]
```

**URL:** Separate URLs, `/api/v1/users/` and `/api/v2/users/`.

**How version is detected:** From the namespace of the URL that matched the request. `NamespaceVersioning` sets `request.version` based on `request.resolver_match.namespace`.

**What the scheme decides:** Only that `request.version` is populated from the matched namespace.

**What your application decides:** Whether each namespace routes to a distinct view (as above) or whether multiple namespaces include the same URLconf and therefore the same view. The official DRF documentation shows a shared URLconf included under multiple namespaces; the same view handles both versions. Separate views are one possible organization, not a requirement of the scheme.

The separate-view pattern above is common when versions diverge substantially. The shared-URLconf pattern is common when versions differ only in small ways and the view already branches on `request.version` elsewhere.

## Comparison: what each scheme decides

The table separates what the versioning scheme decides from what your application decides.

| Aspect | AcceptHeaderVersioning | URLPathVersioning | NamespaceVersioning |
| --- | --- | --- | --- |
| Version source | Accept header parameter | URL keyword argument (`VERSION_PARAM`) | Django URL namespace |
| Version visible in URL | No | Yes | Yes |
| Populates `request.version` | Yes | Yes | Yes |
| Shared view possible | Yes | Yes | Yes |
| Separate views possible | Yes | Yes | Yes |
| View branching required by the scheme | No | No | No |
| Typical URL configuration | One shared route | One dynamic route, or separate static routes per version | Shared URLconf included under multiple namespaces, or separate URLconfs per namespace |
| `request.version` reflects URL when static routes are used | N/A (URL has no version) | No — returns `DEFAULT_VERSION` unless a version keyword argument is supplied | Yes — namespace is the version source |

These schemes determine how DRF identifies the requested version. They do not prescribe whether your application uses shared views with conditional logic or separate views for each version. That is an independent architectural decision.

## View organization is the real tradeoff

Once you separate version detection from view organization, the practical decision is not "which DRF scheme" but "how will I organize my views and URLs." Two organizations dominate:

**Shared view with branching:** One view class per endpoint, branching inside methods on `request.version`. This works with any of the three schemes. It scales poorly as versions diverge, because each new version adds branches to the shared view. Endpoints that don't change need no new branches, but endpoints that do change need one branch per version boundary.

**Separate views per version:** One view class per endpoint per version. This also works with any of the three schemes, but with one qualification. `NamespaceVersioning` makes this organization natural—each namespace gets its own views, and `request.version` reflects the URL. `URLPathVersioning` supports it only if you use a dynamic version parameter so that `request.version` is populated; with static paths per version, the URLconf dispatches correctly but `request.version` stays at `DEFAULT_VERSION`. `AcceptHeaderVersioning` supports it only if the dispatch between views happens inside the request pipeline, since the URL alone cannot distinguish versions.

The two organizations are the actual decision point. The scheme you pick determines how you identify the version; the organization you pick determines how your codebase grows.

## Scaling from v2 to v4

How a codebase scales depends on the organization, not the scheme. Two scenarios:

**Shared view with branching:** If your API has 20 endpoints and half of them change between versions, up to 10 views accumulate version branches. Endpoints that never change need no branches. Endpoints that change at every version boundary grow a branch per version.

**Separate views per version:** If nine of ten endpoints are unchanged between versions, and you choose to give each version its own view classes, you write nine extra view classes and nine extra `path()` entries. If instead you reuse the same view class across versions—as `NamespaceVersioning` allows, and as `URLPathVersioning` with a dynamic version parameter also allows—you write only the view for the endpoints that changed.

`NamespaceVersioning` does not require you to duplicate every view. It requires only that the URL structure distinguishes versions by namespace. Whether that namespace includes a shared URLconf or a per-version URLconf is your choice.

## When a routing library changes the model

A dedicated library like `django-api-versioning` offers a different model: each endpoint implementation is registered at the version where it becomes active. That registration remains effective for subsequent versions until a later registration overrides it.

This is not "register once and forget." It is "register at the version where the endpoint changes, and rely on inheritance for versions where it doesn't." A three-version API with one endpoint implementation change looks like this:

```python
# settings.py
API_MIN_VERSION = 1
API_MAX_VERSION = 3
```

```python
# views.py
from django_api_versioning.decorators import endpoint
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework import serializers

class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']

@endpoint("users/", version=1)
class UserListView(APIView):
    def get(self, request):
        users = User.objects.all()
        return Response(UserSerializerV1(users, many=True).data)

@endpoint("users/", version=2)
class UserListViewV2(APIView):
    def get(self, request):
        users = User.objects.all()
        return Response(UserSerializerV2(users, many=True).data)
```

```python
# urls.py
from django.urls import include, path
from . import views  # noqa: F401 — import first so decorators register
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

With `API_MAX_VERSION = 3`, the example covers versions 1, 2, and 3:

- `/api/v1/users/` uses `UserListView` (registered at `version=1`).
- `/api/v2/users/` uses `UserListViewV2` (registered at `version=2`).
- `/api/v3/users/` uses `UserListViewV2` (the `version=2` registration stays active through `API_MAX_VERSION` until a later version overrides it).

**How it differs from the three DRF schemes:**

- **Version source:** The URL path segment, generated by the library from `API_BASE_PATH` (`"api/v{version}/"` by default). Similar to `URLPathVersioning` with a dynamic parameter, but the URL is generated from the registration rather than written in a URLconf pattern.
- **View organization:** Separate per-version views, without URLconf duplication. Each changed endpoint gets its own view class; unchanged endpoints have a single class active across the version range.
- **Registration model:** Each endpoint implementation is declared at the version it becomes active. Versions where the endpoint doesn't change inherit the previous registration. This is different from `NamespaceVersioning` (where each namespace gets its own URLconf) and from `URLPathVersioning` with shared views (where one class branches on `request.version`).

The override happens at the registration layer, not through Python class inheritance. `UserListViewV2` inherits from `APIView`, not from `UserListView`. Each `@endpoint` call with the same postfix and a higher version replaces the previous registration from that version onward, up to `API_MAX_VERSION`.

**ViewSet note:** DRF `ModelViewSet` classes cannot be decorated directly with `@endpoint`: the decorator calls `as_view()` without an action mapping, while DRF ViewSets need one. ViewSets should normally be registered through a DRF router. A manually configured `ModelViewSet.as_view(actions)` callable can also be passed to the decorator for a specific route, but this does not replace the router's automatic route generation for all ViewSet actions.

## When each approach fits

**AcceptHeaderVersioning:** When the version must travel in the `Accept` header—common when the same URL is a stable resource identifier across versions and clients negotiate representation. View organization is independent; both shared and separate views are possible, with the caveat that separate views need dispatch inside the request pipeline since the URL alone cannot distinguish versions.

**URLPathVersioning:** When the version should be visible in the URL and you want DRF to populate `request.version` from a URL keyword argument. Use a dynamic version parameter (`path('api/<str:version>/users/', ...)`) so that `request.version` reflects the URL. Static paths per version work for routing but leave `request.version` at `DEFAULT_VERSION`.

**NamespaceVersioning:** When you want to use Django namespaces—for version-aware `reverse()` and URL organization. Namespaces can share a URLconf or use separate ones; the choice is architectural, not imposed by the scheme. `request.version` reflects the namespace of the matched URL.

**Version-range registration:** When you have three or more versions that build incrementally—most endpoints stay the same across releases, a few change per version. The cost of learning the library's registration rules and import-order requirement can be worthwhile when you want endpoint implementations to be registered only at the versions where they change, without maintaining separate version-specific URL configurations or branching logic.

For two versions that differ only in a serializer, any DRF scheme works with either view organization. For completely separate APIs (v1 and v2 serve different clients), `NamespaceVersioning` with separate URLconfs makes the separation explicit.

## Design principle

DRF's versioning classes handle version detection: they identify which version the client requested and expose it as `request.version`. They do not decide view organization: which view or view class handles that version. View organization is an architectural decision, and it interacts with the scheme you choose:

- **Shared views with branching** work with all three schemes. The scheme determines how `request.version` is populated; the shared view branches on it.
- **Separate views per version** work with all three schemes, but with different plumbing. `NamespaceVersioning` makes it natural (each namespace routes to its own views). `URLPathVersioning` supports it when a dynamic version parameter is used; with static paths per version, `request.version` stays at `DEFAULT_VERSION`. `AcceptHeaderVersioning` supports it only with dispatch inside the request pipeline, because the URL alone cannot distinguish versions.
- A **single URLconf included under multiple namespaces** is specific to `NamespaceVersioning`. It relies on Django's namespace-based URL organization and does not generalize to the other two schemes.
- **Version-range registration** treats view organization as a first-class concern. Each endpoint is registered at the version where it becomes active, and remains active across subsequent versions unless overridden. The registration layer—not the view layer—decides which endpoint-version pairs exist.

## Explore version-range registration

If you're comparing DRF versioning approaches and want to avoid view branching or per-version URLconf duplication, consider `django-api-versioning` on PyPI. The package implements version-range registration for `APIView` and generic views.

ViewSets are registered through DRF routers separately. See the integration project's URLconf in the package's repository for the router-based pattern, and the decorator source for the exact signature and version-range behavior.

The next articles show how to register endpoints correctly, handle version skipping, test versioned views, and manage deprecation.

Which versioning scheme do you use today? And which view organization—shared views or separate views—did you choose on top of it?
