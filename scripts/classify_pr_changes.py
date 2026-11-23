#!/usr/bin/env python3
"""Classify changed repository paths for the always-running pull-request gate."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

PYTHON_PATHS = (
    "django_api_versioning/",
    "tests/",
    "integration_test_project/",
    "examples/openapi_contract/",
    "examples/consumer_migration/",
)
WEBSITE_PATHS = ("website/", "docs/articles/", "docs/reference/")
WEBSITE_EXAMPLE_PATHS = {
    "pyproject.toml",
    "pytest.ini",
    "requirements-ci.txt",
    "requirements.txt",
    "scripts/verify_distribution_contents.py",
    "scripts/smoke_installed_wheel.py",
    "integration_test_project/segment_lab/generate_routes.py",
    "integration_test_project/segment_lab/scenario_catalog.py",
}
AGENT_PATHS = (
    ".agents/",
    ".claude/",
    ".github/",
    "website/.agents/",
    "website/.claude/",
)
PYTHON_DEPENDENCIES = {
    "pyproject.toml",
    "uv.lock",
    "tox.ini",
    "requirements.txt",
    "requirements-ci.txt",
    "requirements-dev.txt",
    "requirements-build.txt",
}
COMPATIBILITY_PATHS = {
    "tox.ini",
    ".github/workflows/compatibility.yml",
    ".github/workflows/publish.yml",
    ".github/workflows/agent-tooling.yml",
    "scripts/check_tox_workflow_matrix.py",
    "scripts/classify_pr_changes.py",
    "scripts/test_classify_pr_changes.py",
    "scripts/quality_fingerprint.py",
    "scripts/test_quality_fingerprint.py",
    "scripts/release_bootstrap.sh",
    "Makefile",
}
OPENAPI_PATHS = (
    "django_api_versioning/",
    "tests/",
    "integration_test_project/",
    "examples/openapi_contract/",
    "examples/consumer_migration/",
)
OPENAPI_EXPLICIT_PATHS = {
    "docs/design/versioned-openapi-contract.md",
    ".github/workflows/openapi-contract.yml",
    "pyproject.toml",
    "uv.lock",
    "requirements-ci.txt",
    "requirements.txt",
    "scripts/check_coverage_thresholds.py",
    "scripts/quality_fingerprint.py",
    ".github/workflows/publish.yml",
}


def is_version_only_metadata_change(
    base_pyproject: str,
    head_pyproject: str,
    base_lock: str,
    head_lock: str,
) -> bool:
    """Compare parsed project and lock data, allowing only package version changes."""
    try:
        old_project = tomllib.loads(base_pyproject)
        new_project = tomllib.loads(head_pyproject)
        package_name = new_project["project"]["name"]
        old_version = old_project["project"]["version"]
        new_version = new_project["project"]["version"]
        if old_version == new_version:
            return False
        old_project["project"]["version"] = "<PACKAGE_VERSION>"
        new_project["project"]["version"] = "<PACKAGE_VERSION>"
        if old_project != new_project:
            return False

        old_lock = tomllib.loads(base_lock)
        new_lock = tomllib.loads(head_lock)
        for lock, expected_version in (
            (old_lock, old_version),
            (new_lock, new_version),
        ):
            lock.pop("content-hash", None)
            matches = [
                item
                for item in lock.get("package", [])
                if item.get("name") == package_name
            ]
            if len(matches) != 1 or matches[0].get("version") != expected_version:
                return False
            matches[0]["version"] = "<PACKAGE_VERSION>"
        return old_lock == new_lock
    except (KeyError, TypeError, ValueError, tomllib.TOMLDecodeError):
        return False


def detect_release_metadata_only(base_ref: str, paths: list[str]) -> bool:
    """Detect a package-version-only edit using parsed TOML, not path names alone."""
    normalized = [path.strip().removeprefix("./") for path in paths if path.strip()]
    if "pyproject.toml" not in normalized or "uv.lock" not in normalized:
        return False
    quality_paths = (
        "django_api_versioning/",
        "tests/",
        "integration_test_project/",
        "examples/",
        "requirements",
        "tox.ini",
        "pytest.ini",
        "setup.cfg",
        "mutmut_config.py",
        ".github/workflows/",
        ".github/actions/",
    )
    if any(
        path.startswith(quality_paths)
        or path in {
            "scripts/check_coverage_thresholds.py",
            "scripts/check_tox_workflow_matrix.py",
            "scripts/check_reproducible_build.py",
        }
        for path in normalized
    ):
        return False

    def git_content(path: str) -> str | None:
        result = subprocess.run(
            ["git", "show", f"{base_ref}:{path}"],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.stdout if result.returncode == 0 else None

    base_pyproject = git_content("pyproject.toml")
    base_lock = git_content("uv.lock")
    if base_pyproject is None or base_lock is None:
        return False
    head_pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    head_lock = Path("uv.lock").read_text(encoding="utf-8")
    return is_version_only_metadata_change(
        base_pyproject, head_pyproject, base_lock, head_lock
    )


def classify_paths(
    paths: list[str], *, release_metadata_only: bool = False
) -> dict[str, bool]:
    """Return the workflows required for repository-relative changed paths."""
    normalized = [path.strip().removeprefix("./") for path in paths if path.strip()]

    is_python = not release_metadata_only and any(
        path.startswith(PYTHON_PATHS)
        or path
        in {
            "pytest.ini",
            ".github/workflows/tests.yml",
            ".github/workflows/adversarial-testing.yml",
            ".github/actions/mutation-shard/action.yml",
            ".github/workflows/mutation-shard.yml",
            ".github/workflows/pull-request-gate.yml",
            ".github/workflows/compatibility.yml",
            ".github/workflows/openapi-contract.yml",
            ".github/workflows/package-artifacts.yml",
            ".github/workflows/publish.yml",
            ".github/workflows/agent-tooling.yml",
            "scripts/verify_distribution_contents.py",
            "scripts/smoke_installed_wheel.py",
            "scripts/check_coverage_thresholds.py",
            "scripts/check_reproducible_build.py",
            "scripts/classify_pr_changes.py",
            "scripts/test_classify_pr_changes.py",
            "scripts/quality_fingerprint.py",
            "scripts/test_quality_fingerprint.py",
            "scripts/verify_release_evidence.py",
            "scripts/export_mutation_report.py",
            "scripts/fuzz_negotiation.py",
        }
        or path.startswith("fuzz_corpus/negotiation/")
        or path in PYTHON_DEPENDENCIES
        or (path.startswith("requirements") and path.endswith(".txt"))
        for path in normalized
    )
    has_runtime_changes = any(path.startswith(PYTHON_PATHS) for path in normalized)
    compatibility_full = (
        not release_metadata_only
        and not has_runtime_changes
        and any(
            path in PYTHON_DEPENDENCIES
            or path in COMPATIBILITY_PATHS
            or (path.startswith("scripts/") and path.endswith(".py"))
            or (path.startswith("requirements") and path.endswith(".txt"))
            for path in normalized
        )
    )
    is_compatibility = compatibility_full or is_python or any(
        path in COMPATIBILITY_PATHS for path in normalized
    )
    is_package = any(
        path.startswith(("django_api_versioning/", "tests/", "LICENSE"))
        or path
        in {
            "pyproject.toml",
            "MANIFEST.in",
            "README.md",
            "CHANGELOG.md",
            "requirements.txt",
            "requirements-dev.txt",
            "requirements-build.txt",
            "pytest.ini",
            ".github/workflows/package-artifacts.yml",
            "scripts/verify_distribution_contents.py",
            "scripts/smoke_installed_wheel.py",
            "scripts/check_reproducible_build.py",
        }
        for path in normalized
    )
    # Website examples are verified against the package checkout. A package,
    # test, or evidence-harness change must therefore run the website gate too.
    is_website = any(
        path.startswith(WEBSITE_PATHS)
        or (
            not release_metadata_only
            and (
                path.startswith(PYTHON_PATHS)
                or path in WEBSITE_EXAMPLE_PATHS
                or (path.startswith("requirements") and path.endswith(".txt"))
                or path in {
                    ".github/workflows/website-data-preflight.yml",
                    "scripts/verify_website_examples.py",
                }
            )
        )
        for path in normalized
    )
    is_agent = any(
        path
        in {
            "AGENTS.md",
            "website/AGENTS.md",
            "CLAUDE.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "scripts/agent.py",
            "scripts/verify_repository_policy.py",
            "scripts/classify_pr_changes.py",
            "scripts/quality_fingerprint.py",
            "scripts/test_quality_fingerprint.py",
            "scripts/configure_github_repository.sh",
            "scripts/maintain.sh",
            "scripts/release_bootstrap.sh",
            "Makefile",
            "scripts/release_tags.py",
            "scripts/test_release_tags.py",
            "docs/agent-engineering.md",
            "requirements-dev.txt",
            "scripts/test_classify_pr_changes.py",
        }
        or path.startswith(AGENT_PATHS)
        or path.startswith(".github/")
        or path.startswith("scripts/agent_tests/")
        for path in normalized
    )
    needs_dependency_review = not release_metadata_only and any(
        path in PYTHON_DEPENDENCIES
        or path in {"website/package.json", "website/pnpm-lock.yaml"}
        or path.startswith("requirements")
        or path.endswith("/requirements.txt")
        for path in normalized
    )
    is_openapi = not release_metadata_only and any(
        path.startswith(OPENAPI_PATHS) or path in OPENAPI_EXPLICIT_PATHS
        for path in normalized
    )

    return {
        "python": is_python,
        "deep": is_python,
        "metadata": any(
            path in {"pyproject.toml", "uv.lock"} for path in normalized
        ),
        "compatibility": is_compatibility,
        "compatibility_full": compatibility_full,
        "package": is_package,
        "website": is_website,
        "agent": is_agent,
        "dependency": needs_dependency_review,
        "openapi": is_openapi,
    }


def main() -> int:
    if len(sys.argv) not in {3, 4}:
        print(
            "Usage: classify_pr_changes.py <changed-files.txt> <github-output> [base-ref]",
            file=sys.stderr,
        )
        return 2

    changed_files = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    metadata_only = (
        len(sys.argv) == 4
        and detect_release_metadata_only(sys.argv[3], changed_files)
    )
    outputs = classify_paths(changed_files, release_metadata_only=metadata_only)
    with Path(sys.argv[2]).open("a", encoding="utf-8") as output_file:
        for name, enabled in outputs.items():
            output_file.write(f"{name}={'true' if enabled else 'false'}\n")

    print("Changed paths:")
    for path in changed_files:
        print(f"  {path}")
    print(f"Release metadata-only change: {metadata_only}")
    print("Required checks:")
    for name, enabled in outputs.items():
        print(f"  {name}: {'yes' if enabled else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
