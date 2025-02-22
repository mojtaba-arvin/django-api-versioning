import pytest
from unittest.mock import patch
from django.http import JsonResponse
from django.views import View
from django_api_versioning.settings import api_settings as settings
from django_api_versioning.registry import registry
from django_api_versioning.decorators import endpoint
from django_api_versioning.exceptions import InvalidVersionError, VersionTypeError, VersionRangeError


@pytest.fixture(autouse=True)
def clear_registered_routes():
    """Clear the registry before each test to ensure isolation."""
    registry.urlpatterns.clear()  # Clear the previous routes before the test
    yield  # Run the test
    registry.urlpatterns.clear()  # Clean up after the test to ensure isolation

@pytest.fixture
def mock_settings():
    """Fixture to mock settings for API versioning."""
    with patch.object(settings, 'API_MIN_VERSION', 1), patch.object(settings, 'API_MAX_VERSION', 3):
        yield settings

def test_version_below_minimum(mock_settings):
    @endpoint("users", version=0)
    def test_view():
        pass

    registered_routes = [str(p.pattern) for p in registry.urlpatterns]
    assert "api/v0/users" not in registered_routes, f"Unexpected registered routes: {registered_routes}"

def test_version_above_maximum(mock_settings):
    with pytest.raises(InvalidVersionError):
        @endpoint("users", version=4)
        def test_view():
            pass

def test_invalid_version_type(mock_settings):
    with pytest.raises(VersionTypeError):
        @endpoint("users", version="invalid")
        def test_view():
            pass

def test_register_unversioned_route(mock_settings):
    @endpoint("users")
    def test_view():
        pass

    registered_routes = [str(p.pattern) for p in registry.urlpatterns]
    # Assert that no versioned route (e.g., api/v1/users) is registered
    for version in range(1, 4):
        assert f"api/v{version}/users" not in registered_routes, f"Unexpected versioned route: api/v{version}/users"
    # Assert that the unversioned route is registered
    assert "users" in registered_routes, f"Missing unversioned route: {registered_routes}"

def test_backward_compatibility_enabled(mock_settings):
    @endpoint("users", version=3)
    def test_view():
        pass

    registered_routes = [str(p.pattern) for p in registry.urlpatterns]
    # Assert that versions 1, 2, and 3 are registered for backward compatibility
    for version in range(1, 4):
        assert f"api/v{version}/users" in registered_routes, f"Missing route for v{version}: {registered_routes}"

def test_backward_compatibility_disabled(mock_settings):
    @endpoint("users", version=2, backward=False)
    def test_view():
        pass

    registered_routes = [str(p.pattern) for p in registry.urlpatterns]
    # Assert that only version 2 is registered, and versions 1 and 3 are not
    assert "api/v2/users" in registered_routes
    assert "api/v1/users" not in registered_routes
    assert "api/v3/users" not in registered_routes

def test_invalid_version_range(mock_settings):
    # Set an invalid version range (min > max)
    with patch.object(settings, 'API_MIN_VERSION', 4), patch.object(settings, 'API_MAX_VERSION', 3):
        with pytest.raises(VersionRangeError):
            @endpoint("users", version=2)
            def test_view():
                pass

def test_missing_api_version_settings():
    # Remove API version settings to test for missing settings scenario
    with patch.dict(settings.__dict__, {'API_MIN_VERSION': None, 'API_MAX_VERSION': None}):
        with pytest.raises(VersionRangeError):
            @endpoint("users", version=2)
            def test_view():
                pass

def test_class_based_view(mock_settings):
    # Create a class-based view and decorate it with the `endpoint` decorator
    @endpoint("users", version=2)
    class UsersView(View):
        def get(self, request):
            return JsonResponse({"message": "API Version 2 Users"})

    # Register the view and check if the route is correctly registered
    registered_routes = [str(p.pattern) for p in registry.urlpatterns]
    assert "api/v2/users" in registered_routes, f"Route for version 2 is missing: {registered_routes}"

def test_class_based_view_with_invalid_version(mock_settings):
    # Test invalid version for class-based view
    with pytest.raises(InvalidVersionError):
        @endpoint("users", version=4)
        class UsersView(View):
            def get(self, request):
                return JsonResponse({"message": "API Version 4 Users"})

def test_class_based_view_with_backward_compatibility(mock_settings):
    # Test class-based view with backward compatibility
    @endpoint("users", version=3)
    class UsersView(View):
        def get(self, request):
            return JsonResponse({"message": "API Version 3 Users"})

    registered_routes = [str(p.pattern) for p in registry.urlpatterns]
    # Assert that versions 1, 2, and 3 are registered for backward compatibility
    for version in range(1, 4):
        assert f"api/v{version}/users" in registered_routes, f"Missing route for v{version}: {registered_routes}"
