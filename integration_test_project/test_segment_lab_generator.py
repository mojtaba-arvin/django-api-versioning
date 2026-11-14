"""Unit tests for Segment Lab evidence-generation helpers."""

import ast
import sys

import pytest
from pathlib import Path

INTEGRATION_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(INTEGRATION_ROOT))

from segment_lab.generate_routes import (  # noqa: E402
    _setting_references,
    _unique_line_reference,
)


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



def test_unique_line_reference_returns_the_only_matching_line():
    assert _unique_line_reference(
        ["first", "    return view", "last"],
        "decorators.py",
        "    return view",
    ) == {"line": 2, "code": "return view"}


@pytest.mark.parametrize(
    ("lines", "expected_error"),
    [
        (["return view", "    return view"], "ambiguous"),
        (["first", "last"], "not found"),
    ],
)
def test_unique_line_reference_rejects_ambiguous_or_missing_anchors(
    lines, expected_error
):
    with pytest.raises(SystemExit, match=expected_error):
        _unique_line_reference(lines, "decorators.py", "return view")
