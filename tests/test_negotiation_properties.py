"""Property-based and stateful tests for version negotiation and registry invariants."""

import pytest
from django.test import RequestFactory
from hypothesis import given, settings as hypothesis_settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from django_api_versioning.negotiation import (
    _UnsupportedVersion,
    _header_version,
    _parse_version,
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
    """Generate registration/removal sequences and assert registry invariants."""

    def __init__(self):
        super().__init__()
        self.registry = UrlRegistry()
        self._original_max_version = api_settings.API_MAX_VERSION
        api_settings.API_MAX_VERSION = 3

    def teardown(self):
        api_settings.API_MAX_VERSION = self._original_max_version

    @rule(
        endpoint_id=st.integers(min_value=0, max_value=8),
        source_version=st.integers(min_value=1, max_value=3),
    )
    def register_inherited_endpoint(self, endpoint_id, source_version):
        logical = f"stateful-{endpoint_id}"

        def callback(request, value=(endpoint_id, source_version)):
            return value

        for route_version in range(source_version, 4):
            self.registry.register(
                f"api/v{route_version}/stateful/{endpoint_id}/",
                callback,
                source_version=source_version,
                route_version=route_version,
                logical_endpoint=logical,
            )

    @rule(
        endpoint_id=st.integers(min_value=0, max_value=8),
        from_version=st.integers(min_value=1, max_value=3),
    )
    def remove_endpoint_from_version(self, endpoint_id, from_version):
        self.registry.remove(f"stateful-{endpoint_id}", from_version)

    @invariant()
    def active_route_patterns_are_unique(self):
        routes = [str(pattern.pattern) for pattern in self.registry.urlpatterns]
        assert len(routes) == len(set(routes))

    @invariant()
    def no_active_route_is_suppressed_by_a_removal_boundary(self):
        for pattern in self.registry.urlpatterns:
            logical = getattr(pattern, self.registry._LOGICAL_ENDPOINT_ATTR, None)
            route_version = getattr(pattern, self.registry._ROUTE_VERSION_ATTR, None)
            source_version = getattr(pattern, self.registry._SOURCE_VERSION_ATTR, None)
            boundary = self.registry._removal_boundary(logical, route_version)
            assert boundary is None or (
                source_version is not None and source_version > boundary
            )


TestRegistryLifecycleStateMachine = RegistryLifecycleMachine.TestCase
TestRegistryLifecycleStateMachine.settings = hypothesis_settings(
    max_examples=30,
    stateful_step_count=35,
    deadline=None,
)
