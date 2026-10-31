from typing import Optional

from django.http import HttpRequest


def extract_version(request: HttpRequest, channels: list[str]) -> Optional[int]:
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


def _from_path(request: HttpRequest) -> Optional[int]:
    match = getattr(request, "resolver_match", None)
    if match and "version" in match.kwargs:
        try:
            return int(match.kwargs["version"])
        except (TypeError, ValueError):
            return None
    if hasattr(request, "version") and request.version is not None:
        try:
            return int(request.version)
        except (TypeError, ValueError):
            return None
    return None


def _from_header(request: HttpRequest) -> Optional[int]:
    raw = request.headers.get("Accept-Version")
    if not raw:
        return None
    raw = raw.strip().lower().lstrip("v")
    try:
        return int(raw)
    except ValueError:
        return None


def _from_query(request: HttpRequest) -> Optional[int]:
    raw = request.GET.get("version")
    if not raw:
        return None
    raw = raw.strip().lower().lstrip("v")
    try:
        return int(raw)
    except ValueError:
        return None
