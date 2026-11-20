#!/usr/bin/env python3
"""Classify changed repository paths for the always-running pull-request gate."""

from __future__ import annotations

import sys
from pathlib import Path

PYTHON_PATHS = (
    "django_api_versioning/",
    "tests/",
    "integration_test_project/",
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
    "scripts/check_tox_workflow_matrix.py",
    "scripts/release_bootstrap.sh",
    "Makefile",
}
OPENAPI_PATHS = (
    "django_api_versioning/",
    "examples/openapi_contract/",
    "examples/consumer_migration/",
)
OPENAPI_EXPLICIT_PATHS = {
    "docs/design/versioned-openapi-contract.md",
    ".github/workflows/openapi-contract.yml",
    ".github/workflows/publish.yml",
}


def classify_paths(paths: list[str]) -> dict[str, bool]:
    """Return the workflows required for repository-relative changed paths."""
    normalized = [path.strip().removeprefix("./") for path in paths if path.strip()]

    is_python = any(
        path.startswith(PYTHON_PATHS)
        or path
        in {
            "pytest.ini",
            ".github/workflows/tests.yml",
            "scripts/verify_distribution_contents.py",
            "scripts/smoke_installed_wheel.py",
        }
        or path in PYTHON_DEPENDENCIES
        or (path.startswith("requirements") and path.endswith(".txt"))
        for path in normalized
    )
    is_compatibility = is_python or any(
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
        }
        for path in normalized
    )
    # Website examples are verified against the package checkout. A package,
    # test, or evidence-harness change must therefore run the website gate too.
    is_website = any(
        path.startswith(WEBSITE_PATHS + PYTHON_PATHS)
        or path in WEBSITE_EXAMPLE_PATHS
        or (path.startswith("requirements") and path.endswith(".txt"))
        or path
        in {
            ".github/workflows/website-data-preflight.yml",
            "scripts/verify_website_examples.py",
        }
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
    needs_dependency_review = any(
        path in PYTHON_DEPENDENCIES
        or path in {"website/package.json", "website/pnpm-lock.yaml"}
        or path.startswith("requirements")
        or path.endswith("/requirements.txt")
        for path in normalized
    )
    is_openapi = any(
        path.startswith(OPENAPI_PATHS) or path in OPENAPI_EXPLICIT_PATHS
        for path in normalized
    )

    return {
        "python": is_python,
        "compatibility": is_compatibility,
        "package": is_package,
        "website": is_website,
        "agent": is_agent,
        "dependency": needs_dependency_review,
        "openapi": is_openapi,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: classify_pr_changes.py <changed-files.txt> <github-output>",
            file=sys.stderr,
        )
        return 2

    changed_files = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    outputs = classify_paths(changed_files)
    with Path(sys.argv[2]).open("a", encoding="utf-8") as output_file:
        for name, enabled in outputs.items():
            output_file.write(f"{name}={'true' if enabled else 'false'}\n")

    print("Changed paths:")
    for path in changed_files:
        print(f"  {path}")
    print("Required checks:")
    for name, enabled in outputs.items():
        print(f"  {name}: {'yes' if enabled else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
