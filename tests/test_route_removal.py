from io import StringIO
from types import ModuleType

import pytest
from django.core.management import call_command
from django.http import JsonResponse
from django.test import override_settings
from django.urls import NoReverseMatch, clear_url_caches

from django_api_versioning import api_reverse, endpoint, remove_endpoint
from django_api_versioning.exceptions import VersionMatrixError, VersioningError
from django_api_versioning.registry import registry
from django_api_versioning.testing import assert_version_matrix, build_version_matrix


def _view(name):
    def callback(request):
        return JsonResponse({"implementation": name})

    callback.__name__ = name
    return callback


def _register_segment(view, source_version=1):
    for version in range(source_version, 6):
        registry.register(
            f"api/v{version}/orders/",
            view,
            name="orders",
            source_version=source_version,
            route_version=version,
            logical_endpoint="shop/orders/",
        )


def _register_explicit(view, versions):
    for version in versions:
        registry.register(
            f"api/v{version}/orders/",
            view,
            name="orders",
            source_version=version,
            route_version=version,
            logical_endpoint="shop/orders/",
        )


def _active_versions():
    return {
        getattr(pattern, registry._ROUTE_VERSION_ATTR)
        for pattern in registry.urlpatterns
        if (getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None) == "shop/orders/")
    }


def test_remove_after_registration_suppresses_the_forward_segment():
    original = _view("orders_v1")
    _register_segment(original)

    registry.remove("shop/orders/", from_version=3)

    assert _active_versions() == {1, 2}
    matrix = build_version_matrix()
    assert matrix["api/v3/orders/"] == {"3": "<removed>"}
    assert matrix["api/v4/orders/"] == {"4": "<removed>"}
    assert matrix["api/v5/orders/"] == {"5": "<removed>"}
    assert api_reverse("orders", version=2) == "/api/v2/orders/"
    with pytest.raises(NoReverseMatch):
        api_reverse("orders", version=3)


def test_removal_before_registration_is_order_independent():
    original = _view("orders_v1")
    registry.remove("shop/orders/", from_version=3)
    _register_segment(original)

    assert _active_versions() == {1, 2}
    matrix = build_version_matrix()
    assert matrix["api/v3/orders/"] == {"3": "<removed>"}
    assert matrix["api/v4/orders/"] == {"4": "<removed>"}
    assert matrix["api/v5/orders/"] == {"5": "<removed>"}


def test_later_registration_reintroduces_route_without_resurrecting_gap():
    original = _view("orders_v1")
    replacement = _view("orders_v4")
    _register_segment(original)
    registry.remove("shop/orders/", from_version=3)
    _register_segment(replacement, source_version=4)

    assert _active_versions() == {1, 2, 4, 5}
    matrix = build_version_matrix()
    assert matrix["api/v3/orders/"] == {"3": "<removed>"}
    assert matrix["api/v4/orders/"] == {"4": "orders_v4"}
    assert matrix["api/v5/orders/"] == {"5": "orders_v4"}
    assert api_reverse("orders", version=4) == "/api/v4/orders/"


def test_late_older_registration_cannot_replace_reintroduced_route():
    original = _view("orders_v1")
    replacement = _view("orders_v4")
    _register_segment(original)
    registry.remove("shop/orders/", from_version=3)
    _register_segment(replacement, source_version=4)

    # Simulate a module containing the old declaration being imported late.
    for version in range(1, 6):
        registry.register(
            f"api/v{version}/orders/",
            original,
            name="orders",
            source_version=1,
            route_version=version,
            logical_endpoint="shop/orders/",
        )

    assert _active_versions() == {1, 2, 4, 5}
    assert {
        getattr(pattern, registry._ROUTE_VERSION_ATTR): pattern.callback
        for pattern in registry.urlpatterns
        if getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None) == "shop/orders/"
    }[4] is replacement


def test_explicit_version_registration_respects_removal_boundary():
    original = _view("orders_explicit")
    _register_explicit(original, [1, 3, 5])
    registry.remove("shop/orders/", from_version=3)

    assert _active_versions() == {1, 5}
    assert api_reverse("orders", version=5) == "/api/v5/orders/"
    with pytest.raises(NoReverseMatch):
        api_reverse("orders", version=3)


def test_public_remove_endpoint_uses_decorator_logical_identity():
    @endpoint("invoices/", version=1, view_name="invoices", app_name="billing")
    def invoices(request):
        return JsonResponse({})

    remove_endpoint("invoices/", from_version=4, app_name="billing")

    assert {
        getattr(pattern, registry._ROUTE_VERSION_ATTR)
        for pattern in registry.urlpatterns
        if (
            getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
            == "billing/invoices/"
        )
    } == {1, 2, 3}
    with pytest.raises(NoReverseMatch):
        api_reverse("invoices", version=4)


def test_router_removal_is_action_specific():
    from rest_framework import viewsets
    from rest_framework.decorators import action
    from rest_framework.response import Response
    from rest_framework.test import APIClient

    from django_api_versioning.routers import VersionedRouter

    class OrderViewSetV1(viewsets.ViewSet):
        def list(self, request):
            return Response({})

        @action(detail=False, methods=["get"], url_path="archive")
        def archive(self, request):
            return Response({})

    router = VersionedRouter()
    router.register("orders", OrderViewSetV1, version=1, basename="order")
    router.remove("orders", "order-archive", from_version=3)

    active = {
        pattern.name
        for pattern in registry.urlpatterns
        if getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, "").startswith("orders:")
    }
    assert "order-list" in active
    assert "order-archive" in active
    urlconf = ModuleType("route_removal_test_urls")
    urlconf.urlpatterns = router.urls
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        client = APIClient()
        assert client.get("/api/v2/orders/archive/").status_code == 200
        assert client.get("/api/v3/orders/").status_code == 200
        assert client.get("/api/v3/orders/archive/").status_code == 404

    assert all(
        getattr(pattern, registry._ROUTE_VERSION_ATTR) < 3
        for pattern in registry.urlpatterns
        if (
            getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
            == "orders:order-archive"
        )
    )


def test_strict_snapshot_distinguishes_removed_from_missing(tmp_path):
    original = _view("orders_v1")
    _register_segment(original)
    snapshot = tmp_path / "version-matrix.json"

    assert_version_matrix(snapshot=str(snapshot), update=True, strict=True)
    registry.remove("shop/orders/", from_version=3)

    with pytest.raises(VersionMatrixError, match="<removed>"):
        assert_version_matrix(snapshot=str(snapshot), strict=True)

    assert_version_matrix(snapshot=str(snapshot), update=True, strict=True)
    import json

    expected = json.loads(snapshot.read_text())
    assert expected["api/v3/orders/"] == {"3": "<removed>"}
    assert_version_matrix(snapshot=str(snapshot), strict=True)


def test_reused_physical_path_keeps_the_new_active_route_in_snapshot():
    original = _view("orders_v1")
    replacement = _view("orders_v3_replacement")
    _register_segment(original)
    registry.remove("shop/orders/", from_version=3)

    registry.register(
        "api/v3/orders/",
        replacement,
        name="orders",
        source_version=3,
        route_version=3,
        logical_endpoint="shop/replacement-orders/",
    )

    matrix = build_version_matrix()
    assert matrix["api/v3/orders/"] == {"3": "orders_v3_replacement"}


def test_check_versions_displays_explicit_removed_state():
    original = _view("orders_v1")
    _register_segment(original)
    registry.remove("shop/orders/", from_version=3)

    output = StringIO()
    call_command("check_versions", stdout=output)

    assert "shop/orders/" in output.getvalue()
    assert "v3" in output.getvalue()
    assert "<removed>" in output.getvalue()



@pytest.mark.parametrize("prefix", ["/orders", "orders/"])
def test_router_remove_rejects_non_normalized_prefix(prefix):
    from django_api_versioning.routers import VersionedRouter

    router = VersionedRouter()
    with pytest.raises(VersioningError, match="relative path"):
        router.remove(prefix, "order-archive", from_version=3)


def test_router_remove_rejects_empty_route_name():
    from django_api_versioning.routers import VersionedRouter

    router = VersionedRouter()
    with pytest.raises(VersioningError, match="route_name"):
        router.remove("orders", "", from_version=3)
