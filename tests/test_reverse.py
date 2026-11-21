import pytest
from django.http import JsonResponse
from django.test import Client, override_settings
from django.urls import NoReverseMatch, path, re_path, register_converter

from django_api_versioning import api_reverse
from django_api_versioning.decorators import endpoint
from django_api_versioning.exceptions import AmbiguousVersionError, VersionTypeError
from django_api_versioning.registry import registry
from django_api_versioning.settings import api_settings as settings


@pytest.fixture
def versions_1_to_5():
    old_min, old_max = settings.API_MIN_VERSION, settings.API_MAX_VERSION
    settings.API_MIN_VERSION, settings.API_MAX_VERSION = 1, 5
    yield
    settings.API_MIN_VERSION, settings.API_MAX_VERSION = old_min, old_max


def _register_users():
    @endpoint("users", version=3, view_name="users")
    def users_v3(request):
        return JsonResponse({})

    @endpoint("users", version=5, view_name="users")
    def users_v5(request):
        return JsonResponse({})


class TestApiReverse:
    def test_explicit_version(self, versions_1_to_5):
        _register_users()
        assert api_reverse("users", version=3) == "/api/v3/users"
        assert api_reverse("users", version=4) == "/api/v4/users"
        assert api_reverse("users", version=5) == "/api/v5/users"

    @pytest.mark.parametrize("invalid_version", [True, 1.0, "1"])
    def test_non_integer_version_is_rejected(self, invalid_version):
        @endpoint("typed-version/", versions=[1], view_name="typed-version")
        def typed_version(request):
            return JsonResponse({})

        with pytest.raises(VersionTypeError, match="Version must be an integer"):
            api_reverse("typed-version", version=invalid_version)

    def test_missing_version_raises_no_reverse_match(self, versions_1_to_5):
        _register_users()
        with pytest.raises(NoReverseMatch):
            api_reverse("users", version=99)

    def test_unknown_name_raises_no_reverse_match(self, versions_1_to_5):
        _register_users()
        with pytest.raises(NoReverseMatch):
            api_reverse("unknown-name", version=3)

    def test_no_version_with_multiple_matches_raises_ambiguous(self, versions_1_to_5):
        _register_users()
        with pytest.raises(AmbiguousVersionError):
            api_reverse("users")

    def test_no_version_with_single_match_returns_it(self):
        # NOTE: versions=[1], not version=1 — a segment would register v1..v5
        # and produce multiple matches, which is the wrong fixture for this case.
        @endpoint("only", versions=[1], view_name="only")
        def only(request):
            return JsonResponse({})

        assert api_reverse("only") == "/api/v1/only"

    def test_kwargs_are_passed_through(self):
        @endpoint("users/<int:pk>/", version=1, view_name="user-detail")
        def user_detail(request, pk):
            return JsonResponse({"pk": pk})

        # kwargs are passed as regular keyword arguments, not as a dict.
        url = api_reverse("user-detail", version=1, pk=42)
        assert url == "/api/v1/users/42/"

    def test_missing_kwarg_raises_no_reverse_match(self):
        @endpoint("users/<int:pk>/", version=1, view_name="user-detail")
        def user_detail(request, pk):
            return JsonResponse({"pk": pk})

        with pytest.raises(NoReverseMatch, match="Missing required parameter"):
            api_reverse("user-detail", version=1)

    def test_unexpected_kwarg_raises_no_reverse_match(self):
        @endpoint("users/<int:pk>/", version=1, view_name="user-detail-extra")
        def user_detail(request, pk):
            return JsonResponse({"pk": pk})

        with pytest.raises(NoReverseMatch, match="Unexpected parameter"):
            api_reverse("user-detail-extra", version=1, pk=42, username="alice")

    def test_invalid_int_parameter_raises_no_reverse_match(self):
        @endpoint("users/<int:pk>/", version=1, view_name="user-detail-invalid-int")
        def user_detail(request, pk):
            return JsonResponse({"pk": pk})

        with pytest.raises(NoReverseMatch):
            api_reverse("user-detail-invalid-int", version=1, pk="not-an-int")

    def test_string_parameter_rejects_path_separator(self):
        @endpoint("users/<str:username>/", version=1, view_name="user-detail-slash")
        def user_detail(request, username):
            return JsonResponse({"username": username})

        with pytest.raises(NoReverseMatch):
            api_reverse("user-detail-slash", version=1, username="alice/admin")

    def test_path_converter_accepts_path_separator(self):
        @endpoint("files/<path:resource>/", version=1, view_name="file-detail")
        def file_detail(request, resource):
            return JsonResponse({"resource": resource})

        assert api_reverse("file-detail", version=1, resource="reports/annual.pdf") == (
            "/api/v1/files/reports/annual.pdf/"
        )

    def test_custom_path_converter_to_url_is_used(self):
        class LowercaseConverter:
            regex = "[a-z]+"

            def to_python(self, value):
                return value

            def to_url(self, value):
                return str(value).lower()

        register_converter(LowercaseConverter, "lowercase")

        @endpoint("items/<lowercase:code>/", version=1, view_name="item-detail")
        def item_detail(request, code):
            return JsonResponse({"code": code})

        assert api_reverse("item-detail", version=1, code="ABC") == (
            "/api/v1/items/abc/"
        )

    def test_kwarg_with_backslash_not_treated_as_regex_escape(self):
        """Ensure parameters with backslashes don't trigger regex escape sequences."""

        @endpoint("docs/<slug>/", version=1, view_name="doc-detail")
        def doc_detail(request, slug):
            return JsonResponse({"slug": slug})

        # Parameter containing backslash should be literal, not regex escape sequence
        url = api_reverse("doc-detail", version=1, slug=r"path\to\file")
        assert url == "/api/v1/docs/path%5Cto%5Cfile/"

    def test_kwarg_with_dollar_sign_not_treated_as_regex_group(self):
        """Ensure parameters with $ don't trigger regex group references."""

        @endpoint("items/<name>/", version=1, view_name="item-detail")
        def item_detail(request, name):
            return JsonResponse({"name": name})

        # Parameter containing $ should be literal, not regex group reference
        url = api_reverse("item-detail", version=1, name="price$5")
        assert url == "/api/v1/items/price$5/"

    def test_kwarg_with_regex_metacharacters(self):
        """Ensure all regex metacharacters are escaped in parameters."""

        @endpoint("search/<query>/", version=1, view_name="search-results")
        def search(request, query):
            return JsonResponse({"query": query})

        # Test various regex metacharacters
        test_cases = [
            ("(pattern)", "/api/v1/search/(pattern)/"),
            ("[abc]", "/api/v1/search/%5Babc%5D/"),
            ("a.b", "/api/v1/search/a.b/"),
            ("a*b", "/api/v1/search/a*b/"),
            ("a+b", "/api/v1/search/a+b/"),
            ("a?b", "/api/v1/search/a%3Fb/"),
            ("a|b", "/api/v1/search/a%7Cb/"),
            ("a{2}", "/api/v1/search/a%7B2%7D/"),
        ]
        for query, expected_url in test_cases:
            url = api_reverse("search-results", version=1, query=query)
            assert url == expected_url, f"Failed for query={query!r}"


def test_regex_backed_urlpattern_uses_django_reverse():
    """DRF-style RegexPattern routes can be reversed with named groups."""

    def view(request, pk):
        return JsonResponse({"pk": pk})

    pattern = re_path(
        r"^api/v2/orders/(?P<pk>[0-9]+)/$",
        view,
        name="regex-order-detail",
    )
    registry.register_urlpattern(
        pattern,
        source_version=2,
        route_version=2,
        logical_endpoint="orders:regex-order-detail",
    )

    assert api_reverse("regex-order-detail", version=2, pk=42) == ("/api/v2/orders/42/")
    with pytest.raises(NoReverseMatch):
        api_reverse("regex-order-detail", version=2, pk="not-an-integer")


def test_explicit_version_rejects_duplicate_view_names():
    """Exact-version reversal must not silently pick an arbitrary route."""

    def view(request):
        return JsonResponse({})

    registry.register_urlpattern(
        re_path(r"^api/v1/orders/$", view, name="duplicate-route"),
        source_version=1,
        route_version=1,
    )
    registry.register_urlpattern(
        re_path(r"^api/v1/shipments/$", view, name="duplicate-route"),
        source_version=1,
        route_version=1,
    )

    with pytest.raises(NoReverseMatch, match="registered more than once"):
        api_reverse("duplicate-route", version=1)


def test_api_reverse_percent_encodes_reserved_path_characters_for_round_trip():
    @endpoint("search/<str:query>/", version=1, view_name="search-query")
    def search(request, query):
        return JsonResponse({"query": query})

    url = api_reverse("search-query", version=1, query="a?b")
    response = Client().get(url)

    assert response.status_code == 200
    assert response.json() == {"query": "a?b"}


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [
        ("header", "/api/orders/"),
        ("hostname", "/api/orders/"),
        ("query", "/api/orders/?version=2"),
    ],
)
def test_api_reverse_uses_the_selected_non_path_transport(scheme, expected):
    @endpoint("orders/", versions=[2], view_name="negotiated-orders")
    def orders(request):
        return JsonResponse({})

    with override_settings(
        API_VERSIONING_SCHEME=scheme,
        API_BASE_PATH="api/v{version}/",
        API_UNVERSIONED_BASE_PATH="api/",
        API_VERSIONING_QUERY_PARAMETER="version",
    ):
        assert api_reverse("negotiated-orders", version=2) == expected


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [
        ("header", "https://api.example.com/api/posts/"),
        ("hostname", "https://api.example.com/api/posts/"),
        ("query", "https://api.example.com/api/posts/?version=2"),
    ],
)
def test_format_negotiated_url_recovers_version_from_concrete_route(scheme, expected):
    from django_api_versioning.reverse import format_negotiated_url

    with override_settings(
        API_VERSIONING_SCHEME=scheme,
        API_BASE_PATH="api/v{version}/",
        API_UNVERSIONED_BASE_PATH="api/",
        API_VERSIONING_QUERY_PARAMETER="version",
    ):
        assert (
            format_negotiated_url(
                "https://api.example.com/api/v2/posts/",
                version=None,
            )
            == expected
        )


def test_api_reverse_uses_urlpattern_defaults_for_missing_path_parameters():
    """Django URLPattern defaults should satisfy omitted converter parameters."""

    def view(request, pk):
        return JsonResponse({"pk": pk})

    pattern = path(
        "api/v1/orders/<int:pk>/",
        view,
        {"pk": 42, "format": "json"},
        name="default-order-detail",
    )
    registry.register_urlpattern(
        pattern,
        source_version=1,
        route_version=1,
        logical_endpoint="orders:default-order-detail",
    )

    assert api_reverse("default-order-detail", version=1) == (
        "/api/v1/orders/42/"
    )

    # A path parameter can override its URLPattern default, as in Django reverse().
    assert api_reverse("default-order-detail", version=1, pk=43) == (
        "/api/v1/orders/43/"
    )

    # Non-path default kwargs must still match the URLPattern defaults.
    with pytest.raises(NoReverseMatch, match="conflict with URL defaults"):
        api_reverse("default-order-detail", version=1, format="xml")
