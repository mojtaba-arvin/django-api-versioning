import logging
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any, Callable

from django.conf import settings as django_settings
from django.http import HttpRequest, HttpResponse, HttpResponseGone

from .registry import registry
from .settings import api_settings

logger = logging.getLogger(__name__)


def _get_api_setting(name: str, default: Any = None) -> Any:
    """
    Get API setting from django.conf.settings at request time.

    This ensures that override_settings in tests affects middleware behavior.
    For backward compatibility with monkeypatch-based tests, also checks
    the cached api_settings object if the setting is not found in django.conf.settings.

    Falls back to default if setting is not configured in either location.
    """
    if hasattr(django_settings, name):
        return getattr(django_settings, name)

    if hasattr(api_settings, name):
        return getattr(api_settings, name)

    return default


class LifecycleMiddleware:
    """
    Inject Deprecation / Sunset headers and enforce version-wide sunset.

    Resolved requests use Django's actual resolver match. Unresolved requests
    retain path-based lifecycle behavior only when the API version is
    unambiguous.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable,
        view_args: list,
        view_kwargs: dict,
    ) -> HttpResponse | None:
        """Enforce sunset after URL resolution and before the selected view."""
        state = _get_lifecycle_state(request)
        if state is None:
            return None

        version, meta, _, sunset_date = state
        if not meta or sunset_date is None or not _is_past(sunset_date):
            return None

        request._django_api_version_lifecycle_sunset_enforced = True
        sunset = meta.get("sunset")
        return HttpResponseGone(
            f"API version {version} has been retired as of {sunset}."
        )

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """Apply lifecycle headers or preserve version-wide 410 behavior."""
        state = _get_lifecycle_state(request)
        if state is not None:
            version, meta, version_deprecation_date, version_sunset_date = state

        # Version-wide retirement remains authoritative and is evaluated
        # before endpoint metadata. Endpoint Sunset never changes the status
        # code or suppresses the existing version-wide 410 contract.
        if (
            state is not None
            and state[1]
            and state[3] is not None
            and _is_past(state[3])
        ):
            if not getattr(
                request, "_django_api_version_lifecycle_sunset_enforced", False
            ):
                sunset = state[1].get("sunset")
                response = HttpResponseGone(
                    f"API version {state[0]} has been retired as of {sunset}."
                )

        endpoint_lifecycle = _get_endpoint_lifecycle_state(
            request,
            allow_unmapped_method=response.status_code == 405,
        )
        if (state is None or not state[1]) and endpoint_lifecycle is None:
            return response

        deprecation_dates = []
        sunset_dates = []

        if state is not None and state[1]:
            version, meta, version_deprecation_date, version_sunset_date = state
            status = meta.get("status")
            if status in ("deprecated", "retired"):
                if version_deprecation_date is not None:
                    deprecation_dates.append(version_deprecation_date)
                elif status == "deprecated":
                    logger.warning(
                        "Deprecated API version %s has no valid deprecated_at date; "
                        "omitting the Deprecation header.",
                        version,
                    )
                if version_sunset_date is not None:
                    sunset_dates.append(version_sunset_date)

        if endpoint_lifecycle is not None:
            if endpoint_lifecycle.deprecated_at is not None:
                deprecation_dates.append(endpoint_lifecycle.deprecated_at)
            if endpoint_lifecycle.sunset is not None:
                sunset_dates.append(endpoint_lifecycle.sunset)

        if deprecation_dates:
            response["Deprecation"] = _to_structured_field_date(min(deprecation_dates))
        if sunset_dates:
            response["Sunset"] = _to_http_date(min(sunset_dates))
        return response


def _get_lifecycle_state(
    request: HttpRequest,
) -> tuple[int, dict | None, datetime | None, datetime | None] | None:
    """Resolve and cache lifecycle metadata once per request."""
    if hasattr(request, "_django_api_version_lifecycle_state"):
        return request._django_api_version_lifecycle_state

    version = _extract_version(request)
    if version is None:
        return None

    lifecycle = _get_api_setting("API_VERSION_LIFECYCLE", {})
    meta = lifecycle.get(version)
    if not meta:
        state = (version, None, None, None)
    else:
        deprecated_at = meta.get("deprecated_at")
        deprecation_date = (
            _parse_lifecycle_date(deprecated_at, "deprecation")
            if deprecated_at
            else None
        )
        sunset = meta.get("sunset")
        sunset_date = _parse_sunset(sunset) if sunset else None
        state = (version, meta, deprecation_date, sunset_date)

    request._django_api_version_lifecycle_state = state
    return state


def _get_endpoint_lifecycle_state(
    request: HttpRequest,
    *,
    allow_unmapped_method: bool = False,
):
    """Resolve endpoint lifecycle metadata from Django's actual URL match."""
    cache_attr = (
        "_django_api_endpoint_lifecycle_state_405"
        if allow_unmapped_method
        else "_django_api_endpoint_lifecycle_state"
    )
    if hasattr(request, cache_attr):
        return getattr(request, cache_attr)

    match = getattr(request, "resolver_match", None)
    if match is None:
        lifecycle = None
    else:
        operation = registry.resolve_operation(
            match,
            request.method,
            allow_unmapped_method=allow_unmapped_method,
        )
        lifecycle = (
            registry.get_endpoint_lifecycle(operation)
            if operation is not None
            else None
        )

    setattr(request, cache_attr, lifecycle)
    return lifecycle


def _coerce_version(value: Any) -> int | None:
    """Accept integer versions without truncating booleans or other numeric types."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        try:
            return int(value)
        except ValueError:
            # Python limits decimal-string conversion length on modern releases.
            # An untrusted/custom request.version must not turn a response into 500.
            return None
    return None


def _extract_version(request: HttpRequest) -> int | None:
    """Prefer the actual matched route over request/path heuristics."""
    match = getattr(request, "resolver_match", None)
    if match:
        # Resolver kwargs are application-defined. A parameter named
        # "version" on an unrelated route must not activate API lifecycle
        # policy; identify the API version from the actual matched route.
        route = getattr(match, "route", None)
        if isinstance(route, str):
            matched, route_version = registry.get_resolved_route_version_for_match(
                match
            )
            if matched:
                return _coerce_version(route_version)
            version = _extract_version_from_value(route)
            if version is not None:
                return version

    # Retain support for explicitly supplied request.version when no matched
    # route metadata identifies a version.
    version = _coerce_version(getattr(request, "version", None))
    if version is not None:
        return version

    # Unresolved requests use a conservative path fallback. Multiple distinct
    # version segments are ambiguous and must not select the wrong policy.
    return _extract_version_from_path(request)


def _extract_version_from_path(request: HttpRequest) -> int | None:
    """
    Extract an unambiguous version from a static URL path.

    This fallback is used for unresolved requests. A resolved request uses
    ResolverMatch and registry route metadata instead.
    """
    path = request.path_info or request.path
    if not path:
        return None
    return _extract_version_from_value(path)


def _extract_version_from_value(value: str) -> int | None:
    """Extract one distinct version from a path or resolved route string."""
    api_base_path = _get_api_setting("API_BASE_PATH", "api/v{version}/")
    if not api_base_path or api_base_path.count("{version}") != 1:
        return None

    parts = api_base_path.split("{version}")
    prefix = re.escape(parts[0].lstrip("/"))
    suffix = re.escape(parts[1])
    pattern = f"(?:^|/){prefix}([0-9]+){suffix}"

    try:
        versions = {int(match.group(1)) for match in re.finditer(pattern, value)}
    except (IndexError, ValueError, re.error):
        return None

    return next(iter(versions)) if len(versions) == 1 else None


def _parse_sunset(value: Any) -> datetime | None:
    """Parse a configured sunset value and normalize it to UTC."""
    return _parse_lifecycle_date(value, "sunset")


def _parse_lifecycle_date(value: Any, field_name: str) -> datetime | None:
    """Parse an ISO 8601 lifecycle date and normalize it to UTC."""
    if not isinstance(value, str):
        logger.warning("Invalid %s date %r; ignoring.", field_name, value)
        return None

    try:
        normalized_value = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized_value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        # A valid ISO offset can still move year 1/9999 outside datetime's
        # representable UTC range during normalization.
        logger.warning("Invalid %s date %r; ignoring.", field_name, value)
        return None


def _is_past(date: datetime) -> bool:
    return date < datetime.now(timezone.utc)


def _to_http_date(date: datetime) -> str:
    """Format an HTTP-date with locale-independent English day/month names."""
    return format_datetime(date.astimezone(timezone.utc), usegmt=True)


def _to_structured_field_date(date: datetime) -> str:
    """Serialize an RFC 9745 Date as an RFC 9651 Structured Field Date."""
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = date - epoch
    # timedelta's normalized days/seconds representation floors fractional
    # seconds correctly for pre-epoch dates; int(timestamp()) truncates toward
    # zero and can turn 1969-12-31T23:59:59.5Z into @0.
    seconds = delta.days * 86400 + delta.seconds
    return f"@{seconds}"
