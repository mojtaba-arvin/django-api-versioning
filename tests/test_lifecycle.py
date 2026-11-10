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
