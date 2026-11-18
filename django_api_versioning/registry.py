from typing import Callable

from django.http import HttpResponse
from django.urls import URLPattern, path
from django.views import View

from .exceptions import InvalidVersionError, VersionRangeError, VersionTypeError
from .settings import api_settings

REMOVED_ROUTE = object()

ViewType = Callable[..., HttpResponse] | type[View]


class UrlRegistry:
    """Registry for managing API versioning URLs."""

    _SOURCE_VERSION_ATTR = "_django_api_versioning_source_version"
    _ROUTE_VERSION_ATTR = "_django_api_versioning_route_version"
    _LOGICAL_ENDPOINT_ATTR = "_django_api_versioning_logical_endpoint"

    def __init__(self) -> None:
        self.urlpatterns: list[URLPattern] = []
        self._removal_boundaries: dict[str, set[int]] = {}
        self._removed_patterns: dict[tuple[str, int], URLPattern] = {}

    def clear(self) -> None:
        """Clear active routes and removal declarations."""
        self.urlpatterns.clear()
        self._removal_boundaries.clear()
        self._removed_patterns.clear()

    def remove(self, logical_endpoint: str, from_version: int) -> None:
        """Suppress an endpoint from a concrete version until reintroduced."""
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

        self._removal_boundaries.setdefault(logical_endpoint, set()).add(from_version)

        for index in range(len(self.urlpatterns) - 1, -1, -1):
            pattern = self.urlpatterns[index]
            if getattr(pattern, self._LOGICAL_ENDPOINT_ATTR, None) != logical_endpoint:
                continue
            route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
            source_version = getattr(pattern, self._SOURCE_VERSION_ATTR, None)
            if route_version is None or route_version < from_version:
                continue
            if source_version is not None and source_version > from_version:
                continue
            self._removed_patterns[(logical_endpoint, route_version)] = pattern
            del self.urlpatterns[index]

    def _removal_boundary(
        self,
        logical_endpoint: str | None,
        route_version: int | None,
    ) -> int | None:
        if logical_endpoint is None or route_version is None:
            return None
        boundaries = self._removal_boundaries.get(logical_endpoint, set())
        applicable = [boundary for boundary in boundaries if boundary <= route_version]
        return max(applicable) if applicable else None

    def _is_suppressed(
        self,
        logical_endpoint: str | None,
        route_version: int | None,
        source_version: int | None,
    ) -> bool:
        boundary = self._removal_boundary(logical_endpoint, route_version)
        return boundary is not None and (
            source_version is None or source_version <= boundary
        )

    def _record_removed(self, pattern: URLPattern, logical_endpoint: str) -> None:
        route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
        if route_version is not None:
            self._removed_patterns[(logical_endpoint, route_version)] = pattern

    def register(
        self,
        route: str,
        view: ViewType,
        name: str | None = None,
        source_version: int | None = None,
        route_version: int | None = None,
        logical_endpoint: str | None = None,
    ) -> None:
        """Register a route, preferring definitions from newer source versions."""
        route_index = self._find_route_index(route)

        if route_index is not None:
            existing_pattern = self.urlpatterns[route_index]

            if not self._should_replace(existing_pattern, source_version):
                return

        pattern = self._create_pattern(route, view, name)
        setattr(pattern, self._SOURCE_VERSION_ATTR, source_version)
        setattr(pattern, self._ROUTE_VERSION_ATTR, route_version)
        if logical_endpoint is not None:
            setattr(pattern, self._LOGICAL_ENDPOINT_ATTR, logical_endpoint)

        if self._is_suppressed(logical_endpoint, route_version, source_version):
            if route_index is not None:
                existing = self.urlpatterns[route_index]
                existing_logical = getattr(existing, self._LOGICAL_ENDPOINT_ATTR, None)
                existing_version = getattr(existing, self._ROUTE_VERSION_ATTR, None)
                existing_source = getattr(existing, self._SOURCE_VERSION_ATTR, None)
                if self._is_suppressed(existing_logical, existing_version, existing_source):
                    del self.urlpatterns[route_index]
            if logical_endpoint is not None:
                self._record_removed(pattern, logical_endpoint)
            return

        if logical_endpoint is not None and route_version is not None:
            self._removed_patterns.pop((logical_endpoint, route_version), None)

        if route_index is None:
            self.urlpatterns.append(pattern)
        else:
            self.urlpatterns[route_index] = pattern

        self._sort_urlpatterns()

    def register_urlpattern(
        self,
        pattern: URLPattern,
        source_version: int | None = None,
        route_version: int | None = None,
        logical_endpoint: str | None = None,
    ) -> None:
        """Register an existing Django URLPattern without rebuilding it.

        This is the lossless insertion path for integrations that generate
        URLPatterns themselves (for example, DRF routers). The original
        pattern, callback, converters, defaults, name, and callback metadata
        are retained. Collision precedence is identical to ``register()``.
        """
        if not isinstance(pattern, URLPattern):
            raise TypeError("pattern must be a django.urls.URLPattern instance.")

        route_key = str(pattern.pattern)
        route_index = self._find_route_index(route_key)

        if route_index is not None:
            existing_pattern = self.urlpatterns[route_index]
            if not self._should_replace(existing_pattern, source_version):
                return

        setattr(pattern, self._SOURCE_VERSION_ATTR, source_version)
        setattr(pattern, self._ROUTE_VERSION_ATTR, route_version)
        if logical_endpoint is not None:
            setattr(pattern, self._LOGICAL_ENDPOINT_ATTR, logical_endpoint)

        if self._is_suppressed(logical_endpoint, route_version, source_version):
            if route_index is not None:
                existing = self.urlpatterns[route_index]
                existing_logical = getattr(existing, self._LOGICAL_ENDPOINT_ATTR, None)
                existing_version = getattr(existing, self._ROUTE_VERSION_ATTR, None)
                existing_source = getattr(existing, self._SOURCE_VERSION_ATTR, None)
                if self._is_suppressed(existing_logical, existing_version, existing_source):
                    del self.urlpatterns[route_index]
            if logical_endpoint is not None:
                self._record_removed(pattern, logical_endpoint)
            return

        if logical_endpoint is not None and route_version is not None:
            self._removed_patterns.pop((logical_endpoint, route_version), None)

        if route_index is None:
            self.urlpatterns.append(pattern)
        else:
            self.urlpatterns[route_index] = pattern

        self._sort_urlpatterns()

    def get_route_version(self, route: str) -> int | None:
        """Return the concrete version registered for a resolved route."""
        route_index = self._find_route_index(route)
        if route_index is None:
            return None

        return getattr(
            self.urlpatterns[route_index],
            self._ROUTE_VERSION_ATTR,
            None,
        )

    def get_version_matrix(self) -> dict[str, dict[int | None, Callable]]:
        """
        Return ``{route: {route_version: callback}}``.

        ``route_version`` is ``None`` for unversioned routes.  This is the
        source of truth for ``check_versions`` and ``assert_version_matrix``.
        """
        matrix: dict[str, dict[int | None, Callable]] = {}
        for pattern in self.urlpatterns:
            route = str(pattern.pattern)
            route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
            matrix.setdefault(route, {})[route_version] = pattern.callback
        for (_, route_version), pattern in self._removed_patterns.items():
            route = str(pattern.pattern)
            matrix.setdefault(route, {})[route_version] = REMOVED_ROUTE
        return matrix

    def get_logical_version_matrix(self) -> dict[str, dict[int | None, Callable]]:
        """
        Return ``{logical_endpoint: {route_version: callback}}``.

        Groups physical URLs by their logical endpoint identity. This is used
        by check_versions to correctly identify gaps within each logical
        endpoint's version span, avoiding false warnings.
        """
        matrix: dict[str, dict[int | None, Callable]] = {}
        for pattern in self.urlpatterns:
            # Use logical endpoint if available, else fall back to route pattern
            logical_id = getattr(
                pattern, self._LOGICAL_ENDPOINT_ATTR, str(pattern.pattern)
            )
            route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
            matrix.setdefault(logical_id, {})[route_version] = pattern.callback
        for (logical_id, route_version), _pattern in self._removed_patterns.items():
            matrix.setdefault(logical_id, {})[route_version] = REMOVED_ROUTE
        return matrix

    def _find_route_index(self, route: str) -> int | None:
        """Return the index of a registered route, or None if absent."""
        for index, pattern in enumerate(self.urlpatterns):
            if str(pattern.pattern) == route:
                return index

        return None

    def _should_replace(
        self,
        existing_pattern: URLPattern,
        source_version: int | None,
    ) -> bool:
        """Return whether the new declaration should replace the existing one.

        Newer ``source_version`` values win. When either side has no source
        version (e.g. unversioned endpoints or direct ``register()`` calls),
        the last registration wins.
        """
        existing_version = getattr(
            existing_pattern,
            self._SOURCE_VERSION_ATTR,
            None,
        )

        if existing_version is None or source_version is None:
            return True

        return source_version >= existing_version

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

    def _sort_urlpatterns(self) -> None:
        """Order unversioned routes first, then versioned routes by version."""
        unversioned: list[URLPattern] = []
        versioned: list[URLPattern] = []

        for pattern in self.urlpatterns:
            route_version = getattr(
                pattern,
                self._ROUTE_VERSION_ATTR,
                None,
            )

            if route_version is None:
                unversioned.append(pattern)
            else:
                versioned.append(pattern)

        versioned.sort(
            key=lambda p: getattr(
                p,
                self._ROUTE_VERSION_ATTR,
            )
        )

        self.urlpatterns[:] = unversioned + versioned


registry = UrlRegistry()
