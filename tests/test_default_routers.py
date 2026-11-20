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
    VersionedDefaultRouter,
    VersionedRouterVersioning,
)

urlconf = ModuleType("versioned_default_router_test_urls")
urlconf.urlpatterns = []


class PostViewSetV1(viewsets.ViewSet):
    versioning_class = VersionedRouterVersioning

    def list(self, request, *args, **kwargs):
        return Response({"implementation": "v1", "version": request.version})

    def retrieve(self, request, pk=None, *args, **kwargs):
        return Response({"implementation": "v1", "version": request.version, "pk": pk})

    @action(detail=False, methods=["get"])
    def metadata(self, request, *args, **kwargs):
        return Response({"implementation": "v1-action", "version": request.version})


class PostViewSetV2(viewsets.ViewSet):
    versioning_class = VersionedRouterVersioning

    def list(self, request, *args, **kwargs):
        return Response({"implementation": "v2", "version": request.version})

    def retrieve(self, request, pk=None, *args, **kwargs):
        return Response({"implementation": "v2", "version": request.version, "pk": pk})


class CommentViewSet(viewsets.ViewSet):
    versioning_class = VersionedRouterVersioning

    def list(self, request, *args, **kwargs):
        return Response({"resource": "comments", "version": request.version})


@pytest.fixture(autouse=True)
def reset_urlconf():
    urlconf.urlpatterns = []
    clear_url_caches()
    yield
    urlconf.urlpatterns = []
    clear_url_caches()


def test_api_root_is_generated_from_the_effective_routes_for_each_version():
    router = VersionedDefaultRouter()
    router.register("posts", PostViewSetV1, version=1, basename="post")
    router.register("posts", PostViewSetV2, version=2, basename="post")
    router.register("comments", CommentViewSet, version=2, basename="comment")
    router.remove("comments", "comment-list", from_version=3)

    urlconf.urlpatterns = router.urls
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        client = APIClient()
        v1 = client.get("/api/v1/")
        v2 = client.get("/api/v2/")
        v3 = client.get("/api/v3/")

        assert v1.status_code == 200
        assert set(v1.json()) == {"posts"}
        assert v1.json()["posts"].endswith("/api/v1/posts/")

        assert v2.status_code == 200
        assert set(v2.json()) == {"posts", "comments"}
        assert v2.json()["posts"].endswith("/api/v2/posts/")
        assert v2.json()["comments"].endswith("/api/v2/comments/")

        assert v3.status_code == 200
        assert set(v3.json()) == {"posts"}
        assert v3.json()["posts"].endswith("/api/v3/posts/")
        assert client.get("/api/v3/comments/").status_code == 404


def test_format_suffixes_work_for_versioned_routes_and_api_roots():
    router = VersionedDefaultRouter()
    router.register("posts", PostViewSetV1, version=1, basename="post")
    router.register("posts", PostViewSetV2, version=2, basename="post")

    urlconf.urlpatterns = router.urls
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        client = APIClient()

        v1 = client.get("/api/v1/posts.json")
        v2 = client.get("/api/v2/posts.json")
        inherited_action = client.get("/api/v2/posts/metadata.json")
        root = client.get("/api/v2/.json")

    assert v1.status_code == 200
    assert v1.json() == {"implementation": "v1", "version": "1"}
    assert v2.status_code == 200
    assert v2.json() == {"implementation": "v2", "version": "2"}
    assert inherited_action.status_code == 200
    assert inherited_action.json() == {
        "implementation": "v1-action",
        "version": "2",
    }
    assert root.status_code == 200
    assert root.json()["posts"].endswith("/api/v2/posts.json")


def test_format_suffixes_preserve_path_converters_and_trailing_slash_setting():
    class IntegerViewSet(viewsets.ViewSet):
        versioning_class = VersionedRouterVersioning
        lookup_value_converter = "int"

        def retrieve(self, request, pk=None, *args, **kwargs):
            return Response({"pk": pk, "version": request.version})

    router = VersionedDefaultRouter(use_regex_path=False, trailing_slash=False)
    router.register("items", IntegerViewSet, version=1, basename="item")
    urlconf.urlpatterns = router.urls
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        response = APIClient().get("/api/v1/items/42.json")

    assert response.status_code == 200
    assert response.json() == {"pk": 42, "version": "1"}


def test_nested_namespace_is_preserved_by_versioned_api_root():
    router = VersionedDefaultRouter()
    router.register("posts", PostViewSetV1, version=1, basename="post")
    urlconf.urlpatterns = [
        path(
            "root/",
            include((router.urls, "outer"), namespace="outer"),
        )
    ]
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        response = APIClient().get("/root/api/v1/")

    assert response.status_code == 200
    assert response.json()["posts"].endswith("/root/api/v1/posts/")


def test_unversioned_default_router_api_root_is_supported():
    class HealthViewSet(viewsets.ViewSet):
        def list(self, request, *args, **kwargs):
            return Response({"status": "ok"})

    router = VersionedDefaultRouter()
    router.register("health", HealthViewSet, basename="health")
    urlconf.urlpatterns = router.urls
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        client = APIClient()
        root = client.get("/")
        health = client.get("/health/")

    assert root.status_code == 200
    assert root.json()["health"].endswith("/health/")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


def test_api_root_can_be_disabled_while_format_suffixes_remain_enabled():
    router = VersionedDefaultRouter(
        include_root_view=False,
        include_format_suffixes=True,
    )
    router.register("posts", PostViewSetV1, version=1, basename="post")
    urlconf.urlpatterns = router.urls
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        client = APIClient()
        assert client.get("/api/v1/").status_code == 404
        assert client.get("/api/v1/posts.json").status_code == 200


def test_format_suffixes_can_be_disabled_while_api_root_remains_enabled():
    router = VersionedDefaultRouter(
        include_root_view=True,
        include_format_suffixes=False,
    )
    router.register("posts", PostViewSetV1, version=1, basename="post")
    urlconf.urlpatterns = router.urls
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        client = APIClient()
        assert client.get("/api/v1/").status_code == 200
        assert client.get("/api/v1/posts.json").status_code == 404
        assert client.get("/api/v1/posts/").status_code == 200


def test_versioned_default_router_validates_options():
    with pytest.raises(TypeError, match="include_root_view must be a bool"):
        VersionedDefaultRouter(include_root_view=1)

    with pytest.raises(TypeError, match="include_format_suffixes must be a bool"):
        VersionedDefaultRouter(include_format_suffixes="yes")

    with pytest.raises(VersioningError, match="root_view_name"):
        VersionedDefaultRouter(root_view_name=" ")
