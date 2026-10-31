from django.test import RequestFactory

from django_api_versioning.channels import extract_version


def test_returns_none_when_no_channel_yields_a_version():
    request = RequestFactory().get("/users")
    assert extract_version(request, ["path", "header", "query"]) is None


def test_unknown_channel_is_ignored():
    request = RequestFactory().get("/users?version=3")
    assert extract_version(request, ["unknown", "query"]) == 3


def test_header_without_v_prefix():
    request = RequestFactory().get("/users", HTTP_ACCEPT_VERSION="3")
    assert extract_version(request, ["header"]) == 3


def test_header_with_uppercase_v():
    request = RequestFactory().get("/users", HTTP_ACCEPT_VERSION="V4")
    assert extract_version(request, ["header"]) == 4


def test_invalid_header_value_returns_none():
    request = RequestFactory().get("/users", HTTP_ACCEPT_VERSION="abc")
    assert extract_version(request, ["header"]) is None


def test_invalid_query_value_returns_none():
    request = RequestFactory().get("/users?version=abc")
    assert extract_version(request, ["query"]) is None
