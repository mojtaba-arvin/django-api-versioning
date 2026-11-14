---
slug: "023-django-api-versioning-installation-configuration"
title: "Install and Configure django-api-versioning"
description: "Install django-api-versioning, configure version boundaries, register endpoints, reverse versioned URLs, and verify routing with Django REST Framework."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "django-api-versioning"
  - "Django API versioning"
  - "Django REST Framework"
  - "Endpoint registration"
  - "API lifecycle"
---

# Install and Configure django-api-versioning

`django-api-versioning` registers versioned Django URL patterns through the `@endpoint` decorator. You declare an endpoint at its starting version, and the package generates its URL patterns through the configured maximum version. Later declarations can replace selected implementations without requiring a separate declaration for every unchanged endpoint.

This guide covers installation, version settings, endpoint registration, URL reversal, lifecycle middleware, and integration testing.

The package is maintained by the author of this article. For current release metadata and compatibility information, consult the package metadata and compatibility report linked below.

## Install

Install the package from [PyPI](https://pypi.org/project/django-api-versioning/):

```bash
pip install django-api-versioning
```

Check the installed version:

```bash
pip show django-api-versioning
```

### Python, Django, and DRF requirements

The package's runtime requirements are declared in its project metadata. Django REST Framework is not required to install the core package; it is used by the DRF integration examples and the project's development and testing setup.

For the current Python and Django requirements, see the [package metadata](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/pyproject.toml). For tested environment combinations, see the [compatibility report](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/COMPATIBILITY_REPORT.md).

If your project uses DRF, install it separately:

```bash
pip install djangorestframework
```

The development dependency does not define a supported DRF version range. Check the package's [current project metadata](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/pyproject.toml) and test the Python, Django, and DRF combination used by your application.

## Configure Django settings

The package provides defaults for its version settings:

| Setting | Default | Purpose |
| --- | --- | --- |
| `API_MIN_VERSION` | `1` | Lowest supported API version |
| `API_MAX_VERSION` | `1` | Highest supported API version |
| `API_BASE_PATH` | `"api/v{version}/"` | Versioned URL prefix template |

To register endpoints for v1 and v2, configure the version range:

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

Both settings are optional because they have defaults. However, `API_MAX_VERSION` must be raised when you register endpoints above the default maximum of v1.

For example, with `API_MAX_VERSION = 2`, an endpoint declared with `version=1` generates routes for both v1 and v2 unless a later declaration replaces the v2 implementation.

You can customize the URL prefix:

```python
API_BASE_PATH = "api/v{version}/"
```

This is the default. The pattern must contain `{version}` and is normalized to end with a slash.

The package uses integer version identifiers in Python configuration and decorator arguments. The `v` prefix belongs to the generated URL representation: `version=2` produces a `v2` URL segment.

See the [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md) for the complete rules governing version identifiers, URL construction, registration precedence, and supported view types.

## Configure the URLconf

Import the modules containing your `@endpoint` declarations before importing the package's URL patterns:

```python
# urls.py

from django.urls import include, path

from . import views  # noqa: F401
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The import order matters.

The `@endpoint` decorator registers routes when the module containing the decorated view is imported. The package's `urlpatterns` references the registry's URL patterns. If you import `api_urlpatterns` before importing the modules containing your views, their declarations have not executed yet and their routes will be missing.

If your endpoints are spread across several modules, import all of those modules before importing `api_urlpatterns`.

### Organize endpoint declarations by version

As an API grows, you can organize view modules by version and resource:

```text
api/
    views/
        __init__.py
        v1/
            __init__.py
            users.py
        v2/
            __init__.py
            users.py
    urls.py
```

The version directories are an application organization choice. They do not determine the generated URL. The decorator arguments, `API_BASE_PATH`, optional `app_name`, and `postfix` determine the route.

For this layout, import the declaration modules in `api/views/__init__.py`:

```python
# api/views/__init__.py

from .v1 import users as v1_users
from .v2 import users as v2_users
```

Then import `api.views` before the package URL patterns:

```python
# project/urls.py

from django.urls import include, path

from api import views  # noqa: F401
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The imports intentionally execute the decorators. They are not ordinary URL includes.

### Why mount at the root?

With the default `API_BASE_PATH`, the package already includes the `api/v{version}/` prefix.

Mounting its patterns at the root produces URLs such as:

```text
/api/v1/users/
/api/v2/users/
```

Do not mount the patterns under another `api/` prefix unless you intentionally want that prefix added to the generated paths.

The final URL combines the URLconf mount point with the route generated by the package.

## Register an endpoint

Import the decorator from the package's public API:

```python
from django_api_versioning import endpoint
```

Its public signature is:

```python
def endpoint(
    postfix: str,
    version: int | None = None,
    versions: list[int] | None = None,
    app_name: str | None = None,
    view_name: str | None = None,
) -> Callable[[ViewT], ViewT]:
    ...
```

The main arguments are:

- `postfix`: The endpoint path after the configured base path and optional `app_name` segment.
- `version`: The starting version. The endpoint is registered from this version through `API_MAX_VERSION`, inclusive.
- `versions`: An explicit list of versions. It cannot be used together with `version`.
- `app_name`: An optional path segment for grouping endpoints.
- `view_name`: An optional Django URL pattern name, used for URL reversal.

The following example registers a list endpoint and a detail endpoint for v1. The list implementation changes in v2, while the detail implementation remains unchanged.

```python
# views.py

from django_api_versioning import endpoint
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from .models import User
from .serializers import UserSerializerV1, UserSerializerV2


@endpoint("users/", version=1, view_name="user-list")
class UserListViewV1(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint(
    "users/<int:pk>/",
    version=1,
    view_name="user-detail",
)
class UserDetailViewV1(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


# Only the list endpoint changes in v2.
@endpoint("users/", version=2, view_name="user-list")
class UserListViewV2(UserListViewV1):
    serializer_class = UserSerializerV2
```

With `API_MIN_VERSION = 1` and `API_MAX_VERSION = 2`, the resulting URL patterns are:

| URL | Registered view |
| --- | --- |
| `/api/v1/users/` | `UserListViewV1` |
| `/api/v2/users/` | `UserListViewV2` |
| `/api/v1/users/<int:pk>/` | `UserDetailViewV1` |
| `/api/v2/users/<int:pk>/` | `UserDetailViewV1` |

The v1 list declaration generates both v1 and v2 routes. The later v2 declaration replaces the v2 implementation.

The detail declaration has no v2 replacement, so its implementation is carried forward.

**Now:**

- A request to `/api/v1/users/` is handled by `UserListViewV1`.
- A request to `/api/v2/users/` is handled by `UserListViewV2`.
- A request to `/api/v1/users/42/` is handled by `UserDetailViewV1`.
- A request to `/api/v2/users/42/` is also handled by `UserDetailViewV1`.

Python class inheritance and route carry-forward are separate mechanisms:

- `UserListViewV2` inherits Python behavior from `UserListViewV1`.
- The package generates the v2 detail route from the v1 declaration because no later declaration replaces it.

**Scope: routing only.** The package selects the view callable registered for each URL. It does not merge serializers, inherit business logic between unrelated view classes, or guarantee that the response contract remains backward compatible.

## Reverse URLs with `view_name`

If you want to reverse a URL by name, provide `view_name` in the endpoint declaration.

The package does not infer URL names from the Python class name or endpoint postfix. Without `view_name`, the URL pattern has no name for named reversal.

Import `api_reverse` from the package:

```python
from django_api_versioning import api_reverse
```

### Use one name across versions

You can use the same `view_name` for the same logical endpoint across multiple versions:

```python
api_reverse("user-list", version=1)
api_reverse("user-list", version=2)
```

The `version` argument selects the intended registered route.

For a name registered in multiple versions, omitting `version` raises the package's `AmbiguousVersionError`. The helper requires an explicit version because more than one route matches the name.

Django's standard `reverse()` function does not provide this package-specific version-selection argument. Use `api_reverse()` when you need to select a particular registered version.

### Use distinct names instead

Distinct names are an alternative to using one name across versions. Do not combine this alternative with the preceding declarations: replace the `view_name` values in those declarations with version-specific names.

For example, change the decorators to:

```python
@endpoint("users/", version=1, view_name="user-list-v1")
class UserListViewV1(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/", version=2, view_name="user-list-v2")
class UserListViewV2(UserListViewV1):
    serializer_class = UserSerializerV2
```

Then reverse each name without specifying a version:

```python
api_reverse("user-list-v1")
api_reverse("user-list-v2")
```

A name registered in exactly one version can be resolved without an explicit version. A name registered in multiple versions requires one.

## Register an explicit set of versions

Use `versions` when an endpoint should exist only in selected versions rather than every version from a starting point onward.

For example:

```python
@endpoint(
    "beta/",
    versions=[1, 2],
    view_name="beta-endpoint",
)
class BetaView(ListCreateAPIView):
    ...
```

This registers the endpoint for v1 and v2.

The list selects versions within the configured `API_MIN_VERSION`–`API_MAX_VERSION` range. It does not extend that range.

The validation behavior is important:

- A version below `API_MIN_VERSION` produces a warning and is skipped.
- A version above `API_MAX_VERSION` raises `InvalidVersionError`.
- Supplying both `version` and `versions` raises `VersionRangeError`.
- Version identifiers must be integers; booleans are not accepted as version values.

For example, `versions=[1, 3]` requires `API_MAX_VERSION` to be at least `3`.

## Group endpoints with `app_name`

The `app_name` argument inserts one path segment between `API_BASE_PATH` and the endpoint postfix.

```python
@endpoint(
    "reports/",
    version=1,
    app_name="internal",
)
class InternalReportView(ListCreateAPIView):
    ...
```

With the default base path, the resulting URL is:

```text
/api/v1/internal/reports/
```

`app_name` is a single grouping segment. It is not an arbitrary URL template and does not replace the endpoint's `postfix`.

## Configure API version lifecycle

Version registration and version lifecycle are separate concerns. The package provides `LifecycleMiddleware` for deprecation and sunset handling.

Configure lifecycle metadata in Django settings:

```python
# settings.py

API_VERSION_LIFECYCLE = {
    1: {
        "status": "deprecated",
        "sunset": "2027-06-01",
    },
    2: {
        "status": "active",
    },
}
```

The date above is an example future date relative to this article's publication. Replace it with the actual sunset date for your API before deploying the configuration.

Add the middleware to Django's `MIDDLEWARE` setting:

```python
MIDDLEWARE = [
    # Other middleware
    "django_api_versioning.lifecycle.LifecycleMiddleware",
]
```

For a request whose version has matching lifecycle metadata, the middleware behaves as follows:

| Lifecycle metadata | Behavior |
| --- | --- |
| `status="active"` | No lifecycle headers are added |
| `status="deprecated"` without `sunset` | Adds `Deprecation: true` to the downstream response |
| `status="deprecated"` with a future `sunset` | Adds `Deprecation: true` and a `Sunset` HTTP-date header |
| Any status with a past `sunset` | Returns `410 Gone` before calling the downstream view |
| `status="retired"` without a past `sunset` | Does not, by itself, return `410 Gone` |

The middleware identifies the version using this priority:

1. `request.version`, if it is already available.
2. `request.resolver_match.kwargs["version"]`, if the URL resolver provides it.
3. The static URL path, parsed using `API_BASE_PATH`.

For the package's generated segment-based URLs, the static path fallback allows the middleware to identify the version from paths such as `/api/v1/users/`.

There is an important integration detail for DRF: Django middleware runs before an `APIView` initializes DRF's request object and applies its versioning class. Do not assume that a DRF-populated `request.version` will be available to this middleware during the request's initial middleware phase. The package's static segment paths can be parsed through `API_BASE_PATH`.

### Deprecation header standards

The lifecycle middleware currently emits:

```http
Deprecation: true
```

This is a legacy draft-style value, not the date-based value specified by [RFC 9745](https://www.rfc-editor.org/rfc/rfc9745.html). Check the [current lifecycle implementation](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/lifecycle.py) for the exact header behavior. Applications requiring RFC 9745 compliance need to provide the appropriate date-valued header themselves or use an implementation that supports it.

The `Sunset` header is generated as an HTTP-date from the configured ISO date. The middleware returns `410 Gone` when the configured sunset date is in the past. That enforcement is based on the date, not on `status="retired"`.

The middleware does not add a `Link` header pointing to a deprecation policy or migration guide. If your API needs that link or RFC 9745-compliant deprecation metadata, implement the additional response behavior in your application.

## Verify the setup

A basic integration test can verify that the package registered the expected routes and that each version uses the intended serializer.

The following example assumes:

- Your test project has a `UserFactory` that creates a valid `User` record.
- The factory creates a user with a non-empty `phone` value.
- DRF pagination is configured with `PageNumberPagination`.
- `UserSerializerV1` does not expose `phone`, while `UserSerializerV2` does.

Configure pagination in Django settings:

```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "PAGE_SIZE": 10,
}
```

Then write the test:

```python
# tests/test_api_versions.py

from django.test import TestCase
from rest_framework.test import APIClient

from api.tests.factories import UserFactory


class APIVersioningTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        UserFactory()

    def test_v1_endpoint(self):
        response = self.client.get("/api/v1/users/")

        self.assertEqual(response.status_code, 200)

    def test_v2_endpoint(self):
        response = self.client.get("/api/v2/users/")

        self.assertEqual(response.status_code, 200)

    def test_v1_does_not_expose_phone(self):
        response = self.client.get("/api/v1/users/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("phone", response.data["results"][0])

    def test_v2_exposes_phone(self):
        response = self.client.get("/api/v2/users/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("phone", response.data["results"][0])
```

Replace the factory import with the factory used by your project. The important requirement is that the test database contains at least one valid user.

If your project uses a different pagination class or response structure, adapt the `response.data["results"]` assertions accordingly.

These tests verify both route availability and the serializer contract exposed by each version. A status-code-only test would not establish that v1 and v2 actually expose the intended response fields.

If both versioned requests return `200` but expose the same serializer fields, check the following:

1. The v2 view has its own `@endpoint` declaration.
2. The v2 declaration uses the expected `version`.
3. The module containing the v2 view is imported before `api_urlpatterns`.
4. `API_MAX_VERSION` includes v2.
5. The v2 view uses the intended serializer.

The package generates routes at registration time. A missing import or an incorrect version declaration can therefore result in a route that was never registered.

## What the package does not provide

`django-api-versioning` handles URL registration, provides `api_reverse()`, and includes lifecycle middleware. It does not implement every part of a production API versioning policy. See the [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md) for its routing responsibilities and limitations.

### Version discovery

The package does not provide a discovery endpoint such as `/api/versions/`.

If clients need to discover supported versions, implement an application-level endpoint that returns the version information clients need.

### OpenAPI documentation

The package does not generate OpenAPI documentation or automatically create separate API schemas for each version.

Use a documentation tool such as [drf-spectacular](https://drf-spectacular.readthedocs.io/en/latest/) or [drf-yasg](https://drf-yasg.readthedocs.io/en/stable/) and configure it for your application's versioning strategy.

### Direct ModelViewSet support

`@endpoint` does not support decorating a `ModelViewSet` class directly.

A `ModelViewSet` requires an action mapping when it is converted into a view. The package's class-based view registration calls `.as_view()` without such a mapping.

For resource-oriented ViewSets, keep a DRF router per version and mount the generated router URLs under the desired versioned prefixes:

```python
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register("users", UserViewSet, basename="user")
```

See the DRF documentation for [ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/) and [routers](https://www.django-rest-framework.org/api-guide/routers/).

A manually configured callable such as `UserViewSet.as_view({"get": "list"})` can be registered as an individual endpoint, but this does not replace router-based generation of the ViewSet's full set of routes and actions.

Use `APIView` or generic views with `@endpoint` when you want to register individual endpoint views. Keep router-managed ViewSets when their generated routes and action mappings are central to the resource.

### DRF request version configuration

The decorator registers URL patterns. It does not configure DRF's versioning class or automatically populate `request.version`.

In a standard DRF `APIView` without a configured versioning class, `request.version` is `None`.

If your views depend on `request.version`, configure DRF versioning separately and make sure its behavior is consistent with your URL structure. See the DRF documentation on [versioning](https://www.django-rest-framework.org/api-guide/versioning/).

## Migrate from manual per-version routers

If your project currently uses one `SimpleRouter` per API version, migration to `@endpoint` is a per-endpoint decision. The package is useful when you want to register individual endpoint views and carry unchanged routes forward without repeating their declarations.

### Before: one router per version

Assume `UserViewSetV1` and `UserViewSetV2` are existing `ModelViewSet` subclasses:

```python
# urls.py

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import UserViewSetV1, UserViewSetV2

v1_router = SimpleRouter()
v1_router.register(
    "users",
    UserViewSetV1,
    basename="v1-user",
)

v2_router = SimpleRouter()
v2_router.register(
    "users",
    UserViewSetV2,
    basename="v2-user",
)

urlpatterns = [
    path("api/v1/", include(v1_router.urls)),
    path("api/v2/", include(v2_router.urls)),
]
```

Each router generates its own route set. This is appropriate when the resource relies on ViewSet actions and router-generated URL patterns.

### After: register individual endpoint views

If the resource is suitable for generic views, you can replace its router-generated list and detail endpoints with individual declarations.

This is an alternative implementation of the same resource, not an additional set of declarations to keep alongside the router configuration.

```python
# views.py

from django_api_versioning import endpoint
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from .models import User
from .serializers import UserSerializerV1, UserSerializerV2


@endpoint("users/", version=1, view_name="user-list")
class UserListViewV1(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint(
    "users/<int:pk>/",
    version=1,
    view_name="user-detail",
)
class UserDetailViewV1(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/", version=2, view_name="user-list")
class UserListViewV2(UserListViewV1):
    serializer_class = UserSerializerV2


# UserDetailViewV1 is not redeclared for v2.
# Its v1 declaration already generates the v2 route.
```

Update the URL configuration:

```python
# urls.py

from django.urls import include, path

from . import views  # noqa: F401
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The example preserves the list and detail URL paths, but it does not preserve the original router's URL names. Update any reverse calls, tests, and references that depend on the old names.

Before migrating, check two things.

**ViewSets and custom actions need a different registration strategy.**

`@endpoint` cannot decorate a `ModelViewSet` class directly. If your project relies heavily on ViewSets and `@action` methods, keeping a router per version may be simpler.

You can convert selected resources to generic views, but that means representing each route as an individual view. A configured `ModelViewSet.as_view({...})` callable can also be registered for one route, but it does not replace the router's full route generation.

**The views import is required.**

The module containing the endpoint declarations must be imported before `api_urlpatterns`.

The import is intentional even if the imported module is not referenced directly in the URLconf. Its purpose is to execute the decorators and register the routes.

## Troubleshooting

### `VersionTypeError` or `VersionRangeError` during settings initialization

Check that both version settings are integers and that the minimum does not exceed the maximum:

```python
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

Booleans are not valid version values.

These exceptions are defined by the package in `django_api_versioning.exceptions`.

### `InvalidVersionError` during endpoint registration

A declaration uses a version greater than `API_MAX_VERSION`.

For example:

```python
@endpoint("beta/", version=3)
class BetaView(ListCreateAPIView):
    ...
```

requires:

```python
API_MAX_VERSION = 3
```

Raising `API_MAX_VERSION` does not automatically create a new implementation for every endpoint. Existing declarations are carried forward, and new declarations can replace selected routes.

### `AmbiguousVersionError` from `api_reverse()`

This error occurs when the same `view_name` is registered for multiple versions and `api_reverse()` is called without an explicit version.

For example:

```python
api_reverse("user-list")
```

If `user-list` is registered for v1 and v2, select the intended route:

```python
api_reverse("user-list", version=2)
```

The exception is defined by the package and can be imported from:

```python
from django_api_versioning.exceptions import AmbiguousVersionError
```

### `NoReverseMatch` from `api_reverse()`

`NoReverseMatch` means the requested name/version combination cannot be resolved, or the registered route cannot be reversed with the supplied arguments.

Check that:

- The endpoint declaration includes `view_name`.
- The requested version is actually registered for that name.
- All required path-converter arguments are supplied.
- The route uses a supported `path()`-based pattern.

For example, a detail route containing `<int:pk>` requires the `pk` argument:

```python
api_reverse("user-detail", version=2, pk=42)
```

Do not confuse this error with `AmbiguousVersionError`: an ambiguous name has multiple registered versions and requires an explicit version.

### 404 on `/api/v2/users/`

Check the URL configuration and import order:

```python
from . import views
from django_api_versioning.urls import urlpatterns as api_urlpatterns
```

Also verify that:

- `API_MAX_VERSION` is at least `2`.
- The endpoint's starting version is not above the configured maximum.
- The module containing the endpoint declaration is imported.
- The URLconf mounts `api_urlpatterns` at the intended path.
- The endpoint postfix and configured base path produce the URL being requested.

### `AttributeError` for an unknown package attribute

The package's public API exports:

```python
from django_api_versioning import (
    api_reverse,
    endpoint,
    ver_range,
)
```

Do not assume that internal or third-party names such as `VersionedEndpoint` and `register_versioned_routers` are part of the package's public API. Verify available imports against the package's current public exports.

Check your imports against the [package exports](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/__init__.py), [decorator implementation](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/decorators.py), and [reverse implementation](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/reverse.py).

## Trade-offs and scope

**What the package simplifies:** unchanged endpoints do not need separate declarations for every API version. A declaration at v1 can generate routes through `API_MAX_VERSION`, while later declarations replace selected implementations.

**What it does not reduce:** the number of runtime URL patterns. For the same API surface, the application still needs the corresponding versioned routes.

**When the benefit is smaller:** a single-version API with no plans for additional versions may be simpler with a hand-written URLconf. A project built primarily around `ModelViewSet` classes may also be better served by DRF routers.

The package is most useful when you want to manage individual endpoint implementations across multiple URL-based API versions without repeating declarations for unchanged endpoints. Its route carry-forward behavior should be paired with explicit version-matrix and response-contract tests.

## Next steps

Install `django-api-versioning`, configure the version range, import the endpoint declaration modules before the generated URL patterns, and test the route and response contract for each supported version. The package handles route registration and lifecycle enforcement; discovery and OpenAPI schema generation remain application-level or documentation-tool responsibilities.

For the implementation and version-specific source, see the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
