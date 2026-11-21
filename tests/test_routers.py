from types import ModuleType, SimpleNamespace

import pytest
from django.test import override_settings
from django.urls import clear_url_caches, include, path, resolve
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.serializers import HyperlinkedIdentityField, Serializer
from rest_framework.test import APIClient

from django_api_versioning.exceptions import (
    InvalidVersionError,
    VersioningError,
    VersionRangeError,
    VersionTypeError,
)
from django_api_versioning.registry import registry
from django_api_versioning.reverse import api_reverse
from django_api_versioning.routers import VersionedRouter, VersionedRouterVersioning

urlconf = ModuleType("versioned_router_test_urls")
urlconf.urlpatterns = []


@pytest.fixture(autouse=True)
def reset_urlconf():
    urlconf.urlpatterns = []
    clear_url_caches()
    yield
    urlconf.urlpatterns = []
    clear_url_caches()


class PostHyperlinkedSerializer(Serializer):
    url = HyperlinkedIdentityField(view_name="post-detail")


class PostViewSetV1(viewsets.ViewSet):
    versioning_class = VersionedRouterVersioning

    def list(self, request):
        return Response({"implementation": "v1", "version": request.version})

    def retrieve(self, request, pk=None):
        return Response({"implementation": "v1", "version": request.version, "pk": pk})

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        return Response(
            {"implementation": "v1-publish", "version": request.version, "pk": pk}
        )

    @action(detail=False, methods=["get"], url_path="reverse-list")
    def reverse_list(self, request):
        return Response(
            {
                "implementation": "v1-reverse",
                "url": self.reverse_action("list"),
                "request_version": request.version,
                "versioning_scheme": type(request.versioning_scheme).__name__,
                "transport": getattr(request._request, "api_versioning_scheme", None),
            }
        )

    @action(detail=False, methods=["get"], url_path="status")
    def status(self, request):
        return Response({"method": "get", "version": request.version})

    @status.mapping.post
    def status_post(self, request):
        return Response({"method": "post", "version": request.version})

    @action(detail=False, methods=["get"])
    def hyperlink(self, request):
        serializer = PostHyperlinkedSerializer(
            instance=SimpleNamespace(pk=1),
            context={"request": request},
        )
        return Response(serializer.data)


class PostViewSetV2(viewsets.ViewSet):
    versioning_class = VersionedRouterVersioning

    def list(self, request):
        return Response({"implementation": "v2", "version": request.version})

    def retrieve(self, request, pk=None):
        return Response({"implementation": "v2", "version": request.version, "pk": pk})


@pytest.fixture
def versioned_router():
    router = VersionedRouter()
    router.register("posts", PostViewSetV1, version=1, basename="post")
    router.register("posts", PostViewSetV2, version=2, basename="post")
    urlconf.urlpatterns = router.urls
    clear_url_caches()
    yield router
    urlconf.urlpatterns = []
    clear_url_caches()


class TestVersionedRouter:
    def test_viewset_dispatch_and_per_route_inheritance(self, versioned_router):
        with override_settings(ROOT_URLCONF=urlconf):
            client = APIClient()

            v1 = client.get("/api/v1/posts/")
            v2 = client.get("/api/v2/posts/")
            v3 = client.get("/api/v3/posts/")

            assert v1.status_code == 200
            assert v1.json() == {"implementation": "v1", "version": "1"}
            assert v2.status_code == 200
            assert v2.json() == {"implementation": "v2", "version": "2"}
            assert v3.status_code == 200
            assert v3.json() == {"implementation": "v2", "version": "3"}

            # This custom action exists only in V1. It must remain inherited
            # when V2 replaces list/detail, and request.version must be V2.
            inherited = client.post("/api/v2/posts/1/publish/")
            assert inherited.status_code == 200
            assert inherited.json() == {
                "implementation": "v1-publish",
                "version": "2",
                "pk": "1",
            }

    def test_reverse_action_uses_the_current_version_namespace(self, versioned_router):
        with override_settings(ROOT_URLCONF=urlconf):
            response = APIClient().get("/api/v2/posts/reverse-list/")

        assert response.status_code == 200
        assert response.json()["url"].endswith("/api/v2/posts/")

    def test_nested_namespace_is_preserved_for_version_and_reverse(
        self, versioned_router
    ):
        urlconf.urlpatterns = [
            path(
                "root/",
                include((versioned_router.urls, "outer"), namespace="outer"),
            )
        ]
        clear_url_caches()

        with override_settings(ROOT_URLCONF=urlconf):
            response = APIClient().get("/root/api/v2/posts/reverse-list/")

        assert response.status_code == 200
        assert response.json()["url"].endswith("/root/api/v2/posts/")

    def test_explicit_versions_leave_gaps_unregistered(self):
        router = VersionedRouter()
        router.register(
            "premium",
            PostViewSetV1,
            versions=[2, 4],
            basename="premium",
        )
        urlconf.urlpatterns = router.urls
        clear_url_caches()

        with override_settings(ROOT_URLCONF=urlconf):
            client = APIClient()
            assert client.get("/api/v2/premium/").status_code == 200
            assert client.get("/api/v3/premium/").status_code == 404
            assert client.get("/api/v4/premium/").status_code == 200

    def test_inconsistent_basenames_for_same_prefix_are_rejected(self):
        router = VersionedRouter()
        router.register("posts", PostViewSetV1, version=1, basename="post")

        with pytest.raises(VersioningError, match="same basename across versions"):
            router.register("posts", PostViewSetV2, version=2, basename="posts")

    def test_unversioned_registration_is_not_wrapped_in_a_version_namespace(self):
        class HealthViewSet(viewsets.ViewSet):
            def list(self, request):
                return Response({"status": "ok"})

        router = VersionedRouter()
        router.register("health", HealthViewSet, basename="health")
        urlconf.urlpatterns = router.urls
        clear_url_caches()

        assert len(router.urls) == 1
        assert resolve("/health/", urlconf=urlconf).namespace == ""

        with override_settings(ROOT_URLCONF=urlconf):
            response = APIClient().get("/health/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_custom_action_method_mapping_is_preserved_on_inherited_route(
        self, versioned_router
    ):
        with override_settings(ROOT_URLCONF=urlconf):
            response = APIClient().post("/api/v2/posts/status/")

        assert response.status_code == 200
        assert response.json() == {"method": "post", "version": "2"}

    def test_hyperlinked_field_reverses_with_the_active_api_version(
        self, versioned_router
    ):
        with override_settings(ROOT_URLCONF=urlconf):
            response = APIClient().get("/api/v2/posts/hyperlink/")

        assert response.status_code == 200
        assert response.json()["url"].endswith("/api/v2/posts/1/")


def test_router_lifecycle_scopes_one_viewset_action():
    class LifecycleViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

        def create(self, request):
            return Response({}, status=201)

    router = VersionedRouter()
    router.register("orders", LifecycleViewSet, version=2, basename="order")
    router.set_lifecycle(
        "orders",
        "order-list",
        version=2,
        action="list",
        deprecated_at="2027-01-01T00:00:00Z",
    )
    urlconf.urlpatterns = router.urls
    match = resolve("/api/v2/orders/", urlconf=urlconf)

    list_operation = registry.resolve_operation(match, "GET")
    create_operation = registry.resolve_operation(match, "POST")

    assert list_operation is not None
    assert list_operation.action == "list"
    assert registry.get_endpoint_lifecycle(list_operation) is not None
    assert create_operation is not None
    assert create_operation.action == "create"
    assert registry.get_endpoint_lifecycle(create_operation) is None


def test_router_lifecycle_methods_resolve_through_action_map():
    class LifecycleViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

        def create(self, request):
            return Response({}, status=201)

    router = VersionedRouter()
    router.register("orders", LifecycleViewSet, version=2, basename="order")
    router.set_lifecycle(
        "orders",
        "order-list",
        version=2,
        methods=["POST"],
        deprecated_at="2027-01-01T00:00:00Z",
    )
    urlconf.urlpatterns = router.urls
    match = resolve("/api/v2/orders/", urlconf=urlconf)

    list_operation = registry.resolve_operation(match, "GET")
    create_operation = registry.resolve_operation(match, "POST")

    assert list_operation is not None
    assert registry.get_endpoint_lifecycle(list_operation) is None
    assert create_operation is not None
    assert registry.get_endpoint_lifecycle(create_operation) is not None


def test_router_lifecycle_rejects_unknown_action():
    class LifecycleViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register("orders", LifecycleViewSet, version=2, basename="order")

    with pytest.raises(VersioningError, match="not registered"):
        router.set_lifecycle(
            "orders",
            "order-list",
            version=2,
            action="archive",
            deprecated_at="2027-01-01T00:00:00Z",
        )


@pytest.mark.parametrize("invalid_version", [True, 1.0, "1"])
def test_router_rejects_non_integer_version_values(invalid_version):
    router = VersionedRouter()
    with pytest.raises(VersionTypeError, match="Version must be an integer"):
        router.register(
            "posts",
            PostViewSetV1,
            version=invalid_version,
            basename="post",
        )


def test_router_rejects_versions_above_the_configured_maximum():
    router = VersionedRouter()
    with pytest.raises(InvalidVersionError):
        router.register(
            "posts",
            PostViewSetV1,
            version=6,
            basename="post",
        )


def test_router_rejects_duplicate_explicit_versions():
    router = VersionedRouter()
    with pytest.raises(VersionRangeError, match="must not contain duplicates"):
        router.register(
            "posts",
            PostViewSetV1,
            versions=[1, 2, 2],
            basename="post",
        )


def test_path_converter_router_patterns_are_preserved_and_reversible():
    class IntegerPostViewSet(viewsets.ViewSet):
        lookup_value_converter = "int"

        def retrieve(self, request, pk=None):
            return Response({"pk": pk})

    router = VersionedRouter(use_regex_path=False, trailing_slash=False)
    router.register(
        "integer-posts",
        IntegerPostViewSet,
        version=1,
        basename="integer-post",
    )
    urlconf.urlpatterns = router.urls
    clear_url_caches()

    match = resolve("/api/v1/integer-posts/42", urlconf=urlconf)
    assert match.kwargs["pk"] == 42
    assert api_reverse("integer-post-detail", version=1, pk=42) == (
        "/api/v1/integer-posts/42"
    )


def test_router_rejects_duplicate_basenames_across_prefixes():
    router = VersionedRouter()
    router.register("posts", PostViewSetV1, version=1, basename="resource")

    with pytest.raises(VersioningError, match="already registered for prefix"):
        router.register("comments", PostViewSetV2, version=1, basename="resource")


def test_versioning_adapter_uses_nested_version_namespace():
    versioning = VersionedRouterVersioning()
    request = SimpleNamespace(resolver_match=SimpleNamespace(namespace="outer:v3"))

    assert versioning.determine_version(request) == "3"
    assert versioning.get_versioned_viewname("post-list", request) == (
        "outer:v3:post-list"
    )


def test_versioning_adapter_rejects_disallowed_namespace_version():
    versioning = VersionedRouterVersioning()
    versioning.allowed_versions = ["1", "2"]
    request = SimpleNamespace(resolver_match=SimpleNamespace(namespace="v3"))

    with pytest.raises(NotFound, match="allowed API version"):
        versioning.determine_version(request)


def test_versioning_adapter_does_not_allow_missing_version_when_allowlist_is_set():
    versioning = VersionedRouterVersioning()
    versioning.default_version = None
    versioning.allowed_versions = ["1"]
    request = SimpleNamespace(resolver_match=SimpleNamespace(namespace="outer"))

    with pytest.raises(NotFound, match="allowed API version"):
        versioning.determine_version(request)


def test_router_rejects_invalid_constructor_and_registration_inputs():
    with pytest.raises(VersioningError, match="app_name"):
        VersionedRouter(app_name=" ")

    router = VersionedRouter()
    with pytest.raises(TypeError, match="prefix must be a string"):
        router.register(1, PostViewSetV1)
    with pytest.raises(VersioningError, match="relative path"):
        router.register("/posts", PostViewSetV1)
    with pytest.raises(VersionRangeError, match="either 'version' or 'versions'"):
        router.register("posts", PostViewSetV1, version=1, versions=[1])
    with pytest.raises(VersionTypeError, match="must be a list"):
        router.register("posts", PostViewSetV1, versions=(1, 2))


def test_router_skips_declarations_below_minimum_version(monkeypatch, caplog):
    monkeypatch.setattr("django_api_versioning.routers.api_settings.API_MIN_VERSION", 2)
    router = VersionedRouter()

    with caplog.at_level("WARNING"):
        router.register("old-posts", PostViewSetV1, version=1, basename="old-post")
        router.register(
            "selected-posts",
            PostViewSetV1,
            versions=[1, 2],
            basename="selected-post",
        )

    assert router.urls
    assert all(
        "v1" not in str(pattern.pattern)
        for pattern in router.urls
        if hasattr(pattern, "pattern")
    )
    assert "No routes will be registered" in caplog.text
    assert "Skipping this version" in caplog.text


@pytest.mark.parametrize(
    ("prefix", "route_name", "error", "message"),
    [
        (1, "post-list", TypeError, "prefix must be a string"),
        ("/posts", "post-list", VersioningError, "relative path"),
        ("posts", 1, TypeError, "route_name must be a string"),
        ("posts", "", VersioningError, "route_name must be a non-empty"),
    ],
)
def test_router_remove_validates_route_identity(prefix, route_name, error, message):
    with pytest.raises(error, match=message):
        VersionedRouter().remove(prefix, route_name, from_version=2)


@pytest.mark.parametrize(
    ("methods", "message"),
    [
        ([], "non-empty list"),
        ([""], "non-empty HTTP method strings"),
        (["GET", " get "], "must not contain duplicates"),
        (["PATCH"], "is not registered"),
    ],
)
def test_router_lifecycle_validates_http_method_mapping(methods, message):
    router = VersionedRouter()
    router.register("posts", PostViewSetV1, version=1, basename="post")

    with pytest.raises(VersioningError, match=message):
        router.set_lifecycle(
            "posts",
            "post-list",
            version=1,
            methods=methods,
            deprecated_at="2027-01-01T00:00:00Z",
        )


def test_router_lifecycle_maps_head_to_get_action():
    router = VersionedRouter()
    router.register("posts", PostViewSetV1, version=1, basename="post")

    router.set_lifecycle(
        "posts",
        "post-list",
        version=1,
        action="list",
        methods=["HEAD"],
        deprecated_at="2027-01-01T00:00:00Z",
    )

    assert any(
        key[0] == "posts:post-list" and key[2] == "HEAD" and key[3] == "list"
        for key in registry._endpoint_lifecycle
    )


def test_router_lifecycle_rejects_method_action_mismatch():
    router = VersionedRouter()
    router.register("posts", PostViewSetV1, version=1, basename="post")

    with pytest.raises(VersioningError, match="maps to action"):
        router.set_lifecycle(
            "posts",
            "post-status",
            version=1,
            action="status",
            methods=["POST"],
            deprecated_at="2027-01-01T00:00:00Z",
        )


def test_failed_registration_does_not_reserve_prefix_or_basename():
    """A collision must not poison a router's future valid registrations."""
    existing_router = VersionedRouter()
    existing_router.register("posts", PostViewSetV1, version=1, basename="post")

    retryable_router = VersionedRouter()
    with pytest.raises(VersioningError, match="another VersionedRouter"):
        retryable_router.register("posts", PostViewSetV2, version=1, basename="post")

    # The failed declaration did not become a registration. Reusing its
    # basename for a different prefix on the same router must remain valid.
    retryable_router.register("comments", PostViewSetV2, version=1, basename="post")
    assert any(
        getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR, None) == "comments:post-list"
        for pattern in registry.urlpatterns
    )


def test_multi_version_registration_is_atomic_when_a_later_version_collides():
    """A collision in a later concrete version must not leave earlier versions."""
    existing_router = VersionedRouter()
    existing_router.register("posts", PostViewSetV1, version=2, basename="post")

    candidate_router = VersionedRouter()
    with pytest.raises(VersioningError, match="another VersionedRouter"):
        candidate_router.register(
            "posts",
            PostViewSetV2,
            versions=[1, 2],
            basename="post",
        )

    candidate_routes = [
        pattern
        for pattern in registry.urlpatterns
        if getattr(pattern, registry._ROUTER_OWNER_ATTR, None)
        is candidate_router._registry_owner
    ]
    assert candidate_routes == []


def test_separate_default_routers_keep_reverse_namespaces_isolated():
    """Distinct routers must not alias the same default vN namespace."""
    posts_router = VersionedRouter()
    posts_router.register("posts", PostViewSetV1, version=1, basename="post")

    comments_router = VersionedRouter()
    comments_router.register("comments", PostViewSetV1, version=1, basename="comment")

    urlconf.urlpatterns = posts_router.urls + comments_router.urls
    clear_url_caches()

    with override_settings(ROOT_URLCONF=urlconf):
        response = APIClient().get("/api/v1/posts/reverse-list/")

    assert response.status_code == 200
    assert response.json()["url"].endswith("/api/v1/posts/")


def test_failed_multi_method_lifecycle_declaration_is_atomic():
    """An invalid later method must not leave lifecycle metadata for earlier ones."""
    router = VersionedRouter()
    router.register("posts", PostViewSetV1, version=1, basename="post")

    with pytest.raises(VersioningError, match="is not registered"):
        router.set_lifecycle(
            "posts",
            "post-list",
            version=1,
            methods=["GET", "PATCH"],
            deprecated_at="2030-01-01T00:00:00Z",
        )

    assert not any(
        key[0] == "posts:post-list" and key[1] == 1
        for key in registry._endpoint_lifecycle
    )


def test_conflicting_later_lifecycle_scope_rolls_back_earlier_scopes():
    """A conflict in the last method must not persist earlier new scopes."""

    class OrderViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

        def create(self, request):
            return Response({}, status=201)

    router = VersionedRouter()
    router.register("orders", OrderViewSet, version=1, basename="order")
    router.set_lifecycle(
        "orders",
        "order-list",
        version=1,
        methods=["POST"],
        deprecated_at="2030-01-01T00:00:00Z",
    )

    with pytest.raises(VersioningError, match="Conflicting endpoint lifecycle"):
        router.set_lifecycle(
            "orders",
            "order-list",
            version=1,
            methods=["GET", "POST"],
            deprecated_at="2040-01-01T00:00:00Z",
        )

    assert (
        "orders:order-list",
        1,
        "GET",
        "list",
    ) not in registry._endpoint_lifecycle
    assert (
        registry._endpoint_lifecycle[
            ("orders:order-list", 1, "POST", "create")
        ].deprecated_at.year
        == 2030
    )


@pytest.mark.parametrize(
    ("scheme", "path", "headers", "expected_url"),
    [
        (
            "header",
            "/api/posts/reverse-list/",
            {"HTTP_ACCEPT_VERSION": "2"},
            "/api/posts/",
        ),
        (
            "query",
            "/api/posts/reverse-list/?version=2",
            {},
            "/api/posts/?version=2",
        ),
    ],
)
def test_router_dispatch_and_reverse_follow_non_path_transport(
    versioned_router, scheme, path, headers, expected_url
):
    with override_settings(
        ROOT_URLCONF=urlconf,
        MIDDLEWARE=["django_api_versioning.negotiation.VersionNegotiationMiddleware"],
        API_VERSIONING_SCHEME=scheme,
        API_BASE_PATH="api/v{version}/",
        API_UNVERSIONED_BASE_PATH="api/",
        API_MIN_VERSION=1,
        API_MAX_VERSION=3,
    ):
        response = APIClient().get(path, **headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["implementation"] == "v1-reverse"
    assert payload["request_version"] == "2", payload
    assert payload["versioning_scheme"] == "VersionedRouterVersioning", payload
    assert payload["transport"] == scheme, payload
    assert payload["url"].endswith(expected_url), payload
    assert "/api/v2/" not in payload["url"]


def test_negative_version_is_rejected():
    router = VersionedRouter()
    with pytest.raises(VersionRangeError, match="non-negative"):
        router.register("negative", PostViewSetV1, version=-1, basename="negative")
    assert registry.urlpatterns == []


def test_negative_explicit_version_is_rejected_atomically():
    router = VersionedRouter()
    with pytest.raises(VersionRangeError, match="non-negative"):
        router.register(
            "negative-list",
            PostViewSetV1,
            versions=[1, -1, 2],
            basename="negative-list",
        )
    assert registry.urlpatterns == []


def test_path_router_rejects_ambiguous_literal_prefixes():
    router = VersionedRouter(use_regex_path=False)
    for prefix in ("orders/../admin", "orders//archive", "orders/%252e%252e/admin"):
        with pytest.raises(VersioningError, match="prefix"):
            router.register(prefix, PostViewSetV1, versions=[1], basename="unsafe")


@pytest.mark.parametrize("option", ["trailing_slash", "use_regex_path"])
@pytest.mark.parametrize("value", ["false", 0, None])
def test_router_boolean_options_require_actual_booleans(option, value):
    options = {option: value}
    with pytest.raises(TypeError, match=f"{option} must be a bool"):
        VersionedRouter(**options)
