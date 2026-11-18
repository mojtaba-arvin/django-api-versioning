from typing import Callable

from django.http import HttpResponse
from django.urls import URLPattern, path
from django.views import View

ViewType = Callable[..., HttpResponse] | type[View]


class UrlRegistry:
    """Registry for managing API versioning URLs."""

    _SOURCE_VERSION_ATTR = "_django_api_versioning_source_version"
    _ROUTE_VERSION_ATTR = "_django_api_versioning_route_version"
    _LOGICAL_ENDPOINT_ATTR = "_django_api_versioning_logical_endpoint"

    def __init__(self) -> None:
        self.urlpatterns: list[URLPattern] = []

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

    def get_resolved_route_version(self, route: str) -> int | None:
        """Resolve a version from the longest registered route suffix.

        Django's ResolverMatch.route includes every parent URLResolver prefix.
        Matching a registered route as a complete suffix therefore supports
        nested includes without confusing a parent API-like prefix for the
        child endpoint's version.
        """
        matches: list[tuple[int, int]] = []
        for pattern in self.urlpatterns:
            registered_pattern = str(pattern.pattern)
            pattern_variants = {registered_pattern}
            normalized_pattern = registered_pattern.removeprefix("^").removesuffix("$")
            pattern_variants.add(normalized_pattern)

            matched_length = 0
            for candidate in pattern_variants:
                start = len(route) - len(candidate)
                if start < 0 or route[start:] != candidate:
                    continue
                if start and route[start - 1] != "/":
                    continue
                matched_length = max(matched_length, len(candidate))

            version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
            if (
                matched_length
                and isinstance(version, int)
                and not isinstance(version, bool)
            ):
                matches.append((matched_length, version))

        if not matches:
            return None

        longest = max(length for length, _ in matches)
        versions = {version for length, version in matches if length == longest}
        return next(iter(versions)) if len(versions) == 1 else None

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
