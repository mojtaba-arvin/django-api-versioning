<p align="center">
  <a href="https://mojtaba-arvin.github.io/django-api-versioning/">
    <img src="https://raw.githubusercontent.com/mojtaba-arvin/django-api-versioning/main/website/public/favicon.svg" alt="Django API Versioning logo" width="64" height="64">
  </a>
</p>

# Django API Versioning

[![PyPI version](https://img.shields.io/pypi/v/django-api-versioning?logo=pypi&logoColor=white)](https://pypi.org/project/django-api-versioning/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-api-versioning.svg)](https://pypi.org/project/django-api-versioning/)
[![Django versions](https://img.shields.io/badge/django-4.2%20%7C%205.2%20%7C%206.0%20%7C%206.1-blue)](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/tox.ini)
[![Python tests](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/tests.yml/badge.svg)](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/LICENSE)

**Version your Django API by endpoint, not by duplicating URL patterns.** Register a view once; unchanged routes carry forward to later API versions, and a newer declaration replaces the implementation from that version onward.

[Explore Django API Versioning — documentation, examples, and interactive playground](https://mojtaba-arvin.github.io/django-api-versioning/) · [Install django-api-versioning from PyPI](https://pypi.org/project/django-api-versioning/)

## See how it works

Install the package:

```bash
pip install django-api-versioning
```

Django REST Framework is optional. The example below uses DRF views because many projects already do; if you use DRF, install a compatible version separately (see [Requirements](#requirements)).

Declare only the versions where an endpoint's behavior changes:

```python
from rest_framework.response import Response
from rest_framework.views import APIView

from django_api_versioning import endpoint


@endpoint("orders/", version=1, view_name="order-list")
class OrderListV1(APIView):
    def get(self, request):
        return Response({"total": "19.99"})


@endpoint("orders/", version=2, view_name="order-list")
class OrderListV2(APIView):
    def get(self, request):
        return Response({"total": 1999, "currency": "USD"})
```

With `API_MAX_VERSION = 3`, the generated routes are:

| Request | View |
| --- | --- |
| `GET /api/v1/orders/` | `OrderListV1` |
| `GET /api/v2/orders/` | `OrderListV2` |
| `GET /api/v3/orders/` | `OrderListV2` |

The v1 view serves v1 until another declaration replaces it. The v2 view then serves v2 and v3. **You write a new view when the endpoint changes—not another copy of every unchanged route.**

For the complete setup, including Django settings and URL configuration, see the [Django API Versioning getting-started guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/022-django-api-versioning-how-does-it-work/).

## What problem does it solve?

In a growing API, only some endpoints change between releases. Manually maintaining a separate URL configuration for every version can repeat registrations and obscure which implementation handles each version.

Django API Versioning makes that mapping explicit with `@endpoint`:

- **Forward route inheritance:** `version=1` registers the endpoint from v1 through `API_MAX_VERSION`.
- **Version-specific replacement:** a v2 declaration takes over from v2 onward; earlier versions retain the v1 implementation.
- **Explicit registration:** use `versions=[...]` or `ver_range(...)` when an endpoint should exist only in selected versions.
- **Visibility:** inspect the generated route matrix with `python manage.py check_versions --fail-on-empty` and guard it with `assert_version_matrix(snapshot=".version_matrix.json", strict=True)`.

Route registration is inherited; semantic compatibility of responses and business behavior remains an application concern (see [FAQ](#faq)).

## Is it a good fit?

Choose this package when API versions need different view implementations but most routes stay unchanged, and you want those decisions declared once and verified as a route matrix. It supports existing Django views and DRF ViewSets, incremental adoption, and Django-native endpoints without requiring DRF.

If DRF's built-in versioning already identifies the requested version, that may be enough. Serializer and response transformations and tenant policy remain application responsibilities; this package focuses on routing and view selection.

### How it complements Django REST Framework

DRF and this package solve related but different parts of API versioning:

| Responsibility | Django REST Framework | django-api-versioning |
|---|---|---|
| Identify a requested version | Built-in schemes such as URL path, namespace, query parameter, hostname, and Accept header | Select one transport per deployment with `API_VERSIONING_SCHEME`; middleware resolves it before Django selects the registered view |
| Generate ViewSet routes | SimpleRouter and DefaultRouter generate actions and URL patterns | `VersionedRouter` delegates to `SimpleRouter`; since `1.4.0`, `VersionedDefaultRouter` adds a version-specific API root and configurable format suffixes |
| Select a different implementation per version | Application code or separately maintained URL configurations | Declarative endpoint registration and per-generated-route inheritance/replacement |
| Carry unchanged endpoints forward | Application-managed | Built in to the registry |
| Inspect and guard the effective route matrix | Application-managed | check_versions and assert_version_matrix |

**Release status:** `VersionedDefaultRouter` is included in the `1.4.0` release. It is additive: existing `VersionedRouter` behavior and URL-path defaults remain unchanged.

Use DRF's own versioning schemes when request-version identification is all you need. Use ordinary DRF routers when you want to manage each version's URL configuration yourself. Choose this package when you want a central registry to map each negotiated version to the correct endpoint implementation and carry unchanged routes forward. For ViewSets, use VersionedRouter; for Django views, APIView, and GenericAPIView, use @endpoint.

### What it does not do

- It does not combine transports as a fallback chain. A deployment selects exactly one of `path`, `header`, `query`, or `hostname` with `API_VERSIONING_SCHEME`. Tenant-specific policy resolution remains outside the current contract.
- It does not transform serializers or response payloads, guarantee semantic backward compatibility, or replace application contract tests.
- It does not decorate DRF ViewSet classes directly with @endpoint; use VersionedRouter for package-managed SimpleRouter integration.
- VersionedRouter intentionally follows SimpleRouter behavior. Use VersionedDefaultRouter when you also need a version-specific API root and optional format-suffix routes; this is not a drop-in implementation of every DefaultRouter extension.
- The package does not bundle an OpenAPI generator. The repository includes an executable drf-spectacular integration that generates one schema per version and validates changes with oasdiff; these remain consumer-side tooling, not runtime dependencies.
- It does not infer semantic backward compatibility. Route-matrix checks, OpenAPI contract checks, and request-level behavior tests cover different parts of compatibility; see the [API compatibility boundaries](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/api-compatibility-boundaries.md).


**Available since 1.2.0:** Explicit endpoint removal is supported through remove_endpoint() for decorator endpoints and VersionedRouter.remove() for generated DRF actions. Earlier versions retain the route, removed versions return 404, and a later declaration can explicitly reintroduce it. Version 1.2.0 also adds set_endpoint_lifecycle() for decorator endpoints and VersionedRouter.set_lifecycle() for DRF operations. The optional EndpointLifecycleAutoSchema integration marks matching deprecated OpenAPI operations. See the endpoint-removal and endpoint-lifecycle design documents.

## Request version negotiation

The default remains URL-path versioning. For deployments that need a versionless public URL, `VersionNegotiationMiddleware` selects one configured request transport **before Django resolves the URL**. It does not merely set `request.version`: it rewrites the internal path to the selected registered route so the registry and `VersionedRouter` still choose the actual view. This request-negotiation feature is available since `1.3.0`.

Configure one scheme for the whole deployment; do not treat this setting as a priority or fallback list:

| Scheme | Request | Required setting |
| --- | --- | --- |
| path | /api/v2/orders/ | API_VERSIONING_SCHEME = "path" (default) |
| header | /api/orders/ plus Accept-Version: 2 | API_VERSIONING_SCHEME = "header" |
| query | /api/orders/?version=2 | API_VERSIONING_SCHEME = "query" |
| hostname | v2.api.example.com/api/orders/ | API_VERSIONING_SCHEME = "hostname" and an exact host map |

For non-path schemes, install the middleware before components that depend on the resolved path:

```python
# settings.py
API_VERSIONING_SCHEME = "header"
API_VERSIONING_HEADER = "Accept-Version"  # default
API_UNVERSIONED_BASE_PATH = "api/"       # default
API_DEFAULT_VERSION = 1                  # optional; missing version is 400 otherwise

MIDDLEWARE = [
    "django_api_versioning.negotiation.VersionNegotiationMiddleware",
    # CommonMiddleware, application middleware, then LifecycleMiddleware
]
```

Header mode also accepts DRF's media-type form, such as Accept: application/json; version=2. If both it and Accept-Version are supplied, they must agree. Responses add Vary for the selected header fields; reverse proxies and CDNs must include those fields in their cache key.

For query mode, set API_VERSIONING_QUERY_PARAMETER to change the default version parameter. For hostname mode, provide an explicit API_VERSIONING_HOSTS = {"v1.api.example.com": 1, "v2.api.example.com": 2} mapping and keep Django's ALLOWED_HOSTS configured. Wildcard hosts and tenant inference from client-controlled headers are not supported.

Non-path inputs accept ASCII decimal integer values without a v prefix. Malformed or missing values without a default return 400; globally unsupported versions and unmapped hostnames return 406; valid versions without a registered endpoint remain 404. There is no fallback to the newest implementation. API_VERSIONING_CHANNELS is deprecated/inert; use API_VERSIONING_SCHEME.

Request-version negotiation is available in the published `1.3.0` release. See the [request negotiation contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/request-version-negotiation.md) for middleware ordering, reversal, lifecycle, caching, and error semantics.

## Consumer-owned integration boundary

In a consuming project, keep imports of django_api_versioning in one project-owned module, for example project/api_versioning.py. Make your views and root URLconf depend on your own get_urlpatterns() function. When replacing this package, rewrite only that module with ordinary Django path() declarations or DRF routers; business views and the root URLconf need not import package internals. The [executable OpenAPI consumer example](https://github.com/mojtaba-arvin/django-api-versioning/tree/main/examples/openapi_contract) demonstrates this boundary.

## Contract tests

Since `1.3.0`, the package provides `assert_schema_snapshot()` alongside `assert_version_matrix()`. Generate and validate your OpenAPI document with your preferred schema tool, then compare it with a reviewed snapshot per API version. Pair exact snapshots with a semantic breaking-change tool such as oasdiff breaking when additive schema changes should be permitted. Continue to test business behavior, validation, authorization, and error bodies with real requests; schema comparison cannot prove semantic compatibility.

## Why use it with Django REST Framework?

DRF already provides request-version identification and ViewSet route generation. Django API Versioning adds the missing connection between those capabilities: **mapping each concrete API version to the correct ViewSet implementation while inheriting unchanged routes independently**.

For Django-native function-based and class-based views, use `@endpoint`. For DRF `ViewSet` and `ModelViewSet` classes, use the optional `VersionedRouter`. It delegates route generation to DRF's `SimpleRouter`, preserving standard actions, custom `@action` routes, lookup behavior, and action-level configuration. Use `VersionedDefaultRouter` when you also need a version-specific API root and format suffixes.

The optional `VersionedRouterVersioning` adapter exposes the selected version as DRF's `request.version` and keeps `reverse_action()` and hyperlinked serializers version-aware. DRF remains optional for projects that use only Django-native views; the package itself is installed once as shown in [See how it works](#see-how-it-works).

## Quick configuration

Add the package (and DRF, if used) to `INSTALLED_APPS` and configure the supported version range:

```python
# settings.py
INSTALLED_APPS = [
    "rest_framework",  # omit when using Django-native views only
    "django_api_versioning",
]

API_MIN_VERSION = 1
API_MAX_VERSION = 3
# API_BASE_PATH defaults to "api/v{version}/"
```

Import modules containing endpoint declarations before including the generated patterns:

```python
# project/urls.py
from django.urls import include, path

from orders import views as _order_views  # noqa: F401
from django_api_versioning.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("", include(api_urlpatterns)),
]
```

Run the route-matrix check:

```bash
python manage.py check_versions
```

## Registration options

| Declaration | Routes created |
| --- | --- |
| `@endpoint("orders/", version=2)` | v2 through `API_MAX_VERSION` |
| `@endpoint("orders/", versions=[1, 3, 5])` | Only v1, v3, and v5 |
| `@endpoint("health/")` | One unversioned route |

For an inclusive range, use `ver_range(1, 3)`. Other APIs include `api_reverse()` for version-aware URL reversal and `assert_version_matrix()` for regression tests.

See the [versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md) for exact URL construction, import order, collision precedence, validation, and edge cases.

## Versioned DRF ViewSets

Use `VersionedRouter` when you want DRF's normal ViewSet workflow with version-aware implementation dispatch:

```python
# settings.py — configure before importing ViewSet modules
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": (
        "django_api_versioning.routers.VersionedRouterVersioning"
    ),
}
```

```python
# project/urls.py
from django_api_versioning.routers import VersionedRouter
from orders.views import OrderViewSetV1, OrderViewSetV2

router = VersionedRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")
router.register("orders", OrderViewSetV2, version=2, basename="order")

urlpatterns = router.urls
```

With `API_MAX_VERSION = 3`, the routes are served at `/api/v1/orders/`, `/api/v2/orders/`, and `/api/v3/orders/`. V2 replaces only the generated routes it declares. If a custom action exists in V1 but is not redeclared in V2, that action remains inherited in v2 and v3 while list/detail can use V2.

For endpoints that should exist only in selected versions, pass `versions=[1, 3]`; v2 remains a 404. The router also supports `trailing_slash=False` and `use_regex_path=False` for Django path converters.

The adapter is required when ViewSets need `request.version`, `reverse_action()`, or hyperlinked serializer support. You can configure it globally through `REST_FRAMEWORK` as shown above, or set `versioning_class = VersionedRouterVersioning` on selected ViewSets.

### Versioned DefaultRouter behavior

When an API needs DRF's browsable API root and `.json`-style URLs, use `VersionedDefaultRouter` instead:

```python
from django_api_versioning.routers import VersionedDefaultRouter

router = VersionedDefaultRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")
router.register("orders", OrderViewSetV2, version=2, basename="order")

urlpatterns = router.urls
```

Each concrete version gets its own API root (for example, `GET /api/v1/` and `GET /api/v2/`). The root links are built from the effective routes after version inheritance and explicit removals, so a route removed from v3 is not advertised by the v3 root. Format suffixes are enabled by default; set `include_root_view=False` or `include_format_suffixes=False` to disable either feature independently. The root's `.json` URL is available at `/api/v1/.json`. DRF passes the parsed suffix to the action as the `format` keyword argument, so custom ViewSet actions should accept `*args, **kwargs` or an explicit `format` parameter.

This class reuses DRF's `DefaultRouter.APIRootView` and `format_suffix_patterns`; it does not create a parallel route generator. Use one root-owning router per API root path. When combining router instances under the same version prefix, disable extra roots or mount them beneath distinct URL prefixes/namespaces.

For the complete supported boundary and test matrix, see the [version-aware DRF router design](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/versioned-drf-router.md).

**Scope:** `VersionedRouter` delegates to DRF SimpleRouter; `VersionedDefaultRouter` additionally provides a version-specific API root and optional format-suffix routes. It does not reproduce every DefaultRouter extension or transform serializers and response payloads. A route omitted from a later ViewSet remains inherited; remove it explicitly with VersionedRouter.remove() (available since 1.2.0). Non-path negotiation requires `VersionNegotiationMiddleware`; configure one scheme per deployment as described below.

For DRF installation, use a version compatible with your Django release:
```bash
# Django 4.2 compatibility
pip install "djangorestframework>=3.17.2,<3.18"

# Django 5.2, 6.0, or 6.1
pip install "djangorestframework>=3.18.3,<3.19"
```

See the [Versioned DRF ViewSet guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/025-django-api-versioning-viewset-support-limitations/) for route inheritance, reversal, namespaces, and the exact integration boundary.

For the repository's executable OpenAPI workflow, see the [versioned OpenAPI contract example](https://github.com/mojtaba-arvin/django-api-versioning/tree/main/examples/openapi_contract). This consumer example and its `oasdiff` CI gate are repository-level validation tooling, not package runtime features or wheel contents. They do not make drf-spectacular or oasdiff runtime dependencies.

## Requirements

- Python 3.10+
- Django 4.2+ (retained for compatibility with existing 1.x installations)
- Django REST Framework is optional.

**For new deployments, use a currently supported Django release, preferably Django 5.2 LTS or later.** Django 4.2 reached the end of extended support on 7 April 2026. It remains in this package's compatibility matrix for existing projects, but no longer receives Django security fixes. See [Django's supported versions](https://www.djangoproject.com/download/#supported-versions).

The configured CI matrix covers selected combinations of Python 3.10–3.15 and Django 4.2, 5.2, 6.0, and 6.1. DRF is tested against versions supported by each upstream combination: DRF 3.17.2 on Django 4.2, and DRF 3.18.x on Django 5.2, 6.0, and 6.1. DRF 3.18 dropped Django 4.2, so these lines are deliberately pinned separately rather than relying on an unbounded latest version.

See [tox.ini](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/tox.ini) for configured environments and [GitHub Actions](https://github.com/mojtaba-arvin/django-api-versioning/actions) for results tied to a specific commit.

## Upgrading to 1.0.0

Version 1.0.0 tightened API lifecycle configuration and changed the `Deprecation` response header format. If you use `API_VERSION_LIFECYCLE`:

- Every entry must have a `status` of `active`, `deprecated`, or `retired`.
- A deprecated version must define `deprecated_at` as an ISO 8601 date or datetime.
- A retired version must define a `sunset` date.
- The `Deprecation` header now uses the RFC 9745 date-valued Structured Field (for example, `Deprecation: @1767225600`), not the legacy `Deprecation: true` value.

For migration steps, see the [1.0.0 changelog](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/CHANGELOG.md#100---2026-11-16).

## FAQ

### Why isn't the endpoint-to-implementation mapping explicit in `urls.py`?

For teams that prefer "explicit over implicit," this is a deliberate cognitive trade-off. Yes, mapping an endpoint to its implementation is not spelled out line-by-line in `urls.py`. That is intentional: higher DRY at the cost of less readability from URL structure alone. Transparency is not removed—it is moved to tooling and tests. The registry is deterministic, `check_versions` shows the real matrix, and `assert_version_matrix(strict=True)` locks that matrix in CI.

### Does the package provide backward compatibility?

No. The package does not guarantee semantic compatibility and does not claim to. What it provides is: (a) isolation of version implementations at the routing layer, (b) snapshot tooling to lock path contracts, and (c) patterns and executable examples for OpenAPI contract tests and runtime behavior tests. Proving semantic compatibility remains the application's responsibility.

### Is versioning limited to the URL path? What about header, query, or hostname?

Four negotiation methods are supported (`path`, `header`, `query`, `hostname`), but the core resolution model remains path-based. For non-path schemes, middleware rewrites the internal path before Django URL resolution so the same single registry is used. That means the transport used to carry the version can change without duplicating the endpoint model—yet final resolution stays path-oriented. This is a conscious architectural choice to avoid four parallel systems.

### What about maintenance continuity for a single-maintainer package?

Maintainer continuity is a real risk for any single-maintainer package, and we do not deny it. What we can commit to is: (a) a replaceable architecture that keeps exit cost low, (b) a controlled lifecycle that makes migration gradual, and (c) governance documentation and an open invitation to contributors that make the path to additional maintainers clear. None of these replaces a second committed maintainer; we treat that as a residual risk. See [GOVERNANCE.md](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/GOVERNANCE.md).

## Documentation

- [Django API Versioning documentation and interactive playground](https://mojtaba-arvin.github.io/django-api-versioning/) — overview, examples, lifecycle demonstration, and guides.
- [Public API reference](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/index.md) — settings, decorators, routers, reverse, testing helpers, lifecycle, and management commands.
- [Routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md) — implementation-backed behavior and limitations.
- [DRF integration guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/013-drf-version-negotiation-vs-endpoint-registration/).
- [Python and Django compatibility guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/024-django-api-versioning-supported-django-python-versions/).
- [Documentation source map](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/README.md).
- [Request version negotiation design](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/request-version-negotiation.md) — how the selected transport is dispatched, reversed, cached, and secured.
- [API compatibility boundaries](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/api-compatibility-boundaries.md) — separates route, schema, and semantic compatibility and describes the consumer CI guardrails.
- [Maintainer and ownership governance](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/GOVERNANCE.md) — maintainer progression, release handover, and project continuity.

## Quality and release engineering

The repository enforces five independent mutation-testing domains at 100%, line and branch coverage of at least 95% each, public API and OpenAPI consumer contracts, the configured 16-environment Python/Django tox matrix, adversarial security testing, and real Django consumer integration. Release publication additionally requires exact-commit compatibility evidence, validated wheel and source distributions, and installed-artifact checks. See the [quality and release gates](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/quality/release-gates.md) and the [dated quality evidence](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reports/quality-2026-11-23.md).

## Contributing

Bug reports, corrections, and pull requests are welcome. Read the [contribution guidelines](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/CONTRIBUTING.md) and [security policy](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/SECURITY.md).

## License

Released under the [MIT License](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/LICENSE).
