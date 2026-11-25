"""Transport-specific API-version negotiators.

Parsing, host normalization, and transport candidate selection live here;
VersionNegotiationMiddleware remains the sole request orchestration boundary.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings as django_settings
from django.http import HttpRequest

from .settings import api_settings


class _UnsupportedVersion(Exception):
    """The transport is valid, but the requested version is not available."""


def _setting(name: str, default: Any = None) -> Any:
    if hasattr(django_settings, name):
        return getattr(django_settings, name)
    return getattr(api_settings, name, default)


def _parse_version(value: object) -> int:
    raw = str(value).strip()
    if not raw or not raw.isascii() or not raw.isdecimal():
        raise ValueError("A version must be an ASCII decimal integer.")
    return int(raw)


def _path_match(path_info: str, template: str):
    """Return the numeric path-version match without converting its digits."""
    if not isinstance(template, str) or template.count("{version}") != 1:
        return None
    prefix, suffix = template.split("{version}")
    pattern = "^" + re.escape(prefix.lstrip("/")) + r"([0-9]+)" + re.escape(suffix)
    return re.match(pattern, path_info.lstrip("/"))


def _path_version(
    path_info: str, template: str, maximum_version: int | None = None
) -> int | None:
    match = _path_match(path_info, template)
    if match is None:
        return None

    # A long numeric segment is still a versioned path, even when it cannot
    # be a supported version. Avoid unbounded int conversion (which raises on
    # Python 3.11+ after the configured digit limit) while preserving that
    # distinction for non-path negotiation schemes.
    digits = match.group(1).lstrip("0") or "0"  # pragma: no mutate
    maximum = maximum_version
    if maximum is None:
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
    start = 0  # pragma: no mutate
    quoted = False  # pragma: no mutate
    escaped = False  # pragma: no mutate

    for index, character in enumerate(value):
        if quoted and escaped:
            escaped = False  # pragma: no mutate
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
        if len(value) < 2 or not value.startswith('"') or not value.endswith('"'):
            raise ValueError("Accept contains an invalid quoted parameter.")

        # RFC quoted-string permits an embedded DQUOTE only as a quoted-pair
        # (backslash escape). Merely checking the outer quotes accepts malformed
        # values such as `profile="one""two"`, which can make an invalid Accept
        # field influence version selection.
        escaped = False  # pragma: no mutate
        for character in value[1:-1]:
            codepoint = ord(character)
            if escaped:
                if (codepoint < 32 and character != "\t") or codepoint == 127:
                    raise ValueError("Accept contains an invalid quoted parameter.")
                escaped = False  # pragma: no mutate
            elif character == "\\":
                escaped = True
            elif character == '"':
                raise ValueError("Accept contains an invalid quoted parameter.")
            elif (codepoint < 32 and character != "\t") or codepoint == 127:
                raise ValueError("Accept contains an invalid quoted parameter.")

        if escaped:
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
    saw_quality = False  # pragma: no mutate
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
    saw_version = False  # pragma: no mutate
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


class PathNegotiator:
    """Resolve a path transport candidate using an explicit route template."""

    def __init__(
        self, template: str, maximum_version: int | None = None
    ) -> None:
        self.template = template
        self.maximum_version = maximum_version

    def negotiate(self, path_info: str) -> int | None:
        return _path_version(path_info, self.template, self.maximum_version)

    def matches(self, path_info: str) -> bool:
        """Detect a versioned path without parsing or bounding its number."""
        return _path_match(path_info, self.template) is not None


class HeaderNegotiator:
    """Resolve Accept-Version and Accept media-type version candidates."""

    def __init__(self, header_name: str) -> None:
        self.header_name = header_name

    def negotiate(self, request: HttpRequest) -> int | None:
        return _header_version(request, self.header_name)


class QueryNegotiator:
    """Resolve one configured query parameter, rejecting duplicates."""

    def __init__(self, parameter: str) -> None:
        self.parameter = parameter

    def negotiate(self, request: HttpRequest) -> int | None:
        values = request.GET.getlist(self.parameter)
        if len(values) > 1:
            raise ValueError("The API version query parameter must appear once.")
        return _parse_version(values[0]) if values else None


class HostnameNegotiator:
    """Resolve a request host through an exact, normalized hostname map."""

    def __init__(self, host_map: dict[str, int]) -> None:
        self.host_map = host_map

    def negotiate(self, request: HttpRequest) -> int:
        version = _host_version(request, self.host_map)
        if version is None:
            raise _UnsupportedVersion(
                "The request hostname has no API version mapping."
            )
        return version
