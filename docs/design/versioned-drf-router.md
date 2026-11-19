# Version-aware DRF ViewSet router

**Status:** Initial `VersionedRouter` integration was merged in PR #37 and shipped in v1.1.0. Mainline follow-ups added explicit route removal (PR #58), endpoint lifecycle metadata (PR #71), and fail-closed cross-router collision handling (PR #83). The latter follow-ups remain under `Unreleased` until a future package release.  
**Target API:** `VersionedRouter` and `VersionedRouterVersioning`  
**Runtime dependency:** Django REST Framework remains optional.  
**Initial scope:** DRF `SimpleRouter` integration; no serializer or response transformation.

## 1. Product problem and boundary

Django REST Framework's routers generate standard ViewSet list/detail routes and dynamic routes declared with `@action`. DRF's versioning schemes expose `request.version` and version-aware reversal, but the application still has to choose which implementation should serve a given API version.

This package adds that missing route-to-implementation layer:

- Register a ViewSet at a version boundary.
- Generate the same complete route set DRF would generate.
- Replace only the routes that changed in a later version.
- Inherit unchanged routes and custom actions into later versions.
- Expose the concrete route version to DRF through `request.version`.
- Keep route registration visible to the package's version matrix, snapshots, reversal helper, and lifecycle middleware.

The package does **not** infer serializer compatibility, transform response payloads, or replace DRF's authentication, permission, throttle, filter, pagination, renderer, or schema systems.

References:
- https://www.django-rest-framework.org/api-guide/routers/
- https://www.django-rest-framework.org/api-guide/viewsets/
- https://www.django-rest-framework.org/api-guide/versioning/

## 2. Public API

```python
from django_api_versioning.routers import VersionedRouter
from orders.views import OrderViewSetV1, OrderViewSetV2

router = VersionedRouter()

router.register(
    "orders",
    OrderViewSetV1,
    version=1,
    basename="order",
)
router.register(
    "orders",
    OrderViewSetV2,
    version=2,
    basename="order",
)

urlpatterns = router.urls
```

With `API_MAX_VERSION = 3`:

- The V1 declaration supplies the v1 route set.
- The V2 declaration replaces matching routes from v2 onward.
- A route introduced only in V2 exists from v2 onward.
- A route that exists in V1 but is not redeclared by V2 remains inherited in v2 and later versions.

Explicit version registration is also supported:

```python
router.register(
    "exports",
    ExportViewSet,
    versions=[1, 3],
    basename="export",
)
```

The v2 export routes do not exist; they return 404 rather than falling forward to another implementation.

The constructor supports DRF's `trailing_slash` and `use_regex_path` options, plus an `app_name` for Django URL resolver metadata.

## 3. Route-level inheritance

Inheritance is per generated URLPattern, not all-or-nothing per ViewSet class.

For example, if V1 defines `list`, `retrieve`, and a `publish` custom action, while V2 redeclares only `list` and `retrieve`:

| Concrete API version | list | retrieve | publish |
| --- | --- | --- | --- |
| v1 | V1 | V1 | V1 |
| v2 | V2 | V2 | V1 inherited |
| v3 | V2 inherited | V2 inherited | V1 inherited |

This preserves DRF-generated callback metadata, action method maps, action-level kwargs, basename, detail/suffix metadata, lookup behavior, and custom URL paths/names.

Omitting an earlier action from a later ViewSet still leaves that action inherited. To remove it, declare the operation explicitly with `VersionedRouter.remove()`; the tombstone applies from the selected version boundary, keeps earlier versions available, and permits deliberate reintroduction by a later source declaration. See [Explicit endpoint removal and reintroduction](endpoint-removal.md). Endpoint lifecycle metadata is a separate capability; see [Endpoint-level lifecycle metadata](endpoint-lifecycle.md).

## 4. Architecture

### 4.1 Delegate route generation to DRF

The implementation creates a DRF `SimpleRouter` for each ViewSet declaration and delegates route generation to its public registration API. It does not copy `SimpleRouter.get_urls()` or reimplement DRF's route templates.

The complete generated Django `URLPattern` objects are passed to the package registry. This preserves both regex-backed patterns (DRF's default) and path-converter patterns (when `use_regex_path=False`). Reconstructing callbacks from route strings is explicitly avoided.

### 4.2 Registry metadata

Each registered pattern retains:
- logical endpoint identity (router prefix plus generated route name);
- source version (the ViewSet declaration that supplied the callback);
- concrete route version (the URL version in which that callback is installed);
- generated URL name and original Django/DRF callback metadata.

The registry remains the source of truth for route precedence, version matrices, strict snapshots, and package-level reversal.

### 4.3 Version namespaces and DRF adapter

The router places each concrete version's URL patterns under a Django namespace named `vN`, while the physical URL continues to use `API_BASE_PATH` (by default `api/v{version}/`).

Configure the adapter as DRF's default versioning class, or set it on the relevant ViewSet:

```python
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "django_api_versioning.routers.VersionedRouterVersioning"
    ),
}
```

The adapter exposes the integer API version as a string through `request.version` (for example, `"2"`, not `"v2"`). It validates `ALLOWED_VERSIONS` using DRF-compatible semantics and preserves the full resolver namespace when reversing URLs. This supports:

- `ViewSet.reverse_action()`;
- `HyperlinkedIdentityField` and `HyperlinkedRelatedField`;
- nested application namespaces around the router.

Mount independent router instances under distinct outer namespaces and give them distinct route prefixes. Identical generated internal route patterns owned by different router instances are rejected with `VersioningError` rather than allowing one router to replace another router's callback (PR #83).

### 4.4 Lifecycle middleware

`LifecycleMiddleware` extracts the version from the configured `API_BASE_PATH` at a path-segment boundary. This supports APIs mounted below parent URL prefixes through nested `include()` calls without matching lookalike segments such as `notapi/v2/`.

### 4.5 Optional dependency boundary

Importing the core package and using Django-native `@endpoint` routes does not import DRF. Importing `django_api_versioning.routers` without DRF raises an actionable optional-dependency error. Applications using `VersionedRouter` must install a DRF release compatible with their Django version.

The tested compatibility lines are:
- DRF 3.17.2 for the Django 4.2 compatibility environments.
- DRF 3.18.3 for Django 5.2, 6.0, and 6.1 compatibility environments.

## 5. URL reversal

There are two distinct reversal contracts:

- `api_reverse(view_name, version=N, ...)` selects a package-registered route and returns its path under Django's script prefix. It is package-relative and does not add an outer URL namespace.
- DRF's `reverse_action()` and hyperlinked serializer fields use `VersionedRouterVersioning`, which qualifies the view name with the active full namespace and produces the correct versioned URL.

`api_reverse()` supports path-converter patterns and regex-backed patterns. Regex reversal is delegated to Django's `URLResolver`; path converters use their registered converter behavior. Duplicate route names within one exact version fail instead of silently selecting an arbitrary pattern.

## 6. Supported scope and non-goals

Supported:
- DRF `SimpleRouter` standard list/detail routes;
- `@action` routes and action method maps;
- explicit basenames and per-version route inheritance;
- explicit `versions=[...]` gaps;
- regex and path-converter routes;
- trailing-slash configuration;
- DRF request version, reverse actions, hyperlinks, and nested namespaces;
- lifecycle headers for APIs mounted below parent URL prefixes.

Not included in this integration:
- DRF `DefaultRouter` API-root and format-suffix parity;
- header, query-parameter, host, or tenant-based negotiation;
- serializer or response-payload transformation;
- automatic backward-compatibility inference;
- implicit removal by omission (removal must be declared explicitly; see [endpoint-removal.md](endpoint-removal.md));
- a replacement OpenAPI generator or schema-diff engine.

Header/query/tenant negotiation remains a separate design decision. DRF already provides version parsers for those channels; a safe implementation would still need a runtime dispatcher, correct cache variation, reverse semantics, and trusted tenant identity. See parent roadmap Issue #36.

The optional versioned OpenAPI integration is implemented separately: drf-spectacular generates each version's schema, the package adapter marks matching deprecated operations, and the consumer contract validates per-version snapshots with oasdiff. The package does not own a competing schema generator or semantic diff engine; see [Versioned OpenAPI contract integration](versioned-openapi-contract.md).

## 7. Verification gates

The implementation is not considered complete unless all of the following remain green:

1. V1/V2 ViewSets with list/detail replacement and V1-only custom action inheritance.
2. Actual HTTP requests proving dispatch and `request.version` for v1, v2, and inherited v3 routes.
3. Explicit version gaps return 404.
4. `reverse_action()` and hyperlinked fields resolve within the active version.
5. Nested namespaces preserve version resolution and reversal.
6. Unversioned registrations remain unversioned.
7. Regex-backed and path-converter URLPatterns reverse correctly.
8. Duplicate basenames and duplicate names within one version fail deterministically.
9. Lifecycle headers work when the API is mounted below a parent URL prefix.
10. Core package imports remain independent of DRF.
11. Full package and integration tests, lint, distribution build, website verification, and the supported Python/Django/DRF matrix pass.

The initial `VersionedRouter` integration shipped in v1.1.0. Explicit removal and endpoint-level lifecycle were added to `main` afterward and are recorded under `Unreleased`; do not infer that those follow-ups are present in the currently published PyPI artifact. Current compatibility evidence is commit-specific and belongs to the corresponding GitHub Actions run, not this design note.
