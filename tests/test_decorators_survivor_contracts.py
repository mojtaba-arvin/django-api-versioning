"""Focused behavioral assertions for surviving decorator mutants."""

from contextlib import contextmanager

import pytest

from django_api_versioning import decorators
from django_api_versioning.decorators import (
    ViewT,
    _app_name_prefix,
    _register_endpoint_route,
    _register_endpoint_routes,
    _validate_version,
    endpoint,
    remove_endpoint,
    set_endpoint_lifecycle,
    ver_range,
)
from django_api_versioning.exceptions import (
    InvalidVersionError,
    VersioningError,
    VersionRangeError,
    VersionTypeError,
)
from django_api_versioning.registry import registry
from django_api_versioning.settings import api_settings


def test_view_typevar_name_is_preserved_for_runtime_introspection():
    assert ViewT.__name__ == "ViewT"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        ("", ""),
        ("billing", "billing/"),
        ("billing/invoices", "billing/invoices/"),
    ],
)
def test_app_name_prefix_returns_exact_relative_prefix(value, expected):
    assert _app_name_prefix(value) == expected


@pytest.mark.parametrize("value", [1, [], object()])
def test_app_name_prefix_rejects_non_strings_with_exact_type_error(value):
    with pytest.raises(TypeError) as exc:
        _app_name_prefix(value)
    assert str(exc.value) == "app_name must be a string or None."


@pytest.mark.parametrize("value", [" billing", "billing "])
def test_app_name_prefix_rejects_outer_whitespace_with_exact_error(value):
    with pytest.raises(VersioningError) as exc:
        _app_name_prefix(value)
    assert str(exc.value) == "app_name must not have leading or trailing whitespace."


@pytest.mark.parametrize(
    "value",
    [
        "/billing",
        "billing/",
        "billing//invoices",
        ".",
        "..",
        "billing/./invoices",
        "billing/../invoices",
    ],
)
def test_app_name_prefix_rejects_empty_and_dot_segments(value):
    with pytest.raises(VersioningError) as exc:
        _app_name_prefix(value)
    assert (
        str(exc.value)
        == "app_name must be a relative path without empty, '.' or '..' segments."
    )


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        (True, 2, "ver_range start must be an integer."),
        ("1", 2, "ver_range start must be an integer."),
        (1, True, "ver_range end must be an integer."),
        (1, "2", "ver_range end must be an integer."),
    ],
)
def test_ver_range_rejects_invalid_integer_types_exactly(start, end, message):
    with pytest.raises(VersionTypeError) as exc:
        ver_range(start, end)
    assert str(exc.value) == message


def test_ver_range_rejects_reversed_range_with_exact_error():
    with pytest.raises(VersionRangeError) as exc:
        ver_range(3, 2)
    assert str(exc.value) == "ver_range start (3) must be <= end (2)."


def test_ver_range_accepts_zero_and_includes_both_bounds(monkeypatch):
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)
    assert ver_range(0, 0) == [0]
    assert ver_range(2, 4) == [2, 3, 4]


def test_ver_range_rejects_negative_start_with_exact_error():
    with pytest.raises(VersionRangeError) as exc:
        ver_range(-1, 2)
    assert str(exc.value) == "ver_range start must be a non-negative API version."


def test_ver_range_rejects_end_above_maximum_with_exact_error(monkeypatch):
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)
    with pytest.raises(InvalidVersionError) as exc:
        ver_range(1, 6)
    assert str(exc.value) == "Version 6 is above the maximum allowed version 5."


@pytest.mark.parametrize(
    ("version", "exception", "message"),
    [
        (True, VersionTypeError, "Version must be an integer."),
        ("2", VersionTypeError, "Version must be an integer."),
        (-1, VersionRangeError, "Version must be a non-negative API version."),
        (6, InvalidVersionError, "Version 6 is above the maximum allowed version 5."),
    ],
)
def test_validate_version_enforces_type_range_and_maximum(
    monkeypatch, version, exception, message
):
    with pytest.raises(exception) as exc:
        _validate_version(version, 5)
    assert str(exc.value) == message


def test_register_endpoint_route_builds_versioned_path_and_logical_identity(
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(api_settings, "API_BASE_PATH", "api/v{version}/")
    monkeypatch.setattr(
        registry, "register", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    def view(request):
        return None

    _register_endpoint_route("orders/", "billing/", view, "orders", 3, 2)

    args, kwargs = calls[0]
    assert args == ("api/v3/billing/orders/", view, "orders")
    assert kwargs == {
        "source_version": 2,
        "route_version": 3,
        "logical_endpoint": "billing/orders/",
    }


def test_register_endpoint_routes_skips_segment_below_minimum(monkeypatch):
    calls = []
    monkeypatch.setattr(decorators.settings, "API_MIN_VERSION", 2)
    monkeypatch.setattr(decorators.settings, "API_MAX_VERSION", 4)
    monkeypatch.setattr(
        decorators, "_register_endpoint_route", lambda *a, **k: calls.append((a, k))
    )

    _register_endpoint_routes("orders", "", lambda request: None, None, 1, None, 2, 4)
    assert calls == []


def test_register_endpoint_routes_registers_inclusive_segment(monkeypatch):
    calls = []
    monkeypatch.setattr(
        decorators, "_register_endpoint_route", lambda *a, **k: calls.append((a, k))
    )
    _register_endpoint_routes("orders", "", lambda request: None, None, 2, None, 1, 4)
    assert [call[0][4] for call in calls] == [2, 3, 4]
    assert [call[1]["source_version"] for call in calls] == [2, 2, 2]


def test_register_endpoint_routes_skips_only_explicit_versions_below_minimum(
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(
        decorators, "_register_endpoint_route", lambda *a, **k: calls.append((a, k))
    )
    _register_endpoint_routes(
        "orders", "", lambda request: None, None, None, [1, 2, 4], 2, 4
    )
    assert [call[0][4] for call in calls] == [2, 4]
    assert [call[1]["source_version"] for call in calls] == [2, 4]


@pytest.mark.parametrize(
    ("postfix", "exception", "message"),
    [
        (None, TypeError, "postfix must be a string."),
        (
            "/orders",
            VersioningError,
            "postfix must be relative and must not start with '/'.",
        ),
    ],
)
def test_endpoint_postfix_validation_has_exact_public_errors(
    postfix, exception, message
):
    with pytest.raises(exception) as exc:
        endpoint(postfix, version=1)
    assert str(exc.value) == message


def test_endpoint_rejects_version_arguments_that_are_mutually_exclusive():
    with pytest.raises(VersionRangeError) as exc:
        endpoint("orders", version=1, versions=[1])
    assert str(exc.value) == "Use either 'version' or 'versions', not both."


def test_endpoint_rejects_non_list_versions_with_exact_error():
    with pytest.raises(VersionTypeError) as exc:
        endpoint("orders", versions=(1, 2))
    assert str(exc.value) == "'versions' must be a list of integers."


@pytest.mark.parametrize(
    ("methods", "message"),
    [
        ([], "methods must be a non-empty list of HTTP methods."),
        ([1], "methods must contain non-empty HTTP method strings."),
        (["get", "GET"], "methods must not contain duplicates."),
    ],
)
def test_lifecycle_method_validation_has_exact_errors(methods, message):
    with pytest.raises(VersioningError) as exc:
        set_endpoint_lifecycle("orders", version=2, methods=methods)
    assert str(exc.value) == message


def test_lifecycle_method_names_are_normalized_before_registration(monkeypatch):
    calls = []
    monkeypatch.setattr(
        registry, "register_endpoint_lifecycle", lambda *a, **k: calls.append((a, k))
    )
    set_endpoint_lifecycle("orders", version=2, methods=[" get ", "post"])
    assert [call[1]["method"] for call in calls] == ["GET", "POST"]


@pytest.mark.parametrize(
    ("postfix", "exception", "message"),
    [
        (None, TypeError, "postfix must be a string."),
        (
            "/orders",
            VersioningError,
            "postfix must be relative and must not start with '/'.",
        ),
    ],
)
def test_remove_endpoint_postfix_validation_has_exact_errors(
    postfix, exception, message
):
    with pytest.raises(exception) as exc:
        remove_endpoint(postfix, from_version=1)
    assert str(exc.value) == message


def test_decorator_transaction_wrappers_enter_and_exit_for_public_operations(
    monkeypatch,
):
    events = []

    @contextmanager
    def transaction():
        events.append("enter")
        try:
            yield
        finally:
            events.append("exit")

    monkeypatch.setattr(registry, "transaction", transaction)
    monkeypatch.setattr(decorators, "_register_endpoint_routes", lambda *a, **k: None)
    monkeypatch.setattr(registry, "register_endpoint_lifecycle", lambda *a, **k: None)
    monkeypatch.setattr(registry, "remove", lambda *a, **k: None)

    def view(request):
        return None

    decorators._register_endpoint_view(view, "tx-view", None, None, None, None)
    set_endpoint_lifecycle("tx-lifecycle", version=1)
    remove_endpoint("tx-remove", from_version=1)

    assert events == ["enter", "exit", "enter", "exit", "enter", "exit"]


def test_remove_endpoint_does_not_remove_unrelated_router_owned_tombstone():
    from rest_framework import viewsets
    from rest_framework.response import Response
    from django_api_versioning.routers import VersionedRouter

    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register("owned-orders", OrdersViewSet, version=1, basename="owned-orders")
    router.remove("owned-orders", "owned-orders-list", from_version=1)

    # A different logical endpoint remains independently removable.
    remove_endpoint("unrelated-orders", from_version=1)
