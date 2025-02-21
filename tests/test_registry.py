import pytest
from django_api_versioning.registry import registry  


@pytest.fixture
def clear_registry():
    """Clears the registry before each test to ensure isolation."""
    registry.urlpatterns.clear()
    yield
    registry.urlpatterns.clear()


def test_register_new_route(clear_registry):
    """Test that a new route is correctly registered."""
    def sample_view():
        pass
    
    route = "api/v1/users"
    registry.register(route, sample_view)

    assert len(registry.urlpatterns) == 1
    assert str(registry.urlpatterns[0].pattern) == route


def test_register_duplicate_route(clear_registry):
    """Test that a duplicate route is detected and removed."""
    def sample_view():
        pass
    
    route = "api/v1/users"
    registry.register(route, sample_view)
    registry.register(route, sample_view)  # Registering the same route again

    assert len(registry.urlpatterns) == 1  # Only one instance of the route should be registered
    assert str(registry.urlpatterns[0].pattern) == route


def test_register_route_with_name(clear_registry):
    """Test that a route is registered with a custom name."""
    def sample_view():
        pass
    
    route = "api/v1/users"
    route_name = "user-list"
    registry.register(route, sample_view, name=route_name)

    # Check if the route has the correct name
    assert len(registry.urlpatterns) == 1
    assert registry.urlpatterns[0].name == route_name
    assert str(registry.urlpatterns[0].pattern) == route


def test_register_route_with_view_conversion(clear_registry):
    """Test that a view is correctly converted to an 'as_view' callable if needed."""
    class SampleView:
        def as_view(self):
            return lambda: None  # Simulate view conversion

    route = "api/v1/items"
    view = SampleView()
    
    registry.register(route, view)

    # Check if the route is registered with the converted view
    assert len(registry.urlpatterns) == 1
    assert callable(registry.urlpatterns[0].callback)  # Should be callable as a view
    assert str(registry.urlpatterns[0].pattern) == route


def test_duplicate_route_removal(clear_registry):
    """Test that duplicate routes are correctly removed."""
    def sample_view():
        pass
    
    route1 = "api/v1/posts"
    route2 = "api/v1/posts"  # Duplicate route
    
    registry.register(route1, sample_view)
    registry.register(route2, sample_view)  # Registering the same route again

    # Check that only one route exists after attempting to register the duplicate
    assert len(registry.urlpatterns) == 1
    assert str(registry.urlpatterns[0].pattern) == route1
