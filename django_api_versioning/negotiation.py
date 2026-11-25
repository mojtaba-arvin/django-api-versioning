"""Request-version negotiation before Django resolves versioned URL patterns.

Install this middleware before middleware that depends on request.path_info.
For non-path schemes it rewrites only the configured unversioned API prefix to
the package's concrete versioned prefix; Django then resolves the normal URL
pattern and DRF's VersionedRouterVersioning sees the same concrete namespace.
"""

from __future__ import annotations

from typing import Any, Callable

from django.conf import settings as django_settings
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.utils.cache import patch_vary_headers

from .negotiators import (
    HeaderNegotiator,
    HostnameNegotiator,
    PathNegotiator,
    QueryNegotiator,
    _header_version,
    _host_version,
    _normalize_hostname,
    _parse_accept_media_range,
    _parse_accept_parameter_value,
    _parse_version,
    _path_version,
    _split_quoted_header,
    _UnsupportedVersion,
)
from .settings import api_settings


def _setting(name: str, default: Any = None) -> Any:
    """Preserve the middleware module's historical settings patch point."""
    if hasattr(django_settings, name):
        return getattr(django_settings, name)
    return getattr(api_settings, name, default)


__all__ = [
    "VersionNegotiationMiddleware",
    "_UnsupportedVersion",
    "_header_version",
    "_host_version",
    "_normalize_hostname",
    "_parse_accept_media_range",
    "_parse_accept_parameter_value",
    "_parse_version",
    "_path_version",
    "_split_quoted_header",
]


class VersionNegotiationMiddleware:
    """Select the effective API version before URL resolution.

    API_VERSIONING_SCHEME is one of path, header, query, or hostname. Exactly
    one transport is active per deployment. Header mode accepts Accept-Version
    (configurable) and DRF's Accept media-type version parameter. Query mode
    uses a single version parameter by default. Hostname mode requires an
    explicit hostname-to-version map.

    Non-path modes expect an unversioned path under API_UNVERSIONED_BASE_PATH
    and rewrite it internally to API_BASE_PATH for the selected version. The
    browser/client-visible URL is unchanged.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        scheme = _setting("API_VERSIONING_SCHEME", "path")
        request.api_versioning_scheme = scheme
        vary_header = scheme == "header"
        if scheme == "path":
            version = PathNegotiator(
                _setting("API_BASE_PATH", "api/v{version}/"),
                _setting(
                    "API_MAX_VERSION", getattr(api_settings, "API_MAX_VERSION", 1)
                ),
            ).negotiate(request.path_info)
            if version is not None and version >= 0:
                request.requested_api_version = version
                request.api_version = version
                request.version = str(version)
            response = self.get_response(request)
        else:
            response = self._dispatch_negotiated(request, scheme)

        if vary_header:
            patch_vary_headers(
                response,
                [_setting("API_VERSIONING_HEADER", "Accept-Version"), "Accept"],
            )
        return response

    def _dispatch_negotiated(self, request: HttpRequest, scheme: str) -> HttpResponse:
        unversioned_base = (
            "/" + _setting("API_UNVERSIONED_BASE_PATH", "api/").strip("/") + "/"
        )
        path_info = request.path_info or "/"  # pragma: no mutate

        # This middleware is global; unrelated application URLs pass through.
        versioned_path = PathNegotiator(
            _setting("API_BASE_PATH", "api/v{version}/"),
            _setting("API_MAX_VERSION", getattr(api_settings, "API_MAX_VERSION", 1)),
        ).negotiate(path_info)
        if versioned_path is not None:
            return HttpResponseBadRequest(
                "This deployment does not accept URL-path API versions."
            )
        if not path_info.startswith(unversioned_base):
            return self.get_response(request)

        try:
            version = self._requested_version(request, scheme)
        except _UnsupportedVersion:
            return HttpResponse(
                "The requested API version is not available for this host.",
                status=406,
            )
        except (ValueError, KeyError):
            return HttpResponseBadRequest("Invalid API version value.")

        if version is None:
            version = _setting("API_DEFAULT_VERSION")
        if version is None:
            return HttpResponseBadRequest(
                "An API version is required for this endpoint."
            )

        minimum = _setting("API_MIN_VERSION", 1)
        maximum = _setting("API_MAX_VERSION", 1)
        if isinstance(version, bool) or not isinstance(version, int):
            return HttpResponseBadRequest("Invalid API version value.")
        if not minimum <= version <= maximum:
            return HttpResponse(
                "The requested API version is not supported.", status=406
            )

        versioned_base = (
            "/"
            + _setting("API_BASE_PATH", "api/v{version}/")
            .format(version=version)
            .strip("/")
            + "/"
        )
        remainder = path_info[len(unversioned_base) :]
        rewritten_path = versioned_base + remainder

        request.original_path_info = path_info
        request.requested_api_version = version
        request.api_version = version
        request.version = str(version)
        # Django stores PATH_INFO on request.path_info when constructing the
        # HttpRequest. Update both representations so downstream middleware,
        # URL resolution, and diagnostics observe the intended internal route.
        request.META["PATH_INFO"] = rewritten_path
        request.path_info = rewritten_path
        original_path = request.path
        if path_info and original_path.endswith(path_info):  # pragma: no mutate
            request.path = original_path[: -len(path_info)] + rewritten_path
        else:
            request.path = rewritten_path
        request._django_api_version_negotiated = True
        return self.get_response(request)

    @staticmethod
    def _requested_version(request: HttpRequest, scheme: str) -> int | None:
        if scheme == "header":
            return HeaderNegotiator(
                _setting("API_VERSIONING_HEADER", "Accept-Version")
            ).negotiate(request)
        if scheme == "query":
            return QueryNegotiator(
                _setting("API_VERSIONING_QUERY_PARAMETER", "version")
            ).negotiate(request)
        if scheme == "hostname":
            return HostnameNegotiator(_setting("API_VERSIONING_HOSTS", {})).negotiate(
                request
            )
        raise ValueError(f"Unsupported API versioning scheme: {scheme!r}.")
