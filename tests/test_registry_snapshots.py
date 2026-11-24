"""Regression tests for immutable registry snapshots and transaction boundaries."""

import importlib
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from django_api_versioning.registry import UrlRegistry, registry


def _view_factory(marker):
    def view(request):
        return marker

    return view


def test_snapshot_is_deeply_immutable_and_old_generations_remain_stable():
    route_registry = UrlRegistry()
    initial = route_registry.current_snapshot
    first_view = _view_factory("first")

    with route_registry.transaction():
        route_registry.register(
            "api/v1/items/",
            first_view,
            source_version=1,
            route_version=1,
            logical_endpoint="items",
        )
        assert route_registry.current_snapshot is initial
        route_registry.register(
            "api/v2/items/",
            first_view,
            source_version=1,
            route_version=2,
            logical_endpoint="items",
        )

    committed = route_registry.current_snapshot
    assert committed.generation == initial.generation + 1
    assert len(committed.active_routes) == 2
    assert initial.active_routes == ()
    assert committed.active_routes[0].implementation is first_view

    with pytest.raises(TypeError):
        committed.active_by_identity[("path", "other/", 1, "unowned")] = (
            committed.active_routes[0]
        )

    with pytest.raises((AttributeError, TypeError)):
        committed.active_routes[0].route = "mutated/"

    route_registry.remove("items", 2)
    removed = route_registry.current_snapshot
    assert len(removed.active_routes) == 1
    assert len(removed.removed_routes) == 1
    assert len(committed.active_routes) == 2
    assert committed.removed_routes == ()

    route_registry.register(
        "api/v2/items/",
        _view_factory("reintroduced"),
        source_version=3,
        route_version=2,
        logical_endpoint="items",
    )
    reintroduced = route_registry.current_snapshot
    assert len(reintroduced.active_routes) == 2
    assert reintroduced.removed_routes == ()
    assert len(removed.active_routes) == 1
    assert len(removed.removed_routes) == 1

    route_registry.clear()
    assert route_registry.current_snapshot.active_routes == ()
    assert len(reintroduced.active_routes) == 2
    assert len(removed.active_routes) == 1
    assert len(removed.removed_routes) == 1


def test_failed_transaction_restores_state_without_publishing_a_snapshot():
    route_registry = UrlRegistry()
    before = route_registry.current_snapshot

    with pytest.raises(RuntimeError, match="abort transaction"):
        with route_registry.transaction():
            route_registry.register(
                "api/v1/temporary/",
                _view_factory("temporary"),
                source_version=1,
                route_version=1,
                logical_endpoint="temporary",
            )
            raise RuntimeError("abort transaction")

    assert route_registry.urlpatterns == []
    assert route_registry.current_snapshot is before
    assert route_registry.current_snapshot.generation == before.generation


def test_successful_multi_operation_transaction_publishes_once():
    route_registry = UrlRegistry()
    before = route_registry.current_snapshot

    with route_registry.transaction():
        route_registry.register(
            "api/v1/first/",
            _view_factory("first"),
            source_version=1,
            route_version=1,
            logical_endpoint="first",
        )
        route_registry.register(
            "api/v1/second/",
            _view_factory("second"),
            source_version=1,
            route_version=1,
            logical_endpoint="second",
        )
        assert route_registry.current_snapshot is before

    after = route_registry.current_snapshot
    assert after.generation == before.generation + 1
    assert {record.logical_endpoint for record in after.active_routes} == {
        "first",
        "second",
    }


def test_reloading_a_urlconf_replaces_the_declaration_without_duplicates(
    tmp_path, monkeypatch
):
    registry.clear()
    module_name = "snapshot_reload_urlconf"
    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(
        "from django_api_versioning.registry import registry\n"
        "def view(request):\n"
        "    return 'loaded'\n"
        "registry.register(\n"
        "    'api/v1/reloaded/', view, source_version=1,\n"
        "    route_version=1, logical_endpoint='reloaded'\n"
        ")\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop(module_name, None)

    try:
        module = importlib.import_module(module_name)
        first_snapshot = registry.current_snapshot
        first_callback = first_snapshot.active_routes[0].implementation

        importlib.reload(module)

        second_snapshot = registry.current_snapshot
        assert len(registry.urlpatterns) == 1
        assert len(second_snapshot.active_routes) == 1
        assert second_snapshot.generation > first_snapshot.generation
        assert second_snapshot.active_routes[0].implementation is module.view
        assert second_snapshot.active_routes[0].implementation is not first_callback
        assert first_snapshot.active_routes[0].implementation is first_callback
    finally:
        registry.clear()
        sys.modules.pop(module_name, None)


def test_snapshot_includes_removal_boundaries_without_existing_routes():
    route_registry = UrlRegistry()
    before = route_registry.current_snapshot

    route_registry.remove("future-endpoint", 2)

    boundary_snapshot = route_registry.current_snapshot
    assert boundary_snapshot.generation == before.generation + 1
    assert len(boundary_snapshot.removal_boundaries) == 1
    boundary = boundary_snapshot.removal_boundaries[0]
    assert boundary.logical_endpoint == "future-endpoint"
    assert boundary.from_version == 2
    assert boundary.owner == "unowned"
    assert boundary_snapshot.active_routes == ()
    assert boundary_snapshot.removed_routes == ()

    route_registry.register(
        "api/v2/future-endpoint/",
        _view_factory("suppressed"),
        source_version=1,
        route_version=2,
        logical_endpoint="future-endpoint",
    )
    assert route_registry.current_snapshot.removal_boundaries == (boundary,)
    assert route_registry.current_snapshot.active_routes == ()
    assert len(route_registry.current_snapshot.removed_routes) == 1


def test_failed_transaction_restores_metadata_on_existing_urlpattern():
    route_registry = UrlRegistry()
    original_view = _view_factory("original")
    route_registry.register(
        "api/v1/existing/",
        original_view,
        source_version=1,
        route_version=1,
        logical_endpoint="existing",
    )
    before = route_registry.current_snapshot
    original_pattern = route_registry.urlpatterns[0]

    with pytest.raises(RuntimeError, match="rollback existing pattern"):
        with route_registry.transaction():
            route_registry.register_urlpattern(
                original_pattern,
                source_version=2,
                route_version=1,
                logical_endpoint="changed",
            )
            raise RuntimeError("rollback existing pattern")

    assert route_registry.urlpatterns[0] is original_pattern
    assert getattr(original_pattern, route_registry._SOURCE_VERSION_ATTR) == 1
    assert (
        getattr(original_pattern, route_registry._LOGICAL_ENDPOINT_ATTR) == "existing"
    )
    assert route_registry.current_snapshot is before


def test_concurrent_reader_observes_only_the_committed_transaction():
    route_registry = UrlRegistry()
    before = route_registry.current_snapshot
    transaction_open = Event()
    allow_commit = Event()
    reader_started = Event()

    def write_routes():
        with route_registry.transaction():
            route_registry.register(
                "api/v1/first/",
                _view_factory("first"),
                source_version=1,
                route_version=1,
                logical_endpoint="first",
            )
            transaction_open.set()
            if not allow_commit.wait(timeout=5):
                raise TimeoutError("test did not release the writer")
            route_registry.register(
                "api/v1/second/",
                _view_factory("second"),
                source_version=1,
                route_version=1,
                logical_endpoint="second",
            )

    def read_snapshot():
        reader_started.set()
        return route_registry.current_snapshot

    with ThreadPoolExecutor(max_workers=2) as executor:
        writer = executor.submit(write_routes)
        assert transaction_open.wait(timeout=5)
        reader = executor.submit(read_snapshot)
        assert reader_started.wait(timeout=5)
        allow_commit.set()
        writer.result(timeout=5)
        observed = reader.result(timeout=5)

    assert observed.generation == before.generation + 1
    assert {record.logical_endpoint for record in observed.active_routes} == {
        "first",
        "second",
    }
    assert before.active_routes == ()
