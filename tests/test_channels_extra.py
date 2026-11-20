import pytest
from django.test import RequestFactory
from urllib.parse import urlencode

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


def test_invalid_resolver_match_falls_back_to_request_version():
    request = RequestFactory().get("/users")
    request.resolver_match = type("M", (), {"kwargs": {"version": "invalid"}})()
    request.version = 7

    assert extract_version(request, ["path"]) == 7


def test_invalid_resolver_match_without_request_version_returns_none():
    request = RequestFactory().get("/users")
    request.resolver_match = type("M", (), {"kwargs": {"version": "invalid"}})()

    assert extract_version(request, ["path"]) is None


def test_repeated_v_prefix_in_header_is_rejected():
    request = RequestFactory().get("/users", HTTP_ACCEPT_VERSION="vv4")

    assert extract_version(request, ["header"]) is None


def test_repeated_v_prefix_in_query_is_rejected():
    request = RequestFactory().get("/users?version=vv5")

    assert extract_version(request, ["query"]) is None


def test_invalid_header_falls_through_to_query_channel():
    request = RequestFactory().get(
        "/users?version=5",
        HTTP_ACCEPT_VERSION="vv4",
    )

    assert extract_version(request, ["header", "query"]) == 5



@pytest.mark.parametrize("channel,value", [
    ("path", "-1"),
    ("path", "v-1"),
    ("path", "+2"),
    ("path", "1_0"),
    ("header", "-1"),
    ("header", "v-1"),
    ("header", "+2"),
    ("header", "v+2"),
    ("header", "1_0"),
    ("query", "-1"),
    ("query", "v-1"),
    ("query", "+2"),
    ("query", "1_0"),
])
def test_version_channels_reject_non_decimal_integer_syntax(channel, value):
    """Channel values must follow the documented non-negative decimal grammar."""
    if channel == "path":
        request = RequestFactory().get("/users")
        request.resolver_match = type(
            "M", (), {"kwargs": {"version": value}}
        )()
        request.version = None
    elif channel == "header":
        request = RequestFactory().get("/users", HTTP_ACCEPT_VERSION=value)
    else:
        request = RequestFactory().get("/users?" + urlencode({"version": value}))

    assert extract_version(request, [channel]) is None


def test_version_channels_reject_non_ascii_decimal_digits():
    request = RequestFactory().get("/users", HTTP_ACCEPT_VERSION="v٣")

    assert extract_version(request, ["header"]) is None
