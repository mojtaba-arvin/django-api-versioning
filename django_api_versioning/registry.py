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
                # If as_view has an 'actions' parameter, it's likely a ViewSet
                if 'actions' in sig.parameters:
                    actions_param = sig.parameters['actions']
                    # If 'actions' has no default, it's required (ViewSet behavior)
                    if actions_param.default == inspect.Parameter.empty:
                        raise TypeError(
                            f"ViewSet '{view.__name__}' cannot be registered directly. "
                            f"Pass a configured callable like: "
                            f"{view.__name__}.as_view({{'get': 'list', 'post': 'create'}})"
                        )
            except Exception:
                # If inspection fails, try calling as_view() anyway
                # to get the original error message if it is indeed a problem
                pass

            try:
                view = view.as_view()
            except TypeError as e:
                # Re-raise with better context if it's an actions-related error
                if "actions" in str(e):
                    raise TypeError(
                        "ViewSet requires action configuration. "
                        "Use view.as_view({'get': 'list', ...}) with appropriate HTTP methods."
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
