"""Lifecycle fallback version grammar regression tests."""

import pytest
from django.http import HttpResponseNotFound
from django.test import RequestFactory

from django_api_versioning.lifecycle import LifecycleMiddleware, _extract_version
from django_api_versioning.settings import api_settings


@pytest.mark.parametrize("version_text", ["٣", "３", "𝟛"])
def test_unresolved_non_ascii_path_version_does_not_apply_ascii_lifecycle_policy(
    monkeypatch, version_text
):
    """A malformed Unicode version segment must not turn a 404 into a 410."""
    monkeypatch.setitem(
        api_settings.API_VERSION_LIFECYCLE,
        3,
        {"status": "retired", "sunset": "2000-01-01"},
    )
    request = RequestFactory().get(f"/api/v{version_text}/missing")
    request.version = None

    def not_found(_request):
        return HttpResponseNotFound("not found")

    response = LifecycleMiddleware(not_found)(request)

    assert response.status_code == 404
    assert response.content == b"not found"


@pytest.mark.parametrize("version_text", ["٣", "３", "𝟛"])
def test_request_version_does_not_accept_non_ascii_decimal_digits(version_text):
    """String request.version values follow the same ASCII grammar as paths."""
    request = RequestFactory().get("/unrelated/")
    request.version = version_text
    request.resolver_match = None

    assert _extract_version(request) is None


def test_negative_integer_request_version_is_not_an_api_version():
    """Integer request.version values must respect the non-negative contract."""
    request = RequestFactory().get("/unrelated/")
    request.version = -1
    request.resolver_match = None

    assert _extract_version(request) is None
