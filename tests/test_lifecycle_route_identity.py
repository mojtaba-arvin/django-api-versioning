"""Regression tests for lifecycle metadata on unrelated URL patterns."""

from types import ModuleType

from django.http import HttpResponse
from django.test import Client, override_settings
from django.urls import clear_url_caches, include, path

from django_api_versioning import endpoint, set_endpoint_lifecycle
from django_api_versioning.registry import registry


def test_manual_route_with_matching_suffix_and_name_does_not_inherit_endpoint_lifecycle():
    """A route outside the registry must not inherit metadata by suffix alone."""

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
        path(
            "api/v1/resources/",
            unrelated_resource,
            name="shared-resource",
        )
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
