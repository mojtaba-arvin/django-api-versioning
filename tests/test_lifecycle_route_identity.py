"""Regression tests for lifecycle metadata on unrelated URL patterns."""

from types import ModuleType

from django.http import HttpResponse
from django.test import Client, override_settings
from django.urls import clear_url_caches, include, path

from django_api_versioning import endpoint, set_endpoint_lifecycle
from django_api_versioning.registry import registry
from django_api_versioning.routers import VersionedRouter


def test_unregistered_route_does_not_inherit_lifecycle_from_route_suffix():
    """A matching suffix and URL name do not establish registered identity."""

    @endpoint("resources/", versions=[1], view_name="shared-resource")
    def registered_resource(request):
        return HttpResponse("registered")

    set_endpoint_lifecycle(
        "resources/",
        version=1,
        deprecated_at="2030-01-01T00:00:00Z",
    )

    def unrelated_resource(request):
        return HttpResponse("unrelated")

    child_urlconf = ModuleType("unrelated_resource_urls")
    child_urlconf.urlpatterns = [
        path("api/v1/resources/", unrelated_resource, name="shared-resource")
    ]
    root_urlconf = ModuleType("unrelated_resource_root_urls")
    root_urlconf.urlpatterns = [path("proxy/", include(child_urlconf))]
    clear_url_caches()

    with override_settings(
        ROOT_URLCONF=root_urlconf,
        MIDDLEWARE=["django_api_versioning.lifecycle.LifecycleMiddleware"],
        API_VERSION_LIFECYCLE={1: {"status": "active"}},
    ):
        response = Client().get("/proxy/api/v1/resources/")

    assert response.status_code == 200
    assert response.content == b"unrelated"
    assert "Deprecation" not in response
    assert "Sunset" not in response


def test_registered_endpoint_lifecycle_survives_nested_include():
    """The exact registered URLPattern remains identifiable through includes."""

    @endpoint("nested-resources/", versions=[1], view_name="nested-resource")
    def nested_resource(request):
        return HttpResponse("registered")

    set_endpoint_lifecycle(
        "nested-resources/",
        version=1,
        deprecated_at="2030-01-01T00:00:00Z",
    )

    root_urlconf = ModuleType("registered_resource_root_urls")
    root_urlconf.urlpatterns = [path("proxy/", include(list(registry.urlpatterns)))]
    clear_url_caches()

    with override_settings(
        ROOT_URLCONF=root_urlconf,
        MIDDLEWARE=["django_api_versioning.lifecycle.LifecycleMiddleware"],
        API_VERSION_LIFECYCLE={1: {"status": "active"}},
    ):
        response = Client().get("/proxy/api/v1/nested-resources/")

    assert response.status_code == 200
    assert response.content == b"registered"
    assert response["Deprecation"] == "@1893456000"


def test_router_lifecycle_metadata_is_scoped_to_router_owner():
    """A trailing-slash sibling router must not inherit another router's policy."""
    from rest_framework import viewsets
    from rest_framework.response import Response

    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response({"ok": True})

    slash_router = VersionedRouter(
        trailing_slash=True,
        use_regex_path=False,
        app_name="slash_api",
    )
    no_slash_router = VersionedRouter(
        trailing_slash=False,
        use_regex_path=False,
        app_name="no_slash_api",
    )
    slash_router.register(
        "shared-orders", OrdersViewSet, versions=[2], basename="shared"
    )
    no_slash_router.register(
        "shared-orders", OrdersViewSet, versions=[2], basename="shared"
    )
    slash_router.set_lifecycle(
        "shared-orders",
        "shared-list",
        version=2,
        deprecated_at="2030-01-01T00:00:00Z",
    )

    root_urlconf = ModuleType("router_lifecycle_owner_urls")
    root_urlconf.urlpatterns = [
        path("slash/", include((slash_router.urls, "slash"), namespace="slash")),
        path(
            "no-slash/",
            include((no_slash_router.urls, "no_slash"), namespace="no_slash"),
        ),
    ]
    clear_url_caches()

    with override_settings(
        ROOT_URLCONF=root_urlconf,
        MIDDLEWARE=["django_api_versioning.lifecycle.LifecycleMiddleware"],
        API_VERSION_LIFECYCLE={2: {"status": "active"}},
    ):
        slash_response = Client().get("/slash/api/v2/shared-orders/")
        no_slash_response = Client().get("/no-slash/api/v2/shared-orders")

        # Removing one router's lifecycle segment must not erase the sibling's.
        no_slash_router.set_lifecycle(
            "shared-orders",
            "shared-list",
            version=2,
            deprecated_at="2031-01-01T00:00:00Z",
        )
        slash_router.remove("shared-orders", "shared-list", from_version=2)
        surviving_response = Client().get("/no-slash/api/v2/shared-orders")

    assert slash_response.status_code == 200
    assert slash_response["Deprecation"] == "@1893456000"
    assert no_slash_response.status_code == 200
    assert "Deprecation" not in no_slash_response
    assert "Sunset" not in no_slash_response
    assert surviving_response.status_code == 200
    assert surviving_response["Deprecation"] == "@1924992000"
