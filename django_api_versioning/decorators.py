from functools import wraps
from typing import Callable, Optional, List
from django.views import View
from .settings import api_settings as settings
from .registry import registry
from .exceptions import InvalidVersionError, VersionRangeError, VersionTypeError


def endpoint(
    postfix: str,
    version: Optional[int] = None,
    backward: bool = True,
    app_name: Optional[str] = None,
    view_name: Optional[str] = None,
) -> Callable:
    """
    Decorator to register API views with versioning support.

    - Uses `API_MIN_VERSION` and `API_MAX_VERSION` from Django settings.
    - Supports backward compatibility by registering multiple versions if needed.
    - Ensures that no version lower than `API_MIN_VERSION` is registered.
    
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

    Returns:
        Callable: The decorated view function.

    Raises:
        VersionTypeError: If the provided `version` is not an integer.
        VersionRangeError: If `API_MIN_VERSION` or `API_MAX_VERSION` are not properly set.
    """

    def decorator(func: Callable) -> Callable:
        
        @wraps(func)
        def view(*args, **kwargs):
            # Check if the view is a class-based view (CBV)
            if isinstance(func, type) and issubclass(func, View):
                # For class-based views, ensure it's called as a method
                return func.as_view()(*args, **kwargs)
            return func(*args, **kwargs)

        # Read API versioning settings
        min_version: int = getattr(settings, "API_MIN_VERSION", 1)
        max_version: int = getattr(settings, "API_MAX_VERSION", 1)

        if not isinstance(min_version, int) or not isinstance(max_version, int):
            raise VersionRangeError("API_MIN_VERSION and API_MAX_VERSION must be integers.")
        
        if min_version > max_version:
            raise VersionRangeError("API_MIN_VERSION cannot be greater than API_MAX_VERSION.")
        
        if version is not None and not isinstance(version, int):
            raise VersionTypeError("Version must be an integer or None.")
        
        if version is not None and version > max_version:
            raise InvalidVersionError(f"Version {version} is above the maximum allowed version {max_version}.")

        app_name_part: str = f"{app_name}/" if app_name else ""

        def _register_route(ver: Optional[int]) -> None:
            """Helper function to register a route in the registry."""
            if ver is None:
                base_path = ""  # No version prefix
            else:
                base_path = settings.API_BASE_PATH.format(version=ver)
            route = f"{base_path}{app_name_part}{postfix}"
            registry.register(route, view, view_name)

        def _get_valid_versions() -> List[Optional[int]]:
            """Returns a list of valid versions to register."""
            if version is None:
                # If no version is given, register only the unversioned route
                return [None]  # Just register the unversioned route
            if version < min_version:
                return []  # Ignore versions below min_version
            if backward:
                return list(range(min_version, version + 1))  # Register all versions up to the given version
            return [version]  # Only register the specified version when backward is False

        # Register valid versions
        valid_versions = _get_valid_versions()

        for ver in valid_versions:
            _register_route(ver)

        return view

    return decorator