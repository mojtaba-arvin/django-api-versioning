"""Contracts for the shared registry registration component."""

import importlib

import pytest
from django.urls import path

from django_api_versioning.registry import UrlRegistry, registry


@pytest.mark.parametrize("use_urlpattern", [False, True])
def test_registration_entrypoints_share_source_version_precedence(use_urlpattern):
    """Both public entrypoints apply the same lower/equal source-version rules."""
    target = UrlRegistry()

    def original(request):
        return None

    def lower(request):
        return None

    def equal(request):
        return None

    def register(callback, source_version):
        if use_urlpattern:
            target.register_urlpattern(
                path("api/v2/shared-registration/", callback, name="shared"),
                source_version=source_version,
                route_version=2,
                logical_endpoint="shared-registration",
            )
        else:
            target.register(
                "api/v2/shared-registration/",
                callback,
                source_version=source_version,
                route_version=2,
                logical_endpoint="shared-registration",
            )

    register(original, 2)
    first_snapshot = target.current_snapshot
    assert target.urlpatterns[0].callback is original
    assert first_snapshot.generation == 1

    register(lower, 1)
    assert target.urlpatterns[0].callback is original
    assert target.current_snapshot is first_snapshot

    # Equal source versions preserve the established last-registration-wins rule.
    register(equal, 2)
    assert target.urlpatterns[0].callback is equal
    assert target.current_snapshot.generation == first_snapshot.generation + 1


def test_registry_import_path_remains_the_single_compatibility_facade():
    """The package import path keeps the original facade and singleton identity."""
    module = importlib.import_module("django_api_versioning.registry")

    assert module.UrlRegistry is UrlRegistry
    assert module.registry is registry
    assert module.__file__ is not None
    assert module.__file__.endswith("registry/__init__.py")
