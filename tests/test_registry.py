import pytest
from django.urls import clear_url_caches, reverse
from django.views import View

from django_api_versioning.registry import registry
from django_api_versioning.urls import urlpatterns as api_urlpatterns


@pytest.fixture
def clear_registry():
    """Clear registered routes and URL resolver caches."""
    registry.urlpatterns.clear()
    clear_url_caches()

    yield
    registry.urlpatterns.clear()
    clear_url_caches()


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

    def sample_view(request):
        return None

    route = "api/v1/users"
    registry.register(route, sample_view)
    registry.register(route, sample_view)  # Registering the same route again

    assert (
        len(registry.urlpatterns) == 1
    )  # Only one instance of the route should be registered
    assert str(registry.urlpatterns[0].pattern) == route


def test_register_route_with_name(clear_registry):
    """Test that a route is registered with a custom name."""

    def sample_view(request):
        return None

    route = "api/v1/users"
    route_name = "user-list"
    registry.register(route, sample_view, name=route_name)

    # Check if the route has the correct name
    assert len(registry.urlpatterns) == 1
    assert registry.urlpatterns[0].name == route_name
    assert str(registry.urlpatterns[0].pattern) == route


def test_register_route_with_view_conversion(clear_registry):
    """A class-based view is converted via ``as_view`` and keeps view_class."""

    class SampleView(View):
        def get(self, request):
            return None

    route = "api/v1/items"
    registry.register(route, SampleView)

    # Check if the route is registered with the converted view
    assert len(registry.urlpatterns) == 1
    pattern = registry.urlpatterns[0]
    assert callable(pattern.callback)  # Should be callable as a view
    assert str(pattern.pattern) == route
    # The resulting callback retains ``view_class`` for resolve() and DRF.
    assert pattern.callback.view_class is SampleView


def test_register_rejects_view_instance(clear_registry):
    """Passing a View instance fails early with a clear error."""

    class SampleView(View):
        def get(self, request):
            return None

    with pytest.raises(TypeError, match="Pass the view class 'SampleView'"):
        registry.register("api/v1/items", SampleView())


def test_register_plain_callable_instance(clear_registry):
    """A callable instance that is not a View is registered as-is."""

    class CallableView:
        def __call__(self, request):
            return None

    route = "api/v1/items"
    view = CallableView()
    registry.register(route, view)

    assert registry.urlpatterns[0].callback is view


def test_register_function_keeps_identity(clear_registry):
    """A function-based view is stored as-is, not wrapped."""

    def sample_view(request):
        return None

    registry.register("api/v1/users", sample_view)
    assert registry.urlpatterns[0].callback is sample_view


def test_duplicate_route_removal(clear_registry):
    """Test that duplicate routes are correctly removed."""

    def sample_view(request):
        return None

    route = "api/v1/posts"

    registry.register(route, sample_view)
    registry.register(route, sample_view)  # Registering the same route again

    # Check that only one route exists after attempting to register the duplicate
    assert len(registry.urlpatterns) == 1
    assert str(registry.urlpatterns[0].pattern) == route


def test_duplicate_replacement_preserves_urlpatterns_reference(
    clear_registry,
):
    """Replacement preserves the shared urlpatterns list object."""

    def first_view(request):
        return None

    def second_view(request):
        return None

    original_urlpatterns = registry.urlpatterns

    registry.register("api/v1/users", first_view)
    registry.register("api/v1/users", second_view)

    assert registry.urlpatterns is original_urlpatterns
    assert api_urlpatterns is original_urlpatterns
    assert len(api_urlpatterns) == 1
    assert api_urlpatterns[0].callback is second_view


@pytest.mark.parametrize(
    "register_override_first",
    [
        pytest.param(False, id="inherited-routes-first"),
        pytest.param(True, id="override-first"),
    ],
)
def test_newer_definition_wins_regardless_of_registration_order(
    clear_registry,
    register_override_first,
):
    """Ensure a newer endpoint definition wins over an inherited one."""

    def users_v2(request):
        return None

    def users_v3(request):
        return None

    def register_v2_inherited_routes():
        for route_version in (1, 2, 3):
            registry.register(
                f"api/v{route_version}/users",
                users_v2,
                name="users",
                source_version=2,
                route_version=route_version,
            )

    def register_v3_override():
        registry.register(
            "api/v3/users",
            users_v3,
            name="users",
            source_version=3,
            route_version=3,
        )

    if register_override_first:
        register_v3_override()
        register_v2_inherited_routes()
    else:
        register_v2_inherited_routes()
        register_v3_override()

    routes = {str(p.pattern): p.callback for p in registry.urlpatterns}

    assert routes == {
        "api/v1/users": users_v2,
        "api/v2/users": users_v2,
        "api/v3/users": users_v3,
    }


def test_routes_are_sorted_by_version(clear_registry):
    """Ensure routes are ordered by version, with unversioned routes first."""

    def sample_view(request):
        return None

    registrations = (
        ("api/v3/users", 3),
        ("health", None),
        ("metrics", None),
        ("api/v1/users", 1),
        ("api/v2/users", 2),
    )

    for route, route_version in registrations:
        registry.register(
            route,
            sample_view,
            route_version=route_version,
        )

    assert [
        (
            str(p.pattern),
            getattr(
                p,
                "_django_api_versioning_route_version",
                None,
            ),
        )
        for p in registry.urlpatterns
    ] == [
        ("health", None),
        ("metrics", None),
        ("api/v1/users", 1),
        ("api/v2/users", 2),
        ("api/v3/users", 3),
    ]


@pytest.mark.parametrize(
    "registration_order",
    [
        pytest.param((1, 2, 3), id="ascending-registration"),
        pytest.param((3, 2, 1), id="descending-registration"),
    ],
)
def test_reverse_uses_highest_version_for_duplicate_names(
    clear_registry,
    registration_order,
):
    """Ensure reverse resolves a shared name to the highest version."""

    def users_v1(request):
        return None

    def users_v2(request):
        return None

    def users_v3(request):
        return None

    views = {
        1: users_v1,
        2: users_v2,
        3: users_v3,
    }

    for version in registration_order:
        registry.register(
            f"api/v{version}/users",
            views[version],
            name="users",
            source_version=version,
            route_version=version,
        )

    clear_url_caches()

    assert (
        reverse(
            "users",
            urlconf="django_api_versioning.urls",
        )
        == "/api/v3/users"
    )
