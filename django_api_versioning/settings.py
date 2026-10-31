import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .exceptions import (
    VersioningError,
    VersionRangeError,
    VersionTypeError,
)

# Initialize logger
logger = logging.getLogger(__name__)


# Single source of truth for package defaults.
_DEFAULT_API_BASE_PATH = "api/v{version}/"
_DEFAULT_API_MAX_VERSION = 1
_DEFAULT_API_MIN_VERSION = 1
_DEFAULT_ROOT_URLCONF = "django_api_versioning.urls"
_DEFAULT_LIFECYCLE: Dict[int, Dict[str, Any]] = {}
_DEFAULT_CHANNELS: List[str] = ["path"]
_DEFAULT_RESOLVER: Optional[Callable] = None


@dataclass
class APISettings:
    """Validated configuration for API versioning."""

    API_BASE_PATH: str = _DEFAULT_API_BASE_PATH
    API_MAX_VERSION: int = _DEFAULT_API_MAX_VERSION
    API_MIN_VERSION: int = _DEFAULT_API_MIN_VERSION
    ROOT_URLCONF: str = _DEFAULT_ROOT_URLCONF
    API_VERSION_LIFECYCLE: Dict[int, Dict[str, Any]] = field(
        default_factory=lambda: dict(_DEFAULT_LIFECYCLE)
    )
    API_VERSIONING_CHANNELS: List[str] = field(
        default_factory=lambda: list(_DEFAULT_CHANNELS)
    )
    API_EFFECTIVE_VERSION_RESOLVER: Optional[Callable] = _DEFAULT_RESOLVER

    def __post_init__(self) -> None:
        self._validate_base_path()
        self._validate_version_settings()
        self._validate_root_urlconf()
        self._validate_lifecycle()
        self._validate_channels()
        self._validate_resolver()

    @staticmethod
    def get_setting(name: str, default: Any = None) -> Any:
        """
        Reads the setting from Django settings and provides a default if not found.
        """
        return getattr(settings, name, default)

    @classmethod
    def from_django_settings(cls) -> "APISettings":
        """Build validated API settings from Django's configuration."""
        return cls(
            API_BASE_PATH=cls.get_setting("API_BASE_PATH", _DEFAULT_API_BASE_PATH),
            API_MAX_VERSION=cls.get_setting(
                "API_MAX_VERSION", _DEFAULT_API_MAX_VERSION
            ),
            API_MIN_VERSION=cls.get_setting(
                "API_MIN_VERSION", _DEFAULT_API_MIN_VERSION
            ),
            ROOT_URLCONF=cls.get_setting("ROOT_URLCONF", _DEFAULT_ROOT_URLCONF),
            API_VERSION_LIFECYCLE=cls.get_setting(
                "API_VERSION_LIFECYCLE", dict(_DEFAULT_LIFECYCLE)
            ),
            API_VERSIONING_CHANNELS=cls.get_setting(
                "API_VERSIONING_CHANNELS", list(_DEFAULT_CHANNELS)
            ),
            API_EFFECTIVE_VERSION_RESOLVER=cls.get_setting(
                "API_EFFECTIVE_VERSION_RESOLVER", _DEFAULT_RESOLVER
            ),
        )

    def _validate_base_path(self) -> None:
        """Validate and normalize the API URL prefix."""
        if not isinstance(self.API_BASE_PATH, str):
            raise VersioningError("API_BASE_PATH must be a string.")

        if "{version}" not in self.API_BASE_PATH:
            raise VersioningError(
                "API_BASE_PATH must contain '{version}' like 'api/v{version}/' "
                "to support API versioning."
            )

        if not self.API_BASE_PATH.endswith("/"):
            logger.warning(
                "API_BASE_PATH should end with a '/'. Adding '/' automatically."
            )
            self.API_BASE_PATH += "/"

    def _validate_version_settings(self) -> None:
        """Validate version boundaries and their ordering."""
        for name, value in (
            ("API_MIN_VERSION", self.API_MIN_VERSION),
            ("API_MAX_VERSION", self.API_MAX_VERSION),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise VersionTypeError(
                    f"{name} must be an integer, got {type(value).__name__}."
                )

        if self.API_MIN_VERSION > self.API_MAX_VERSION:
            raise VersionRangeError(
                "API_MIN_VERSION cannot be greater than API_MAX_VERSION."
            )

    def _validate_root_urlconf(self) -> None:
        """Ensure Django's root URL configuration is a non-empty string."""
        if not self.ROOT_URLCONF:
            raise ImproperlyConfigured("ROOT_URLCONF is required.")

    def _validate_lifecycle(self) -> None:
        if not isinstance(self.API_VERSION_LIFECYCLE, dict):
            raise VersioningError("API_VERSION_LIFECYCLE must be a dict.")
        for version, meta in self.API_VERSION_LIFECYCLE.items():
            if not isinstance(version, int) or isinstance(version, bool):
                raise VersionTypeError(
                    f"Lifecycle key must be an integer version, got {version!r}."
                )
            if not isinstance(meta, dict):
                raise VersioningError(
                    f"Lifecycle metadata for version {version} must be a dict."
                )

    def _validate_channels(self) -> None:
        allowed = {"path", "header", "query"}
        if not isinstance(self.API_VERSIONING_CHANNELS, list):
            raise VersioningError("API_VERSIONING_CHANNELS must be a list.")
        for channel in self.API_VERSIONING_CHANNELS:
            if channel not in allowed:
                raise VersioningError(
                    f"Unknown versioning channel {channel!r}. "
                    f"Allowed: {sorted(allowed)}."
                )

    def _validate_resolver(self) -> None:
        resolver = self.API_EFFECTIVE_VERSION_RESOLVER
        if resolver is not None and not callable(resolver):
            raise VersioningError(
                "API_EFFECTIVE_VERSION_RESOLVER must be callable or None."
            )


api_settings = APISettings.from_django_settings()
