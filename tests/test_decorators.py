import logging

import pytest
from django.http import JsonResponse

from django_api_versioning.decorators import endpoint, ver_range
from django_api_versioning.exceptions import (
    InvalidVersionError,
    VersionRangeError,
    VersionTypeError,
)
from django_api_versioning.registry import registry
from django_api_versioning.settings import api_settings as settings


@pytest.fixture
def versions_1_to_5():
    old_min, old_max = settings.API_MIN_VERSION, settings.API_MAX_VERSION
    settings.API_MIN_VERSION, settings.API_MAX_VERSION = 1, 5
    yield
    settings.API_MIN_VERSION, settings.API_MAX_VERSION = old_min, old_max


def _routes():
    return {str(p.pattern) for p in registry.urlpatterns}


class TestVerRange:
    def test_inclusive(self):
        assert ver_range(1, 3) == [1, 2, 3]

    def test_single(self):
        assert ver_range(3, 3) == [3]

    def test_start_greater_than_end_raises(self):
        with pytest.raises(VersionRangeError):
            ver_range(5, 2)


class TestSegment:
    def test_registers_all_versions_from_n_to_max(self, versions_1_to_5):
        @endpoint("users", version=3)
        def users(request):
            return JsonResponse({})

        assert _routes() == {
            "api/v3/users",
            "api/v4/users",
            "api/v5/users",
        }

    def test_below_min_version_warns_and_skips(self, versions_1_to_5, caplog):
        with caplog.at_level(logging.WARNING):

            @endpoint("users", version=0)
            def users(request):
                return JsonResponse({})

        assert _routes() == set()
        assert "API_MIN_VERSION" in caplog.text


class TestExplicitVersions:
    def test_single_version(self, versions_1_to_5):
        @endpoint("beta", versions=[3])
        def beta(request):
            return JsonResponse({})

        assert _routes() == {"api/v3/beta"}

    def test_scattered_versions(self, versions_1_to_5):
        @endpoint("audit", versions=[2, 4])
        def audit(request):
            return JsonResponse({})

        assert _routes() == {"api/v2/audit", "api/v4/audit"}

    def test_ver_range_as_versions(self, versions_1_to_5):
        @endpoint("legacy", versions=ver_range(1, 3))
        def legacy(request):
            return JsonResponse({})

        assert _routes() == {
            "api/v1/legacy",
            "api/v2/legacy",
            "api/v3/legacy",
        }


class TestValidation:
    def test_both_version_and_versions_raises(self):
        with pytest.raises(VersionRangeError):
            endpoint("x", version=3, versions=[3])

    def test_non_int_version_raises(self):
        with pytest.raises(VersionTypeError):

            @endpoint("x", version="3")
            def x(request):
                pass

    def test_version_above_max_raises(self, versions_1_to_5):
        with pytest.raises(InvalidVersionError):

            @endpoint("x", version=10)
            def x(request):
                pass

    def test_versions_above_max_raises(self, versions_1_to_5):
        with pytest.raises(InvalidVersionError):

            @endpoint("x", versions=[2, 10])
            def x(request):
                pass


class TestUnversioned:
    def test_unversioned_registers_single_route(self):
        @endpoint("health")
        def health(request):
            return JsonResponse({})

        assert _routes() == {"health"}


class TestMetadata:
    def test_app_name_prefixes_route(self, versions_1_to_5):
        @endpoint("users", version=3, app_name="accounts")
        def users(request):
            return JsonResponse({})

        assert "api/v3/accounts/users" in _routes()

    def test_view_name_is_registered(self, versions_1_to_5):
        @endpoint("users", version=3, view_name="users-list")
        def users(request):
            return JsonResponse({})

        names = {p.name for p in registry.urlpatterns if p.name}
        assert "users-list" in names


class TestRepeatedDecorator:
    def test_same_view_registered_at_multiple_change_points(self, versions_1_to_5):
        @endpoint("x", version=2)
        @endpoint("x", version=4)
        def x_b(request):
            return JsonResponse({"impl": "B"})

        v2_cb = None
        v4_cb = None
        for p in registry.urlpatterns:
            rv = getattr(p, "_django_api_versioning_route_version", None)
            if rv == 2:
                v2_cb = p.callback
            elif rv == 4:
                v4_cb = p.callback
        assert v2_cb is not None
        assert v4_cb is not None
        assert v2_cb is v4_cb
