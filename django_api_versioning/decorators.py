import logging
from typing import Callable, TypeVar

from .exceptions import (
    InvalidVersionError,
    VersioningError,
    VersionRangeError,
    VersionTypeError,
)
from .registry import registry
from .settings import api_settings as settings

logger = logging.getLogger(__name__)
ViewT = TypeVar("ViewT", bound=Callable)


def _app_name_prefix(app_name: str | None) -> str:
    """Validate and format the optional relative application path prefix."""
    if app_name is None:
        return ""
    if not isinstance(app_name, str):
        raise TypeError("app_name must be a string or None.")
    if app_name == "":
        return ""
    if app_name != app_name.strip():
        raise VersioningError("app_name must not have leading or trailing whitespace.")
    segments = app_name.split("/")
    if any(not segment or segment in {".", ".."} for segment in segments):
        raise VersioningError(
            "app_name must be a relative path without empty, '.' or '..' segments."
        )
    return f"{app_name}/"


def ver_range(start: int, end: int) -> list[int]:
    """Inclusive range of API versions, e.g. ver_range(1, 3) -> [1, 2, 3]."""
    if isinstance(start, bool) or not isinstance(start, int):
        raise VersionTypeError("ver_range start must be an integer.")
    if isinstance(end, bool) or not isinstance(end, int):
        raise VersionTypeError("ver_range end must be an integer.")
    if start > end:
        raise VersionRangeError(f"ver_range start ({start}) must be <= end ({end}).")
    if start < 0:
        raise VersionRangeError("ver_range start must be a non-negative API version.")
    if end > settings.API_MAX_VERSION:
        raise InvalidVersionError(
            f"Version {end} is above the maximum allowed version "
            f"{settings.API_MAX_VERSION}."
        )
    return list(range(start, end + 1))


def _register_endpoint_route(
    postfix: str,
    app_name_part: str,
    view: Callable,
    view_name: str | None,
    version: int | None,
    source_version: int | None,
) -> None:
    """Register one concrete route for an endpoint declaration."""
    base_path = (
        settings.API_BASE_PATH.format(version=version) if version is not None else ""
    )
    route = f"{base_path}{app_name_part}{postfix}"
    registry.register(
        route,
        view,
        view_name,
        source_version=source_version,
        route_version=version,
        logical_endpoint=f"{app_name_part}{postfix}",
    )


def _register_endpoint_routes(
    postfix: str,
    app_name_part: str,
    view: Callable,
    view_name: str | None,
    version: int | None,
    versions: list[int] | None,
    min_version: int,
    max_version: int,
) -> None:
    """Register all concrete versions selected by one endpoint declaration."""
    if version is not None:
        if version < min_version:
            logger.warning(
                "Endpoint %r is declared for version %d, but API_MIN_VERSION is %d. "
                "No routes will be registered.",
                postfix,
                version,
                min_version,
            )
            return
        for ver in range(version, max_version + 1):
            _register_endpoint_route(
                postfix,
                app_name_part,
                view,
                view_name,
                ver,
                source_version=version,
            )
    elif versions is not None:
        for ver in versions:
            if ver < min_version:
                logger.warning(
                    "Endpoint %r is declared for version %d, but API_MIN_VERSION is %d. "
                    "Skipping this version.",
                    postfix,
                    ver,
                    min_version,
                )
                continue
            _register_endpoint_route(
                postfix,
                app_name_part,
                view,
                view_name,
                ver,
                source_version=ver,
            )
    else:
        _register_endpoint_route(
            postfix,
            app_name_part,
            view,
            view_name,
            None,
            source_version=None,
        )


def _register_endpoint_view(
    view: Callable,
    postfix: str,
    version: int | None,
    versions: list[int] | None,
    app_name: str | None,
    view_name: str | None,
) -> None:
    """Register an endpoint view atomically and attach schema identity."""
    min_version: int = settings.API_MIN_VERSION
    max_version: int = settings.API_MAX_VERSION

    if version is not None:
        _validate_version(version, max_version)
    if versions is not None:
        for concrete_version in versions:
            _validate_version(concrete_version, max_version)

    app_name_part = _app_name_prefix(app_name)
    logical_endpoint = f"{app_name_part}{postfix}"
    attribute_name = registry._LOGICAL_ENDPOINT_ATTR
    view_class = getattr(view, "cls", None)
    attribute_targets = [view]
    if isinstance(view_class, type) and view_class is not view:
        attribute_targets.append(view_class)

    missing = object()
    previous_attributes = [
        (
            target,
            getattr(target, attribute_name, missing),
            attribute_name in getattr(target, "__dict__", {}),
        )
        for target in attribute_targets
    ]
    previous_urlpatterns = list(registry.urlpatterns)
    previous_removed_patterns = dict(registry._removed_patterns)

    try:
        for target in attribute_targets:
            setattr(target, attribute_name, logical_endpoint)
        _register_endpoint_routes(
            postfix,
            app_name_part,
            view,
            view_name,
            version,
            versions,
            min_version,
            max_version,
        )
    except Exception:
        registry.urlpatterns[:] = previous_urlpatterns
        registry._removed_patterns.clear()
        registry._removed_patterns.update(previous_removed_patterns)
        for target, previous_value, had_own_attribute in previous_attributes:
            if had_own_attribute:
                setattr(target, attribute_name, previous_value)
            elif previous_value is missing or hasattr(target, "__dict__"):
                try:
                    delattr(target, attribute_name)
                except AttributeError:
                    pass
            else:
                setattr(target, attribute_name, previous_value)
        raise


def endpoint(
    postfix: str,
    version: int | None = None,
    versions: list[int] | None = None,
    app_name: str | None = None,
    view_name: str | None = None,
) -> Callable[[ViewT], ViewT]:
    """
    Register an API view.

    - ``version=N``: segment from N to ``API_MAX_VERSION`` (default, ~80% of cases).
    - ``versions=[...]``: explicit versions, e.g. ``[2, 4, 6]`` or ``ver_range(1, 3)``.
    - Neither: unversioned route.

    Repeated decorators on the same function are allowed for revert scenarios::

        @endpoint("x", version=2)
        @endpoint("x", version=4)
        def x_b(request): ...

    Args:
        postfix: Resource path, e.g. ``"users"`` or ``"users/"``.
        version: Segment start version. Mutually exclusive with ``versions``.
        versions: Explicit versions. Mutually exclusive with ``version``.
        app_name: Optional path segment for grouping.
        view_name: Stable name for ``api_reverse()``.

    Raises:
        VersionRangeError: If both ``version`` and ``versions`` are given, or
            settings are invalid, or ``ver_range`` receives an invalid range.
        VersionTypeError: If a version is not an integer.
        VersioningError: If the route postfix is absolute.
        InvalidVersionError: If a version exceeds ``API_MAX_VERSION``.
    """
    if not isinstance(postfix, str):
        raise TypeError("postfix must be a string.")
    if postfix.startswith("/"):
        raise VersioningError("postfix must be relative and must not start with '/'.")
    _app_name_prefix(app_name)
    if version is not None and versions is not None:
        raise VersionRangeError("Use either 'version' or 'versions', not both.")
    if versions is not None and not isinstance(versions, list):
        raise VersionTypeError("'versions' must be a list of integers.")

    def decorator(view: Callable) -> Callable:
        _register_endpoint_view(
            view,
            postfix,
            version,
            versions,
            app_name,
            view_name,
        )
        if version is not None:
            if version < settings.API_MIN_VERSION:
                return view
        return view

    return decorator


def set_endpoint_lifecycle(
    postfix: str,
    *,
    version: int,
    app_name: str | None = None,
    methods: list[str] | None = None,
    deprecated_at: str | None = None,
    sunset: str | None = None,
) -> None:
    """Declare lifecycle dates for one concrete decorator endpoint version.

    Unlike ``endpoint(version=N)``, this declaration applies only to the
    explicit concrete ``version``. Omitting ``methods`` applies to every
    HTTP method on the logical endpoint; providing methods narrows the scope.
    """
    if not isinstance(postfix, str):
        raise TypeError("postfix must be a string.")
    if postfix.startswith("/"):
        raise VersioningError("postfix must be relative and must not start with '/'.")
    app_name_part = _app_name_prefix(app_name)
    logical_endpoint = f"{app_name_part}{postfix}"

    if methods is None:
        registry.register_endpoint_lifecycle(
            logical_endpoint,
            version,
            deprecated_at=deprecated_at,
            sunset=sunset,
        )
        return

    if not isinstance(methods, list) or not methods:
        raise VersioningError("methods must be a non-empty list of HTTP methods.")
    normalized_methods = [
        method.strip().upper() if isinstance(method, str) else method
        for method in methods
    ]
    if any(not isinstance(method, str) or not method for method in normalized_methods):
        raise VersioningError("methods must contain non-empty HTTP method strings.")
    if len(set(normalized_methods)) != len(normalized_methods):
        raise VersioningError("methods must not contain duplicates.")

    # Match VersionedRouter.set_lifecycle(): a multi-method declaration
    # is one logical operation and must not leave earlier methods registered
    # when a later method conflicts with existing metadata.
    previous_lifecycle = dict(registry._endpoint_lifecycle)
    try:
        for method in normalized_methods:
            registry.register_endpoint_lifecycle(
                logical_endpoint,
                version,
                method=method,
                deprecated_at=deprecated_at,
                sunset=sunset,
            )
    except Exception:
        registry._endpoint_lifecycle.clear()
        registry._endpoint_lifecycle.update(previous_lifecycle)
        raise


def _validate_version(version: int, max_version: int) -> None:
    if isinstance(version, bool) or not isinstance(version, int):
        raise VersionTypeError("Version must be an integer.")
    if version > max_version:
        raise InvalidVersionError(
            f"Version {version} is above the maximum allowed version {max_version}."
        )


def remove_endpoint(
    postfix: str,
    *,
    from_version: int,
    app_name: str | None = None,
) -> None:
    """Remove a logical endpoint from a version onward.

    A later declaration with a higher source version can reintroduce it.
    """
    if not isinstance(postfix, str):
        raise TypeError("postfix must be a string.")
    if postfix.startswith("/"):
        raise VersioningError("postfix must be relative and must not start with '/'.")
    app_name_part = _app_name_prefix(app_name)
    logical_endpoint = f"{app_name_part}{postfix}"

    # The decorator removal API owns only decorator-registered routes. The
    # registry is shared with VersionedRouter, so reject matching router-owned
    # active routes and tombstones before creating a cross-owner boundary.
    def _matches_router_endpoint(endpoint: object) -> bool:
        if not isinstance(endpoint, str):
            return False
        router_prefix = logical_endpoint.rstrip("/")
        return endpoint == logical_endpoint or endpoint.startswith(
            f"{router_prefix}:"
        )

    router_owned = any(
        _matches_router_endpoint(
            getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
        )
        and getattr(pattern, registry._ROUTER_OWNER_ATTR, None) is not None
        for pattern in registry.urlpatterns
    ) or any(
        _matches_router_endpoint(key[0])
        and getattr(pattern, registry._ROUTER_OWNER_ATTR, None) is not None
        for key, pattern in registry._removed_patterns.items()
    )
    if router_owned:
        raise VersioningError(
            f"Endpoint {logical_endpoint!r} is owned by a VersionedRouter; "
            "use router.remove() instead."
        )

    registry.remove(logical_endpoint, from_version)
