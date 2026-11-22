"""Focused contracts derived from the surviving mutation reports.

These tests assert observable boundaries and ownership semantics rather than
raising mutation thresholds or excluding difficult code paths.
"""

import re
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from django.core.exceptions import DisallowedHost
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import path, re_path
from django.views import View
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from django_api_versioning.decorators import (
    _app_name_prefix,
    _validate_version,
    endpoint,
    remove_endpoint,
    set_endpoint_lifecycle,
    ver_range,
)
from django_api_versioning.exceptions import (
    InvalidVersionError,
    VersioningError,
    VersionRangeError,
    VersionTypeError,
)
from django_api_versioning.lifecycle import (
    LifecycleMiddleware,
    _coerce_version,
    _extract_version_from_value,
    _get_endpoint_lifecycle_state,
    _is_past,
    _parse_lifecycle_date,
    _to_structured_field_date,
)
from django_api_versioning.negotiation import (
    VersionNegotiationMiddleware,
    _header_version,
    _normalize_hostname,
    _parse_accept_media_range,
    _parse_accept_parameter_value,
    _parse_version,
    _path_version,
    _split_quoted_header,
    _UnsupportedVersion,
)
from django_api_versioning.registry import (
    REMOVED_ROUTE,
    ResolvedOperation,
    UrlRegistry,
    registry,
)
from django_api_versioning.routers import (
    VersionedDefaultRouter,
    VersionedRouter,
    VersionedRouterVersioning,
)
from django_api_versioning.settings import api_settings


def _view(request):
    return None


def _registered_pattern(
    target_registry,
    callback=None,
    *,
    version=2,
    logical_endpoint="orders:order-list",
    owner=None,
    prefix="orders",
    trailing_slash=True,
):
    callback = callback or _view
    callback.actions = {"get": "list", "post": "create"}
    pattern = path("api/v2/orders/", callback, name="order-list")
    setattr(pattern, target_registry._ROUTE_VERSION_ATTR, version)
    setattr(pattern, target_registry._SOURCE_VERSION_ATTR, version)
    setattr(pattern, target_registry._LOGICAL_ENDPOINT_ATTR, logical_endpoint)
    setattr(pattern, target_registry._ROUTER_OWNER_ATTR, owner)
    setattr(pattern, target_registry._ROUTER_PREFIX_ATTR, prefix)
    setattr(pattern, target_registry._ROUTER_TRAILING_SLASH_ATTR, trailing_slash)
    return pattern


def test_resolved_operation_is_immutable():
    operation = ResolvedOperation(
        logical_endpoint="orders:order-list",
        route_version=2,
        source_version=2,
        method="GET",
        action="list",
        route_name="order-list",
        namespace="v2",
        route="api/v2/orders/",
        registered_route="api/v2/orders/",
    )

    with pytest.raises(FrozenInstanceError):
        operation.route_version = 3


def test_registry_synchronization_and_wrapper_metadata_are_preserved():
    class LockProbe:
        def __init__(self):
            self.entries = 0

        def __enter__(self):
            self.entries += 1

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    target = UrlRegistry()
    lock = LockProbe()
    target._lock = lock

    target.clear()

    assert lock.entries == 1
    assert UrlRegistry.clear.__name__ == "clear"


def test_registry_canonical_route_key_only_normalizes_literal_regex_paths():
    canonical = UrlRegistry._canonical_route_key

    assert canonical(r"^api/v1/orders/\$/items/$") == "api/v1/orders/$/items/"
    assert canonical(r"^api/v1/orders/\./$") == "api/v1/orders/./"
    assert canonical(r"^api/v\d+/orders/$") == r"^api/v\d+/orders/$"
    assert canonical(r"^api/v1/<int:pk>/$") == r"^api/v1/<int:pk>/$"
    assert canonical("api/v1/orders/") == "api/v1/orders/"


def test_resolved_route_match_requires_a_complete_path_segment():
    match_length = UrlRegistry._resolved_route_match_length

    assert match_length("root/api/v2/orders/", "api/v2/orders/") == len(
        "api/v2/orders/"
    )
    assert match_length("rootxapi/v2/orders/", "api/v2/orders/") == 0
    assert match_length("api/v2/orders/", "^api/v2/orders/$") == len("api/v2/orders/")


def test_registry_remove_tracks_router_prefix_and_slash_identity():
    target = UrlRegistry()
    owner = object()
    logical = "orders:order-list"
    pattern = _registered_pattern(target, owner=owner)
    target.urlpatterns.append(pattern)

    target.remove(logical, 3, owner=owner)

    owned_boundary = target._removal_boundary(
        logical, 4, owner=owner, router_prefix="orders", trailing_slash=True
    )
    global_fallback = target._removal_boundary(
        logical, 4, owner=object(), router_prefix="orders", trailing_slash=True
    )
    assert owned_boundary == 3
    assert global_fallback == 3

    target._removal_boundaries.clear()
    assert (
        target._removal_boundary(
            logical, 4, owner=owner, router_prefix="orders", trailing_slash=True
        )
        == 3
    )
    assert (
        target._removal_boundary(
            logical, 4, owner=object(), router_prefix="other", trailing_slash=False
        )
        is None
    )
    assert pattern in target.urlpatterns


def test_registry_does_not_transfer_a_removed_route_between_owners():
    target = UrlRegistry()
    logical = "orders:order-list"
    first_owner = object()
    second_owner = object()
    first = _registered_pattern(target, owner=first_owner)
    second = _registered_pattern(target, owner=second_owner)

    target._record_removed(first, logical)
    target._record_removed(second, logical)

    assert target._removed_patterns[(logical, 2, "orders", True)] is first


def test_registry_suppression_allows_only_a_newer_source_to_reintroduce_route():
    target = UrlRegistry()
    target.remove("orders:order-list", 2)

    target.register(
        "api/v2/orders/",
        _view,
        name="order-list",
        source_version=1,
        route_version=2,
        logical_endpoint="orders:order-list",
    )
    assert target.urlpatterns == []
    assert ("orders:order-list", 2) in target._removed_patterns

    target.register(
        "api/v2/orders/",
        _view,
        name="order-list",
        source_version=3,
        route_version=2,
        logical_endpoint="orders:order-list",
    )
    assert len(target.urlpatterns) == 1
    assert target.urlpatterns[0].callback is _view
    assert ("orders:order-list", 2) not in target._removed_patterns


def test_registry_resolver_trace_and_method_action_mapping_fail_closed():
    target = UrlRegistry()

    def callback(request):
        return None

    callback.actions = {"get": "list", "post": "create"}
    pattern = _registered_pattern(target, callback)
    target.urlpatterns.append(pattern)
    match = SimpleNamespace(
        route="api/v2/orders/",
        func=callback,
        url_name="order-list",
        tried=[[pattern]],
        namespaces=("v2",),
        namespace="v2",
    )

    assert target.get_resolved_route_version_for_match(match) == (True, 2)
    assert target.resolve_operation(match, "HEAD").action == "list"
    assert target.resolve_operation(match, "PATCH") is None
    assert (
        target.resolve_operation(match, "PATCH", allow_unmapped_method=True).action
        is None
    )
    assert target.resolve_operation(match, "OPTIONS").action is None
    assert target.resolve_operation(match, 3) is None

    wrong_namespace = SimpleNamespace(
        route="api/v2/orders/",
        func=callback,
        url_name="order-list",
        tried=[[pattern]],
        namespaces=("v3",),
        namespace="v3",
    )
    assert target.resolve_operation(wrong_namespace, "GET") is None

    foreign_pattern = path("api/v2/other/", lambda request: None, name="other")
    foreign_match = SimpleNamespace(
        route="api/v2/orders/",
        func=foreign_pattern.callback,
        url_name="other",
        tried=[[foreign_pattern]],
        namespaces=("v2",),
        namespace="v2",
    )
    assert target.get_resolved_route_version_for_match(foreign_match) == (False, None)
    assert target.resolve_operation(foreign_match, "GET") is None


def test_registry_ambiguous_resolver_matches_do_not_choose_a_version():
    target = UrlRegistry()
    first = _registered_pattern(target, version=1)
    second = _registered_pattern(target, version=2)
    target.urlpatterns.extend([first, second])
    match = SimpleNamespace(
        route="api/v2/orders/",
        func=first.callback,
        url_name="order-list",
    )

    assert target.get_resolved_route_version_for_match(match) == (True, None)
    assert target.resolve_operation(match, "GET", require_exact_pattern=False) is None


def test_registry_registered_operation_requires_one_identity_and_maps_head():
    target = UrlRegistry()
    pattern = _registered_pattern(target)
    target.urlpatterns.append(pattern)

    operation = target.resolve_registered_operation("orders:order-list", 2, "HEAD")
    assert operation is not None
    assert operation.action == "list"
    assert target.resolve_registered_operation("orders:missing", 2, "GET") is None
    assert target.resolve_registered_operation("orders:order-list", True, "GET") is None
    assert target.resolve_registered_operation("orders:order-list", 2, None) is None

    duplicate = _registered_pattern(target, version=2)
    target.urlpatterns.append(duplicate)
    assert target.resolve_registered_operation("orders:order-list", 2, "GET") is None


def test_registry_lifecycle_scopes_compose_conservatively_for_head():
    target = UrlRegistry()
    target.register_endpoint_lifecycle(
        "orders:order-list", 2, deprecated_at="2028-01-01T00:00:00Z"
    )
    target.register_endpoint_lifecycle(
        "orders:order-list",
        2,
        method="GET",
        action="list",
        deprecated_at="2027-01-01T00:00:00Z",
        sunset="2030-01-01T00:00:00Z",
    )
    target.register_endpoint_lifecycle(
        "orders:order-list",
        2,
        method="HEAD",
        action="list",
        sunset="2029-01-01T00:00:00Z",
    )
    operation = ResolvedOperation(
        logical_endpoint="orders:order-list",
        route_version=2,
        source_version=2,
        method="HEAD",
        action="list",
        route_name="order-list",
        namespace="v2",
        route="api/v2/orders/",
        registered_route="api/v2/orders/",
    )

    lifecycle = target.get_endpoint_lifecycle(operation)
    assert lifecycle.deprecated_at == datetime(2027, 1, 1, tzinfo=timezone.utc)
    assert lifecycle.sunset == datetime(2029, 1, 1, tzinfo=timezone.utc)


def test_registry_route_specificity_prefers_static_and_longer_dynamic_routes():
    static = path("orders/archive/", _view)
    short_dynamic = path("orders/<int:pk>/", _view)
    long_dynamic = path("orders/<int:pk>/archive/", _view)

    assert UrlRegistry._route_specificity_key(static) < (
        UrlRegistry._route_specificity_key(short_dynamic)
    )
    assert UrlRegistry._route_specificity_key(long_dynamic) < (
        UrlRegistry._route_specificity_key(short_dynamic)
    )

    target = UrlRegistry()
    target.urlpatterns = [short_dynamic, static]
    target._sort_urlpatterns()
    assert target.urlpatterns[0] is static


def test_registry_view_creation_rejects_instances_and_unconfigured_viewsets():
    class SampleView(View):
        def get(self, request):
            return None

    with pytest.raises(TypeError, match=re.escape("Pass the view class 'SampleView'")):
        UrlRegistry._create_pattern("items/", SampleView(), None)

    class SampleViewSet(ViewSet):
        def list(self, request):
            return None

    with pytest.raises(TypeError, match="cannot be registered directly"):
        UrlRegistry._create_pattern("items/", SampleViewSet, None)


def test_router_constructor_defaults_and_validation_messages():
    router = VersionedRouter()
    assert router.trailing_slash is True
    assert router.use_regex_path is True
    assert router.app_name == "django_api_versioning"

    with pytest.raises(
        VersioningError, match=re.escape("app_name must be a non-empty string.")
    ):
        VersionedRouter(app_name=" ")
    with pytest.raises(TypeError, match=re.escape("trailing_slash must be a bool.")):
        VersionedRouter(trailing_slash=1)
    with pytest.raises(TypeError, match=re.escape("use_regex_path must be a bool.")):
        VersionedRouter(use_regex_path=1)


def test_router_registration_and_removal_validate_public_inputs_exactly():
    router = VersionedRouter()

    with pytest.raises(TypeError, match=re.escape("prefix must be a string.")):
        router.register(1, object)
    with pytest.raises(
        VersioningError,
        match=re.escape(
            "prefix must be a non-empty relative path without leading or trailing '/'."
        ),
    ):
        router.register("orders/", object)
    with pytest.raises(
        VersionRangeError,
        match=re.escape("Use either 'version' or 'versions', not both."),
    ):
        router.register("orders", object, version=1, versions=[1])
    with pytest.raises(
        VersionTypeError, match=re.escape("'versions' must be a list of integers.")
    ):
        router.register("orders", object, versions=(1, 2))
    with pytest.raises(
        VersionRangeError, match=re.escape("'versions' must not contain duplicates.")
    ):
        router.register("orders", object, versions=[1, 1])

    with pytest.raises(TypeError, match=re.escape("prefix must be a string.")):
        router.remove(1, "order-list", from_version=1)
    with pytest.raises(TypeError, match=re.escape("route_name must be a string.")):
        router.remove("orders", 1, from_version=1)
    with pytest.raises(
        VersioningError, match=re.escape("route_name must be a non-empty string.")
    ):
        router.remove("orders", "", from_version=1)


def test_router_version_validation_keeps_zero_and_maximum_inclusive(monkeypatch):
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)

    VersionedRouter._validate_version(0)
    VersionedRouter._validate_version(5)

    with pytest.raises(VersionRangeError):
        VersionedRouter._validate_version(-1)
    with pytest.raises(InvalidVersionError):
        VersionedRouter._validate_version(6)
    with pytest.raises(VersionTypeError):
        VersionedRouter._validate_version(True)


def test_router_lifecycle_method_resolution_checks_duplicates_head_and_action():
    actions = {"get": "list", "post": "create"}
    assert VersionedRouter._resolve_lifecycle_methods(
        ["HEAD"], actions, None, "orders:order-list"
    ) == [("HEAD", "list")]

    with pytest.raises(
        VersioningError, match=re.escape("methods must not contain duplicates.")
    ):
        VersionedRouter._resolve_lifecycle_methods(
            ["GET", " get "], actions, None, "orders:order-list"
        )
    with pytest.raises(
        VersioningError,
        match=re.escape(
            "HTTP method 'PATCH' is not registered for 'orders:order-list'."
        ),
    ):
        VersionedRouter._resolve_lifecycle_methods(
            ["PATCH"], actions, None, "orders:order-list"
        )
    with pytest.raises(
        VersioningError,
        match=re.escape("HTTP method 'POST' maps to action 'create', not 'list'."),
    ):
        VersionedRouter._resolve_lifecycle_methods(
            ["POST"], actions, "list", "orders:order-list"
        )


def test_router_default_router_options_are_type_checked():
    with pytest.raises(TypeError, match=re.escape("include_root_view must be a bool.")):
        VersionedDefaultRouter(include_root_view=1)
    with pytest.raises(
        TypeError, match=re.escape("include_format_suffixes must be a bool.")
    ):
        VersionedDefaultRouter(include_format_suffixes="yes")
    with pytest.raises(
        VersioningError, match=re.escape("root_view_name must be a non-empty string.")
    ):
        VersionedDefaultRouter(root_view_name=" ")


def test_router_versioning_ignores_malformed_namespace_and_uses_allowed_default():
    versioning = VersionedRouterVersioning()
    versioning.default_version = "1"
    versioning.allowed_versions = ["1"]
    request = SimpleNamespace(
        resolver_match=SimpleNamespace(route=None, namespace="v2beta")
    )

    assert versioning.determine_version(request) == "1"
    assert versioning.is_allowed_version("1") is True
    assert versioning.is_allowed_version("2") is False


def test_router_versioning_qualifies_namespaces_only_once():
    versioning = VersionedRouterVersioning()
    request = SimpleNamespace(resolver_match=SimpleNamespace(namespace="outer:v2"))

    assert versioning.get_versioned_viewname("order-list", request) == (
        "outer:v2:order-list"
    )
    assert versioning.get_versioned_viewname("outer:v2:order-list", request) == (
        "outer:v2:order-list"
    )


def test_decorator_app_name_and_version_range_boundaries_are_explicit(monkeypatch):
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)

    assert _app_name_prefix(None) == ""
    assert _app_name_prefix("billing/v1") == "billing/v1/"
    assert ver_range(0, 5) == [0, 1, 2, 3, 4, 5]
    assert ver_range(5, 5) == [5]
    _validate_version(0, 5)
    _validate_version(5, 5)

    with pytest.raises(TypeError, match="app_name must be a string or None"):
        _app_name_prefix(1)
    with pytest.raises(VersioningError, match="leading or trailing whitespace"):
        _app_name_prefix(" billing")
    with pytest.raises(VersioningError, match="empty, '.' or '..' segments"):
        _app_name_prefix("billing//v1")
    with pytest.raises(VersionRangeError):
        ver_range(2, 1)
    with pytest.raises(VersionTypeError):
        ver_range(True, 2)


def test_endpoint_registers_the_api_minimum_and_maximum_inclusively(monkeypatch):
    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 2)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 3)

    @endpoint("orders/", version=2)
    def orders(request):
        return None

    versions = {
        getattr(pattern, registry._ROUTE_VERSION_ATTR, None)
        for pattern in registry.urlpatterns
    }
    assert versions == {2, 3}


def test_decorator_rollback_preserves_an_inherited_metadata_attribute():
    attribute = registry._LOGICAL_ENDPOINT_ATTR

    class BaseView:
        pass

    setattr(BaseView, attribute, "base:route")

    class InheritedView(BaseView):
        def __call__(self, request):
            return None

    class CollisionViewSet(ViewSet):
        def list(self, request):
            return None

    router = VersionedRouter()
    router.register("collision", CollisionViewSet, version=1, basename="collision")
    before = list(registry.urlpatterns)

    with pytest.raises(VersioningError, match="owned by a VersionedRouter"):
        endpoint("collision/", version=1)(InheritedView)

    assert attribute not in InheritedView.__dict__
    assert getattr(InheritedView, attribute) == "base:route"
    assert registry.urlpatterns == before


def test_decorator_lifecycle_rejects_duplicate_methods_and_router_tombstones():
    with pytest.raises(
        VersioningError, match=re.escape("methods must not contain duplicates.")
    ):
        set_endpoint_lifecycle(
            "orders/",
            version=2,
            methods=["GET", " get "],
            deprecated_at="2027-01-01T00:00:00Z",
        )

    class OrdersViewSet(ViewSet):
        def list(self, request):
            return None

    router = VersionedRouter()
    router.register("orders", OrdersViewSet, version=1, basename="order")
    router.remove("orders", "order-list", from_version=1)

    with pytest.raises(VersioningError, match="owned by a VersionedRouter"):
        remove_endpoint("orders:order-list", from_version=1)


def test_negotiation_ascii_version_and_path_template_boundaries():
    assert _parse_version("0002") == 2
    assert _path_version("/api/v0002/orders/", "api/v{version}/") == 2
    assert _path_version("/api/v" + ("9" * 1000) + "/orders/", "api/v{version}/") == -1
    assert _path_version("/api/v2/orders/", "api/v{version}/{version}/") is None

    with pytest.raises(ValueError, match="ASCII decimal integer"):
        _parse_version("٢")
    with pytest.raises(ValueError, match="ASCII decimal integer"):
        _parse_version(True)


def test_negotiation_hostname_normalization_is_idna_safe():
    assert _normalize_hostname("EXAMPLE.COM.") == "example.com"
    assert _normalize_hostname("münich.example") == "xn--mnich-kva.example"
    assert _normalize_hostname("example.com..") is None
    assert _normalize_hostname("") is None


def test_accept_parser_respects_quoted_delimiters_and_rejects_bad_escapes():
    assert _split_quoted_header('profile="a,b;c"; version=2', ";") == [
        'profile="a,b;c"',
        " version=2",
    ]
    assert _parse_accept_parameter_value('"a\\"b"') == ('a\\"b', True)

    with pytest.raises(ValueError, match="unterminated quoted parameter"):
        _split_quoted_header('profile="unterminated', ";")
    with pytest.raises(ValueError, match="invalid quoted parameter"):
        _parse_accept_parameter_value('"bad\x01value"')


def test_accept_media_range_rejects_duplicate_parameters_and_bad_quality():
    assert _parse_accept_media_range("application/json; version=2; q=0.8") == (
        "2",
        0.8,
    )

    with pytest.raises(ValueError, match="duplicate version parameters"):
        _parse_accept_media_range("application/json; version=2; version=3")
    with pytest.raises(ValueError, match="invalid quality value"):
        _parse_accept_media_range("application/json; q=0.8; q=0.5")


def test_accept_negotiation_uses_quality_and_rejects_ambiguity():
    request = RequestFactory().get(
        "/",
        HTTP_ACCEPT=(
            "application/json; version=2; q=0.8, " "application/json; version=3; q=0.9"
        ),
    )
    assert _header_version(request, "Accept-Version") == 3

    tied = RequestFactory().get(
        "/",
        HTTP_ACCEPT=(
            "application/json; version=2; q=0.8, " "application/json; version=3; q=0.8"
        ),
    )
    with pytest.raises(ValueError, match="equally preferred conflicting"):
        _header_version(tied, "Accept-Version")

    zero_quality = RequestFactory().get(
        "/", HTTP_ACCEPT="application/json; version=2; q=0"
    )
    with pytest.raises(_UnsupportedVersion):
        _header_version(zero_quality, "Accept-Version")


def test_negotiation_query_and_hostname_transports_validate_inputs():
    duplicate_query = RequestFactory().get("/?version=2&version=3")
    with pytest.raises(ValueError, match="must appear once"):
        VersionNegotiationMiddleware._requested_version(duplicate_query, "query")

    with pytest.raises(ValueError, match="conflict"):
        _header_version(
            RequestFactory().get(
                "/",
                HTTP_ACCEPT="application/json; version=3",
                HTTP_ACCEPT_VERSION="2",
            ),
            "Accept-Version",
        )


def test_lifecycle_version_coercion_and_ambiguous_path_fallbacks():
    assert _coerce_version(0) == 0
    assert _coerce_version("02") == 2
    assert _coerce_version(True) is None
    assert _coerce_version(-1) is None
    assert _coerce_version("٢") is None
    assert _coerce_version("9" * 1000) == int("9" * 1000)

    assert _extract_version_from_value("api/v2/orders/api/v2/items/") == 2
    assert _extract_version_from_value("api/v2/orders/api/v3/items/") is None


def test_lifecycle_date_normalization_and_structured_date_flooring():
    assert _parse_lifecycle_date("0001-01-01T00:00:00+23:59", "sunset") is None
    before_epoch = datetime(1969, 12, 31, 23, 59, 59, 500000, tzinfo=timezone.utc)
    assert _to_structured_field_date(before_epoch) == "@-1"


def test_lifecycle_past_boundary_is_strict(monkeypatch):
    import django_api_versioning.lifecycle as lifecycle_module

    fixed_now = datetime(2030, 1, 1, tzinfo=timezone.utc)

    class FrozenDateTime:
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(lifecycle_module, "datetime", FrozenDateTime)
    assert _is_past(fixed_now) is False
    assert _is_past(datetime(2029, 12, 31, tzinfo=timezone.utc)) is True


def test_lifecycle_405_resolution_uses_a_separate_cache(monkeypatch):
    calls = []

    def resolve_operation(match, method, *, allow_unmapped_method=False):
        calls.append(allow_unmapped_method)
        return "405" if allow_unmapped_method else "normal"

    monkeypatch.setattr(registry, "resolve_operation", resolve_operation)
    monkeypatch.setattr(registry, "get_endpoint_lifecycle", lambda operation: operation)
    request = SimpleNamespace(resolver_match=object(), method="GET")

    assert _get_endpoint_lifecycle_state(request) == "normal"
    assert _get_endpoint_lifecycle_state(request, allow_unmapped_method=True) == "405"
    assert calls == [False, True]


def test_registry_source_version_replacement_is_last_write_only_when_unversioned():
    target = UrlRegistry()
    existing = path("orders/", _view)
    setattr(existing, target._SOURCE_VERSION_ATTR, 3)

    assert target._should_replace(existing, None) is True
    assert target._should_replace(existing, 2) is False
    assert target._should_replace(existing, 3) is True
    assert target._should_replace(existing, 4) is True

    setattr(existing, target._SOURCE_VERSION_ATTR, None)
    assert target._should_replace(existing, 1) is True


def test_registry_lifecycle_registration_validates_identity_scope_and_conflicts():
    target = UrlRegistry()

    with pytest.raises(
        VersioningError, match="logical_endpoint must be a non-empty string"
    ):
        target.register_endpoint_lifecycle("", 2)
    with pytest.raises(VersionTypeError, match="version must be an integer"):
        target.register_endpoint_lifecycle("orders", True)
    with pytest.raises(VersionRangeError):
        target.register_endpoint_lifecycle("orders", 0)
    with pytest.raises(InvalidVersionError):
        target.register_endpoint_lifecycle("orders", api_settings.API_MAX_VERSION + 1)
    with pytest.raises(VersioningError, match="method must be a string"):
        target.register_endpoint_lifecycle("orders", 2, method="")
    with pytest.raises(VersioningError, match="action must be a string"):
        target.register_endpoint_lifecycle("orders", 2, action="")

    target.register_endpoint_lifecycle(
        "orders",
        2,
        method="GET",
        action="list",
        deprecated_at="2027-01-01T00:00:00Z",
    )
    with pytest.raises(VersioningError, match="Conflicting endpoint lifecycle"):
        target.register_endpoint_lifecycle(
            "orders",
            2,
            method="GET",
            action="list",
            deprecated_at="2028-01-01T00:00:00Z",
        )


def test_router_removal_does_not_cross_trailing_slash_ownership():
    class OrdersViewSet(ViewSet):
        def list(self, request):
            return None

    slash_router = VersionedRouter(trailing_slash=True)
    no_slash_router = VersionedRouter(trailing_slash=False)
    slash_router.register("orders", OrdersViewSet, version=1, basename="order")
    no_slash_router.register("orders", OrdersViewSet, version=1, basename="order")
    no_slash_patterns = [
        pattern
        for pattern in registry.urlpatterns
        if getattr(pattern, registry._ROUTER_OWNER_ATTR, None)
        is no_slash_router._registry_owner
    ]
    assert no_slash_patterns

    slash_router.remove("orders", "order-list", from_version=1)

    assert all(pattern in registry.urlpatterns for pattern in no_slash_patterns)


def test_nested_router_namespace_uses_the_innermost_version():
    versioning = VersionedRouterVersioning()
    versioning.default_version = "1"
    versioning.allowed_versions = ["1", "3"]
    request = SimpleNamespace(
        resolver_match=SimpleNamespace(route=None, namespace="outer:v2:v3")
    )

    assert versioning.determine_version(request) == "3"


def test_decorator_lifecycle_rolls_back_earlier_methods_on_late_conflict():
    registry.register_endpoint_lifecycle(
        "orders/",
        2,
        method="POST",
        deprecated_at="2027-01-01T00:00:00Z",
    )
    before = dict(registry._endpoint_lifecycle)

    with pytest.raises(VersioningError, match="Conflicting endpoint lifecycle"):
        set_endpoint_lifecycle(
            "orders/",
            version=2,
            methods=["GET", "POST"],
            deprecated_at="2028-01-01T00:00:00Z",
        )

    assert registry._endpoint_lifecycle == before


def test_negotiation_accept_version_header_and_hostname_mapping():
    dedicated = RequestFactory().get("/", HTTP_ACCEPT_VERSION="2")
    assert _header_version(dedicated, "Accept-Version") == 2

    with override_settings(
        ALLOWED_HOSTS=["example.com"],
        API_VERSIONING_HOSTS={"example.com": 2},
    ):
        request = RequestFactory().get("/", HTTP_HOST="example.com")
        assert VersionNegotiationMiddleware._requested_version(request, "hostname") == 2


urlpatterns = [path("api/v2/orders/", _view, name="order-list")]


def test_router_reverse_uses_underlying_api_version_when_request_version_is_missing():
    with override_settings(
        ROOT_URLCONF=__name__,
        API_BASE_PATH="api/v{version}/",
        API_UNVERSIONED_BASE_PATH="api/",
    ):
        django_request = RequestFactory().get("/")
        django_request.resolver_match = SimpleNamespace(namespace="")
        django_request.api_version = 2
        django_request.api_versioning_scheme = "query"
        request = Request(django_request)
        request.version = None

        url = VersionedRouterVersioning().reverse("order-list", request=request)

    assert url.endswith("/api/orders/?version=2")


def test_registry_remove_validates_all_version_boundaries_and_tombstones(monkeypatch):
    target = UrlRegistry()
    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 1)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)

    with pytest.raises(TypeError, match="logical_endpoint must be a non-empty string"):
        target.remove("", 1)
    with pytest.raises(VersionTypeError, match="Removal version must be an integer"):
        target.remove("orders", True)
    with pytest.raises(VersionRangeError, match="below the minimum allowed version"):
        target.remove("orders", 0)
    with pytest.raises(InvalidVersionError, match="above the maximum allowed version"):
        target.remove("orders", 6)

    target.register(
        "api/v5/orders/",
        _view,
        name="order-list",
        source_version=1,
        route_version=5,
        logical_endpoint="orders:order-list",
    )
    target.remove("orders:order-list", 5)

    assert target._removal_boundary("orders:order-list", 5) == 5
    assert target.get_route_version("api/v5/orders/") is None
    assert target.get_version_matrix()["api/v5/orders/"][5] is REMOVED_ROUTE
    assert target.get_logical_version_matrix()["orders:order-list"][5] is REMOVED_ROUTE


def test_registry_pattern_identity_constants_and_dataclass_shape_are_stable():
    assert UrlRegistry._SOURCE_VERSION_ATTR == "_django_api_versioning_source_version"
    assert UrlRegistry._ROUTE_VERSION_ATTR == "_django_api_versioning_route_version"
    assert UrlRegistry._LOGICAL_ENDPOINT_ATTR == (
        "_django_api_versioning_logical_endpoint"
    )
    assert UrlRegistry._ROUTER_OWNER_ATTR == "_django_api_versioning_router_owner"
    assert UrlRegistry._ROUTER_PREFIX_ATTR == "_django_api_versioning_router_prefix"
    assert (
        UrlRegistry._ROUTER_TRAILING_SLASH_ATTR
        == "_django_api_versioning_router_trailing_slash"
    )
    assert ResolvedOperation.__dataclass_params__.frozen is True
    assert "__slots__" in ResolvedOperation.__dict__

    for method in (
        UrlRegistry.clear,
        UrlRegistry.remove,
        UrlRegistry.register,
        UrlRegistry.register_urlpattern,
        UrlRegistry.get_route_version,
        UrlRegistry.get_version_matrix,
        UrlRegistry.get_logical_version_matrix,
        UrlRegistry.resolve_operation,
    ):
        assert method.__name__ == method.__wrapped__.__name__


def test_registry_register_urlpattern_preserves_regex_pattern_and_route_version():
    target = UrlRegistry()
    pattern = re_path(r"^api/v2/orders/$", _view, name="order-list")

    target.register_urlpattern(
        pattern,
        source_version=1,
        route_version=2,
        logical_endpoint="orders:order-list",
    )

    assert target.urlpatterns == [pattern]
    assert target.urlpatterns[0] is pattern
    assert target.urlpatterns[0].callback is _view
    assert target.get_route_version(r"^api/v2/orders/$") == 2
    assert target.get_route_version("api/v2/orders/") == 2
    assert target.get_route_version("api/v3/orders/") is None


def test_registry_logical_matrix_disambiguates_router_ownership_and_slash_policy():
    target = UrlRegistry()
    slash_owner = object()
    no_slash_owner = object()
    slash = _registered_pattern(
        target, owner=slash_owner, prefix="orders", trailing_slash=True
    )
    no_slash = _registered_pattern(
        target, owner=no_slash_owner, prefix="orders", trailing_slash=False
    )
    target.urlpatterns.extend((slash, no_slash))

    matrix = target.get_logical_version_matrix()

    assert (
        matrix["orders:order-list [router='orders', trailing_slash=True]"][2] is _view
    )
    assert (
        matrix["orders:order-list [router='orders', trailing_slash=False]"][2] is _view
    )
    assert len(matrix) == 2


def test_registry_resolve_operation_normalizes_methods_and_rejects_bad_actions():
    target = UrlRegistry()

    def callback(request):
        return None

    callback.actions = {"get": "list", "post": "create"}
    pattern = _registered_pattern(target, callback)
    target.urlpatterns.append(pattern)
    match = SimpleNamespace(
        route="api/v2/orders/",
        func=callback,
        url_name="order-list",
        tried=[[pattern]],
        namespaces=("v2",),
        namespace="v2",
    )

    operation = target.resolve_operation(match, "get")
    assert operation is not None
    assert operation.method == "GET"
    assert operation.action == "list"
    assert target.resolve_operation(match, "OPTIONS").action is None
    assert target.resolve_operation(match, "PATCH") is None
    assert (
        target.resolve_operation(match, "PATCH", allow_unmapped_method=True).action
        is None
    )

    callback.actions = {"get": ""}
    assert target.resolve_operation(match, "GET") is None


def test_registry_lifecycle_metadata_isolated_by_router_owner():
    target = UrlRegistry()
    first_owner = object()
    second_owner = object()
    target.register_endpoint_lifecycle(
        "orders:order-list",
        2,
        deprecated_at="2027-01-01T00:00:00Z",
        owner=first_owner,
    )
    target.register_endpoint_lifecycle(
        "orders:order-list",
        2,
        deprecated_at="2028-01-01T00:00:00Z",
        owner=second_owner,
    )

    def operation(owner):
        return ResolvedOperation(
            logical_endpoint="orders:order-list",
            route_version=2,
            source_version=2,
            method="GET",
            action="list",
            route_name="order-list",
            namespace="v2",
            route="api/v2/orders/",
            registered_route="api/v2/orders/",
            router_owner=owner,
        )

    first = target.get_endpoint_lifecycle(operation(first_owner))
    second = target.get_endpoint_lifecycle(operation(second_owner))

    assert first.deprecated_at == datetime(2027, 1, 1, tzinfo=timezone.utc)
    assert second.deprecated_at == datetime(2028, 1, 1, tzinfo=timezone.utc)


def test_router_transaction_wrappers_preserve_public_method_metadata():
    for method in (
        VersionedRouter.register,
        VersionedRouter.remove,
        VersionedRouter.set_lifecycle,
    ):
        assert method.__name__ == method.__wrapped__.__name__


def test_router_remove_validates_version_before_checking_ownership(monkeypatch):
    router = VersionedRouter()
    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 1)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)

    with pytest.raises(VersionTypeError, match="Version must be an integer"):
        router.remove("orders", "order-list", from_version=True)
    with pytest.raises(VersionRangeError, match="below API_MIN_VERSION"):
        router.remove("orders", "order-list", from_version=0)
    with pytest.raises(InvalidVersionError, match="above the maximum allowed version"):
        router.remove("orders", "order-list", from_version=6)


def test_router_collects_only_owned_versioned_and_unversioned_patterns():
    class OrdersViewSet(ViewSet):
        def list(self, request):
            return None

    first = VersionedRouter()
    second = VersionedRouter()
    first.register("orders", OrdersViewSet, version=2, basename="order")
    second.register("invoices", OrdersViewSet, version=2, basename="invoice")
    first.register("health", OrdersViewSet, basename="health")

    versioned, unversioned = first._collect_registered_patterns()

    assert set(versioned) == set(range(2, api_settings.API_MAX_VERSION + 1))
    assert all(
        getattr(pattern, registry._ROUTER_OWNER_ATTR) is first._registry_owner
        for patterns in versioned.values()
        for pattern in patterns
    )
    assert unversioned
    assert all(pattern.name.startswith("health-") for pattern in unversioned)
    assert all(
        getattr(pattern, registry._ROUTER_OWNER_ATTR) is not second._registry_owner
        for patterns in versioned.values()
        for pattern in patterns
    )


def test_router_versioning_rejects_disallowed_namespace_version():
    versioning = VersionedRouterVersioning()
    versioning.default_version = "1"
    versioning.allowed_versions = ["1", "2"]
    request = SimpleNamespace(
        resolver_match=SimpleNamespace(route=None, namespace="outer:v9")
    )
    with pytest.raises(NotFound, match="allowed API version"):
        versioning.determine_version(request)


def test_router_versioning_resolves_nested_registered_route_from_resolver_trace():
    pattern = _registered_pattern(registry, version=2)
    registry.urlpatterns.append(pattern)
    versioning = VersionedRouterVersioning()
    versioning.default_version = "1"
    versioning.allowed_versions = ["1", "2"]
    request = SimpleNamespace(
        resolver_match=SimpleNamespace(
            route="outer/api/v2/orders/",
            func=pattern.callback,
            url_name=pattern.name,
            tried=[[pattern]],
            namespaces=("outer", "v2"),
            namespace="outer:v2",
        )
    )

    assert versioning.determine_version(request) == "2"


def test_negotiation_path_version_zero_and_template_validation_are_exact():
    assert _parse_version(" 0002 ") == 2
    assert _path_version("/api/v0/orders/", "api/v{version}/") == 0
    assert _path_version("/api/v2/orders/", "api/v{version}/") == 2
    assert _path_version("/api/v2/orders/", "api/v{version}/{version}/") is None
    assert _path_version("/api/v2/orders/", "api/v{version}/extra/") is None

    with pytest.raises(ValueError, match="ASCII decimal integer"):
        _parse_version(None)
    with pytest.raises(ValueError, match="ASCII decimal integer"):
        _parse_version(True)


def test_negotiation_quoted_header_parser_handles_escaped_delimiters_and_controls():
    header = r'profile="one\,two;three"; version=2, application/json'
    assert _split_quoted_header(header, ",") == [
        r'profile="one\,two;three"; version=2',
        " application/json",
    ]
    assert _parse_accept_parameter_value("token") == ("token", False)
    assert _parse_accept_parameter_value('"one two"') == ("one two", True)
    assert _parse_accept_parameter_value('""') == ("", True)
    assert _parse_accept_parameter_value('"one\ttwo"') == ("one\ttwo", True)

    with pytest.raises(ValueError, match="unterminated quoted parameter"):
        _split_quoted_header('profile="unterminated', ",")
    with pytest.raises(ValueError, match="invalid quoted parameter"):
        _parse_accept_parameter_value('"one\x01two"')
    with pytest.raises(ValueError, match="invalid quoted parameter"):
        _parse_accept_parameter_value('"one\x7ftwo"')
    with pytest.raises(ValueError, match="invalid media parameter value"):
        _parse_accept_parameter_value("token with space")


def test_negotiation_media_ranges_validate_wildcards_quality_and_duplicates():
    assert _parse_accept_media_range("*/*; version=2") == ("2", 1.0)
    assert _parse_accept_media_range("application/json; version=2; q=0.5") == (
        "2",
        0.5,
    )

    with pytest.raises(ValueError, match="invalid media range"):
        _parse_accept_media_range("*/json; version=2")
    with pytest.raises(ValueError, match="invalid quality value"):
        _parse_accept_media_range('application/json; q="0.5"')
    with pytest.raises(ValueError, match="invalid quality value"):
        _parse_accept_media_range("application/json; q=0.5; q=0.7")
    with pytest.raises(ValueError, match="duplicate version parameters"):
        _parse_accept_media_range("application/json; version=2; VERSION=3")


def test_negotiation_header_selection_checks_dedicated_header_and_accept_conflicts():
    dedicated_only = RequestFactory().get("/", HTTP_ACCEPT_VERSION="2")
    assert _header_version(dedicated_only, "Accept-Version") == 2

    matching = RequestFactory().get(
        "/",
        HTTP_ACCEPT_VERSION="2",
        HTTP_ACCEPT="application/json; version=2",
    )
    assert _header_version(matching, "Accept-Version") == 2

    with pytest.raises(ValueError, match="conflict"):
        _header_version(
            RequestFactory().get(
                "/",
                HTTP_ACCEPT_VERSION="2",
                HTTP_ACCEPT="application/json; version=3",
            ),
            "Accept-Version",
        )


def test_negotiation_middleware_rewrites_every_django_path_representation():
    with override_settings(
        API_VERSIONING_SCHEME="query",
        API_UNVERSIONED_BASE_PATH="api/",
        API_BASE_PATH="api/v{version}/",
        API_VERSIONING_QUERY_PARAMETER="v",
        API_DEFAULT_VERSION=None,
        API_MIN_VERSION=1,
        API_MAX_VERSION=3,
    ):
        request = RequestFactory().get("/api/orders/?v=2")
        response = VersionNegotiationMiddleware(lambda current: HttpResponse("ok"))(
            request
        )

    assert response.status_code == 200
    assert request.original_path_info == "/api/orders/"
    assert request.path_info == "/api/v2/orders/"
    assert request.META["PATH_INFO"] == "/api/v2/orders/"
    assert request.path == "/api/v2/orders/"
    assert request.requested_api_version == 2
    assert request.api_version == 2
    assert request.version == "2"
    assert request._django_api_version_negotiated is True


def test_negotiation_path_scheme_preserves_zero_and_header_scheme_sets_vary():
    with override_settings(
        API_VERSIONING_SCHEME="path",
        API_BASE_PATH="api/v{version}/",
    ):
        request = RequestFactory().get("/api/v0/orders/")
        VersionNegotiationMiddleware(lambda current: HttpResponse("ok"))(request)

    assert request.requested_api_version == 0
    assert request.api_version == 0
    assert request.version == "0"

    with override_settings(
        API_VERSIONING_SCHEME="header",
        API_VERSIONING_HEADER="Accept-Version",
    ):
        response = VersionNegotiationMiddleware(lambda current: HttpResponse("ok"))(
            RequestFactory().get("/unrelated/")
        )

    assert set(response.headers["Vary"].split(", ")) == {"Accept-Version", "Accept"}


def test_negotiation_hostname_lookup_keeps_django_allowed_hosts_validation():
    request = RequestFactory().get("/", HTTP_HOST="evil.example")
    with override_settings(ALLOWED_HOSTS=["example.com"]):
        with pytest.raises(DisallowedHost):
            VersionNegotiationMiddleware._requested_version(request, "hostname")


def test_lifecycle_process_response_requests_route_only_resolution_for_405():
    calls = []

    def resolve_operation(match, method, *, allow_unmapped_method=False):
        calls.append((method, allow_unmapped_method))
        return None

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(registry, "resolve_operation", resolve_operation)
    try:
        request = SimpleNamespace(
            resolver_match=object(),
            method="PATCH",
            path_info="/unrelated/",
            path="/unrelated/",
        )
        response = LifecycleMiddleware(
            lambda current: HttpResponse(status=405)
        ).process_response(request, HttpResponse(status=405))
    finally:
        monkeypatch.undo()

    assert response.status_code == 405
    assert calls == [("PATCH", True)]


def test_set_and_remove_endpoint_lifecycle_validate_absolute_postfix_and_app_prefix():
    with pytest.raises(
        VersioningError,
        match="postfix must be relative and must not start with",
    ):
        set_endpoint_lifecycle("/orders/", version=2)
    with pytest.raises(
        VersioningError,
        match="postfix must be relative and must not start with",
    ):
        remove_endpoint("/orders/", from_version=2)

    set_endpoint_lifecycle(
        "orders/",
        version=2,
        app_name="billing",
        deprecated_at="2027-01-01T00:00:00Z",
    )
    remove_endpoint("orders/", from_version=2, app_name="billing")


def _assert_exact_exception(exception_type, message, operation):
    with pytest.raises(exception_type) as captured:
        operation()
    assert str(captured.value) == message


def test_mutation95_decorator_validation_and_warning_contracts(monkeypatch, caplog):
    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 2)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)

    _assert_exact_exception(
        TypeError,
        "app_name must be a string or None.",
        lambda: _app_name_prefix(1),
    )
    _assert_exact_exception(
        VersioningError,
        "app_name must not have leading or trailing whitespace.",
        lambda: _app_name_prefix(" billing"),
    )
    _assert_exact_exception(
        VersioningError,
        "app_name must be a relative path without empty, '.' or '..' segments.",
        lambda: _app_name_prefix("billing//v1"),
    )
    _assert_exact_exception(
        VersionRangeError,
        "ver_range start (2) must be <= end (1).",
        lambda: ver_range(2, 1),
    )
    _assert_exact_exception(
        VersionRangeError,
        "ver_range start must be a non-negative API version.",
        lambda: ver_range(-1, 1),
    )
    _assert_exact_exception(
        InvalidVersionError,
        "Version 6 is above the maximum allowed version 5.",
        lambda: ver_range(0, 6),
    )
    _assert_exact_exception(
        VersionTypeError,
        "ver_range start must be an integer.",
        lambda: ver_range(True, 2),
    )
    _assert_exact_exception(
        VersioningError,
        "postfix must be relative and must not start with '/'.",
        lambda: endpoint("/orders/"),
    )
    _assert_exact_exception(
        VersionRangeError,
        "Use either 'version' or 'versions', not both.",
        lambda: endpoint("orders/", version=2, versions=[2]),
    )
    _assert_exact_exception(
        VersionTypeError,
        "'versions' must be a list of integers.",
        lambda: endpoint("orders/", versions="2"),
    )
    _assert_exact_exception(
        VersioningError,
        "postfix must be relative and must not start with '/'.",
        lambda: set_endpoint_lifecycle("/orders/", version=2),
    )
    _assert_exact_exception(
        VersioningError,
        "methods must be a non-empty list of HTTP methods.",
        lambda: set_endpoint_lifecycle("orders/", version=2, methods=[]),
    )
    _assert_exact_exception(
        VersioningError,
        "methods must contain non-empty HTTP method strings.",
        lambda: set_endpoint_lifecycle("orders/", version=2, methods=["GET", 1]),
    )
    _assert_exact_exception(
        VersioningError,
        "methods must not contain duplicates.",
        lambda: set_endpoint_lifecycle(
            "orders/", version=2, methods=["GET", " get "]
        ),
    )
    _assert_exact_exception(
        VersioningError,
        "postfix must be relative and must not start with '/'.",
        lambda: remove_endpoint("/orders/", from_version=2),
    )

    caplog.clear()
    with caplog.at_level("WARNING"):
        endpoint("old/", version=1)(_view)
    assert [record.getMessage() for record in caplog.records] == [
        "Endpoint 'old/' is declared for version 1, but API_MIN_VERSION is 2. "
        "No routes will be registered."
    ]

    caplog.clear()
    with caplog.at_level("WARNING"):
        endpoint("orders/", versions=[1, 3])(_view)
    assert [record.getMessage() for record in caplog.records] == [
        "Endpoint 'orders/' is declared for version 1, but API_MIN_VERSION is 2. "
        "Skipping this version."
    ]
    assert {
        getattr(pattern, registry._ROUTE_VERSION_ATTR, None)
        for pattern in registry.urlpatterns
    } == {3}


def test_mutation95_decorator_preserves_drf_viewset_class_metadata():
    class OrdersViewSet(ViewSet):
        def list(self, request):
            return None

    callback = OrdersViewSet.as_view({"get": "list"})
    endpoint("orders/", version=2)(callback)

    attribute = registry._LOGICAL_ENDPOINT_ATTR
    assert getattr(callback, attribute) == "orders/"
    assert getattr(OrdersViewSet, attribute) == "orders/"
    assert any(
        str(pattern.pattern) == "api/v2/orders/" and pattern.callback is callback
        for pattern in registry.urlpatterns
    )


def test_mutation95_router_validation_errors_are_exact(monkeypatch):
    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 1)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)

    class OrdersViewSet(ViewSet):
        def list(self, request):
            return None

    _assert_exact_exception(
        VersioningError,
        "app_name must be a non-empty string.",
        lambda: VersionedRouter(app_name=" "),
    )
    _assert_exact_exception(
        TypeError,
        "trailing_slash must be a bool.",
        lambda: VersionedRouter(trailing_slash=1),
    )
    _assert_exact_exception(
        TypeError,
        "use_regex_path must be a bool.",
        lambda: VersionedRouter(use_regex_path=1),
    )

    router = VersionedRouter()
    _assert_exact_exception(
        TypeError,
        "prefix must be a string.",
        lambda: router.register(1, OrdersViewSet),
    )
    _assert_exact_exception(
        VersioningError,
        "prefix must be a non-empty relative path without leading or trailing '/'.",
        lambda: router.register("/orders", OrdersViewSet),
    )
    _assert_exact_exception(
        VersionRangeError,
        "Use either 'version' or 'versions', not both.",
        lambda: router.register("orders", OrdersViewSet, version=1, versions=[1]),
    )
    _assert_exact_exception(
        VersionTypeError,
        "'versions' must be a list of integers.",
        lambda: router.register("orders", OrdersViewSet, versions=(1, 2)),
    )
    _assert_exact_exception(
        VersionRangeError,
        "'versions' must not contain duplicates.",
        lambda: router.register("orders", OrdersViewSet, versions=[1, 1]),
    )
    _assert_exact_exception(
        TypeError,
        "route_name must be a string.",
        lambda: router.remove("orders", 1, from_version=1),
    )
    _assert_exact_exception(
        VersioningError,
        "route_name must be a non-empty string.",
        lambda: router.remove("orders", "", from_version=1),
    )
    _assert_exact_exception(
        VersionTypeError,
        "Version must be an integer.",
        lambda: router.remove("orders", "order-list", from_version=True),
    )
    _assert_exact_exception(
        VersionRangeError,
        "Removal version 0 is below API_MIN_VERSION 1.",
        lambda: router.remove("orders", "order-list", from_version=0),
    )
    _assert_exact_exception(
        InvalidVersionError,
        "Version 6 is above the maximum allowed version 5.",
        lambda: router.remove("orders", "order-list", from_version=6),
    )
    _assert_exact_exception(
        VersioningError,
        "Router does not own an active route for 'orders:order-list'.",
        lambda: router.remove("orders", "order-list", from_version=1),
    )
    _assert_exact_exception(
        VersioningError,
        "Expected one registered route for 'orders:order-list' in version 1; found 0.",
        lambda: router.set_lifecycle("orders", "order-list", version=1),
    )

    _assert_exact_exception(
        VersioningError,
        "methods must not contain duplicates.",
        lambda: VersionedRouter._resolve_lifecycle_methods(
            ["GET", " get "], {"get": "list"}, None, "orders:order-list"
        ),
    )
    _assert_exact_exception(
        VersioningError,
        "HTTP method 'PATCH' is not registered for 'orders:order-list'.",
        lambda: VersionedRouter._resolve_lifecycle_methods(
            ["PATCH"], {"get": "list"}, None, "orders:order-list"
        ),
    )
    _assert_exact_exception(
        VersioningError,
        "HTTP method 'POST' maps to action 'create', not 'list'.",
        lambda: VersionedRouter._resolve_lifecycle_methods(
            ["POST"], {"post": "create"}, "list", "orders:order-list"
        ),
    )


def test_mutation95_registry_validation_and_registration_errors_are_exact(monkeypatch):
    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 1)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)
    target = UrlRegistry()

    _assert_exact_exception(
        TypeError,
        "logical_endpoint must be a non-empty string.",
        lambda: target.remove("", 1),
    )
    _assert_exact_exception(
        VersionTypeError,
        "Removal version must be an integer.",
        lambda: target.remove("orders", True),
    )
    _assert_exact_exception(
        InvalidVersionError,
        "Removal version 6 is above the maximum allowed version 5.",
        lambda: target.remove("orders", 6),
    )
    _assert_exact_exception(
        VersionRangeError,
        "Removal version 0 is below the minimum allowed version 1.",
        lambda: target.remove("orders", 0),
    )
    _assert_exact_exception(
        TypeError,
        "pattern must be a django.urls.URLPattern instance.",
        lambda: target.register_urlpattern(object()),
    )
    _assert_exact_exception(
        VersioningError,
        "logical_endpoint must be a non-empty string.",
        lambda: target.register_endpoint_lifecycle("", 2),
    )
    _assert_exact_exception(
        VersionTypeError,
        "Endpoint lifecycle version must be an integer.",
        lambda: target.register_endpoint_lifecycle("orders", True),
    )
    _assert_exact_exception(
        VersionRangeError,
        "Endpoint lifecycle version 0 is below API_MIN_VERSION 1.",
        lambda: target.register_endpoint_lifecycle("orders", 0),
    )
    _assert_exact_exception(
        InvalidVersionError,
        "Endpoint lifecycle version 6 is above API_MAX_VERSION 5.",
        lambda: target.register_endpoint_lifecycle("orders", 6),
    )
    _assert_exact_exception(
        VersioningError,
        "Endpoint lifecycle method must be a string.",
        lambda: target.register_endpoint_lifecycle("orders", 2, method=" "),
    )
    _assert_exact_exception(
        VersioningError,
        "Endpoint lifecycle action must be a string.",
        lambda: target.register_endpoint_lifecycle("orders", 2, action=" "),
    )

    target.register_endpoint_lifecycle(
        "orders", 2, deprecated_at="2027-01-01T00:00:00Z"
    )
    _assert_exact_exception(
        VersioningError,
        "Conflicting endpoint lifecycle declarations for 'orders' version 2.",
        lambda: target.register_endpoint_lifecycle(
            "orders", 2, deprecated_at="2028-01-01T00:00:00Z"
        ),
    )

    class OrdersViewSet(ViewSet):
        def list(self, request):
            return None

    router = VersionedRouter()
    router.register("orders", OrdersViewSet, version=1, basename="order")
    _assert_exact_exception(
        VersioningError,
        "Route pattern 'api/v1/orders/' is already owned by a VersionedRouter; "
        "decorator registration cannot replace it.",
        lambda: registry.register(
            "api/v1/orders/", _view, name="order-list", route_version=1
        ),
    )

    _assert_exact_exception(
        TypeError,
        "Pass the view class 'View', not an instance. Use @endpoint(...) on the "
        "class itself, or call View.as_view() before registering.",
        lambda: UrlRegistry._create_pattern("orders/", View(), "orders"),
    )


def test_mutation95_negotiation_parser_errors_are_exact():
    _assert_exact_exception(
        ValueError,
        "A version must be an ASCII decimal integer.",
        lambda: _parse_version(None),
    )
    _assert_exact_exception(
        ValueError,
        "Accept contains an unterminated quoted parameter.",
        lambda: _split_quoted_header('profile="unfinished', ";"),
    )
    _assert_exact_exception(
        ValueError,
        "Accept contains an empty media parameter value.",
        lambda: _parse_accept_parameter_value(" "),
    )
    _assert_exact_exception(
        ValueError,
        "Accept contains an invalid quoted parameter.",
        lambda: _parse_accept_parameter_value('"unfinished'),
    )
    _assert_exact_exception(
        ValueError,
        "Accept contains an invalid quoted parameter.",
        lambda: _parse_accept_parameter_value('"bad\x01value"'),
    )
    _assert_exact_exception(
        ValueError,
        "Accept contains an invalid media parameter value.",
        lambda: _parse_accept_parameter_value("not a token"),
    )
    _assert_exact_exception(
        ValueError,
        "Accept contains an invalid media range.",
        lambda: _parse_accept_media_range("*/json; version=2"),
    )
    _assert_exact_exception(
        ValueError,
        "Accept contains an invalid media parameter.",
        lambda: _parse_accept_media_range("application/json; version"),
    )
    _assert_exact_exception(
        ValueError,
        "Accept contains an invalid quality value.",
        lambda: _parse_accept_media_range("application/json; q=0.5; q=0.7"),
    )
    _assert_exact_exception(
        ValueError,
        "Accept contains duplicate version parameters.",
        lambda: _parse_accept_media_range(
            "application/json; version=2; VERSION=3"
        ),
    )
    _assert_exact_exception(
        ValueError,
        "Accept contains equally preferred conflicting API versions.",
        lambda: _header_version(
            RequestFactory().get(
                "/",
                HTTP_ACCEPT=(
                    "application/json; version=2; q=0.8, "
                    "application/json; version=3; q=0.8"
                ),
            ),
            "Accept-Version",
        ),
    )
    _assert_exact_exception(
        ValueError,
        "Accept-Version and Accept media-type version parameters conflict.",
        lambda: _header_version(
            RequestFactory().get(
                "/",
                HTTP_ACCEPT_VERSION="2",
                HTTP_ACCEPT="application/json; version=3",
            ),
            "Accept-Version",
        ),
    )


def test_mutation95_negotiation_middleware_response_contracts_are_exact():
    middleware = VersionNegotiationMiddleware(lambda request: HttpResponse("ok"))
    common = {
        "API_VERSIONING_SCHEME": "query",
        "API_VERSIONING_QUERY_PARAMETER": "version",
        "API_UNVERSIONED_BASE_PATH": "api/",
        "API_BASE_PATH": "api/v{version}/",
        "API_DEFAULT_VERSION": None,
        "API_MIN_VERSION": 1,
        "API_MAX_VERSION": 3,
    }

    with override_settings(**common):
        missing = middleware(RequestFactory().get("/api/orders/"))
        invalid = middleware(RequestFactory().get("/api/orders/?version=abc"))
        unsupported = middleware(RequestFactory().get("/api/orders/?version=4"))
        path_version = middleware(RequestFactory().get("/api/v2/orders/"))

    assert (missing.status_code, missing.content) == (
        400,
        b"An API version is required for this endpoint.",
    )
    assert (invalid.status_code, invalid.content) == (
        400,
        b"Invalid API version value.",
    )
    assert (unsupported.status_code, unsupported.content) == (
        406,
        b"The requested API version is not supported.",
    )
    assert (path_version.status_code, path_version.content) == (
        400,
        b"This deployment does not accept URL-path API versions.",
    )

    with override_settings(
        API_VERSIONING_SCHEME="hostname",
        API_UNVERSIONED_BASE_PATH="api/",
        API_BASE_PATH="api/v{version}/",
        API_DEFAULT_VERSION=None,
        API_VERSIONING_HOSTS={"example.com": 2},
        ALLOWED_HOSTS=["example.com", "other.example"],
    ):
        response = middleware(
            RequestFactory().get("/api/orders/", HTTP_HOST="other.example")
        )
    assert (response.status_code, response.content) == (
        406,
        b"The requested API version is not available for this host.",
    )

    with override_settings(
        API_VERSIONING_SCHEME="header",
        API_VERSIONING_HEADER="Accept-Version",
        API_UNVERSIONED_BASE_PATH="api/",
        API_BASE_PATH="api/v{version}/",
        API_DEFAULT_VERSION=None,
    ):
        response = middleware(
            RequestFactory().get("/api/orders/", HTTP_ACCEPT_VERSION="not-a-version")
        )
    assert (response.status_code, response.content) == (
        400,
        b"Invalid API version value.",
    )


def test_mutation95_lifecycle_default_resolution_and_response_contracts(
    monkeypatch, caplog
):
    calls = []

    def resolve_operation(match, method, *, allow_unmapped_method=False):
        calls.append((method, allow_unmapped_method))
        return None

    monkeypatch.setattr(registry, "resolve_operation", resolve_operation)
    request = SimpleNamespace(resolver_match=object(), method="PATCH")
    assert _get_endpoint_lifecycle_state(request) is None
    assert calls == [("PATCH", False)]

    with override_settings(
        API_VERSION_LIFECYCLE={
            2: {
                "status": "retired",
                "sunset": "2000-01-01T00:00:00Z",
            }
        }
    ):
        expired_request = RequestFactory().get("/api/v2/orders/")
        gone = LifecycleMiddleware(lambda current: HttpResponse("ok")).process_view(
            expired_request, _view, [], {}
        )
    assert gone.status_code == 410
    assert gone.content == b"API version 2 has been retired as of 2000-01-01T00:00:00Z."

    caplog.clear()
    with override_settings(
        API_VERSION_LIFECYCLE={
            2: {
                "status": "deprecated",
                "deprecated_at": "not-a-date",
            }
        }
    ):
        invalid_date_request = RequestFactory().get("/api/v2/orders/")
        original_response = HttpResponse("ok")
        response = LifecycleMiddleware(lambda current: current).process_response(
            invalid_date_request, original_response
        )
    assert response is original_response
    assert [record.getMessage() for record in caplog.records] == [
        "Invalid deprecation date 'not-a-date'; ignoring.",
        "Deprecated API version 2 has no valid deprecated_at date; "
        "omitting the Deprecation header.",
    ]

    no_version_request = RequestFactory().get("/health/")
    untouched = HttpResponse("unchanged", status=202)
    assert (
        LifecycleMiddleware(lambda current: current).process_response(
            no_version_request, untouched
        )
        is untouched
    )


def test_mutation95_registry_import_time_contracts_are_exercised():
    import importlib
    import importlib.util
    import sys

    registry_module = importlib.import_module("django_api_versioning.registry")
    module_name = "django_api_versioning._mutation_probe_registry"
    spec = importlib.util.spec_from_file_location(module_name, registry_module.__file__)
    assert spec is not None and spec.loader is not None
    probe = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = probe
    try:
        spec.loader.exec_module(probe)
        assert probe.REMOVED_ROUTE is not None
        assert probe.ViewType is not None
        assert probe.UrlRegistry._SOURCE_VERSION_ATTR == (
            "_django_api_versioning_source_version"
        )
        assert probe.UrlRegistry._ROUTE_VERSION_ATTR == (
            "_django_api_versioning_route_version"
        )
        assert probe.UrlRegistry._LOGICAL_ENDPOINT_ATTR == (
            "_django_api_versioning_logical_endpoint"
        )
        assert probe.UrlRegistry._ROUTER_OWNER_ATTR == (
            "_django_api_versioning_router_owner"
        )
        assert probe.UrlRegistry._ROUTER_PREFIX_ATTR == (
            "_django_api_versioning_router_prefix"
        )
        assert probe.UrlRegistry._ROUTER_TRAILING_SLASH_ATTR == (
            "_django_api_versioning_router_trailing_slash"
        )

        operation = probe.ResolvedOperation(
            logical_endpoint="orders",
            route_version=2,
            source_version=1,
            method="GET",
            action="list",
            route_name="order-list",
            namespace="v2",
            route="api/v2/orders/",
            registered_route="api/v2/orders/",
        )
        assert not hasattr(operation, "__dict__")
        with pytest.raises(FrozenInstanceError):
            operation.route = "api/v1/orders/"

        synchronized_methods = (
            "clear",
            "remove",
            "register",
            "register_urlpattern",
            "get_route_version",
            "get_version_matrix",
            "get_logical_version_matrix",
            "get_resolved_route_version_for_match",
            "get_resolved_route_version",
            "resolve_operation",
            "resolve_registered_operation",
            "register_endpoint_lifecycle",
        )
        for method_name in synchronized_methods:
            method = getattr(probe.UrlRegistry, method_name)
            assert method.__name__ == method_name
            assert callable(getattr(method, "__wrapped__", None))
    finally:
        sys.modules.pop(module_name, None)


def test_mutation95_registry_removal_boundaries_are_inclusive_and_source_aware(
    monkeypatch,
):
    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 1)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 3)

    target = UrlRegistry()
    target.register(
        "api/v1/orders/",
        _view,
        source_version=1,
        route_version=1,
        logical_endpoint="orders",
    )
    target.register(
        "api/v2/orders/",
        _view,
        source_version=1,
        route_version=2,
        logical_endpoint="orders",
    )
    target.register(
        "api/v3/orders/",
        _view,
        source_version=2,
        route_version=3,
        logical_endpoint="orders",
    )
    target.register_endpoint_lifecycle(
        "orders", 2, deprecated_at="2027-01-01T00:00:00Z"
    )
    target.register_endpoint_lifecycle(
        "orders", 3, deprecated_at="2028-01-01T00:00:00Z"
    )

    target.remove("orders", 2)

    assert {
        getattr(pattern, target._ROUTE_VERSION_ATTR)
        for pattern in target.urlpatterns
    } == {1}
    assert set(target._removed_patterns) == {("orders", 2), ("orders", 3)}
    assert all(key[1] < 2 for key in target._endpoint_lifecycle)

    newer_source = UrlRegistry()
    newer_source.register(
        "api/v2/orders/",
        _view,
        source_version=3,
        route_version=2,
        logical_endpoint="orders",
    )
    newer_source.register_endpoint_lifecycle(
        "orders", 2, deprecated_at="2029-01-01T00:00:00Z"
    )
    newer_source.remove("orders", 2)
    assert len(newer_source.urlpatterns) == 1
    assert ("orders", 2, None, None, None) in newer_source._endpoint_lifecycle


def test_mutation95_registry_router_removal_is_owner_and_route_identity_scoped():
    target = UrlRegistry()
    owner_with_slash = object()
    owner_without_slash = object()

    with_slash = path("api/v2/orders/", _view, name="orders")
    without_slash = path("api/v2/orders", _view, name="orders")
    for pattern, owner, trailing_slash in (
        (with_slash, owner_with_slash, True),
        (without_slash, owner_without_slash, False),
    ):
        setattr(pattern, target._ROUTER_OWNER_ATTR, owner)
        setattr(pattern, target._ROUTER_PREFIX_ATTR, "orders")
        setattr(pattern, target._ROUTER_TRAILING_SLASH_ATTR, trailing_slash)
        target.register_urlpattern(
            pattern,
            source_version=2,
            route_version=2,
            logical_endpoint="orders",
        )

    target.remove("orders", 2, owner=owner_with_slash)

    assert with_slash not in target.urlpatterns
    assert without_slash in target.urlpatterns
    assert target._router_removal_boundaries == {
        ("orders", "orders", True): {2},
    }


def test_mutation95_registry_resolver_match_uses_exact_trace_and_url_name():
    target = UrlRegistry()
    version_one = path("api/v1/orders/", _view, name="order-list")
    version_two = path("api/v2/orders/", _view, name="order-list")
    version_three = path("api/v2/orders/", _view, name="order-list")
    for pattern, version in (
        (version_one, 1),
        (version_two, 2),
        (version_three, 3),
    ):
        setattr(pattern, target._ROUTE_VERSION_ATTR, version)
    target.urlpatterns[:] = [version_one, version_two, version_three]

    exact = SimpleNamespace(
        route="api/v2/orders/",
        func=_view,
        url_name=None,
        tried=[[version_two]],
    )
    assert target.get_resolved_route_version_for_match(exact) == (True, 2)

    empty_trace = SimpleNamespace(
        route="api/v2/orders/",
        func=_view,
        url_name=None,
        tried=[[]],
    )
    assert target.get_resolved_route_version_for_match(empty_trace) == (False, None)

    ambiguous = SimpleNamespace(
        route="api/v2/orders/",
        func=_view,
        url_name="order-list",
        tried=[[version_two], [version_three]],
    )
    assert target.get_resolved_route_version_for_match(ambiguous) == (True, None)

    wrong_name = SimpleNamespace(
        route="api/v2/orders/",
        func=_view,
        url_name="missing",
        tried=[[version_two]],
    )
    assert target.get_resolved_route_version_for_match(wrong_name) == (False, None)

    longest = UrlRegistry()
    short = path("orders/", _view, name="order-list")
    long = path("api/v2/orders/", _view, name="order-list")
    setattr(short, longest._ROUTE_VERSION_ATTR, 1)
    setattr(long, longest._ROUTE_VERSION_ATTR, 2)
    longest.urlpatterns[:] = [short, long]
    fallback = SimpleNamespace(
        route="nested/api/v2/orders/",
        func=_view,
        url_name=None,
        tried=None,
    )
    assert longest.get_resolved_route_version_for_match(fallback) == (True, 2)
    assert longest._resolved_route_match_length(
        "nested/api/v2/orders/", "api/v2/orders/"
    ) == len("api/v2/orders/")
    assert longest._resolved_route_match_length(
        "prefixapi/v2/orders/", "api/v2/orders/"
    ) == 0


def test_mutation95_registry_operation_resolution_fails_closed_on_bad_identity():
    target = UrlRegistry()

    def callback(request):
        return None

    callback.actions = {"get": "list"}
    pattern = path("api/v2/orders/", callback, name="order-list")
    setattr(pattern, target._LOGICAL_ENDPOINT_ATTR, "orders")
    setattr(pattern, target._ROUTE_VERSION_ATTR, 2)
    setattr(pattern, target._SOURCE_VERSION_ATTR, 1)
    target.urlpatterns.append(pattern)

    match = SimpleNamespace(
        route="api/v2/orders/",
        func=callback,
        url_name=None,
        namespace="v2",
        namespaces=("v2",),
        tried=[[pattern]],
    )
    operation = target.resolve_operation(match, "HEAD")
    assert operation is not None
    assert operation.logical_endpoint == "orders"
    assert operation.route_version == 2
    assert operation.source_version == 1
    assert operation.method == "HEAD"
    assert operation.action == "list"
    assert operation.namespace == "v2"

    assert target.resolve_operation(match, "PATCH") is None
    unmapped = target.resolve_operation(
        match, "PATCH", allow_unmapped_method=True
    )
    assert unmapped is not None and unmapped.action is None

    wrong_namespace = SimpleNamespace(
        route=match.route,
        func=callback,
        url_name=None,
        namespace="v3",
        namespaces=("v3",),
        tried=[[pattern]],
    )
    assert target.resolve_operation(wrong_namespace, "GET") is None

    invalid_endpoint = path("api/v2/orders/", callback, name="order-list")
    setattr(invalid_endpoint, target._LOGICAL_ENDPOINT_ATTR, "")
    setattr(invalid_endpoint, target._ROUTE_VERSION_ATTR, 2)
    invalid_version = path("api/v2/orders/", callback, name="order-list")
    setattr(invalid_version, target._LOGICAL_ENDPOINT_ATTR, "orders")
    setattr(invalid_version, target._ROUTE_VERSION_ATTR, True)

    for invalid_pattern in (invalid_endpoint, invalid_version):
        invalid_registry = UrlRegistry()
        invalid_registry.urlpatterns.append(invalid_pattern)
        invalid_match = SimpleNamespace(
            route="api/v2/orders/",
            func=callback,
            url_name=None,
            namespace="",
            namespaces=(),
            tried=[[invalid_pattern]],
        )
        assert invalid_registry.resolve_operation(invalid_match, "GET") is None

    assert target.resolve_registered_operation("orders", 2, "HEAD").action == "list"
    assert target.resolve_registered_operation("orders", True, "GET") is None
    assert target.resolve_registered_operation("orders", 2, "") is None


def test_mutation95_registry_regex_canonicalization_and_specificity_boundaries():
    target = UrlRegistry()
    assert target._canonical_route_key(r"^api/v2/orders/\.$") == "api/v2/orders/."
    assert target._canonical_route_key(r"^api/v2/orders/\d/$") == r"^api/v2/orders/\d/$"
    assert target._canonical_route_key(r"^api/v2/orders/\\") == r"^api/v2/orders/\\"

    static_path = path("api/v2/orders/search/", _view)
    dynamic_path = path("api/v2/orders/<int:pk>/", _view)
    assert target._route_specificity_key(static_path) < target._route_specificity_key(
        dynamic_path
    )

    static_regex = re_path(r"^api/v2/orders/\.$", _view)
    dynamic_regex = re_path(r"^api/v2/orders/\d/$", _view)
    assert target._route_specificity_key(static_regex) < target._route_specificity_key(
        dynamic_regex
    )


def test_mutation95_router_error_messages_are_exact(monkeypatch):
    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 1)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 2)

    class OrdersViewSet(ViewSet):
        def list(self, request):
            return None

    class InvoicesViewSet(ViewSet):
        def list(self, request):
            return None

    router = VersionedRouter()
    router.register("orders", OrdersViewSet, version=1, basename="order")
    _assert_exact_exception(
        VersioningError,
        "ViewSets registered for prefix 'orders' must use the same basename "
        "across versions; got 'order' and 'orders'. Pass an explicit basename.",
        lambda: router.register("orders", OrdersViewSet, version=2, basename="orders"),
    )

    registry.clear()
    other_router = VersionedRouter()
    other_router.register("orders", OrdersViewSet, version=1, basename="shared")
    _assert_exact_exception(
        VersioningError,
        "Basename 'shared' is already registered for prefix 'orders'; use a "
        "unique basename for prefix 'invoices'.",
        lambda: other_router.register(
            "invoices", InvoicesViewSet, version=1, basename="shared"
        ),
    )

    _assert_exact_exception(
        TypeError,
        "include_root_view must be a bool.",
        lambda: VersionedDefaultRouter(include_root_view=1),
    )
    _assert_exact_exception(
        TypeError,
        "include_format_suffixes must be a bool.",
        lambda: VersionedDefaultRouter(include_format_suffixes=1),
    )
    _assert_exact_exception(
        VersioningError,
        "root_view_name must be a non-empty string.",
        lambda: VersionedDefaultRouter(root_view_name=" "),
    )


def test_mutation95_lifecycle_cache_and_unversioned_metadata_contracts(
    monkeypatch, caplog
):
    from django_api_versioning.lifecycle import _get_lifecycle_state

    with override_settings(API_VERSION_LIFECYCLE={}):
        request = RequestFactory().get("/api/v2/orders/")
        assert _get_lifecycle_state(request) == (2, None, None, None)
        assert request._django_api_version_lifecycle_state == (2, None, None, None)

    calls = []

    def resolve_operation(match, method, *, allow_unmapped_method=False):
        calls.append((method, allow_unmapped_method))
        return None

    monkeypatch.setattr(registry, "resolve_operation", resolve_operation)
    request = SimpleNamespace(resolver_match=object(), method="GET")
    assert _get_endpoint_lifecycle_state(request) is None
    assert request._django_api_endpoint_lifecycle_state is None
    assert not hasattr(request, "_django_api_endpoint_lifecycle_state_405")
    assert _get_endpoint_lifecycle_state(
        request, allow_unmapped_method=True
    ) is None
    assert request._django_api_endpoint_lifecycle_state_405 is None
    assert calls == [("GET", False), ("GET", True)]

    caplog.clear()
    with caplog.at_level("WARNING"):
        assert _parse_lifecycle_date(None, "sunset") is None
    assert [record.getMessage() for record in caplog.records] == [
        "Invalid sunset date None; ignoring."
    ]


def test_mutation95_lifecycle_default_is_false_at_definition_time():
    import importlib
    import importlib.util
    import inspect
    import sys

    lifecycle_module = importlib.import_module("django_api_versioning.lifecycle")
    module_name = "django_api_versioning._mutation_probe_lifecycle"
    spec = importlib.util.spec_from_file_location(module_name, lifecycle_module.__file__)
    assert spec is not None and spec.loader is not None
    probe = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = probe
    try:
        spec.loader.exec_module(probe)
        default = inspect.signature(
            probe._get_endpoint_lifecycle_state
        ).parameters["allow_unmapped_method"].default
        assert default is False
    finally:
        sys.modules.pop(module_name, None)


def test_mutation95_lifecycle_process_response_preserves_retirement_body():
    with override_settings(
        API_VERSION_LIFECYCLE={
            2: {
                "status": "retired",
                "sunset": "2000-01-01T00:00:00Z",
            }
        }
    ):
        request = RequestFactory().get("/api/v2/orders/")
        response = LifecycleMiddleware(
            lambda current: HttpResponse("ok")
        ).process_response(request, HttpResponse("ok"))
    assert response.status_code == 410
    assert response.content == b"API version 2 has been retired as of 2000-01-01T00:00:00Z."


def test_mutation95_decorator_url_prefix_labels_and_router_prefix_boundaries(
    monkeypatch,
):
    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 1)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 2)

    _assert_exact_exception(
        VersioningError,
        "app_name must not contain percent-encoded path separators or "
        "query/fragment delimiters.",
        lambda: _app_name_prefix("billing%2Fadmin"),
    )
    _assert_exact_exception(
        VersioningError,
        "postfix must not contain percent-encoded path separators or "
        "query/fragment delimiters.",
        lambda: endpoint("orders%2Fadmin"),
    )

    class OrdersViewSet(ViewSet):
        def list(self, request):
            return None

    router = VersionedRouter()
    router.register("orders", OrdersViewSet, version=2, basename="order")
    remove_endpoint("orders-archive/", from_version=2)
    router.register("ordersX", OrdersViewSet, version=2, basename="order_x")
    with pytest.raises(VersioningError):
        remove_endpoint("ordersX/", from_version=2)


def test_mutation95_negotiation_query_uniqueness_and_internal_path_rewrite():
    duplicate = RequestFactory().get("/api/orders/?version=2&version=3")
    _assert_exact_exception(
        ValueError,
        "The API version query parameter must appear once.",
        lambda: VersionNegotiationMiddleware._requested_version(
            duplicate, "query"
        ),
    )
    _assert_exact_exception(
        ValueError,
        "Unsupported API versioning scheme: 'bogus'.",
        lambda: VersionNegotiationMiddleware._requested_version(
            RequestFactory().get("/api/orders/"), "bogus"
        ),
    )

    from django_api_versioning.negotiation import _header_version

    _assert_exact_exception(
        _UnsupportedVersion,
        "All requested API versions have q=0.",
        lambda: _header_version(
            RequestFactory().get(
                "/api/orders/",
                HTTP_ACCEPT="application/json; version=2; q=0",
            ),
            "Accept-Version",
        ),
    )

    observed = {}

    def downstream(request):
        observed["path"] = request.path
        observed["path_info"] = request.path_info
        observed["meta_path"] = request.META["PATH_INFO"]
        observed["original_path_info"] = request.original_path_info
        observed["version"] = request.version
        observed["api_version"] = request.api_version
        observed["negotiated"] = request._django_api_version_negotiated
        return HttpResponse("ok")

    middleware = VersionNegotiationMiddleware(downstream)
    with override_settings(
        API_VERSIONING_SCHEME="query",
        API_VERSIONING_QUERY_PARAMETER="version",
        API_UNVERSIONED_BASE_PATH="api/",
        API_BASE_PATH="api/v{version}/",
        API_DEFAULT_VERSION=None,
        API_MIN_VERSION=1,
        API_MAX_VERSION=3,
    ):
        response = middleware(
            RequestFactory().get("/api/orders/?version=2")
        )

    assert response.status_code == 200
    assert observed == {
        "path": "/api/v2/orders/",
        "path_info": "/api/v2/orders/",
        "meta_path": "/api/v2/orders/",
        "original_path_info": "/api/orders/",
        "version": "2",
        "api_version": 2,
        "negotiated": True,
    }
