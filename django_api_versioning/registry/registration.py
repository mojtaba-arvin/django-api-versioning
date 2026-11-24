"""Single registration engine for the compatibility registry facade.

The facade owns the one authoritative mutable state and transaction boundary.
This module owns declaration collision and source-version precedence decisions.
"""

from django.urls import URLPattern
from django.urls.resolvers import RegexPattern

from ..exceptions import VersioningError


def should_replace(existing_pattern, source_version, source_version_attribute):
    """Return whether a declaration wins over the current route owner."""
    existing_version = getattr(existing_pattern, source_version_attribute, None)
    if existing_version is None or source_version is None:
        return True
    return source_version >= existing_version


def register_pattern(
    registry,
    pattern: URLPattern,
    *,
    source_version: int | None,
    route_version: int | None,
    logical_endpoint: str | None,
    allow_router_owner: bool,
) -> None:
    """Apply one declaration to the registry's authoritative state.

    Both decorator-created patterns and router-created URLPatterns use this
    path, so collision checks, precedence, tombstone handling, and ordering
    cannot drift between the two public facade methods.
    """
    route_key = str(pattern.pattern)
    pattern_owner = getattr(pattern, registry._ROUTER_OWNER_ATTR, None)
    route_index = registry._find_route_index(
        route_key,
        regex_route=isinstance(pattern.pattern, RegexPattern),
    )

    if not allow_router_owner and route_index is not None:
        existing = registry.urlpatterns[route_index]
        if getattr(existing, registry._ROUTER_OWNER_ATTR, None) is not None:
            raise VersioningError(
                f"Route pattern {route_key!r} is already owned by a VersionedRouter; "
                "decorator registration cannot replace it."
            )

    if allow_router_owner and route_index is None:
        new_prefix = getattr(pattern, registry._ROUTER_PREFIX_ATTR, None)
        new_trailing_slash = getattr(
            pattern, registry._ROUTER_TRAILING_SLASH_ATTR, None
        )
        if pattern_owner is not None and new_prefix is not None:
            for existing in registry.urlpatterns:
                existing_owner = getattr(existing, registry._ROUTER_OWNER_ATTR, None)
                if (
                    existing_owner is not None
                    and existing_owner is not pattern_owner
                    and getattr(existing, registry._ROUTER_PREFIX_ATTR, None)
                    == new_prefix
                    and getattr(
                        existing, registry._ROUTER_TRAILING_SLASH_ATTR, None
                    )
                    == new_trailing_slash
                    and getattr(existing, registry._ROUTE_VERSION_ATTR, None)
                    == route_version
                ):
                    raise VersioningError(
                        f"Router prefix {new_prefix!r} in version {route_version} "
                        "is already registered by another VersionedRouter instance."
                    )

    if allow_router_owner and route_index is not None:
        existing = registry.urlpatterns[route_index]
        existing_owner = getattr(existing, registry._ROUTER_OWNER_ATTR, None)
        if (
            existing_owner is not None
            and pattern_owner is not None
            and existing_owner is not pattern_owner
        ):
            existing_prefix = getattr(existing, registry._ROUTER_PREFIX_ATTR, None)
            new_prefix = getattr(pattern, registry._ROUTER_PREFIX_ATTR, None)
            same_router_prefix = (
                existing_prefix is not None
                and existing_prefix == new_prefix
                and getattr(existing, registry._ROUTER_TRAILING_SLASH_ATTR, None)
                == getattr(pattern, registry._ROUTER_TRAILING_SLASH_ATTR, None)
                and getattr(existing, registry._ROUTE_VERSION_ATTR, None)
                == route_version
            )
            if same_router_prefix:
                raise VersioningError(
                    f"Router prefix {new_prefix!r} in version {route_version} "
                    "is already registered by another VersionedRouter instance."
                )
            raise VersioningError(
                f"Route pattern {route_key!r} is already registered by another "
                "VersionedRouter instance. Use a distinct route prefix for each router."
            )

        if (existing_owner is None) != (pattern_owner is None):
            raise VersioningError(
                f"Route pattern {route_key!r} is already registered by a "
                "different registration owner. Use a distinct route path."
            )

    if route_index is not None:
        existing = registry.urlpatterns[route_index]
        if not should_replace(
            existing, source_version, registry._SOURCE_VERSION_ATTR
        ):
            return

    setattr(pattern, registry._SOURCE_VERSION_ATTR, source_version)
    setattr(pattern, registry._ROUTE_VERSION_ATTR, route_version)
    if logical_endpoint is not None:
        setattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, logical_endpoint)

    router_prefix = getattr(pattern, registry._ROUTER_PREFIX_ATTR, None)
    router_trailing_slash = getattr(
        pattern, registry._ROUTER_TRAILING_SLASH_ATTR, None
    )
    if registry._is_suppressed(
        logical_endpoint,
        route_version,
        source_version,
        owner=pattern_owner,
        router_prefix=router_prefix,
        trailing_slash=router_trailing_slash,
    ):
        if route_index is not None:
            existing = registry.urlpatterns[route_index]
            existing_logical = getattr(
                existing, registry._LOGICAL_ENDPOINT_ATTR, None
            )
            existing_version = getattr(existing, registry._ROUTE_VERSION_ATTR, None)
            existing_source = getattr(existing, registry._SOURCE_VERSION_ATTR, None)
            if registry._is_suppressed(
                existing_logical,
                existing_version,
                existing_source,
                owner=getattr(existing, registry._ROUTER_OWNER_ATTR, None),
                router_prefix=getattr(existing, registry._ROUTER_PREFIX_ATTR, None),
                trailing_slash=getattr(
                    existing, registry._ROUTER_TRAILING_SLASH_ATTR, None
                ),
            ):
                del registry.urlpatterns[route_index]
        if logical_endpoint is not None:
            registry._record_removed(pattern, logical_endpoint)
        return

    registry._clear_removed_pattern(
        logical_endpoint,
        route_version,
        owner=pattern_owner,
        router_prefix=router_prefix,
        trailing_slash=router_trailing_slash,
    )

    if route_index is None:
        registry.urlpatterns.append(pattern)
    else:
        registry.urlpatterns[route_index] = pattern

    registry._sort_urlpatterns()
