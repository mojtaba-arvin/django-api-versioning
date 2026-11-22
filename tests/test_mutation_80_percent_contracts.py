"""High-value mutation contracts across negotiation, lifecycle, registry and routers."""

from datetime import datetime, timezone

import pytest
from types import SimpleNamespace
from django.test import RequestFactory
from django.urls import path, re_path

from django_api_versioning.decorators import _app_name_prefix, _register_endpoint_routes
from django_api_versioning.exceptions import VersioningError
from django_api_versioning.lifecycle import (
    _coerce_version,
    _extract_version_from_value,
    _get_endpoint_lifecycle_state,
    _get_lifecycle_state,
    _extract_version_from_path,
    _is_past,
    LifecycleMiddleware,
    _parse_lifecycle_date,
)
from django_api_versioning.negotiation import (
    _header_version,
    _host_version,
    _normalize_hostname,
    _parse_version,
    _parse_accept_media_range,
    _parse_accept_parameter_value,
    _path_version,
    _split_quoted_header,
    _UnsupportedVersion,
)
from django_api_versioning.registry import ResolvedOperation, UrlRegistry
from django_api_versioning.routers import (
    VersionedDefaultRouter,
    VersionedRouter,
    VersionedRouterVersioning,
)


def test_app_name_prefix_rejects_encoded_and_query_path_components():
    for value in ("accounts%2Fadmin", "accounts?next=admin", "accounts%"):
        with pytest.raises(VersioningError):
            _app_name_prefix(value)


def test_register_endpoint_routes_preserves_inclusive_minimum_and_maximum(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "django_api_versioning.decorators._register_endpoint_route",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    _register_endpoint_routes("orders/", "", lambda request: None, None, 2, None, 2, 2)
    assert [call[0][4] for call in calls] == [2]


def test_register_endpoint_routes_explicit_versions_skip_only_below_minimum(
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(
        "django_api_versioning.decorators._register_endpoint_route",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    _register_endpoint_routes(
        "orders/", "", lambda request: None, None, None, [1, 2, 4], 2, 4
    )
    assert [call[0][4] for call in calls] == [2, 4]


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0), ("0", 0), ("001", 1), (-1, None), (True, None), ("٣", None)],
)
def test_lifecycle_version_coercion_keeps_non_negative_ascii_contract(value, expected):
    assert _coerce_version(value) == expected


def test_lifecycle_path_extraction_requires_one_unambiguous_version(monkeypatch):
    monkeypatch.setattr(
        "django_api_versioning.lifecycle._get_api_setting",
        lambda name, default=None: (
            "api/v{version}/" if name == "API_BASE_PATH" else default
        ),
    )
    assert _extract_version_from_value("/api/v0/orders/") == 0
    assert _extract_version_from_value("/api/v1/orders/api/v2/items/") is None
    assert _extract_version_from_value("/other/v2/orders/") is None


def test_lifecycle_date_parser_normalizes_z_and_naive_values_to_utc():
    assert _parse_lifecycle_date("2030-01-01T00:00:00Z", "sunset") == datetime(
        2030, 1, 1, tzinfo=timezone.utc
    )
    assert _parse_lifecycle_date("2030-01-01T00:00:00", "sunset") == datetime(
        2030, 1, 1, tzinfo=timezone.utc
    )


def test_lifecycle_state_is_cached_on_request(monkeypatch):
    request = RequestFactory().get("/api/v2/orders/")
    monkeypatch.setattr(
        "django_api_versioning.lifecycle._extract_version", lambda _request: 2
    )
    monkeypatch.setattr(
        "django_api_versioning.lifecycle._get_api_setting",
        lambda name, default=None: (
            {2: {"status": "active"}} if name == "API_VERSION_LIFECYCLE" else default
        ),
    )
    first = _get_lifecycle_state(request)
    request._django_api_version_lifecycle_state = ("sentinel", None, None, None)
    assert _get_lifecycle_state(request) == ("sentinel", None, None, None)
    assert first[0] == 2


def test_accept_header_splitter_respects_escaped_delimiters():
    assert _split_quoted_header(
        r'application/json; profile="a\\;b,c", text/plain', ","
    ) == [
        r'application/json; profile="a\\;b,c"',
        " text/plain",
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('"profile"', ("profile", True)),
        ("token", ("token", False)),
        ('""', ("", True)),
    ],
)
def test_accept_parameter_value_unwraps_valid_quoted_and_token_values(raw, expected):
    assert _parse_accept_parameter_value(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", '"unterminated', 'token with space', '"embedded"quote"', '"trailing\\'],
)
def test_accept_parameter_value_rejects_malformed_values(raw):
    with pytest.raises(ValueError):
        _parse_accept_parameter_value(raw)


def test_accept_media_range_applies_default_quality_and_rejects_duplicate_quality():
    assert _parse_accept_media_range("application/json; version=2") == ("2", 1.0)
    with pytest.raises(ValueError, match="invalid quality"):
        _parse_accept_media_range("application/json; q=0.5; q=0.8; version=2")


def test_accept_media_range_rejects_invalid_wildcard_shape():
    with pytest.raises(ValueError, match="invalid media range"):
        _parse_accept_media_range("*/json; version=2")


def test_path_version_accepts_zero_and_rejects_prefix_or_suffix_near_misses():
    assert _path_version("/api/v0/orders/", "api/v{version}/") == 0
    assert _path_version("/xapi/v2/orders/", "api/v{version}/") is None
    assert _path_version("/api/v2/orders", "api/v{version}/") == 2


@pytest.mark.parametrize(
    ("hostname", "expected"),
    [
        ("EXAMPLE.COM", "example.com"),
        ("example.com.", "example.com"),
        ("bücher.example", "xn--bcher-kva.example"),
        ("example.com..", None),
        ("", None),
    ],
)
def test_hostname_normalization_handles_case_idna_and_root_dot(hostname, expected):
    assert _normalize_hostname(hostname) == expected


def test_registry_replacement_prefers_newer_source_and_last_unversioned_registration():
    registry = UrlRegistry()

    def first(request):
        return None

    pattern = registry._create_pattern("orders/", first, "orders")
    assert registry._should_replace(pattern, 2) is True
    pattern._django_api_versioning_source_version = 3
    assert registry._should_replace(pattern, 2) is False
    assert registry._should_replace(pattern, 3) is True
    assert registry._should_replace(pattern, None) is True


def test_registry_route_specificity_distinguishes_literal_and_dynamic_routes():
    from django.urls import path

    literal = path("orders/archive/", lambda request: None)
    converter = path("orders/<slug:slug>/", lambda request: None)
    regex = re_path(r"^orders/(?P<slug>[a-z]+)/$", lambda request: None)
    assert UrlRegistry._route_specificity_key(literal)[1] is False
    assert UrlRegistry._route_specificity_key(converter)[1] is True
    assert UrlRegistry._route_specificity_key(regex)[1] is True
    assert (
        UrlRegistry._route_specificity_key(literal)[0]
        < UrlRegistry._route_specificity_key(converter)[0]
    )


def test_registry_lifecycle_scopes_compose_by_earliest_date():
    registry = UrlRegistry()
    owner = object()
    registry.register_endpoint_lifecycle(
        "orders:list", 2, deprecated_at="2030-01-01T00:00:00Z", owner=owner
    )
    registry.register_endpoint_lifecycle(
        "orders:list",
        2,
        method="GET",
        deprecated_at="2029-01-01T00:00:00Z",
        owner=owner,
    )
    operation = ResolvedOperation(
        logical_endpoint="orders:list",
        route_version=2,
        source_version=2,
        method="GET",
        action="list",
        route_name="orders-list",
        namespace="",
        route="api/v2/orders/",
        registered_route="api/v2/orders/",
        router_owner=owner,
    )
    assert registry.get_endpoint_lifecycle(operation).deprecated_at == datetime(
        2029, 1, 1, tzinfo=timezone.utc
    )


def test_registry_registered_operation_maps_head_to_get_action():
    registry = UrlRegistry()

    def callback(request):
        return None

    callback.actions = {"get": "list"}
    registry.register(
        "api/v2/orders/",
        callback,
        "orders-list",
        source_version=2,
        route_version=2,
        logical_endpoint="orders:list",
    )
    operation = registry.resolve_registered_operation("orders:list", 2, "HEAD")
    assert operation is not None
    assert operation.method == "HEAD"
    assert operation.action == "list"
    assert registry.resolve_registered_operation("orders:list", True, "GET") is None
    assert registry.resolve_registered_operation("orders:list", 2, "") is None


def test_router_lifecycle_method_resolution_maps_head_and_rejects_action_mismatch():
    actions = {"get": "list", "post": "create"}
    resolved = VersionedRouter._resolve_lifecycle_methods(
        ["HEAD", "POST"], actions, None, "orders:order-list"
    )
    assert resolved == [("HEAD", "list"), ("POST", "create")]
    with pytest.raises(VersioningError, match="maps to action"):
        VersionedRouter._resolve_lifecycle_methods(
            ["POST"], actions, "list", "orders:order-list"
        )


def test_router_constructor_defaults_and_boolean_validation():
    router = VersionedRouter()
    assert router.trailing_slash is True
    assert router.use_regex_path is True
    with pytest.raises(TypeError, match="use_regex_path must be a bool"):
        VersionedRouter(use_regex_path=1)


def test_router_lifecycle_method_resolution_rejects_duplicate_and_unmapped_methods():
    with pytest.raises(VersioningError, match="duplicates"):
        VersionedRouter._resolve_lifecycle_methods(
            ["GET", " get "], {"get": "list"}, None, "orders:order-list"
        )
    with pytest.raises(VersioningError, match="not registered"):
        VersionedRouter._resolve_lifecycle_methods(
            ["PATCH"], {"get": "list"}, None, "orders:order-list"
        )


@pytest.mark.parametrize("value", [None, True, False, "", "  ", "٢", "2.0", "-1"])
def test_negotiation_version_parser_rejects_non_ascii_decimal_values(value):
    with pytest.raises(ValueError, match="ASCII decimal integer"):
        _parse_version(value)


def test_negotiation_version_parser_trims_ascii_decimal_and_accepts_zero():
    assert _parse_version("  0002  ") == 2
    assert _parse_version("0") == 0


def test_path_version_handles_leading_zeroes_and_oversized_segments():
    assert _path_version("/api/v0002/orders/", "api/v{version}/") == 2
    assert _path_version("/api/v999999999999/orders/", "api/v{version}/") == -1
    assert _path_version("/api/v2/orders/", "api/v{version}/extra") is None


@pytest.mark.parametrize("template", [None, "api/v1/", "api/{version}/{version}/"])
def test_path_version_rejects_invalid_templates(template):
    assert _path_version("/api/v2/orders/", template) is None


def test_host_version_normalizes_request_and_configured_idna_hostnames():
    request = type("Request", (), {"get_host": lambda self: "XN--BCHER-KVA.EXAMPLE."})()
    assert _host_version(request, {"bücher.example": 4}) == 4
    assert _host_version(request, {"other.example": 4}) is None


def test_quoted_header_splitter_rejects_unterminated_quote_and_escape():
    with pytest.raises(ValueError, match="unterminated quoted"):
        _split_quoted_header('application/json; profile="unfinished', ",")
    with pytest.raises(ValueError, match="unterminated quoted"):
        _split_quoted_header('application/json; profile="unfinished\\\\', ",")


def test_accept_parameter_parser_allows_escaped_quote_but_rejects_control_bytes():
    assert _parse_accept_parameter_value('"one\\\\\\"two"') == ('one\\"two', True)
    with pytest.raises(ValueError, match="invalid quoted"):
        _parse_accept_parameter_value('"bad\\x01value"')


def test_accept_media_range_rejects_duplicate_version_and_malformed_quality():
    with pytest.raises(ValueError, match="duplicate version"):
        _parse_accept_media_range("application/json; version=2; VERSION=3")
    with pytest.raises(ValueError, match="invalid quality"):
        _parse_accept_media_range("application/json; q=1.001; version=2")


def test_header_version_prefers_highest_quality_and_ignores_unversioned_ranges():
    request = RequestFactory().get(
        "/api/orders/",
        HTTP_ACCEPT="text/plain, application/json;version=2;q=0.4, application/xml;version=3;q=0.8",
    )
    assert _header_version(request, "Accept-Version") == 3


def test_header_version_rejects_equal_quality_conflicts_and_all_zero_quality():
    conflict = RequestFactory().get(
        "/api/orders/",
        HTTP_ACCEPT="application/json;version=2;q=0.8, application/xml;version=3;q=0.8",
    )
    with pytest.raises(ValueError, match="equally preferred"):
        _header_version(conflict, "Accept-Version")

    unacceptable = RequestFactory().get(
        "/api/orders/", HTTP_ACCEPT="application/json;version=2;q=0"
    )
    with pytest.raises(_UnsupportedVersion, match="q=0"):
        _header_version(unacceptable, "Accept-Version")


def test_header_version_rejects_conflicting_dedicated_and_accept_versions():
    request = RequestFactory().get(
        "/api/orders/",
        HTTP_ACCEPT="application/json;version=3",
        HTTP_ACCEPT_VERSION="2",
    )
    with pytest.raises(ValueError, match="conflict"):
        _header_version(request, "Accept-Version")


def test_header_version_uses_dedicated_header_when_accept_is_empty():
    request = RequestFactory().get("/api/orders/", HTTP_ACCEPT="", HTTP_ACCEPT_VERSION="4")
    assert _header_version(request, "Accept-Version") == 4


def test_lifecycle_path_fallback_uses_request_path_when_path_info_is_empty():
    request = RequestFactory().get("/api/v2/orders/")
    request.path_info = ""
    assert _extract_version_from_path(request) == 2


def test_lifecycle_path_extraction_rejects_invalid_base_path_templates(monkeypatch):
    request = RequestFactory().get("/api/v2/orders/")
    monkeypatch.setattr(
        "django_api_versioning.lifecycle._get_api_setting",
        lambda name, default=None: "api/v{version}/{version}/"
        if name == "API_BASE_PATH"
        else default,
    )
    assert _extract_version_from_path(request) is None


def test_lifecycle_date_parser_warns_and_ignores_non_string_and_invalid_values(caplog):
    assert _parse_lifecycle_date(None, "sunset") is None
    assert _parse_lifecycle_date("not-a-date", "sunset") is None
    assert "Invalid sunset date" in caplog.text


def test_lifecycle_date_parser_handles_utc_offset_and_extreme_overflow():
    assert _parse_lifecycle_date("2030-01-01T03:00:00+03:00", "sunset") == datetime(
        2030, 1, 1, tzinfo=timezone.utc
    )
    assert _parse_lifecycle_date("0001-01-01T00:00:00+14:00", "sunset") is None


def test_lifecycle_is_past_uses_strict_utc_comparison(monkeypatch):
    fixed_now = datetime(2030, 1, 1, tzinfo=timezone.utc)

    class FixedDateTime:
        @staticmethod
        def now(tz=None):
            assert tz is timezone.utc
            return fixed_now

    monkeypatch.setattr("django_api_versioning.lifecycle.datetime", FixedDateTime)
    assert _is_past(datetime(2029, 12, 31, tzinfo=timezone.utc)) is True
    assert _is_past(fixed_now) is False
    assert _is_past(datetime(2030, 1, 2, tzinfo=timezone.utc)) is False


def test_lifecycle_process_view_marks_enforced_sunset_response(monkeypatch):
    request = RequestFactory().get("/api/v2/orders/")
    state = (2, {"sunset": "2020-01-01"}, None, datetime(2020, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr("django_api_versioning.lifecycle._get_lifecycle_state", lambda _request: state)
    monkeypatch.setattr("django_api_versioning.lifecycle._is_past", lambda _date: True)
    response = LifecycleMiddleware(lambda _request: None).process_view(request, lambda: None, [], {})
    assert response.status_code == 410
    assert request._django_api_version_lifecycle_sunset_enforced is True


def test_endpoint_lifecycle_cache_is_separate_for_405_resolution(monkeypatch):
    request = RequestFactory().get("/api/v2/orders/")
    normal = object()
    method_405 = object()
    calls = []

    def resolve(_match, _method, allow_unmapped_method=False):
        calls.append(allow_unmapped_method)
        return normal if not allow_unmapped_method else method_405

    monkeypatch.setattr("django_api_versioning.lifecycle.registry.resolve_operation", resolve)
    monkeypatch.setattr(
        "django_api_versioning.lifecycle.registry.get_endpoint_lifecycle",
        lambda operation: operation,
    )
    request.resolver_match = object()
    assert _get_endpoint_lifecycle_state(request) is normal
    assert _get_endpoint_lifecycle_state(request, allow_unmapped_method=True) is method_405
    assert _get_endpoint_lifecycle_state(request) is normal
    assert calls == [False, True]


def test_lifecycle_version_coercion_rejects_oversized_decimal_strings():
    assert _coerce_version("9" * 5000) is None


def test_default_router_options_control_root_and_suffix_generation():
    router = VersionedDefaultRouter(
        include_root_view=False,
        include_format_suffixes=False,
        root_view_name="root",
    )
    assert router.include_root_view is False
    assert router.include_format_suffixes is False
    assert router.root_view_name == "root"
    assert router._build_default_urls() == []


def test_default_router_rejects_invalid_root_configuration():
    with pytest.raises(TypeError, match="include_root_view must be a bool"):
        VersionedDefaultRouter(include_root_view=1)
    with pytest.raises(TypeError, match="include_format_suffixes must be a bool"):
        VersionedDefaultRouter(include_format_suffixes=1)
    with pytest.raises(VersioningError, match="root_view_name"):
        VersionedDefaultRouter(root_view_name="  ")


def test_router_builds_version_namespaces_in_numeric_order():
    router = VersionedRouter()
    pattern_three = path("three/", lambda request: None, name="three")
    pattern_two = path("two/", lambda request: None, name="two")
    patterns = router._build_namespaced_urlpatterns(
        {3: [pattern_three], 2: [pattern_two]}, []
    )
    assert [pattern.namespace for pattern in patterns] == ["v2", "v3"]
    assert [pattern.app_name for pattern in patterns] == [
        "django_api_versioning",
        "django_api_versioning",
    ]


def test_router_versioning_allowed_versions_include_default_and_explicit_values():
    versioning = VersionedRouterVersioning()
    versioning.allowed_versions = [2, 3]
    versioning.default_version = "1"
    assert versioning.is_allowed_version("1") is True
    assert versioning.is_allowed_version("2") is True
    assert versioning.is_allowed_version("4") is False
    versioning.allowed_versions = []
    assert versioning.is_allowed_version("anything") is True


def test_router_versioning_extracts_namespace_and_validates_allowed_version():
    versioning = VersionedRouterVersioning()
    versioning.allowed_versions = ["2"]
    versioning.default_version = None
    request = SimpleNamespace(
        resolver_match=SimpleNamespace(namespace="outer:v2", route=None)
    )
    assert versioning.determine_version(request) == "2"

    versioning.allowed_versions = ["3"]
    with pytest.raises(Exception, match="allowed API version"):
        versioning.determine_version(request)


def test_router_versioning_qualifies_view_names_once_with_full_namespace():
    versioning = VersionedRouterVersioning()
    request = SimpleNamespace(
        resolver_match=SimpleNamespace(namespace="outer:v2")
    )
    assert versioning.get_versioned_viewname("orders-list", request) == "outer:v2:orders-list"
    assert versioning.get_versioned_viewname("outer:v2:orders-list", request) == "outer:v2:orders-list"
    request.resolver_match.namespace = ""
    assert versioning.get_versioned_viewname("orders-list", request) == "orders-list"
