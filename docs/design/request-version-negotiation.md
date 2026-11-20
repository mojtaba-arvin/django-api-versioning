# Request version negotiation

**Status:** Implemented on the current development branch; not part of a published release yet.  
**Scope:** Select one API version transport per deployment and dispatch the request to the matching registered Django view or DRF ViewSet.

## Decision

The application selects exactly one transport with `API_VERSIONING_SCHEME`:

- `path` — existing URL-path behavior and default.
- `header` — `Accept-Version: 2`, or DRF's `Accept: application/json; version=2` form.
- `query` — `?version=2`.
- `hostname` — an exact hostname-to-version mapping in `API_VERSIONING_HOSTS`.

These are supported alternatives, not a fallback chain. A deployment must not accept conflicting sources as competing authorities. In header mode, if both the dedicated header and the Accept media-type parameter are present, they must identify the same version.

## Runtime dispatch

Install `VersionNegotiationMiddleware` before middleware that depends on `request.path_info` (including `CommonMiddleware` and `LifecycleMiddleware`).

For non-path schemes, clients call an unversioned URL below `API_UNVERSIONED_BASE_PATH` (default `api/`). The middleware:

1. Reads the selected transport.
2. Rejects malformed or missing values unless `API_DEFAULT_VERSION` is configured.
3. Rejects globally unsupported versions with 406.
4. Sets `request.requested_api_version`, `request.api_version`, and `request.version`.
5. Rewrites `request.META["PATH_INFO"]` internally from the unversioned prefix to the concrete `API_BASE_PATH` for that version.
6. Lets Django's normal resolver select the actual registered callback. A valid version with no endpoint registration naturally remains a 404.

There is no redirect and no second router. The original URL remains the public URL; only the internal path used for Django resolution changes. The existing registry, route precedence, URLPattern identity, and lifecycle middleware therefore remain the dispatch source of truth.

Path mode does not rewrite the path. It exposes the parsed URL-path version as `request.api_version` and `request.version` before dispatch; DRF's `VersionedRouterVersioning` continues to resolve its version from the router namespace.

## Configuration

The following is illustrative. Keep the chosen scheme and its settings in the consumer project's `settings.py`.

### Header

```python
API_VERSIONING_SCHEME = "header"
API_VERSIONING_HEADER = "Accept-Version"  # default
API_DEFAULT_VERSION = 1  # optional; otherwise a missing version is 400
API_UNVERSIONED_BASE_PATH = "api/"  # default

MIDDLEWARE = [
    "django_api_versioning.negotiation.VersionNegotiationMiddleware",
    # CommonMiddleware and LifecycleMiddleware follow this middleware.
]
```

Clients may send either `Accept-Version: 2` or
`Accept: application/json; version=2`. If both forms are present and conflict,
the request is rejected with 400. Header-selected responses include
`Vary: Accept-Version, Accept`. Reverse proxies and CDNs must honor these
headers in their cache keys.

### Query parameter

```python
API_VERSIONING_SCHEME = "query"
API_VERSIONING_QUERY_PARAMETER = "version"  # default
API_DEFAULT_VERSION = 1  # optional

MIDDLEWARE = [
    "django_api_versioning.negotiation.VersionNegotiationMiddleware",
    # other middleware...
]
```

Repeated version parameters are rejected. Configure shared caches to include
the selected query parameter in their cache keys.

### Hostname

```python
API_VERSIONING_SCHEME = "hostname"
API_VERSIONING_HOSTS = {
    "v1.api.example.com": 1,
    "v2.api.example.com": 2,
}

MIDDLEWARE = [
    "django_api_versioning.negotiation.VersionNegotiationMiddleware",
    # other middleware...
]
```

Hostname matching is exact; wildcards, arbitrary subdomains, URL paths, ports,
and user-supplied tenant headers are not used as version maps. Django's
`request.get_host()` validation (and therefore `ALLOWED_HOSTS`) remains in
force. Behind a reverse proxy, configure Django's trusted proxy settings
correctly before relying on forwarded host information.

### Path

```python
API_VERSIONING_SCHEME = "path"  # default
API_BASE_PATH = "api/v{version}/"  # default

MIDDLEWARE = [
    "django_api_versioning.negotiation.VersionNegotiationMiddleware",
    # other middleware...
]
```

Existing URLs such as `/api/v2/orders/` continue to work unchanged.

## URL reversal

`api_reverse(name, version=N)` and DRF's `VersionedRouterVersioning.reverse()`
respect the configured transport:

- Path mode returns the versioned URL.
- Query mode returns the unversioned path with the configured version query parameter.
- Header and hostname modes return the unversioned path; callers must provide the selected header or use the mapped hostname.

An unversioned path cannot, by itself, encode a header or hostname version. The
reverse helpers do not invent a hostname or claim that a URL alone carries a
header-selected version.

## Errors and security

| Condition | Result |
|---|---:|
| Missing version, with no configured default | 400 |
| Malformed version, repeated query value, or conflicting header values | 400 |
| Hostname without an explicit mapping | 406 |
| Version outside `API_MIN_VERSION` / `API_MAX_VERSION` | 406 |
| Valid version but no endpoint registered for that version | 404 |
| Valid version with a matching registration | Normal view response |

Values are non-negative ASCII decimal integers. Signs, floats, repeated
prefixes, and strings such as `v2` are invalid outside path mode. No nearest
version or newest-view fallback is attempted.

The legacy `API_VERSIONING_CHANNELS` setting remains deprecated and inert; it
does not enable multiple transports or define precedence. Select one scheme
with `API_VERSIONING_SCHEME`. `API_EFFECTIVE_VERSION_RESOLVER` also remains a
reserved policy hook; tenant-pinned version negotiation is not implemented by
this change. DRF token-authenticated `request.user` must not be assumed to be
available during middleware version resolution.

## What this does not promise

This feature selects the registered implementation. It does not transform
serializers or payloads, make different versions semantically compatible, or
replace consumer-owned OpenAPI and request-level contract tests. The
`django_api_versioning.testing.assert_schema_snapshot()` helper provides a
reviewed schema baseline; use a semantic breaking-change tool alongside it
when additive schema evolution is allowed.

## Verification requirements

Before release, the branch must pass:

- middleware tests for each transport, malformed/missing/unsupported versions, default version, hostname allowlist, and real Django callback selection;
- DRF tests for `request.version`, `reverse_action()`, and hyperlinked serializer reversal in header and query modes;
- cache `Vary` tests for Header mode and consumer-side query/host cache-key guidance;
- lifecycle tests proving deprecation and sunset use the effective version;
- Django/Python compatibility matrix, lint, installed-wheel smoke, distribution-content, and existing OpenAPI contract workflows.

The settings and middleware are not considered published support until these
checks pass for the final commit and a package release includes the code.
