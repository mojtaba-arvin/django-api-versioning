import logging
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from dataclasses import dataclass
from typing import Optional, Any
from .exceptions import VersionTypeError, VersionRangeError, VersioningError

# Initialize logger
logger = logging.getLogger(__name__)

@dataclass
class APISettings:
    
    API_BASE_PATH: str = "api/v{version}/"
    API_MAX_VERSION: int = 1
    API_MIN_VERSION: int = 1
    ROOT_URLCONF: str = 'django_api_versioning.urls'

    @staticmethod
    def get_setting(name: str, default: Optional[Any] = None) -> Any:
        """
        Reads the setting from Django settings and provides a default if not found.
        """
        return getattr(settings, name, default)
    
    def __post_init__(self):
        # Ensure API_BASE_PATH contains "{version}"
        if "{version}" not in self.API_BASE_PATH:
            raise VersioningError("API_BASE_PATH must contain '{version}' like 'api/v{version}/' to support API versioning.")
        
        # Ensure that API_BASE_PATH ends with a "/"
        if not self.API_BASE_PATH.endswith("/"):
            logger.warning("API_BASE_PATH should end with a '/'. Adding '/' automatically.")
            self.API_BASE_PATH += "/"

        # Validate version settings
        self.validate_version_settings()

        if not self.ROOT_URLCONF:
            raise ImproperlyConfigured("ROOT_URLCONF is required in settings.")

    def validate_version_settings(self) -> None:
        """
        Validates that the API_MIN_VERSION and API_MAX_VERSION are integers
        and that API_MIN_VERSION is not greater than API_MAX_VERSION.
        """
        if not isinstance(self.API_MIN_VERSION, int):
            raise VersionTypeError(f"API_MIN_VERSION must be an integer, got {type(self.API_MIN_VERSION).__name__}.")
        
        if not isinstance(self.API_MAX_VERSION, int):
            raise VersionTypeError(f"API_MAX_VERSION must be an integer, got {type(self.API_MAX_VERSION).__name__}.")
        
        if self.API_MIN_VERSION > self.API_MAX_VERSION:
            raise VersionRangeError("API_MIN_VERSION cannot be greater than API_MAX_VERSION.")


# Adding default settings if not defined in Django settings
default_settings = {
    'API_BASE_PATH': "api/v{version}/",
    'API_MAX_VERSION': 1,
    'API_MIN_VERSION': 1,
    'ROOT_URLCONF': 'django_api_versioning.urls',
}

# Override default settings with actual Django settings if they exist
for setting, default_value in default_settings.items():
    setattr(settings, setting, getattr(settings, setting, default_value))

# Initialize APISettings from Django settings
api_settings = APISettings(
    API_BASE_PATH=APISettings.get_setting("API_BASE_PATH", "api/v{version}/"),
    API_MAX_VERSION=APISettings.get_setting("API_MAX_VERSION", 1),
    API_MIN_VERSION=APISettings.get_setting("API_MIN_VERSION", 1),
    ROOT_URLCONF=APISettings.get_setting("ROOT_URLCONF", 'django_api_versioning.urls')
)
