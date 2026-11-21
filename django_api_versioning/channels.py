from django.http import HttpRequest

from .settings import api_settings


def extract_version(request: HttpRequest, channels: list[str]) -> int | None:
    """
    Extract API version from the configured channels, in priority order.

    Supported channels:
    - ``"path"``: ``request.resolver_match.kwargs["version"]`` or ``request.version``
    - ``"header"``: ``Accept-Version: v3`` or ``Accept-Version: 3``
    - ``"query"``: ``?version=3``
    """
    for channel in channels:
        if channel == "path":
            version = _from_path(request)
        elif channel == "header":
            version = _from_header(request)
        elif channel == "query":
            version = _from_query(request)
        else:
            version = None
        if version is not None:
            return version
    return None


def _from_path(request: HttpRequest) -> int | None:
    match = getattr(request, "resolver_match", None)
    kwargs = getattr(match, "kwargs", {}) if match else {}
    if "version" in kwargs:
        version = _parse_version(kwargs["version"])
        if version is not None:
            return version
    return _parse_version(getattr(request, "version", None))


def _from_header(request: HttpRequest) -> int | None:
    return _parse_version(request.headers.get("Accept-Version"))


def _from_query(request: HttpRequest) -> int | None:
    return _parse_version(request.GET.get("version"))


def _parse_version(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None

    raw = str(value).strip().lower()
    if raw.startswith("v"):
        raw = raw[1:]
    if not raw:
        return None

    # API versions are non-negative ASCII decimal identifiers. Python's
    # int() also accepts signs and underscores, which are not part of the
    # documented channel grammar (for example, "-1", "+2", and "1_0").
    if not raw.isascii() or not raw.isdecimal():
        return None

    # Reject unsupported versions before converting attacker-controlled,
    # arbitrarily long decimal strings to Python integers. Comparing the
    # normalized decimal representation avoids Python's int digit limit and
    # behaves consistently across supported Python versions.
    normalized = raw.lstrip("0") or "0"
    maximum = str(api_settings.API_MAX_VERSION)
    if len(normalized) > len(maximum) or (
        len(normalized) == len(maximum) and normalized > maximum
    ):
        return None
    try:
        return int(normalized)
    except ValueError:
        # Keep malformed/oversized values on the documented non-match path,
        # including when the interpreter's integer-string limit is configured
        # more restrictively than the default.
        return None
