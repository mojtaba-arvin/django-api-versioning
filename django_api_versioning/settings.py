import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .exceptions import (
    ForwardTypeError,
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
_DEFAULT_API_FORWARD_INHERITANCE = False
_DEFAULT_ROOT_URLCONF = "django_api_versioning.urls"


# Django settings-module defaults.
# These are ordinary module-level settings, not runtime mutations.
API_BASE_PATH = _DEFAULT_API_BASE_PATH
API_MAX_VERSION = _DEFAULT_API_MAX_VERSION
API_MIN_VERSION = _DEFAULT_API_MIN_VERSION
API_FORWARD_INHERITANCE = _DEFAULT_API_FORWARD_INHERITANCE
ROOT_URLCONF = _DEFAULT_ROOT_URLCONF


@dataclass
class APISettings:
    """Validated configuration for API versioning."""

    API_BASE_PATH: str = _DEFAULT_API_BASE_PATH
    API_MAX_VERSION: int = _DEFAULT_API_MAX_VERSION
    API_MIN_VERSION: int = _DEFAULT_API_MIN_VERSION
    API_FORWARD_INHERITANCE: bool = _DEFAULT_API_FORWARD_INHERITANCE
    ROOT_URLCONF: str = _DEFAULT_ROOT_URLCONF

    def __post_init__(self) -> None:
        self._validate_base_path()
        self._validate_version_settings()
        self._validate_forward_inheritance()
        self._validate_root_urlconf()

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
            API_BASE_PATH=cls.get_setting(
                "API_BASE_PATH",
                _DEFAULT_API_BASE_PATH,
            ),
            API_MAX_VERSION=cls.get_setting(
                "API_MAX_VERSION",
                _DEFAULT_API_MAX_VERSION,
            ),
            API_MIN_VERSION=cls.get_setting(
                "API_MIN_VERSION",
                _DEFAULT_API_MIN_VERSION,
            ),
            API_FORWARD_INHERITANCE=cls.get_setting(
                "API_FORWARD_INHERITANCE",
                _DEFAULT_API_FORWARD_INHERITANCE,
            ),
            ROOT_URLCONF=cls.get_setting(
                "ROOT_URLCONF",
                _DEFAULT_ROOT_URLCONF,
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
        version_settings = (
            ("API_MIN_VERSION", self.API_MIN_VERSION),
            ("API_MAX_VERSION", self.API_MAX_VERSION),
        )

        for name, value in version_settings:
            if isinstance(value, bool) or not isinstance(value, int):
                raise VersionTypeError(
                    f"{name} must be an integer, got {type(value).__name__}."
                )

        if self.API_MIN_VERSION > self.API_MAX_VERSION:
            raise VersionRangeError(
                "API_MIN_VERSION cannot be greater than API_MAX_VERSION."
            )

    def _validate_forward_inheritance(self) -> None:
        """Ensure forward inheritance is explicitly enabled or disabled."""
        if not isinstance(self.API_FORWARD_INHERITANCE, bool):
            raise ForwardTypeError("API_FORWARD_INHERITANCE must be a boolean.")

    def _validate_root_urlconf(self) -> None:
        """Ensure Django's root URL configuration is a non-empty string."""
        if not isinstance(self.ROOT_URLCONF, str) or not self.ROOT_URLCONF.strip():
            raise ImproperlyConfigured("ROOT_URLCONF is required in settings.")


# Initialize APISettings from Django settings
api_settings = APISettings.from_django_settings()
