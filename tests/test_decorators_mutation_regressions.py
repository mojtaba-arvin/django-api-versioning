"""Mutation-sensitive rollback and validation contracts for decorators."""

from contextlib import contextmanager

import pytest
from django_api_versioning.decorators import (
    _app_name_prefix,
    _register_endpoint_view,
    _registry_transaction,
    set_endpoint_lifecycle,
)
from django_api_versioning.exceptions import VersioningError
from django_api_versioning.registry import registry


def test_registry_transaction_enters_and_exits_even_when_wrapped_function_raises(
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

    @_registry_transaction
    def operation(value):
        events.append(("call", value))
        raise LookupError("sentinel failure")

    with pytest.raises(LookupError, match="sentinel failure"):
        operation(7)

    assert events == ["enter", ("call", 7), "exit"]


@pytest.mark.parametrize(
    ("app_name", "expected"),
    [
        (None, ""),
        ("", ""),
        ("accounts", "accounts/"),
        ("billing/internal", "billing/internal/"),
    ],
)
def test_app_name_prefix_normalizes_only_the_valid_relative_prefix(app_name, expected):
    assert _app_name_prefix(app_name) == expected


@pytest.mark.parametrize(
    "app_name", [" ", " accounts", "accounts ", "/accounts", "accounts/"]
)
def test_app_name_prefix_rejects_whitespace_and_empty_segments(app_name):
    with pytest.raises(VersioningError):
        _app_name_prefix(app_name)


@pytest.mark.parametrize(
    "app_name", [".", "..", "accounts/./users", "accounts/../users"]
)
def test_app_name_prefix_rejects_dot_segments(app_name):
    with pytest.raises(VersioningError):
        _app_name_prefix(app_name)


def test_register_endpoint_view_restores_routes_tombstones_and_view_attribute_on_late_failure(
    monkeypatch,
):
    def existing_view(request):
        return None

    def new_view(request):
        return None

    registry.register(
        "api/v1/previous/",
        existing_view,
        source_version=1,
        route_version=1,
        logical_endpoint="previous",
    )
    registry.remove("previous", from_version=1)

    attribute = registry._LOGICAL_ENDPOINT_ATTR
    setattr(new_view, attribute, "pre-existing-value")
    original_patterns = list(registry.urlpatterns)
    original_removed = dict(registry._removed_patterns)
    original_register = registry.register
    calls = 0

    def fail_after_first_route(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("late route registration failure")
        return original_register(*args, **kwargs)

    monkeypatch.setattr(registry, "register", fail_after_first_route)

    with pytest.raises(RuntimeError, match="late route registration failure"):
        _register_endpoint_view(
            new_view,
            "new-resource/",
            1,
            None,
            None,
            None,
        )

    assert calls == 2
    assert len(registry.urlpatterns) == len(original_patterns)
    assert all(
        actual is expected
        for actual, expected in zip(registry.urlpatterns, original_patterns)
    )
    assert registry._removed_patterns == original_removed
    assert getattr(new_view, attribute) == "pre-existing-value"


def test_register_endpoint_view_removes_attribute_it_introduced_when_registration_fails(
    monkeypatch,
):
    def view(request):
        return None

    attribute = registry._LOGICAL_ENDPOINT_ATTR
    assert attribute not in view.__dict__
    original_register = registry.register

    def fail_registration(*args, **kwargs):
        original_register(*args, **kwargs)
        raise RuntimeError("registration failed")

    monkeypatch.setattr(registry, "register", fail_registration)

    with pytest.raises(RuntimeError, match="registration failed"):
        _register_endpoint_view(view, "new-resource/", None, [1], None, None)

    assert attribute not in view.__dict__
    assert registry.urlpatterns == []


def test_set_endpoint_lifecycle_restores_all_methods_after_late_conflict(monkeypatch):
    original = registry.register_endpoint_lifecycle
    calls = []

    def fail_on_second_method(*args, **kwargs):
        calls.append(kwargs.get("method"))
        if len(calls) == 2:
            raise RuntimeError("second method rejected")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        registry, "register_endpoint_lifecycle", fail_on_second_method
    )
    before = dict(registry._endpoint_lifecycle)

    with pytest.raises(RuntimeError, match="second method rejected"):
        set_endpoint_lifecycle(
            "payments",
            version=2,
            methods=["GET", "POST"],
            deprecated_at="2027-01-01T00:00:00Z",
        )

    assert calls == ["GET", "POST"]
    assert registry._endpoint_lifecycle == before


def test_register_endpoint_view_preserves_class_attribute_when_callback_has_cls(
    monkeypatch,
):
    class ViewClass:
        pass

    def callback(request):
        return None

    callback.cls = ViewClass
    attribute = registry._LOGICAL_ENDPOINT_ATTR
    setattr(ViewClass, attribute, "class-before")
    setattr(callback, attribute, "callback-before")

    original_register = registry.register

    def fail_registration(*args, **kwargs):
        original_register(*args, **kwargs)
        raise RuntimeError("forced failure")

    monkeypatch.setattr(registry, "register", fail_registration)

    with pytest.raises(RuntimeError, match="forced failure"):
        _register_endpoint_view(callback, "class-endpoint/", None, [1], None, None)

    assert getattr(callback, attribute) == "callback-before"
    assert getattr(ViewClass, attribute) == "class-before"
    assert registry.urlpatterns == []
