"""Regression contracts for transport negotiation fallback configuration."""

from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory

import django_api_versioning.negotiation as negotiation_module


def test_path_mode_uses_one_as_default_version_digit_limit(monkeypatch):
    observed_maximums = []
    original = negotiation_module.PathNegotiator

    class RecordingPathNegotiator(original):
        def __init__(self, template, maximum_version=None):
            observed_maximums.append(maximum_version)
            super().__init__(template, maximum_version)

    monkeypatch.setattr(negotiation_module, "PathNegotiator", RecordingPathNegotiator)
    monkeypatch.setattr(
        negotiation_module,
        "django_settings",
        SimpleNamespace(
            API_VERSIONING_SCHEME="path",
            API_BASE_PATH="api/v{version}/",
        ),
    )
    monkeypatch.setattr(negotiation_module, "api_settings", SimpleNamespace())

    request = RequestFactory().get("/api/v2/orders/")
    response = negotiation_module.VersionNegotiationMiddleware(
        lambda current: HttpResponse("ok")
    )(request)

    assert response.status_code == 200
    assert request.api_version == 2
    assert observed_maximums == [1]
