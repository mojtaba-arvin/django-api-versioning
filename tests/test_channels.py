from django.test import RequestFactory

from django_api_versioning.channels import extract_version


def test_path_channel():
    request = RequestFactory().get("/api/v3/users")
    request.resolver_match = type("M", (), {"kwargs": {"version": "3"}})()
    assert extract_version(request, ["path"]) == 3


def test_header_channel():
    request = RequestFactory().get("/users", HTTP_ACCEPT_VERSION="v4")
    assert extract_version(request, ["header"]) == 4


def test_query_channel():
    request = RequestFactory().get("/users?version=5")
    assert extract_version(request, ["query"]) == 5


def test_priority_order():
    request = RequestFactory().get(
        "/api/v2/users?version=5",
        HTTP_ACCEPT_VERSION="v4",
    )
    request.resolver_match = type("M", (), {"kwargs": {"version": "2"}})()
    assert extract_version(request, ["header", "path", "query"]) == 4
