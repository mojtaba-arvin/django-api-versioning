"""Unit tests for Segment Lab evidence-generation helpers."""

import ast
import sys
from pathlib import Path

INTEGRATION_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(INTEGRATION_ROOT))

from segment_lab.generate_routes import _setting_references  # noqa: E402


def test_setting_references_excludes_docstrings_and_string_literals():
    tree = ast.parse(
        '"""API_VERSIONING_CHANNELS and API_EFFECTIVE_VERSION_RESOLVER."""\n'
        'message = "API_VERSIONING_CHANNELS"\n'
        "API_VERSIONING_CHANNELS = []\n"
        "def inspect_settings(settings):\n"
        "    return settings.API_VERSIONING_CHANNELS, API_EFFECTIVE_VERSION_RESOLVER\n"
    )

    assert set(_setting_references(tree)) == {
        ("API_VERSIONING_CHANNELS", 5),
        ("API_EFFECTIVE_VERSION_RESOLVER", 5),
    }


def test_setting_references_only_reports_read_accesses():
    tree = ast.parse(
        "API_VERSIONING_CHANNELS = []\n"
        "API_EFFECTIVE_VERSION_RESOLVER = None\n"
        "def configure():\n"
        "    API_VERSIONING_CHANNELS = []\n"
        "    return API_EFFECTIVE_VERSION_RESOLVER\n"
    )

    assert list(_setting_references(tree)) == [
        ("API_EFFECTIVE_VERSION_RESOLVER", 5)
    ]
