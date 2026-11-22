import json

import pytest
from django.http import HttpResponse, JsonResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import path

from django_api_versioning.negotiation import (
    VersionNegotiationMiddleware,
    _header_version,
    _host_version,
    _normalize_hostname,
    _parse_accept_media_range,
    _parse_accept_parameter_value,
    _parse_version,
    _path_version,
    _split_quoted_header,
)


def _dispatch(path, **headers):
    request = RequestFactory().get(path, **headers)
    middleware = VersionNegotiationMiddleware(lambda req: HttpResponse(req.path_info))
    return request, middleware(request)


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_accept_version_header_rewrites_before_url_resolution():
    request, response = _dispatch("/api/orders/", HTTP_ACCEPT_VERSION="2")

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
    request, response = _dispatch("/api/orders/", HTTP_HOST="v2.api.example.com")

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
    _, response = _dispatch("/api/orders/", HTTP_ACCEPT_VERSION="2.5")

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
    request, response = _dispatch("/health/", HTTP_ACCEPT_VERSION="2")

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
    _, response = _dispatch("/api/v1/orders/", HTTP_ACCEPT_VERSION="2")

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


def _v1_order(request):
    return JsonResponse({"handler": "v1", "version": request.api_version})


def _v2_order(request):
    return JsonResponse({"handler": "v2", "version": request.api_version})


urlpatterns = [
    path("api/v1/orders/", _v1_order),
    path("api/v2/orders/", _v2_order),
]


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=["django_api_versioning.negotiation.VersionNegotiationMiddleware"],
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=2,
    ALLOWED_HOSTS=["testserver"],
)
def test_negotiation_selects_the_matching_registered_view():
    response = Client().get("/api/orders/", HTTP_ACCEPT_VERSION="2")

    assert response.status_code == 200
    assert response.json() == {"handler": "v2", "version": 2}


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_dedicated_and_accept_header_versions_must_agree():
    _, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT_VERSION="2",
        HTTP_ACCEPT="application/json; version=3",
    )

    assert response.status_code == 400


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=[
        "django_api_versioning.negotiation.VersionNegotiationMiddleware",
        "django_api_versioning.lifecycle.LifecycleMiddleware",
    ],
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=2,
    API_VERSION_LIFECYCLE={
        1: {
            "status": "deprecated",
            "deprecated_at": "2020-01-01T00:00:00Z",
            "sunset": "2030-01-01T00:00:00Z",
        },
        2: {"status": "active"},
    },
    ALLOWED_HOSTS=["testserver"],
)
def test_lifecycle_uses_the_effective_negotiated_version():
    client = Client()

    v1 = client.get("/api/orders/", HTTP_ACCEPT_VERSION="1")
    v2 = client.get("/api/orders/", HTTP_ACCEPT_VERSION="2")

    assert v1.status_code == 200
    assert v1.json() == {"handler": "v1", "version": 1}
    assert v1.headers["Deprecation"] == "@1577836800"
    assert "Sunset" in v1.headers

    assert v2.status_code == 200
    assert v2.json() == {"handler": "v2", "version": 2}
    assert "Deprecation" not in v2.headers
    assert "Sunset" not in v2.headers


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_version_parameter_inside_quoted_accept_parameter_is_not_a_version():
    """A semicolon inside a quoted parameter must not start a new media parameter."""
    _, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT=(
            'application/json; profile="application/example; version=2; trailing=token"'
        ),
    )

    assert response.status_code == 400


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_quoted_accept_version_parameter_remains_supported():
    request, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT='application/json; version="2"',
    )

    assert response.status_code == 200
    assert response.content == b"/api/v2/orders/"
    assert request.api_version == 2


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_accept_rejects_unescaped_quotes_inside_quoted_parameters():
    """An embedded DQUOTE must be escaped, not silently accepted as profile text."""
    _, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT='application/json; profile="one""two"; version=2',
    )

    assert response.status_code == 400


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_accept_allows_escaped_quotes_inside_quoted_parameters():
    _, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT=r'application/json; profile="one\"two"; version=2',
    )

    assert response.status_code == 200


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_commas_and_semicolons_inside_quoted_accept_values_are_not_delimiters():
    _, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT='application/json; profile="one,two; version=2; three"',
    )

    assert response.status_code == 400


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_real_accept_version_parameter_wins_over_quoted_profile_text():
    request, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT='application/json; profile="one; version=2; three"; version=3',
    )

    assert response.status_code == 200
    assert response.content == b"/api/v3/orders/"
    assert request.api_version == 3


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=["django_api_versioning.negotiation.VersionNegotiationMiddleware"],
    API_VERSIONING_SCHEME="path",
    API_BASE_PATH="api/v{version}/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=2,
    ALLOWED_HOSTS=["testserver"],
)
def test_extremely_long_path_version_does_not_crash_middleware():
    requested_path = "/api/v" + ("9" * 5000) + "/orders/"

    response = Client().get(requested_path)

    assert response.status_code == 404


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_oversized_explicit_path_is_rejected_in_non_path_mode():
    _, response = _dispatch(
        "/api/v" + ("9" * 5000) + "/orders/",
        HTTP_ACCEPT_VERSION="2",
    )

    assert response.status_code == 400


@override_settings(ALLOWED_HOSTS=["*"])
def test_hostname_negotiation_does_not_strip_multiple_trailing_dots():
    request = RequestFactory().get("/", HTTP_HOST="api.example.com..")

    assert _host_version(request, {"api.example.com": 2}) is None


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_accept_q_zero_does_not_select_an_explicitly_unacceptable_version():
    _, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT="application/json; version=1; q=0",
    )

    assert response.status_code == 406


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_accept_selects_highest_quality_versioned_media_range():
    request, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT=(
            "application/json; version=1; q=0.2, "
            "application/vnd.example+json; version=2; q=0.8"
        ),
    )

    assert response.status_code == 200
    assert response.content == b"/api/v2/orders/"
    assert request.api_version == 2


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_accept_equal_quality_conflicting_versions_are_rejected():
    _, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT=(
            "application/json; version=1; q=0.8, " "text/csv; version=2; q=0.8"
        ),
    )

    assert response.status_code == 400


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_accept_normalizes_equivalent_integer_version_parameters():
    request, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT=("application/json; version=2, " "text/csv; version=02; q=0.5"),
    )

    assert response.status_code == 200
    assert request.api_version == 2


@pytest.mark.parametrize(
    "accept",
    [
        "not-a-media-type; version=2",
        "application/json; version=2; q=1.1",
        "application/json; version=2; q=0.1234",
        "application/json; version=2; q=0.8; q=0.7",
        'application/json; profile="\x00"; version=2',
        'application/json; profile="\x7f"; version=2',
        "application/json; version=2; version=3",
        "application/json; version=2; invalid parameter=x",
    ],
)
@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_malformed_accept_media_ranges_are_rejected(accept):
    _, response = _dispatch("/api/orders/", HTTP_ACCEPT=accept)

    assert response.status_code == 400


@override_settings(
    API_VERSIONING_SCHEME="header",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_version_parameter_after_accept_quality_is_still_processed():
    request, response = _dispatch(
        "/api/orders/",
        HTTP_ACCEPT="application/json; q=0.8; version=2",
    )

    assert response.status_code == 200
    assert request.api_version == 2


@override_settings(
    API_VERSIONING_SCHEME="query",
    API_BASE_PATH="api/v{version}/",
    API_UNVERSIONED_BASE_PATH="api/",
    API_MIN_VERSION=1,
    API_MAX_VERSION=3,
)
def test_negotiation_rewrites_path_and_path_info_with_script_prefix():
    request = RequestFactory().get(
        "/api/orders/?version=2",
        SCRIPT_NAME="/gateway",
    )
    middleware = VersionNegotiationMiddleware(
        lambda req: JsonResponse({"path": req.path, "path_info": req.path_info})
    )

    response = middleware(request)

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "path": "/gateway/api/v2/orders/",
        "path_info": "/api/v2/orders/",
    }
    assert request.META["PATH_INFO"] == "/api/v2/orders/"



@pytest.mark.parametrize("value", [True, None, "", "2.0", "٢"])
def test_parse_version_rejects_values_outside_ascii_decimal_contract(value):
    with pytest.raises(
        ValueError, match=r"^A version must be an ASCII decimal integer\.$"
    ):
        _parse_version(value)


@override_settings(API_MAX_VERSION=3)
def test_path_version_handles_supported_and_oversized_decimal_segments():
    template = "api/v{version}/"

    assert _path_version("/api/v3/orders/", template) == 3
    assert _path_version("/api/v0002/orders/", template) == 2
    assert _path_version("/api/v999/orders/", template) == -1


@override_settings(ALLOWED_HOSTS=["*"])
def test_hostname_normalization_removes_exactly_one_root_dot_and_applies_idna():
    request = RequestFactory().get("/", HTTP_HOST="API.EXAMPLE.COM.")

    assert _normalize_hostname("API.EXAMPLE.COM.") == "api.example.com"
    assert _normalize_hostname("api.example.com..") is None
    assert _host_version(request, {"api.example.com": 2}) == 2


def test_quoted_header_split_preserves_escaped_delimiters():
    value = r'profile="one\\",two;three", version=2'

    assert _split_quoted_header(value, ",") == [
        r'profile="one\",two;three"',
        " version=2",
    ]


@pytest.mark.parametrize("value", ['"one""two"', '"unterminated', '"bad\x00value"'])
def test_accept_parameter_parser_rejects_malformed_quoted_values(value):
    with pytest.raises(ValueError):
        _parse_accept_parameter_value(value)


@pytest.mark.parametrize("value", ['"one\\\"two"', '"tab\tvalue"'])
def test_accept_parameter_parser_accepts_valid_quoted_pairs_and_horizontal_tab(value):
    parsed, quoted = _parse_accept_parameter_value(value)

    assert quoted is True
    assert parsed


def test_accept_parameter_parser_rejects_control_and_delete_characters_exactly():
    for value in ('"bad\x01value"', '"bad\x7fvalue"'):
        with pytest.raises(
            ValueError,
            match=r"^Accept contains an invalid quoted parameter\.$",
        ):
            _parse_accept_parameter_value(value)


@pytest.mark.parametrize(
    "media_range, message",
    [
        ("*/json; version=2", "Accept contains an invalid media range."),
        (
            "application/json; invalid parameter=x",
            "Accept contains an invalid media parameter.",
        ),
        (
            "application/json; version=2; version=3",
            "Accept contains duplicate version parameters.",
        ),
        ("application/json; q=1.1", "Accept contains an invalid quality value."),
    ],
)
def test_accept_media_range_parser_preserves_validation_errors(media_range, message):
    with pytest.raises(ValueError) as error:
        _parse_accept_media_range(media_range)

    assert str(error.value) == message


def test_header_version_rejects_equal_quality_conflicts_with_exact_error():
    request = RequestFactory().get(
        "/",
        HTTP_ACCEPT=(
            "application/json; version=1; q=0.8, "
            "text/csv; version=2; q=0.8"
        ),
    )

    with pytest.raises(ValueError) as error:
        _header_version(request, "Accept-Version")

    assert str(error.value) == (
        "Accept contains equally preferred conflicting API versions."
    )


def test_header_version_rejects_conflicting_dedicated_and_accept_values_exactly():
    request = RequestFactory().get(
        "/",
        HTTP_ACCEPT_VERSION="2",
        HTTP_ACCEPT="application/json; version=3",
    )

    with pytest.raises(ValueError) as error:
        _header_version(request, "Accept-Version")

    assert str(error.value) == (
        "Accept-Version and Accept media-type version parameters conflict."
    )
