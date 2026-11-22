"""Focused regression contracts for registry removal boundaries and types."""

import pytest

from django_api_versioning.exceptions import VersionTypeError
from django_api_versioning.registry import UrlRegistry


@pytest.fixture
def isolated_registry():
    return UrlRegistry()


def test_remove_accepts_a_valid_integer_version(isolated_registry):
    isolated_registry.remove("orders", 2)

    assert isolated_registry._removal_boundaries == {"orders": {2}}


def test_remove_rejects_boolean_versions_even_though_bool_is_an_int_subclass(
    isolated_registry,
):
    with pytest.raises(VersionTypeError, match="Removal version must be an integer"):
        isolated_registry.remove("orders", True)

    assert isolated_registry._removal_boundaries == {}


def test_remove_accepts_the_configured_maximum_version(isolated_registry, monkeypatch):
    from django_api_versioning.settings import api_settings

    monkeypatch.setattr(api_settings, "API_MIN_VERSION", 1)
    monkeypatch.setattr(api_settings, "API_MAX_VERSION", 5)

    isolated_registry.remove("orders", 5)

    assert isolated_registry._removal_boundaries == {"orders": {5}}


def test_removal_boundary_returns_none_without_a_concrete_route_version(
    isolated_registry,
):
    isolated_registry.remove("orders", 2)

    assert isolated_registry._removal_boundary("orders", None) is None


def test_unowned_removal_boundary_uses_the_unowned_boundary_collection(
    isolated_registry,
):
    isolated_registry.remove("orders", 2)

    assert isolated_registry._removal_boundary("orders", 3, owner=None) == 2
