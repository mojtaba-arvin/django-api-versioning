import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from string import Formatter
from typing import Any, Callable

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
_DEFAULT_LIFECYCLE: dict[int, dict[str, Any]] = {}
_DEFAULT_CHANNELS: list[str] = ["path"]
_DEFAULT_VERSIONING_SCHEME = "path"
_DEFAULT_HEADER = "Accept-Version"
_DEFAULT_QUERY_PARAMETER = "version"
_DEFAULT_UNVERSIONED_BASE_PATH = "api/"
_DEFAULT_HOSTS: dict[str, int] = {}
_DEFAULT_API_DEFAULT_VERSION: int | None = None
_DEFAULT_RESOLVER: Callable | None = None


@dataclass
class APISettings:
    """Validated configuration for API versioning."""

    API_BASE_PATH: str = _DEFAULT_API_BASE_PATH
    API_MAX_VERSION: int = _DEFAULT_API_MAX_VERSION
    API_MIN_VERSION: int = _DEFAULT_API_MIN_VERSION
    ROOT_URLCONF: str = _DEFAULT_ROOT_URLCONF
    API_VERSION_LIFECYCLE: dict[int, dict[str, Any]] = field(
        default_factory=lambda: dict(_DEFAULT_LIFECYCLE)
    )
    API_VERSIONING_CHANNELS: list[str] = field(
        default_factory=lambda: list(_DEFAULT_CHANNELS)
    )
    API_VERSIONING_SCHEME: str = _DEFAULT_VERSIONING_SCHEME
    API_VERSIONING_HEADER: str = _DEFAULT_HEADER
    API_VERSIONING_QUERY_PARAMETER: str = _DEFAULT_QUERY_PARAMETER
    API_UNVERSIONED_BASE_PATH: str = _DEFAULT_UNVERSIONED_BASE_PATH
    API_VERSIONING_HOSTS: dict[str, int] = field(
        default_factory=lambda: dict(_DEFAULT_HOSTS)
    )
    API_DEFAULT_VERSION: int | None = _DEFAULT_API_DEFAULT_VERSION
    API_EFFECTIVE_VERSION_RESOLVER: Callable | None = _DEFAULT_RESOLVER

    def __post_init__(self) -> None:
        self._validate_base_path()
        self._validate_version_settings()
        self._validate_root_urlconf()
        self._validate_lifecycle()
        self._validate_channels()
        self._validate_negotiation()
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
            API_VERSIONING_SCHEME=cls.get_setting(
                "API_VERSIONING_SCHEME", _DEFAULT_VERSIONING_SCHEME
            ),
            API_VERSIONING_HEADER=cls.get_setting(
                "API_VERSIONING_HEADER", _DEFAULT_HEADER
            ),
            API_VERSIONING_QUERY_PARAMETER=cls.get_setting(
                "API_VERSIONING_QUERY_PARAMETER", _DEFAULT_QUERY_PARAMETER
            ),
            API_UNVERSIONED_BASE_PATH=cls.get_setting(
                "API_UNVERSIONED_BASE_PATH", _DEFAULT_UNVERSIONED_BASE_PATH
            ),
            API_VERSIONING_HOSTS=cls.get_setting(
                "API_VERSIONING_HOSTS", dict(_DEFAULT_HOSTS)
            ),
            API_DEFAULT_VERSION=cls.get_setting(
                "API_DEFAULT_VERSION", _DEFAULT_API_DEFAULT_VERSION
            ),
            API_EFFECTIVE_VERSION_RESOLVER=cls.get_setting(
                "API_EFFECTIVE_VERSION_RESOLVER", _DEFAULT_RESOLVER
            ),
        )

    def _validate_base_path(self) -> None:
        """Validate and normalize the API URL prefix."""
        if not isinstance(self.API_BASE_PATH, str):
            raise VersioningError("API_BASE_PATH must be a string.")

        try:
            format_fields = [
                (field_name, format_spec, conversion)
                for _, field_name, format_spec, conversion in Formatter().parse(
                    self.API_BASE_PATH
                )
                if field_name is not None
            ]
        except ValueError as exc:
            raise VersioningError(
                "API_BASE_PATH must be a valid format string containing exactly "
                "one plain '{version}' field."
            ) from exc

        if format_fields != [("version", "", None)]:
            raise VersioningError(
                "API_BASE_PATH must contain exactly one plain '{version}' field "
                "and no other format fields."
            )

        if self.API_BASE_PATH.startswith("/"):
            raise VersioningError(
                "API_BASE_PATH must be relative and must not start with '/'."
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

        if self.API_MIN_VERSION < 0 or self.API_MAX_VERSION < 0:
            raise VersionRangeError(
                "API_MIN_VERSION and API_MAX_VERSION must be non-negative integers."
            )

        if self.API_MIN_VERSION > self.API_MAX_VERSION:
            raise VersionRangeError(
                "API_MIN_VERSION cannot be greater than API_MAX_VERSION."
            )

    def _validate_root_urlconf(self) -> None:
        """Ensure Django's root URL configuration is a non-empty string."""
        if not isinstance(self.ROOT_URLCONF, str) or not self.ROOT_URLCONF.strip():
            raise ImproperlyConfigured("ROOT_URLCONF must be a non-empty string.")

    def _validate_lifecycle(self) -> None:
        if not isinstance(self.API_VERSION_LIFECYCLE, dict):
            raise VersioningError("API_VERSION_LIFECYCLE must be a dict.")
        for version, meta in self.API_VERSION_LIFECYCLE.items():
            if not isinstance(version, int) or isinstance(version, bool):
                raise VersionTypeError(
                    f"Lifecycle key must be an integer version, got {version!r}."
                )
            if version < 0:
                raise VersionRangeError(
                    "API_VERSION_LIFECYCLE keys must be non-negative integers; "
                    f"got {version}."
                )

            if not isinstance(meta, dict):
                raise VersioningError(
                    f"Lifecycle metadata for version {version} must be a dict."
                )

            status = meta.get("status")
            if not isinstance(status, str) or status not in {
                "active",
                "deprecated",
                "retired",
            }:
                raise VersioningError(
                    f"Lifecycle status for version {version} must be one of "
                    "'active', 'deprecated', or 'retired'."
                )

            if status == "deprecated" and "deprecated_at" not in meta:
                raise VersioningError(
                    f"Deprecated API version {version} requires a "
                    "'deprecated_at' ISO 8601 date or datetime."
                )
            if status == "retired" and "sunset" not in meta:
                raise VersioningError(
                    f"Retired API version {version} requires a 'sunset' date."
                )

            parsed_dates: dict[str, datetime] = {}
            for field_name in ("deprecated_at", "sunset"):
                if field_name not in meta:
                    continue
                value = meta[field_name]
                if not isinstance(value, str):
                    raise VersioningError(
                        f"Lifecycle {field_name} for version {version} "
                        "must be an ISO 8601 string."
                    )
                try:
                    # Normalize UTC's Z suffix for Python 3.10 compatibility.
                    normalized_value = (
                        value[:-1] + "+00:00" if value.endswith("Z") else value
                    )
                    parsed = datetime.fromisoformat(normalized_value)

                    # Match LifecycleMiddleware: timezone-naive values are UTC.
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    else:
                        parsed = parsed.astimezone(timezone.utc)
                except (OverflowError, ValueError) as exc:
                    raise VersioningError(
                        f"Lifecycle {field_name} for version {version} "
                        "must be a valid ISO 8601 date or datetime "
                        "representable in UTC."
                    ) from exc
                parsed_dates[field_name] = parsed

            deprecation_date = parsed_dates.get("deprecated_at")
            sunset_date = parsed_dates.get("sunset")
            if (
                status in {"deprecated", "retired"}
                and deprecation_date is not None
                and sunset_date is not None
                and sunset_date < deprecation_date
            ):
                raise VersioningError(
                    f"Lifecycle sunset for version {version} must not be "
                    "earlier than deprecated_at."
                )

    def _validate_channels(self) -> None:
        allowed = {"path", "header", "query"}
        if not isinstance(self.API_VERSIONING_CHANNELS, list):
            raise VersioningError("API_VERSIONING_CHANNELS must be a list.")
        for channel in self.API_VERSIONING_CHANNELS:
            if not isinstance(channel, str) or channel not in allowed:
                raise VersioningError(
                    f"Unknown versioning channel {channel!r}. "
                    f"Allowed: {sorted(allowed)}."
                )

        if self.API_VERSIONING_CHANNELS != ["path"]:
            logger.warning(
                "API_VERSIONING_CHANNELS is reserved and does not affect route "
                "selection. django-api-versioning currently generates URL-path "
                "routes only; non-default channel values are ignored."
            )

    def _validate_negotiation(self) -> None:
        """Validate the selected request-version transport and its inputs."""
        allowed_schemes = {"path", "header", "query", "hostname"}
        if self.API_VERSIONING_SCHEME not in allowed_schemes:
            raise VersioningError(
                "API_VERSIONING_SCHEME must be one of "
                f"{sorted(allowed_schemes)}."
            )

        for setting_name, value in (
            ("API_VERSIONING_HEADER", self.API_VERSIONING_HEADER),
            ("API_VERSIONING_QUERY_PARAMETER", self.API_VERSIONING_QUERY_PARAMETER),
        ):
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
                or any(char.isspace() for char in value)
            ):
                raise VersioningError(f"{setting_name} must be a non-empty token.")

        if not isinstance(self.API_UNVERSIONED_BASE_PATH, str):
            raise VersioningError("API_UNVERSIONED_BASE_PATH must be a string.")
        if (
            not self.API_UNVERSIONED_BASE_PATH
            or self.API_UNVERSIONED_BASE_PATH.startswith("/")
            or not self.API_UNVERSIONED_BASE_PATH.endswith("/")
            or "{" in self.API_UNVERSIONED_BASE_PATH
            or "}" in self.API_UNVERSIONED_BASE_PATH
            or "//" in self.API_UNVERSIONED_BASE_PATH
        ):
            raise VersioningError(
                "API_UNVERSIONED_BASE_PATH must be a relative path ending in "
                "'/' and must not contain format fields or doubled slashes."
            )

        if not isinstance(self.API_VERSIONING_HOSTS, dict):
            raise VersioningError("API_VERSIONING_HOSTS must be a hostname-to-version dict.")
        normalized_hosts: dict[str, int] = {}
        for hostname, version in self.API_VERSIONING_HOSTS.items():
            if (
                not isinstance(hostname, str)
                or not hostname
                or hostname != hostname.strip()
                or any(char in hostname for char in "/:@*\\\\")
                or any(char.isspace() for char in hostname)
            ):
                raise VersioningError(
                    f"Invalid API_VERSIONING_HOSTS hostname: {hostname!r}."
                )
            normalized = hostname.rstrip(".").encode("idna").decode("ascii").lower()
            if not normalized or normalized in normalized_hosts:
                raise VersioningError(
                    f"Duplicate or invalid normalized API hostname: {hostname!r}."
                )
            if (
                isinstance(version, bool)
                or not isinstance(version, int)
                or version < self.API_MIN_VERSION
                or version > self.API_MAX_VERSION
            ):
                raise VersioningError(
                    f"Hostname {hostname!r} must map to an integer version "
                    f"between {self.API_MIN_VERSION} and {self.API_MAX_VERSION}."
                )
            normalized_hosts[normalized] = version

        if self.API_VERSIONING_SCHEME == "hostname" and not normalized_hosts:
            raise VersioningError(
                "API_VERSIONING_HOSTS must contain at least one mapping when "
                "API_VERSIONING_SCHEME='hostname'."
            )

        if self.API_DEFAULT_VERSION is not None and (
            isinstance(self.API_DEFAULT_VERSION, bool)
            or not isinstance(self.API_DEFAULT_VERSION, int)
            or not self.API_MIN_VERSION
            <= self.API_DEFAULT_VERSION
            <= self.API_MAX_VERSION
        ):
            raise VersioningError(
                "API_DEFAULT_VERSION must be None or an integer within the "
                "configured API_MIN_VERSION/API_MAX_VERSION range."
            )

    def _validate_resolver(self) -> None:
        resolver = self.API_EFFECTIVE_VERSION_RESOLVER
        if resolver is not None and not callable(resolver):
            raise VersioningError(
                "API_EFFECTIVE_VERSION_RESOLVER must be callable or None."
            )
        if resolver is not None:
            logger.warning(
                "API_EFFECTIVE_VERSION_RESOLVER is reserved and is not invoked "
                "by the current route-registration or request lifecycle."
            )


api_settings = APISettings.from_django_settings()
