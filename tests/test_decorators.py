import json as std_json
from unittest.mock import patch

import pytest
from django.http import JsonResponse
from django.test import RequestFactory
from django.urls import clear_url_caches, resolve, reverse
from django.views import View

from django_api_versioning.decorators import endpoint
from django_api_versioning.exceptions import (
    ForwardTypeError,
    InvalidVersionError,
    VersionRangeError,
    VersionTypeError,
)
from django_api_versioning.registry import registry
from django_api_versioning.settings import api_settings as settings


@pytest.fixture(autouse=True)
def clear_registered_routes():
    """Keep the registry and Django URL caches isolated between tests."""
    registry.urlpatterns.clear()  # Clear the previous routes before the test
    clear_url_caches()

    yield  # Run the test
    registry.urlpatterns.clear()  # Clean up after the test to ensure isolation
    clear_url_caches()


@pytest.fixture
def mock_settings():
    """Fixture to mock settings for API versioning."""
    with (
        patch.object(settings, "API_MIN_VERSION", 1),
        patch.object(settings, "API_MAX_VERSION", 3),
        patch.object(settings, "API_FORWARD_INHERITANCE", False),
    ):
        yield settings


def test_version_below_minimum(mock_settings):
    """Do not register routes for a version below the configured minimum."""

    @endpoint("users", version=0)
    def test_view():
        pass

    assert registry.urlpatterns == []


def test_version_above_maximum(mock_settings):
    """Reject a version above the configured maximum."""
    with pytest.raises(InvalidVersionError):

        @endpoint("users", version=4)
        def test_view():
            pass


@pytest.mark.parametrize(
    "invalid_version",
    [
        pytest.param("invalid", id="string"),
        pytest.param(1.5, id="float"),
    ],
)
def test_invalid_version_type(mock_settings, invalid_version):
    """Reject version values that are not integers."""
    with pytest.raises(VersionTypeError):

        @endpoint("users", version=invalid_version)
        def test_view():
            pass


def test_boolean_version_is_rejected(mock_settings):
    """Reject booleans even though bool is a subclass of int in Python."""
    with pytest.raises(VersionTypeError):

        @endpoint("users", version=True)
        def users_view():
            pass


def test_invalid_forward_type(mock_settings):
    """Reject a forward argument that is not a boolean or None."""
    with pytest.raises(ForwardTypeError):

        @endpoint("users", version=2, forward="yes")
        def users_view():
            pass


def test_register_unversioned_route(mock_settings):
    """Register only an unversioned route when version is omitted."""

    @endpoint("users")
    def test_view():
        pass

    registered_routes = {str(pattern.pattern) for pattern in registry.urlpatterns}

    assert registered_routes == {"users"}


def test_backward_compatibility_enabled(mock_settings):
    """Register the endpoint for every supported version up to its version."""

    @endpoint("users", version=3)
    def test_view():
        pass

    registered_routes = {str(pattern.pattern) for pattern in registry.urlpatterns}

    # Assert that versions 1, 2, and 3 are registered for backward compatibility
    assert registered_routes == {
        "api/v1/users",
        "api/v2/users",
        "api/v3/users",
    }


def test_backward_compatibility_disabled(mock_settings):
    """Register only the explicitly selected version when backward is False."""

    @endpoint("users", version=2, backward=False)
    def test_view():
        pass

    registered_routes = {str(pattern.pattern) for pattern in registry.urlpatterns}
    # Assert that only version 2 is registered, and versions 1 and 3 are not
    assert registered_routes == {"api/v2/users"}


def test_invalid_version_range(mock_settings):
    """Reject a configuration where the minimum exceeds the maximum."""

    # Set an invalid version range (min > max)
    with (
        patch.object(settings, "API_MIN_VERSION", 4),
        patch.object(settings, "API_MAX_VERSION", 3),
    ):
        with pytest.raises(VersionRangeError):

            @endpoint("users", version=2)
            def test_view():
                pass


def test_missing_api_version_settings():
    """Reject missing minimum and maximum API version settings."""
    with (
        patch.object(settings, "API_MIN_VERSION", None),
        patch.object(settings, "API_MAX_VERSION", None),
    ):
        with pytest.raises(VersionRangeError):

            @endpoint("users", version=2)
            def users_view():
                pass


def test_class_based_view(mock_settings):
    """Register routes for a class-based view."""

    @endpoint("users", version=2)
    class UsersView(View):
        def get(self, request):
            return JsonResponse({"message": "API Version 2 Users"})

    registered_routes = {str(pattern.pattern) for pattern in registry.urlpatterns}
    assert registered_routes == {
        "api/v1/users",
        "api/v2/users",
    }


def test_class_based_view_with_invalid_version(mock_settings):
    """Reject a class-based view whose version exceeds the maximum."""

    # Test invalid version for class-based view
    with pytest.raises(InvalidVersionError):

        @endpoint("users", version=4)
        class UsersView(View):
            def get(self, request):
                return JsonResponse({"message": "API Version 4 Users"})


def test_class_based_view_with_backward_compatibility(mock_settings):
    """Register a class-based view for all supported backward-compatible versions."""

    # Test class-based view with backward compatibility
    @endpoint("users", version=3)
    class UsersView(View):
        def get(self, request):
            return JsonResponse({"message": "API Version 3 Users"})

    registered_routes = {str(pattern.pattern) for pattern in registry.urlpatterns}
    assert registered_routes == {
        "api/v1/users",
        "api/v2/users",
        "api/v3/users",
    }


def test_class_based_view_handles_request(mock_settings):
    """Dispatch a request through a registered class-based view."""

    @endpoint("users", version=2)
    class UsersView(View):
        def get(self, request):
            return JsonResponse({"message": "API Version 2 Users"})

    pattern = next(
        (p for p in registry.urlpatterns if str(p.pattern) == "api/v2/users"), None
    )
    assert pattern is not None, "Route api/v2/users was not registered"

    factory = RequestFactory()
    request = factory.get("/api/v2/users")
    response = pattern.callback(request)

    assert response.status_code == 200
    assert std_json.loads(response.content) == {"message": "API Version 2 Users"}


def test_function_based_view_handles_request(mock_settings):
    """Dispatch a request through a registered function-based view."""

    @endpoint("health", version=1)
    def health_view(request):
        return JsonResponse({"status": "ok"})

    pattern = next(
        (p for p in registry.urlpatterns if str(p.pattern) == "api/v1/health"), None
    )
    assert pattern is not None, "Route api/v1/health was not registered"

    request = RequestFactory().get("/api/v1/health")
    response = pattern.callback(request)

    assert response.status_code == 200
    assert std_json.loads(response.content) == {"status": "ok"}


@pytest.mark.parametrize(
    "register_v3_first",
    [
        pytest.param(False, id="inherited-routes-first"),
        pytest.param(True, id="override-first"),
    ],
)
def test_forward_inheritance_and_v3_override(
    mock_settings,
    register_v3_first,
):
    """Ensure a v3 override wins over inherited v2 routes in either registration order."""
    with patch.object(settings, "API_FORWARD_INHERITANCE", True):

        def register_v2():
            @endpoint("users", version=2, view_name="users")
            def users_v2(request):
                return JsonResponse({"version": 2})

        def register_v3():
            @endpoint(
                "users",
                version=3,
                backward=False,
                forward=False,
                view_name="users",
            )
            def users_v3(request):
                return JsonResponse({"version": 3})

        if register_v3_first:
            register_v3()
            register_v2()
        else:
            register_v2()
            register_v3()

    routes = {str(pattern.pattern): pattern for pattern in registry.urlpatterns}

    assert set(routes) == {
        "api/v1/users",
        "api/v2/users",
        "api/v3/users",
    }

    request_factory = RequestFactory()

    for version in (1, 2):
        response = routes[f"api/v{version}/users"].callback(
            request_factory.get(f"/api/v{version}/users")
        )
        assert response.status_code == 200
        assert std_json.loads(response.content) == {"version": 2}

    response = routes["api/v3/users"].callback(request_factory.get("/api/v3/users"))
    assert response.status_code == 200
    assert std_json.loads(response.content) == {"version": 3}

    clear_url_caches()
    assert reverse("users", urlconf="django_api_versioning.urls") == "/api/v3/users"


def test_forward_parameter_overrides_global_setting(mock_settings):
    """Explicit forward values take precedence over the global setting."""

    with patch.object(settings, "API_FORWARD_INHERITANCE", False):

        @endpoint(
            "reports",
            version=2,
            backward=False,
            forward=True,
        )
        def reports_view(request):
            return JsonResponse({"ok": True})

    registered_routes = {str(pattern.pattern) for pattern in registry.urlpatterns}

    assert registered_routes == {
        "api/v2/reports",
        "api/v3/reports",
    }

    with patch.object(settings, "API_FORWARD_INHERITANCE", True):

        @endpoint(
            "metrics",
            version=2,
            backward=False,
            forward=False,
        )
        def metrics_view(request):
            return JsonResponse({"ok": True})

    registered_routes = {str(pattern.pattern) for pattern in registry.urlpatterns}

    assert registered_routes == {
        "api/v2/reports",
        "api/v3/reports",
        "api/v2/metrics",
    }


def test_version_below_minimum_logs_warning(mock_settings, caplog):
    """Registering a version below the configured minimum must log a warning."""
    import logging

    with caplog.at_level(
        logging.WARNING,
        logger="django_api_versioning.decorators",
    ):

        @endpoint("users", version=0)
        def users_view(request):
            return JsonResponse({"ok": True})

    assert registry.urlpatterns == []
    assert "API_MIN_VERSION" in caplog.text


def test_resolve_returns_versioned_view(mock_settings):
    """resolve() picks up the registered versioned view."""

    @endpoint("users", version=2, view_name="users-list")
    def users_view(request):
        return JsonResponse({"version": 2})

    clear_url_caches()
    match = resolve("/api/v2/users", urlconf="django_api_versioning.urls")
    assert match.func is users_view
    assert match.url_name == "users-list"


def test_resolve_unversioned_route(mock_settings):
    """Unversioned routes are still resolvable when version is omitted."""

    @endpoint("health", view_name="health")
    def health_view(request):
        return JsonResponse({"status": "ok"})

    clear_url_caches()
    match = resolve("/health", urlconf="django_api_versioning.urls")
    assert match.func is health_view


def test_cbv_view_class_preserved_through_decoration(mock_settings):
    """The original View class must be reachable from the resolved match."""

    @endpoint("teams", version=2, view_name="teams-list")
    class TeamListView(View):
        def get(self, request):
            return JsonResponse({"results": []})

    clear_url_caches()
    match = resolve("/api/v2/teams", urlconf="django_api_versioning.urls")
    assert match.func.view_class is TeamListView


try:
    from rest_framework.response import Response
    from rest_framework.views import APIView

    HAS_DRF = True
except ImportError:
    HAS_DRF = False


@pytest.mark.skipif(not HAS_DRF, reason="Django REST Framework is not installed")
def test_drf_apiview_is_registered(mock_settings):
    """A DRF APIView is routed through as_view and preserves view_class."""

    @endpoint("invoices", version=2, view_name="invoices-list")
    class InvoiceListView(APIView):
        def get(self, request):
            return Response({"results": []})

    clear_url_caches()
    match = resolve("/api/v2/invoices", urlconf="django_api_versioning.urls")
    assert match.func.view_class is InvoiceListView
