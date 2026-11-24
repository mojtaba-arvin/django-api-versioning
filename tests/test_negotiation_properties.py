"""Property-based and stateful tests for version negotiation and registry invariants."""

import pytest
from django.test import RequestFactory
from django.urls import path
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from django_api_versioning.negotiation import (
    _header_version,
    _parse_version,
    _UnsupportedVersion,
)
from django_api_versioning.registry import UrlRegistry
from django_api_versioning.settings import api_settings


@given(version=st.integers(min_value=0, max_value=10**30))
def test_parse_version_round_trips_arbitrary_non_negative_integers(version):
    assert _parse_version(str(version)) == version


@given(
    version=st.integers(min_value=0, max_value=10**9),
    quality=st.sampled_from(
        ["0", "0.0", "0.000", "0.001", "0.1", "0.5", "0.999", "1", "1.0"]
    ),
)
def test_accept_quality_controls_whether_a_version_is_selectable(version, quality):
    request = RequestFactory().get(
        "/",
        HTTP_ACCEPT=f"application/json; version={version}; q={quality}",
    )

    if float(quality) == 0:
        with pytest.raises(_UnsupportedVersion):
            _header_version(request, "Accept-Version")
        return

    assert _header_version(request, "Accept-Version") == version


@given(
    first_version=st.integers(min_value=0, max_value=1000),
    second_version=st.integers(min_value=0, max_value=1000),
    first_quality=st.sampled_from(["0", "0.1", "0.5", "0.8", "1"]),
    second_quality=st.sampled_from(["0", "0.1", "0.5", "0.8", "1"]),
)
def test_accept_prefers_the_highest_quality_version(
    first_version, second_version, first_quality, second_quality
):
    request = RequestFactory().get(
        "/",
        HTTP_ACCEPT=(
            f"application/json; version={first_version}; q={first_quality}, "
            f"text/plain; version={second_version}; q={second_quality}"
        ),
    )
    q1, q2 = float(first_quality), float(second_quality)

    if q1 == 0 and q2 == 0:
        with pytest.raises(_UnsupportedVersion):
            _header_version(request, "Accept-Version")
        return

    if q1 == q2 and first_version != second_version:
        with pytest.raises(ValueError):
            _header_version(request, "Accept-Version")
        return

    expected = first_version if q1 > q2 else second_version
    assert _header_version(request, "Accept-Version") == expected


class RegistryLifecycleMachine(RuleBasedStateMachine):
    """Generate mixed route-state operations and compare with an independent model."""

    def __init__(self):
        super().__init__()
        self.registry = UrlRegistry()
        self._original_max_version = api_settings.API_MAX_VERSION
        api_settings.API_MAX_VERSION = 3
        self._owners = {}
        self._seen_identities = set()
        self._removal_boundaries = {}
        self._expected_active = {}
        self._sequence = 0

    def teardown(self):
        api_settings.API_MAX_VERSION = self._original_max_version

    def _owner(self, router_id):
        if router_id is None:
            return None
        if router_id not in self._owners:
            self._owners[router_id] = object()
        return self._owners[router_id]

    @staticmethod
    def _logical_endpoint(endpoint_id):
        # Deliberately shared between router owners to test owner isolation.
        return f"stateful-{endpoint_id}"

    @staticmethod
    def _router_prefix(router_id, endpoint_id):
        return f"routers/{router_id}/stateful/{endpoint_id}"

    def _boundary_key(self, logical, router_id, prefix, trailing_slash):
        if router_id is None:
            return (logical, None, None, None)
        return (logical, router_id, prefix, trailing_slash)

    def _current_boundary(
        self, logical, route_version, router_id, prefix, trailing_slash
    ):
        key = self._boundary_key(logical, router_id, prefix, trailing_slash)
        applicable = [
            boundary
            for boundary in self._removal_boundaries.get(key, ())
            if boundary <= route_version
        ]
        return max(applicable) if applicable else None

    def _register(
        self,
        endpoint_id,
        source_version,
        route_versions,
        *,
        router_id=None,
        trailing_slash=True,
        explicit_versions=False,
    ):
        logical = self._logical_endpoint(endpoint_id)
        owner = self._owner(router_id)
        prefix = (
            None
            if router_id is None
            else self._router_prefix(router_id, endpoint_id)
        )
        marker = f"registration-{self._sequence}"
        self._sequence += 1

        def callback(request, result=(logical, router_id, source_version, marker)):
            return result

        callback._stateful_marker = marker

        for route_version in sorted(route_versions):
            declaration_source_version = (
                route_version if explicit_versions else source_version
            )
            route_suffix = "/" if trailing_slash else ""
            if router_id is None:
                route = (
                    f"api/v{route_version}/stateful/{endpoint_id}{route_suffix}"
                )
            else:
                route = f"api/v{route_version}/{prefix}{route_suffix}"

            boundary = self._current_boundary(
                logical,
                route_version,
                router_id,
                prefix,
                trailing_slash,
            )
            suppressed = (
                boundary is not None
                and declaration_source_version <= boundary
            )
            key = (
                logical,
                route_version,
                router_id,
                prefix,
                trailing_slash,
            )
            existing = self._expected_active.get(key)
            should_replace = (
                existing is None
                or declaration_source_version >= existing[0]
            )

            if router_id is None:
                self.registry.register(
                    route,
                    callback,
                    source_version=declaration_source_version,
                    route_version=route_version,
                    logical_endpoint=logical,
                )
            else:
                pattern = path(
                    route,
                    callback,
                    name=f"stateful-{router_id}-{endpoint_id}-v{route_version}",
                )
                setattr(pattern, self.registry._ROUTER_OWNER_ATTR, owner)
                setattr(pattern, self.registry._ROUTER_PREFIX_ATTR, prefix)
                setattr(
                    pattern,
                    self.registry._ROUTER_TRAILING_SLASH_ATTR,
                    trailing_slash,
                )
                self.registry.register_urlpattern(
                    pattern,
                    source_version=declaration_source_version,
                    route_version=route_version,
                    logical_endpoint=logical,
                )

            self._seen_identities.add(
                (logical, router_id, prefix, trailing_slash)
            )
            if not suppressed and should_replace:
                self._expected_active[key] = (
                    declaration_source_version,
                    marker,
                )

    def _remove(self, endpoint_id, from_version, *, router_id=None):
        logical = self._logical_endpoint(endpoint_id)
        owner = self._owner(router_id)

        if router_id is None:
            identities = {(None, None)}
        else:
            identities = {
                (prefix, trailing_slash)
                for seen_logical, seen_owner, prefix, trailing_slash
                in self._seen_identities
                if seen_logical == logical and seen_owner == router_id
            }
            if not identities:
                return

        for prefix, trailing_slash in identities:
            key = self._boundary_key(
                logical, router_id, prefix, trailing_slash
            )
            self._removal_boundaries.setdefault(key, []).append(from_version)

        self.registry.remove(logical, from_version, owner=owner)

        for key, (source_version, _) in list(self._expected_active.items()):
            (
                registered_logical,
                route_version,
                registered_owner,
                _,
                _,
            ) = key
            if (
                registered_logical == logical
                and registered_owner == router_id
                and route_version >= from_version
                and source_version <= from_version
            ):
                del self._expected_active[key]

    @rule(
        endpoint_id=st.integers(min_value=0, max_value=8),
        source_version=st.integers(min_value=1, max_value=3),
        trailing_slash=st.booleans(),
    )
    def register_inherited_endpoint(
        self, endpoint_id, source_version, trailing_slash
    ):
        self._register(
            endpoint_id,
            source_version,
            range(source_version, 4),
            trailing_slash=trailing_slash,
        )

    @rule(
        endpoint_id=st.integers(min_value=0, max_value=8),
        source_version=st.integers(min_value=1, max_value=3),
        route_versions=st.lists(
            st.integers(min_value=1, max_value=3),
            min_size=1,
            max_size=3,
            unique=True,
        ),
        trailing_slash=st.booleans(),
    )
    def register_explicit_versions(
        self, endpoint_id, source_version, route_versions, trailing_slash
    ):
        self._register(
            endpoint_id,
            source_version,
            route_versions,
            trailing_slash=trailing_slash,
            explicit_versions=True,
        )

    @rule(
        router_id=st.integers(min_value=0, max_value=3),
        endpoint_id=st.integers(min_value=0, max_value=8),
        source_version=st.integers(min_value=1, max_value=3),
        explicit=st.booleans(),
        route_versions=st.lists(
            st.integers(min_value=1, max_value=3),
            min_size=1,
            max_size=3,
            unique=True,
        ),
        trailing_slash=st.booleans(),
    )
    def register_router_endpoint(
        self,
        router_id,
        endpoint_id,
        source_version,
        explicit,
        route_versions,
        trailing_slash,
    ):
        versions = route_versions if explicit else range(source_version, 4)
        self._register(
            endpoint_id,
            source_version,
            versions,
            router_id=router_id,
            trailing_slash=trailing_slash,
            explicit_versions=explicit,
        )

    @rule(
        endpoint_id=st.integers(min_value=0, max_value=8),
        from_version=st.integers(min_value=1, max_value=3),
    )
    def remove_endpoint_from_version(self, endpoint_id, from_version):
        self._remove(endpoint_id, from_version)

    @rule(
        router_id=st.integers(min_value=0, max_value=3),
        endpoint_id=st.integers(min_value=0, max_value=8),
        from_version=st.integers(min_value=1, max_value=3),
    )
    def remove_router_endpoint(self, router_id, endpoint_id, from_version):
        self._remove(endpoint_id, from_version, router_id=router_id)

    @invariant()
    def active_route_patterns_are_unique(self):
        routes = [str(pattern.pattern) for pattern in self.registry.urlpatterns]
        assert len(routes) == len(set(routes))

    @invariant()
    def actual_registry_matches_the_independent_expected_model(self):
        actual = {}
        for pattern in self.registry.urlpatterns:
            logical = getattr(pattern, self.registry._LOGICAL_ENDPOINT_ATTR, None)
            route_version = getattr(pattern, self.registry._ROUTE_VERSION_ATTR, None)
            owner = getattr(pattern, self.registry._ROUTER_OWNER_ATTR, None)
            owner_id = next(
                (
                    router_id
                    for router_id, expected_owner in self._owners.items()
                    if owner is expected_owner
                ),
                None,
            )
            prefix = getattr(pattern, self.registry._ROUTER_PREFIX_ATTR, None)
            trailing_slash = (
                getattr(pattern, self.registry._ROUTER_TRAILING_SLASH_ATTR, None)
                if owner is not None
                else str(pattern.pattern).endswith("/")
            )
            key = (
                logical,
                route_version,
                owner_id,
                prefix,
                trailing_slash,
            )
            actual[key] = (
                getattr(pattern, self.registry._SOURCE_VERSION_ATTR, None),
                getattr(pattern.callback, "_stateful_marker", None),
            )

        assert actual == self._expected_active

    @invariant()
    def active_routes_are_not_suppressed_by_the_model(self):
        for key, (source_version, _) in self._expected_active.items():
            logical, route_version, router_id, prefix, trailing_slash = key
            boundary = self._current_boundary(
                logical,
                route_version,
                router_id,
                prefix,
                trailing_slash,
            )
            assert boundary is None or source_version > boundary


TestRegistryLifecycleStateMachine = RegistryLifecycleMachine.TestCase
TestRegistryLifecycleStateMachine.settings = hypothesis_settings(
    max_examples=30,
    stateful_step_count=35,
    deadline=None,
)
