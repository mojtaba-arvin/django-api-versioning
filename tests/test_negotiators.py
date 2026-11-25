"""Focused contracts for the internal transport negotiators."""

import pytest
from django.test import RequestFactory, override_settings

from django_api_versioning.negotiators import (
    HeaderNegotiator,
    HostnameNegotiator,
    PathNegotiator,
    QueryNegotiator,
    _UnsupportedVersion,
)


def test_path_negotiator_parses_only_the_configured_route_template():
    negotiator = PathNegotiator("api/v{version}/", maximum_version=3)

    assert negotiator.negotiate("/api/v2/orders/") == 2
    assert negotiator.negotiate("/health/") is None
    assert negotiator.negotiate("/api/v999999999999999999/orders/") == -1


def test_path_negotiator_matches_long_versions_without_integer_conversion():
    negotiator = PathNegotiator("api/v{version}/")

    assert negotiator.matches("/api/v" + ("9" * 5000) + "/orders/")
    assert not negotiator.matches("/health/")


def test_header_negotiator_selects_the_preferred_accept_version():
    request = RequestFactory().get(
        "/api/orders/",
        HTTP_ACCEPT="application/json; version=2; q=0.9, text/csv; version=3; q=0.4",
    )

    assert HeaderNegotiator("Accept-Version").negotiate(request) == 2


def test_query_negotiator_rejects_duplicate_values():
    request = RequestFactory().get("/api/orders/?version=1&version=2")

    with pytest.raises(ValueError, match="must appear once"):
        QueryNegotiator("version").negotiate(request)


@override_settings(ALLOWED_HOSTS=["xn--bcher-kva.example"])
def test_hostname_negotiator_normalizes_idna_and_uses_exact_mapping():
    request = RequestFactory().get("/api/orders/", HTTP_HOST="xn--bcher-kva.example")

    assert HostnameNegotiator({"bücher.example": 2}).negotiate(request) == 2


@override_settings(ALLOWED_HOSTS=["other.example"])
def test_hostname_negotiator_rejects_an_unmapped_allowed_host():
    request = RequestFactory().get("/api/orders/", HTTP_HOST="other.example")

    with pytest.raises(_UnsupportedVersion):
        HostnameNegotiator({"v2.api.example": 2}).negotiate(request)
