from datetime import date, timedelta

from django.http import HttpResponse
from django.test import RequestFactory

from django_api_versioning.lifecycle import LifecycleMiddleware
from django_api_versioning.settings import api_settings as settings

# Dates relative to "today" so the tests never depend on the current date.
FUTURE = (date.today() + timedelta(days=365)).isoformat()
PAST = (date.today() - timedelta(days=365)).isoformat()


def _request(version: str):
    request = RequestFactory().get(f"/api/v{version}/users")
    request.version = version
    return request


def test_deprecated_version_gets_headers(monkeypatch):
    monkeypatch.setitem(
        settings.API_VERSION_LIFECYCLE,
        2,
        {"status": "deprecated", "sunset": FUTURE},
    )
    middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(_request("2"))

    assert response["Deprecation"] == "true"
    assert "Sunset" in response


def test_deprecated_without_sunset_only_deprecation(monkeypatch):
    monkeypatch.setitem(
        settings.API_VERSION_LIFECYCLE,
        2,
        {"status": "deprecated"},
    )
    middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(_request("2"))

    assert response["Deprecation"] == "true"
    assert "Sunset" not in response


def test_retired_version_returns_410(monkeypatch):
    monkeypatch.setitem(
        settings.API_VERSION_LIFECYCLE,
        1,
        {"status": "retired", "sunset": PAST},
    )
    middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(_request("1"))

    assert response.status_code == 410


def test_future_sunset_with_retired_status_still_serves(monkeypatch):
    """status=retired but sunset is in the future -> serve normally with no 410."""
    monkeypatch.setitem(
        settings.API_VERSION_LIFECYCLE,
        1,
        {"status": "retired", "sunset": FUTURE},
    )
    middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(_request("1"))

    assert response.status_code == 200


def test_active_version_has_no_headers(monkeypatch):
    monkeypatch.setitem(settings.API_VERSION_LIFECYCLE, 3, {"status": "active"})
    middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(_request("3"))

    assert "Deprecation" not in response
    assert "Sunset" not in response


def test_unknown_version_is_passthrough(monkeypatch):
    monkeypatch.setitem(settings.API_VERSION_LIFECYCLE, 3, {"status": "active"})
    middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(_request("99"))

    assert response.status_code == 200
    assert "Deprecation" not in response


def test_request_without_version_is_passthrough():
    request = RequestFactory().get("/some/path")
    middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(request)

    assert response.status_code == 200


def test_invalid_sunset_date_is_ignored(monkeypatch, caplog):
    monkeypatch.setitem(
        settings.API_VERSION_LIFECYCLE,
        2,
        {"status": "deprecated", "sunset": "not-a-date"},
    )
    middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
    response = middleware(_request("2"))

    assert response["Deprecation"] == "true"
    assert "Invalid sunset date" in caplog.text


# Tests for _extract_version() and _extract_version_from_path()
class TestVersionExtraction:
    """Focused unit tests for version extraction logic."""

    def test_extract_version_prefers_request_version(self):
        """Version extraction prefers request.version when set."""
        from django_api_versioning.lifecycle import _extract_version

        request = RequestFactory().get("/api/v2/users/")
        request.version = "3"
        # Even though path says v2, request.version should win
        version = _extract_version(request)
        assert version == 3

    def test_extract_version_prefers_resolver_match_kwargs(self):
        """Version extraction prefers resolver_match.kwargs["version"] over path."""
        from django_api_versioning.lifecycle import _extract_version
        from unittest.mock import Mock

        request = RequestFactory().get("/api/v2/users/")
        request.version = None
        request.resolver_match = Mock()
        request.resolver_match.kwargs = {"version": "4"}
        # resolver_match should be second priority
        version = _extract_version(request)
        assert version == 4

    def test_extract_version_falls_back_to_path(self):
        """Version extraction falls back to URL path when others are unavailable."""
        from django_api_versioning.lifecycle import _extract_version

        request = RequestFactory().get("/api/v2/users/")
        request.version = None
        request.resolver_match = None
        # Should extract version from path
        version = _extract_version(request)
        assert version == 2

    def test_extract_version_from_path_static_url(self):
        """Extract version from static URL path."""
        from django_api_versioning.lifecycle import _extract_version_from_path

        request = RequestFactory().get("/api/v1/users/")
        request.version = None
        version = _extract_version_from_path(request)
        assert version == 1

    def test_extract_version_multi_digit_version(self):
        """Extract multi-digit version numbers from path."""
        from django_api_versioning.lifecycle import _extract_version_from_path

        request = RequestFactory().get("/api/v42/users/")
        request.version = None
        version = _extract_version_from_path(request)
        assert version == 42

    def test_extract_version_with_url_parameters(self):
        """Version is extracted from prefix, not from URL parameters."""
        from django_api_versioning.lifecycle import _extract_version_from_path

        request = RequestFactory().get("/api/v2/users/42/")
        request.version = None
        # Should extract v2, not 42
        version = _extract_version_from_path(request)
        assert version == 2

    def test_extract_version_with_query_string(self):
        """Query string doesn't affect version extraction."""
        from django_api_versioning.lifecycle import _extract_version_from_path

        request = RequestFactory().get("/api/v2/users/?page=1&limit=10")
        request.version = None
        version = _extract_version_from_path(request)
        assert version == 2

    def test_extract_version_no_match_returns_none(self):
        """Returns None when path doesn't match API_BASE_PATH pattern."""
        from django_api_versioning.lifecycle import _extract_version_from_path

        request = RequestFactory().get("/unrelated/path/")
        request.version = None
        version = _extract_version_from_path(request)
        assert version is None

    def test_extract_version_invalid_version_format(self):
        """Returns None for non-numeric version strings."""
        from django_api_versioning.lifecycle import _extract_version_from_path

        request = RequestFactory().get("/api/vx/users/")
        request.version = None
        version = _extract_version_from_path(request)
        assert version is None

    def test_extract_version_anchored_pattern(self):
        """Version is only extracted from start of path, not middle."""
        from django_api_versioning.lifecycle import _extract_version_from_path

        # A path where "api/v2" appears but not at the start
        # This should not match (returns None)
        request = RequestFactory().get("/prefix/api/v2/users/")
        request.version = None
        version = _extract_version_from_path(request)
        # Should be None because pattern is anchored at ^
        assert version is None

    def test_extract_version_with_request_version_invalid(self):
        """Invalid request.version falls back to path extraction."""
        from django_api_versioning.lifecycle import _extract_version

        request = RequestFactory().get("/api/v2/users/")
        request.version = "not_a_number"
        version = _extract_version(request)
        # Should fall back to path and get 2
        assert version == 2

    def test_extract_version_empty_lifecycle_config(self):
        """Version extraction works even with empty lifecycle config."""
        from django_api_versioning.lifecycle import _extract_version

        request = RequestFactory().get("/api/v2/users/")
        request.version = None
        request.resolver_match = None
        version = _extract_version(request)
        # Should still extract from path
        assert version == 2

    def test_extract_version_no_resolver_match(self):
        """Handles missing resolver_match gracefully."""
        from django_api_versioning.lifecycle import _extract_version

        request = RequestFactory().get("/api/v1/users/")
        request.version = None
        # Don't set resolver_match at all
        version = _extract_version(request)
        assert version == 1

    def test_extract_version_precedence_order(self):
        """Verifies version extraction precedence: request.version > kwargs > path."""
        from django_api_versioning.lifecycle import _extract_version
        from unittest.mock import Mock

        # When all three are set, request.version wins
        request = RequestFactory().get("/api/v1/users/")
        request.version = "5"
        request.resolver_match = Mock()
        request.resolver_match.kwargs = {"version": "3"}
        version = _extract_version(request)
        assert version == 5

        # When request.version is None, kwargs wins
        request.version = None
        version = _extract_version(request)
        assert version == 3

        # When both are None, path wins
        request.resolver_match.kwargs = {}
        version = _extract_version(request)
        assert version == 1


# Tests for override_settings compatibility
class TestOverrideSettingsCompatibility:
    """Regression tests for override_settings compatibility (Bug: LifecycleMiddleware ignores override_settings)."""

    def test_override_settings_lifecycle_active_version(self):
        """override_settings(API_VERSION_LIFECYCLE) should affect middleware behavior."""
        from django.test import override_settings

        with override_settings(API_VERSION_LIFECYCLE={1: {"status": "active"}}):
            middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
            response = middleware(_request("1"))

            assert response.status_code == 200
            assert "Deprecation" not in response

    def test_override_settings_lifecycle_deprecated_version(self):
        """override_settings should apply deprecated status and Sunset header."""
        from django.test import override_settings

        with override_settings(
            API_VERSION_LIFECYCLE={2: {"status": "deprecated", "sunset": FUTURE}}
        ):
            middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
            response = middleware(_request("2"))

            assert response.status_code == 200
            assert response["Deprecation"] == "true"
            assert "Sunset" in response

    def test_override_settings_lifecycle_retired_past_sunset(self):
        """override_settings with past sunset should return 410."""
        from django.test import override_settings

        with override_settings(
            API_VERSION_LIFECYCLE={1: {"status": "retired", "sunset": PAST}}
        ):
            middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
            response = middleware(_request("1"))

            assert response.status_code == 410

    def test_override_settings_lifecycle_retired_future_sunset(self):
        """override_settings with future sunset should serve normally."""
        from django.test import override_settings

        with override_settings(
            API_VERSION_LIFECYCLE={1: {"status": "retired", "sunset": FUTURE}}
        ):
            middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
            response = middleware(_request("1"))

            assert response.status_code == 200
            assert "Deprecation" not in response

    def test_override_settings_lifecycle_empty_dict(self):
        """override_settings with empty lifecycle should pass through."""
        from django.test import override_settings

        with override_settings(API_VERSION_LIFECYCLE={}):
            middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
            response = middleware(_request("1"))

            assert response.status_code == 200
            assert "Deprecation" not in response

    def test_override_settings_lifecycle_removed(self):
        """After override_settings context ends, behavior should revert."""
        from django.test import override_settings

        # First, with override_settings: version 1 is retired
        with override_settings(
            API_VERSION_LIFECYCLE={1: {"status": "retired", "sunset": PAST}}
        ):
            middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
            response = middleware(_request("1"))
            assert response.status_code == 410

        # Then, outside context: version 1 uses cached settings (no lifecycle entry)
        middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
        response = middleware(_request("1"))
        assert response.status_code == 200
        assert "Deprecation" not in response

    def test_override_settings_base_path_extraction(self):
        """override_settings(API_BASE_PATH) should affect version extraction."""
        from django.test import override_settings
        from django_api_versioning.lifecycle import _extract_version_from_path

        with override_settings(API_BASE_PATH="svc/v{version}/"):
            request = RequestFactory().get("/svc/v2/things/")
            request.version = None
            version = _extract_version_from_path(request)
            assert version == 2

    def test_override_settings_base_path_extraction_custom_format(self):
        """override_settings with custom base path format should work."""
        from django.test import override_settings
        from django_api_versioning.lifecycle import _extract_version_from_path

        with override_settings(API_BASE_PATH="api/version-{version}/"):
            request = RequestFactory().get("/api/version-3/users/")
            request.version = None
            version = _extract_version_from_path(request)
            assert version == 3

    def test_override_settings_base_path_unchanged_outside_context(self):
        """Version extraction should revert after override_settings context."""
        from django.test import override_settings
        from django_api_versioning.lifecycle import _extract_version_from_path

        # With override_settings, custom path works
        with override_settings(API_BASE_PATH="svc/v{version}/"):
            request = RequestFactory().get("/svc/v2/things/")
            request.version = None
            version = _extract_version_from_path(request)
            assert version == 2

        # Outside override_settings, custom path doesn't match
        request = RequestFactory().get("/svc/v2/things/")
        request.version = None
        version = _extract_version_from_path(request)
        assert version is None  # Uses default api/v{version}/, doesn't match svc/

    def test_override_settings_lifecycle_multiple_versions(self):
        """override_settings with multiple lifecycle entries should work."""
        from django.test import override_settings

        with override_settings(
            API_VERSION_LIFECYCLE={
                1: {"status": "retired", "sunset": PAST},
                2: {"status": "deprecated", "sunset": FUTURE},
                3: {"status": "active"},
            }
        ):
            middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))

            # Version 1: retired with past sunset -> 410
            response = middleware(_request("1"))
            assert response.status_code == 410

            # Version 2: deprecated with future sunset -> 200 with headers
            response = middleware(_request("2"))
            assert response.status_code == 200
            assert response["Deprecation"] == "true"

            # Version 3: active -> 200 with no headers
            response = middleware(_request("3"))
            assert response.status_code == 200
            assert "Deprecation" not in response

    def test_override_settings_with_extract_version_precedence(self):
        """Version extraction precedence should work with override_settings."""
        from django.test import override_settings
        from django_api_versioning.lifecycle import _extract_version
        from unittest.mock import Mock

        with override_settings(API_BASE_PATH="custom/v{version}/"):
            # request.version takes precedence even with custom base path
            request = RequestFactory().get("/custom/v1/things/")
            request.version = "5"
            request.resolver_match = None
            version = _extract_version(request)
            assert version == 5

            # Falls back to custom path when request.version is None
            request.version = None
            version = _extract_version(request)
            assert version == 1

    def test_override_settings_deprecated_without_sunset(self):
        """override_settings with deprecated status but no sunset."""
        from django.test import override_settings

        with override_settings(API_VERSION_LIFECYCLE={2: {"status": "deprecated"}}):
            middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))
            response = middleware(_request("2"))

            assert response.status_code == 200
            assert response["Deprecation"] == "true"
            assert "Sunset" not in response

    def test_override_settings_lifecycle_and_base_path_together(self):
        """override_settings with both lifecycle and base path changes."""
        from django.test import override_settings
        from django_api_versioning.lifecycle import _extract_version

        with override_settings(
            API_BASE_PATH="svc/v{version}/",
            API_VERSION_LIFECYCLE={2: {"status": "retired", "sunset": PAST}},
        ):
            middleware = LifecycleMiddleware(lambda req: HttpResponse("ok"))

            # Extract version from overridden base path
            request = RequestFactory().get("/svc/v2/things/")
            request.version = None
            version = _extract_version(request)
            assert version == 2

            # Check lifecycle with extracted version
            response = middleware(request)
            assert response.status_code == 410
