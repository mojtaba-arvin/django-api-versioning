""""Mutation-driven behavioral contracts for decorator registration APIs.

These tests assert observable callable metadata, public validation messages, and
router/decorator ownership isolation. They intentionally exercise behaviors that
were surviving the full-suite mutation baseline.
"""

import pytest
from rest_framework import viewsets
from rest_framework.response import Response

from django_api_versioning.decorators import (
    _register_endpoint_view,
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
from django_api_versioning.routers import VersionedRouter
from django_api_versioning.settings import api_settings


def test_registry_transaction_wrappers_preserve_callable_metadata():
    """The transaction decorator must preserve introspection metadata."""
    expected = (
        (_register_endpoint_view, "_register_endpoint_view"),
        (set_endpoint_lifecycle, "set_endpoint_lifecycle"),
        (remove_endpoint, "remove_endpoint"),
    )

    for wrapped, name in expected:
        assert wrapped.__name__ == name
        assert wrapped.__wrapped__.__name__ == name
        assert wrapped.__doc__


def test_ver_range_reports_exact_maximum_version_error(monkeypatch):
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)

    with pytest.raises(InvalidVersionError) as exc_info:
        ver_range(1, 6)

    assert str(exc_info.value) == ("Version 6 is above the maximum allowed version 5.")


def test_endpoint_rejects_duplicate_versions_with_exact_error():
    def view(request):
        return None

    with pytest.raises(VersionRangeError) as exc_info:
        endpoint("duplicate-versions", versions=[1, 1])(view)

    assert str(exc_info.value) == "'versions' must not contain duplicates."


def test_endpoint_rejects_mutually_exclusive_version_arguments_exactly():
    with pytest.raises(VersionRangeError) as exc_info:
        endpoint("exclusive", version=1, versions=[1])

    assert str(exc_info.value) == "Use either 'version' or 'versions', not both."


def test_endpoint_rejects_non_list_versions_with_exact_error():
    with pytest.raises(VersionTypeError) as exc_info:
        endpoint("versions-type", versions=(1, 2))

    assert str(exc_info.value) == "'versions' must be a list of integers."


@pytest.mark.parametrize(
    ("methods", "message"),
    [
        ([], "methods must be a non-empty list of HTTP methods."),
        ([1], "methods must contain non-empty HTTP method strings."),
        (["get", "GET"], "methods must not contain duplicates."),
    ],
)
def test_set_endpoint_lifecycle_reports_exact_method_validation_error(methods, message):
    with pytest.raises(VersioningError) as exc_info:
        set_endpoint_lifecycle("method-contract", version=1, methods=methods)

    assert str(exc_info.value) == message


@pytest.mark.parametrize(
    ("version", "exception", "message"),
    [
        (True, VersionTypeError, "Version must be an integer."),
        (-1, VersionRangeError, "Version must be a non-negative API version."),
        (
            6,
            InvalidVersionError,
            "Version 6 is above the maximum allowed version 5.",
        ),
    ],
)
def test_endpoint_version_validation_reports_exact_error(
    monkeypatch, version, exception, message
):
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)

    def view(request):
        return None

    with pytest.raises(exception) as exc_info:
        endpoint("version-contract", version=version)(view)

    assert str(exc_info.value) == message


@pytest.mark.parametrize(
    ("postfix", "exception", "message"),
    [
        (None, TypeError, "postfix must be a string."),
        (
            "/absolute",
            VersioningError,
            "postfix must be relative and must not start with '/'.",
        ),
    ],
)
def test_remove_endpoint_reports_exact_postfix_validation_error(
    postfix, exception, message
):
    with pytest.raises(exception) as exc_info:
        remove_endpoint(postfix, from_version=1)

    assert str(exc_info.value) == message


def _router_with_removed_route():
    class OrdersViewSet(viewsets.ViewSet):
        def list(self, request):
            return Response([])

    router = VersionedRouter()
    router.register(
        "router-owned-tombstone",
        OrdersViewSet,
        version=1,
        basename="router-owned-tombstone",
    )
    router.remove(
        "router-owned-tombstone",
        "router-owned-tombstone-list",
        from_version=1,
    )
    return router


def test_decorator_removal_does_not_treat_foreign_router_tombstone_as_ownership():
    """An unrelated router tombstone must not block decorator endpoint removal."""
    _router_with_removed_route()

    # The foreign router-owned tombstone is present, but its logical endpoint
    # does not match this decorator removal request.
    remove_endpoint("unrelated-decorator-endpoint", from_version=1)


def test_decorator_removal_detects_router_tombstone_with_trailing_slash():
    """Ownership matching normalizes the caller's trailing slash."""
    _router_with_removed_route()

    with pytest.raises(VersioningError) as exc_info:
        remove_endpoint("router-owned-tombstone/", from_version=1)

    assert "owned by a VersionedRouter" in str(exc_info.value)


def test_decorator_removal_reports_exact_router_ownership_error():
    _router_with_removed_route()

    with pytest.raises(VersioningError) as exc_info:
        remove_endpoint("router-owned-tombstone", from_version=1)

    assert str(exc_info.value) == (
        "Endpoint 'router-owned-tombstone' is owned by a VersionedRouter; "
        "use router.remove() instead."
    )
