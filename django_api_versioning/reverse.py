import re
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from django.conf import settings as django_settings
from django.urls import NoReverseMatch, get_script_prefix
from django.urls.resolvers import RegexPattern, URLResolver

from .exceptions import AmbiguousVersionError, VersionTypeError
from .registry import registry
from .settings import api_settings

# Matches Django path parameters, with or without an explicit converter.
_CONVERTER_RE = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")
_PATH_SAFE_CHARS = "/~:@!$&()*+,;=" + chr(39)


def format_negotiated_url(
    url: str,
    version: int | str | None,
    *,
    scheme: str | None = None,
) -> str:
    """Adapt an internally reversed versioned URL to the configured transport.

    Header and hostname modes cannot encode a version in the URL. Query mode
    appends the configured query parameter. Path mode preserves the existing
    versioned URL contract.
    """
    if scheme is None:
        scheme = getattr(
            django_settings, "API_VERSIONING_SCHEME", api_settings.API_VERSIONING_SCHEME
        )
    if scheme == "path":
        return url

    api_base_path = getattr(
        django_settings, "API_BASE_PATH", api_settings.API_BASE_PATH
    )
    unversioned_base_path = getattr(
        django_settings, "API_UNVERSIONED_BASE_PATH", "api/"
    )
    parts = urlsplit(url)
    path = parts.path

    # DRF's NamespaceVersioning adapter can reverse the URL using the
    # resolver namespace even when request.version is not forwarded to this
    # method. In that case, recover the exact version from the concrete
    # internal URL rather than guessing a default or latest version.
    if version is None and api_base_path.count("{version}") == 1:
        template_prefix, template_suffix = api_base_path.split("{version}")
        route_pattern = (
            r"(?:^|/)"
            + re.escape(template_prefix.lstrip("/"))
            + r"([0-9]+)"
            + re.escape(template_suffix)
        )
        match = re.search(route_pattern, path)
        if match is not None:
            version = int(match.group(1))
    if version is None:
        return url

    versioned_base = "/" + api_base_path.format(version=version).strip("/") + "/"
    unversioned_base = "/" + unversioned_base_path.strip("/") + "/"
    script_prefix = get_script_prefix()
    if script_prefix != "/" and path.startswith(script_prefix):
        relative_path = "/" + path[len(script_prefix) :].lstrip("/")
        prefix = script_prefix.rstrip("/")
    else:
        relative_path = path
        prefix = ""

    if not relative_path.startswith(versioned_base):
        return url

    negotiated_path = unversioned_base + relative_path[len(versioned_base) :]
    query = parts.query
    if scheme == "query":
        parameter = getattr(
            django_settings, "API_VERSIONING_QUERY_PARAMETER", "version"
        )
        pairs = [
            (key, value)
            for key, value in parse_qsl(query, keep_blank_values=True)
            if key != parameter
        ]
        pairs.append((parameter, str(version)))
        query = urlencode(pairs)
    elif scheme not in {"header", "hostname"}:
        return url

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            prefix + negotiated_path,
            query,
            parts.fragment,
        )
    )


def api_reverse(
    view_name: str,
    version: int | None = None,
    **kwargs: Any,
) -> str:
    """
    Reverse a versioned URL explicitly.

    - ``version=N``: return the URL registered for exactly version N.
    - ``version=None``: if exactly one version is registered for ``view_name``,
      return it; otherwise raise ``AmbiguousVersionError``.
    """
    if version is not None and (
        isinstance(version, bool) or not isinstance(version, int)
    ):
        raise VersionTypeError("Version must be an integer.")

    matches = []
    for pattern in registry.urlpatterns:
        if pattern.name != view_name:
            continue
        route_version = getattr(pattern, "_django_api_versioning_route_version", None)
        if version is None or route_version == version:
            matches.append((route_version, pattern))

    if not matches:
        raise NoReverseMatch(
            f"No reverse match for {view_name!r} (version={version!r})."
        )

    if version is None and len(matches) > 1:
        versions = sorted(v for v, _ in matches if v is not None)
        raise AmbiguousVersionError(
            f"View name {view_name!r} is registered more than once for "
            f"versions {versions}. Pass an explicit version."
        )
    if version is not None and len(matches) > 1:
        raise NoReverseMatch(
            f"View name {view_name!r} is registered more than once "
            f"for version {version!r}."
        )

    selected_version, target_pattern = matches[0]
    route_pattern = target_pattern.pattern

    if not hasattr(route_pattern, "_route"):
        # DRF's default SimpleRouter generates RegexPattern instances. Delegate
        # their reversal to Django's URLResolver rather than parsing regex
        # groups or interpolating user-provided values ourselves.
        resolver = URLResolver(RegexPattern(r"^"), [target_pattern])
        url = get_script_prefix() + resolver.reverse(view_name, **kwargs)
        return format_negotiated_url(url, selected_version)

    route = route_pattern._route
    parameter_names = {match.group(1) for match in _CONVERTER_RE.finditer(route)}
    default_args = getattr(target_pattern, "default_args", None) or {}
    unexpected_parameters = sorted(set(kwargs) - parameter_names - set(default_args))
    if unexpected_parameters:
        raise NoReverseMatch(
            f"Unexpected parameter(s) {unexpected_parameters!r} for {view_name!r}."
        )

    # Match Django's reverse() semantics: URLPattern defaults can satisfy an
    # omitted path converter. Defaults for non-path kwargs remain fixed, while
    # a supplied path parameter may override its fallback default.
    conflicting_defaults = sorted(
        name
        for name, default_value in default_args.items()
        if (
            name not in parameter_names
            and name in kwargs
            and kwargs[name] != default_value
        )
    )
    if conflicting_defaults:
        raise NoReverseMatch(
            f"Parameter(s) {conflicting_defaults!r} conflict with URL defaults "
            f"for {view_name!r}."
        )

    def _substitute(match: re.Match) -> str:
        name = match.group(1)
        if name in kwargs:
            value = kwargs[name]
        elif name in default_args:
            value = default_args[name]
        else:
            raise NoReverseMatch(
                f"Missing required parameter {name!r} for {view_name!r}."
            )

        converter = route_pattern.converters.get(name)
        try:
            value = converter.to_url(value) if converter else value
        except (TypeError, ValueError) as exc:
            raise NoReverseMatch(
                f"Invalid value for parameter {name!r} in {view_name!r}: {exc}"
            ) from exc
        return str(value)

    route = _CONVERTER_RE.sub(_substitute, route)

    # A converter's to_url() method does not necessarily validate its output.
    # Match the completed route against Django's compiled RoutePattern so
    # api_reverse() cannot return a URL that the same route would not resolve.
    if not route_pattern.regex.fullmatch(route):
        raise NoReverseMatch(
            f"Invalid parameter value for {view_name!r}; "
            f"the generated path does not match {route_pattern!r}."
        )

    url = get_script_prefix() + quote(
        route.lstrip("/"),
        safe=_PATH_SAFE_CHARS,
    )
    return format_negotiated_url(url, selected_version)
