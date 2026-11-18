"""End-to-end lifecycle middleware tests using Django's real URL resolver."""

from types import ModuleType

from asgiref.sync import async_to_sync
from django.http import HttpResponse, HttpResponseNotFound
from django.test import AsyncClient, Client, override_settings
from django.urls import clear_url_caches, include, path, resolve
from rest_framework import viewsets
from rest_framework.response import Response

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
