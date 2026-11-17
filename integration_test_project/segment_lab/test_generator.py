from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from segment_lab.generate_routes import (
    PACKAGE_DIR,
    SCENARIOS,
    _preserve_generated_at,
    build,
    provenance,
    source_refs,
)
from segment_lab.probe import callback_info

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_provenance_is_from_the_current_repository_checkout() -> None:
    result = provenance()
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    commit = os.environ.get("SOURCE_COMMIT")
    if not commit:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    assert result["version"] == project["project"]["version"]
    assert result["commit"] == commit
    assert result["source_mode"] == "repository-checkout"
    assert result["install_method"] == "repository-checkout"
    assert result["files"]

    for item in result["files"] + result["evidence_files"]:
        path = REPO_ROOT / item["file"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]

    evidence_paths = {item["file"] for item in result["evidence_files"]}
    assert "pyproject.toml" in evidence_paths
    assert "integration_test_project/segment_lab/generate_routes.py" in evidence_paths
    assert "integration_test_project/segment_lab/scenario_catalog.py" in evidence_paths
    assert "integration_test_project/api/views.py" in evidence_paths
    assert "integration_test_project/project/urls.py" in evidence_paths
    assert "tests/test_reverse.py" in evidence_paths
    assert "pytest.ini" in evidence_paths
    assert "requirements-ci.txt" in evidence_paths
    assert "requirements.txt" in evidence_paths
    assert "scripts/verify_distribution_contents.py" in evidence_paths
    assert "scripts/smoke_installed_wheel.py" in evidence_paths


def test_all_scenario_view_modules_resolve() -> None:
    assert len(SCENARIOS) == 20
    for name, spec in SCENARIOS.items():
        module = spec["views"]
        if module is not None:
            assert importlib.util.find_spec(module) is not None, name


def test_source_references_resolve_against_current_package() -> None:
    refs = source_refs(PACKAGE_DIR)
    assert "endpoint" in refs["symbols"]
    assert "UrlRegistry.register" in refs["symbols"]
    assert "LifecycleMiddleware.__call__" in refs["symbols"]
    assert "_parse_sunset" in refs["symbols"]
    assert refs["lines"]["sunset_410"]["code"] == (
        "if sunset_date and _is_past(sunset_date):"
    )
    assert refs["lines"]["gap_warning"]["code"] == (
        'self.style.WARNING(f"  [{endpoint}] v{v} is not defined.")'
    )
    assert refs["lines"]["callback_name"]["code"] == (
        "callback_name = self._get_callback_name(versions[version])"
    )

    for ref in refs["lines"].values():
        source_file = REPO_ROOT / ref["file"]
        line = source_file.read_text().splitlines()[ref["line"] - 1]
        assert line.strip() == ref["code"]


def test_full_evidence_build_records_current_package_behaviour() -> None:
    data, main_stdout = build()
    scenarios = data["scenarios"]

    assert data["schema_version"] == 1
    assert (
        data["source"]["version"]
        == tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"][
            "version"
        ]
    )
    assert len(scenarios) == len(SCENARIOS) == 20
    assert main_stdout.strip()

    main_requests = {item["path"]: item for item in scenarios["main"]["requests"]}
    assert scenarios["main"]["urlconf_import"]["ok"] is True
    assert main_requests["/api/v1/users/"]["status"] == 200
    assert main_requests["/api/v2/users/"]["status"] == 200
    assert main_requests["/api/v3/users/"]["status"] == 200
    assert main_requests["/api/v4/users/"]["status"] == 404

    existing = scenarios["existing_integration_project"]
    existing_requests = {item["path"]: item for item in existing["requests"]}
    assert existing["urlconf_import"]["ok"] is True
    assert existing_requests["/api/v4/users/"]["status"] == 200
    assert existing_requests["/api/v5/users/"]["status"] == 404
    assert existing_requests["/api/v2/blogposts/"]["status"] == 200

    drf_default = scenarios["drf_default"]
    invoice = next(
        item for item in drf_default["requests"] if item["path"] == "/api/v2/invoices/"
    )
    assert invoice["status"] == 200
    assert invoice["body"]["request.version"] is None

    router = scenarios["drf_router"]
    router_users = next(
        item for item in router["requests"] if item["path"] == "/api/v2/users/"
    )
    assert router_users["status"] == 200
    assert router_users["body"]["handler"] == "UserViewSet.list"

    assert scenarios["drf_viewset_class"]["urlconf_import"]["ok"] is False
    assert scenarios["order_reversed"]["matrix_equal_to"]["equal"] is True

    quick_start = scenarios["website_quick_start"]
    quick_start_requests = {item["path"]: item for item in quick_start["requests"]}
    assert quick_start_requests["/api/v1/invoices/42/"]["status"] == 404
    for version in (2, 3):
        response = quick_start_requests[f"/api/v{version}/invoices/42/"]
        assert response["status"] == 200
        assert response["body"] == {"id": 42, "status": "paid"}

    assert main_stdout.strip().startswith("users/:")
    assert (
        scenarios["website_check_versions"]["check_versions"][0]["stdout"]
        == main_stdout
    )


def test_generated_at_is_preserved_when_evidence_content_is_unchanged() -> None:
    existing = {
        "generated_at": "2026-11-14T10:00:00+00:00",
        "source": {"commit": "a" * 40},
        "scenarios": {"main": {"request_count": 3}},
    }
    regenerated = {
        "generated_at": "2026-11-14T10:05:00+00:00",
        "source": {"commit": "a" * 40},
        "scenarios": {"main": {"request_count": 3}},
    }

    result = _preserve_generated_at(regenerated, existing)

    assert result["generated_at"] == existing["generated_at"]
    assert result["source"] == regenerated["source"]
    assert result["scenarios"] == regenerated["scenarios"]


def test_generated_at_changes_when_evidence_content_changes() -> None:
    existing = {
        "generated_at": "2026-11-14T10:00:00+00:00",
        "source": {"commit": "a" * 40},
    }
    regenerated = {
        "generated_at": "2026-11-14T10:05:00+00:00",
        "source": {"commit": "b" * 40},
    }

    result = _preserve_generated_at(regenerated, existing)

    assert result is regenerated
    assert result["generated_at"] == regenerated["generated_at"]


def test_callback_info_uses_stable_names_for_callable_instances() -> None:
    class CallableView:
        def __call__(self, request):
            return None

    result = callback_info(CallableView())

    assert result == {
        "callback": "CallableView",
        "view_class": None,
        "actions": None,
    }
