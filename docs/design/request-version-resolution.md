# Request version resolution: research and architecture decision

**Status:** Historical design record; superseded by [request-version-negotiation.md](request-version-negotiation.md)  
**Original target:** A future minor release for non-path negotiation  
**Current branch status:** The development branch now contains header, query, and hostname request negotiation middleware. The new document is authoritative for its current implementation contract. The published 1.2.2 release remains path-only until a later release includes this work.

## 1. Decision summary

Do not activate `API_VERSIONING_CHANNELS` or `API_EFFECTIVE_VERSION_RESOLVER` as they currently exist. They are reserved settings, and the runtime warnings are intentional. A parser that reads a header or query parameter is not sufficient: the package must use the resolved version to select the corresponding endpoint implementation.

The product boundary remains **version-aware endpoint routing and lifecycle governance**, not a general response-compatibility or serializer-transformation framework.

The current differentiator is the combination of:

- declaring an endpoint implementation only when its behavior changes;
- carrying unchanged route registrations forward to later versions;
- making the generated route matrix inspectable and snapshot-testable;
- applying API deprecation and sunset policy to the version actually being served;
- supporting DRF ViewSets through an optional VersionedRouter while preserving DRF's generated actions and route metadata;
- exposing the selected path version through DRF's request.version and version-aware reversal adapter;
- remaining usable with Django-native views while keeping DRF optional.

This is distinct from DRF's built-in versioning schemes, which identify a request version but leave the application to decide how behavior changes. It also avoids adopting a serializer transformation layer whose schema and data-conversion edge cases would substantially broaden the package's responsibility.

## 2. Developer problems and ecosystem evidence

### 2.1 Request version identification is not implementation selection

Django REST Framework supports URL path, namespace, hostname, query parameter, and Accept-header versioning. It exposes the selected value as `request.version`, but its documentation explicitly leaves behavior variation to the application.

This package solves a neighboring problem: mapping an endpoint and version to the correct Django view, with forward inheritance for unchanged registrations. Its VersionedRouter also provides a path-versioning adapter that exposes the matched route version as DRF's request.version. These capabilities should compose, rather than compete; the adapter does not enable DRF's header/query/host schemes for route dispatch.

References:

- [DRF versioning documentation](https://www.django-rest-framework.org/api-guide/versioning/)
- [DRF versioning implementation](https://github.com/encode/django-rest-framework/blob/main/rest_framework/versioning.py)
- [DRF APIView initialization](https://github.com/encode/django-rest-framework/blob/main/rest_framework/views.py)

### 2.2 Compatibility transforms are powerful but create a larger contract

The `djangorestframework-versioning` project demonstrates a different model: transforms adapt serializer input and output between versions. Its public issue tracker documents unresolved concerns around OpenAPI integration, field required/nullability changes, enum evolution, and exception integration. These are useful examples of the cost of taking ownership of response compatibility; they are not evidence that every competitor or every DRF project has those defects.

References:

- [djangorestframework-versioning on PyPI](https://pypi.org/project/djangorestframework-versioning/)
- [OpenAPI integration issue](https://github.com/binnev/djangorestframework_versioning/issues/11)
- [Transform edge cases](https://github.com/binnev/djangorestframework_versioning/issues/12)
- [DRF API exception integration issue](https://github.com/binnev/djangorestframework_versioning/issues/10)

### 2.3 Tenant-pinned versions are a real use case, but authentication timing matters

An API provider may need a stable default version per customer account while still allowing an explicit, policy-approved request override. Stripe documents an account-level pinned API version with a request-level override. This is a useful design precedent, but it should not be copied as a full compatibility engine.

A generic resolver cannot safely assume that `request.user` is authenticated at the point DRF chooses a version. In DRF's `APIView.initial()`, version determination occurs before `perform_authentication()`. A resolver called during initial version negotiation therefore cannot rely on DRF token authentication having populated the user.

References:

- [Stripe API versioning](https://stripe.com/blog/api-versioning)
- [DRF APIView.initial()](https://github.com/encode/django-rest-framework/blob/main/rest_framework/views.py)

## 3. Why the current settings must not be enabled as-is

### `API_VERSIONING_CHANNELS`

A priority list such as `["header", "path", "query"]` suggests that the package can select the first available value. That is not true for the current router: a path-versioned URL has already selected a concrete callback by the time a view or ordinary middleware-level helper can inspect the request. Returning a different integer from `extract_version()` does not switch the selected callback.

There is also a format mismatch: the current helper reads a dedicated `Accept-Version` header. DRF's `AcceptHeaderVersioning` reads a `version` media-type parameter from the `Accept` header (for example, `Accept: application/json; version=2`). These are different wire contracts and must not be presented as interchangeable.

### `API_EFFECTIVE_VERSION_RESOLVER`

A callable alone does not define:

- whether it chooses a default or overrides an explicit client version;
- which request context is trusted;
- whether the caller may select a version outside the tenant's allowed set;
- how an endpoint missing in that version behaves;
- whether lifecycle headers and sunset enforcement use the requested or effective version;
- how shared caches vary by the effective version and tenant.

Enabling the setting without answering these questions would create a false security and compatibility guarantee.

## 4. Original negotiation proposal (historical)

This section is the accepted direction for a future implementation. It is not a claim about the current package.

### 4.1 One version transport per deployment

Do not interpret the existing channels list as a fallback chain. A deployment selects exactly one transport:

- `path`: current behavior and default; the URL contains the version.
- `accept-version`: a dedicated `Accept-Version: 2` request header.
- `query`: `?version=2`.

For the two non-path transports, trim surrounding HTTP/query whitespace, then accept only ASCII decimal digits with no sign, decimal point, or repeated prefix. Do not accept `v2` in the header or query string; the `v` prefix belongs to the existing URL-path representation.

The dedicated `Accept-Version` field is deliberately distinct from DRF's `Accept: application/json; version=2` media-type negotiation. This avoids reimplementing media-type selection and prevents API-version negotiation from accidentally changing renderer/content-negotiation semantics. A future optional DRF adapter may compose with DRF's own Accept-header scheme, but the core package must not claim that behavior unless it is tested end to end.

The selected transport is explicit and mutually exclusive. Conflicting path/header/query values are not silently reconciled because non-selected transports are ignored in that deployment. When path mode is active, the version in the URL is authoritative.

Path mode continues to use the existing `API_BASE_PATH` template. The non-path modes need one stable, versionless route prefix; the implementation proposal should add a separately validated `API_UNVERSIONED_BASE_PATH` (default `"api/"`) rather than weaken or reinterpret the existing `API_BASE_PATH` contract. A new single-value `API_VERSIONING_SCHEME` would select the transport. The legacy `API_VERSIONING_CHANNELS` list remains reserved and must not become a fallback chain.

### 4.2 Integer version identifiers

The existing integer version model is retained. Wire values in Header/Query mode must be unambiguous ASCII decimal integers; signs, `v` prefixes, floats, empty strings, and partial numeric strings are invalid. The package must never truncate or loosely coerce values such as `2.5` into version `2`. The configured `API_MIN_VERSION` and `API_MAX_VERSION` remain the bounds; this proposal does not add a new positivity constraint.

### 4.3 Resolution stages

The future request lifecycle is:

1. Read the version from the one configured transport.
2. If configured, invoke the effective-version policy resolver with the original Django `HttpRequest` and the parsed requested version (or `None` when omitted).
3. Otherwise use the explicit requested version; when it is omitted, use `API_DEFAULT_VERSION` only if the application configured one.
4. Validate the resulting integer against global version bounds and the endpoint's registered version map.
5. Dispatch exactly one registered view. Do not fall forward to the newest view, nearest version, or another available handler when the selected version is not registered.

The resolver is a policy hook, not a parser and not an implicit "latest version" selector. Its eventual contract must be synchronous and deterministic for a request, return one integer effective version, and fail closed. The resolver may use trusted context established before dispatch (for example, `request.tenant` populated by upstream middleware). The first implementation must not promise access to DRF token-authenticated `request.user` during version resolution.

A tenant policy may use the resolver to choose the tenant's pinned default when no version was requested, or reject/approve an explicit override. The policy must be visible in the application's code; the package must not infer tenant identity, trust arbitrary headers, or query tenant configuration itself.

### 4.4 Missing, malformed, and unavailable versions

The implementation must distinguish:

- missing version with no configured default: `400 Bad Request`; never silently choose the maximum version;
- malformed value: `400 Bad Request`;
- syntactically valid but globally unsupported or policy-denied version: `406 Not Acceptable`;
- valid version for which this endpoint has no registration: `404 Not Found`;
- valid version with a matching registration: dispatch the mapped implementation.

No fallback to a newer endpoint is permitted. That would make a missing route behave differently from the declared route-inheritance contract and could silently expose a response schema the client did not request.

The exact exception classes and Django/DRF response mapping must be fixed in the implementation proposal and covered by tests before the setting becomes public.

### 4.5 Effective version is the single source of truth

The effective version—not merely the raw requested value—must be the value exposed to downstream code as `request.version` (for DRF) and `request.api_version` (for Django-native views). The same effective version must drive:

- endpoint callback selection;
- lifecycle headers and sunset enforcement;
- version-aware URL reversal where the transport can encode a version;
- diagnostics and route-matrix observability.

The package must not expose two competing values as though both were authoritative. If the original client request is useful for logs, it may be retained separately as `request.requested_api_version`.

### 4.6 URL reversal

- Path mode returns a versioned path as it does today.
- Query mode can return an unversioned endpoint URL with an explicit `version` query parameter when a version is supplied.
- Header mode cannot encode the version in a URL; callers must send the `Accept-Version` header. The reverse helper must not imply otherwise.

A reverse call without an explicit version may use only a configured default. It must not guess when more than one implementation is available.

### 4.7 Caching and security

Header-selected responses must include `Vary: Accept-Version`. That response header is part of HTTP's cache-selection contract, but it is not a substitute for configuring every CDN or reverse proxy correctly: the cache must honor the nominated header and include it in its cache key. A CDN configuration that ignores `Vary` or does not forward/cache on `Accept-Version` can still serve the wrong representation.

Query-selected responses use distinct request target URIs, but deployments must not assume that every CDN includes query strings in its cache key. For example, CloudFront cache policies can exclude all query strings or include only selected names. The configured `version` parameter must be included in the cache key and forwarded to the origin whenever query mode is used.

Tenant-specific version selection must also account for the tenant dimension in the application's cache key and vary policy. A tenant identifier should not be trusted merely because it appears in a client-controlled header. If a trusted tenant context cannot be represented safely in the shared cache key, tenant-specific responses must bypass shared caching or be marked private. The package must not allow a shared cache to serve one tenant's effective-version response to another tenant.

The resolver must consume trusted server-side context. A client-supplied version is a request, not authorization to access a tenant's version. Resolver outcomes must be validated against the global version range and the endpoint's registered implementations.

Implementation acceptance tests must verify the response's `Vary` behavior and tenant isolation at the application boundary. CDN cache-key configuration remains a deployment responsibility and must be covered by the consumer's infrastructure tests or deployment checklist.

References:
- [RFC 9111: HTTP Caching, cache keys and Vary](https://www.rfc-editor.org/rfc/rfc9111.html)
- [Cloudflare: Vary and cache-key behavior](https://developers.cloudflare.com/cache/concepts/vary/)
- [Amazon CloudFront: cache policy and query-string cache keys](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cache-key-understand-cache-policy.html)

## 5. Explicit non-goals

The package will not become a serializer transformation framework. It will not promise automatic compatibility for response fields, validation semantics, ORM models, database migrations, or generated OpenAPI schemas. Applications remain responsible for the data contract implemented by each view.

The package will not silently rewrite arbitrary URLs, infer the tenant from untrusted request data, or perform authentication itself.

## 6. Original implementation gates and current status

The following list was the acceptance gate for the original proposal. The development branch now implements the dispatcher, route rewrite, lifecycle version propagation, URL reversal, header cache variation, and exact hostname mapping described in [request-version-negotiation.md](request-version-negotiation.md). The release remains blocked until the final PR gate and full compatibility/packaging verification pass. Tenant policy resolution is still intentionally deferred.

The original gates were:

- one real dispatcher path for non-path modes, selecting the registered view (not merely parsing a value);
- Django function-based and class-based view integration;
- optional DRF integration with verified `request.version` behavior and correct ordering relative to authentication;
- deterministic handling of missing, malformed, denied, unsupported, and endpoint-unregistered versions;
- consistent effective-version use in lifecycle enforcement and headers;
- correct `api_reverse()` behavior for each transport;
- cache-vary and tenant-isolation tests;
- coverage for async/sync views, URLconf inclusion, middleware ordering, and route snapshots;
- full supported Python/Django matrix and installed-wheel smoke tests.

At the time this ADR was written, keeping the warning was safer than enabling a parser without dispatch. The reserved channel list remains inert; the new single-value `API_VERSIONING_SCHEME` is the supported configuration.

## 7. Separate compatibility note: Django 4.2

Django 4.2 reached the end of extended support on 7 April 2026. Keeping it in the current 1.x test matrix can be useful for existing installations, but it should not be presented as the recommended choice for new deployments. Django 5.2 is an LTS line with security support beyond the current 1.x lifecycle.

References:

- [Django supported versions](https://www.djangoproject.com/download/#supported-versions)
- [Django 4.2 end-of-support announcement](https://www.djangoproject.com/weblog/2026/apr/07/django-42-end-of-extended-support/)

## 8. Release decision

This ADR and clearer compatibility guidance are documentation-only and do not justify a package release by themselves. Do not publish a new version until an actual runtime improvement has passed the implementation gates and the existing compatibility, packaging, security, and documentation checks.


## 9. Completed adoption opportunity: DRF ViewSet router integration

The earlier adoption gap was that the `@endpoint` API could not accept a DRF `ViewSet` class directly because `ViewSet.as_view()` requires an action mapping. Registering one manually configured callable covered one route, but did not provide the router-generated list, detail, and extra-action routes.

That gap is now addressed by the optional `VersionedRouter` and `VersionedRouterVersioning` integration in PR #37:

```python
from django_api_versioning.routers import VersionedRouter
from orders.views import OrderViewSetV1, OrderViewSetV2

router = VersionedRouter()
router.register("orders", OrderViewSetV1, version=1, basename="order")
router.register("orders", OrderViewSetV2, version=2, basename="order")
urlpatterns = router.urls
```

The implementation delegates route generation to DRF's `SimpleRouter`, preserves complete Django URLPattern objects and callback metadata, and applies version precedence independently to each generated route. Unchanged custom actions remain inherited. The adapter exposes the concrete path version as `request.version` and preserves namespaces for `reverse_action()` and hyperlinked serializers.

The VersionedRouter's namespace adapter continues to identify the concrete path selected by Django. The optional `VersionNegotiationMiddleware` can select an alternative transport before that same router resolves the request. It does not implement tenant-pinned policy or transform serializers/payloads, and it does not claim `DefaultRouter` API-root or format-suffix parity.

References:
- [Versioned DRF ViewSet guide](https://mojtaba-arvin.github.io/django-api-versioning/articles/025-django-api-versioning-viewset-support-limitations/)
- [VersionedRouter implementation PR #37](https://github.com/mojtaba-arvin/django-api-versioning/pull/37)
- [VersionedRouter implementation design](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/design/versioned-drf-router.md)

### Why negotiation is implemented at the middleware boundary

DRF already supplies common request-version schemes and a custom versioning-class extension point. Reimplementing those parsers provides little differentiation unless the package also solves view selection, cache variation, and tenant policy.

The path-based ViewSet integration removes a documented DRF onboarding limitation while reinforcing the package's core advantage: one declarative registry, inherited route implementations, and a testable version matrix. Non-path negotiation remains a separate, more complex runtime-dispatch problem with a distinct trust and caching model.

