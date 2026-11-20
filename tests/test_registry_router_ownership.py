"""Adversarial tests for ownership boundaries between route registration APIs."""

from types import ModuleType

import pytest
from django.http import HttpResponse
from django.urls import clear_url_caches, resolve
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django_api_versioning import endpoint, remove_endpoint
from django_api_versioning.exceptions import VersioningError
from django_api_versioning.registry import registry
from django_api_versioning.routers import VersionedRouter

urlconf = ModuleType("router_ownership_test_urls")
urlconf.urlpatterns = []


@pytest.mark.parametrize("use_regex_path", [False, True])
def test_router_registration_cannot_replace_existing_decorator_route(use_regex_path):
    """A router must not silently take over a decorator-owned route."""

    @endpoint(
        "router-ownership-collision/",
        version=1,
        view_name="router-ownership-collision",
    )
    def decorator_view(request):
        return HttpResponse("decorator")

    original = next(
        pattern
        for pattern in registry.urlpatterns
        if str(pattern.pattern) == "api/v1/router-ownership-collision/"
    )

    class CollisionViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"source": "router"})

    router = VersionedRouter(use_regex_path=use_regex_path)
    with pytest.raises(VersioningError, match="different registration owner"):
        router.register(
            "router-ownership-collision",
            CollisionViewSet,
            version=1,
            basename="router-ownership-collision",
        )

    assert router._route_keys == set()
    assert any(pattern is original for pattern in registry.urlpatterns)
    assert original.callback is decorator_view


@pytest.mark.parametrize("use_regex_path", [False, True])
def test_decorator_registration_cannot_replace_existing_router_route(use_regex_path):
    """A decorator must not silently remove a router-owned URLPattern."""

    class CollisionViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"source": "router"})

    router = VersionedRouter(use_regex_path=use_regex_path)
    router.register(
        "router-owned-collision",
        CollisionViewSet,
        version=1,
        basename="router-owned-collision",
    )
    original = next(
        pattern
        for pattern in registry.urlpatterns
        if (
            getattr(pattern, registry._ROUTER_OWNER_ATTR, None)
            is router._registry_owner
            and getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
            == "router-owned-collision:router-owned-collision-list"
        )
    )

    with pytest.raises(VersioningError, match="owned by a VersionedRouter"):
        endpoint(
            "router-owned-collision/",
            version=1,
            view_name="router-owned-collision-list",
        )(lambda request: HttpResponse("decorator"))

    assert any(pattern is original for pattern in registry.urlpatterns)
    router_patterns = [
        pattern
        for wrapper in router.urls
        for pattern in getattr(wrapper, "url_patterns", [wrapper])
    ]
    assert original in router_patterns


def test_router_lifecycle_preserves_case_sensitive_action_names():
    class ExportViewSet(viewsets.ViewSet):
        @action(detail=False, methods=["get"], url_path="export")
        def exportCSV(self, request):
            return Response({"ok": True})

    router = VersionedRouter()
    router.register("exports", ExportViewSet, versions=[2], basename="export")
    export_pattern = next(
        pattern
        for pattern in registry.urlpatterns
        if getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
        == "exports:export-exportCSV"
    )

    router.set_lifecycle(
        "exports",
        export_pattern.name,
        version=2,
        action="exportCSV",
        deprecated_at="2027-01-01T00:00:00Z",
    )
    urlconf.urlpatterns = router.urls
    clear_url_caches()
    match = resolve("/api/v2/exports/export/", urlconf=urlconf)
    operation = registry.resolve_operation(match, "GET")

    assert operation is not None
    assert operation.action == "exportCSV"
    assert registry.get_endpoint_lifecycle(operation) is not None


def test_router_registration_rolls_back_earlier_versions_after_late_owner_collision():
    """A later collision must not leave earlier versions registered."""

    class CollisionViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    existing = VersionedRouter()
    existing.register(
        "atomic-owner-collision",
        CollisionViewSet,
        versions=[2],
        basename="atomic-owner-collision",
    )
    existing_patterns = list(registry.urlpatterns)

    candidate = VersionedRouter()
    with pytest.raises(
        VersioningError,
        match="already registered by another VersionedRouter",
    ):
        candidate.register(
            "atomic-owner-collision",
            CollisionViewSet,
            versions=[1, 2],
            basename="atomic-owner-collision",
        )

    assert candidate._route_keys == set()
    assert registry.urlpatterns == existing_patterns
    assert all(
        getattr(pattern, registry._ROUTER_OWNER_ATTR, None) is existing._registry_owner
        for pattern in registry.urlpatterns
    )


def test_multi_version_decorator_registration_rolls_back_after_late_router_collision():
    """A collision in the last version must not leave earlier decorator routes."""

    class CollisionViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register(
        "atomic-decorator-collision",
        CollisionViewSet,
        version=2,
        basename="atomic-decorator-collision",
    )
    existing_patterns = list(registry.urlpatterns)

    def decorator_view(request):
        return HttpResponse("decorator")

    with pytest.raises(VersioningError, match="owned by a VersionedRouter"):
        endpoint(
            "atomic-decorator-collision/",
            versions=[1, 2],
            view_name="atomic-decorator-collision",
        )(decorator_view)

    assert registry.urlpatterns == existing_patterns
    assert not hasattr(decorator_view, registry._LOGICAL_ENDPOINT_ATTR)


def test_public_remove_endpoint_cannot_remove_router_owned_routes():
    """Decorator removal must not cross the VersionedRouter ownership boundary."""
    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register("orders", OrdersViewSet, version=1, basename="order")
    logical_endpoint = "orders:order-list"
    original = next(
        pattern
        for pattern in registry.urlpatterns
        if (
            getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
            == logical_endpoint
        )
    )
    removal_boundaries = set(
        registry._removal_boundaries.get(logical_endpoint, set())
    )

    with pytest.raises(VersioningError, match="VersionedRouter"):
        remove_endpoint(logical_endpoint, from_version=1)

    assert any(pattern is original for pattern in registry.urlpatterns)
    assert any(
        child is original
        for container in router.urls
        for child in getattr(container, "url_patterns", [container])
    )
    assert (
        registry._removal_boundaries.get(logical_endpoint, set())
        == removal_boundaries
    )


def test_decorator_removal_boundary_does_not_suppress_router_registration():
    """A decorator tombstone must not preempt a later Router declaration."""
    logical_endpoint = "orders:order-list"
    remove_endpoint(logical_endpoint, from_version=1)

    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register("orders", OrdersViewSet, version=1, basename="order")

    assert any(
        getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None) == logical_endpoint
        and getattr(pattern, registry._ROUTER_OWNER_ATTR, None) is not None
        for pattern in registry.urlpatterns
    )


def test_removing_router_segment_preserves_newer_foreign_lifecycle_metadata():
    """An older router removal must not erase metadata for a newer route owner."""
    class OrdersV1ViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    class OrdersV3ViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router_v1 = VersionedRouter()
    router_v3 = VersionedRouter()
    router_v1.register("orders", OrdersV1ViewSet, versions=[1], basename="order")
    router_v3.register("orders", OrdersV3ViewSet, versions=[3], basename="order")
    router_v3.set_lifecycle(
        "orders",
        "order-list",
        version=3,
        deprecated_at="2027-06-30",
        sunset="2027-07-30",
    )
    lifecycle_key = ("orders:order-list", 3, None, None)

    assert lifecycle_key in registry._endpoint_lifecycle
    router_v1.remove("orders", "order-list", from_version=2)

    assert lifecycle_key in registry._endpoint_lifecycle
