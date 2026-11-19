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

from django_api_versioning.exceptions import (
    VersionRangeError,
    VersioningError,
    VersionTypeError,
)
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


def test_registered_namespace_resolves_regex_route_when_route_text_is_not_matchable():
    """A namespace can identify a regex route whose resolver text is synthetic."""

    class DetailViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

        def retrieve(self, request, pk=None):
            return Response({"pk": pk})

    router = VersionedRouter()
    router.register("orders", DetailViewSet, version=1, basename="order")
    request = type(
        "RegexRouteRequest",
        (),
        {
            "resolver_match": type(
                "ResolverMatch",
                (),
                {
                    "route": "api/v2/orders/(?P<pk>[^/.]+)/",
                    "url_name": "order-detail",
                    "namespace": "v2",
                },
            )()
        },
    )()

    assert VersionedRouterVersioning().determine_version(request) == "2"


def test_regex_detail_route_uses_its_versioned_namespace_at_runtime():
    """A detail route's regex representation must not fall back to default version."""

    class DetailViewSet(viewsets.ViewSet):
        versioning_class = VersionedRouterVersioning

        def retrieve(self, request, pk=None):
            return Response({"pk": pk, "version": request.version})

    router = VersionedRouter()
    router.register("orders", DetailViewSet, version=1, basename="order")
    urlconf = ModuleType("adversarial_regex_detail_route_urls")
    urlconf.urlpatterns = router.urls
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        response = APIClient().get("/api/v2/orders/42/")

    assert response.status_code == 200
    assert response.json() == {"pk": "42", "version": "2"}


def test_router_urls_exclude_reintroduced_routes_owned_by_another_router(monkeypatch):
    from django_api_versioning.registry import registry
    from django_api_versioning.settings import api_settings

    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 3)

    class OriginalOrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"owner": "original"})

    class ReintroducedOrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"owner": "reintroduced"})

    original_router = VersionedRouter(app_name="original_api")
    original_router.register(
        "orders", OriginalOrdersViewSet, version=1, basename="order"
    )
    original_router.remove("orders", "order-list", from_version=2)

    replacement_router = VersionedRouter(app_name="replacement_api")
    replacement_router.register(
        "orders", ReintroducedOrdersViewSet, version=3, basename="order"
    )

    def owned_versions(router):
        return {
            getattr(pattern, registry._ROUTE_VERSION_ATTR)
            for wrapper in router.urls
            for pattern in getattr(wrapper, "url_patterns", [wrapper])
        }

    assert owned_versions(original_router) == {1}
    assert owned_versions(replacement_router) == {3}

    with pytest.raises(VersioningError, match="found 0"):
        original_router.set_lifecycle(
            "orders",
            "order-list",
            version=3,
            deprecated_at="2030-01-01T00:00:00Z",
        )


def test_router_remove_cannot_delete_another_routers_versioned_route():
    from django_api_versioning.registry import registry

    class OriginalViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"owner": "original"})

    class ReplacementViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"owner": "replacement"})

    original_router = VersionedRouter()
    original_router.register("shared", OriginalViewSet, versions=[1], basename="shared")

    replacement_router = VersionedRouter()
    replacement_router.register(
        "shared", ReplacementViewSet, version=2, basename="shared"
    )

    replacement_patterns = [
        pattern
        for pattern in registry.urlpatterns
        if getattr(pattern, registry._ROUTER_OWNER_ATTR, None)
        is replacement_router._registry_owner
    ]
    assert replacement_patterns

    with pytest.raises(VersioningError, match="owned by another VersionedRouter"):
        original_router.remove("shared", "shared-list", from_version=2)

    assert all(pattern in registry.urlpatterns for pattern in replacement_patterns)
    assert any(
        getattr(pattern, registry._ROUTER_OWNER_ATTR, None)
        is replacement_router._registry_owner
        for wrapper in replacement_router.urls
        for pattern in getattr(wrapper, "url_patterns", [wrapper])
    )


def test_router_remove_rejects_a_router_that_does_not_own_the_endpoint():
    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    owner = VersionedRouter()
    owner.register("orders", OrdersViewSet, versions=[1], basename="order")
    unrelated = VersionedRouter()

    with pytest.raises(VersioningError, match="does not own an active route"):
        unrelated.remove("orders", "order-list", from_version=2)


def test_router_remove_remains_idempotent_for_its_own_tombstoned_route():
    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register("orders", OrdersViewSet, version=1, basename="order")

    router.remove("orders", "order-list", from_version=2)
    router.remove("orders", "order-list", from_version=2)


@pytest.mark.parametrize("invalid_version", [True, "2", 2.0])
def test_router_remove_validates_version_before_foreign_owner_checks(invalid_version):
    """Invalid versions must fail validation before route ownership is inspected."""

    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    owner = VersionedRouter()
    owner.register("shared", OrdersViewSet, version=1, basename="shared")
    unrelated = VersionedRouter()

    with pytest.raises(VersionTypeError, match="Version must be an integer"):
        unrelated.remove("shared", "shared-list", from_version=invalid_version)


def test_suppressed_re_registration_cannot_steal_router_tombstone_ownership():
    """A suppressed registration must not let another router claim a tombstone."""

    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    owner = VersionedRouter()
    owner.register("orders", OrdersViewSet, versions=[1, 2], basename="order")
    owner.remove("orders", "order-list", from_version=2)

    unrelated = VersionedRouter()
    unrelated.register("orders", OrdersViewSet, versions=[2], basename="order")

    with pytest.raises(VersioningError, match="does not own an active route"):
        unrelated.remove("orders", "order-list", from_version=2)

    # The original owner retains its tombstone and can repeat removal safely.
    owner.remove("orders", "order-list", from_version=2)


@pytest.mark.parametrize("versioned", [False, True])
def test_routers_with_different_path_modes_cannot_register_same_route_prefix(versioned):
    """Regex and path converters can overlap despite different pattern strings."""

    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    regex_router = VersionedRouter(use_regex_path=True)
    path_router = VersionedRouter(use_regex_path=False)
    if versioned:
        regex_router.register("orders", OrdersViewSet, versions=[2], basename="order")
    else:
        regex_router.register("orders", OrdersViewSet, basename="order")

    with pytest.raises(
        VersioningError,
        match="Router prefix .* already registered by another VersionedRouter",
    ):
        if versioned:
            # Different basenames also produce different logical endpoint IDs;
            # the shared route prefix is still a collision.
            path_router.register(
                "orders", OrdersViewSet, versions=[2], basename="orders"
            )
        else:
            path_router.register("orders", OrdersViewSet, basename="orders")

    assert path_router._route_keys == set()


def test_router_remove_validates_minimum_version_before_ownership_checks():
    """Out-of-range removal versions must fail before checking router ownership."""

    unrelated = VersionedRouter()
    with pytest.raises(VersionRangeError, match="below API_MIN_VERSION"):
        unrelated.remove("orders", "order-list", from_version=0)


def test_same_router_prefix_with_distinct_trailing_slash_modes_can_coexist():
    """Distinct URL paths are not a collision merely because the prefix matches."""

    from django_api_versioning.registry import registry

    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    slash_router = VersionedRouter(trailing_slash=True, use_regex_path=True)
    no_slash_router = VersionedRouter(trailing_slash=False, use_regex_path=False)
    slash_router.register("orders", OrdersViewSet, versions=[2], basename="order")
    no_slash_router.register("orders", OrdersViewSet, versions=[2], basename="order")

    patterns = [
        pattern
        for pattern in registry.urlpatterns
        if getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None)
        == "orders:order-list"
        and getattr(pattern, registry._ROUTE_VERSION_ATTR, None) == 2
    ]
    assert len(patterns) == 2
    assert str(patterns[0].pattern) != str(patterns[1].pattern)
