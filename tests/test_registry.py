import pytest
from types import ModuleType

from django.urls import clear_url_caches, include, path, re_path, resolve, reverse
from django.views import View

from django_api_versioning.registry import registry
from django_api_versioning.urls import urlpatterns as api_urlpatterns

# Optional DRF imports
try:
    from rest_framework.views import APIView
    from rest_framework.viewsets import ViewSet

    HAS_DRF = True
except ImportError:
    HAS_DRF = False
    APIView = None
    ViewSet = None


@pytest.fixture
def clear_registry():
    """Clear registered routes and URL resolver caches."""
    registry.clear()
    clear_url_caches()

    yield
    registry.clear()
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


def test_explicit_declarations_do_not_collapse(clear_registry):
    """Three explicit declarations produce three independent routes.

    Regression guard for the 0.2.0 collapse bug: with the default
    ``backward=True``, ``version=2`` used to overwrite ``version=1``
    because inherited fills and explicit declarations were treated
    identically.
    """

    def make_view(n):
        def view(request):
            return None

        view.__name__ = f"users_v{n}"
        return view

    views = {n: make_view(n) for n in (1, 2, 3)}

    for version in (1, 2, 3):
        registry.register(
            f"api/v{version}/users",
            views[version],
            name="users",
            source_version=version,
            route_version=version,
        )

    routes = {str(p.pattern): p.callback for p in registry.urlpatterns}

    assert routes == {
        "api/v1/users": views[1],
        "api/v2/users": views[2],
        "api/v3/users": views[3],
    }


def test_higher_source_version_replaces_lower(clear_registry):
    """
    0.3.0 segment contract: a registration with a higher source_version
    replaces an existing route registration at the same path.
    """

    def users_v2(request):
        return None

    def users_v5(request):
        return None

    # Simulate: @endpoint("users", version=2) fills v2..v5 with source_version=2
    for route_version in range(2, 6):
        registry.register(
            f"api/v{route_version}/users",
            users_v2,
            name="users",
            source_version=2,
            route_version=route_version,
        )

    # Simulate: @endpoint("users", version=5) overrides only v5
    registry.register(
        "api/v5/users",
        users_v5,
        name="users",
        source_version=5,
        route_version=5,
    )

    routes = {str(p.pattern): p.callback for p in registry.urlpatterns}
    assert routes["api/v2/users"] is users_v2
    assert routes["api/v3/users"] is users_v2
    assert routes["api/v4/users"] is users_v2
    assert routes["api/v5/users"] is users_v5


def test_lower_source_version_does_not_replace_higher(clear_registry):
    """
    0.3.0 segment contract: a registration with a lower source_version does
    NOT replace an existing route registration at the same path.
    """

    def users_v5(request):
        return None

    def users_v2(request):
        return None

    registry.register(
        "api/v5/users",
        users_v5,
        name="users",
        source_version=5,
        route_version=5,
    )

    # Simulate: @endpoint("users", version=2) — should NOT clobber v5
    registry.register(
        "api/v5/users",
        users_v2,
        name="users",
        source_version=2,
        route_version=5,
    )

    routes = {str(p.pattern): p.callback for p in registry.urlpatterns}
    assert routes["api/v5/users"] is users_v5


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


@pytest.mark.skipif(not HAS_DRF, reason="DRF not installed")
class TestDRFViewSetRegistration:
    """Test handling of DRF ViewSet registration."""

    def test_viewset_without_actions_raises_clear_error(self, clear_registry):
        """ViewSet without action configuration fails with actionable error."""

        class UserViewSet(ViewSet):
            def list(self, request):
                return None

        with pytest.raises(TypeError) as exc_info:
            registry.register("api/v1/users", UserViewSet)

        assert str(exc_info.value) == (
            "ViewSet 'UserViewSet' cannot be registered directly. "
            "Pass a configured callable like: "
            "UserViewSet.as_view({'get': 'list', 'post': 'create'})"
        )

    def test_viewset_with_actions_succeeds(self, clear_registry):
        """ViewSet with action configuration via as_view() succeeds."""

        class UserViewSet(ViewSet):
            def list(self, request):
                return None

            def create(self, request):
                return None

        registry.register(
            "api/v1/users", UserViewSet.as_view({"get": "list", "post": "create"})
        )

        assert len(registry.urlpatterns) == 1
        assert str(registry.urlpatterns[0].pattern) == "api/v1/users"

    def test_apiview_still_works(self, clear_registry):
        """DRF APIView should still register without issues."""

        class UserAPIView(APIView):
            def get(self, request):
                return None

        registry.register("api/v1/users", UserAPIView)
        assert len(registry.urlpatterns) == 1
        assert str(registry.urlpatterns[0].pattern) == "api/v1/users"
        assert registry.urlpatterns[0].callback.view_class is UserAPIView


def test_register_urlpattern_preserves_regex_pattern_and_callback_metadata(
    clear_registry,
):
    """Router-generated regex patterns and callback metadata remain intact."""

    def callback(request, pk):
        return None

    callback.actions = {"get": "retrieve"}
    pattern = re_path(
        r"^api/v1/orders/(?P<pk>[0-9]+)/$",
        callback,
        name="order-detail",
    )
    original_pattern = pattern.pattern

    registry.register_urlpattern(
        pattern,
        source_version=1,
        route_version=1,
        logical_endpoint="orders:order-detail",
    )

    assert len(registry.urlpatterns) == 1
    assert registry.urlpatterns[0] is pattern
    assert pattern.pattern is original_pattern
    assert pattern.callback is callback
    assert pattern.callback.actions == {"get": "retrieve"}
    assert pattern.name == "order-detail"
    assert getattr(pattern, registry._SOURCE_VERSION_ATTR) == 1
    assert getattr(pattern, registry._ROUTE_VERSION_ATTR) == 1
    assert getattr(pattern, registry._LOGICAL_ENDPOINT_ATTR) == ("orders:order-detail")


def test_register_urlpattern_preserves_path_converters_and_defaults(clear_registry):
    """Path converter instances and URLPattern defaults are not reconstructed."""

    def callback(request, order_id):
        return None

    pattern = path(
        "api/v1/orders/<int:order_id>/",
        callback,
        {"source": "router"},
        name="order-detail",
    )
    original_converter = pattern.pattern.converters["order_id"]

    registry.register_urlpattern(
        pattern,
        source_version=1,
        route_version=1,
        logical_endpoint="orders:order-detail",
    )

    assert registry.urlpatterns[0] is pattern
    assert pattern.pattern.converters["order_id"] is original_converter
    assert pattern.default_args == {"source": "router"}


def test_register_urlpattern_uses_source_version_precedence(clear_registry):
    """Higher source versions win; lower versions cannot replace them."""

    def v1_callback(request):
        return None

    def v2_callback(request):
        return None

    def stale_callback(request):
        return None

    first = re_path(r"^api/v2/orders/$", v1_callback, name="order-list")
    second = re_path(r"^api/v2/orders/$", v2_callback, name="order-list")
    stale = re_path(r"^api/v2/orders/$", stale_callback, name="order-list")

    registry.register_urlpattern(first, source_version=1, route_version=2)
    registry.register_urlpattern(second, source_version=2, route_version=2)
    registry.register_urlpattern(stale, source_version=1, route_version=2)

    assert len(registry.urlpatterns) == 1
    assert registry.urlpatterns[0] is second
    assert registry.urlpatterns[0].callback is v2_callback


def test_register_urlpattern_equal_source_version_is_last_registration_wins(
    clear_registry,
):
    """Equal source versions retain the registry's existing tie-break rule."""

    def first_callback(request):
        return None

    def second_callback(request):
        return None

    first = re_path(r"^api/v1/orders/$", first_callback, name="order-list")
    second = re_path(r"^api/v1/orders/$", second_callback, name="order-list")

    registry.register_urlpattern(first, source_version=1, route_version=1)
    registry.register_urlpattern(second, source_version=1, route_version=1)

    assert len(registry.urlpatterns) == 1
    assert registry.urlpatterns[0] is second


def test_register_urlpattern_groups_logical_routes_across_versions(clear_registry):
    """Different physical version paths share a logical endpoint identity."""

    def v1_callback(request):
        return None

    def v2_callback(request):
        return None

    registry.register_urlpattern(
        re_path(r"^api/v1/orders/$", v1_callback, name="order-list"),
        source_version=1,
        route_version=1,
        logical_endpoint="orders:order-list",
    )
    registry.register_urlpattern(
        re_path(r"^api/v2/orders/$", v2_callback, name="order-list"),
        source_version=2,
        route_version=2,
        logical_endpoint="orders:order-list",
    )

    assert registry.get_logical_version_matrix() == {
        "orders:order-list": {
            1: v1_callback,
            2: v2_callback,
        }
    }


def test_register_urlpattern_rejects_non_urlpattern(clear_registry):
    """Invalid integration input fails with a clear type error."""

    with pytest.raises(
        TypeError,
        match="pattern must be a django.urls.URLPattern instance",
    ):
        registry.register_urlpattern("api/v1/orders/")



def test_resolve_operation_uses_resolver_route_and_nested_namespace(clear_registry):
    """Nested includes and path converters resolve through the actual URL match."""

    def callback(request, order_id):
        return None

    pattern = path(
        "api/v2/orders/<int:order_id>/",
        callback,
        name="order-detail",
    )
    registry.register_urlpattern(
        pattern,
        source_version=2,
        route_version=2,
        logical_endpoint="orders:order-detail",
    )

    urlconf = ModuleType("resolved_operation_nested_urls")
    urlconf.urlpatterns = [
        path(
            "proxy/",
            include((registry.urlpatterns, "orders"), namespace="outer"),
        )
    ]
    match = resolve("/proxy/api/v2/orders/42/", urlconf=urlconf)

    operation = registry.resolve_operation(match, "get")

    assert operation is not None
    assert operation.logical_endpoint == "orders:order-detail"
    assert operation.route_version == 2
    assert operation.source_version == 2
    assert operation.method == "GET"
    assert operation.action is None
    assert operation.route_name == "order-detail"
    assert operation.namespace == "outer"
    assert operation.registered_route == "api/v2/orders/<int:order_id>/"


def test_resolve_operation_fails_closed_for_unregistered_or_mismatched_route(
    clear_registry,
):
    """A route-name mismatch cannot borrow another endpoint's lifecycle identity."""

    def callback(request):
        return None

    registered = path("api/v2/orders/", callback, name="registered-order-list")
    registry.register_urlpattern(
        registered,
        source_version=2,
        route_version=2,
        logical_endpoint="orders:registered-order-list",
    )

    urlconf = ModuleType("resolved_operation_mismatch_urls")
    urlconf.urlpatterns = [path("api/v2/orders/", callback, name="other-order-list")]
    match = resolve("/api/v2/orders/", urlconf=urlconf)

    assert registry.resolve_operation(match, "GET") is None


def test_resolve_operation_fails_closed_when_registered_routes_are_ambiguous(
    clear_registry,
):
    """Equivalent route suffixes with the same URL name are not guessed."""

    def callback(request):
        return None

    registry.register_urlpattern(
        path("api/v2/orders/", callback, name="order-list"),
        source_version=2,
        route_version=2,
        logical_endpoint="orders:order-list",
    )
    registry.register_urlpattern(
        re_path(r"^api/v2/orders/$", callback, name="order-list"),
        source_version=2,
        route_version=2,
        logical_endpoint="orders:legacy-order-list",
    )

    urlconf = ModuleType("resolved_operation_ambiguous_urls")
    urlconf.urlpatterns = [path("api/v2/orders/", callback, name="order-list")]
    match = resolve("/api/v2/orders/", urlconf=urlconf)

    assert registry.resolve_operation(match, "GET") is None


@pytest.mark.skipif(not HAS_DRF, reason="DRF not installed")
def test_resolve_operation_distinguishes_drf_methods_and_actions(clear_registry):
    """A shared DRF URLPattern resolves each HTTP method to its own action."""

    class OrderViewSet(ViewSet):
        def list(self, request):
            return None

        def create(self, request):
            return None

    callback = OrderViewSet.as_view({"get": "list", "post": "create"})
    pattern = path("api/v2/orders/", callback, name="order-list")
    registry.register_urlpattern(
        pattern,
        source_version=2,
        route_version=2,
        logical_endpoint="orders:order-list",
    )

    urlconf = ModuleType("resolved_operation_drf_urls")
    urlconf.urlpatterns = [
        path(
            "",
            include((registry.urlpatterns, "orders"), namespace="v2"),
        )
    ]
    match = resolve("/api/v2/orders/", urlconf=urlconf)

    get_operation = registry.resolve_operation(match, "GET")
    post_operation = registry.resolve_operation(match, "POST")

    assert get_operation is not None
    assert get_operation.action == "list"
    assert get_operation.method == "GET"
    assert post_operation is not None
    assert post_operation.action == "create"
    assert post_operation.method == "POST"
    assert registry.resolve_operation(match, "DELETE") is None


def test_resolve_operation_rejects_conflicting_version_namespace(clear_registry):
    """A vN namespace must agree with the registered concrete route version."""

    def callback(request):
        return None

    pattern = path("api/v2/orders/", callback, name="order-list")
    registry.register_urlpattern(
        pattern,
        source_version=2,
        route_version=2,
        logical_endpoint="orders:order-list",
    )

    urlconf = ModuleType("resolved_operation_wrong_namespace_urls")
    urlconf.urlpatterns = [
        path(
            "",
            include((registry.urlpatterns, "orders"), namespace="v3"),
        )
    ]
    match = resolve("/api/v2/orders/", urlconf=urlconf)

    assert registry.resolve_operation(match, "GET") is None


def test_get_route_version_returns_registered_urlpattern_version(clear_registry):
    """Resolved route strings can recover their concrete API version."""

    def callback(request):
        return None

    pattern = re_path(r"^api/v3/orders/$", callback, name="order-list")
    registry.register_urlpattern(pattern, source_version=3, route_version=3)

    assert registry.get_route_version(str(pattern.pattern)) == 3
    assert registry.get_route_version("^api/v4/orders/$") is None
