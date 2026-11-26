"""Regression tests for executable documentation/source consistency gates."""

from pathlib import Path

import pytest

from scripts.verify_docs_contracts import (
    verify_compatibility_article,
    verify_settings_and_endpoint_contract,
)

ROOT = Path(__file__).resolve().parents[1]
TICK = chr(96)
REFERENCE = (ROOT / "docs/reference/index.md").read_text(encoding="utf-8")
SETTINGS = (ROOT / "django_api_versioning/settings.py").read_text(encoding="utf-8")
DECORATORS = (ROOT / "django_api_versioning/decorators.py").read_text(encoding="utf-8")
ARTICLE = (
    ROOT / "docs/articles/024-django-api-versioning-supported-versions.md"
).read_text(encoding="utf-8")
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
TOX = (ROOT / "tox.ini").read_text(encoding="utf-8")


def test_reference_settings_defaults_and_endpoint_signature_match_source():
    verify_settings_and_endpoint_contract(REFERENCE, SETTINGS, DECORATORS)


def test_reference_setting_default_drift_fails():
    old = "| " + TICK + "API_MIN_VERSION" + TICK + " | " + TICK + "1" + TICK + " |"
    new = "| " + TICK + "API_MIN_VERSION" + TICK + " | " + TICK + "9" + TICK + " |"
    stale = REFERENCE.replace(old, new)
    with pytest.raises(ValueError, match="API_MIN_VERSION"):
        verify_settings_and_endpoint_contract(stale, SETTINGS, DECORATORS)


def test_new_endpoint_argument_requires_reference_update():
    changed = DECORATORS.replace(
        "    view_name: str | None = None,\n",
        "    view_name: str | None = None,\n    route_name: str | None = None,\n",
        1,
    )
    with pytest.raises(ValueError, match="route_name"):
        verify_settings_and_endpoint_contract(REFERENCE, SETTINGS, changed)


def test_compatibility_article_matches_classifiers_and_tox_matrix():
    verify_compatibility_article(ARTICLE, PYPROJECT, TOX)


def test_stale_tox_matrix_row_fails():
    stale = ARTICLE.replace(
        "| 6.1 | 3.12, 3.13, 3.14, 3.15 | 4 |",
        "| 6.1 | 3.12, 3.13, 3.14 | 3 |",
    )
    with pytest.raises(ValueError, match="tox.ini"):
        verify_compatibility_article(stale, PYPROJECT, TOX)


def test_stale_classifier_table_fails():
    stale = ARTICLE.replace("| 3.15 | Yes |", "| 3.15 | No |")
    with pytest.raises(ValueError, match="pyproject.toml"):
        verify_compatibility_article(stale, PYPROJECT, TOX)

ARCHITECTURE = (
    ROOT / "docs/design/runtime-architecture.md"
).read_text(encoding="utf-8")
ROOT_README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_runtime_architecture_diagram_covers_the_documented_request_pipeline():
    diagram_start = ARCHITECTURE.index("```mermaid")
    diagram_end = ARCHITECTURE.index("```", diagram_start + len("```mermaid"))
    diagram = ARCHITECTURE[diagram_start:diagram_end]

    assert "flowchart TD" in diagram
    for component in (
        "VersionNegotiationMiddleware",
        "PathNegotiator",
        "HeaderNegotiator",
        "QueryNegotiator",
        "HostnameNegotiator",
        "Django URL resolver",
        "LifecycleMiddleware",
        "VersionedRouterVersioning",
    ):
        assert component in diagram

    assert "runtime-architecture.md" in ROOT_README
    assert "runtime-architecture.md" in REFERENCE
