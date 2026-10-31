import pytest
from django.http import JsonResponse
from django.urls import NoReverseMatch

from django_api_versioning import api_reverse
from django_api_versioning.decorators import endpoint
from django_api_versioning.exceptions import AmbiguousVersionError
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
