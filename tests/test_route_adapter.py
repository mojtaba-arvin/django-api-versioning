"""Contracts for the narrow optional router capability seam."""

import inspect

import pytest

from django_api_versioning.registry.router import (
    DRFRouteCapabilities,
    RouteCapabilities,
    resolve_drf_operation_action,
    route_capabilities,
)


def test_action_resolution_handles_head_options_and_unmapped_methods():
    callback = type(
        "Callback",
        (),
        {"actions": {"get": "list", "post": "create"}},
    )()

    assert resolve_drf_operation_action(callback, "GET") == (True, "list")
    assert resolve_drf_operation_action(callback, "HEAD") == (True, "list")
    assert resolve_drf_operation_action(callback, "OPTIONS") == (True, None)
    assert resolve_drf_operation_action(callback, "PATCH") == (False, None)
    assert resolve_drf_operation_action(callback, "PATCH", True) == (True, None)


def test_action_resolution_ignores_callbacks_without_an_action_map():
    def callback(request):
        return None

    assert resolve_drf_operation_action(callback, "GET") == (True, None)


def test_generic_django_cbv_is_left_to_the_core_registry():
    class GenericView:
        @classmethod
        def as_view(cls):
            def callback(request):
                return None

            return callback

    assert route_capabilities.create_view_callback(GenericView) is None


def test_viewset_adapter_preserves_actionable_registration_error():
    class RequiredActionsViewSet:
        @classmethod
        def as_view(cls, actions):
            def callback(request):
                return None

            return callback

    with pytest.raises(TypeError) as exc:
        route_capabilities.create_view_callback(RequiredActionsViewSet)

    assert str(exc.value) == (
        "ViewSet 'RequiredActionsViewSet' cannot be registered directly. "
        "Pass a configured callable like: "
        "RequiredActionsViewSet.as_view({'get': 'list', 'post': 'create'})"
    )


def test_viewset_adapter_accepts_an_explicit_optional_action_map():
    def callback(request):
        return None

    class OptionalActionsViewSet:
        @classmethod
        def as_view(cls, actions=None):
            return callback

    assert route_capabilities.create_view_callback(OptionalActionsViewSet) is callback


def test_route_capability_defaults_fail_closed_for_unmapped_methods():
    protocol_default = inspect.signature(
        RouteCapabilities.resolve_operation_action
    ).parameters["allow_unmapped_method"].default
    adapter_default = inspect.signature(
        DRFRouteCapabilities.resolve_operation_action
    ).parameters["allow_unmapped_method"].default

    callback = type("Callback", (), {"actions": {"get": "list"}})()

    assert protocol_default is False
    assert adapter_default is False
    assert route_capabilities.resolve_operation_action(callback, "PATCH") == (
        False,
        None,
    )
    assert route_capabilities.resolve_operation_action(callback, "OPTIONS") == (
        True,
        None,
    )
