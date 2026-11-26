"""Contracts for the package's supported top-level import surface."""

import os
import subprocess
import sys
from pathlib import Path

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


def test_core_package_import_does_not_load_optional_drf_in_a_clean_interpreter():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "tests.settings"
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(root), env.get("PYTHONPATH", "")))
    )
    code = """
import sys

class RejectDRF:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "rest_framework" or fullname.startswith("rest_framework."):
            raise RuntimeError("Core package import attempted to load optional DRF")

sys.meta_path.insert(0, RejectDRF())
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
assert "rest_framework" not in sys.modules
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
