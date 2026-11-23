"""Focused regression contracts for registry removal boundaries and types."""

import pytest

from django_api_versioning.exceptions import VersionTypeError
from django_api_versioning.registry import UrlRegistry


@pytest.fixture
def isolated_registry():
    return UrlRegistry()


def test_remove_accepts_a_valid_integer_version(isolated_registry):
    isolated_registry.remove("orders", 2)

    assert isolated_registry._removal_boundaries == {"orders": {2}}


def test_remove_rejects_boolean_versions_even_though_bool_is_an_int_subclass(
    isolated_registry,
):
    with pytest.raises(VersionTypeError, match="Removal version must be an integer"):
        isolated_registry.remove("orders", True)

    assert isolated_registry._removal_boundaries == {}


def test_remove_accepts_the_configured_maximum_version(isolated_registry, monkeypatch):
    from django_api_versioning.settings import api_settings

    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 1)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)

    isolated_registry.remove("orders", 5)

    assert isolated_registry._removal_boundaries == {"orders": {5}}


def test_removal_boundary_returns_none_without_a_concrete_route_version(
    isolated_registry,
):
    isolated_registry.remove("orders", 2)

    assert isolated_registry._removal_boundary("orders", None) is None


def test_unowned_removal_boundary_uses_the_unowned_boundary_collection(
    isolated_registry,
):
    isolated_registry.remove("orders", 2)

    assert isolated_registry._removal_boundary("orders", 3, owner=None) == 2


def _registered_route(target, *, source_version=1, route_version=2, endpoint="orders"):
    from django.urls import path

    def callback(request):
        return None

    callback.actions = {"get": "list"}
    pattern = path("api/v2/orders/", callback, name="order-list")
    setattr(pattern, target._SOURCE_VERSION_ATTR, source_version)
    setattr(pattern, target._ROUTE_VERSION_ATTR, route_version)
    setattr(pattern, target._LOGICAL_ENDPOINT_ATTR, endpoint)
    return pattern


def test_suppressed_register_removes_an_existing_suppressed_pattern():
    target = UrlRegistry()

    def callback(request):
        return None

    target.register(
        "api/v2/orders/",
        callback,
        source_version=1,
        route_version=2,
        logical_endpoint="orders",
    )
    target._removal_boundaries.setdefault("orders", set()).add(2)
    target.register(
        "api/v2/orders/",
        callback,
        source_version=2,
        route_version=2,
        logical_endpoint="orders",
    )

    assert target.urlpatterns == []
    assert ("orders", 2) in target._removed_patterns


def test_suppressed_register_urlpattern_removes_existing_suppressed_pattern():
    target = UrlRegistry()
    target.register_urlpattern(
        _registered_route(target),
        source_version=1,
        route_version=2,
        logical_endpoint="orders",
    )
    target._removal_boundaries.setdefault("orders", set()).add(2)

    target.register_urlpattern(
        _registered_route(target, source_version=2),
        source_version=2,
        route_version=2,
        logical_endpoint="orders",
    )

    assert target.urlpatterns == []
    assert ("orders", 2) in target._removed_patterns


def test_register_urlpattern_preserves_invalid_unowned_tombstone_key():
    from django.urls import path

    target = UrlRegistry()
    tombstone = path("api/v2/legacy/", lambda request: None)
    target._removed_patterns[(None, 2)] = tombstone

    target.register_urlpattern(
        path("api/v2/orders/", lambda request: None),
        source_version=1,
        route_version=2,
        logical_endpoint=None,
    )

    assert target._removed_patterns[(None, 2)] is tombstone


def test_router_owned_registration_does_not_clear_unowned_tombstone():
    target = UrlRegistry()
    tombstone = _registered_route(target, endpoint="legacy")
    target._removed_patterns[("orders", 2)] = tombstone
    owner_tombstone = _registered_route(target, endpoint="orders")
    owner_key = ("orders", 2, "orders", True)
    target._removed_patterns[owner_key] = owner_tombstone
    owner = object()
    pattern = _registered_route(target, source_version=3)
    setattr(pattern, target._ROUTER_OWNER_ATTR, owner)
    setattr(pattern, target._ROUTER_PREFIX_ATTR, "orders")
    setattr(pattern, target._ROUTER_TRAILING_SLASH_ATTR, True)

    target.register_urlpattern(
        pattern, source_version=3, route_version=2, logical_endpoint="orders"
    )

    assert target._removed_patterns[("orders", 2)] is tombstone
    assert owner_key not in target._removed_patterns


@pytest.mark.parametrize("invalid_candidate", ["name", "endpoint", "version", "namespace"])
def test_resolve_operation_skips_invalid_candidate_and_finds_later_valid_route(
    invalid_candidate,
):
    from types import SimpleNamespace
    from django.urls import path

    target = UrlRegistry()

    def callback(request):
        return None

    callback.actions = {"get": "list"}
    invalid = path(
        "api/v2/orders/",
        callback,
        name="wrong-name" if invalid_candidate == "name" else "order-list",
    )
    valid = path("api/v2/orders/", callback, name="order-list")
    setattr(
        invalid,
        target._LOGICAL_ENDPOINT_ATTR,
        123 if invalid_candidate == "endpoint" else "orders",
    )
    invalid_version = (
        True if invalid_candidate == "version"
        else 3 if invalid_candidate == "namespace"
        else 2
    )
    setattr(invalid, target._ROUTE_VERSION_ATTR, invalid_version)
    setattr(valid, target._LOGICAL_ENDPOINT_ATTR, "orders")
    setattr(valid, target._ROUTE_VERSION_ATTR, 2)
    target.urlpatterns[:] = [invalid, valid]
    match = SimpleNamespace(
        route="api/v2/orders/",
        func=callback,
        url_name="order-list" if invalid_candidate == "name" else None,
        namespaces=("v2",),
        tried=None,
    )

    operation = target.resolve_operation(match, "GET")

    assert operation is not None
    assert operation.logical_endpoint == "orders"
    assert operation.route_version == 2



def test_route_specificity_stops_at_escaped_regex_operator():
    from django.urls import re_path

    pattern = re_path(r"^api/\d{2}/orders/$", lambda request: None)

    assert UrlRegistry._route_specificity_key(pattern)[0] == -len("api/")


def test_route_specificity_keeps_x_as_literal_path_text():
    from django.urls import re_path

    pattern = re_path(r"^api/Xorders/$", lambda request: None)

    assert UrlRegistry._route_specificity_key(pattern) == (
        -len("api/Xorders/"),
        False,
        -len(r"^api/Xorders/$"),
    )


def test_resolve_registered_operation_rejects_non_string_endpoint_and_boolean_version():
    from django.urls import path

    target = UrlRegistry()

    def callback(request):
        return None

    callback.actions = {"get": "list"}
    invalid_endpoint = path("api/v2/orders/", callback, name="order-list")
    setattr(invalid_endpoint, target._LOGICAL_ENDPOINT_ATTR, 123)
    setattr(invalid_endpoint, target._ROUTE_VERSION_ATTR, 2)
    target.urlpatterns[:] = [invalid_endpoint]
    assert target.resolve_registered_operation(123, 2, "GET") is None

    invalid_version = path("api/v2/orders/", callback, name="order-list")
    setattr(invalid_version, target._LOGICAL_ENDPOINT_ATTR, "orders")
    setattr(invalid_version, target._ROUTE_VERSION_ATTR, True)
    target.urlpatterns[:] = [invalid_version]
    assert target.resolve_registered_operation("orders", True, "GET") is None
