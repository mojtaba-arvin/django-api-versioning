---
slug: "025-django-api-versioning-viewset-support-limitations"
title: "Versioned DRF ViewSets with Route-Level Inheritance"
description: "Register DRF ViewSets by API version, inherit unchanged routes, preserve version-aware reversal, and understand lifecycle and OpenAPI boundaries."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "django-api-versioning"
  - "Django REST Framework"
  - "VersionedRouter"
  - "ViewSets"
  - "API versioning"
---

# Versioned DRF ViewSets with Route-Level Inheritance

> **Package disclosure:** The author is the creator, owner, and maintainer of `django-api-versioning`.

Django REST Framework (DRF) provides ViewSets, action mappings, and router-generated URL patterns. It also provides versioning classes that expose the selected API version through `request.version`. These are separate responsibilities: a versioning class identifies a request's version, while a router maps URL patterns to view callables.

[django-api-versioning](https://pypi.org/project/django-api-versioning/) provides an optional `VersionedRouter` integration for DRF's `SimpleRouter`. It registers the URL patterns generated for each ViewSet in the package's version registry. The registry then selects implementations per generated route, so unchanged actions can carry forward while changed actions are replaced. The current repository mainline also adds an unreleased `VersionedDefaultRouter` with a version-specific API root and optional format-suffix URLs; this convenience is not part of the published 1.3.0 artifact.

For Django-native function-based and class-based views, use `@endpoint`. For DRF ViewSets, use `VersionedRouter`. The two registration styles can coexist in one URL configuration.

The package-specific behavior described here follows the [canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md). The published 1.3.0 package includes the `VersionedRouter` integration and the endpoint-removal and endpoint-lifecycle APIs. The repository mainline contains an additional `VersionedDefaultRouter` API-root and format-suffix integration that is not yet part of the published wheel.

## 1. Install and configure the DRF adapter

DRF is optional; it is not a runtime dependency of the package's core Django integration. Install a DRF version compatible with your Django version. The repository's [compatibility matrix](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/tox.ini) records the combinations exercised in CI.

Configure the version range and DRF versioning adapter before importing your ViewSet modules:

```python
# settings.py

API_MIN_VERSION = 1
API_MAX_VERSION = 3

REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "django_api_versioning.routers.VersionedRouterVersioning"
    ),
}
```

You can instead set `versioning_class = VersionedRouterVersioning` on an individual ViewSet when you do not want to change the project-wide DRF default.

`VersionedRouterVersioning` reads the concrete version namespace created by the router and exposes the version as a string through `request.version`, for example `"2"`. The `v` prefix belongs to the URL namespace; it is not included in the value of `request.version`. If you configure it on an individual ViewSet instead of using the project-wide setting, import it with `from django_api_versioning.routers import VersionedRouterVersioning` and assign `versioning_class = VersionedRouterVersioning` on that ViewSet.

## 2. Register ViewSets

Use the familiar DRF registration style, adding either `version` or `versions`:

The example assumes the application already defines `orders.models.Order` with `status` and `total` fields.

```python
# orders/views.py

from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from orders.models import Order


class OrderPagination(PageNumberPagination):
    page_size = 20


class OrderV1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "status"]


class OrderV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "status", "total"]


class OrderViewSetV1(viewsets.ReadOnlyModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderV1Serializer
    pagination_class = OrderPagination
    filter_backends = [SearchFilter]
    search_fields = ["status"]

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return Response({"detail": "Archive requested"})


class OrderViewSetV2(viewsets.ReadOnlyModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderV2Serializer
    pagination_class = OrderPagination
    filter_backends = [SearchFilter]
    search_fields = ["status"]
```

Register the two implementations in the root URLconf:

```python
# project/urls.py

from django_api_versioning.routers import VersionedRouter
from orders.views import OrderViewSetV1, OrderViewSetV2

router = VersionedRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")
router.register("orders", OrderViewSetV2, version=2, basename="order")

urlpatterns = router.urls
```

With `API_BASE_PATH = "api/v{version}/"`, `API_MAX_VERSION = 3`, and these patterns mounted at the project root, the generated route mapping is:

| Request | Implementation |
| --- | --- |
| `GET /api/v1/orders/` | `OrderViewSetV1.list()` |
| `GET /api/v2/orders/` | `OrderViewSetV2.list()` |
| `GET /api/v3/orders/` | `OrderViewSetV2.list()` |

The same route-by-route mapping applies to detail routes. The V1 `archive` action remains inherited in v2 and v3 because V2 does not redeclare it. Pagination and filtering remain configured on each ViewSet; the router does not move or infer those policies.

Use the same explicit `basename` for registrations of the same prefix across versions. This keeps generated URL names stable. The router rejects basename changes for one prefix and duplicate basenames across different prefixes within the same router.

To register an operation only in selected versions, use `versions`. The example assumes `exports.views.ExportViewSet` is defined by the application:

```python
from exports.views import ExportViewSet

router.register(
    "exports",
    ExportViewSet,
    versions=[1, 3],
    basename="export",
)
```

The export routes are registered in v1 and v3, but not v2. The router does not silently fall forward to another version.

## 3. Inheritance happens per generated route

The router does not replace an entire ViewSet route set when a newer class is registered. It registers each URL pattern generated by DRF and lets the package registry resolve matching routes independently.

Suppose V1 defines `list`, `retrieve`, and a custom `publish` action. V2 changes `list` and `retrieve`, but does not redeclare `publish`.

| Concrete version | list | retrieve | publish |
| --- | --- | --- | --- |
| v1 | V1 | V1 | V1 |
| v2 | V2 | V2 | V1 inherited |
| v3 | V2 inherited | V2 inherited | V1 inherited |

This is route inheritance, not automatic serializer or response compatibility. An inherited action continues to use its original callback and associated DRF configuration. Review its behavior as part of the API contract.

A route omitted from a newer ViewSet remains inherited. Omission is not a removal declaration.

## 4. Actions, URL reversal, and hyperlinks

The router delegates route generation to DRF's `SimpleRouter`. It preserves the generated URL patterns and callbacks, including standard list/detail mappings, custom `@action` routes, action-level keyword arguments, lookup regexes or path converters, and the configured trailing-slash policy.

The versioning adapter uses the active version namespace for DRF's reverse operations:

- `ViewSet.reverse_action()` reverses within the current version.
- `HyperlinkedIdentityField` generates links within the current version.
- `HyperlinkedRelatedField` validates links against the current version.
- Nested application namespaces are retained.

For package-level reversal, use `api_reverse()` with an explicit version:

```python
from django_api_versioning import api_reverse

url = api_reverse("order-list", version=2)
```

This returns the registered route path under Django's script prefix. It does not add an outer URL namespace. DRF's versioning adapter handles namespaced reversal for ViewSets and hyperlinked serializers.

The router supports DRF's regex-backed routes and Django path-converter routes. Duplicate route names within one concrete version are rejected rather than resolved arbitrarily.

## 5. Router options and multiple routers

The constructor supports the relevant `SimpleRouter` options:

```python
from django_api_versioning.routers import VersionedRouter

router = VersionedRouter(
    trailing_slash=False,
    use_regex_path=False,
)
```

Set `use_regex_path=False` to use Django path converters, including custom converters, instead of DRF's default regex lookup patterns.

Each concrete API version is placed under a Django namespace named `vN`. If multiple independent router instances are mounted in one URLconf, use distinct outer namespaces and distinct route prefixes. The example assumes `orders_router` and `billing_router` are separately configured `VersionedRouter` instances with distinct route prefixes:

```python
from django.urls import include, path

urlpatterns = [
    path(
        "",
        include((orders_router.urls, "orders"), namespace="orders"),
    ),
    path(
        "",
        include((billing_router.urls, "billing"), namespace="billing"),
    ),
]
```

The versioning adapter preserves the complete namespace chain, such as `orders:v2`, when reversing a route. Independent router instances that generate the same internal route pattern are rejected with `VersioningError`; distinct outer namespaces alone do not make duplicate generated patterns safe.

## 6. Lifecycle middleware and nested URL includes

The physical route uses `API_BASE_PATH`, which defaults to `api/v{version}/`. If the API is mounted below a parent URL prefix, such as `/internal/api/v2/orders/`, `LifecycleMiddleware` resolves the version using Django's matched route and registry metadata. The middleware also uses a conservative path fallback when a request has no usable resolver match.

This allows version-wide deprecation and sunset behavior to work with nested URL includes. A lookalike segment such as `/notapi/v2/` is not treated as the configured API base path.

Version-wide lifecycle configuration is separate from the endpoint-level declarations described below. Add `django_api_versioning.lifecycle.LifecycleMiddleware` to Django's `MIDDLEWARE` setting when your application uses the package's lifecycle headers or version-wide sunset enforcement.

## 7. Explicit route removal (available since 1.2.0)

A route that is inherited into later versions must be removed explicitly. Version 1.2.0 added `VersionedRouter.remove()`, which targets one generated route by its stable URL name:

```python
from django_api_versioning.routers import VersionedRouter
from orders.views import OrderViewSetV1

router = VersionedRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")

# Remove only the custom archive action from v3 onward.
router.remove("orders", "order-archive", from_version=3)
```

The route name is the name generated from the registration basename and ViewSet action, not a URL regex. In this example, `order-archive` is the route name for the custom `archive` action.

The removal boundary is inclusive: earlier versions keep the route; v3 and later do not resolve or reverse it. A later declaration with a strictly higher source version can deliberately reintroduce the route. Removing one action does not remove the ViewSet's list, detail, or unrelated custom actions.

This feature is available in the published package since 1.2.0. See the [endpoint-removal contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/endpoint-removal.md) for the full tombstone and reintroduction semantics.

## 8. Endpoint-level lifecycle and OpenAPI (available since 1.2.0)

Version 1.2.0 also added `VersionedRouter.set_lifecycle()` for metadata attached to one route and concrete API version. Using a router registered as in section 2:

```python
router.set_lifecycle(
    "orders",
    "order-list",
    version=1,
    action="list",
    deprecated_at="2030-01-01T00:00:00Z",
    sunset="2031-01-01T00:00:00Z",
)
```

The declaration is scoped to the resolved operation. You can narrow it further by HTTP methods with the optional `methods` argument. Matching requests receive the configured RFC 9745 `Deprecation` and RFC 8594 `Sunset` headers.

An endpoint-level Sunset date does not automatically remove the route or turn it into a 410 response. The route remains registered until the application explicitly removes it in a later API version. Version-wide retirement retains its separate 410 behavior.

For schema output, configure the optional drf-spectacular adapter:

```python
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": (
        "django_api_versioning.spectacular.EndpointLifecycleAutoSchema"
    ),
}
```

This adapter marks the matching deprecated operation with OpenAPI's `deprecated: true` field. It requires `drf-spectacular` and is imported only by applications that configure it; it is not a core runtime dependency. Missing or ambiguous route identity fails closed, leaving the generated operation unchanged.

The repository's [executable OpenAPI consumer example](https://github.com/mojtaba-arvin/django-api-versioning/tree/main/examples/openapi_contract) demonstrates per-version schemas, committed baselines, request-level checks, deterministic generation, and an `oasdiff` breaking-change gate. This example and its CI gate are repository-level tooling and are not included in the published wheel. The endpoint-level lifecycle API and schema deprecation adapter described above are included in the published 1.2.0 package.

## 9. Boundaries and non-goals

**Scope: version-aware routing.** `VersionedRouter` registers DRF-generated routes, selects the applicable callback for each API version, and preserves version-aware reversal. The application remains responsible for serializer design, response compatibility, authentication, permissions, filtering, and pagination configuration on its ViewSets.

The published 1.3.0 integration uses DRF `SimpleRouter`; the `VersionedRouter` class itself does not add a browsable API root or format-suffix patterns. The current repository mainline adds an optional `VersionedDefaultRouter` for those two conveniences:

- A separate API root is mounted under each concrete version prefix.
- Its links come from the effective list routes after version inheritance and explicit removals, rather than the raw registration list.
- DRF format-suffix patterns are enabled by default and can be disabled independently of the API root.
- The suffixed API root is available at a path such as `/api/v2/.json`.
- It reuses DRF's API root view and suffix utility; it is not a full drop-in reimplementation of every `DefaultRouter` extension or third-party router hook.

This `VersionedDefaultRouter` addition is not included in the published 1.3.0 wheel. Use it from repository source until a later package release includes it. See the [VersionedDefaultRouter design](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/versioned-drf-router.md) for its exact contract and verification gates.

The integration also does not:

- Transform serializers or response payloads.
- Infer whether a ViewSet implementation is backward-compatible.
- Change authentication, permissions, throttling, filtering, pagination, or rendering.
- Infer tenant-specific version policy.
- Remove an inherited route merely because a later ViewSet omits its action.
- Automatically remove a route when an endpoint Sunset date passes.

The package manages route-to-view selection. It does not establish semantic backward compatibility. Route-matrix checks, OpenAPI snapshots/diffs, and application request-level tests provide separate evidence for routing, representation, and runtime behavior. See the [API compatibility boundaries](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/api-compatibility-boundaries.md).

When the package's benefit is smaller: if every endpoint is resource-oriented, a single API version is maintained, and there is no need to inherit route implementations between versions, a plain DRF `SimpleRouter` may be simpler. `VersionedRouter` is most useful when endpoint implementations change incrementally and unchanged actions should remain available without repeating their registrations.
## 10. Verification and evidence

The repository contains direct tests for router version registration, namespace-based version resolution, path-converter preservation, duplicate basename and route handling, and lifecycle action/method mapping. Endpoint-removal tests cover action-specific removal, earlier-version preservation, 404 behavior, URL reversal, and later reintroduction. The optional schema adapter has focused tests for resolver identity, version resolution, and fail-closed behavior.

The executable OpenAPI consumer example separately exercises real API requests, schema generation, schema validation, deterministic output, committed version snapshots, and semantic comparison. These are distinct forms of evidence: source inspection and focused unit tests do not by themselves establish that every illustrative code block in this article has been executed as a complete application.

## Summary

Use `VersionedRouter` for published DRF ViewSet support and the repository's unreleased `VersionedDefaultRouter` when a version-specific API root and format-suffix URLs are also needed. Use `@endpoint` for Django-native views, including DRF `APIView` and `GenericAPIView` endpoints. The router delegates route generation to DRF, while the package manages version-specific implementation selection, per-route inheritance, namespace-aware reversal, and the route matrix. DRF remains responsible for ViewSet behavior and serializer contracts.

To evaluate the implementation and its integration examples against your API, start with the [django-api-versioning source repository](https://github.com/mojtaba-arvin/django-api-versioning).
