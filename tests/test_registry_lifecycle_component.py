from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from django_api_versioning.exceptions import (
    InvalidVersionError,
    VersioningError,
)
from django_api_versioning.lifecycle_metadata import EndpointLifecycle
from django_api_versioning.registry.lifecycle import EndpointLifecycleStore


def operation(
    *,
    method="GET",
    action="list",
    logical_endpoint="orders:order-list",
    route_version=2,
    owner=None,
):
    return SimpleNamespace(
        method=method,
        action=action,
        logical_endpoint=logical_endpoint,
        route_version=route_version,
        router_owner=owner,
    )


def test_registry_lifecycle_store_composes_earliest_scope_dates():
    store = EndpointLifecycleStore()
    owner = object()
    store.register(
        "orders:order-list",
        2,
        deprecated_at="2027-01-01T00:00:00Z",
        sunset="2028-01-01T00:00:00Z",
        owner=owner,
    )
    store.register(
        "orders:order-list",
        2,
        action="list",
        deprecated_at="2026-06-01T00:00:00+02:00",
        owner=owner,
    )
    store.register(
        "orders:order-list",
        2,
        method="GET",
        action="list",
        sunset="2027-01-01T00:00:00Z",
        owner=owner,
    )

    assert store.get(operation(owner=owner)) == EndpointLifecycle(
        deprecated_at=datetime(2026, 5, 31, 22, tzinfo=timezone.utc),
        sunset=datetime(2027, 1, 1, tzinfo=timezone.utc),
    )
    assert store.get(operation(method="POST", action="create", owner=owner)) == (
        EndpointLifecycle(
            deprecated_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
            sunset=datetime(2028, 1, 1, tzinfo=timezone.utc),
        )
    )


def test_registry_lifecycle_store_maps_head_to_get_scope():
    store = EndpointLifecycleStore()
    owner = object()
    store.register(
        "orders:order-list",
        2,
        method="GET",
        action="list",
        deprecated_at="2027-01-01T00:00:00Z",
        owner=owner,
    )

    assert store.get(operation(method="HEAD", owner=owner)) == EndpointLifecycle(
        deprecated_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
        sunset=None,
    )


def test_registry_lifecycle_store_registration_is_idempotent_and_conflict_safe():
    store = EndpointLifecycleStore()
    declaration = {
        "deprecated_at": "2027-01-01T00:00:00Z",
    }
    store.register("orders", 2, **declaration)
    store.register("orders", 2, deprecated_at="2027-01-01T00:00:00+00:00")

    with pytest.raises(VersioningError, match="Conflicting endpoint lifecycle"):
        store.register("orders", 2, deprecated_at="2026-01-01T00:00:00Z")


@pytest.mark.parametrize(
    ("logical_endpoint", "version", "kwargs", "error"),
    [
        ("", 2, {"deprecated_at": "2027-01-01T00:00:00Z"}, VersioningError),
        ("orders", True, {"deprecated_at": "2027-01-01T00:00:00Z"}, VersioningError),
        (
            "orders",
            2,
            {"method": " ", "deprecated_at": "2027-01-01T00:00:00Z"},
            VersioningError,
        ),
        (
            "orders",
            2,
            {"action": " ", "deprecated_at": "2027-01-01T00:00:00Z"},
            VersioningError,
        ),
        ("orders", 2, {"deprecated_at": "not-a-date"}, VersioningError),
        (
            "orders",
            2,
            {"deprecated_at": "2028-01-01T00:00:00Z", "sunset": "2027-01-01T00:00:00Z"},
            VersioningError,
        ),
    ],
)
def test_registry_lifecycle_store_rejects_invalid_declarations(
    logical_endpoint, version, kwargs, error
):
    store = EndpointLifecycleStore()
    with pytest.raises(error):
        store.register(logical_endpoint, version, **kwargs)


def test_registry_lifecycle_store_rejects_version_above_configured_maximum():
    store = EndpointLifecycleStore()
    from django_api_versioning.settings import api_settings

    with pytest.raises(InvalidVersionError):
        store.register(
            "orders",
            api_settings.API_MAX_VERSION + 1,
            deprecated_at="2027-01-01T00:00:00Z",
        )


def test_registry_lifecycle_store_invalidation_respects_owner_and_preserved_versions():
    store = EndpointLifecycleStore()
    owner = object()
    other_owner = object()
    for version in (2, 3, 4):
        store.register(
            "orders",
            version,
            deprecated_at=f"202{version}-01-01T00:00:00Z",
            owner=owner,
        )
    store.register(
        "orders",
        3,
        deprecated_at="2029-01-01T00:00:00Z",
        owner=other_owner,
    )

    store.invalidate_for_removal(
        "orders",
        3,
        owner=owner,
        preserved_versions={4},
    )

    assert ("orders", 2, None, None, owner) in store.records
    assert ("orders", 3, None, None, owner) not in store.records
    assert ("orders", 4, None, None, owner) in store.records
    assert ("orders", 3, None, None, other_owner) in store.records


def test_registry_lifecycle_store_snapshot_restore_and_clear_preserve_mapping_identity():
    store = EndpointLifecycleStore()
    records = store.records
    store.register("orders", 2, deprecated_at="2027-01-01T00:00:00Z")
    snapshot = store.snapshot()
    store.register("orders", 3, sunset="2028-01-01T00:00:00Z")

    store.restore(snapshot)
    assert store.records is records
    assert len(records) == 1
    assert ("orders", 3, None, None, None) not in records

    store.clear()
    assert store.records is records
    assert records == {}


def test_registry_module_preserves_historical_exception_and_settings_exports():
    from importlib import import_module

    from django_api_versioning import exceptions
    from django_api_versioning.settings import api_settings

    registry_module = import_module("django_api_versioning.registry")

    assert registry_module.InvalidVersionError is exceptions.InvalidVersionError
    assert registry_module.VersionRangeError is exceptions.VersionRangeError
    assert registry_module.VersionTypeError is exceptions.VersionTypeError
    assert registry_module.VersioningError is exceptions.VersioningError
    assert registry_module.api_settings is api_settings
