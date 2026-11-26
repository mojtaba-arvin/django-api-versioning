"""Contracts for the narrow optional router capability seam."""

from django_api_versioning.registry.router import (
    resolve_drf_operation_action,
    route_capabilities,
)


def test_action_resolution_handles_head_options_and_unmapped_methods():
    callback = type("Callback", (), {"actions": {"get": "list", "post": "create"}})()

    assert resolve_drf_operation_action(callback, "GET") == (True, "list")
    assert resolve_drf_operation_action(callback, "HEAD") == (True, "list")
    assert resolve_drf_operation_action(callback, "OPTIONS") == (True, None)
    assert resolve_drf_operation_action(callback, "PATCH") == (False, None)
    assert resolve_drf_operation_action(callback, "PATCH", True) == (True, None)


def test_action_resolution_ignores_callbacks_without_an_action_map():
    assert resolve_drf_operation_action(lambda request: None, "GET") == (True, None)


def test_generic_django_cbv_is_left_to_the_core_registry():
    class GenericView:
        @classmethod
        def as_view(cls):
            return lambda request: None

    assert route_capabilities.create_view_callback(GenericView) is None


def test_viewset_adapter_preserves_actionable_registration_error():
    class RequiredActionsViewSet:
        @classmethod
        def as_view(cls, actions):
            return lambda request: None

    try:
        route_capabilities.create_view_callback(RequiredActionsViewSet)
    except TypeError as exc:
        assert str(exc) == (
            "ViewSet 'RequiredActionsViewSet' cannot be registered directly. "
            "Pass a configured callable like: "
            "RequiredActionsViewSet.as_view({'get': 'list', 'post': 'create'})"
        )
    else:
        raise AssertionError("a ViewSet without an action map must be rejected")


def test_viewset_adapter_accepts_an_explicit_optional_action_map():
    callback = lambda request: None

    class OptionalActionsViewSet:
        @classmethod
        def as_view(cls, actions=None):
            return callback

    assert route_capabilities.create_view_callback(OptionalActionsViewSet) is callback
