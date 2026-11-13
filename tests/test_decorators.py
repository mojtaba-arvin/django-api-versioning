import logging
import sys
import subprocess
import json

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


class TestIssue0VersionAboveMax:
    """Issue 1: Versions above API_MAX_VERSION must be rejected."""

    def test_version_above_max_raises(self, versions_1_to_5):
        """Single version above max must raise InvalidVersionError."""
        with pytest.raises(InvalidVersionError, match="above the maximum allowed"):

            @endpoint("x", version=6)
            def x(request):
                pass

    def test_version_equals_max_succeeds(self, versions_1_to_5):
        """version == API_MAX_VERSION must succeed and register exactly v5."""
        @endpoint("y", version=5)
        def y(request):
            return JsonResponse({})

        assert _routes() == {"api/v5/y"}

    def test_versions_list_above_max_raises(self, versions_1_to_5):
        """Explicit versions list with any version above max must raise."""
        with pytest.raises(InvalidVersionError, match="above the maximum allowed"):

            @endpoint("z", versions=[2, 3, 6])
            def z(request):
                pass

    def test_invalid_versions_list_does_not_partially_register(self, versions_1_to_5):
        """Failed registration with invalid versions must not leave partial routes."""
        initial_count = len(registry.urlpatterns)

        with pytest.raises(InvalidVersionError):

            @endpoint("partial", versions=[2, 3, 6])
            def partial(request):
                pass

        # Registry must not have any new routes
        assert len(registry.urlpatterns) == initial_count


class TestIssue0SimultaneousVersionAndVersions:
    """Issue 2: Mutual exclusivity of 'version' and 'versions' parameters."""

    def test_both_version_and_versions_raises_with_message(self):
        """Providing both version and versions must raise VersionRangeError."""
        with pytest.raises(
            VersionRangeError, match="Use either 'version' or 'versions', not both"
        ):
            endpoint("x", version=1, versions=[2])

    def test_registration_incomplete_after_mutual_exclusive_violation(self):
        """Failed registration due to mutual exclusivity must leave no routes."""
        initial_count = len(registry.urlpatterns)

        with pytest.raises(VersionRangeError):
            endpoint("x", version=1, versions=[2])

        # Registry must not have any new routes
        assert len(registry.urlpatterns) == initial_count


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


class TestIssue1BooleanVersions:
    """Issue 3: Boolean versions must be rejected explicitly."""

    def test_boolean_true_version_raises(self):
        """True is a bool subclass of int but must be rejected."""
        with pytest.raises(VersionTypeError, match="Version must be an integer"):

            @endpoint("x", version=True)
            def x(request):
                pass

    def test_boolean_false_version_raises(self):
        """False is a bool subclass of int but must be rejected."""
        with pytest.raises(VersionTypeError, match="Version must be an integer"):

            @endpoint("x", version=False)
            def x(request):
                pass

    def test_boolean_in_explicit_versions_true_raises(self):
        """True in explicit versions list must be rejected."""
        with pytest.raises(VersionTypeError, match="Version must be an integer"):

            @endpoint("x", versions=[1, True, 3])
            def x(request):
                pass

    def test_boolean_in_explicit_versions_false_raises(self):
        """False in explicit versions list must be rejected."""
        with pytest.raises(VersionTypeError, match="Version must be an integer"):

            @endpoint("x", versions=[1, False, 3])
            def x(request):
                pass


class TestIssue2StringVersions:
    """Issue 4: String version values must be rejected."""

    def test_string_version_raises(self):
        """String "2" must be rejected."""
        with pytest.raises(VersionTypeError, match="Version must be an integer"):

            @endpoint("x", version="2")
            def x(request):
                pass

    def test_zero_padded_string_version_raises(self):
        """Zero-padded string "02" must be rejected."""
        with pytest.raises(VersionTypeError, match="Version must be an integer"):

            @endpoint("x", version="02")
            def x(request):
                pass

    def test_float_version_raises(self):
        """Float 2.0 must be rejected even though it equals 2."""
        with pytest.raises(VersionTypeError, match="Version must be an integer"):

            @endpoint("x", version=2.0)
            def x(request):
                pass

    def test_string_in_explicit_versions_raises(self):
        """String in versions list must be rejected."""
        with pytest.raises(VersionTypeError, match="Version must be an integer"):

            @endpoint("x", versions=[1, "2", 3])
            def x(request):
                pass

    def test_float_in_explicit_versions_raises(self):
        """Float in versions list must be rejected."""
        with pytest.raises(VersionTypeError, match="Version must be an integer"):

            @endpoint("x", versions=[1, 2.0, 3])
            def x(request):
                pass


class TestIssue5VerRangeValidation:
    """Issue 5: ver_range must validate input types and range order."""

    def test_ver_range_boolean_start_raises(self):
        """Boolean start must be rejected with VersionTypeError."""
        with pytest.raises(VersionTypeError, match="must be an integer"):
            ver_range(True, 3)

    def test_ver_range_boolean_end_raises(self):
        """Boolean end must be rejected with VersionTypeError."""
        with pytest.raises(VersionTypeError, match="must be an integer"):
            ver_range(1, False)

    def test_ver_range_float_start_raises(self):
        """Float start must be rejected with VersionTypeError."""
        with pytest.raises(VersionTypeError, match="must be an integer"):
            ver_range(1.0, 3)

    def test_ver_range_float_end_raises(self):
        """Float end must be rejected with VersionTypeError."""
        with pytest.raises(VersionTypeError, match="must be an integer"):
            ver_range(1, 3.0)

    def test_ver_range_string_start_raises(self):
        """String start must be rejected with VersionTypeError."""
        with pytest.raises(VersionTypeError, match="must be an integer"):
            ver_range("1", 3)

    def test_ver_range_string_end_raises(self):
        """String end must be rejected with VersionTypeError."""
        with pytest.raises(VersionTypeError, match="must be an integer"):
            ver_range(1, "3")


class TestIssue6ViewInstanceRejection:
    """Issue 6: View instances must be rejected, only classes accepted."""

    def test_view_instance_in_registry_raises(self):
        """Passing View instance to registry.register must raise TypeError."""
        from django.views import View

        class MyView(View):
            def get(self, request):
                return JsonResponse({})

        with pytest.raises(TypeError, match="Pass the view class 'MyView'"):
            registry.register("api/v1/x", MyView())

    def test_view_class_in_registry_succeeds(self):
        """Passing View class to registry.register must succeed."""
        from django.views import View

        class MyView(View):
            def get(self, request):
                return JsonResponse({})

        registry.register("api/v1/myview", MyView)
        assert any(str(p.pattern) == "api/v1/myview" for p in registry.urlpatterns)
        assert any(
            p.callback.view_class is MyView for p in registry.urlpatterns
            if hasattr(p.callback, "view_class")
        )

    def test_view_as_view_succeeds(self):
        """Passing View.as_view() to registry.register must succeed."""
        from django.views import View

        class MyView(View):
            def get(self, request):
                return JsonResponse({})

        route = "api/v1/test"
        registry.register(route, MyView.as_view())
        assert any(str(p.pattern) == route for p in registry.urlpatterns)


class TestIssue7OverrideSettingsAfterImport:
    """Issue 7: Package settings are initialized at import time.

    override_settings(API_MAX_VERSION=...) changes Django settings, not the
    pre-loaded api_settings object. This test documents the current behavior
    and verifies that late settings changes do not silently affect decorators.
    """

    def test_override_settings_does_not_affect_cached_api_settings(self):
        """Settings changed after import do not affect api_settings."""
        from django.test import override_settings

        # At this point, settings module is imported with cached api_settings.
        # api_settings reflects Django settings at import time.
        original_max = settings.API_MAX_VERSION

        with override_settings(API_MAX_VERSION=original_max + 10):
            # override_settings changes Django settings, not api_settings
            assert settings.API_MAX_VERSION == original_max, (
                "api_settings was initialized at import time; "
                "override_settings does not rebuild it"
            )

    def test_override_settings_late_does_not_enable_new_version(self):
        """Decorators registered after override_settings still use original settings."""
        from django.test import override_settings

        original_max = settings.API_MAX_VERSION

        # Settings change after package import
        with override_settings(API_MAX_VERSION=original_max + 5):
            # But decorator validation still uses cached settings from import time
            with pytest.raises(InvalidVersionError):

                @endpoint("late", version=original_max + 5)
                def late_endpoint(request):
                    pass

    def test_settings_before_import_are_honored(self):
        """This test documents the correct usage: set Django settings before import."""
        # This test is informational. In practice:
        # 1. Django settings must be configured first
        # 2. Then import django_api_versioning modules
        # 3. api_settings will reflect those Django settings
        #
        # See documentation for correct patterns.
        assert settings.API_MIN_VERSION <= settings.API_MAX_VERSION
