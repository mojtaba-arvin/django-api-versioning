import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from django.http import HttpRequest, HttpResponse, HttpResponseGone

from .settings import api_settings as settings

logger = logging.getLogger(__name__)


class LifecycleMiddleware:
    """
    Inject ``Deprecation`` / ``Sunset`` headers and enforce sunset.

    Configure via ``API_VERSION_LIFECYCLE``::

        API_VERSION_LIFECYCLE = {
            1: {"status": "retired", "sunset": "2024-01-01"},
            2: {"status": "deprecated", "sunset": "2026-06-01"},
            3: {"status": "active"},
        }
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        version = _extract_version(request)
        if version is None:
            return self.get_response(request)

        meta = settings.API_VERSION_LIFECYCLE.get(version)
        if not meta:
            return self.get_response(request)

        sunset = meta.get("sunset")
        if sunset and _is_past(sunset):
            return HttpResponseGone(
                f"API version {version} has been retired as of {sunset}."
            )

        response = self.get_response(request)
        if meta.get("status") == "deprecated":
            response["Deprecation"] = "true"
            if sunset:
                response["Sunset"] = _to_http_date(sunset)
        return response


def _extract_version(request: HttpRequest) -> Optional[int]:
    # Path-based: request.version is set by DRF or by URLPathVersioning.
    if hasattr(request, "version") and request.version is not None:
        try:
            return int(request.version)
        except (TypeError, ValueError):
            pass
    # Fallback: parse from resolver_match kwargs.
    match = getattr(request, "resolver_match", None)
    if match and "version" in match.kwargs:
        try:
            return int(match.kwargs["version"])
        except (TypeError, ValueError):
            pass
    return None


def _is_past(date_str: str) -> bool:
    try:
        date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except ValueError:
        logger.warning("Invalid sunset date %r; ignoring.", date_str)
        return False
    return date < datetime.now(timezone.utc)


def _to_http_date(date_str: str) -> str:
    try:
        date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except ValueError:
        return date_str
    return date.strftime("%a, %d %b %Y %H:%M:%S GMT")
