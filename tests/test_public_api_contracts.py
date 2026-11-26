"""Contracts for the package's supported import surface."""

import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

import django_api_versioning
from django_api_versioning import (
    api_reverse,
    decorators,
    endpoint,
    remove_endpoint,
    reverse,
    set_endpoint_lifecycle,
    ver_range,
)


# This is the single categorized inventory of supported module-level imports.
# Keep root exports governed separately by the package's explicit __all__.
STABLE_IMPORTS = {
    "django_api_versioning.lifecycle": ("LifecycleMiddleware",),
    "django_api_versioning.negotiation": ("VersionNegotiationMiddleware",),
    "django_api_versioning.exceptions": (
        "VersioningError",
        "InvalidVersionError",
        "VersionRangeError",
        "VersionTypeError",
        "AmbiguousVersionError",
        "VersionMatrixError",
        "ContractSnapshotError",
    ),
    "django_api_versioning.testing": (
        "build_version_matrix",
        "assert_version_matrix",
        "assert_schema_snapshot",
    ),
}

OPTIONAL_IMPORTS = {
    "django_api_versioning.routers": (
        "rest_framework",
        ("VersionedRouter", "VersionedDefaultRouter", "VersionedRouterVersioning"),
    ),
    "django_api_versioning.spectacular": (
        "drf_spectacular",
        ("EndpointLifecycleAutoSchema",),
    ),
}

# Importability is not a promise of compatibility. These implementation paths
# are deliberately excluded from the supported import inventory.
INTERNAL_IMPORTS = (
    "django_api_versioning.registry",
    "django_api_versioning.registry.registration",
    "django_api_versioning.registry.resolution",
    "django_api_versioning.registry.removal",
    "django_api_versioning.registry.lifecycle",
    "django_api_versioning.registry.matrix",
    "django_api_versioning.registry.router",
)


def test_package_root_exports_the_complete_stable_public_api():
    expected = [
        "endpoint",
        "remove_endpoint",
        "set_endpoint_lifecycle",
        "ver_range",
        "api_reverse",
    ]

    assert django_api_versioning.__all__ == expected
    assert django_api_versioning.endpoint is decorators.endpoint is endpoint
    assert (
        django_api_versioning.remove_endpoint
        is decorators.remove_endpoint
        is remove_endpoint
    )
    assert (
        django_api_versioning.set_endpoint_lifecycle
        is decorators.set_endpoint_lifecycle
        is set_endpoint_lifecycle
    )
    assert django_api_versioning.ver_range is decorators.ver_range is ver_range
    assert django_api_versioning.api_reverse is reverse.api_reverse is api_reverse


def test_categorized_module_imports_are_available_and_internal_paths_are_excluded():
    for module_path, names in STABLE_IMPORTS.items():
        module = importlib.import_module(module_path)
        for name in names:
            assert getattr(module, name) is not None, f"{module_path}.{name}"

    stable_paths = {
        f"{module_path}.{name}"
        for module_path, names in STABLE_IMPORTS.items()
        for name in names
    }
    assert not any(
        path == internal or path.startswith(f"{internal}.")
        for path in stable_paths
        for internal in INTERNAL_IMPORTS
    )
    assert not set(INTERNAL_IMPORTS).intersection(
        f"django_api_versioning.{name}" for name in django_api_versioning.__all__
    )


def test_optional_import_categories_are_available_when_dependencies_are_installed():
    for module_path, (dependency, names) in OPTIONAL_IMPORTS.items():
        if importlib.util.find_spec(dependency) is None:
            pytest.skip(f"optional dependency {dependency} is not installed")
        module = importlib.import_module(module_path)
        for name in names:
            assert getattr(module, name) is not None, f"{module_path}.{name}"


def test_core_package_import_does_not_load_optional_integrations_in_a_clean_interpreter():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "tests.settings"
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(root), env.get("PYTHONPATH", "")))
    )
    code = """
import sys

class RejectOptionalIntegrations:
    def find_spec(self, fullname, path=None, target=None):
        if (
            fullname == "rest_framework"
            or fullname.startswith("rest_framework.")
            or fullname == "drf_spectacular"
            or fullname.startswith("drf_spectacular.")
        ):
            raise RuntimeError("Core package import attempted to load an optional integration")

sys.meta_path.insert(0, RejectOptionalIntegrations())
import django_api_versioning
import django_api_versioning.urls
from django_api_versioning.registry import registry

assert django_api_versioning.__all__ == [
    "endpoint",
    "remove_endpoint",
    "set_endpoint_lifecycle",
    "ver_range",
    "api_reverse",
]
assert registry is not None
assert "django_api_versioning.routers" not in sys.modules
assert "django_api_versioning.spectacular" not in sys.modules
assert "rest_framework" not in sys.modules
assert "drf_spectacular" not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("blocked_package", "integration_module", "message"),
    [
        (
            "rest_framework",
            "django_api_versioning.routers",
            "VersionedRouter requires Django REST Framework",
        ),
        (
            "drf_spectacular",
            "django_api_versioning.spectacular",
            "EndpointLifecycleAutoSchema requires drf-spectacular",
        ),
    ],
)
def test_optional_imports_fail_with_actionable_errors_when_dependency_is_absent(
    blocked_package, integration_module, message
):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(root), env.get("PYTHONPATH", "")))
    )
    code = """
import importlib
import sys

blocked = sys.argv[1]
class RejectOptionalDependency:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == blocked or fullname.startswith(blocked + "."):
            raise ModuleNotFoundError("blocked optional dependency: " + blocked)

sys.meta_path.insert(0, RejectOptionalDependency())
try:
    importlib.import_module(sys.argv[2])
except ImportError as exc:
    assert sys.argv[3] in str(exc), str(exc)
else:
    raise AssertionError("optional integration unexpectedly imported")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            blocked_package,
            integration_module,
            message,
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
