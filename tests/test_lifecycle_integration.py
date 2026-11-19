"""End-to-end lifecycle middleware tests using Django's real URL resolver."""

from types import ModuleType

import pytest
from asgiref.sync import async_to_sync
from django.http import HttpResponse, HttpResponseNotFound
from django.test import AsyncClient, Client, override_settings
from django.urls import clear_url_caches, include, path, resolve
from rest_framework import viewsets
from rest_framework.response import Response

from django_api_versioning import endpoint, set_endpoint_lifecycle
from django_api_versioning.exceptions import VersioningError
from django_api_versioning.registry import registry
from django_api_versioning.routers import VersionedRouter
from django_api_versioning.settings import api_settings

urlconf = ModuleType("lifecycle_route_test_urls")
urlconf.urlpatterns = []


class RequestURLConfOverrideMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.urlconf = urlconf
        return self.get_response(request)


def _lifecycle(version_one, version_two):
    return {
        1: version_one,
        2: version_two,
    }


def _retired():
    return {"status": "retired", "sunset": "2000-01-01"}


def _deprecated():
    return {
        "status": "deprecated",
        "deprecated_at": "2020-01-01T00:00:00+00:00",
        "sunset": "2099-01-01",
    }


def _install(patterns, lifecycle):
    urlconf.urlpatterns = patterns
    clear_url_caches()
    return override_settings(
        ROOT_URLCONF=urlconf,
        MIDDLEWARE=["django_api_versioning.lifecycle.LifecycleMiddleware"],
        API_VERSION_LIFECYCLE=lifecycle,
    )


def test_nested_decorator_route_uses_the_child_version_not_parent_prefix():
    calls = []

    def orders(request):
        calls.append("called")
        return HttpResponse("orders")

    registry.register_urlpattern(
        path("api/v2/orders/", orders),
        route_version=2,
    )
    context = _install(
        [path("api/v1/proxy/", include(registry.urlpatterns))],
        _lifecycle(_retired(), _deprecated()),
    )

    with context:
        response = Client().get("/api/v1/proxy/api/v2/orders/")

    assert response.status_code == 200
    assert response.content == b"orders"
    assert calls == ["called"]
    assert response["Deprecation"] == "@1577836800"
    assert response["Sunset"] == "Thu, 01 Jan 2099 00:00:00 GMT"


def test_expired_resolved_child_version_short_circuits_before_view():
    calls = []

    def orders(request):
        calls.append("called")
        return HttpResponse("must not run")

    registry.register_urlpattern(
        path("api/v2/orders/", orders),
        route_version=2,
    )
    context = _install(
        [path("api/v1/proxy/", include(registry.urlpatterns))],
        _lifecycle({"status": "active"}, _retired()),
    )

    with context:
        response = Client().get("/api/v1/proxy/api/v2/orders/")

    assert response.status_code == 410
    assert calls == []


def test_unresolved_path_with_one_version_keeps_version_wide_gone_behavior():
    def orders(request):
        return HttpResponse("orders")

    registry.register_urlpattern(
        path("api/v2/orders/", orders),
        route_version=2,
    )
    context = _install(
        list(registry.urlpatterns),
        _lifecycle({"status": "active"}, _retired()),
    )

    with context:
        response = Client().get("/api/v2/unknown/")

    assert response.status_code == 410


def test_unresolved_nested_path_with_multiple_versions_is_not_guessed():
    def orders(request):
        return HttpResponse("orders")

    registry.register_urlpattern(
        path("api/v2/orders/", orders),
        route_version=2,
    )
    context = _install(
        [path("api/v1/proxy/", include(registry.urlpatterns))],
        _lifecycle(_retired(), _retired()),
    )

    with context:
        response = Client().get("/api/v1/proxy/api/v2/unknown/")

    assert response.status_code == 404


def test_resolved_view_404_still_receives_lifecycle_headers():
    def missing_order(request):
        return HttpResponseNotFound("not found")

    registry.register_urlpattern(
        path("api/v2/orders/", missing_order),
        route_version=2,
    )
    context = _install(
        list(registry.urlpatterns),
        _lifecycle({"status": "active"}, _deprecated()),
    )

    with context:
        response = Client().get("/api/v2/orders/")

    assert response.status_code == 404
    assert response["Deprecation"] == "@1577836800"
    assert response["Sunset"] == "Thu, 01 Jan 2099 00:00:00 GMT"


def test_versioned_router_route_metadata_survives_nested_include(monkeypatch):
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 2)

    class OrderViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"ok": True})

    router = VersionedRouter()
    router.register("orders", OrderViewSet, version=2, basename="order")
    context = _install(
        [path("api/v1/proxy/", include(router.urls))],
        _lifecycle(_retired(), _deprecated()),
    )

    with context:
        match = resolve("/api/v1/proxy/api/v2/orders/", urlconf=urlconf)
        assert registry.get_resolved_route_version(match.route) == 2, match.route
        response = Client().get("/api/v1/proxy/api/v2/orders/")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert response["Deprecation"] == "@1577836800"


def test_decorator_endpoint_lifecycle_headers_are_concrete_version_scoped():
    @endpoint("lifecycle-orders", versions=[2, 3])
    def orders(request):
        return HttpResponse("orders")

    set_endpoint_lifecycle(
        "lifecycle-orders",
        version=2,
        deprecated_at="2030-01-01T00:00:00Z",
        sunset="2031-01-01T00:00:00Z",
    )
    context = _install(
        list(registry.urlpatterns),
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        version_two = Client().get("/api/v2/lifecycle-orders")
        version_three = Client().get("/api/v3/lifecycle-orders")

    assert version_two.status_code == 200
    assert version_two["Deprecation"] == "@1893456000"
    assert version_two["Sunset"] == "Wed, 01 Jan 2031 00:00:00 GMT"
    assert version_three.status_code == 200
    assert "Deprecation" not in version_three
    assert "Sunset" not in version_three


def test_endpoint_lifecycle_metadata_is_scoped_to_resolved_drf_action():
    calls = []

    class OrderViewSet(viewsets.ViewSet):
        def list(self, request):
            calls.append("list")
            return Response({"action": "list"})

        def create(self, request):
            calls.append("create")
            return Response({"action": "create"}, status=201)

    router = VersionedRouter()
    router.register("orders", OrderViewSet, versions=[2], basename="order")
    router.set_lifecycle(
        "orders",
        "order-list",
        version=2,
        action="list",
        deprecated_at="2030-01-01T00:00:00Z",
    )
    context = _install(
        list(router.urls),
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        listed = Client().get("/api/v2/orders/")
        created = Client().post(
            "/api/v2/orders/", data="{}", content_type="application/json"
        )

    assert listed.status_code == 200
    assert listed["Deprecation"] == "@1893456000"
    assert created.status_code == 201
    assert "Deprecation" not in created
    assert calls == ["list", "create"]


def test_past_endpoint_sunset_emits_headers_without_returning_410():
    @endpoint("past-endpoint", versions=[2])
    def past_endpoint(request):
        return HttpResponse("still available")

    set_endpoint_lifecycle(
        "past-endpoint",
        version=2,
        deprecated_at="2020-01-01T00:00:00Z",
        sunset="2021-01-01T00:00:00Z",
    )
    context = _install(
        list(registry.urlpatterns),
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        response = Client().get("/api/v2/past-endpoint")

    assert response.status_code == 200
    assert response.content == b"still available"
    assert response["Deprecation"] == "@1577836800"
    assert response["Sunset"] == "Fri, 01 Jan 2021 00:00:00 GMT"


def test_endpoint_sunset_without_deprecation_emits_only_sunset_header():
    @endpoint("sunset-only", versions=[2])
    def sunset_only(request):
        return HttpResponse("sunset only")

    set_endpoint_lifecycle(
        "sunset-only",
        version=2,
        sunset="2031-01-01T00:00:00Z",
    )
    context = _install(
        list(registry.urlpatterns),
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        response = Client().get("/api/v2/sunset-only")

    assert response.status_code == 200
    assert "Deprecation" not in response
    assert response["Sunset"] == "Wed, 01 Jan 2031 00:00:00 GMT"


def test_version_wide_sunset_410_takes_precedence_over_endpoint_lifecycle():
    calls = []

    @endpoint("version-retired", versions=[2])
    def version_retired(request):
        calls.append("called")
        return HttpResponse("must not run")

    set_endpoint_lifecycle(
        "version-retired",
        version=2,
        deprecated_at="2030-01-01T00:00:00Z",
        sunset="2031-01-01T00:00:00Z",
    )
    context = _install(
        list(registry.urlpatterns),
        _lifecycle({"status": "active"}, _retired()),
    )

    with context:
        response = Client().get("/api/v2/version-retired")

    assert response.status_code == 410
    assert calls == []


def test_endpoint_and_version_lifecycle_headers_choose_earliest_date():
    @endpoint("combined-lifecycle", versions=[2])
    def combined(request):
        return HttpResponse("combined")

    set_endpoint_lifecycle(
        "combined-lifecycle",
        version=2,
        deprecated_at="2028-01-01T00:00:00Z",
        sunset="2030-01-01T00:00:00Z",
    )
    context = _install(
        list(registry.urlpatterns),
        _lifecycle(
            {"status": "active"},
            {
                "status": "deprecated",
                "deprecated_at": "2029-01-01T00:00:00Z",
                "sunset": "2031-01-01T00:00:00Z",
            },
        ),
    )

    with context:
        response = Client().get("/api/v2/combined-lifecycle")

    assert response.status_code == 200
    assert response["Deprecation"] == "@1830297600"
    assert response["Sunset"] == "Tue, 01 Jan 2030 00:00:00 GMT"


def test_async_endpoint_lifecycle_headers_use_resolved_operation():
    @endpoint("async-endpoint-lifecycle", versions=[2])
    async def async_endpoint(request):
        return HttpResponse("async endpoint")

    set_endpoint_lifecycle(
        "async-endpoint-lifecycle",
        version=2,
        deprecated_at="2030-01-01T00:00:00Z",
    )
    context = _install(
        list(registry.urlpatterns),
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    async def make_request():
        with context:
            return await AsyncClient().get("/api/v2/async-endpoint-lifecycle")

    response = async_to_sync(make_request)()

    assert response.status_code == 200
    assert response.content == b"async endpoint"
    assert response["Deprecation"] == "@1893456000"


def test_async_request_uses_resolved_route_lifecycle_policy():
    calls = []

    async def async_orders(request):
        calls.append("called")
        return HttpResponse("async")

    registry.register_urlpattern(
        path("api/v2/async-orders/", async_orders),
        route_version=2,
    )
    context = _install(
        list(registry.urlpatterns),
        _lifecycle({"status": "active"}, _retired()),
    )

    async def make_request():
        with context:
            return await AsyncClient().get("/api/v2/async-orders/")

    response = async_to_sync(make_request)()

    assert response.status_code == 410
    assert calls == []


def test_request_urlconf_override_controls_resolved_lifecycle_version():
    def orders(request):
        return HttpResponse("custom urlconf")

    registry.register_urlpattern(
        path("api/v2/orders/", orders),
        route_version=2,
    )
    urlconf.urlpatterns = list(registry.urlpatterns)

    root_urlconf = ModuleType("lifecycle_root_urls")
    root_urlconf.urlpatterns = [
        path("api/v2/orders/", orders, kwargs={"version": 1}),
    ]
    middleware = [
        f"{__name__}.RequestURLConfOverrideMiddleware",
        "django_api_versioning.lifecycle.LifecycleMiddleware",
    ]
    context = override_settings(
        ROOT_URLCONF=root_urlconf,
        MIDDLEWARE=middleware,
        API_VERSION_LIFECYCLE=_lifecycle(_retired(), _deprecated()),
    )

    with context:
        response = Client().get("/api/v2/orders/")

    assert response.status_code == 200
    assert response.content == b"custom urlconf"
    assert response["Deprecation"] == "@1577836800"


def test_endpoint_lifecycle_declaration_before_registration_is_applied():
    set_endpoint_lifecycle(
        "lifecycle-before-registration",
        version=2,
        deprecated_at="2030-01-01T00:00:00Z",
    )

    @endpoint("lifecycle-before-registration", versions=[2])
    def before_registration(request):
        return HttpResponse("registered after declaration")

    @endpoint("lifecycle-after-registration", versions=[2])
    def after_registration(request):
        return HttpResponse("declared after registration")

    set_endpoint_lifecycle(
        "lifecycle-after-registration",
        version=2,
        deprecated_at="2030-01-01T00:00:00Z",
    )
    context = _install(
        list(registry.urlpatterns),
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        before = Client().get("/api/v2/lifecycle-before-registration")
        after = Client().get("/api/v2/lifecycle-after-registration")

    assert before.status_code == 200
    assert before["Deprecation"] == "@1893456000"
    assert after.status_code == 200
    assert after["Deprecation"] == "@1893456000"


def test_reintroduced_endpoint_does_not_inherit_previous_version_lifecycle(
    monkeypatch,
):
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 3)

    @endpoint("reintroduced-lifecycle", version=1)
    def original(request):
        return HttpResponse("original")

    set_endpoint_lifecycle(
        "reintroduced-lifecycle",
        version=1,
        deprecated_at="2030-01-01T00:00:00Z",
    )
    registry.remove("reintroduced-lifecycle", from_version=2)

    @endpoint("reintroduced-lifecycle", version=3)
    def reintroduced(request):
        return HttpResponse("reintroduced")

    context = _install(
        list(registry.urlpatterns),
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        version_one = Client().get("/api/v1/reintroduced-lifecycle")
        removed_version = Client().get("/api/v2/reintroduced-lifecycle")
        version_three = Client().get("/api/v3/reintroduced-lifecycle")

    assert version_one.status_code == 200
    assert version_one["Deprecation"] == "@1893456000"
    assert removed_version.status_code == 404
    assert version_three.status_code == 200
    assert version_three.content == b"reintroduced"
    assert "Deprecation" not in version_three
    assert "Sunset" not in version_three


def test_versioned_routers_reject_duplicate_route_patterns_across_namespaces():
    class PrimaryOrderViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"router": "primary"})

    class SecondaryOrderViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"router": "secondary"})

    primary_router = VersionedRouter(app_name="primary_api")
    primary_router.register(
        "orders", PrimaryOrderViewSet, versions=[2], basename="order"
    )

    secondary_router = VersionedRouter(app_name="secondary_api")
    with pytest.raises(
        VersioningError,
        match="already registered by another VersionedRouter",
    ):
        secondary_router.register(
            "orders", SecondaryOrderViewSet, versions=[2], basename="order"
        )

    context = _install(
        [
            path(
                "primary/",
                include((primary_router.urls, "primary_api"), namespace="primary"),
            ),
        ],
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        primary = Client().get("/primary/api/v2/orders/")

    assert primary.status_code == 200
    assert primary.json() == {"router": "primary"}


def test_route_lifecycle_headers_apply_to_drf_options_requests():
    """DRF handles OPTIONS outside the ViewSet action map.

    The URL still resolves to a registered endpoint, so route-wide lifecycle
    metadata must be retained even though OPTIONS has no ViewSet action.
    """

    class ReadOnlyProductViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register("products", ReadOnlyProductViewSet, version=1, basename="product")
    router.set_lifecycle(
        "products",
        "product-list",
        version=1,
        deprecated_at="2030-01-01T00:00:00Z",
    )
    context = _install(
        router.urls,
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        response = Client().options("/api/v1/products/")

    assert response.status_code == 200
    assert response["Deprecation"] == "@1893456000"


def test_route_wide_lifecycle_headers_are_present_on_drf_405_responses():
    """A resolved route keeps its route-wide lifecycle contract on HTTP 405."""

    class ReadOnlyOrderViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register("orders", ReadOnlyOrderViewSet, version=1, basename="order")
    router.set_lifecycle(
        "orders",
        "order-list",
        version=1,
        deprecated_at="2030-01-01T00:00:00Z",
    )
    context = _install(
        router.urls,
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        response = Client().patch("/api/v1/orders/")

    assert response.status_code == 405
    assert response["Deprecation"] == "@1893456000"


def test_action_scoped_lifecycle_does_not_leak_to_unmapped_drf_methods():
    """A 405 has route identity but no selected action."""

    class ReadOnlyOrderViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register("orders", ReadOnlyOrderViewSet, version=1, basename="order")
    router.set_lifecycle(
        "orders",
        "order-list",
        version=1,
        action="list",
        deprecated_at="2030-01-01T00:00:00Z",
    )
    context = _install(
        router.urls,
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        response = Client().patch("/api/v1/orders/")

    assert response.status_code == 405
    assert "Deprecation" not in response


def test_get_scoped_lifecycle_metadata_also_applies_to_head_requests():
    """HTTP HEAD shares GET semantics and must not lose GET lifecycle headers."""

    class ReadOnlyOrderViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register("orders", ReadOnlyOrderViewSet, version=1, basename="order")
    router.set_lifecycle(
        "orders",
        "order-list",
        version=1,
        methods=["GET"],
        deprecated_at="2030-01-01T00:00:00Z",
    )
    context = _install(
        router.urls,
        _lifecycle({"status": "active"}, {"status": "active"}),
    )

    with context:
        get_response = Client().get("/api/v1/orders/")
        head_response = Client().head("/api/v1/orders/")

    assert get_response.status_code == 200
    assert head_response.status_code == 200
    assert get_response["Deprecation"] == "@1893456000"
    assert head_response["Deprecation"] == get_response["Deprecation"]
