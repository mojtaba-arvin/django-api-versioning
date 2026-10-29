import logging
from typing import Callable, List, Optional, TypeVar

from .exceptions import (
    ForwardTypeError,
    InvalidVersionError,
    VersionRangeError,
    VersionTypeError,
)
from .registry import registry
from .settings import api_settings as settings

logger = logging.getLogger(__name__)

ViewT = TypeVar("ViewT", bound=Callable)


def endpoint(
    postfix: str,
    version: Optional[int] = None,
    backward: bool = True,
    app_name: Optional[str] = None,
    view_name: Optional[str] = None,
    forward: Optional[bool] = None,
) -> Callable[[ViewT], ViewT]:
    """
    Decorator to register API views with versioning support.

    - Uses `API_MIN_VERSION` and `API_MAX_VERSION` from Django settings.
    - Supports backward compatibility by registering multiple versions if needed.
    - Ensures that no version lower than `API_MIN_VERSION` is registered.
    - Supports forward inheritance by registering routes for future versions if needed.

    Args:
        postfix (str): The endpoint suffix (e.g., "users" →
                    "api/v1/users").
        version (Optional[int]): The version of the API. Defaults
                                to None (unversioned).
        backward (bool): If True, registers routes for all versions
                        from `API_MIN_VERSION` up to the current
                        version, which is less than or equal to
                        `API_MAX_VERSION`. Defaults to True.
        app_name (Optional[str]): The app name to be prefixed to
                                the route.
        view_name (Optional[str]): The custom view name for Django.
        forward (Optional[bool]): If True, registers routes for
                                future versions up to `API_MAX_VERSION`.
                                Defaults to None (follow
                                ``API_FORWARD_INHERITANCE``).

    Returns:
        Callable: The decorated view, unchanged.

    Raises:
        VersionTypeError: If ``version`` is not an integer or ``None``.
        VersionRangeError: If ``API_MIN_VERSION`` or ``API_MAX_VERSION`` are
            not integers, or if the range is invalid.
        InvalidVersionError: If ``version`` exceeds ``API_MAX_VERSION``.
        ForwardTypeError: If ``forward`` is not a boolean or ``None``.
    """

    def decorator(view: Callable) -> Callable:
        # Read API versioning settings
        min_version: int = getattr(settings, "API_MIN_VERSION", 1)
        max_version: int = getattr(settings, "API_MAX_VERSION", 1)

        if not isinstance(min_version, int) or not isinstance(max_version, int):
            raise VersionRangeError(
                "API_MIN_VERSION and API_MAX_VERSION must be integers."
            )

        if min_version > max_version:
            raise VersionRangeError(
                "API_MIN_VERSION cannot be greater than API_MAX_VERSION."
            )

        if version is not None and (
            isinstance(version, bool) or not isinstance(version, int)
        ):
            raise VersionTypeError("Version must be an integer or None.")

        if version is not None and version > max_version:
            raise InvalidVersionError(
                f"Version {version} is above the maximum allowed version {max_version}."
            )

        if forward is not None and not isinstance(forward, bool):
            raise ForwardTypeError("Forward must be a boolean or None.")

        effective_forward = (
            settings.API_FORWARD_INHERITANCE if forward is None else forward
        )
        app_name_part: str = f"{app_name}/" if app_name else ""

        def _register_route(ver: Optional[int]) -> None:
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
                source_version=version,
                route_version=ver,
            )

        def _get_valid_versions() -> List[Optional[int]]:
            """Returns a list of valid versions to register."""
            if version is None:
                # If no version is given, register only the unversioned route
                return [None]  # Just register the unversioned route
            if version < min_version:
                # Ignore versions below min_version
                logger.warning(
                    "Endpoint %r is declared for version %d, but "
                    "API_MIN_VERSION is %d. No routes will be registered.",
                    postfix,
                    version,
                    min_version,
                )
                return []

            versions: List[Optional[int]] = (
                list(range(min_version, version + 1)) if backward else [version]
            )
            if effective_forward:
                # Register all versions up to max_version
                versions.extend(range(version + 1, max_version + 1))

            return versions

        # Register valid versions
        valid_versions = _get_valid_versions()

        for ver in valid_versions:
            _register_route(ver)

        return view

    return decorator
