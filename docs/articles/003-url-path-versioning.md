---
slug: "003-url-path-versioning"

title: "URL path-based versioning: explicit routes and inheritance patterns"

description: "Compare explicit Django URL patterns, DRF URLPathVersioning, and declarative route registration for APIs that evolve across URL versions."

author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"

keywords:
  - "URL path API versioning"
  - "Django URL routing"
  - "DRF URLPathVersioning"
  - "endpoint inheritance"

---

# URL path-based versioning: explicit routes and inheritance patterns

URL path versioning makes the API version visible in the request URL:

```http
GET /api/v1/users/
GET /api/v2/users/
```

The version segment gives clients an explicit contract boundary. In Django, however, the URL design and the choice of view implementation are separate decisions. You can write explicit URL patterns, reuse views across patterns, branch inside a DRF view using `request.version`, or use a registration layer that generates versioned routes.

This article compares those approaches and explains where declarative endpoint registration reduces maintenance—and where ordinary Django routing is already sufficient.

## 1. Explicit URL patterns

The most direct approach is to map each versioned URL to a view:

```python
# urls.py
from django.urls import path

from .views import UserListV1, UserListV2

urlpatterns = [
    path("api/v1/users/", UserListV1.as_view(), name="v1-user-list"),
    path("api/v2/users/", UserListV2.as_view(), name="v2-user-list"),
]
```

The mapping is visible and easy to trace. Each route points to a specific implementation, and Django's URL resolver performs the dispatch.

The view classes can share implementation through ordinary Python inheritance:

```python
# views.py
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.generics import ListAPIView


class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class UserListV1(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


class UserListV2(UserListV1):
    serializer_class = UserSerializerV2
```

Here, `UserListV2` inherits Python behavior from `UserListV1` and changes the serializer. The URL configuration still explicitly maps each version to its view.

That distinction matters: **Python class inheritance reuses implementation; it does not generate or inherit URL patterns.**

### Reusing URL configuration

A fully repeated URLconf is not the only manual option. Django lets you compose and reuse URL patterns with `include()`, and multiple patterns can point to the same view callable when the behavior is intentionally shared.

For example, if an endpoint has not changed, both versioned paths can use the same view:

```python
from django.urls import include, path

from .views import UserListV1, UserListV2, PostList

urlpatterns = [
    path(
        "api/v1/",
        include([
            path("users/", UserListV1.as_view(), name="v1-user-list"),
            path("posts/", PostList.as_view(), name="v1-post-list"),
        ]),
    ),
    path(
        "api/v2/",
        include([
            path("users/", UserListV2.as_view(), name="v2-user-list"),
            path("posts/", PostList.as_view(), name="v2-post-list"),
        ]),
    ),
]
```

This still declares the versioned URL mappings explicitly, but it does not require a separate implementation for every endpoint in every version. The trade-off is that the URLconf remains responsible for expressing which implementation is exposed at each version.

Django's official documentation covers [URL dispatcher patterns](https://docs.djangoproject.com/en/stable/topics/http/urls/) and [including other URLconfs](https://docs.djangoproject.com/en/stable/topics/http/urls/#including-other-urlconfs).

## 2. DRF URLPathVersioning

Django REST Framework provides `URLPathVersioning` to extract a version from a dynamic URL path parameter and expose it as `request.version`.

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "rest_framework.versioning.URLPathVersioning"
    ),
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ("v1", "v2"),
}
```

A view can use that value to select version-specific behavior:

```python
# views.py
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.generics import ListAPIView


class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class UserList(ListAPIView):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.version == "v1":
            return UserSerializerV1
        return UserSerializerV2
```

The URL pattern uses a converter whose name matches DRF's default `VERSION_PARAM`:

```python
# urls.py
from django.urls import path

from .views import UserList

urlpatterns = [
    path("api/<str:version>/users/", UserList.as_view()),
]
```

The URL resolver passes the captured `version` keyword argument to the view, and DRF's versioning class uses it to set `request.version`.

This is different from static patterns such as `api/v1/users/` and `api/v2/users/`. Those patterns do not provide a dynamic `version` keyword argument. With static segments, `URLPathVersioning` therefore falls back to `DEFAULT_VERSION`; the URLconf may still dispatch to separate views, but `request.version` will not automatically reflect the static segment.

DRF's versioning classes identify the request's version. Your application decides how that value changes behavior—for example, by selecting a serializer, branching in a view, or delegating to a version-specific handler. They do not generate a separate route table or choose a different view implementation automatically.

See the official [DRF versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/#urlpathversioning).

## 3. Declarative route registration with `django-api-versioning`

A third option is to keep version-specific view implementations while declaring their route registrations with `@endpoint`. The package builds the versioned URL patterns from those declarations.

The example below uses DRF `APIView` classes, which the package supports. It deliberately does not use a `ViewSet`: direct decoration of DRF ViewSets is not supported because a ViewSet needs the action mapping normally supplied by a router.

### Configure the package

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django_api_versioning",
]

API_BASE_PATH = "api/v{version}/"
API_MAX_VERSION = 3
```

The version identifiers used by this package are integers. With the default base path, version `2` becomes the URL segment `v2`; the string identifier `"v2"` used by DRF is a different convention.

### Declare endpoint implementations

```python
# views.py
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from django_api_versioning.decorators import endpoint


User = get_user_model()


class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


@endpoint("users/", version=1)
class UserListV1(APIView):
    def get(self, request):
        users = User.objects.all()
        return Response(UserSerializerV1(users, many=True).data)


@endpoint("users/", version=2)
class UserListV2(APIView):
    def get(self, request):
        users = User.objects.all()
        return Response(UserSerializerV2(users, many=True).data)
```

The first `users/` declaration registers the v1 implementation from version 1 through `API_MAX_VERSION`. The v2 declaration replaces that implementation from version 2 onward. As a result, v1 uses `UserListV1`, while v2 and v3 use `UserListV2`.

The function or class name is not used to construct the URL. The URL is derived from `API_BASE_PATH` and the endpoint's `postfix` (plus `app_name` when supplied). The names `UserListV1` and `UserListV2` are conventions for readers; the `version` argument controls registration.

### Include the generated patterns

The endpoint modules must be imported before the package's URL patterns are evaluated. The decorators register endpoints when those modules are imported.

```python
# project/urls.py
from django.urls import include, path

from api import views  # noqa: F401 — import runs the endpoint declarations
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

With `API_BASE_PATH = "api/v{version}/"`, the resulting mapping is:

**Now:**

- `/api/v1/users/` → `UserListV1`
- `/api/v2/users/` → `UserListV2`
- `/api/v3/users/` → `UserListV2`

The package applies a deterministic registration rule when multiple implementations target the same endpoint and version: the registration with the higher integer `source_version` takes precedence; if the source versions are equal, the last registration wins.

For the full contract—including identifier types, URL construction, import order, registration precedence, and supported view types—see the [canonical versioning reference](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

**Scope: routing only.** Registration inheritance determines which view is reachable at a versioned URL. It does not prove that the selected view's response remains semantically backward-compatible, nor does it manage serializer compatibility, database migrations, or OpenAPI schema evolution. Those remain application-level responsibilities.

## 4. What changes as the API grows?

Consider an API with 10 logical endpoints and three URL versions. Suppose all 10 endpoints exist in v1, two endpoints receive new implementations in v2, and no endpoint changes in v3.

There are 30 endpoint-version slots in the resulting API surface: 10 endpoints multiplied by 3 versions.

The amount of source configuration depends on the strategy:

- **Fully explicit per-version URLconfs:** up to 30 route declarations if every endpoint-version mapping is written separately.
- **Reusable manual URL patterns:** fewer declarations may be possible by composing shared patterns or pointing multiple paths to the same view. The URLconf still expresses the mappings that are not shared.
- **DRF `URLPathVersioning`:** a shared dynamic route can serve all three versions, while the view or delegated handlers contain the version-dependent behavior. The number of branches depends on how many endpoints actually differ.
- **Declarative endpoint registration:** 10 initial declarations plus 2 overrides can describe the same three-version mapping when `version=1` carries the original implementation forward and the v2 declarations replace only the changed endpoints. The registry expands those declarations into the 30 route slots.

These are different measures: route declarations, view implementations, conditional branches, and generated URL patterns are not interchangeable counts. The package reduces repeated registration declarations in this scenario; it does not reduce the number of URLs clients can call or eliminate the need to test the supported version matrix.

A version-directory layout can also help teams keep substantial implementation differences organized:

```text
api/
    v1/
        users.py
        posts.py
    v2/
        users.py
```

That is an application organization choice, not a package requirement. The package's role is to map the selected endpoint implementations to versioned routes; it does not impose a directory structure or discover modules from version-named folders. The project must still import the modules that contain the endpoint declarations before including the generated URL patterns.

## 5. Comparison

| Concern | Explicit Django URL patterns | DRF `URLPathVersioning` | `django-api-versioning` |
| --- | --- | --- | --- |
| Version source | Static or dynamic URL patterns | Dynamic URL path parameter | Integer registration version formatted into the URL |
| Route-to-view mapping | Written in URLconf | Usually one route; application chooses behavior | Declared with `@endpoint` |
| Different view per version | Explicit URL mapping | Application-level dispatch or separate URL patterns | Register an implementation for the relevant version |
| Reuse unchanged endpoints | Reuse views and URL patterns manually | Share view logic or handlers | Earlier implementation carries forward through the configured range |
| Version identifier | Whatever the URLconf defines | String from the configured URL parameter | Integer |
| Works without DRF | Yes | No | Yes |
| Direct DRF ViewSet registration | Use a DRF router | Use a DRF router | Not supported; mount router URLs separately |

No approach is universally best. Explicit URL patterns are transparent and remain a strong choice when the route table is small or versions differ substantially. DRF's versioning classes are appropriate when a shared route and application-level version dispatch match the design. Declarative registration is useful when many endpoints remain unchanged across successive versions and maintaining each mapping by hand becomes repetitive.

## Trade-offs and scope

The package introduces a registry and a set of rules that developers must understand: integer version identifiers, endpoint import order, URL construction, and registration precedence. That is additional machinery compared with a short URLconf.

For each endpoint and target version, the registry uses the applicable registration with the highest source version. In practical terms, an implementation registered at v2 takes precedence over one registered at v1 for v2 and later versions covered by that registration. If registrations have the same source version, the last registration wins. This is route-registration inheritance—not Python class inheritance and not a guarantee of semantic API compatibility.

In return, the application can express the version-to-view mapping at the endpoint declaration and let the package generate the route table. This is most valuable when versions evolve incrementally and most endpoints continue using an earlier implementation.

**When the benefit is smaller:** For two stable versions with only a few endpoints, or for APIs whose versions have fundamentally different endpoint sets, explicit Django routing may be easier to inspect and maintain. A routing abstraction should earn its place through reduced repeated configuration, not simply because an API has reached a particular version number.

## Getting started

If your API has a growing set of URL-versioned endpoints and you want to declare only the implementations that change, explore [`django-api-versioning` on PyPI](https://pypi.org/project/django-api-versioning/).
