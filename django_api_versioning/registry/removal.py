"""Removal boundaries, tombstones, and reintroduction transitions.

UrlRegistry remains the sole state owner and transaction boundary. These
functions centralize all decisions that mutate its removal-related state.
"""

from django.urls import URLPattern

from ..exceptions import InvalidVersionError, VersionRangeError, VersionTypeError
from ..settings import api_settings


def clear(registry):
    """Clear active routes and all removal/lifecycle declarations."""
    registry.urlpatterns.clear()
    registry._removal_boundaries.clear()
    registry._router_removal_boundaries.clear()
    registry._removed_patterns.clear()
    registry._endpoint_lifecycle.clear()


def remove(registry, logical_endpoint, from_version, *, owner=None):
    """Suppress one owned endpoint from a concrete version until reintroduced."""
    if not isinstance(logical_endpoint, str) or not logical_endpoint:
        raise TypeError("logical_endpoint must be a non-empty string.")
    if isinstance(from_version, bool) or not isinstance(from_version, int):
        raise VersionTypeError("Removal version must be an integer.")
    if from_version > api_settings.API_MAX_VERSION:
        raise InvalidVersionError(
            f"Removal version {from_version} is above the maximum allowed "
            f"version {api_settings.API_MAX_VERSION}."
        )
    if from_version < api_settings.API_MIN_VERSION:
        raise VersionRangeError(
            f"Removal version {from_version} is below the minimum allowed "
            f"version {api_settings.API_MIN_VERSION}."
        )

    if owner is None:
        registry._removal_boundaries.setdefault(logical_endpoint, set()).add(
            from_version
        )
    else:
        owner_patterns = [
            pattern
            for pattern in [
                *registry.urlpatterns,
                *registry._removed_patterns.values(),
            ]
            if getattr(pattern, registry._ROUTER_OWNER_ATTR, None) is owner
            and getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
            == logical_endpoint
        ]
        route_identities = {
            (
                getattr(pattern, registry._ROUTER_PREFIX_ATTR, None),
                getattr(pattern, registry._ROUTER_TRAILING_SLASH_ATTR, None),
            )
            for pattern in owner_patterns
        }
        for router_prefix, trailing_slash in route_identities:
            registry._router_removal_boundaries.setdefault(
                (logical_endpoint, router_prefix, trailing_slash), set()
            ).add(from_version)

    preserved_versions = set()
    for index in range(len(registry.urlpatterns) - 1, -1, -1):
        pattern = registry.urlpatterns[index]
        if getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None) != logical_endpoint:
            continue
        if getattr(pattern, registry._ROUTER_OWNER_ATTR, None) is not owner:
            continue
        route_version = getattr(pattern, registry._ROUTE_VERSION_ATTR, None)
        source_version = getattr(pattern, registry._SOURCE_VERSION_ATTR, None)
        if route_version is None or route_version < from_version:
            continue
        if source_version is not None and source_version > from_version:
            preserved_versions.add(route_version)
            continue
        record_removed(registry, pattern, logical_endpoint)
        del registry.urlpatterns[index]

    # Lifecycle metadata belongs to a concrete active declaration segment.
    # Preserve it only for versions that already have a newer active source.
    for key in list(registry._endpoint_lifecycle):
        endpoint, version, _, _, metadata_owner = key
        if (
            metadata_owner is owner
            and endpoint == logical_endpoint
            and version >= from_version
            and version not in preserved_versions
        ):
            del registry._endpoint_lifecycle[key]


def removal_boundary(
    registry,
    logical_endpoint,
    route_version,
    owner=None,
    router_prefix=None,
    trailing_slash=None,
):
    """Return the latest removal boundary applicable to one route identity."""
    if logical_endpoint is None or route_version is None:
        return None
    if owner is None:
        boundaries = registry._removal_boundaries.get(logical_endpoint, set())
    else:
        boundaries = registry._router_removal_boundaries.get(
            (logical_endpoint, router_prefix, trailing_slash), set()
        )
    applicable = [boundary for boundary in boundaries if boundary <= route_version]
    return max(applicable) if applicable else None


def is_suppressed(
    registry,
    logical_endpoint,
    route_version,
    source_version,
    owner=None,
    router_prefix=None,
    trailing_slash=None,
):
    """Return whether a source declaration is hidden by an applicable tombstone."""
    boundary = removal_boundary(
        registry,
        logical_endpoint,
        route_version,
        owner,
        router_prefix,
        trailing_slash,
    )
    return boundary is not None and (
        source_version is None or source_version <= boundary
    )


def clear_removed_pattern(
    registry,
    logical_endpoint,
    route_version,
    *,
    owner,
    router_prefix,
    trailing_slash,
):
    """Clear the matching tombstone when a declaration is reintroduced."""
    if logical_endpoint is None or route_version is None:
        return
    if owner is None:
        key = (logical_endpoint, route_version)
    else:
        key = (logical_endpoint, route_version, router_prefix, trailing_slash)
    registry._removed_patterns.pop(key, None)


def record_removed(registry, pattern: URLPattern, logical_endpoint: str) -> None:
    """Record a removed declaration without transferring another owner's tombstone."""
    route_version = getattr(pattern, registry._ROUTE_VERSION_ATTR, None)
    if route_version is None:
        return

    owner = getattr(pattern, registry._ROUTER_OWNER_ATTR, None)
    if owner is None:
        key = (logical_endpoint, route_version)
    else:
        key = (
            logical_endpoint,
            route_version,
            getattr(pattern, registry._ROUTER_PREFIX_ATTR, None),
            getattr(pattern, registry._ROUTER_TRAILING_SLASH_ATTR, None),
        )
    existing = registry._removed_patterns.get(key)
    if existing is not None:
        existing_owner = getattr(existing, registry._ROUTER_OWNER_ATTR, None)
        new_owner = getattr(pattern, registry._ROUTER_OWNER_ATTR, None)
        if existing_owner is not new_owner:
            return

    registry._removed_patterns[key] = pattern
