---
slug: "001-django-api-versioning-packages"
title: "Django API versioning: choosing a routing model"
description: "Compare manual Django routing, DRF version detection, and version-range registration for APIs whose endpoint implementations evolve over time."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "Django API versioning"
  - "DRF versioning"
  - "versioned URL routing"
  - "endpoint registration"
---

# Django API versioning: choosing a routing model

> **Assessment:** Package behavior in this article is verified against `django-api-versioning` 0.3.5 on 2026-11-12. The author is also the package maintainer; package-specific claims link to the source and canonical contract reference.

## The architectural question

An API version is a public contract, not merely a URL prefix. A versioning design must preserve the behavior promised to existing clients while allowing newer versions to introduce deliberate changes. Routing is one part of that design: it determines which implementation handles a request. It does not by itself guarantee compatibility of serializers, permissions, filtering, pagination, error formats, or generated schemas.

In Django projects, three concerns are often conflated:

1. **Version identification:** how the request communicates which version it targets.
2. **View organization:** whether versions share a view, branch inside a view, or use separate view classes.
3. **Route registration:** how URL patterns map versioned paths to the selected implementations.

Django REST Framework (DRF) provides version-identification schemes. Django provides URL routing and namespacing. A separate registration layer can automate mapping endpoint implementations to version ranges. These are related choices, but they are not interchangeable.

## Option 1: explicit Django URL patterns

For a small API, explicit URL patterns can be the clearest solution. A project can place version-specific views in separate modules and mount each module under a version prefix.

A simple project structure might be:

```text
accounts/
    api/
        v1/
            views.py
            serializers.py
        v2/
            views.py
            serializers.py
project/
    urls.py
```

The URL configuration can then make the mapping visible:

```python
# project/urls.py
from django.urls import include, path

from accounts.api.v1 import views as v1_views
from accounts.api.v2 import views as v2_views

urlpatterns = [
    path(
        "api/v1/",
        include([
            path("users/", v1_views.UserListV1.as_view(), name="v1-user-list"),
        ]),
    ),
    path(
        "api/v2/",
        include([
            path("users/", v2_views.UserListV2.as_view(), name="v2-user-list"),
        ]),
    ),
]
```

This is explicit and easy to inspect. It does not require a package. The cost appears when many endpoints remain unchanged across versions: each version's URL configuration still needs to include the routes that should exist in that version. Reusing the same view callable across multiple URL patterns is valid, so explicit routing does **not** inherently require duplicate view implementations.

Names should be unique or namespaced deliberately. Do not assume that duplicate names across versioned URL patterns will reverse to the intended version without an explicit strategy.

## Option 2: DRF versioning schemes

DRF versioning classes identify the requested version and expose it as `request.version`. They do not choose the view organization or automatically create a separate view for every version. The official [DRF versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/) describes the available schemes and their configuration.

For example, `URLPathVersioning` can use a dynamic URL parameter:

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ("v1", "v2"),
}
```

```python
# urls.py
from django.urls import path
from .views import UserList

urlpatterns = [
    path("api/<str:version>/users/", UserList.as_view(), name="user-list"),
]
```

The URL keyword argument is named `version`, matching DRF's default `VERSION_PARAM`. The configured values (`"v1"`, `"v2"`) match the URL segment values. A shared view can branch on `request.version`, or delegate to version-specific serializers or handlers:

```python
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.generics import ListAPIView

User = get_user_model()

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

This is a valid DRF-only design. A single URL pattern and view class serve both versions; the view chooses the serializer based on `request.version`. Other DRF schemes include `AcceptHeaderVersioning`, `NamespaceVersioning`, `QueryParameterVersioning`, and `HostNameVersioning`. Each has a different version source, so choose based on client, caching, URL, and routing requirements—not on an assumption that DRF forces one view per version.

A useful distinction: with static URL patterns such as `api/v1/users/` and `api/v2/users/`, `URLPathVersioning` does not receive a dynamic version keyword argument. In that case it falls back to `DEFAULT_VERSION`; the URLconf can still dispatch to different views, but `request.version` will not automatically reflect the static path segment. `NamespaceVersioning` is an alternative when the version is represented by the matched URL namespace.

For ViewSets, DRF's [ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/) and [routers](https://www.django-rest-framework.org/api-guide/routers/) provide the action mapping and URL generation. A router can be mounted under version-specific prefixes; this is a native DRF option and should be considered before introducing another routing layer.

## Option 3: version-range endpoint registration

A registration library addresses a different concern: mapping endpoint implementations to versioned URL patterns. `django-api-versioning` uses a decorator to register a view at the version where that implementation becomes active. Its segment rule carries that registration forward through `API_MAX_VERSION`; a later declaration for the same route at a higher version takes over from that version onward.

The package-specific contract—including integer version identifiers, imports, URL construction, collision precedence, and import order—is defined in the [canonical routing reference](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md). If you want to evaluate this model as a package, see [`django-api-versioning` on PyPI](https://pypi.org/project/django-api-versioning/).

For example, with `API_MIN_VERSION = 1` and `API_MAX_VERSION = 3`:

```python
# settings.py
API_MIN_VERSION = 1
API_MAX_VERSION = 3
```

```python
# accounts/views.py
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django_api_versioning.decorators import endpoint

User = get_user_model()

@endpoint("users/", version=1, view_name="user-list")
def user_list_v1(request):
    return JsonResponse({"version": 1, "fields": ["id", "username"]})

@endpoint("users/", version=2, view_name="user-list")
def user_list_v2(request):
    return JsonResponse({"version": 2, "fields": ["id", "username", "email"]})
```

The registration produces this mapping:

```text
/api/v1/users/  -> user_list_v1
/api/v2/users/  -> user_list_v2
/api/v3/users/  -> user_list_v2
```

The v2 declaration replaces the v1 implementation from v2 onward. Because `API_MAX_VERSION` is 3, the v2 implementation also serves v3 unless another declaration overrides it. This is route-registration inheritance, not Python class inheritance: the two functions above are independent functions.

The URL patterns are populated when decorated modules are imported. Import endpoint modules before importing the package's URL patterns:

```python
# project/urls.py
from django.urls import include, path

from accounts import views as account_views  # noqa: F401
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The import is intentional: it executes the decorators and registers the routes. If endpoint modules have not been imported when the package URL patterns are evaluated, the registry will not contain those declarations.

### What the package does—and does not—inherit

The segment model applies to the registered route. A declaration with `version=N` covers N through `API_MAX_VERSION`. A later, higher-version declaration for the same route replaces it from that point forward. For non-contiguous versions, use `versions=[...]` or `ver_range(start, end)` rather than assuming a skipped version is implicitly filled.

This behavior does not merge Python classes, serializers, permissions, or response contracts. It only selects which callable is attached to each versioned URL. The package does not prove that a carried-forward implementation remains semantically compatible with the newer API contract.

There is also a material trade-off: if an endpoint contract changes and the team forgets to register an override, the previous implementation continues to serve later versions. That can unintentionally expose an old contract and make version-by-version differences harder to see. Inspect the registered version matrix and test behavior—not just route existence—across the versions you support.

**ViewSet limitation:** DRF ViewSet classes cannot be decorated directly with `@endpoint` in 0.3.5. The registry calls `as_view()` without the `actions` mapping that a ViewSet requires. Use DRF's `DefaultRouter` or `SimpleRouter` and mount its generated URLs separately. That is router-based DRF routing, not automatic ViewSet registration or inheritance by this package. A manually configured `ViewSet.as_view({"get": "list"})` callable represents a specific route and does not replace router generation for the full action set.

## Compare the trade-offs

| Concern | Explicit URL patterns | DRF versioning classes | Version-range registration |
| --- | --- | --- | --- |
| Identifies request version | Through URL layout or application logic | Yes; sets `request.version` | URL version is generated from the registered route |
| Shares one view across versions | Yes, by reusing the callable | Yes, often with `request.version` | Yes, by carrying the registration across a version segment |
| Separate implementation per version | Yes | Yes, with URLconf or dispatch design | Yes, by registering an override |
| Generates versioned routes | You write URL patterns | You configure URL patterns or routers | Decorator registration creates package-managed patterns |
| Direct DRF ViewSet registration | Through DRF routers | Through DRF routers | Not supported directly by `@endpoint` |
| Main trade-off | Explicit repetition can grow | Version-dependent behavior stays in application/view design | Implicit carry-forward requires deliberate contract and matrix review |

No option is universally best. Manual routing remains appropriate when the route map is small and explicitness is valuable. DRF schemes are appropriate when version identification and application-controlled dispatch are sufficient. Version-range registration is useful when teams want to declare only endpoint implementation changes and have the routing registry carry each declaration across its configured segment.

## Trade-offs and scope

**Scope: routing only.** API versioning also requires a contract policy: which changes are breaking, how long older contracts remain supported, how clients learn about deprecation, when a version is retired, and how documentation and OpenAPI schemas represent each supported contract. Neither a URL router nor `request.version` answers those questions automatically.

For the package, the trade-off is between fewer repeated route declarations and more implicit routing behavior. The team must understand the segment rule, import order, collision precedence, and the risk of a missed override. It should test the route matrix and contract behavior for each supported version. Do not infer lower runtime latency or performance from a smaller URLconf; this is a code-organization and routing-registration choice, not a benchmark result.

**Maturity snapshot (2026-11-12):** The repository identifies release 0.3.5 as Beta. Package metadata requires Python 3.10 or later and Django 4.2 or later; DRF is an optional development extra, not a core runtime dependency. The 0.3.5 changelog reports 131 tests passing during release verification, and the GitHub Actions workflow builds and runs the test container. These are project-reported facts, not independent adoption evidence or a published DRF compatibility matrix. See the [changelog](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/CHANGELOG.md), [test workflow](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/.github/workflows/tests.yml), and [test suite](https://github.com/mojtaba-arvin/django-api-versioning/tree/main/tests).

## When the benefit is smaller

For two stable versions with only a small number of changed endpoints, explicit URL patterns or a shared DRF view may be easier to understand than introducing a registration abstraction. For major versions that represent fundamentally different APIs, separate URLconfs or namespaces can make the boundary clearer. The package is most relevant when endpoint implementations evolve incrementally and the team values centralized version-range registration enough to accept its learning and review costs.

**Now:** choose how clients identify the version; choose shared or separate views based on how endpoint behavior diverges; then decide whether explicit URL patterns or version-range registration best expresses the route map. Keep contract compatibility, deprecation, client communication, and schema versioning as explicit parts of the broader API lifecycle.

## Explore the implementation

If the version-range model fits your API, inspect the [django-api-versioning source repository](https://github.com/mojtaba-arvin/django-api-versioning).
