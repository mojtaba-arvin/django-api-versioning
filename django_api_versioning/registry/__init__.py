from collections.abc import Iterator
from contextlib import contextmanager
from functools import wraps
from threading import RLock
from typing import Callable, cast

from django.http import HttpResponse
from django.urls import URLPattern, path
from django.urls.resolvers import RegexPattern
from django.views import View

from .. import exceptions as _exceptions
from ..exceptions import VersioningError  # noqa: F401
from ..lifecycle_metadata import EndpointLifecycle
from ..route_state import RegistrySnapshot, build_registry_snapshot
from ..settings import api_settings  # noqa: F401
from .lifecycle import EndpointLifecycleStore
from .matrix import (
    REMOVED_ROUTE,  # noqa: F401
    _ROUTER_OWNER_IDENTITY,  # noqa: F401
    _UNOWNED_OWNER_IDENTITY,  # noqa: F401
    VersionMatrix,
    project_logical_version_matrix,
    project_version_matrix,
)
from .resolution import OPERATION_ACTION_RESOLVER_ATTR, ResolvedOperation
from .resolution import ResolvedRouteCandidate as _ResolvedRouteCandidate

ResolvedRouteCandidate = _ResolvedRouteCandidate

# Preserve historical module attributes for callers importing these names
# from django_api_versioning.registry.
InvalidVersionError = _exceptions.InvalidVersionError
VersionRangeError = _exceptions.VersionRangeError
VersionTypeError = _exceptions.VersionTypeError

VersionKey = int | None
RouteSortKey = tuple[bool, VersionKey, bool, int, int]

_MUTATING_METHODS = frozenset(
    {
        "clear",
        "remove",
        "register",
        "register_urlpattern",
        "register_endpoint_lifecycle",
    }
)
_MISSING_ATTRIBUTE = object()
_PATTERN_STATE_ATTRIBUTES = (
    "_django_api_versioning_source_version",
    "_django_api_versioning_route_version",
    "_django_api_versioning_logical_endpoint",
    "_django_api_versioning_router_owner",
    "_django_api_versioning_router_prefix",
    "_django_api_versioning_router_trailing_slash",
)


ViewType = Callable[..., HttpResponse] | type[View]


def _optional_operation_action(
    callback: object,
    method: str,
    allow_unmapped_method: bool = False,
) -> tuple[bool, str | None]:
    """Delegate optional action metadata without coupling core resolution to DRF."""
    capability = getattr(callback, OPERATION_ACTION_RESOLVER_ATTR, None)
    if callable(capability):
        return capability(callback, method, allow_unmapped_method)

    # Direct UrlRegistry registrations predate the callback capability seam.
    # Discover the optional DRF adapter only when the callback advertises
    # method/action metadata; importing the core registry never imports DRF.
    if getattr(callback, "actions", None) is None:
        return True, None
    try:
        from ..routers import resolve_drf_operation_action
    except ImportError:
        return True, None
    return resolve_drf_operation_action(callback, method, allow_unmapped_method)


def _synchronized(method):
    """Serialize registry mutations and keep multi-step checks atomic."""

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            result = method(self, *args, **kwargs)
            if method.__name__ in _MUTATING_METHODS and not self._transaction_stack:
                self._publish_snapshot()
            return result

    return wrapper


class UrlRegistry:
    """Registry for managing API versioning URLs."""

    _SOURCE_VERSION_ATTR = "_django_api_versioning_source_version"
    _ROUTE_VERSION_ATTR = "_django_api_versioning_route_version"
    _LOGICAL_ENDPOINT_ATTR = "_django_api_versioning_logical_endpoint"
    _ROUTER_OWNER_ATTR = "_django_api_versioning_router_owner"
    _ROUTER_PREFIX_ATTR = "_django_api_versioning_router_prefix"
    _ROUTER_TRAILING_SLASH_ATTR = "_django_api_versioning_router_trailing_slash"

    def __init__(self) -> None:
        self._lock = RLock()
        self.urlpatterns: list[URLPattern] = []
        self._removal_boundaries: dict[str, set[int]] = {}
        self._router_removal_boundaries: dict[
            tuple[str, str | None, bool | None], set[int]
        ] = {}
        self._removed_patterns: dict[tuple[object, ...], URLPattern] = {}
        self._lifecycle_store = EndpointLifecycleStore()
        self._transaction_stack: list[tuple[object, ...]] = []
        self._snapshot = build_registry_snapshot(
            generation=0,
            active_patterns=self.urlpatterns,
            removed_patterns=self._removed_patterns,
            lifecycle_state=self._lifecycle_store.records,
            removal_boundaries=self._removal_boundaries,
            router_removal_boundaries=self._router_removal_boundaries,
        )

    @property
    def current_snapshot(self) -> RegistrySnapshot:
        """Return the latest committed immutable registry snapshot."""
        with self._lock:
            return self._snapshot

    def _capture_state(self) -> tuple[object, ...]:
        return (
            list(self.urlpatterns),
            {key: set(value) for key, value in self._removal_boundaries.items()},
            {key: set(value) for key, value in self._router_removal_boundaries.items()},
            dict(self._removed_patterns),
            self._lifecycle_store.snapshot(),
            [
                (
                    pattern,
                    {
                        attribute: getattr(pattern, attribute, _MISSING_ATTRIBUTE)
                        for attribute in _PATTERN_STATE_ATTRIBUTES
                    },
                )
                for pattern in {
                    id(pattern): pattern
                    for pattern in [
                        *self.urlpatterns,
                        *self._removed_patterns.values(),
                    ]
                }.values()
            ],
        )

    def _restore_state(self, state: tuple[object, ...]) -> None:
        (
            active,
            boundaries,
            router_boundaries,
            removed,
            lifecycle,
            pattern_attributes,
        ) = state
        self.urlpatterns[:] = cast(list[URLPattern], active)
        self._removal_boundaries.clear()
        self._removal_boundaries.update(cast(dict[str, set[int]], boundaries))
        self._router_removal_boundaries.clear()
        self._router_removal_boundaries.update(
            cast(dict[tuple[str, str | None, bool | None], set[int]], router_boundaries)
        )
        self._removed_patterns.clear()
        self._removed_patterns.update(
            cast(dict[tuple[object, ...], URLPattern], removed)
        )
        self._lifecycle_store.restore(cast(dict, lifecycle))
        saved_patterns = cast(
            list[tuple[URLPattern, dict[str, object]]], pattern_attributes
        )
        for pattern, attributes in saved_patterns:
            for attribute, value in attributes.items():
                if value is _MISSING_ATTRIBUTE:
                    if hasattr(pattern, attribute):
                        delattr(pattern, attribute)
                else:
                    setattr(pattern, attribute, value)

    def _publish_snapshot(self) -> None:
        candidate = build_registry_snapshot(
            generation=self._snapshot.generation + 1,
            active_patterns=self.urlpatterns,
            removed_patterns=self._removed_patterns,
            lifecycle_state=self._lifecycle_store.records,
            removal_boundaries=self._removal_boundaries,
            router_removal_boundaries=self._router_removal_boundaries,
        )
        if (
            candidate.active_routes == self._snapshot.active_routes
            and candidate.removed_routes == self._snapshot.removed_routes
            and candidate.lifecycle == self._snapshot.lifecycle
            and candidate.removal_boundaries == self._snapshot.removal_boundaries
        ):
            return
        self._snapshot = candidate

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Publish one snapshot on commit and restore state on failure."""
        with self._lock:
            self._transaction_stack.append(self._capture_state())
            try:
                yield
            except BaseException:
                state = self._transaction_stack.pop()
                self._restore_state(state)
                raise
            else:
                self._transaction_stack.pop()
                if not self._transaction_stack:
                    self._publish_snapshot()

    @_synchronized
    def clear(self) -> None:
        """Clear active routes and removal declarations."""
        from .removal import clear

        clear(self)

    @_synchronized
    def remove(
        self,
        logical_endpoint: str,
        from_version: int,
        *,
        owner: object | None = None,
    ) -> None:
        """Suppress an endpoint from a concrete version until reintroduced."""
        from .removal import remove

        remove(self, logical_endpoint, from_version, owner=owner)

    def _removal_boundary(
        self,
        logical_endpoint: str | None,
        route_version: int | None,
        owner: object | None = None,
        router_prefix: str | None = None,
        trailing_slash: bool | None = None,
    ) -> int | None:
        from .removal import removal_boundary

        return removal_boundary(
            self,
            logical_endpoint,
            route_version,
            owner,
            router_prefix,
            trailing_slash,
        )

    def _is_suppressed(
        self,
        logical_endpoint: str | None,
        route_version: int | None,
        source_version: int | None,
        owner: object | None = None,
        router_prefix: str | None = None,
        trailing_slash: bool | None = None,
    ) -> bool:
        from .removal import is_suppressed

        return is_suppressed(
            self,
            logical_endpoint,
            route_version,
            source_version,
            owner,
            router_prefix,
            trailing_slash,
        )

    def _clear_removed_pattern(
        self,
        logical_endpoint: str | None,
        route_version: int | None,
        *,
        owner: object | None,
        router_prefix: str | None,
        trailing_slash: bool | None,
    ) -> None:
        from .removal import clear_removed_pattern

        clear_removed_pattern(
            self,
            logical_endpoint,
            route_version,
            owner=owner,
            router_prefix=router_prefix,
            trailing_slash=trailing_slash,
        )

    def _record_removed(self, pattern: URLPattern, logical_endpoint: str) -> None:
        from .removal import record_removed

        record_removed(self, pattern, logical_endpoint)

    def _has_removed_route(self, logical_endpoint: str, *, owner: object) -> bool:
        from .removal import has_removed_route

        return has_removed_route(self, logical_endpoint, owner=owner)

    @_synchronized
    def register(
        self,
        route: str,
        view: ViewType,
        name: str | None = None,
        source_version: int | None = None,
        route_version: int | None = None,
        logical_endpoint: str | None = None,
    ) -> None:
        """Register a route through the shared registration component."""
        from .registration import register_pattern

        pattern = self._create_pattern(route, view, name)
        register_pattern(
            self,
            pattern,
            source_version=source_version,
            route_version=route_version,
            logical_endpoint=logical_endpoint,
            allow_router_owner=False,
        )

    @_synchronized
    def register_urlpattern(
        self,
        pattern: URLPattern,
        source_version: int | None = None,
        route_version: int | None = None,
        logical_endpoint: str | None = None,
    ) -> None:
        """Register an existing URLPattern through the shared registration core."""
        from .registration import register_pattern

        if not isinstance(pattern, URLPattern):
            raise TypeError("pattern must be a django.urls.URLPattern instance.")
        register_pattern(
            self,
            pattern,
            source_version=source_version,
            route_version=route_version,
            logical_endpoint=logical_endpoint,
            allow_router_owner=True,
        )

    @_synchronized
    def get_route_version(self, route: str) -> int | None:
        """Return the concrete version registered for a resolved route."""
        route_index = next(
            (
                index
                for index, pattern in enumerate(self.urlpatterns)
                if str(pattern.pattern) == route
            ),
            None,
        )
        if route_index is None:
            route_index = self._find_route_index(route)
        if route_index is None:
            return None

        return getattr(
            self.urlpatterns[route_index],
            self._ROUTE_VERSION_ATTR,
            None,
        )

    @_synchronized
    def get_version_matrix(self) -> VersionMatrix:
        """
        Return ``{route: {route_version: callback}}``.

        ``route_version`` is ``None`` for unversioned routes. This remains
        the source of truth for ``check_versions`` and ``assert_version_matrix``,
        projected from the latest immutable registry snapshot.
        """
        return project_version_matrix(self._snapshot)

    @_synchronized
    def get_logical_version_matrix(self) -> VersionMatrix:
        """
        Return ``{logical_endpoint: {route_version: callback}}``.

        Physical URLs are grouped by logical endpoint identity. When independent
        routers or physical routes collide, stable discriminators preserve every
        callback rather than silently overwriting one. The projection reads only
        the latest immutable registry snapshot.
        """
        return project_logical_version_matrix(self._snapshot)

    @staticmethod
    def _canonical_route_key(route: str) -> str:
        from .resolution import canonical_route_key

        return canonical_route_key(route)

    def _find_route_index(
        self,
        route: str,
        *,
        regex_route: bool = False,
    ) -> int | None:
        from .resolution import find_route_index

        return find_route_index(self, route, regex_route=regex_route)

    @staticmethod
    def _resolved_route_match_length(route: str, registered_route: str) -> int:
        from .resolution import resolved_route_match_length

        return resolved_route_match_length(route, registered_route)

    @_synchronized
    def get_resolved_route_version_for_match(
        self, resolver_match: object
    ) -> tuple[bool, int | None]:
        from .resolution import get_resolved_route_version_for_match

        return get_resolved_route_version_for_match(self, resolver_match)

    @_synchronized
    def get_resolved_route_version(self, route: str) -> int | None:
        from .resolution import get_resolved_route_version

        return get_resolved_route_version(self, route)

    @_synchronized
    def resolve_operation(
        self,
        resolver_match: object,
        method: str,
        *,
        allow_unmapped_method: bool = False,
        require_exact_pattern: bool = True,
        action_resolver: Callable | None = None,
    ) -> ResolvedOperation | None:
        from .resolution import resolve_operation

        return resolve_operation(
            self,
            resolver_match,
            method,
            allow_unmapped_method=allow_unmapped_method,
            require_exact_pattern=require_exact_pattern,
            action_resolver=action_resolver or _optional_operation_action,
        )

    @_synchronized
    def resolve_registered_operation(
        self,
        logical_endpoint: str,
        route_version: int,
        method: str,
        *,
        action_resolver: Callable | None = None,
    ) -> ResolvedOperation | None:
        from .resolution import resolve_registered_operation

        return resolve_registered_operation(
            self,
            logical_endpoint,
            route_version,
            method,
            action_resolver=action_resolver or _optional_operation_action,
        )

    @property
    def _endpoint_lifecycle(self) -> dict:
        """Compatibility view of the lifecycle store's authoritative mapping."""
        return self._lifecycle_store.records

    @_synchronized
    def register_endpoint_lifecycle(
        self,
        logical_endpoint: str,
        route_version: int,
        *,
        method: str | None = None,
        action: str | None = None,
        deprecated_at: str | None = None,
        sunset: str | None = None,
        owner: object | None = None,
    ) -> None:
        """Register lifecycle dates for a route, HTTP method, or DRF action."""
        self._lifecycle_store.register(
            logical_endpoint,
            route_version,
            method=method,
            action=action,
            deprecated_at=deprecated_at,
            sunset=sunset,
            owner=owner,
        )

    @_synchronized
    def get_endpoint_lifecycle(
        self, operation: ResolvedOperation
    ) -> EndpointLifecycle | None:
        """Return the most conservative metadata applicable to an operation."""
        return self._lifecycle_store.get(operation)

    def _should_replace(
        self,
        existing_pattern: URLPattern,
        source_version: int | None,
    ) -> bool:
        """Compatibility delegate to the registration component."""
        from .registration import should_replace

        return should_replace(
            existing_pattern, source_version, self._SOURCE_VERSION_ATTR
        )

    @staticmethod
    def _create_pattern(
        route: str,
        view: ViewType,
        name: str | None,
    ) -> URLPattern:
        """Create a URL pattern from a function or class-based view.

        Only class-based views are routed through ``as_view()``. Calling
        ``as_view`` on an instance would still "work" because the classmethod
        is accessible from the instance, but the resulting pattern loses the
        ``view_class`` reference used by ``resolve()`` and DRF.
        """
        if isinstance(view, View):
            raise TypeError(
                f"Pass the view class {type(view).__name__!r}, not an instance. "
                f"Use @endpoint(...) on the class itself, or call "
                f"{type(view).__name__}.as_view() before registering."
            )

        if isinstance(view, type) and callable(getattr(view, "as_view", None)):
            # Check if this is a DRF ViewSet (has actions in signature)
            # ViewSets require an action dict to be passed to as_view()
            try:
                import inspect

                sig = inspect.signature(view.as_view)
            except (TypeError, ValueError):
                # Some extension-backed callables do not expose a signature.
                # Calling as_view() below remains the authoritative check.
                sig = None

            if sig is not None and "actions" in sig.parameters:
                actions_param = sig.parameters["actions"]
                if actions_param.default is inspect.Parameter.empty:
                    raise TypeError(
                        f"ViewSet '{view.__name__}' cannot be registered directly. "
                        f"Pass a configured callable like: "
                        f"{view.__name__}.as_view({{'get': 'list', 'post': 'create'}})"
                    )

            try:
                view = view.as_view()
            except TypeError as e:
                # DRF ViewSetMixin exposes actions=None but rejects a missing map
                # when called. Preserve that runtime signal and add class context.
                if "actions" in str(e):
                    raise TypeError(
                        f"ViewSet '{view.__name__}' cannot be registered directly. "
                        f"Pass a configured callable like: "
                        f"{view.__name__}.as_view({{'get': 'list', 'post': 'create'}})"
                    ) from e
                raise
        return path(route, view, name=name)

    @staticmethod
    def _route_specificity_key(pattern: URLPattern) -> tuple[int, bool, int]:
        """Prefer longer literal prefixes before generic converter/regex routes."""
        route_text = str(pattern.pattern)
        if isinstance(pattern.pattern, RegexPattern):
            source = route_text[1:] if route_text.startswith("^") else route_text
            source = source[:-1] if source.endswith("$") else source
            escaped = False  # pragma: no mutate
            dynamic_start = len(source)
            for index, character in enumerate(source):
                if escaped:
                    escaped = False  # pragma: no mutate
                    continue
                if character == "\\":
                    if index + 1 < len(source) and source[index + 1].isalnum():
                        dynamic_start = index
                        break
                    escaped = True
                    continue
                if character in "([?*+{.^$|)]}":
                    dynamic_start = index
                    break
            literal_prefix = source[:dynamic_start]
            has_dynamic = dynamic_start < len(source)
        else:
            dynamic_start = route_text.find("<")
            literal_prefix = (
                route_text if dynamic_start < 0 else route_text[:dynamic_start]
            )
            has_dynamic = dynamic_start >= 0

        return (-len(literal_prefix), has_dynamic, -len(route_text))

    def _sort_urlpatterns(self) -> None:
        """Order versions first, then static and specific routes before catch-alls."""

        def sort_key(pattern: URLPattern) -> RouteSortKey:
            route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
            specificity = self._route_specificity_key(pattern)
            has_dynamic = specificity[1]
            return (
                route_version is not None,
                route_version,
                has_dynamic,
                specificity[0] * int(has_dynamic),
                specificity[2] * int(has_dynamic),
            )

        self.urlpatterns.sort(key=sort_key)


registry = UrlRegistry()
