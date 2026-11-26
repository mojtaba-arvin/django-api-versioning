"""Contracts for deterministic immutable route-matrix projections."""

from types import MappingProxyType
from typing import Callable

from django_api_versioning.registry import REMOVED_ROUTE, UrlRegistry
from django_api_versioning.registry.matrix import (
    REMOVED_ROUTE as MATRIX_REMOVED_ROUTE,
    VersionMatrix,
    _ROUTER_OWNER_IDENTITY,
    project_logical_version_matrix,
    project_version_matrix,
)
from django_api_versioning.route_state import RegistrySnapshot, RouteRecord


def _record(
    route,
    version,
    callback,
    *,
    logical_endpoint="orders",
    owner="unowned",
    prefix=None,
    trailing_slash=None,
    sequence=0,
):
    return RouteRecord(
        identity=("path", route, version, owner),
        logical_endpoint=logical_endpoint,
        route=route,
        is_regex=False,
        source_version=version,
        route_version=version,
        implementation=callback,
        owner=owner,
        source_location=None,
        router_prefix=prefix,
        trailing_slash=trailing_slash,
        sequence=sequence,
    )


def _snapshot(active=(), removed=()):
    active = tuple(active)
    removed = tuple(removed)
    return RegistrySnapshot(
        generation=7,
        active_routes=active,
        removed_routes=removed,
        lifecycle=(),
        removal_boundaries=(),
        active_by_identity=MappingProxyType(
            {record.identity: record for record in active}
        ),
        removed_by_identity=MappingProxyType(
            {record.identity: record for record in removed}
        ),
    )


def test_registry_matrix_physical_projection_keeps_active_routes_and_tombstones():
    active = object()
    removed = object()
    snapshot = _snapshot(
        active=(
            _record("api/v1/orders/", 1, active),
            _record("api/v2/orders/", 2, active),
        ),
        removed=(
            _record("api/v2/orders/", 2, removed),
            _record("api/v3/orders/", 3, removed),
        ),
    )

    matrix = project_version_matrix(snapshot)

    assert matrix == {
        "api/v1/orders/": {1: active},
        "api/v2/orders/": {2: active},
        "api/v3/orders/": {3: REMOVED_ROUTE},
    }


def test_registry_matrix_logical_projection_preserves_legacy_unambiguous_key():
    callback = object()
    snapshot = _snapshot(
        active=(
            _record("api/v1/orders/", 1, callback),
            _record("api/v2/orders/", 2, callback),
        )
    )

    assert project_logical_version_matrix(snapshot) == {
        "orders": {1: callback, 2: callback}
    }


def test_registry_matrix_logical_projection_discriminates_colliding_owners_and_routes():
    unowned_v1 = object()
    unowned_v2 = object()
    router_v1 = object()
    snapshot = _snapshot(
        active=(
            _record("api/v1/orders/", 1, unowned_v1),
            _record("api/v2/orders/", 2, unowned_v2),
            _record(
                "api/v1/orders/",
                1,
                router_v1,
                owner="router:'orders':trailing_slash=True",
                prefix="orders",
                trailing_slash=True,
            ),
        )
    )

    matrix = project_logical_version_matrix(snapshot)

    assert matrix == {
        "orders [route='api/v1/orders/']": {1: unowned_v1},
        "orders [route='api/v2/orders/']": {2: unowned_v2},
        "orders [router='orders', trailing_slash=True]": {1: router_v1},
    }


def test_registry_matrix_logical_projection_keeps_removed_tombstones():
    snapshot = _snapshot(removed=(_record("api/v3/orders/", 3, None),))

    assert project_logical_version_matrix(snapshot) == {"orders": {3: REMOVED_ROUTE}}


def test_registry_matrix_logical_projection_uses_physical_route_when_identity_is_missing():
    callback = object()
    snapshot = _snapshot(
        active=(_record("legacy/", None, callback, logical_endpoint=None),)
    )

    assert project_logical_version_matrix(snapshot) == {"legacy/": {None: callback}}


def test_registry_matrix_projections_are_deterministic_and_do_not_mutate_snapshot():
    callback = object()
    record = _record("api/v1/orders/", 1, callback)
    snapshot = _snapshot(active=(record,))
    before_active = snapshot.active_routes
    before_removed = snapshot.removed_routes

    first_physical = project_version_matrix(snapshot)
    second_physical = project_version_matrix(snapshot)
    first_logical = project_logical_version_matrix(snapshot)
    second_logical = project_logical_version_matrix(snapshot)

    assert first_physical == second_physical
    assert first_logical == second_logical
    assert snapshot.active_routes is before_active
    assert snapshot.removed_routes is before_removed
    assert snapshot.generation == 7


def test_registry_matrix_facades_read_the_published_snapshot():
    target = UrlRegistry()

    def callback(request):
        return None

    target.register(
        "api/v1/orders/",
        callback,
        source_version=1,
        route_version=1,
        logical_endpoint="orders",
    )

    assert target.get_version_matrix() == {"api/v1/orders/": {1: callback}}
    assert target.get_logical_version_matrix() == {"orders": {1: callback}}


def test_registry_matrix_identity_sentinels_and_typing_alias_are_stable():
    assert VersionMatrix == dict[str, dict[int | None, Callable]]

    sentinels = (MATRIX_REMOVED_ROUTE, _ROUTER_OWNER_IDENTITY)
    assert all(type(sentinel) is object for sentinel in sentinels)
    assert len({id(sentinel) for sentinel in sentinels}) == len(sentinels)


def test_registry_matrix_disambiguates_unowned_and_router_across_versions():
    unowned = object()
    router = object()
    snapshot = _snapshot(
        active=(
            _record("legacy/v1/", 1, unowned, logical_endpoint="legacy"),
            _record(
                "legacy/v2/",
                2,
                router,
                logical_endpoint="legacy",
                owner="router:route='legacy/v2/'",
            ),
        )
    )

    assert project_logical_version_matrix(snapshot) == {
        "legacy [route='legacy/v1/']": {1: unowned},
        "legacy [router=None, trailing_slash=None]": {2: router},
    }
