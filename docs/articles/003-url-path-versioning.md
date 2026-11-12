---
slug: "004-api-routing-library"
title: "API routing libraries: declarative versioning and automatic inheritance"
description: "How declarative endpoint registration and forward route inheritance reduce repetitive URL configuration in multi-version Django REST Framework APIs."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - Django API versioning
  - DRF API versioning
  - declarative API routing
  - endpoint registration
  - API routing patterns
  - forward route inheritance
---

# API routing libraries: declarative versioning and automatic inheritance

API versioning introduces a routing problem that grows with the number of endpoints and versions.

When an API evolves, some endpoints change while others remain compatible with newer versions. A routing configuration must represent both cases: endpoints that have a new implementation and endpoints that can continue using an existing implementation.

Django and Django REST Framework provide the building blocks for versioned APIs. However, maintaining every versioned route explicitly can become repetitive, especially when most endpoints remain unchanged between releases.

A routing library can move that responsibility out of the project's URL configuration. Instead of declaring every route for every version, developers declare where an endpoint implementation starts being used. The library generates the corresponding URL patterns and carries that implementation forward until another declaration replaces it.

This article explores that design through `django-api-versioning`, including its routing model, Python inheritance, trade-offs, and the situations where declarative registration provides the most value.

**Package version:** `0.3.4`  
**Technical assessment date:** `2026-11-12`

The examples target Django REST Framework class-based views and use path-based versioning.

## The routing problem

Consider an API with three versions:

- v1 introduces the initial endpoint implementation.
- v2 changes some endpoint behavior.
- v3 introduces a few additional changes while leaving most v2 endpoints untouched.

A conventional URL configuration can represent this explicitly:

```python
from django.urls import path

urlpatterns = [
    path("api/v1/users/", UserListViewV1.as_view()),
    path("api/v2/users/", UserListViewV2.as_view()),
    path("api/v3/users/", UserListViewV2.as_view()),
]
```

This is valid Django code. The same view can be reused across multiple URL patterns, so separate view implementations are not inherently necessary.

The maintenance cost comes from having to declare and keep track of the versioned routes themselves. As the number of endpoints and versions grows, the URL configuration becomes another place where API evolution must be maintained.

For an endpoint whose implementation changes only in v2, the routing intent is simpler:

- v1 uses the v1 implementation.
- v2 uses the v2 implementation.
- v3 continues using the v2 implementation until a v3 implementation is introduced.

A declarative routing library can express that intent directly.

## Declarative endpoint registration

The `django-api-versioning` package uses an `@endpoint` decorator to register a view for a version segment.

The following settings establish three supported API versions:

```python
# settings.py

INSTALLED_APPS = [
    # ...
    "django_api_versioning",
]

API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 3
```

The `API_BASE_PATH` setting defines the versioned URL prefix. The `{version}` placeholder is replaced with the registered version number.

An endpoint declaration identifies the resource path and the version where its implementation begins:

```python
from django_api_versioning import endpoint


@endpoint("users/", version=1)
class UserListViewV1(ListCreateAPIView):
    ...
```

With the configured version range, `version=1` registers the view for v1, v2, and v3 unless a higher-priority declaration replaces it for a particular version.

A second declaration can introduce a new implementation starting in v2:

```python
@endpoint("users/", version=2)
class UserListViewV2(UserListViewV1):
    ...
```

The resulting routing is:

| URL | Registered view |
| --- | --- |
| `/api/v1/users/` | `UserListViewV1` |
| `/api/v2/users/` | `UserListViewV2` |
| `/api/v3/users/` | `UserListViewV2` |

The v3 route does not need another declaration. It continues using the v2 implementation because the v2 segment extends through `API_MAX_VERSION`.

This is forward route inheritance: a declaration for a version also covers subsequent configured versions until another declaration takes precedence.

It is a routing behavior, not Python class inheritance. The two concepts can be used together, but they solve different problems.

## Connecting the generated routes to Django

The package maintains the registered URL patterns and exposes them through its URL configuration.

If the project already has a root URL configuration, include the generated patterns once:

```python
# project/urls.py

from django.urls import include, path
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    # Other project routes
    path("", include(api_urlpatterns)),
]
```

The import order of endpoint declarations matters. The modules containing decorated views must be imported before the package's generated URL patterns are evaluated.

For example, if the views live in `api/views.py`, import that module before importing the generated patterns:

```python
# project/urls.py

import api.views

from django.urls import include, path
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

This ensures that the decorators have registered their endpoints before Django receives the generated URL patterns.

The package generates concrete URL patterns during registration and URL configuration setup. It does not perform a backward lookup through view declarations for every incoming request.

## Python inheritance and routing inheritance

The previous example uses two different forms of inheritance.

Python inheritance allows a new view class to reuse or extend the behavior of an existing class:

```python
class UserListViewV2(UserListViewV1):
    serializer_class = UserSerializerV2
```

Routing inheritance determines which API versions are registered to use that view:

```python
@endpoint("users/", version=2)
class UserListViewV2(UserListViewV1):
    serializer_class = UserSerializerV2
```

The Python class hierarchy determines the methods and attributes available to `UserListViewV2`.

The decorator determines the versions for which the view is registered.

Neither mechanism guarantees that the resulting API contract is backward-compatible. That remains an application-level responsibility.

For example, a v2 serializer may introduce a different response structure. If that implementation is automatically used by v3, then v3 receives the same response structure unless a separate v3 declaration is added.

This is useful when the newer version intentionally retains the same behavior. It can also introduce accidental contract changes when developers assume that every new API version needs a separate implementation.

## Extending an endpoint in a later version

Suppose the v3 API introduces an additional validation rule for user creation.

The v2 implementation already handles listing and creating users. The v3 implementation can inherit that behavior and override only the method that needs to change:

```python
from rest_framework.exceptions import ValidationError


@endpoint("users/", version=3)
class UserListViewV3(UserListViewV2):

    def post(self, request, *args, **kwargs):
        email = request.data.get("email") or ""

        if email and not email.endswith("@example.com"):
            raise ValidationError(
                {"email": "Only example.com addresses are accepted."}
            )

        return super().post(request, *args, **kwargs)
```

The resulting routing becomes:

| URL | Registered view |
| --- | --- |
| `/api/v1/users/` | `UserListViewV1` |
| `/api/v2/users/` | `UserListViewV2` |
| `/api/v3/users/` | `UserListViewV3` |

The v3 implementation inherits the existing v2 behavior and changes only the POST operation.

The same principle applies when a later version changes a queryset, serializer, permission class, pagination policy, or another part of the view.

The important distinction is that a new declaration changes the routing assignment. It does not automatically merge methods from different view implementations.

## A second example: an endpoint that skips a version

Not every endpoint needs to exist in every API version.

Suppose a reporting endpoint is introduced in v1, but its implementation is replaced in v3:

```python
@endpoint("reports/", version=1)
class ReportListViewV1(ListAPIView):
    ...

@endpoint("reports/", version=3)
class ReportListViewV3(ListAPIView):
    ...
```

The resulting mapping is:

| URL | Registered view |
| --- | --- |
| `/api/v1/reports/` | `ReportListViewV1` |
| `/api/v2/reports/` | `ReportListViewV1` |
| `/api/v3/reports/` | `ReportListViewV3` |

The v3 declaration takes precedence for v3. The v1 implementation remains responsible for v1 and v2.

For more specific routing requirements, the package also supports explicit version lists:

```python
@endpoint("ranking/", versions=[1, 3])
class RankingView(APIView):
    ...
```

This registers the endpoint only for v1 and v3. It does not create a v2 route.

The `versions` argument is useful when an endpoint must be available in selected versions rather than in a continuous segment. The package also provides `ver_range()` for expressing inclusive version ranges.

## How route declarations take precedence

When multiple declarations target the same URL pattern, the registry needs a deterministic rule for deciding which view is used.

The package uses the declaration's `source_version`:

1. A declaration with a higher integer `source_version` takes precedence over one with a lower integer `source_version`.
2. If the declarations have the same `source_version`, the last registered declaration wins.
3. If either declaration has `source_version=None`, the last registered declaration wins.

This is more precise than saying that a later import always replaces an earlier one.

For ordinary versioned declarations, a higher source version wins even if its module is imported first. The precedence rule is based on the declared source version, not simply on Python import order.

This makes the intended routing behavior easier to reason about when endpoint modules are distributed across an application.

## Declarative routing versus manual URL configuration

Django's URL configuration is flexible. Developers can reuse view callables, include shared URL configurations, and organize routes across multiple modules.

DRF also provides versioning schemes such as `URLPathVersioning`, which identify the requested API version through the URL and expose it through `request.version`.

These mechanisms solve related but different problems.

DRF's versioning classes identify the version of an incoming request. They do not automatically generate a separate route for each endpoint implementation or define a forward inheritance policy for unchanged endpoints.

A declarative routing library addresses that additional registration problem.

For a concrete comparison, consider an API with:

- 20 endpoints.
- 4 supported API versions.
- 3 endpoint changes at each version boundary.

A fully explicit URL configuration with a separate route entry for every endpoint in every version requires:

- 20 × 4 = 80 route declarations.

With declarative registration:

- 20 initial endpoint declarations establish the original implementations.
- 3 overrides at the v2 boundary introduce changed implementations.
- 3 overrides at the v3 boundary introduce changed implementations.
- 3 overrides at the v4 boundary introduce changed implementations.

That produces:

- 20 + 3 + 3 + 3 = 29 endpoint declarations.

This comparison counts route declarations, not view implementations. It assumes a fully explicit per-version URL configuration; Django can reuse the same view callable across multiple paths, so the 80 entries do not imply 80 separate view classes or functions.

| Approach | Route declarations |
| --- | ---: |
| Fully explicit routes for every endpoint and version | 80 |
| Initial declarations plus changed endpoint overrides | 29 |
| Difference | 51 fewer declarations |

The benefit comes from describing only the points where routing behavior changes rather than repeating unchanged mappings.

The actual reduction depends on the API's evolution pattern. If nearly every endpoint changes in every version, the difference becomes smaller.

## Trade-offs and scope

Declarative endpoint registration is useful, but it introduces its own abstraction and conventions.

| Consideration | Declarative routing | Manual URL configuration |
| --- | --- | --- |
| Route registration | Generated from endpoint declarations | Defined explicitly |
| Unchanged endpoints | Can carry forward to later versions | Must be mapped through the project's URL configuration |
| Version-specific changes | Introduced with another declaration | Added through another route mapping |
| Routing visibility | Distributed across decorated view modules | Visible in URL configuration |
| Fine-grained routing control | Follows the package's registration model | Uses Django's full URL configuration API |
| Additional dependency | Requires a routing package | Uses Django directly |

### When the benefit is smaller

The package is not automatically the better choice for every API.

Manual URL configuration may be preferable when:

- The API has only a small number of endpoints and versions.
- Most endpoints have substantially different behavior in each version.
- Routing depends on complex URL composition or custom resolution rules.
- The team prefers Django's built-in URL configuration without an additional dependency.

Declarative registration becomes more valuable when many endpoints remain unchanged across versions and the team wants to keep version-specific routing declarations close to their view implementations.

The deciding factor is not a fixed number of API versions. It is how frequently endpoint routing changes relative to the number of endpoints that remain stable.

### Important compatibility considerations

Forward route inheritance reduces repeated routing declarations, but it does not establish semantic API compatibility.

When a new version is introduced, teams should verify the complete version matrix for:

- Request and response serializers.
- Permissions and authentication behavior.
- Queryset filtering and object visibility.
- Pagination and filtering rules.
- Error response formats.
- Schema generation and API documentation.
- Any behavior that clients depend on.

A view declared at v2 may continue serving v3 automatically. If the v3 contract must differ, register a v3 implementation explicitly.

For endpoints that should exist only in selected versions, use `versions=[...]` rather than relying on a continuous version segment.

The package handles route registration. Application teams remain responsible for defining and testing the API contracts.

### Scope: routing only

The package's responsibility is versioned URL registration. It does not replace DRF's request-version identification mechanisms, automatically make API contracts compatible, or generate a separate schema for every API version.

DRF ViewSet classes are also not directly supported by `@endpoint`. A ViewSet's `as_view()` method requires an action mapping that the decorator does not supply. Use DRF routers to register ViewSets separately, or use APIView-based views for endpoints registered through the decorator.

For the precise behavior of endpoint declarations, collision precedence, version ranges, and supported view types, see the [versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Getting started

The package is available on [PyPI](https://pypi.org/project/django-api-versioning/).

The integration example and implementation are available in the repository:

- [Integration URL configuration](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/integration_test_project/project/urls.py)
- [Endpoint decorator implementation](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/decorators.py)

I maintain this package, and the examples in this article describe its routing model rather than a hypothetical API design.

If your API has many endpoints that evolve incrementally, declarative registration can make the routing layer reflect those changes with fewer repeated declarations.

Explore the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning) to review the implementation and decide whether its routing model fits your API.
