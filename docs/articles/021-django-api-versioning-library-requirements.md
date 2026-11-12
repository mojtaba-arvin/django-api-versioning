---
slug: "021-django-api-versioning-production-requirements"
title: "Production Evaluation of django-api-versioning"
description: "Evaluate django-api-versioning v0.3.5 through route inheritance, version isolation, lifecycle handling, routing inspection, and regression tests."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"

keywords:
  - "Django API versioning"
  - "Django REST Framework"
  - "Versioned routing"
  - "API lifecycle management"
  - "Routing regression testing"

---

# Production Evaluation of django-api-versioning

A production API versioning strategy needs more than a version number in a URL. The application must resolve each version to the intended view, preserve older response contracts, expose a predictable routing structure, and manage the eventual retirement of older versions.

This article evaluates those requirements through **django-api-versioning v0.3.5**. Rather than treating versioned routing as a collection of manually maintained URL patterns, it examines how the package's declarative registration model works, what it automates, and which production responsibilities remain with the application.

The package provides:

- Declarative endpoint registration for function-based and supported class-based views.
- Version-range registration and explicit version selection.
- Route inheritance when a new API version is introduced.
- Version-aware reverse lookup.
- Routing inspection and snapshot-based regression protection.
- Configurable lifecycle middleware for deprecation headers and sunset enforcement.

**Scope: routing and its supporting lifecycle behavior.** The package does not enforce semantic backward compatibility, coordinate client migrations, or replace application-level contract tests.

The author maintains `django-api-versioning`. The examples and package-specific claims in this article refer to v0.3.5.

Install the package from [PyPI](https://pypi.org/project/django-api-versioning/).

## 1. Start with the routing model

The package's central abstraction is a versioned endpoint declaration:

```python
from django_api_versioning import endpoint
```

The decorator registers a view against a resource path and one or more API versions. The package then builds Django URL patterns from those declarations.

With the default configuration:

```python
API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

this declaration:

```python
@endpoint("users/", version=1, view_name="user-list")
class UserListView(ListAPIView):
    ...
```

produces these versioned paths:

```text
/api/v1/users/
/api/v2/users/
```

The path is derived from three elements:

1. `API_BASE_PATH`, formatted with the integer version.
2. The optional `app_name` segment.
3. The endpoint's `postfix`, here `"users/"`.

The Python class name does not determine the URL path or URL name. Use `view_name` when the route needs an explicit Django URL pattern name.

The package's registration rules, import paths, version identifiers, route construction, and ViewSet boundary are documented in the [canonical versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md). That document is the reference for package-specific routing semantics used throughout this article.

## 2. Route inheritance and version-specific implementations

A production routing design should make it clear which implementation handles a request for each supported version.

### Register a new implementation without duplicating every route

Consider an API with two versions of the users endpoint:

```python
from django_api_versioning import endpoint
from rest_framework.generics import ListAPIView

from .models import User
from .serializers import UserSerializerV1, UserSerializerV2


@endpoint("users/", version=1, view_name="user-list")
class UserListV1(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV1


@endpoint("users/", version=2, view_name="user-list")
class UserListV2(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerV2
```

With `API_MIN_VERSION = 1` and `API_MAX_VERSION = 2`, the routing matrix is:

| Request | Registered handler |
| --- | --- |
| `/api/v1/users/` | `UserListV1` |
| `/api/v2/users/` | `UserListV2` |

The declarations use the same `postfix` and `view_name`, but different source versions. The newer declaration replaces the older implementation for v2. The v1 route continues to use `UserListV1`.

This is route-registration inheritance, not Python class inheritance. The registry selects which view callable is attached to each generated URL. It does not create subclasses, merge serializers, or copy methods between views.

### The inheritance traversal rule

For a request to version N, the effective implementation is the registered implementation with the highest source version that is less than or equal to N.

In other words, resolution starts at the requested version and moves toward lower source versions until it reaches the applicable registration. It does not search toward newer versions.

For example, consider these declarations:

```python
@endpoint("orders/", version=1, view_name="order-list")
def order_list_v1(request):
    return JsonResponse({"implementation": "v1"})


@endpoint("orders/", version=3, view_name="order-list")
def order_list_v3(request):
    return JsonResponse({"implementation": "v3"})
```

With `API_MIN_VERSION = 1` and `API_MAX_VERSION = 4`, the effective routing matrix is:

| Requested version | Handler |
| --- | --- |
| v1 | `order_list_v1` |
| v2 | `order_list_v1` |
| v3 | `order_list_v3` |
| v4 | `order_list_v3` |

**Now:**

- A request to v1 resolves to `order_list_v1`.
- A request to v2 resolves to `order_list_v1`.
- A request to v3 resolves to `order_list_v3`.
- A request to v4 resolves to `order_list_v3`.

The explicit routing matrix matters: inheritance through an unchanged version and replacement by a newer declaration are different cases.

### Release a new version without changing every endpoint

Suppose the application initially has:

```python
API_MIN_VERSION = 1
API_MAX_VERSION = 2
```

and an endpoint registered with `version=1`.

When the application introduces v3, increasing the maximum:

```python
API_MAX_VERSION = 3
```

extends that endpoint's registration to v3. The existing implementation continues to serve the new version unless a newer declaration overrides it.

This is useful when a new API version is introduced but most endpoints retain their existing contracts. Only endpoints that need a different implementation require new declarations.

The alternative is not necessarily duplicating business logic. A manually maintained URL configuration can point several versioned paths to the same view. The package's benefit is reducing repeated registration declarations and making the effective version-to-view mapping explicit in a central registry.

### Distinguish a missing endpoint from a missing API version

Explicit version registration is available when an endpoint should exist only in selected versions:

```python
@endpoint(
    "reports/",
    versions=[1, 3],
    view_name="report-list",
)
def report_list(request):
    return JsonResponse({"reports": []})
```

This registers the endpoint for v1 and v3, but not v2.

There are two different situations to distinguish:

- **The API version does not exist in the configured range.** For example, v4 is outside a configuration whose maximum is 3.
- **The API version exists, but this endpoint is not registered for it.** In the example above, v2 exists as an API version, but the reports endpoint has no v2 route.

A request to an unregistered endpoint/version combination does not become valid merely because the API version itself is supported.

Use `version=N` for a continuous segment of versions and `versions=[...]` when the endpoint must exist only in explicitly selected versions.

## 3. Version isolation is an application responsibility

Route selection does not guarantee response-contract isolation.

For example, separate serializers allow an application to evolve a response:

```python
class UserSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name"]


class UserSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "display_name"]
```

The v2 view can use `UserSerializerV2` while v1 continues to use `UserSerializerV1`.

However, separate serializer classes do not isolate shared dependencies. Changes to a model field, permission class, shared base class, or utility function can still affect both versions.

A useful project structure is to keep version-specific API code organized explicitly:

```text
api/
    v1/
        serializers.py
        views.py
    v2/
        serializers.py
        views.py
```

This is an application organization convention, not a directory structure required by the package. `@endpoint` connects the version-specific view implementations to the generated routing structure.

For each version, test the actual response contract. Review changes to shared dependencies and database schemas while older versions remain active.

## 4. Supported view types and the DRF ViewSet boundary

The package supports function-based views and supported Django class-based views, including DRF's `APIView` and `GenericAPIView`.

A DRF ViewSet class is different. It requires an action mapping when converted into a view callable. The package's registry calls `as_view()` on a class without supplying that mapping, so decorating a `ModelViewSet` class directly with `@endpoint` is not supported.

For resource-oriented ViewSets, use DRF's [ViewSet documentation](https://www.django-rest-framework.org/api-guide/viewsets/) and [router documentation](https://www.django-rest-framework.org/api-guide/routers/). Register the ViewSet with a DRF router and mount the resulting router URLs under the appropriate versioned prefixes.

A manually configured callable such as:

```python
UserViewSet.as_view({"get": "list"})
```

represents a specific route/action mapping. It is not automatic router integration and does not replace the router-generated list, detail, and custom-action routes.

Likewise, an `@action` method does not automatically become a version-specific endpoint through `@endpoint`.

These are concrete boundaries of the package's integration model. They are not a general incompatibility between DRF routers and versioned URLs. The [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md#supported-view-types-and-the-viewsetrouter-boundary) describes the supported view types and the recommended boundary.

## 5. Reverse lookup and request version

### Generate a URL for a specific version

The package provides `api_reverse()` for version-aware URL generation:

```python
from django_api_versioning import api_reverse

url = api_reverse("user-list", version=2)
```

The endpoint must have been registered with the corresponding `view_name`.

When multiple matching versions exist and no version is supplied, the package raises `AmbiguousVersionError`. This avoids silently selecting one of several registered versioned routes.

If no matching route exists, `api_reverse()` raises Django's `NoReverseMatch`.

Use an explicit version when the application needs a deterministic version-specific URL.

### Do not assume that `request.version` is populated

The package registers version-specific URL patterns. Its `@endpoint` decorator does not itself populate DRF's `request.version`.

A request to `/api/v1/users/` can resolve to the v1 view without `request.version` being set.

DRF's `URLPathVersioning` expects a URL keyword argument named `version`. The package's default static paths, such as `/api/v1/users/`, are not dynamic URL patterns containing `<int:version>`.

If application code needs `request.version`, configure a compatible extraction mechanism and test it against the actual URL patterns. Do not assume that enabling `URLPathVersioning` alone is sufficient.

The distinction is:

- `django-api-versioning` selects the registered view through its generated URL patterns.
- DRF's versioning scheme determines how a request version is extracted and exposed through `request.version`.

## 6. Inspect and protect the routing matrix

Declarative registration is more useful in production when the effective routing configuration can be inspected and reviewed.

### Inspect registered routes

The package provides the `check_versions` management command:

```bash
python manage.py check_versions
```

It displays the registered routing matrix, including the route and the view callback associated with each version. It also warns when a route has gaps within the configured version range.

For example, an endpoint explicitly registered for v1 and v3 may produce a warning for v2. That warning is evidence to review, not necessarily a defect: the omission may be intentional.

Run the command after the modules containing `@endpoint` declarations have been imported. The registry is populated when those modules are imported.

### Protect the routing configuration with a snapshot

The package also provides `assert_version_matrix()` through `django_api_versioning.testing`.

First, generate the initial snapshot deliberately:

```python
from django_api_versioning.testing import assert_version_matrix

assert_version_matrix(
    snapshot=".version_matrix.json",
    update=True,
)
```

Review the generated file and commit it to version control.

Then use the assertion in the test suite:

```python
from django_api_versioning.testing import assert_version_matrix


def test_version_matrix():
    assert_version_matrix(snapshot=".version_matrix.json")
```

If the current routing matrix differs from the committed snapshot, the assertion raises `VersionMatrixError` and reports the differences.

There is an important setup detail: if the snapshot does not exist, `assert_version_matrix()` creates it. Therefore, the first execution does not prove that a previously approved routing configuration has remained unchanged. Generate and commit the baseline before relying on the test as regression protection.

The snapshot protects route registration, not response semantics. It cannot prove that serializers, permissions, filtering, pagination, or business behavior remain compatible.

## 7. API lifecycle handling

Routing and lifecycle management are related, but they are not the same responsibility.

An application may need to communicate that a version is deprecated and eventually reject requests to it. The relevant HTTP standards include [RFC 9745 for the Deprecation response header](https://www.rfc-editor.org/rfc/rfc9745) and [RFC 8594 for the Sunset HTTP header](https://www.rfc-editor.org/rfc/rfc8594).

`django-api-versioning` v0.3.5 provides `LifecycleMiddleware` and the `API_VERSION_LIFECYCLE` setting for configured lifecycle behavior.

For example, an application can define lifecycle metadata:

```python
# settings.py

API_VERSION_LIFECYCLE = {
    1: {
        "status": "deprecated",
        "sunset": "YYYY-MM-DD",
    },
    2: {
        "status": "active",
    },
}
```

Add the middleware to Django's `MIDDLEWARE` setting:

```python
MIDDLEWARE = [
    # Other middleware
    "django_api_versioning.lifecycle.LifecycleMiddleware",
]
```

Replace the date placeholder with the actual planned sunset date before deployment.

The middleware can identify the version from the request and, when necessary, extract it from the package's static URL path. It does not require DRF's `request.version` to be populated for that path-based extraction.

The v0.3.5 behavior has important details:

- A version with `status: "deprecated"` receives a `Deprecation` response header.
- If a sunset date is configured for that deprecated version, the middleware also sends a `Sunset` header.
- The current implementation sends `Deprecation: true`. This is a legacy draft-era value, not the date value specified by RFC 9745. Applications requiring RFC 9745 conformance should account for this limitation.
- When the configured sunset date has passed, the middleware returns `410 Gone`.
- A `retired` status by itself does not trigger `410 Gone`; the configured sunset date must have passed.
- A future sunset date combined with `retired` status does not produce the same deprecation headers as `deprecated`.

The middleware implements technical lifecycle behavior. The application team still owns the retirement policy, date selection, client communication, usage monitoring, and migration plan.

For a more focused implementation discussion, see [How to deprecate old Django REST API versions with Sunset headers](/deprecate-old-django-api-versions-sunset-headers/).

## 8. Version discovery and API documentation

A versioned routing system should not make clients guess which versions or endpoints are available.

An application may expose a discovery endpoint such as `/api/versions/`, but it should not blindly report every integer between `API_MIN_VERSION` and `API_MAX_VERSION` as an endpoint-level capability.

For example:

```python
@endpoint(
    "reports/",
    versions=[1, 3],
    view_name="report-list",
)
def report_list(request):
    return JsonResponse({"reports": []})
```

The configured range may include v2, but this endpoint is not registered for v2.

If clients need endpoint-level discovery, derive the response from a verified routing matrix or maintain an explicit application-level policy. `django-api-versioning` v0.3.5 does not provide a built-in version-discovery endpoint.

API documentation is a separate concern as well. Tools such as [drf-spectacular](https://drf-spectacular.readthedocs.io/) and [drf-yasg](https://drf-yasg.readthedocs.io/) generate API documentation. Registering multiple URL patterns does not automatically guarantee correctly separated OpenAPI documents for each version.

Configure and test the documentation tool for the version-specific schemas the application intends to publish.

## 9. URLconf integration and migration

The package's decorators register routes when the modules containing them are imported. Import those modules before importing the package's URL patterns.

For example:

```python
# project/urls.py

from django.urls import include, path

from accounts import views as account_views
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The `account_views` import is intentional: importing the module executes its endpoint declarations and populates the registry.

For an existing application, a migration should compare the previous URL configuration with the generated routing matrix:

1. Identify the existing version-to-view mapping.
2. Add `@endpoint` declarations to the relevant views.
3. Import the declaration modules before the package URL patterns.
4. Inspect the generated matrix with `check_versions`.
5. Compare representative requests and response contracts across supported versions.
6. Commit a routing snapshot if the project needs regression protection.

A migration is not complete merely because Django starts successfully. Existing URLs, reverse lookup behavior, response contracts, and permissions must continue to match the application's intended behavior.

## 10. Trade-offs and scope

The package's main benefit is declarative route registration with explicit version inheritance. It reduces repeated registration declarations when endpoints remain unchanged across API versions and makes the effective routing matrix inspectable.

That benefit comes with a responsibility: a declaration using `version=N` carries the implementation forward through `API_MAX_VERSION`. If an endpoint's contract changes, the team must decide whether to add a newer implementation or use explicit version registration.

A newer implementation does not retroactively fix older overrides. If v2 has its own implementation, changing the v1 implementation does not replace the v2 route.

The package also does not:

- Enforce backward compatibility between serializers, views, or database schemas.
- Populate DRF's `request.version` by itself.
- Decorate DRF ViewSet classes directly.
- Automatically register `@action` methods or integrate with DRF routers.
- Generate separate OpenAPI schemas for every API version.
- Provide a built-in version-discovery endpoint.
- Decide deprecation policy or coordinate client migration.
- Guarantee deployment safety or rollback.

**When the benefit is smaller:** if an API has very few versioned endpoints, rarely introduces new versions, and its existing URL configuration is already straightforward to maintain, adopting a separate registration model may add more complexity than it removes.

The useful evaluation is not whether the package replaces every part of API versioning. It is whether declarative registration, route inheritance, version-aware reverse lookup, routing inspection, regression protection, and configured lifecycle behavior address the specific maintenance problems in the application.

## 11. Production verification checklist

Use this checklist when integrating `django-api-versioning` into a production project:

| Area | Verification |
| --- | --- |
| Version registration | Each declaration generates the intended versioned paths |
| Route inheritance | Requests resolve to the expected source-version implementation |
| Explicit versions | Endpoints are absent from versions not listed in `versions=[...]` |
| Version boundaries | `API_MIN_VERSION` and `API_MAX_VERSION` match the intended release range |
| View support | The registered callable is a supported function or class-based view |
| ViewSet boundary | Router-generated ViewSet routes are mounted separately |
| URL construction | The generated path matches `API_BASE_PATH`, `app_name`, and `postfix` |
| Reverse lookup | `api_reverse()` generates the intended version-specific URL |
| Request version | Any required `request.version` extraction is configured and tested |
| Contract isolation | Each version returns the intended response fields and behavior |
| Lifecycle headers | Deprecation behavior matches the application's requirements |
| Sunset enforcement | Requests after the configured sunset date receive the expected response |
| Routing inspection | `check_versions` output has been reviewed |
| Routing regression | The approved version matrix snapshot is committed and checked in CI |
| Documentation | Each published OpenAPI document describes the intended version |
| Migration | Existing URLs and response contracts remain correct |
| Deployment | Version rollout, client migration, retirement, and rollback have defined owners |

The package supplies concrete mechanisms for the routing-related rows. The remaining application and operational requirements need their own implementation and tests.

## Next step

If your project uses Django and DRF and its versioned URL registrations are becoming repetitive, evaluate the v0.3.5 registration model against your current route matrix. Start with the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning), review the canonical routing contract, and verify the generated matrix before migrating production routes.
