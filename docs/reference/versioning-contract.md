
# django-api-versioning: canonical routing contract

> **Applies to:** `django-api-versioning` `1.1.0`, published from the annotated `v1.1.0` tag.
> **Current stable release:** `1.1.0`. The tag-based publish workflow verified the release tag, ran the compatibility matrix, built and verified the wheel and sdist, smoke-tested the installed wheel, and published both artifacts to PyPI through Trusted Publishing. The release workflow completed successfully on commit `66bb4da557b9df4081be3ee65b9ad01db5030f2a`. The tag-based publish workflow verifies the tag target, runs the compatibility matrix, builds and verifies the wheel and sdist, smoke-tests the installed wheel, and publishes the verified artifacts to PyPI through Trusted Publishing. The configured Python/Django environments are defined in [`tox.ini`](../../tox.ini) and checked against the [compatibility workflow](../../.github/workflows/compatibility.yml). Actual outcomes are commit-specific; consult the [workflow run history](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/compatibility.yml) rather than treating the configured matrix as proof of a passing run. The [v0.3.8 compatibility report](../reports/compatibility-0.3.8.md) is historical evidence for that release only.
>
> This document defines the package-specific contract for version identifiers, public imports, URL construction, endpoint registration, route precedence, URL reversal, and Django REST Framework integration.
>
> It is the canonical reference for technical claims about these behaviors. If another package document conflicts with this contract, verify the implementation and tests before changing either document.

## 1. Version identifiers

The package uses **integer API version identifiers** in Python configuration and endpoint declarations.

Use integers such as `1`, `2`, and `3` for:

- The `version` argument.
- Entries in the `versions` argument.
- `API_MIN_VERSION`.
- `API_MAX_VERSION`.

The default URL template is `api/v{version}/`.

An integer version of `2` therefore produces the URL segment `v2`. The `v` prefix belongs to the URL representation; it is not part of the Python version identifier.

Do not copy DRF examples using string identifiers such as `"v1"` or `"1.0"` into this package's integer-only `version` and `versions` arguments.

## 2. Canonical imports and public API

The package exposes `endpoint`, `remove_endpoint`, `ver_range`, and `api_reverse` from its top-level namespace. The optional DRF integration is imported from `django_api_versioning.routers` so core Django users do not need DRF installed.

Use these public imports:

```python
from django_api_versioning import endpoint, remove_endpoint, ver_range, api_reverse
```

The decorators are implemented in `django_api_versioning.decorators`, so importing them directly from that module also works:

```python
from django_api_versioning.decorators import endpoint, remove_endpoint, ver_range
```

For application code and documentation examples, prefer the top-level import path. It is the package's public API and avoids coupling consumers to the internal module structure.

The optional DRF integration is deliberately imported from its own module so Django-only installations do not need DRF:

```python
from django_api_versioning.routers import VersionedRouter, VersionedRouterVersioning
```

Import the generated URL patterns from:

```python
from django_api_versioning.urls import urlpatterns as api_urlpatterns
```

The public decorator signature is:

```python
endpoint(
    postfix: str,
    version: int | None = None,
    versions: list[int] | None = None,
    app_name: str | None = None,
    view_name: str | None = None,
)
```

Arguments:

- `postfix`: Resource path appended to the generated version prefix.
- `version`: Starting version for a forward segment.
- `versions`: Explicit list of versions for which the endpoint is registered.
- `app_name`: Optional path segment prepended to `postfix`.
- `view_name`: Optional Django URL pattern name used by `api_reverse()`.

The decorator does not accept `path`, `forward`, or `backward` keyword arguments.

## 3. URL construction

For a versioned declaration, the registry constructs the route from:

1. `API_BASE_PATH` formatted with the integer version.
2. The optional `app_name` segment followed by `/`.
3. `postfix`.

With the default `API_BASE_PATH = "api/v{version}/"`:

```python
@endpoint(
    "users/<int:user_id>/",
    app_name="accounts",
    version=2,
    view_name="accounts-user-detail",
)
def user_detail(request, user_id):
    ...
```

The generated route is:

```text
api/v2/accounts/users/<int:user_id>/
```

With the package URL patterns included at the project root, a request for user ID `42` resolves at:

```text
/api/v2/accounts/users/42/
```

`app_name` is a path prefix, not a Django URL namespace.

### API_BASE_PATH

`API_BASE_PATH` must contain exactly one plain `{version}` field. Other format fields, conversions, and format specifications are rejected during settings validation.

The default is:

```python
API_BASE_PATH = "api/v{version}/"
```

The package formats this template with each registered integer version. It also normalizes the setting to end with `/` when necessary.

The setting is the versioned route prefix. It is not a separate mount prefix that should be duplicated in the project's URL configuration.

### Unversioned routes

An endpoint with neither `version` nor `versions` is registered without `API_BASE_PATH`.

For example:

```python
@endpoint("health/")
def health_check(request):
    ...
```

Its final URL depends on the prefix where the generated URL patterns are included.

If the patterns are included at the project root, the route is:

```text
/health/
```

If they are included under `/api/`, the route is:

```text
/api/health/
```

### Path converters

The package passes the generated route to Django's `path()` function.

Django path converters in `postfix`, such as `<int:pk>`, `<int:user_id>`, and `<slug:slug>`, are supported by the routing layer.

## 4. Registration semantics

Exactly one of `version` or `versions` may be supplied.

### Segment registration: version=N

`version=N` registers the implementation for every integer version from `N` through `API_MAX_VERSION`, inclusive.

For example, with:

```python
API_MIN_VERSION = 1
API_MAX_VERSION = 4
```

this declaration:

```python
@endpoint("orders/", version=2)
def orders_v2(request):
    ...
```

registers the implementation for:

- v2
- v3
- v4

It does not register the endpoint for v1.

A later declaration for the same route at a higher source version replaces the earlier implementation from that version onward.

For example:

```python
@endpoint("orders/", version=2)
def orders_v2(request):
    ...


@endpoint("orders/", version=3)
def orders_v3(request):
    ...
```

The resulting mapping is:

| Route version | Implementation |
| --- | --- |
| v1 | Not registered |
| v2 | `orders_v2` |
| v3 | `orders_v3` |
| v4 | `orders_v3` |

The v3 declaration takes over from v3 onward. The v2 implementation remains active for v2.

### Explicit registration: versions=[...]

`versions=[...]` registers the implementation only for the listed versions.

```python
@endpoint("reports/", versions=[1, 3, 4])
def reports(request):
    ...
```

This registers the endpoint for v1, v3, and v4, but not v2.

Use `ver_range(start, end)` when a bounded inclusive set is clearer:

```python
from django_api_versioning import endpoint, ver_range


@endpoint("legacy/", versions=ver_range(1, 3))
def legacy(request):
    ...
```

`ver_range(1, 3)` returns:

```python
[1, 2, 3]
```

### Explicit endpoint removal

Forward inheritance can be stopped deliberately without deleting the route
from earlier API versions. Use the top-level remove_endpoint() function:

```python
from django_api_versioning import endpoint, remove_endpoint


@endpoint("orders/", version=1, view_name="orders-list")
def orders_v1(request):
    ...


remove_endpoint("orders/", from_version=3)
```

A removal boundary suppresses source declarations at or before that version
for the matching concrete route versions. A later declaration with a strictly
higher source version reintroduces the route from that version onward. The
result is independent of whether the removal or older endpoint module is
imported first.

Removed routes are absent from Django's active URL patterns and return 404.
api_reverse() raises NoReverseMatch for a removed version; it never falls back
to an older implementation. The version-matrix snapshot records the state as
`<removed>`, which is distinct from an undeclared/missing route.

This is an endpoint-level removal, not a version retirement. It does not emit
410 or lifecycle headers; version-wide deprecation and sunset remain the
responsibility of LifecycleMiddleware.

### Unversioned registration

When neither argument is supplied, the endpoint is registered once without a version prefix:

```python
@endpoint("health/")
def health(request):
    ...
```

### Validation and boundaries

- Supplying both `version` and `versions` raises `VersionRangeError`.
- Version values must be integers.
- Boolean values are rejected, even though `bool` is a subclass of `int` in Python.
- A value greater than `API_MAX_VERSION` raises `InvalidVersionError`.
- A segment start below `API_MIN_VERSION` logs a warning and registers no routes for that declaration.
- In an explicit version list, entries below `API_MIN_VERSION` are warned about and skipped.
- `API_MIN_VERSION` and `API_MAX_VERSION` must be integers.
- `API_MIN_VERSION` cannot exceed `API_MAX_VERSION`.

## 5. Collision precedence and route ordering

The registry identifies a collision by the complete route string.

When a new registration collides with an existing route:

1. If both declarations have integer `source_version` values, the higher source version wins.
2. If the source versions are equal, the last registration wins.
3. If either source version is `None`, the last registration wins.

For segment registration, the source version is the segment's starting version.

For explicit registration, each listed route version is its own source version.

After registration, URL patterns are ordered with:

1. Unversioned routes first.
2. Versioned routes in ascending route-version order.

Do not treat this ordering as a guarantee about Django's reverse lookup behavior when multiple patterns share a name.

## 6. URLconf integration and import order

Decorators register routes when their Python modules are imported.

Django does not automatically import every application's `views.py` module just because it exists. Therefore, explicitly import all modules containing `@endpoint` declarations as part of your URL configuration setup.

A typical project URL configuration is:

```python
# project/urls.py

from django.urls import include, path

from accounts import views as account_views  # noqa: F401
from orders import views as order_views  # noqa: F401

from django_api_versioning.urls import urlpatterns as api_urlpatterns


urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

The import aliases are intentionally unused. Importing the modules executes their decorators and registers their endpoints.

**Recommended order:**

1. Import modules containing endpoint declarations.
2. Import the package's generated `api_urlpatterns`.
3. Include those patterns in the project URL configuration.

The package's `urlpatterns` is a reference to the registry's shared URL pattern list, not a separate copy. Importing it before endpoint modules does not, by itself, permanently capture an empty snapshot.

However, importing endpoint modules before the generated patterns keeps URL configuration initialization explicit and predictable.

If endpoint declarations are spread across multiple modules, import each module before the URL configuration is finalized.

### Using the package URLconf as ROOT_URLCONF

The package exposes `django_api_versioning.urls` as a URL configuration module.

It can be used directly as `ROOT_URLCONF` when its generated patterns are sufficient for the project.

However, using it directly does not automatically combine the package's patterns with other application URL configurations. If the project has additional URL patterns, compose them explicitly in a project-level URLconf.

Avoid mounting the package under a prefix that unintentionally duplicates the prefix already defined by `API_BASE_PATH`.

## 7. Supported view types and the ViewSet/router boundary

The package supports:

- Django function-based views.
- Django class-based view classes whose `as_view()` method returns a Django view callable.
- Django REST Framework `APIView` classes.
- DRF generic-view classes.
- DRF `ViewSet` and `ModelViewSet` classes through the optional `VersionedRouter` integration.

For a class-based view, the registry calls `as_view()` when it receives the class. Do not pass an instantiated view object. A generic view must implement the HTTP handlers required by its registered route.

### ViewSets

A DRF `ViewSet` class still cannot be decorated directly with `@endpoint`: the decorator receives a Django view class or callable, while DRF ViewSets require an action map. Use `VersionedRouter` for full router-managed versioned routing:

```python
from django_api_versioning.routers import VersionedRouter
from orders.views import OrderViewSetV1, OrderViewSetV2

router = VersionedRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")
router.register("orders", OrderViewSetV2, version=2, basename="order")
urlpatterns = router.urls
```

The router delegates route generation to DRF's `SimpleRouter`, preserves the generated URLPattern objects, and registers each concrete route version in the package registry. It supports standard list/detail routes, custom `@action` routes, path converters, regex routes, and trailing-slash configuration. `DefaultRouter` API-root and format-suffix parity are not part of this integration.

Configure `VersionedRouterVersioning` as DRF's `DEFAULT_VERSIONING_CLASS` or on the relevant ViewSet when you need `request.version`, `reverse_action()`, or version-aware hyperlinked fields. The adapter returns the numeric version as a string (for example, `"2"`) and preserves nested URL namespaces during reversal.

A manually configured callable such as `MyViewSet.as_view({"get": "list"})` remains valid for a single route, but it does not provide the complete router-generated route set.

The router uses per-route inheritance: a later ViewSet replaces matching routes while earlier custom actions that are not redeclared remain inherited. Remove one generated route/action without removing the rest of the ViewSet by using its URL name:

```python
router.remove("orders", "order-archive", from_version=3)
```

The first argument is the router prefix; the second is the URL name generated from the basename and action. The removal applies from the requested version onward and can be reversed only by a later source-version registration.

## 8. Routing inheritance is not Python inheritance or contract compatibility

The package's segment behavior is **route-registration inheritance**:

- A declaration at version N supplies the route implementation for N through `API_MAX_VERSION`.
- A later declaration for the same route at a higher source version overrides it from that version onward.
- Explicit `versions=[...]` declarations register only the listed versions.

This behavior does not create a Python subclass, copy methods, merge serializers, or prove that a response remains semantically backward compatible.

Two view classes may be unrelated Python classes. The registry selects which callable is attached to each generated URL.

Automatic carry-forward has a real trade-off: if an endpoint's contract changes but its registration is not updated, the newer implementation continues to serve later versions.

Conversely, an implementation intended only for selected versions should use explicit version registration rather than a forward segment.

Teams must deliberately choose between segment registration and explicit version sets, inspect the generated version matrix when contracts change, and test each supported version's behavior.

Relevant request-level compatibility tests may need to cover:

- Response fields and types.
- Serializer selection.
- Authentication and permissions.
- Filtering and pagination.
- Error responses.
- Schema output.

The package manages routing. It does not decide whether a change is backward compatible, maintain a semantic API contract, or automatically version OpenAPI schemas.

## 9. Function names and URL names

The Python function or class name is not used to derive the URL path.

The URL path comes from:

- `API_BASE_PATH`, for versioned routes.
- `app_name`, when supplied.
- `postfix`.

Likewise, the registry does not infer a Django URL name from the Python function name.

Supply `view_name` explicitly when a named route is needed:

```python
@endpoint(
    "orders/",
    version=2,
    view_name="orders-list",
)
def list_orders(request):
    ...
```

A `view_name` is a Django URL pattern name. It is not a URL path segment.

## 10. Reverse registered routes with api_reverse()

The package exposes `api_reverse()` through its top-level namespace:

```python
from django_api_versioning import api_reverse
```

Its signature is:

```python
api_reverse(
    view_name: str,
    version: int | None = None,
    **kwargs,
) -> str
```

The helper searches the package registry for URL patterns whose `view_name` matches the requested name.

### Explicit version lookup

When `version` is supplied, the helper selects a registered route whose route version exactly matches that value.

```python
url = api_reverse(
    "orders-list",
    version=2,
)
```

The helper does not fall back to another version if the requested version is not registered.

### Lookup without a version

When `version` is omitted or `None`, the helper succeeds only if exactly one registered pattern matches the supplied `view_name`.

If multiple patterns match, it raises `AmbiguousVersionError`.

For versioned names shared across multiple route versions, pass an explicit version.

### Path parameters

Named path parameters are supplied as keyword arguments:

```python
@endpoint(
    "orders/<int:order_id>/",
    version=2,
    view_name="order-detail",
)
def order_detail(request, order_id):
    ...


url = api_reverse(
    "order-detail",
    version=2,
    order_id=42,
)
```

The helper substitutes the parameter values into the registered route and returns a path under Django's configured script prefix:

```text
/api/v2/orders/42/
```

The helper requires all named parameters used by the route and does not accept positional `args`. For path-converter routes, it calls the registered converter's `to_url()` method and validates the completed path against the compiled route pattern. For regex-backed routes (including DRF's default `SimpleRouter` patterns), it delegates reversal to Django's `URLResolver`. Both forms use Django's configured script prefix.

### Supported route patterns and limitations

`api_reverse()` supports package-registered Django `RoutePattern` and `RegexPattern` objects, including DRF router-generated patterns. It is not a general replacement for Django's `reverse()` and does not accept arbitrary URLconf names or positional `args`.

If no matching pattern exists, it raises Django's `NoReverseMatch`. If the requested name is registered more than once for an explicit version, it also raises `NoReverseMatch` rather than selecting an arbitrary route. If a name is shared across multiple versions and no version is supplied, it raises `AmbiguousVersionError`.

The helper returns the package route path under the script prefix; it does not add an outer Django URL namespace. DRF `reverse_action()` and hyperlinked serializer fields should use `VersionedRouterVersioning` for namespace-aware reversal.

## 11. DRF version identification versus package routing

Django REST Framework provides versioning schemes such as:

- `URLPathVersioning`
- `NamespaceVersioning`
- `AcceptHeaderVersioning`
- `QueryParameterVersioning`
- `HostNameVersioning`

The package does not reimplement these general parsers. Its path-based `VersionedRouter` uses `VersionedRouterVersioning`, which reads the concrete `vN` namespace emitted by the router and exposes that numeric version as `request.version`. The adapter also preserves the full resolver namespace for `reverse_action()` and hyperlinked serializers.

This does not activate header, query-parameter, host, or tenant-based route negotiation. Those channels require a separate runtime-dispatch contract, cache behavior, and reversal semantics; the reserved `API_VERSIONING_CHANNELS` and `API_EFFECTIVE_VERSION_RESOLVER` settings still have no runtime effect. See the product roadmap in Issue #36.

Do not configure DRF's `URLPathVersioning` as a substitute for `VersionedRouterVersioning`: the former expects a version value in a URL resolver keyword argument, while this package's router uses literal version path segments and version namespaces.

## 12. Version lifecycle headers

`LifecycleMiddleware` reads `API_VERSION_LIFECYCLE` at request time and can enforce a configured sunset by returning `410 Gone`.

A deprecated version must include a `deprecated_at` ISO 8601 date or datetime to emit the `Deprecation` response header:

```python
API_VERSION_LIFECYCLE = {
    1: {
        "status": "deprecated",
        "deprecated_at": "2026-01-01T00:00:00+00:00",
        "sunset": "2027-06-30",
    },
}
```

Settings validation requires `deprecated_at` for deprecated versions and rejects missing or invalid lifecycle dates at initialization. When both dates are supplied, `sunset` must not be earlier than `deprecated_at`; values are compared as UTC instants, with timezone-naive ISO 8601 values (including date-only values at midnight) interpreted as UTC. This prevents emitting a `Sunset` date that contradicts the deprecation date, as required by RFC 9745. If a value is changed after initialization, the middleware logs a warning and omits an invalid `Deprecation` header. Valid values are serialized as an RFC 9745 Structured Field Date (`@` followed by the Unix timestamp); the middleware never emits the legacy non-standard boolean value. `Sunset` is serialized as an HTTP-date under RFC 8594. A sunset date in the past triggers `410 Gone`.

A `retired` version whose sunset date is still in the future is still served. Its responses carry the `Sunset` header, and also the `Deprecation` header when `deprecated_at` is configured; unlike for `deprecated` versions, a missing `deprecated_at` is not logged as a problem. `active` and unknown versions never receive lifecycle headers.

This is a version-wide policy. The middleware also recognizes the configured API base path below parent URL prefixes, so lifecycle headers continue to work when a versioned router is mounted through nested URL includes. It does not generate migration links or resource-specific successor URLs; applications must provide those when needed.

## 13. Scope and known limitations

`django-api-versioning` focuses on version-aware endpoint registration and routing.

It does not:

- Automatically make response schemas backward-compatible or transform serializers and response payloads.
- Select serializers based on a request version.
- Replace DRF authentication, permission, throttle, filter, pagination, or renderer behavior.
- Provide `DefaultRouter` API-root or format-suffix behavior; the current integration targets `SimpleRouter`.
- Infer endpoint removal from an omitted import or missing ViewSet action; use remove_endpoint() or VersionedRouter.remove() to declare it explicitly.
- Enable header, query-parameter, host, or tenant-based route negotiation. `API_VERSIONING_CHANNELS` and `API_EFFECTIVE_VERSION_RESOLVER` remain reserved settings with no runtime effect.
- Validate response payload compatibility through route-matrix checks.
- Automatically generate versioned OpenAPI schemas or diff their compatibility; the optional drf-spectacular/oasdiff workflow is tracked in Issue #38.

Your application remains responsible for API contract design, serializer selection, authentication, permissions, business logic, and request-level compatibility tests.

## 14. Primary source files

The contract above is based on the following implementation and project files:

- [decorators.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/decorators.py)
- [routers.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/routers.py)
- [registry.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/registry.py)
- [reverse.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/reverse.py)
- [lifecycle.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/lifecycle.py)
- [urls.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/urls.py)
- [settings.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/settings.py)
- [integration URLconf](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/integration_test_project/project/urls.py)
- [README and installation requirements](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/README.md)
- [DRF ViewSets documentation](https://www.django-rest-framework.org/api-guide/viewsets/)
- [DRF routers documentation](https://www.django-rest-framework.org/api-guide/routers/)
- [DRF versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/)
