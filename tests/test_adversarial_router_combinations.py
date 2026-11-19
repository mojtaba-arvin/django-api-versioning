"""Adversarial integration tests for interactions across router features.

These tests deliberately vary registration order and namespace topology rather
than exercising each feature in isolation.
"""

from itertools import permutations
from types import ModuleType

import pytest
from django.test import override_settings
from django.urls import clear_url_caches, include, path
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.test import APIClient

from django_api_versioning.exceptions import VersioningError
from django_api_versioning.routers import (
    VersionedRouter,
    VersionedRouterVersioning,
)


class OrderedViewSetV1(viewsets.ViewSet):
    versioning_class = VersionedRouterVersioning

    def list(self, request):
        return Response({"implementation": "v1", "version": request.version})

    @action(detail=False, methods=["post"])
    def publish(self, request):
        return Response({"implementation": "v1-publish", "version": request.version})


class OrderedViewSetV2(viewsets.ViewSet):
    versioning_class = VersionedRouterVersioning

    def list(self, request):
        return Response({"implementation": "v2", "version": request.version})


class OrderedViewSetV3(viewsets.ViewSet):
    versioning_class = VersionedRouterVersioning

    def list(self, request):
        return Response({"implementation": "v3", "version": request.version})


@pytest.mark.parametrize(
    "registration_order",
    list(permutations((1, 2, 3))),
    ids=lambda order: "-".join(map(str, order)),
)
def test_router_override_precedence_is_independent_of_all_registration_orders(
    registration_order,
):
    """Every permutation must produce the same version-to-implementation map."""
    router = VersionedRouter()
    viewsets_by_version = {
        1: OrderedViewSetV1,
        2: OrderedViewSetV2,
        3: OrderedViewSetV3,
    }

    for version in registration_order:
        router.register(
            "orders",
            viewsets_by_version[version],
            version=version,
            basename="order",
        )

    urlconf = ModuleType("adversarial_registration_order_urls")
    urlconf.urlpatterns = router.urls
    clear_url_caches()

    expected = {
        1: "v1",
        2: "v2",
        3: "v3",
        4: "v3",
        5: "v3",
    }
    with override_settings(ROOT_URLCONF=urlconf):
        client = APIClient()
        for version, implementation in expected.items():
            response = client.get(f"/api/v{version}/orders/")
            assert response.status_code == 200
            assert response.json() == {
                "implementation": implementation,
                "version": str(version),
            }

        # An action omitted by later ViewSets must remain inherited at every
        # version, regardless of which declaration was registered first.
        for version in range(1, 6):
            response = client.post(f"/api/v{version}/orders/publish/")
            assert response.status_code == 200
            assert response.json() == {
                "implementation": "v1-publish",
                "version": str(version),
            }


def test_unversioned_router_does_not_mistake_outer_v_number_namespace_for_api_version():
    """Only a namespace emitted by VersionedRouter may select its API version."""

    class HealthViewSet(viewsets.ViewSet):
        versioning_class = VersionedRouterVersioning

        def list(self, request):
            return Response({"version": request.version})

    router = VersionedRouter()
    router.register("health", HealthViewSet, basename="health")

    urlconf = ModuleType("adversarial_outer_v_namespace_urls")
    urlconf.urlpatterns = [
        path(
            "outer/",
            include((router.urls, "health_api"), namespace="v9"),
        )
    ]
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        response = APIClient().get("/outer/health/")

    assert response.status_code == 200
    assert response.json() == {"version": None}


def test_nested_outer_v_namespace_does_not_override_actual_router_version():
    """The nearest package version namespace must win over a numeric outer one."""

    class HealthViewSet(viewsets.ViewSet):
        versioning_class = VersionedRouterVersioning

        def list(self, request):
            return Response({"version": request.version})

    router = VersionedRouter()
    router.register("health", HealthViewSet, version=2, basename="health")

    urlconf = ModuleType("adversarial_nested_v_namespace_urls")
    urlconf.urlpatterns = [
        path(
            "outer/",
            include((router.urls, "health_api"), namespace="v9"),
        )
    ]
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        response = APIClient().get("/outer/api/v3/health/")

    assert response.status_code == 200
    assert response.json() == {"version": "3"}


@pytest.mark.parametrize("collision_version", [1, 2, 3])
def test_failed_multi_version_registration_rolls_back_at_every_collision_position(
    collision_version,
):
    """Failure at any generated route must restore all shared and local state."""
    from django_api_versioning.registry import registry

    class ExistingViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"owner": "existing"})

    existing_router = VersionedRouter()
    existing_router.register(
        "inventory",
        ExistingViewSet,
        versions=[collision_version],
        basename="inventory",
    )

    baseline_patterns = list(registry.urlpatterns)
    baseline_removed = dict(registry._removed_patterns)
    candidate_router = VersionedRouter()

    with pytest.raises(VersioningError, match="another VersionedRouter"):
        candidate_router.register(
            "inventory",
            ExistingViewSet,
            versions=[1, 2, 3],
            basename="inventory",
        )

    assert registry.urlpatterns == baseline_patterns
    assert registry._removed_patterns == baseline_removed
    assert candidate_router._route_keys == set()
    assert candidate_router._basenames == {}
    assert candidate_router._basename_prefixes == {}
