import re
from typing import Any

from django.urls import NoReverseMatch, get_script_prefix
from urllib.parse import quote
from django.urls.resolvers import RegexPattern, URLResolver

from .exceptions import AmbiguousVersionError, VersionTypeError
from .registry import registry

# Matches Django path parameters, with or without an explicit converter.
_CONVERTER_RE = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")


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

    _, target_pattern = matches[0]
    route_pattern = target_pattern.pattern

    if not hasattr(route_pattern, "_route"):
        # DRF's default SimpleRouter generates RegexPattern instances. Delegate
        # their reversal to Django's URLResolver rather than parsing regex
        # groups or interpolating user-provided values ourselves.
        resolver = URLResolver(RegexPattern(r"^"), [target_pattern])
        return get_script_prefix() + resolver.reverse(view_name, **kwargs)

    route = route_pattern._route
    parameter_names = {match.group(1) for match in _CONVERTER_RE.finditer(route)}
    unexpected_parameters = sorted(set(kwargs) - parameter_names)
    if unexpected_parameters:
        raise NoReverseMatch(
            f"Unexpected parameter(s) {unexpected_parameters!r} for {view_name!r}."
        )

    def _substitute(match: re.Match) -> str:
        name = match.group(1)
        if name not in kwargs:
            raise NoReverseMatch(
                f"Missing required parameter {name!r} for {view_name!r}."
            )

        converter = route_pattern.converters.get(name)
        try:
            value = converter.to_url(kwargs[name]) if converter else kwargs[name]
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

    return quote(get_script_prefix() + route.lstrip("/"), safe="!return iri_to_uri(get_script_prefix() + route.lstrip("/"))'()*+,;=:@/~")
