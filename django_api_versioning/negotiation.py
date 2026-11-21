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
    if not match:
        return None

    # A long numeric segment is still a versioned path, even when it cannot
    # be a supported version. Avoid unbounded int conversion (which raises on
    # Python 3.11+ after the configured digit limit) while preserving that
    # distinction for non-path negotiation schemes.
    digits = match.group(1).lstrip("0") or "0"
    maximum = _setting("API_MAX_VERSION", api_settings.API_MAX_VERSION)
    if len(digits) > len(str(maximum)):
        return -1
    return int(digits)


def _normalize_hostname(hostname: str) -> str | None:
    """Normalize one DNS hostname without accepting multiple root dots."""
    if not hostname or hostname.endswith(".."):
        return None
    hostname = hostname[:-1] if hostname.endswith(".") else hostname
    try:
        return hostname.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None


def _host_version(request: HttpRequest, host_map: dict[str, int]) -> int | None:
    # request.get_host() applies Django's ALLOWED_HOSTS validation. Do not read
    # HTTP_HOST or X-Forwarded-Host directly, bypassing that validation.
    host = _normalize_hostname(urlsplit("//" + request.get_host()).hostname or "")
    if host is None:
        return None
    for configured_host, version in host_map.items():
        candidate = _normalize_hostname(configured_host)
        if host == candidate:
            return version
    return None


def _split_quoted_header(value: str, delimiter: str) -> list[str]:
    """Split an HTTP header outside quoted strings.

    Accept media parameters may contain commas and semicolons inside quoted
    values. Treating those characters as delimiters without tracking quoted
    strings can mistake arbitrary profile text for an API version parameter.
    """
    parts: list[str] = []
    start = 0
    quoted = False
    escaped = False

    for index, character in enumerate(value):
        if quoted and escaped:
            escaped = False
            continue
        if quoted and character == "\\":
            escaped = True
            continue
        if character == '"':
            quoted = not quoted
            continue
        if character == delimiter and not quoted:
            parts.append(value[start:index])
            start = index + 1

    if quoted or escaped:
        raise ValueError("Accept contains an unterminated quoted parameter.")

    parts.append(value[start:])
    return parts


_HTTP_TOKEN = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
_ACCEPT_MEDIA_TYPE_RE = re.compile(rf"^({_HTTP_TOKEN}|\*)/({_HTTP_TOKEN}|\*)$")
_ACCEPT_QVALUE_RE = re.compile(r"^(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)$")


def _parse_accept_parameter_value(raw_value: str) -> tuple[str, bool]:
    """Validate and unwrap one Accept parameter value."""
    value = raw_value.strip()
    if not value:
        raise ValueError("Accept contains an empty media parameter value.")

    quoted = value.startswith('"') or value.endswith('"')
    if quoted:
        if (
            len(value) < 2
            or not value.startswith('"')
            or not value.endswith('"')
            or any(
                (ord(character) < 32 and character != "\t") or ord(character) == 127
                for character in value[1:-1]
            )
        ):
            raise ValueError("Accept contains an invalid quoted parameter.")
        return value[1:-1], True

    if not re.fullmatch(_HTTP_TOKEN, value):
        raise ValueError("Accept contains an invalid media parameter value.")
    return value, False


def _parse_accept_media_range(media_range: str) -> tuple[str | None, float]:
    """Return a version parameter and quality from one syntactically valid range."""
    parameters = _split_quoted_header(media_range, ";")
    match = _ACCEPT_MEDIA_TYPE_RE.fullmatch(parameters[0].strip())
    if match is None or (match.group(1) == "*" and match.group(2) != "*"):
        raise ValueError("Accept contains an invalid media range.")

    quality = 1.0
    saw_quality = False
    version_value = None

    for parameter in parameters[1:]:
        name, separator, raw_value = parameter.partition("=")
        name = name.strip()
        if not re.fullmatch(_HTTP_TOKEN, name) or not separator:
            raise ValueError("Accept contains an invalid media parameter.")

        value, quoted = _parse_accept_parameter_value(raw_value)
        folded_name = name.casefold()
        if folded_name == "q":
            if saw_quality or quoted or not _ACCEPT_QVALUE_RE.fullmatch(value):
                raise ValueError("Accept contains an invalid quality value.")
            saw_quality = True
            quality = float(value)
        elif folded_name == "version":
            if version_value is not None:
                raise ValueError("Accept contains duplicate version parameters.")
            version_value = value

    return version_value, quality


def _header_version(request: HttpRequest, header_name: str) -> int | None:
    dedicated = request.headers.get(header_name)
    dedicated_version = _parse_version(dedicated) if dedicated is not None else None

    # q=0 means a versioned representation is explicitly unacceptable. If
    # multiple versioned ranges are acceptable, prefer the highest q; equal
    # quality conflicts are ambiguous and fail closed.
    candidates: list[tuple[float, int]] = []
    saw_version = False
    accept = request.headers.get("Accept", "")
    if not accept.strip():
        return dedicated_version

    for media_range in _split_quoted_header(accept, ","):
        version_value, quality = _parse_accept_media_range(media_range)
        if version_value is None:
            continue
        saw_version = True
        if quality > 0:
            candidates.append((quality, _parse_version(version_value)))

    if saw_version and not candidates:
        raise _UnsupportedVersion("All requested API versions have q=0.")

    accept_version = None
    if candidates:
        highest_quality = max(quality for quality, _ in candidates)
        preferred_versions = {
            version for quality, version in candidates if quality == highest_quality
        }
        if len(preferred_versions) != 1:
            raise ValueError(
                "Accept contains equally preferred conflicting API versions."
            )
        accept_version = next(iter(preferred_versions))

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
            version = _host_version(request, _setting("API_VERSIONING_HOSTS", {}))
            if version is None:
                raise _UnsupportedVersion(
                    "The request hostname has no API version mapping."
                )
            return version
        raise ValueError(f"Unsupported API versioning scheme: {scheme!r}.")
