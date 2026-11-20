from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from django_api_versioning.negotiation import VersionNegotiationMiddleware


def _dispatch(path, **headers):
    request = RequestFactory().get(path, **headers)
    middleware = VersionNegotiationMiddleware(
        lambda req: HttpResponse(req.path_info)
    )
    return request, middleware(request)


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_accept_version_header_rewrites_before_url_resolution():
    request, response = _dispatch(
        "/api/orders/", HTTP_ACCEPT_VERSION="2"
    )

    assert response.status_code == 200
    assert response.content == b"/api/v2/orders/"
    assert request.original_path_info == "/api/orders/"
    assert request.api_version == 2
    assert request.version == "2"
    assert "Accept-Version" in response["Vary"]
    assert "Accept" in response["Vary"]


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_accept_media_type_version_parameter_is_supported():
    _, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT="application/json; version=3",
    )

    assert response.status_code == 200
    assert response.content == b"/api/v3/orders/"


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_conflicting_accept_media_type_versions_are_rejected():
    _, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT="application/json; version=2, text/csv; version=3",
    )

    assert response.status_code == 400


@override_settings(
    API_VERSIONING_SCHEME="query",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_VERSIONING_QUERY_PARAMETER="version",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_query_parameter_rewrites_before_url_resolution():
    request, response = _dispatch("/api/orders/?version=3")

    assert response.status_code == 200
    assert response.content == b"/api/v3/orders/"
    assert request.api_version == 3


@override_settings(
    API_VERSIONING_SCHEME="query",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_duplicate_query_version_parameter_is_rejected():
    _, response = _dispatch("/api/orders/?version=1&version=2")

    assert response.status_code == 400


@override_settings(
    API_VERSIONING_SCHEME="hostname",
    API_VERSIONING_HOSTS={"v1.api.example.com": 1, "v2.api.example.com": 2},
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
    ALLOWED_HOSTS=["v1.api.example.com", "v2.api.example.com"],
)
def test_hostname_mapping_rewrites_only_from_exact_allowed_hosts():
    request, response = _dispatch(
        "/api/orders/", HTTP_HOST="v2.api.example.com"
    )

    assert response.status_code == 200
    assert response.content == b"/api/v2/orders/"
    assert request.api_version == 2


@override_settings(
    API_VERSIONING_SCHEME="hostname",
    API_VERSIONING_HOSTS={"v1.api.example.com": 1},
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
    ALLOWED_HOSTS=["v1.api.example.com", "other.example.com"],
)
def test_unmapped_hostname_is_not_acceptable():
    _, response = _dispatch("/api/orders/", HTTP_HOST="other.example.com")

    assert response.status_code == 406


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_missing_version_without_default_is_rejected():
    _, response = _dispatch("/api/orders/")

    assert response.status_code == 400


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_DEFAULT_VERSION=1,
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_configured_default_version_is_used_when_header_is_missing():
    request, response = _dispatch("/api/orders/")

    assert response.status_code == 200
    assert response.content == b"/api/v1/orders/"
    assert request.api_version == 1


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_malformed_version_is_rejected():
    _, response = _dispatch(
        "/api/orders/", HTTP_ACCEPT_VERSION="2.5"
    )

    assert response.status_code == 400


@override_settings(
    API_VERSIONING_SCHEME="query",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_out_of_range_version_returns_not_acceptable():
    _, response = _dispatch("/api/orders/?version=4")

    assert response.status_code == 406


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_non_api_paths_pass_through_unchanged():
    request, response = _dispatch(
        "/health/", HTTP_ACCEPT_VERSION="2"
    )

    assert response.status_code == 200
    assert response.content == b"/health/"
    assert not hasattr(request, "api_version")


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_versioned_path_is_not_accepted_in_non_path_mode():
    _, response = _dispatch(
        "/api/v1/orders/", HTTP_ACCEPT_VERSION="2"
    )

    assert response.status_code == 400


@override_settings(
    API_VERSIONING_SCHEME="path",
    API_BASE_PATH="api/v{version}/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_path_mode_exposes_the_route_version_to_django_views():
    request, response = _dispatch("/api/v2/orders/")

    assert response.status_code == 200
    assert request.api_version == 2
    assert request.version == "2"


@override_settings(
    API_VERSIONING_SCHEME="query",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_non_path_transports_reject_v_prefix_values():
    _, response = _dispatch("/api/orders/?version=v2")

    assert response.status_code == 400
