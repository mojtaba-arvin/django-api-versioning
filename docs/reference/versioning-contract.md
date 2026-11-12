
# django-api-versioning: canonical routing contract

> **Applies to:** django-api-versioning 0.3.4
> **Verified against:** main-branch source on 2026-11-12.
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

The package exposes `endpoint`, `ver_range`, and `api_reverse` from its top-level namespace.

Use these public imports:

```python
from django_api_versioning import endpoint, ver_range, api_reverse
```

The decorators are implemented in `django_api_versioning.decorators`, so importing them directly from that module also works:

```python
from django_api_versioning.decorators import endpoint, ver_range
```

For application code and documentation examples, prefer the top-level import path. It is the package's public API and avoids coupling consumers to the internal module structure.

Import the generated URL patterns from:

```python
from django_api_versioning.urls import urlpatterns as api_urlpatterns
```

The decorator signature in 0.3.4 is:

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

`API_BASE_PATH` must contain the literal `{version}` placeholder.

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

The registry supports:

- Django function-based views.
- Django class-based view classes whose `as_view()` method returns a Django view callable.
- Django REST Framework `APIView` classes.
- DRF generic-view classes.

For a class-based view, the registry calls `as_view()` when it receives the class.

Do not pass an instantiated view object.

A generic view must implement the HTTP handlers required by its registered route.

### ViewSets

A DRF `ViewSet` class cannot be decorated directly with `@endpoint`.

The registry calls `as_view()` without an actions mapping, while DRF ViewSets require an action map.

Use DRF's `DefaultRouter` or `SimpleRouter` for standard ViewSet resource routing.

The package does not automatically generate router-style ViewSet routes or integrate with DRF routers.

A manually configured callable such as:

```python
MyViewSet.as_view({"get": "list"})
```

can be registered as a specific callable route. It is not a replacement for router-generated list, detail, and custom-action routes.

Router setup and mounting remain the application's responsibility.

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

The helper substitutes the parameter values into the registered route and returns a root-relative path:

```text
/api/v2/orders/42/
```

The helper requires all named parameters used by the route.

It does not accept positional `args`. Parameter values are converted using `str()`; Django path converter `to_url()` methods are not called, and converter-level validation is not performed.

### Supported route patterns and limitations

`api_reverse()` supports the package's Django `path()`-based routes.

It does not implement Django's general URL resolver or reverse arbitrary URL patterns.

If no matching pattern exists, it raises Django's `NoReverseMatch`.

If a name is reused for multiple distinct paths at the same version, an explicit version alone does not disambiguate those paths. Avoid reusing the same `view_name` for different routes when calling `api_reverse()`.

If multiple versioned patterns share a name, use an explicit version rather than assuming Django's plain `reverse()` will select the intended route.

## 11. DRF version identification versus package routing

Django REST Framework provides versioning schemes such as:

- `URLPathVersioning`
- `NamespaceVersioning`
- `AcceptHeaderVersioning`
- `QueryParameterVersioning`
- `HostNameVersioning`

These mechanisms identify the requested API version according to a configured strategy.

`django-api-versioning` solves a different problem: it registers version-specific URL patterns and maps them to the declared view implementations.

The package does **not** automatically set `request.version`.

If an application needs DRF's `request.version`, it must configure and integrate the appropriate DRF versioning scheme separately.

In particular, do not assume that DRF's `URLPathVersioning` automatically works with the package's generated routes. That DRF scheme expects a version value in a URL resolver keyword argument, while this package generates literal version segments such as `api/v2/orders/`.

The package's route registration and DRF's request-version identification are separate mechanisms.

## 12. Scope and known limitations

`django-api-versioning` focuses on version-aware endpoint registration and routing.

It does not:

- Automatically make response schemas backward-compatible.
- Select serializers based on a request version.
- Replace DRF authentication or permission classes.
- Replace DRF routers for standard ViewSet resource routing.
- Automatically set `request.version`.
- Automatically integrate with DRF's version-identification schemes.
- Use `API_VERSIONING_CHANNELS` to select routes.
- Use `API_EFFECTIVE_VERSION_RESOLVER` for tenant-specific route selection.
- Validate response payload compatibility through route-matrix checks.
- Automatically version OpenAPI schemas.

Your application remains responsible for API contract design, serializer selection, authentication, permissions, business logic, and request-level compatibility tests.

## 13. Primary source files

The contract above is based on the following implementation and project files:

- [decorators.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/decorators.py)
- [registry.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/registry.py)
- [reverse.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/reverse.py)
- [urls.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/urls.py)
- [settings.py](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/django_api_versioning/settings.py)
- [integration URLconf](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/integration_test_project/project/urls.py)
- [README and installation requirements](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/README.md)
- [DRF ViewSets documentation](https://www.django-rest-framework.org/api-guide/viewsets/)
- [DRF routers documentation](https://www.django-rest-framework.org/api-guide/routers/)
- [DRF versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/)
