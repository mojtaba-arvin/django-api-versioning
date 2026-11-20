"""Request-version negotiation before Django resolves versioned URL patterns.

Install this middleware before middleware that depends on request.path_info.
For non-path schemes it rewrites only the configured unversioned API prefix to
the package's concrete versioned prefix; Django then resolves the normal URL
pattern and DRF's VersionedRouterVersioning sees the same concrete namespace.
"""

from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import urlsplit

from django.conf import settings as django_settings
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.utils.cache import patch_vary_headers

from .settings import api_settings


class _UnsupportedVersion(Exception):
    """The transport is valid, but the requested version is not available."""


def _setting(name: str, default: Any = None) -> Any:
    if hasattr(django_settings, name):
        return getattr(django_settings, name)
    return getattr(api_settings, name, default)


def _parse_version(value: object) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError("A version must be an ASCII decimal integer.")
    raw = str(value).strip()
    if not raw or not raw.isascii() or not raw.isdecimal():
        raise ValueError("A version must be an ASCII decimal integer.")
    return int(raw)


def _path_version(path_info: str, template: str) -> int | None:
    if not isinstance(template, str) or template.count("{version}") != 1:
        return None
    prefix, suffix = template.split("{version}")
    pattern = "^" + re.escape(prefix.lstrip("/")) + r"([0-9]+)" + re.escape(suffix)
    match = re.match(pattern, path_info.lstrip("/"))
    return int(match.group(1)) if match else None


def _host_version(request: HttpRequest, host_map: dict[str, int]) -> int | None:
    # request.get_host() applies Django's ALLOWED_HOSTS validation. Do not read
    # HTTP_HOST or X-Forwarded-Host directly, bypassing that validation.
    host = urlsplit("//" + request.get_host()).hostname
    if not host:
        return None
    normalized = host.rstrip(".").encode("idna").decode("ascii").lower()
    for configured_host, version in host_map.items():
        candidate = configured_host.rstrip(".").encode("idna").decode("ascii").lower()
        if normalized == candidate:
            return version
    return None


def _header_version(request: HttpRequest, header_name: str) -> int | None:
    dedicated = request.headers.get(header_name)
    dedicated_version = _parse_version(dedicated) if dedicated is not None else None

    # Interoperate with DRF's AcceptHeaderVersioning wire format:
    # Accept: application/json; version=2. Reject conflicting values instead
    # of guessing which media range should control route dispatch.
    values = re.findall(
        r'(?:^|[;,])\s*version\s*=\s*(?:"([^"]+)"|([^;,\s]+))',
        request.headers.get("Accept", ""),
        flags=re.IGNORECASE,
    )
    versions = {quoted or bare for quoted, bare in values}
    if len(versions) > 1:
        raise ValueError("Accept contains conflicting API version parameters.")
    accept_version = _parse_version(next(iter(versions))) if versions else None

    if (
        dedicated_version is not None
        and accept_version is not None
        and dedicated_version != accept_version
    ):
        raise ValueError(
            "Accept-Version and Accept media-type version parameters conflict."
        )
    return dedicated_version if dedicated_version is not None else accept_version


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
            version = _path_version(
                request.path_info, _setting("API_BASE_PATH", "api/v{version}/")
            )
            if version is not None:
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

    def _dispatch_negotiated(
        self, request: HttpRequest, scheme: str
    ) -> HttpResponse:
        unversioned_base = "/" + _setting(
            "API_UNVERSIONED_BASE_PATH", "api/"
        ).strip("/") + "/"
        path_info = request.path_info or "/"

        # This middleware is global; unrelated application URLs pass through.
        versioned_path = _path_version(
            path_info, _setting("API_BASE_PATH", "api/v{version}/")
        )
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

        versioned_base = "/" + _setting(
            "API_BASE_PATH", "api/v{version}/"
        ).format(version=version).strip("/") + "/"
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
        request._django_api_version_negotiated = True
        return self.get_response(request)

    @staticmethod
    def _requested_version(request: HttpRequest, scheme: str) -> int | None:
        if scheme == "header":
            return _header_version(
                request, _setting("API_VERSIONING_HEADER", "Accept-Version")
            )
        if scheme == "query":
            parameter = _setting("API_VERSIONING_QUERY_PARAMETER", "version")
            values = request.GET.getlist(parameter)
            if len(values) > 1:
                raise ValueError("The API version query parameter must appear once.")
            return _parse_version(values[0]) if values else None
        if scheme == "hostname":
            version = _host_version(
                request, _setting("API_VERSIONING_HOSTS", {})
            )
            if version is None:
                raise _UnsupportedVersion(
                    "The request hostname has no API version mapping."
                )
            return version
        raise ValueError(f"Unsupported API versioning scheme: {scheme!r}.")
