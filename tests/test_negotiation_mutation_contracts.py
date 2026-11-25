"""Regression contracts for transport negotiation mutation survivors."""

from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory

import django_api_versioning.negotiation as negotiation_module


def test_path_mode_defaults_maximum_version_to_one(monkeypatch):
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
    assert not hasattr(request, "requested_api_version")
    assert not hasattr(request, "api_version")
    assert not hasattr(request, "version")
