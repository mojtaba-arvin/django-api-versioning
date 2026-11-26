"""Narrow capability seam for optional router integrations.

The core registry consumes only action resolution and view callback creation.
This adapter has no Django REST Framework imports, so importing the registry
or a Django-only URLconf never loads the optional dependency.
"""

import inspect
from collections.abc import Mapping
from inspect import Parameter
from typing import Callable, Protocol


class RouteCapabilities(Protocol):
    """The two concrete router capabilities consumed by the core registry."""

    def create_view_callback(self, view: type) -> Callable | None:
        """Return an adapter-created callback, or None for a generic Django CBV."""

    def resolve_operation_action(
        self,
        callback: object,
        method: str,
        allow_unmapped_method: bool = False,
    ) -> tuple[bool, str | None]:
        """Map an HTTP method to a logical operation action."""


def resolve_drf_operation_action(
    callback: object,
    method: str,
    allow_unmapped_method: bool = False,
) -> tuple[bool, str | None]:
    """Resolve one action map without importing DRF or its implementation types."""
    actions = getattr(callback, "actions", None)
    if not isinstance(actions, Mapping):
        return True, None
    action = actions.get(method.lower())
    if action is None and method == "HEAD":
        action = actions.get("get")
    if action is None and method != "OPTIONS" and not allow_unmapped_method:
        return False, None
    if action is not None and (not isinstance(action, str) or not action):
        return False, None
    return True, action


class DRFRouteCapabilities:
    """Isolate the concrete ViewSet as_view(actions) convention."""

    def create_view_callback(self, view: type) -> Callable | None:
        try:
            view_signature = inspect.signature(view.as_view)
        except (TypeError, ValueError):
            # Some extension-backed callables hide their signature. Calling
            # as_view() remains the authoritative check in that case.
            view_signature = None

        if view_signature is not None:
            actions_parameter = view_signature.parameters.get("actions")
            if actions_parameter is None:
                return None
            if actions_parameter.default is Parameter.empty:
                raise self._registration_error(view)

        try:
            return view.as_view()
        except TypeError as exc:
            # DRF ViewSetMixin exposes actions=None but rejects a missing map.
            if "actions" in str(exc):
                raise self._registration_error(view) from exc
            raise

    def resolve_operation_action(
        self,
        callback: object,
        method: str,
        allow_unmapped_method: bool = False,
    ) -> tuple[bool, str | None]:
        return resolve_drf_operation_action(callback, method, allow_unmapped_method)

    @staticmethod
    def _registration_error(view: type) -> TypeError:
        return TypeError(
            f"ViewSet '{view.__name__}' cannot be registered directly. "
            f"Pass a configured callable like: "
            f"{view.__name__}.as_view({{'get': 'list', 'post': 'create'}})"
        )


route_capabilities: RouteCapabilities = DRFRouteCapabilities()
