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
