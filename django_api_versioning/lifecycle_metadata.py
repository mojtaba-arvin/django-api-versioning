"""Normalized metadata and validation for endpoint lifecycle declarations."""

from dataclasses import dataclass
from datetime import datetime, timezone

from .exceptions import VersioningError


@dataclass(frozen=True, slots=True)
class EndpointLifecycle:
    """Deprecation and Sunset instants for one registered endpoint scope."""

    deprecated_at: datetime | None
    sunset: datetime | None


def _parse_date(value: str | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise VersioningError(
            f"Endpoint lifecycle {field_name} must be an ISO 8601 string."
        )

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise VersioningError(
            f"Endpoint lifecycle {field_name} must be a valid ISO 8601 date."
        ) from exc

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_endpoint_lifecycle(
    deprecated_at: str | None,
    sunset: str | None,
) -> EndpointLifecycle:
    """Parse and validate a lifecycle declaration, normalizing dates to UTC."""
    if deprecated_at is None and sunset is None:
        raise VersioningError(
            "An endpoint lifecycle declaration requires deprecated_at or sunset."
        )

    deprecated_date = _parse_date(deprecated_at, "deprecated_at")
    sunset_date = _parse_date(sunset, "sunset")
    if (
        deprecated_date is not None
        and sunset_date is not None
        and sunset_date < deprecated_date
    ):
        raise VersioningError(
            "Endpoint lifecycle sunset must not be earlier than deprecated_at."
        )

    return EndpointLifecycle(
        deprecated_at=deprecated_date,
        sunset=sunset_date,
    )
