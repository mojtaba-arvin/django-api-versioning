import logging
from typing import Callable, List, Optional, TypeVar

from .exceptions import (
    InvalidVersionError,
    VersionRangeError,
    VersionTypeError,
)
from .registry import registry
from .settings import api_settings as settings

logger = logging.getLogger(__name__)
ViewT = TypeVar("ViewT", bound=Callable)


def ver_range(start: int, end: int) -> List[int]:
    """Inclusive range of API versions, e.g. ver_range(1, 3) -> [1, 2, 3]."""
    if start > end:
        raise VersionRangeError(f"ver_range start ({start}) must be <= end ({end}).")
    return list(range(start, end + 1))


def endpoint(
    postfix: str,
    version: Optional[int] = None,
    versions: Optional[List[int]] = None,
    app_name: Optional[str] = None,
    view_name: Optional[str] = None,
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
        InvalidVersionError: If a version exceeds ``API_MAX_VERSION``.
    """
    if version is not None and versions is not None:
        raise VersionRangeError("Use either 'version' or 'versions', not both.")

    def decorator(view: Callable) -> Callable:
        min_version: int = getattr(settings, "API_MIN_VERSION", 1)
        max_version: int = getattr(settings, "API_MAX_VERSION", 1)

        if isinstance(min_version, bool) or not isinstance(min_version, int):
            raise VersionRangeError("API_MIN_VERSION must be an integer.")
        if isinstance(max_version, bool) or not isinstance(max_version, int):
            raise VersionRangeError("API_MAX_VERSION must be an integer.")
        if min_version > max_version:
            raise VersionRangeError(
                "API_MIN_VERSION cannot be greater than API_MAX_VERSION."
            )

        if version is not None:
            _validate_version(version, max_version)
        if versions is not None:
            for v in versions:
                _validate_version(v, max_version)

        app_name_part: str = f"{app_name}/" if app_name else ""

        def _register_route(ver: Optional[int], source_version: Optional[int]) -> None:
            """Helper function to register a route in the registry."""
            if ver is None:
                base_path = ""  # No version prefix
            else:
                base_path = settings.API_BASE_PATH.format(version=ver)
            route = f"{base_path}{app_name_part}{postfix}"
            registry.register(
                route,
                view,
                view_name,
                source_version=source_version,
                route_version=ver,
            )

        if version is not None:
            if version < min_version:
                logger.warning(
                    "Endpoint %r is declared for version %d, but API_MIN_VERSION is %d. "
                    "No routes will be registered.",
                    postfix,
                    version,
                    min_version,
                )
                return view
            for ver in range(version, max_version + 1):
                _register_route(ver, source_version=version)
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
                _register_route(ver, source_version=ver)
        else:
            _register_route(None, source_version=None)

        return view

    return decorator


def _validate_version(version: int, max_version: int) -> None:
    if isinstance(version, bool) or not isinstance(version, int):
        raise VersionTypeError("Version must be an integer.")
    if version > max_version:
        raise InvalidVersionError(
            f"Version {version} is above the maximum allowed version {max_version}."
        )
