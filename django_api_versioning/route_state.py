"""Immutable projections of the mutable Django route registry state.

The registry remains the sole writer during the staged migration.  These
records deliberately retain callback references but never expose URLPattern
objects or the registry's mutable dictionaries.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping

from django.urls import URLPattern
from django.urls.resolvers import RegexPattern

from .lifecycle_metadata import EndpointLifecycle


@dataclass(frozen=True, slots=True)
class RouteRecord:
    """Immutable metadata for one active or removed physical route."""

    identity: tuple[str, str, int | None, str]
    logical_endpoint: str | None
    route: str
    is_regex: bool
    source_version: int | None
    route_version: int | None
    implementation: Callable[..., Any]
    owner: str
    source_location: str | None
    router_prefix: str | None
    trailing_slash: bool | None
    sequence: int


@dataclass(frozen=True, slots=True)
class LifecycleRecord:
    """Immutable lifecycle metadata with a stable, non-object owner label."""

    logical_endpoint: str
    route_version: int
    method: str | None
    action: str | None
    owner: str | None
    metadata: EndpointLifecycle


@dataclass(frozen=True, slots=True)
class RemovalBoundaryRecord:
    """Immutable suppression boundary, including declarations with no route yet."""

    logical_endpoint: str
    from_version: int
    owner: str
    router_prefix: str | None
    trailing_slash: bool | None


@dataclass(frozen=True, slots=True)
class RegistrySnapshot:
    """A deeply immutable view of one committed registry generation."""

    generation: int
    active_routes: tuple[RouteRecord, ...]
    removed_routes: tuple[RouteRecord, ...]
    lifecycle: tuple[LifecycleRecord, ...]
    removal_boundaries: tuple[RemovalBoundaryRecord, ...]
    active_by_identity: Mapping[tuple[str, str, int | None, str], RouteRecord]
    removed_by_identity: Mapping[tuple[str, str, int | None, str], RouteRecord]

    @property
    def routes(self) -> tuple[RouteRecord, ...]:
        """Return active and removed routes in deterministic snapshot order."""
        return self.active_routes + self.removed_routes


def _owner_label(pattern: URLPattern) -> str:
    owner = getattr(pattern, "_django_api_versioning_router_owner", None)
    if owner is None:
        return "unowned"

    prefix = getattr(pattern, "_django_api_versioning_router_prefix", None)
    trailing_slash = getattr(
        pattern, "_django_api_versioning_router_trailing_slash", None
    )
    if prefix is not None:
        return f"router:{prefix!r}:trailing_slash={trailing_slash!r}"
    return f"router:route={str(pattern.pattern)!r}"


def _source_location(callback: Callable[..., Any]) -> str | None:
    module = getattr(callback, "__module__", None)
    qualified_name = getattr(callback, "__qualname__", None)
    if not isinstance(module, str) or not isinstance(qualified_name, str):
        callback_type = type(callback)
        module = getattr(callback_type, "__module__", None)
        qualified_name = getattr(callback_type, "__qualname__", None)
    if not isinstance(module, str) or not isinstance(qualified_name, str):
        return None
    code = getattr(callback, "__code__", None)
    line = getattr(code, "co_firstlineno", None)
    suffix = f":{line}" if isinstance(line, int) else ""
    return f"{module}.{qualified_name}{suffix}"


def _route_record(pattern: URLPattern, sequence: int) -> RouteRecord:
    route = str(pattern.pattern)
    route_version = getattr(pattern, "_django_api_versioning_route_version", None)
    owner = _owner_label(pattern)
    is_regex = isinstance(pattern.pattern, RegexPattern)
    identity = ("regex" if is_regex else "path", route, route_version, owner)
    return RouteRecord(
        identity=identity,
        logical_endpoint=getattr(
            pattern, "_django_api_versioning_logical_endpoint", None
        ),
        route=route,
        is_regex=is_regex,
        source_version=getattr(pattern, "_django_api_versioning_source_version", None),
        route_version=route_version,
        implementation=pattern.callback,
        owner=owner,
        source_location=_source_location(pattern.callback),
        router_prefix=getattr(pattern, "_django_api_versioning_router_prefix", None),
        trailing_slash=getattr(
            pattern, "_django_api_versioning_router_trailing_slash", None
        ),
        sequence=sequence,
    )


def build_registry_snapshot(
    *,
    generation: int,
    active_patterns: list[URLPattern],
    removed_patterns: Mapping[tuple[object, ...], URLPattern],
    lifecycle_state: Mapping[
        tuple[str, int, str | None, str | None, object | None], EndpointLifecycle
    ],
    removal_boundaries: Mapping[str, set[int]],
    router_removal_boundaries: Mapping[tuple[str, str | None, bool | None], set[int]],
) -> RegistrySnapshot:
    """Build fresh immutable collections from the registry's authoritative state."""
    active = tuple(
        _route_record(pattern, sequence)
        for sequence, pattern in enumerate(active_patterns)
    )

    removed_patterns_ordered = sorted(
        removed_patterns.values(),
        key=lambda pattern: (
            str(pattern.pattern),
            getattr(pattern, "_django_api_versioning_route_version", None) or -1,
            _owner_label(pattern),
            isinstance(pattern.pattern, RegexPattern),
        ),
    )
    removed = tuple(
        _route_record(pattern, len(active) + sequence)
        for sequence, pattern in enumerate(removed_patterns_ordered)
    )

    all_patterns = [*active_patterns, *removed_patterns_ordered]
    owner_labels: dict[int, str] = {}
    for pattern in all_patterns:
        owner = getattr(pattern, "_django_api_versioning_router_owner", None)
        if owner is not None:
            owner_labels[id(owner)] = _owner_label(pattern)

    lifecycle = tuple(
        sorted(
            (
                LifecycleRecord(
                    logical_endpoint=logical_endpoint,
                    route_version=route_version,
                    method=method,
                    action=action,
                    owner=("unowned" if owner is None else owner_labels.get(id(owner))),
                    metadata=metadata,
                )
                for (
                    logical_endpoint,
                    route_version,
                    method,
                    action,
                    owner,
                ), metadata in lifecycle_state.items()
            ),
            key=lambda record: (
                record.logical_endpoint,
                record.route_version,
                record.method or "",
                record.action or "",
                record.owner or "",
            ),
        )
    )

    boundaries = tuple(
        sorted(
            (
                RemovalBoundaryRecord(
                    logical_endpoint=logical_endpoint,
                    from_version=from_version,
                    owner="unowned",
                    router_prefix=None,
                    trailing_slash=None,
                )
                for logical_endpoint, versions in removal_boundaries.items()
                for from_version in versions
            ),
            key=lambda record: (record.logical_endpoint, record.from_version),
        )
    )
    router_boundaries = tuple(
        sorted(
            (
                RemovalBoundaryRecord(
                    logical_endpoint=logical_endpoint,
                    from_version=from_version,
                    owner=f"router:{router_prefix!r}:trailing_slash={trailing_slash!r}",
                    router_prefix=router_prefix,
                    trailing_slash=trailing_slash,
                )
                for (
                    logical_endpoint,
                    router_prefix,
                    trailing_slash,
                ), versions in router_removal_boundaries.items()
                for from_version in versions
            ),
            key=lambda record: (
                record.logical_endpoint,
                record.from_version,
                record.owner,
            ),
        )
    )

    return RegistrySnapshot(
        generation=generation,
        active_routes=active,
        removed_routes=removed,
        lifecycle=lifecycle,
        removal_boundaries=boundaries + router_boundaries,
        active_by_identity=MappingProxyType(
            {record.identity: record for record in active}
        ),
        removed_by_identity=MappingProxyType(
            {record.identity: record for record in removed}
        ),
    )
