"""Version-aware integration for Django REST Framework ViewSets.

This module is optional: importing the core package does not require DRF.
"""

import logging
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from django.urls import URLPattern, URLResolver, include, path

try:
    from rest_framework.exceptions import NotFound
    from rest_framework.versioning import NamespaceVersioning
except ImportError as exc:  # pragma: no cover - exercised without optional DRF
    raise ImportError(
        "VersionedRouter requires Django REST Framework. Install a DRF release "
        "compatible with your Django version; see the package compatibility "
        "matrix."
    ) from exc

from .exceptions import (
    InvalidVersionError,
    VersioningError,
    VersionRangeError,
    VersionTypeError,
)
from .registry import registry
from .settings import api_settings

logger = logging.getLogger(__name__)

_ROUTE_VERSION_ATTR = registry._ROUTE_VERSION_ATTR


class VersionedRouter:
    """Register DRF ViewSets as versioned, independently inherited route sets.

    Each declaration is expanded into the concrete versions it covers. The
    package registry resolves collisions per generated URLPattern, so a custom
    action that is absent from a newer ViewSet remains inherited from the
    earlier declaration.
    """

    def __init__(
        self,
        trailing_slash: bool = True,
        use_regex_path: bool = True,
        app_name: str = "django_api_versioning",
    ) -> None:
        if not isinstance(app_name, str) or not app_name.strip():
            raise VersioningError("app_name must be a non-empty string.")

        self.trailing_slash = trailing_slash
        self.use_regex_path = use_regex_path
        self.app_name = app_name
        self._registry_owner = object()
        self._route_keys: set[str] = set()
        self._basenames: dict[str, str] = {}
        self._basename_prefixes: dict[str, str] = {}

    def register(
        self,
        prefix: str,
        viewset: type,
        basename: str | None = None,
        *,
        version: int | None = None,
        versions: list[int] | None = None,
    ) -> None:
        """Register a ViewSet for a version segment or an explicit version set.

        version=N registers the ViewSet from N through API_MAX_VERSION.
        versions=[...] registers only the listed concrete versions.
        Omitting both creates an unversioned route set.
        """
        if not isinstance(prefix, str):
            raise TypeError("prefix must be a string.")
        if not prefix or prefix.startswith("/") or prefix.endswith("/"):
            raise VersioningError(
                "prefix must be a non-empty relative path without leading "
                "or trailing '/'."
            )
        if version is not None and versions is not None:
            raise VersionRangeError("Use either 'version' or 'versions', not both.")
        if versions is not None and not isinstance(versions, list):
            raise VersionTypeError("'versions' must be a list of integers.")

        if version is not None:
            self._validate_version(version)
            if version < api_settings.API_MIN_VERSION:
                logger.warning(
                    "ViewSet prefix %r starts at version %d, below "
                    "API_MIN_VERSION %d. No routes will be registered.",
                    prefix,
                    version,
                    api_settings.API_MIN_VERSION,
                )
                return
            declarations: list[tuple[int | None, int | None]] = [
                (concrete, version)
                for concrete in range(version, api_settings.API_MAX_VERSION + 1)
            ]
        elif versions is not None:
            for declared_version in versions:
                self._validate_version(declared_version)
            if len(set(versions)) != len(versions):
                raise VersionRangeError("'versions' must not contain duplicates.")
            declarations = []
            for declared_version in versions:
                if declared_version < api_settings.API_MIN_VERSION:
                    logger.warning(
                        "ViewSet prefix %r includes version %d, below "
                        "API_MIN_VERSION %d. Skipping this version.",
                        prefix,
                        declared_version,
                        api_settings.API_MIN_VERSION,
                    )
                    continue
                declarations.append((declared_version, declared_version))
        else:
            declarations = [(None, None)]

        # A logical registration may expand into several concrete versions.
        # Treat the expansion as one transaction: a collision in a later
        # version must not leave earlier routes or router bookkeeping behind.
        registry_urlpatterns = list(registry.urlpatterns)
        removed_patterns = dict(registry._removed_patterns)
        route_keys = set(self._route_keys)
        basenames = dict(self._basenames)
        basename_prefixes = dict(self._basename_prefixes)

        try:
            for route_version, source_version in declarations:
                self._register_version(
                    prefix=prefix,
                    viewset=viewset,
                    basename=basename,
                    source_version=source_version,
                    route_version=route_version,
                )
        except Exception:
            registry.urlpatterns[:] = registry_urlpatterns
            registry._removed_patterns.clear()
            registry._removed_patterns.update(removed_patterns)
            self._route_keys.clear()
            self._route_keys.update(route_keys)
            self._basenames.clear()
            self._basenames.update(basenames)
            self._basename_prefixes.clear()
            self._basename_prefixes.update(basename_prefixes)
            raise

    def remove(self, prefix: str, route_name: str, *, from_version: int) -> None:
        """Remove one logical DRF route from a concrete version onward.

        route_name is the URL name generated from the registration basename
        and action (for example, "order-archive"), not a regex pattern.
        """
        if not isinstance(prefix, str):
            raise TypeError("prefix must be a string.")
        if not prefix or prefix.startswith("/") or prefix.endswith("/"):
            raise VersioningError(
                "prefix must be a non-empty relative path without leading "
                "or trailing '/'."
            )
        if not isinstance(route_name, str):
            raise TypeError("route_name must be a string.")
        if not route_name:
            raise VersioningError("route_name must be a non-empty string.")
        registry.remove(f"{prefix}:{route_name}", from_version)

    def set_lifecycle(
        self,
        prefix: str,
        route_name: str,
        *,
        version: int,
        action: str | None = None,
        methods: list[str] | None = None,
        deprecated_at: str | None = None,
        sunset: str | None = None,
    ) -> None:
        """Declare lifecycle metadata for one concrete DRF route version.

        ``action`` scopes the declaration to a ViewSet action. ``methods``
        optionally narrows it to HTTP methods; each method is resolved through
        the router's action map before the declaration is stored.
        """
        if (
            not isinstance(prefix, str)
            or not prefix
            or prefix.startswith("/")
            or prefix.endswith("/")
        ):
            raise VersioningError(
                "prefix must be a non-empty relative path without leading or "
                "trailing '/'."
            )
        if not isinstance(route_name, str) or not route_name:
            raise VersioningError("route_name must be a non-empty string.")
        self._validate_version(version)
        if version < api_settings.API_MIN_VERSION:
            raise VersionRangeError(
                f"Lifecycle version {version} is below API_MIN_VERSION "
                f"{api_settings.API_MIN_VERSION}."
            )

        logical_endpoint = f"{prefix}:{route_name}"
        matches = [
            pattern
            for pattern in registry.urlpatterns
            if str(pattern.pattern) in self._route_keys
            and getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
            == logical_endpoint
            and getattr(pattern, _ROUTE_VERSION_ATTR, None) == version
        ]
        if len(matches) != 1:
            raise VersioningError(
                f"Expected one registered route for {logical_endpoint!r} "
                f"in version {version}; found {len(matches)}."
            )

        actions = getattr(matches[0].callback, "actions", None)
        if not isinstance(actions, Mapping):
            raise VersioningError(
                f"Route {logical_endpoint!r} does not expose a DRF action map."
            )

        normalized_action = None
        if action is not None:
            if not isinstance(action, str) or not action.strip():
                raise VersioningError("action must be a non-empty string.")
            normalized_action = action.strip().lower()
            if normalized_action not in actions.values():
                raise VersioningError(
                    f"Action {normalized_action!r} is not registered for "
                    f"{logical_endpoint!r}."
                )

        if methods is None:
            registry.register_endpoint_lifecycle(
                logical_endpoint,
                version,
                action=normalized_action,
                deprecated_at=deprecated_at,
                sunset=sunset,
            )
            return

        registrations = self._resolve_lifecycle_methods(
            methods,
            actions,
            normalized_action,
            logical_endpoint,
        )
        self._register_lifecycle_methods(
            logical_endpoint,
            version,
            registrations,
            deprecated_at,
            sunset,
        )

    @staticmethod
    def _resolve_lifecycle_methods(
        methods: list[str],
        actions: Mapping,
        normalized_action: str | None,
        logical_endpoint: str,
    ) -> list[tuple[str, str]]:
        if not isinstance(methods, list) or not methods:
            raise VersioningError("methods must be a non-empty list of HTTP methods.")
        normalized_methods = [
            method.strip().upper() if isinstance(method, str) else method
            for method in methods
        ]
        if any(
            not isinstance(method, str) or not method for method in normalized_methods
        ):
            raise VersioningError("methods must contain non-empty HTTP method strings.")
        if len(set(normalized_methods)) != len(normalized_methods):
            raise VersioningError("methods must not contain duplicates.")

        registrations = []
        for method in normalized_methods:
            mapped_action = actions.get(method.lower())
            if mapped_action is None and method == "HEAD":
                mapped_action = actions.get("get")
            if not isinstance(mapped_action, str) or not mapped_action:
                raise VersioningError(
                    f"HTTP method {method!r} is not registered for "
                    f"{logical_endpoint!r}."
                )
            if normalized_action is not None and mapped_action != normalized_action:
                raise VersioningError(
                    f"HTTP method {method!r} maps to action {mapped_action!r}, "
                    f"not {normalized_action!r}."
                )
            registrations.append((method, mapped_action))
        return registrations

    @staticmethod
    def _register_lifecycle_methods(
        logical_endpoint: str,
        version: int,
        registrations: list[tuple[str, str]],
        deprecated_at: str | None,
        sunset: str | None,
    ) -> None:
        # Conflicting existing declarations can fail during insertion. Restore
        # the prior registry state so multi-method declarations are atomic.
        previous_lifecycle = dict(registry._endpoint_lifecycle)
        try:
            for method, mapped_action in registrations:
                registry.register_endpoint_lifecycle(
                    logical_endpoint,
                    version,
                    method=method,
                    action=mapped_action,
                    deprecated_at=deprecated_at,
                    sunset=sunset,
                )
        except Exception:
            registry._endpoint_lifecycle.clear()
            registry._endpoint_lifecycle.update(previous_lifecycle)
            raise

    @staticmethod
    def _validate_version(version: int) -> None:
        if isinstance(version, bool) or not isinstance(version, int):
            raise VersionTypeError("Version must be an integer.")
        if version > api_settings.API_MAX_VERSION:
            raise InvalidVersionError(
                f"Version {version} is above the maximum allowed version "
                f"{api_settings.API_MAX_VERSION}."
            )

    def _register_version(
        self,
        prefix: str,
        viewset: type,
        basename: str | None,
        source_version: int | None,
        route_version: int | None,
    ) -> None:
        # Import lazily: DRF's SimpleRouter imports APIView, which resolves
        # DEFAULT_VERSIONING_CLASS. Importing it at module load time would
        # recurse while DRF is trying to import VersionedRouterVersioning.
        from rest_framework.routers import SimpleRouter

        route_prefix = prefix
        if route_version is not None:
            route_prefix = (
                f"{api_settings.API_BASE_PATH.format(version=route_version)}{prefix}"
            )

        router = SimpleRouter(
            trailing_slash=self.trailing_slash,
            use_regex_path=self.use_regex_path,
        )
        router.register(route_prefix, viewset, basename=basename)
        registered_basename = router.registry[-1][2]

        previous_basename = self._basenames.get(prefix)
        if previous_basename is not None and previous_basename != registered_basename:
            raise VersioningError(
                f"ViewSets registered for prefix {prefix!r} must use the same "
                f"basename across versions; got {previous_basename!r} and "
                f"{registered_basename!r}. Pass an explicit basename."
            )
        previous_prefix = self._basename_prefixes.get(registered_basename)
        if previous_prefix is not None and previous_prefix != prefix:
            raise VersioningError(
                f"Basename {registered_basename!r} is already registered for "
                f"prefix {previous_prefix!r}; use a unique basename for "
                f"prefix {prefix!r}."
            )
        self._basenames[prefix] = registered_basename
        self._basename_prefixes[registered_basename] = prefix

        for pattern in router.urls:
            logical_endpoint = f"{prefix}:{pattern.name}"
            route_key = str(pattern.pattern)
            setattr(pattern, registry._ROUTER_OWNER_ATTR, self._registry_owner)
            registry.register_urlpattern(
                pattern,
                source_version=source_version,
                route_version=route_version,
                logical_endpoint=logical_endpoint,
            )
            self._route_keys.add(route_key)

    @property
    def urls(self) -> list[URLPattern | URLResolver]:
        """Return URL patterns grouped into per-version namespaces.

        The URL path itself includes API_BASE_PATH. The namespace is used by
        DRF's version-aware reverse implementation, including nested includes.
        """
        versioned: dict[int, list[URLPattern]] = defaultdict(list)
        unversioned: list[URLPattern] = []

        for pattern in registry.urlpatterns:
            if str(pattern.pattern) not in self._route_keys:
                continue

            route_version = getattr(pattern, _ROUTE_VERSION_ATTR, None)
            if route_version is None:
                unversioned.append(pattern)
            else:
                versioned[route_version].append(pattern)

        urlpatterns: list[URLPattern | URLResolver] = list(unversioned)
        for route_version in sorted(versioned):
            urlpatterns.append(
                path(
                    "",
                    include(
                        (versioned[route_version], self.app_name),
                        namespace=f"v{route_version}",
                    ),
                )
            )
        return urlpatterns


class VersionedRouterVersioning(NamespaceVersioning):
    """Expose the router-selected version through DRF's request.version.

    The router namespaces each concrete version as vN. This adapter reads
    that namespace and uses the full resolver namespace for reverse(), so
    nested application namespaces and DRF hyperlink fields remain versioned.
    """

    invalid_version_message = (
        "The URL namespace does not identify an allowed API version."
    )

    def determine_version(self, request: Any, *args: Any, **kwargs: Any) -> str | None:
        resolver_match = getattr(request, "resolver_match", None)
        route = getattr(resolver_match, "route", None)
        namespace = getattr(resolver_match, "namespace", "") or ""
        namespace_version = None

        for component in reversed(namespace.split(":")):
            if component.startswith("v") and component[1:].isdigit():
                namespace_version = component[1:]
                break

        if isinstance(route, str):
            route_version = registry.get_resolved_route_version(route)
            namespace_matches_route = False
            if namespace_version is not None:
                configured_prefix = api_settings.API_BASE_PATH.format(
                    version=namespace_version
                ).strip("/")
                route_path = route.strip("^$").strip("/")
                namespace_matches_route = (
                    f"/{configured_prefix}/" in f"/{route_path}/"
                )

            # Namespaces are application-controlled, so a parent namespace
            # named "v9" must not version an unversioned child route. Accept
            # a namespace version only when its configured API path segment is
            # also present in the resolved route. This preserves regex-backed
            # DRF routes whose ResolverMatch text cannot be matched directly
            # against the registry's regex pattern.
            if namespace_matches_route:
                version = namespace_version
            elif route_version is not None:
                version = str(route_version)
            else:
                version = None

            if version is not None:
                if not self.is_allowed_version(version):
                    raise NotFound(self.invalid_version_message)
                return version
        else:
            # Preserve compatibility for direct adapter use with lightweight
            # resolver-match objects that expose only a namespace.
            if namespace_version is not None:
                if not self.is_allowed_version(namespace_version):
                    raise NotFound(self.invalid_version_message)
                return namespace_version

        default_version = self.default_version
        if default_version is not None:
            default_version = str(default_version)
        if not self.is_allowed_version(default_version):
            raise NotFound(self.invalid_version_message)
        return default_version

    def is_allowed_version(self, version: str | None) -> bool:
        if not self.allowed_versions:
            return True
        allowed = {str(value) for value in self.allowed_versions}
        default = (
            str(self.default_version) if self.default_version is not None else None
        )
        return (version is not None and version == default) or version in allowed

    def get_versioned_viewname(self, viewname: str, request: Any) -> str:
        """Return the URL name qualified by the full active namespace.

        DRF's hyperlinked fields call this method when validating incoming
        hyperlinks, so it must match the same namespace used by reverse().
        """
        resolver_match = getattr(request, "resolver_match", None)
        namespace = getattr(resolver_match, "namespace", "") or ""
        return f"{namespace}:{viewname}" if namespace else viewname

    def reverse(
        self,
        viewname: str,
        args: Any = None,
        kwargs: Any = None,
        request: Any = None,
        format: str | None = None,
        **extra: Any,
    ) -> str:
        # NamespaceVersioning.reverse() calls our get_versioned_viewname().
        # Do not pre-qualify the name here or the namespace would be applied twice.
        return super().reverse(
            viewname,
            args=args,
            kwargs=kwargs,
            request=request,
            format=format,
            **extra,
        )
