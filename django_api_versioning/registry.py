from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from threading import RLock
from typing import Callable

from django.http import HttpResponse
from django.urls import URLPattern, path
from django.urls.resolvers import RegexPattern
from django.views import View

from .exceptions import (
    InvalidVersionError,
    VersioningError,
    VersionRangeError,
    VersionTypeError,
)
from .lifecycle_metadata import EndpointLifecycle, parse_endpoint_lifecycle
from .settings import api_settings

VersionKey = int | None
VersionMatrix = dict[str, dict[VersionKey, Callable]]
ResolvedRouteCandidate = tuple[int, URLPattern, str, int, VersionKey]
RouteSortKey = tuple[bool, VersionKey, bool, int, int]
_UNOWNED_OWNER_IDENTITY = object()
_ROUTER_OWNER_IDENTITY = object()

REMOVED_ROUTE = object()


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


ViewType = Callable[..., HttpResponse] | type[View]


def _synchronized(method):
    """Serialize registry mutations and keep multi-step checks atomic."""

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class UrlRegistry:
    """Registry for managing API versioning URLs."""

    _SOURCE_VERSION_ATTR = "_django_api_versioning_source_version"
    _ROUTE_VERSION_ATTR = "_django_api_versioning_route_version"
    _LOGICAL_ENDPOINT_ATTR = "_django_api_versioning_logical_endpoint"
    _ROUTER_OWNER_ATTR = "_django_api_versioning_router_owner"
    _ROUTER_PREFIX_ATTR = "_django_api_versioning_router_prefix"
    _ROUTER_TRAILING_SLASH_ATTR = "_django_api_versioning_router_trailing_slash"

    def __init__(self) -> None:
        self._lock = RLock()
        self.urlpatterns: list[URLPattern] = []
        self._removal_boundaries: dict[str, set[int]] = {}
        self._router_removal_boundaries: dict[
            tuple[str, str | None, bool | None], set[int]
        ] = {}
        self._removed_patterns: dict[tuple[object, ...], URLPattern] = {}
        self._endpoint_lifecycle: dict[
            tuple[str, int, str | None, str | None, object | None], EndpointLifecycle
        ] = {}

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Hold the re-entrant lock for an atomic multi-operation transaction."""
        with self._lock:
            yield

    @_synchronized
    def clear(self) -> None:
        """Clear active routes and removal declarations."""
        self.urlpatterns.clear()
        self._removal_boundaries.clear()
        self._router_removal_boundaries.clear()
        self._removed_patterns.clear()
        self._endpoint_lifecycle.clear()

    @_synchronized
    def remove(
        self,
        logical_endpoint: str,
        from_version: int,
        *,
        owner: object | None = None,
    ) -> None:
        """Suppress an endpoint from a concrete version until reintroduced."""
        if not isinstance(logical_endpoint, str) or not logical_endpoint:
            raise TypeError("logical_endpoint must be a non-empty string.")
        if isinstance(from_version, bool) or not isinstance(from_version, int):
            raise VersionTypeError("Removal version must be an integer.")
        if from_version > api_settings.API_MAX_VERSION:
            raise InvalidVersionError(
                f"Removal version {from_version} is above the maximum allowed "
                f"version {api_settings.API_MAX_VERSION}."
            )
        if from_version < api_settings.API_MIN_VERSION:
            raise VersionRangeError(
                f"Removal version {from_version} is below the minimum allowed "
                f"version {api_settings.API_MIN_VERSION}."
            )

        if owner is None:
            self._removal_boundaries.setdefault(logical_endpoint, set()).add(
                from_version
            )
        else:
            # A router tombstone applies to the same generated URL identity,
            # not every route that happens to share its logical endpoint name.
            # Distinct trailing-slash policies can coexist for one logical name.
            owner_patterns = [
                pattern
                for pattern in [*self.urlpatterns, *self._removed_patterns.values()]
                if getattr(pattern, self._ROUTER_OWNER_ATTR, None) is owner
                and getattr(pattern, self._LOGICAL_ENDPOINT_ATTR, None)
                == logical_endpoint
            ]
            route_identities = {
                (
                    getattr(pattern, self._ROUTER_PREFIX_ATTR, None),
                    getattr(pattern, self._ROUTER_TRAILING_SLASH_ATTR, None),
                )
                for pattern in owner_patterns
            }
            for router_prefix, trailing_slash in route_identities:
                self._router_removal_boundaries.setdefault(
                    (logical_endpoint, router_prefix, trailing_slash), set()
                ).add(from_version)

        preserved_versions = set()
        for index in range(len(self.urlpatterns) - 1, -1, -1):
            pattern = self.urlpatterns[index]
            if getattr(pattern, self._LOGICAL_ENDPOINT_ATTR, None) != logical_endpoint:
                continue
            if getattr(pattern, self._ROUTER_OWNER_ATTR, None) is not owner:
                continue
            route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
            source_version = getattr(pattern, self._SOURCE_VERSION_ATTR, None)
            if route_version is None or route_version < from_version:
                continue
            if source_version is not None and source_version > from_version:
                preserved_versions.add(route_version)
                continue
            self._record_removed(pattern, logical_endpoint)
            del self.urlpatterns[index]

        # Lifecycle metadata belongs to a concrete active declaration segment.
        # Preserve it only for versions that already have a newer active source.
        for key in list(self._endpoint_lifecycle):
            endpoint, version, _, _, metadata_owner = key
            if (
                metadata_owner is owner
                and endpoint == logical_endpoint
                and version >= from_version
                and version not in preserved_versions
            ):
                del self._endpoint_lifecycle[key]

    def _removal_boundary(
        self,
        logical_endpoint: str | None,
        route_version: int | None,
        owner: object | None = None,
        router_prefix: str | None = None,
        trailing_slash: bool | None = None,
    ) -> int | None:
        if logical_endpoint is None or route_version is None:
            return None
        if owner is None:
            boundaries = self._removal_boundaries.get(logical_endpoint, set())
        else:
            boundaries = self._router_removal_boundaries.get(
                (logical_endpoint, router_prefix, trailing_slash), set()
            )
        applicable = [boundary for boundary in boundaries if boundary <= route_version]
        return max(applicable) if applicable else None

    def _is_suppressed(
        self,
        logical_endpoint: str | None,
        route_version: int | None,
        source_version: int | None,
        owner: object | None = None,
        router_prefix: str | None = None,
        trailing_slash: bool | None = None,
    ) -> bool:
        boundary = self._removal_boundary(
            logical_endpoint,
            route_version,
            owner,
            router_prefix,
            trailing_slash,
        )
        return boundary is not None and (
            source_version is None or source_version <= boundary
        )

    def _record_removed(self, pattern: URLPattern, logical_endpoint: str) -> None:
        route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
        if route_version is None:
            return

        owner = getattr(pattern, self._ROUTER_OWNER_ATTR, None)
        if owner is None:
            key = (logical_endpoint, route_version)
        else:
            key = (
                logical_endpoint,
                route_version,
                getattr(pattern, self._ROUTER_PREFIX_ATTR, None),
                getattr(pattern, self._ROUTER_TRAILING_SLASH_ATTR, None),
            )
        existing = self._removed_patterns.get(key)
        if existing is not None:
            existing_owner = getattr(existing, self._ROUTER_OWNER_ATTR, None)
            new_owner = getattr(pattern, self._ROUTER_OWNER_ATTR, None)
            if existing_owner is not new_owner:
                # A suppressed re-registration must not transfer a tombstone
                # to a different router (or from an unowned endpoint).
                return

        self._removed_patterns[key] = pattern

    @_synchronized
    def register(
        self,
        route: str,
        view: ViewType,
        name: str | None = None,
        source_version: int | None = None,
        route_version: int | None = None,
        logical_endpoint: str | None = None,
    ) -> None:
        """Register a route, preferring definitions from newer source versions."""
        route_index = self._find_route_index(route)

        if route_index is not None:
            existing_pattern = self.urlpatterns[route_index]
            if getattr(existing_pattern, self._ROUTER_OWNER_ATTR, None) is not None:
                raise VersioningError(
                    f"Route pattern {route!r} is already owned by a VersionedRouter; "
                    "decorator registration cannot replace it."
                )

            if not self._should_replace(existing_pattern, source_version):
                return

        pattern = self._create_pattern(route, view, name)
        setattr(pattern, self._SOURCE_VERSION_ATTR, source_version)
        setattr(pattern, self._ROUTE_VERSION_ATTR, route_version)
        if logical_endpoint is not None:
            setattr(pattern, self._LOGICAL_ENDPOINT_ATTR, logical_endpoint)

        if self._is_suppressed(logical_endpoint, route_version, source_version):
            if route_index is not None:
                existing = self.urlpatterns[route_index]
                existing_logical = getattr(existing, self._LOGICAL_ENDPOINT_ATTR, None)
                existing_version = getattr(existing, self._ROUTE_VERSION_ATTR, None)
                existing_source = getattr(existing, self._SOURCE_VERSION_ATTR, None)
                if self._is_suppressed(
                    existing_logical, existing_version, existing_source
                ):
                    del self.urlpatterns[route_index]
            if logical_endpoint is not None:
                self._record_removed(pattern, logical_endpoint)
            return

        if logical_endpoint is not None and route_version is not None:
            self._removed_patterns.pop((logical_endpoint, route_version), None)

        if route_index is None:
            self.urlpatterns.append(pattern)
        else:
            self.urlpatterns[route_index] = pattern

        self._sort_urlpatterns()

    @_synchronized
    def register_urlpattern(
        self,
        pattern: URLPattern,
        source_version: int | None = None,
        route_version: int | None = None,
        logical_endpoint: str | None = None,
    ) -> None:
        """Register an existing Django URLPattern without rebuilding it.

        This is the lossless insertion path for integrations that generate
        URLPatterns themselves (for example, DRF routers). The original
        pattern, callback, converters, defaults, name, and callback metadata
        are retained. Collision precedence is identical to ``register()``.
        """
        if not isinstance(pattern, URLPattern):
            raise TypeError("pattern must be a django.urls.URLPattern instance.")

        route_key = str(pattern.pattern)
        pattern_owner = getattr(pattern, self._ROUTER_OWNER_ATTR, None)
        route_index = self._find_route_index(
            route_key,
            regex_route=isinstance(pattern.pattern, RegexPattern),
        )

        if route_index is None:
            new_router = getattr(pattern, self._ROUTER_OWNER_ATTR, None)
            new_prefix = getattr(pattern, self._ROUTER_PREFIX_ATTR, None)
            for existing in self.urlpatterns:
                existing_router = getattr(existing, self._ROUTER_OWNER_ATTR, None)
                existing_prefix = getattr(existing, self._ROUTER_PREFIX_ATTR, None)
                if (
                    new_router is not None
                    and existing_router is not None
                    and existing_router is not new_router
                    and new_prefix is not None
                    and existing_prefix == new_prefix
                    and getattr(existing, self._ROUTER_TRAILING_SLASH_ATTR, None)
                    == getattr(pattern, self._ROUTER_TRAILING_SLASH_ATTR, None)
                    and getattr(existing, self._ROUTE_VERSION_ATTR, None)
                    == route_version
                ):
                    raise VersioningError(
                        f"Router prefix {new_prefix!r} in version {route_version} "
                        "is already registered by another VersionedRouter instance."
                    )

        if route_index is not None:
            existing_pattern = self.urlpatterns[route_index]
            existing_router = getattr(existing_pattern, self._ROUTER_OWNER_ATTR, None)
            new_router = getattr(pattern, self._ROUTER_OWNER_ATTR, None)
            if (
                existing_router is not None
                and new_router is not None
                and existing_router is not new_router
            ):
                existing_prefix = getattr(
                    existing_pattern, self._ROUTER_PREFIX_ATTR, None
                )
                new_prefix = getattr(pattern, self._ROUTER_PREFIX_ATTR, None)
                same_router_prefix = (
                    existing_prefix is not None
                    and existing_prefix == new_prefix
                    and getattr(
                        existing_pattern, self._ROUTER_TRAILING_SLASH_ATTR, None
                    )
                    == getattr(pattern, self._ROUTER_TRAILING_SLASH_ATTR, None)
                    and getattr(existing_pattern, self._ROUTE_VERSION_ATTR, None)
                    == route_version
                )
                if same_router_prefix:
                    raise VersioningError(
                        f"Router prefix {new_prefix!r} in version {route_version} "
                        "is already registered by another VersionedRouter instance."
                    )
                raise VersioningError(
                    f"Route pattern {route_key!r} is already registered by another "
                    "VersionedRouter instance. Use a distinct route prefix for each router."
                )
            if (existing_router is None) != (new_router is None):
                raise VersioningError(
                    f"Route pattern {route_key!r} is already registered by a "
                    "different registration owner. Use a distinct route path."
                )
            if not self._should_replace(existing_pattern, source_version):
                return

        setattr(pattern, self._SOURCE_VERSION_ATTR, source_version)
        setattr(pattern, self._ROUTE_VERSION_ATTR, route_version)
        if logical_endpoint is not None:
            setattr(pattern, self._LOGICAL_ENDPOINT_ATTR, logical_endpoint)

        router_prefix = getattr(pattern, self._ROUTER_PREFIX_ATTR, None)
        router_trailing_slash = getattr(pattern, self._ROUTER_TRAILING_SLASH_ATTR, None)
        if self._is_suppressed(
            logical_endpoint,
            route_version,
            source_version,
            owner=pattern_owner,
            router_prefix=router_prefix,
            trailing_slash=router_trailing_slash,
        ):
            if route_index is not None:
                existing = self.urlpatterns[route_index]
                existing_logical = getattr(existing, self._LOGICAL_ENDPOINT_ATTR, None)
                existing_version = getattr(existing, self._ROUTE_VERSION_ATTR, None)
                existing_source = getattr(existing, self._SOURCE_VERSION_ATTR, None)
                if self._is_suppressed(
                    existing_logical,
                    existing_version,
                    existing_source,
                    owner=getattr(existing, self._ROUTER_OWNER_ATTR, None),
                    router_prefix=getattr(existing, self._ROUTER_PREFIX_ATTR, None),
                    trailing_slash=getattr(
                        existing, self._ROUTER_TRAILING_SLASH_ATTR, None
                    ),
                ):
                    del self.urlpatterns[route_index]
            if logical_endpoint is not None:
                self._record_removed(pattern, logical_endpoint)
            return

        if logical_endpoint is not None and route_version is not None:
            if pattern_owner is None:
                removed_key = (logical_endpoint, route_version)
            else:
                removed_key = (
                    logical_endpoint,
                    route_version,
                    router_prefix,
                    router_trailing_slash,
                )
            self._removed_patterns.pop(removed_key, None)

        if route_index is None:
            self.urlpatterns.append(pattern)
        else:
            self.urlpatterns[route_index] = pattern

        self._sort_urlpatterns()

    @_synchronized
    def get_route_version(self, route: str) -> int | None:
        """Return the concrete version registered for a resolved route."""
        route_index = next(
            (
                index
                for index, pattern in enumerate(self.urlpatterns)
                if str(pattern.pattern) == route
            ),
            None,
        )
        if route_index is None:
            route_index = self._find_route_index(route)
        if route_index is None:
            return None

        return getattr(
            self.urlpatterns[route_index],
            self._ROUTE_VERSION_ATTR,
            None,
        )

    @_synchronized
    def get_version_matrix(self) -> VersionMatrix:
        """
        Return ``{route: {route_version: callback}}``.

        ``route_version`` is ``None`` for unversioned routes.  This is the
        source of truth for ``check_versions`` and ``assert_version_matrix``.
        """
        matrix: VersionMatrix = {}
        for pattern in self.urlpatterns:
            route = str(pattern.pattern)
            route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
            matrix.setdefault(route, {})[route_version] = pattern.callback
        for key, pattern in self._removed_patterns.items():
            route_version = key[1]
            tombstone_path = str(pattern.pattern)
            matrix.setdefault(tombstone_path, {}).setdefault(
                route_version, REMOVED_ROUTE
            )
        return matrix

    @_synchronized
    def get_logical_version_matrix(self) -> VersionMatrix:
        """
        Return ``{logical_endpoint: {route_version: callback}}``.

        Groups physical URLs by their logical endpoint identity. This is used
        by check_versions to correctly identify gaps within each logical
        endpoint's version span, avoiding false warnings.
        """
        entries = []
        for pattern in self.urlpatterns:
            logical_id = getattr(
                pattern, self._LOGICAL_ENDPOINT_ATTR, str(pattern.pattern)
            )
            route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
            entries.append((logical_id, route_version, pattern, pattern.callback))

        for key, pattern in self._removed_patterns.items():
            logical_id, route_version = key[:2]
            entries.append((logical_id, route_version, pattern, REMOVED_ROUTE))

        # A logical endpoint/version can intentionally have more than one
        # physical route when independent routers use different trailing-slash
        # policies. A plain {logical_endpoint: version} map silently overwrites
        # one callback. Keep the familiar key for unambiguous operations and
        # add a stable router/route discriminator only when a collision exists.
        counts = {}
        owner_groups = {}
        for logical_id, route_version, pattern, _callback in entries:
            identity = (logical_id, route_version)
            counts[identity] = counts.get(identity, 0) + 1

            owner = getattr(pattern, self._ROUTER_OWNER_ATTR, None)
            if owner is None:
                owner_identity = (_UNOWNED_OWNER_IDENTITY,)
            else:
                owner_identity = (
                    _ROUTER_OWNER_IDENTITY,
                    getattr(pattern, self._ROUTER_PREFIX_ATTR, None),
                    getattr(pattern, self._ROUTER_TRAILING_SLASH_ATTR, None),
                )
            owner_groups.setdefault(logical_id, set()).add(owner_identity)

        matrix: VersionMatrix = {}
        for logical_id, route_version, pattern, callback in entries:
            owner = getattr(pattern, self._ROUTER_OWNER_ATTR, None)
            has_multiple_owners = len(owner_groups[logical_id]) > 1
            has_same_version_collision = counts[(logical_id, route_version)] > 1

            if has_multiple_owners or has_same_version_collision:
                if owner is not None:
                    discriminator = (
                        f"router={getattr(pattern, self._ROUTER_PREFIX_ATTR, None)!r}, "
                        "trailing_slash="
                        f"{getattr(pattern, self._ROUTER_TRAILING_SLASH_ATTR, None)!r}"
                    )
                else:
                    discriminator = f"route={str(pattern.pattern)!r}"
                matrix_key = f"{logical_id} [{discriminator}]"
            else:
                matrix_key = logical_id
            matrix.setdefault(matrix_key, {})[route_version] = callback
        return matrix

    @staticmethod
    def _canonical_route_key(route: str) -> str:
        """Normalize anchored regexes containing only literal path text."""
        if not (route.startswith("^") and route.endswith("$")):
            return route

        literal = route[1:-1]
        if "<" in literal or ">" in literal:
            return route

        normalized = []
        escaped = False
        for character in literal:
            if escaped:
                # Escaped punctuation is literal; alphanumeric escapes such
                # as \\d and \\w are regex classes, not static path text.
                if character.isalnum():
                    return route
                normalized.append(character)
                escaped = False
            elif character == "\\":
                escaped = True
            elif character in ".^$*+?{}[]|()":
                return route
            else:
                normalized.append(character)

        if escaped:
            return route
        return "".join(normalized)

    def _find_route_index(
        self,
        route: str,
        *,
        regex_route: bool = False,
    ) -> int | None:
        """Return the index of a registered route, or None if absent."""
        for index, pattern in enumerate(self.urlpatterns):
            existing_pattern_text = str(pattern.pattern)
            existing_is_regex = isinstance(pattern.pattern, RegexPattern)
            if existing_pattern_text == route and existing_is_regex == regex_route:
                return index

            route_key = self._canonical_route_key(route) if regex_route else route
            existing_key = (
                self._canonical_route_key(existing_pattern_text)
                if existing_is_regex
                else existing_pattern_text
            )
            if existing_key == route_key:
                return index

        return None

    @staticmethod
    def _resolved_route_match_length(route: str, registered_route: str) -> int:
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
                    continue
                matched_length = max(matched_length, len(pattern_candidate))
        return matched_length

    @_synchronized
    def get_resolved_route_version_for_match(
        self, resolver_match: object
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
                for pattern in self.urlpatterns
                if id(pattern) in matched_pattern_ids
                and pattern.callback is callback
                and (url_name is None or pattern.name == url_name)
                and self._resolved_route_match_length(route, str(pattern.pattern))
            ]
            if not exact_matches:
                return False, None
            versions = {
                getattr(pattern, self._ROUTE_VERSION_ATTR, None)
                for pattern in exact_matches
            }
            if len(versions) != 1:
                return True, None
            return True, next(iter(versions))

        url_name = getattr(resolver_match, "url_name", None)
        matches = []
        for pattern in self.urlpatterns:
            if pattern.callback is not callback:
                continue
            if url_name is not None and pattern.name != url_name:
                continue
            matched_length = self._resolved_route_match_length(
                route, str(pattern.pattern)
            )
            if matched_length:
                matches.append(
                    (
                        matched_length,
                        getattr(pattern, self._ROUTE_VERSION_ATTR, None),
                    )
                )

        if not matches:
            return False, None

        longest = max(length for length, _ in matches)
        versions = {version for length, version in matches if length == longest}
        if len(versions) != 1:
            return True, None
        return True, next(iter(versions))

    @_synchronized
    def get_resolved_route_version(self, route: str) -> int | None:
        """Resolve a version from the longest registered route suffix.

        Django's ResolverMatch.route includes every parent URLResolver prefix.
        Matching a registered route as a complete suffix therefore supports
        nested includes without confusing a parent API-like prefix for the
        child endpoint's version.
        """
        matches: list[tuple[int, int]] = []
        for pattern in self.urlpatterns:
            matched_length = self._resolved_route_match_length(
                route, str(pattern.pattern)
            )
            version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
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

    @_synchronized
    def resolve_operation(
        self,
        resolver_match: object,
        method: str,
        *,
        allow_unmapped_method: bool = False,
        require_exact_pattern: bool = True,
    ) -> ResolvedOperation | None:
        """Resolve one registered logical operation from Django's ResolverMatch.

        Runtime callers require Django's resolver trace to identify the exact
        registered URLPattern. Schema generators may opt into route/name
        matching because their synthetic ResolverMatch can refer to a generated
        operation rather than the original URLPattern. DRF's method-to-action
        map identifies the action selected for this HTTP method.
        Ambiguous or incomplete matches fail closed.
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
        for pattern in self.urlpatterns:
            if (
                matched_pattern_ids is not None
                and id(pattern) not in matched_pattern_ids
            ):
                continue
            if url_name is not None and pattern.name != url_name:
                continue

            logical_endpoint = getattr(pattern, self._LOGICAL_ENDPOINT_ATTR, None)
            route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
            if not isinstance(logical_endpoint, str) or not logical_endpoint:
                continue
            if isinstance(route_version, bool) or not isinstance(route_version, int):
                continue
            if version_namespaces and f"v{route_version}" not in version_namespaces:
                continue

            matched_length = self._resolved_route_match_length(
                route, str(pattern.pattern)
            )
            if not matched_length:
                continue

            source_version = getattr(pattern, self._SOURCE_VERSION_ATTR, None)
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
        actions = getattr(callback, "actions", None)
        action = None
        if isinstance(actions, Mapping):
            action = actions.get(normalized_method.lower())
            if action is None and normalized_method == "HEAD":
                action = actions.get("get")
            # DRF handles OPTIONS outside the ViewSet action map. For a
            # real 405 response, the middleware may also request route-only
            # resolution; action-scoped metadata remains inapplicable.
            if (
                action is None
                and normalized_method != "OPTIONS"
                and not allow_unmapped_method
            ):
                return None
            if action is not None and (not isinstance(action, str) or not action):
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
            router_owner=getattr(pattern, self._ROUTER_OWNER_ATTR, None),
        )

    @_synchronized
    def resolve_registered_operation(
        self, logical_endpoint: str, route_version: int, method: str
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
            for pattern in self.urlpatterns
            if getattr(pattern, self._LOGICAL_ENDPOINT_ATTR, None) == logical_endpoint
            and getattr(pattern, self._ROUTE_VERSION_ATTR, None) == route_version
        ]
        if len(candidates) != 1:
            return None

        pattern = candidates[0]
        normalized_method = method.upper()
        actions = getattr(pattern.callback, "actions", None)
        action = None
        if isinstance(actions, Mapping):
            action = actions.get(normalized_method.lower())
            if action is None and normalized_method == "HEAD":
                action = actions.get("get")
            if not isinstance(action, str) or not action:
                return None

        pattern_text = str(pattern.pattern)
        return ResolvedOperation(
            logical_endpoint=logical_endpoint,
            route_version=route_version,
            source_version=getattr(pattern, self._SOURCE_VERSION_ATTR, None),
            method=normalized_method,
            action=action,
            route_name=pattern.name,
            namespace="",
            route=pattern_text,
            registered_route=pattern_text,
        )

    @_synchronized
    def register_endpoint_lifecycle(
        self,
        logical_endpoint: str,
        route_version: int,
        *,
        method: str | None = None,
        action: str | None = None,
        deprecated_at: str | None = None,
        sunset: str | None = None,
        owner: object | None = None,
    ) -> None:
        """Register lifecycle dates for a route, HTTP method, or DRF action."""
        if not isinstance(logical_endpoint, str) or not logical_endpoint:
            raise VersioningError("logical_endpoint must be a non-empty string.")
        if isinstance(route_version, bool) or not isinstance(route_version, int):
            raise VersionTypeError("Endpoint lifecycle version must be an integer.")
        if route_version < api_settings.API_MIN_VERSION:
            raise VersionRangeError(
                f"Endpoint lifecycle version {route_version} is below "
                f"API_MIN_VERSION {api_settings.API_MIN_VERSION}."
            )
        if route_version > api_settings.API_MAX_VERSION:
            raise InvalidVersionError(
                f"Endpoint lifecycle version {route_version} is above "
                f"API_MAX_VERSION {api_settings.API_MAX_VERSION}."
            )

        normalized_method = None
        if method is not None:
            if not isinstance(method, str) or not method.strip():
                raise VersioningError("Endpoint lifecycle method must be a string.")
            normalized_method = method.strip().upper()

        normalized_action = None
        if action is not None:
            if not isinstance(action, str) or not action.strip():
                raise VersioningError("Endpoint lifecycle action must be a string.")
            normalized_action = action.strip()

        lifecycle = parse_endpoint_lifecycle(deprecated_at, sunset)
        key = (
            logical_endpoint,
            route_version,
            normalized_method,
            normalized_action,
            owner,
        )
        existing = self._endpoint_lifecycle.get(key)
        if existing is not None and existing != lifecycle:
            raise VersioningError(
                "Conflicting endpoint lifecycle declarations for "
                f"{logical_endpoint!r} version {route_version}."
            )
        self._endpoint_lifecycle[key] = lifecycle

    @_synchronized
    def get_endpoint_lifecycle(
        self, operation: ResolvedOperation
    ) -> EndpointLifecycle | None:
        """Return the most conservative metadata applicable to an operation.

        Route-wide, action-wide, method-wide, and exact method/action scopes
        compose monotonically: the earliest configured instant wins for each
        header. A narrower declaration can add metadata but cannot delay it.
        """
        # HTTP HEAD is the body-less form of GET. DRF maps it to the
        # GET action, and GET-scoped lifecycle declarations must therefore
        # apply to HEAD as well. Explicit HEAD declarations still compose.
        methods = (
            (operation.method, "GET")
            if operation.method == "HEAD"
            else (operation.method,)
        )
        scopes = [(None, None), (None, operation.action)]
        for method in methods:
            scopes.extend(
                (
                    (method, None),
                    (method, operation.action),
                )
            )

        records = []
        for method, action in dict.fromkeys(scopes):
            record = self._endpoint_lifecycle.get(
                (
                    operation.logical_endpoint,
                    operation.route_version,
                    method,
                    action,
                    operation.router_owner,
                )
            )
            if record is not None:
                records.append(record)

        if not records:
            return None

        deprecation_dates = [
            record.deprecated_at
            for record in records
            if record.deprecated_at is not None
        ]
        sunset_dates = [
            record.sunset for record in records if record.sunset is not None
        ]
        return EndpointLifecycle(
            deprecated_at=min(deprecation_dates) if deprecation_dates else None,
            sunset=min(sunset_dates) if sunset_dates else None,
        )

    def _should_replace(
        self,
        existing_pattern: URLPattern,
        source_version: int | None,
    ) -> bool:
        """Return whether the new declaration should replace the existing one.

        Newer ``source_version`` values win. When either side has no source
        version (e.g. unversioned endpoints or direct ``register()`` calls),
        the last registration wins.
        """
        existing_version = getattr(
            existing_pattern,
            self._SOURCE_VERSION_ATTR,
            None,
        )

        if existing_version is None or source_version is None:
            return True

        return source_version >= existing_version

    @staticmethod
    def _create_pattern(
        route: str,
        view: ViewType,
        name: str | None,
    ) -> URLPattern:
        """Create a URL pattern from a function or class-based view.

        Only class-based views are routed through ``as_view()``. Calling
        ``as_view`` on an instance would still "work" because the classmethod
        is accessible from the instance, but the resulting pattern loses the
        ``view_class`` reference used by ``resolve()`` and DRF.
        """
        if isinstance(view, View):
            raise TypeError(
                f"Pass the view class {type(view).__name__!r}, not an instance. "
                f"Use @endpoint(...) on the class itself, or call "
                f"{type(view).__name__}.as_view() before registering."
            )

        if isinstance(view, type) and callable(getattr(view, "as_view", None)):
            # Check if this is a DRF ViewSet (has actions in signature)
            # ViewSets require an action dict to be passed to as_view()
            try:
                import inspect

                sig = inspect.signature(view.as_view)
            except (TypeError, ValueError):
                # Some extension-backed callables do not expose a signature.
                # Calling as_view() below remains the authoritative check.
                sig = None

            if sig is not None and "actions" in sig.parameters:
                actions_param = sig.parameters["actions"]
                if actions_param.default is inspect.Parameter.empty:
                    raise TypeError(
                        f"ViewSet '{view.__name__}' cannot be registered directly. "
                        f"Pass a configured callable like: "
                        f"{view.__name__}.as_view({{'get': 'list', 'post': 'create'}})"
                    )

            try:
                view = view.as_view()
            except TypeError as e:
                # DRF ViewSetMixin exposes actions=None but rejects a missing map
                # when called. Preserve that runtime signal and add class context.
                if "actions" in str(e):
                    raise TypeError(
                        f"ViewSet '{view.__name__}' cannot be registered directly. "
                        f"Pass a configured callable like: "
                        f"{view.__name__}.as_view({{'get': 'list', 'post': 'create'}})"
                    ) from e
                raise
        return path(route, view, name=name)

    @staticmethod
    def _route_specificity_key(pattern: URLPattern) -> tuple[int, bool, int]:
        """Prefer longer literal prefixes before generic converter/regex routes."""
        route_text = str(pattern.pattern)
        if isinstance(pattern.pattern, RegexPattern):
            source = route_text[1:] if route_text.startswith("^") else route_text
            source = source[:-1] if source.endswith("$") else source
            escaped = False
            dynamic_start = len(source)
            for index, character in enumerate(source):
                if escaped:
                    escaped = False
                    continue
                if character == "\\":
                    if index + 1 < len(source) and source[index + 1].isalnum():
                        dynamic_start = index
                        break
                    escaped = True
                    continue
                if character in "([?*+{.^$|)]}":
                    dynamic_start = index
                    break
            literal_prefix = source[:dynamic_start]
            has_dynamic = dynamic_start < len(source)
        else:
            dynamic_start = route_text.find("<")
            literal_prefix = (
                route_text if dynamic_start < 0 else route_text[:dynamic_start]
            )
            has_dynamic = dynamic_start >= 0

        return (-len(literal_prefix), has_dynamic, -len(route_text))

    def _sort_urlpatterns(self) -> None:
        """Order versions first, then static and specific routes before catch-alls."""

        def sort_key(pattern: URLPattern) -> RouteSortKey:
            route_version = getattr(pattern, self._ROUTE_VERSION_ATTR, None)
            specificity = self._route_specificity_key(pattern)
            has_dynamic = specificity[1]
            return (
                route_version is not None,
                route_version,
                has_dynamic,
                specificity[0] * int(has_dynamic),
                specificity[2] * int(has_dynamic),
            )

        self.urlpatterns.sort(key=sort_key)


registry = UrlRegistry()
