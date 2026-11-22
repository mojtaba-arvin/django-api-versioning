"""High-value mutation contracts across negotiation, lifecycle, registry and routers."""

from datetime import datetime, timezone

import pytest
from django.test import RequestFactory
from django.urls import re_path

from django_api_versioning.decorators import _app_name_prefix, _register_endpoint_routes
from django_api_versioning.exceptions import VersioningError
from django_api_versioning.lifecycle import (
    _coerce_version,
    _extract_version_from_value,
    _get_lifecycle_state,
    _parse_lifecycle_date,
)
from django_api_versioning.negotiation import (
    _normalize_hostname,
    _parse_accept_media_range,
    _parse_accept_parameter_value,
    _path_version,
    _split_quoted_header,
)
from django_api_versioning.registry import ResolvedOperation, UrlRegistry
from django_api_versioning.routers import VersionedRouter


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


def test_register_endpoint_routes_explicit_versions_skip_only_below_minimum(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "django_api_versioning.decorators._register_endpoint_route",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    _register_endpoint_routes("orders/", "", lambda request: None, None, None, [1, 2, 4], 2, 4)
    assert [call[0][4] for call in calls] == [2, 4]


@pytest.mark.parametrize(("value", "expected"), [(0, 0), ("0", 0), ("001", 1), (-1, None), (True, None), ("٣", None)])
def test_lifecycle_version_coercion_keeps_non_negative_ascii_contract(value, expected):
    assert _coerce_version(value) == expected


def test_lifecycle_path_extraction_requires_one_unambiguous_version(monkeypatch):
    monkeypatch.setattr(
        "django_api_versioning.lifecycle._get_api_setting",
        lambda name, default=None: "api/v{version}/" if name == "API_BASE_PATH" else default,
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
        lambda name, default=None: {2: {"status": "active"}} if name == "API_VERSION_LIFECYCLE" else default,
    )
    first = _get_lifecycle_state(request)
    request._django_api_version_lifecycle_state = ("sentinel", None, None, None)
    assert _get_lifecycle_state(request) == ("sentinel", None, None, None)
    assert first[0] == 2


def test_accept_header_splitter_respects_escaped_delimiters():
    assert _split_quoted_header(r'application/json; profile="a\\;b,c", text/plain', ",") == [
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
    [("EXAMPLE.COM", "example.com"), ("example.com.", "example.com"), ("bücher.example", "xn--bcher-kva.example"), ("example.com..", None), ("", None)],
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
    assert UrlRegistry._route_specificity_key(literal)[0] < UrlRegistry._route_specificity_key(converter)[0]


def test_registry_lifecycle_scopes_compose_by_earliest_date():
    registry = UrlRegistry()
    owner = object()
    registry.register_endpoint_lifecycle(
        "orders:list", 2, deprecated_at="2030-01-01T00:00:00Z", owner=owner
    )
    registry.register_endpoint_lifecycle(
        "orders:list", 2, method="GET", deprecated_at="2029-01-01T00:00:00Z", owner=owner
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
        "api/v2/orders/", callback, "orders-list",
        source_version=2, route_version=2, logical_endpoint="orders:list"
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
