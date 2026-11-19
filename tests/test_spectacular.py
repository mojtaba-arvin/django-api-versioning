"""Focused coverage for the optional drf-spectacular adapter."""

from datetime import datetime, timezone
from pathlib import Path
from subprocess import run
from sys import executable
from types import SimpleNamespace

import pytest
from rest_framework.versioning import URLPathVersioning

from django_api_versioning.lifecycle_metadata import EndpointLifecycle
from django_api_versioning.registry import registry
from django_api_versioning.spectacular import EndpointLifecycleAutoSchema

AutoSchema = pytest.importorskip("drf_spectacular.openapi").AutoSchema


def _schema(monkeypatch, view, operation=None):
    result = {"responses": {}} if operation is None else operation
    monkeypatch.setattr(AutoSchema, "get_operation", lambda self, *args: result)
    schema = EndpointLifecycleAutoSchema()
    schema.view = view
    return schema.get_operation("/orders/", "orders/", "", "GET", None)


def test_none_operation_is_returned_without_resolving_identity(monkeypatch):
    monkeypatch.setattr(AutoSchema, "get_operation", lambda self, *args: None)
    monkeypatch.setattr(
        registry,
        "resolve_operation",
        lambda *args: pytest.fail("must not resolve an empty schema operation"),
    )

    schema = EndpointLifecycleAutoSchema()
    schema.view = SimpleNamespace(request=SimpleNamespace(resolver_match=object()))

    assert schema.get_operation("/orders/", "orders/", "", "GET", None) is None


def test_resolver_match_marks_only_deprecated_registered_operation(monkeypatch):
    resolver_match = object()
    operation = SimpleNamespace(logical_endpoint="orders", route_version=2)
    lifecycle = EndpointLifecycle(
        deprecated_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        sunset=None,
    )
    monkeypatch.setattr(
        registry, "resolve_operation", lambda match, method: operation
    )
    monkeypatch.setattr(
        registry, "get_endpoint_lifecycle", lambda resolved: lifecycle
    )

    result = _schema(
        monkeypatch,
        SimpleNamespace(request=SimpleNamespace(resolver_match=resolver_match)),
    )

    assert result["deprecated"] is True


def test_resolver_match_without_lifecycle_preserves_explicit_schema_flag(monkeypatch):
    operation = SimpleNamespace()
    monkeypatch.setattr(registry, "resolve_operation", lambda *args: operation)
    monkeypatch.setattr(registry, "get_endpoint_lifecycle", lambda resolved: None)
    result = _schema(
        monkeypatch,
        SimpleNamespace(request=SimpleNamespace(resolver_match=object())),
        {"deprecated": True, "responses": {}},
    )

    assert result["deprecated"] is True


@pytest.mark.parametrize("version", [True, "v2", None, 2.0])
def test_url_path_versioning_rejects_non_decimal_or_non_integer_version(
    monkeypatch, version
):
    monkeypatch.setattr(
        registry,
        "resolve_registered_operation",
        lambda *args: pytest.fail("invalid schema version must not be resolved"),
    )
    view = SimpleNamespace(
        request=SimpleNamespace(resolver_match=None),
        versioning_class=URLPathVersioning,
        kwargs={"version": version},
    )

    assert _schema(monkeypatch, view) == {"responses": {}}


def test_url_path_versioning_resolves_decimal_string_version(monkeypatch):
    resolved = SimpleNamespace()
    calls = []
    monkeypatch.setattr(
        registry,
        "resolve_registered_operation",
        lambda logical, version, method: (
            calls.append((logical, version, method)) or resolved
        ),
    )
    monkeypatch.setattr(
        registry, "get_endpoint_lifecycle", lambda operation: None
    )
    view = SimpleNamespace(
        request=SimpleNamespace(resolver_match=None),
        versioning_class=URLPathVersioning,
        kwargs={"version": "02"},
    )
    setattr(view, registry._LOGICAL_ENDPOINT_ATTR, "orders")

    result = _schema(monkeypatch, view)

    assert calls == [("orders", 2, "GET")]
    assert result == {"responses": {}}


def test_non_url_path_versioning_without_resolver_match_is_left_unchanged(
    monkeypatch,
):
    monkeypatch.setattr(
        registry,
        "resolve_registered_operation",
        lambda *args: pytest.fail("unsupported versioning class must not resolve"),
    )
    view = SimpleNamespace(
        request=SimpleNamespace(resolver_match=None),
        versioning_class=object,
        kwargs={"version": 2},
    )

    assert _schema(monkeypatch, view) == {"responses": {}}


def test_missing_logical_identity_is_passed_to_registry_as_none(monkeypatch):
    calls = []
    monkeypatch.setattr(
        registry,
        "resolve_registered_operation",
        lambda logical, version, method: (
            calls.append((logical, version, method)) or None
        ),
    )
    view = SimpleNamespace(
        request=SimpleNamespace(resolver_match=None),
        versioning_class=URLPathVersioning,
        kwargs={"version": 2},
    )

    assert _schema(monkeypatch, view) == {"responses": {}}
    assert calls == [(None, 2, "GET")]


def test_optional_dependency_error_is_actionable_in_isolated_interpreter():
    source_root = Path(__file__).resolve().parents[1]
    script = """
import importlib.abc
import sys

class BlockSpectacular(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "drf_spectacular" or fullname.startswith("drf_spectacular."):
            raise ModuleNotFoundError("blocked optional dependency")
        return None

sys.meta_path.insert(0, BlockSpectacular())
try:
    import django_api_versioning.spectacular
except ImportError as exc:
    assert "requires drf-spectacular" in str(exc)
    assert "Install the optional schema tooling" in str(exc)
else:
    raise AssertionError("optional adapter import unexpectedly succeeded")
"""
    run([executable, "-c", script], cwd=source_root, check=True)
