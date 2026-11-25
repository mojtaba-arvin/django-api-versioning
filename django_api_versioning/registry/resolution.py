"""Framework-neutral route identity and operation resolution.

Django remains responsible for URL matching. This module only interprets its
resolver result against the registry's authoritative registered patterns.
Optional framework capabilities (for example DRF method-to-action mapping)
are supplied through a callback protocol and are never imported here.
"""

from dataclasses import dataclass

from django.urls import URLPattern
from django.urls.resolvers import RegexPattern

OPERATION_ACTION_RESOLVER_ATTR = "_django_api_versioning_operation_action_resolver"


@dataclass(frozen=True, slots=True)
class ResolvedOperation:
    """Stable identity for one operation resolved by Django's URL resolver."""

    logical_endpoint: str
    route_version: int
    source_version: int | None
    method: str
    action: str | None
    route_name: str | None
    namespace: str
    route: str
    registered_route: str
    router_owner: object | None = None


ResolvedRouteCandidate = tuple[int, URLPattern, str, int, int | None]


def canonical_route_key(route: str) -> str:
    """Normalize anchored regexes containing only literal path text."""
    if not (route.startswith("^") and route.endswith("$")):
        return route

    literal = route[1:-1]
    if "<" in literal or ">" in literal:
        return route

    normalized = []
    escaped = False  # pragma: no mutate
    for character in literal:
        if escaped:
            # Escaped punctuation is literal; alphanumeric escapes such
            # as \\d and \\w are regex classes, not static path text.
            if character.isalnum():
                return route
            normalized.append(character)
            escaped = False  # pragma: no mutate
        elif character == "\\":
            escaped = True
        elif character in ".^$*+?{}[]|()":
            return route
        else:
            normalized.append(character)

    if escaped:
        return route
    return "".join(normalized)


def find_route_index(
    registry,
    route: str,
    *,
    regex_route: bool = False,
) -> int | None:
    """Return the index of a registered route, or None if absent."""
    for index, pattern in enumerate(registry.urlpatterns):
        existing_pattern_text = str(pattern.pattern)
        existing_is_regex = isinstance(pattern.pattern, RegexPattern)
        if existing_pattern_text == route and existing_is_regex == regex_route:
            return index

        route_key = canonical_route_key(route) if regex_route else route
        existing_key = (
            canonical_route_key(existing_pattern_text)
            if existing_is_regex
            else existing_pattern_text
        )
        if existing_key == route_key:
            return index

    return None


def resolved_route_match_length(route: str, registered_route: str) -> int:
    """Return the longest complete registered-route suffix match."""
    route_variants = tuple(
        dict.fromkeys((route, route.removeprefix("^").removesuffix("$")))
    )
    pattern_variants = tuple(
        dict.fromkeys(
            (
                registered_route,
                registered_route.removeprefix("^").removesuffix("$"),
            )
        )
    )

    matched_length = 0
    for route_candidate in route_variants:
        for pattern_candidate in pattern_variants:
            start = len(route_candidate) - len(pattern_candidate)
            if start < 0 or route_candidate[start:] != pattern_candidate:
                continue
            if start and route_candidate[start - 1] != "/":
                continue  # pragma: no mutate
            matched_length = max(matched_length, len(pattern_candidate))
    return matched_length


def get_resolved_route_version_for_match(
    registry, resolver_match: object
) -> tuple[bool, int | None]:
    """Resolve version metadata for the exact URLPattern Django matched.

    The boolean distinguishes an explicitly registered unversioned route
    from a route that is absent from this registry. This matters for nested
    includes: a parent URL prefix may contain an API-looking version even
    when the matched child route is unversioned.
    """
    route = getattr(resolver_match, "route", None)
    callback = getattr(resolver_match, "func", None)
    if not isinstance(route, str) or callback is None:
        return False, None

    tried = getattr(resolver_match, "tried", None)
    if isinstance(tried, (list, tuple)):
        matched_pattern_ids = {
            id(chain[-1])
            for chain in tried
            if chain and isinstance(chain[-1], URLPattern)
        }
        url_name = getattr(resolver_match, "url_name", None)
        exact_matches = [
            pattern
            for pattern in registry.urlpatterns
            if id(pattern) in matched_pattern_ids
            and pattern.callback is callback
            and (url_name is None or pattern.name == url_name)
            and resolved_route_match_length(route, str(pattern.pattern))
        ]
        if not exact_matches:
            return False, None
        versions = {
            getattr(pattern, registry._ROUTE_VERSION_ATTR, None)
            for pattern in exact_matches
        }
        if len(versions) != 1:
            return True, None
        return True, next(iter(versions))

    url_name = getattr(resolver_match, "url_name", None)
    matches = []
    for pattern in registry.urlpatterns:
        if pattern.callback is not callback:
            continue
        if url_name is not None and pattern.name != url_name:
            continue
        matched_length = resolved_route_match_length(route, str(pattern.pattern))
        if matched_length:
            matches.append(
                (
                    matched_length,
                    getattr(pattern, registry._ROUTE_VERSION_ATTR, None),
                )
            )

    if not matches:
        return False, None

    longest = max(length for length, _ in matches)
    versions = {version for length, version in matches if length == longest}
    if len(versions) != 1:
        return True, None
    return True, next(iter(versions))


def get_resolved_route_version(registry, route: str) -> int | None:
    """Resolve a version from the longest registered route suffix.

    Django's ResolverMatch.route includes every parent URLResolver prefix.
    Matching a registered route as a complete suffix therefore supports
    nested includes without confusing a parent API-like prefix for the
    child endpoint's version.
    """
    matches: list[tuple[int, int]] = []
    for pattern in registry.urlpatterns:
        matched_length = resolved_route_match_length(route, str(pattern.pattern))
        version = getattr(pattern, registry._ROUTE_VERSION_ATTR, None)
        if (
            matched_length
            and isinstance(version, int)
            and not isinstance(version, bool)
        ):
            matches.append((matched_length, version))

    if not matches:
        return None

    longest = max(length for length, _ in matches)
    versions = {version for length, version in matches if length == longest}
    return next(iter(versions)) if len(versions) == 1 else None


def resolve_operation(
    registry,
    resolver_match: object,
    method: str,
    *,
    allow_unmapped_method: bool = False,
    require_exact_pattern: bool = True,
    action_resolver=None,
) -> ResolvedOperation | None:
    """Resolve one registered logical operation from Django's ResolverMatch.

    Runtime callers require Django's resolver trace to identify the exact
    registered URLPattern. Schema generators may opt into route/name
    matching because their synthetic ResolverMatch can refer to a generated
    operation rather than the original URLPattern. Optional operation
    metadata is supplied by a capability callback attached to the matched
    callback or passed explicitly; core resolution does not interpret a
    framework-specific action map. Ambiguous or incomplete matches fail closed.
    """
    route = getattr(resolver_match, "route", None)
    if not isinstance(route, str) or not isinstance(method, str) or not method:
        return None

    normalized_method = method.upper()
    url_name = getattr(resolver_match, "url_name", None)
    namespaces = tuple(getattr(resolver_match, "namespaces", ()) or ())
    namespace = getattr(resolver_match, "namespace", "") or ""

    # Do not infer endpoint metadata from a matching route suffix alone
    # when Django can identify the exact URLPattern selected by its resolver.
    tried = getattr(resolver_match, "tried", None)
    matched_pattern_ids = None
    if require_exact_pattern and isinstance(tried, (list, tuple)):
        matched_pattern_ids = {
            id(chain[-1])
            for chain in tried
            if chain and isinstance(chain[-1], URLPattern)
        }

    # VersionedRouter places the concrete API version in a vN namespace.
    # If such a namespace is present, it must agree with the registry record.
    version_namespaces = {
        item
        for item in namespaces
        if isinstance(item, str) and item.startswith("v") and item[1:].isdecimal()
    }

    candidates: list[ResolvedRouteCandidate] = []
    for pattern in registry.urlpatterns:
        if matched_pattern_ids is not None and id(pattern) not in matched_pattern_ids:
            continue
        if url_name is not None and pattern.name != url_name:
            continue

        logical_endpoint = getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
        route_version = getattr(pattern, registry._ROUTE_VERSION_ATTR, None)
        if not isinstance(logical_endpoint, str) or not logical_endpoint:
            continue
        if isinstance(route_version, bool) or not isinstance(route_version, int):
            continue
        if version_namespaces and f"v{route_version}" not in version_namespaces:
            continue

        matched_length = resolved_route_match_length(route, str(pattern.pattern))
        if not matched_length:
            continue

        source_version = getattr(pattern, registry._SOURCE_VERSION_ATTR, None)
        candidates.append(
            (
                matched_length,
                pattern,
                logical_endpoint,
                route_version,
                source_version,
            )
        )

    if not candidates:
        return None

    longest = max(item[0] for item in candidates)
    best = [item for item in candidates if item[0] == longest]
    if len(best) != 1:
        return None

    _, pattern, logical_endpoint, route_version, source_version = best[0]
    callback = getattr(resolver_match, "func", None)
    action = None
    capability = action_resolver or getattr(
        callback, OPERATION_ACTION_RESOLVER_ATTR, None
    )
    if callable(capability):
        supported, action = capability(
            callback, normalized_method, allow_unmapped_method
        )
        if not supported:
            return None

    return ResolvedOperation(
        logical_endpoint=logical_endpoint,
        route_version=route_version,
        source_version=source_version,
        method=normalized_method,
        action=action,
        route_name=pattern.name,
        namespace=namespace,
        route=route,
        registered_route=str(pattern.pattern),
        router_owner=getattr(pattern, registry._ROUTER_OWNER_ATTR, None),
    )


def resolve_registered_operation(
    registry,
    logical_endpoint: str,
    route_version: int,
    method: str,
    *,
    action_resolver=None,
) -> ResolvedOperation | None:
    """Resolve decorator metadata from its declared identity and schema version.

    This path is used only when a schema tool's URLPathVersioning adapter
    supplies the concrete version kwarg but no Django ResolverMatch. The
    decorator attaches the logical endpoint to the registered view class;
    the registry then requires one active route for that identity/version.
    """
    if not isinstance(logical_endpoint, str) or not logical_endpoint:
        return None
    if isinstance(route_version, bool) or not isinstance(route_version, int):
        return None
    if not isinstance(method, str) or not method:
        return None

    candidates = [
        pattern
        for pattern in registry.urlpatterns
        if getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None) == logical_endpoint
        and getattr(pattern, registry._ROUTE_VERSION_ATTR, None) == route_version
    ]
    if len(candidates) != 1:
        return None

    pattern = candidates[0]
    normalized_method = method.upper()
    action = None
    capability = action_resolver or getattr(
        pattern.callback, OPERATION_ACTION_RESOLVER_ATTR, None
    )
    if callable(capability):
        supported, action = capability(pattern.callback, normalized_method, False)
        if not supported:
            return None

    pattern_text = str(pattern.pattern)
    return ResolvedOperation(
        logical_endpoint=logical_endpoint,
        route_version=route_version,
        source_version=getattr(pattern, registry._SOURCE_VERSION_ATTR, None),
        method=normalized_method,
        action=action,
        route_name=pattern.name,
        namespace="",
        route=pattern_text,
        registered_route=pattern_text,
    )
