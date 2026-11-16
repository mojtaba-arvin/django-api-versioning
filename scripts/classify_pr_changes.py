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
WEBSITE_PATHS = ("website/", "docs/articles/")
AGENT_PATHS = (".agents/", ".claude/", ".github/")
PYTHON_DEPENDENCIES = {
    "pyproject.toml",
    "uv.lock",
    "tox.ini",
    "requirements.txt",
    "requirements-ci.txt",
    "requirements-dev.txt",
    "requirements-build.txt",
}


def classify_paths(paths: list[str]) -> dict[str, bool]:
    """Return the workflows required for repository-relative changed paths."""
    normalized = [path.strip().removeprefix("./") for path in paths if path.strip()]

    is_python = any(
        path.startswith(PYTHON_PATHS)
        or path == "pytest.ini"
        or path in PYTHON_DEPENDENCIES
        for path in normalized
    )
    is_compatibility = is_python or any(
        path
        in {
            "tox.ini",
            ".github/workflows/compatibility.yml",
            "scripts/check_tox_workflow_matrix.py",
        }
        for path in normalized
    )
    is_package = any(
        path.startswith("django_api_versioning/")
        or path
        in {
            "pyproject.toml",
            "MANIFEST.in",
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
            "LICENSE.txt",
            "requirements.txt",
            "requirements-build.txt",
            "scripts/verify_distribution_contents.py",
            "scripts/smoke_installed_wheel.py",
        }
        for path in normalized
    )
    is_website = any(path.startswith(WEBSITE_PATHS) for path in normalized)
    is_agent = any(
        path
        in {
            "AGENTS.md",
            "CLAUDE.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "scripts/agent.py",
            "scripts/verify_repository_policy.py",
            "scripts/classify_pr_changes.py",
            "docs/agent-engineering.md",
        }
        or path.startswith(AGENT_PATHS)
        or path.startswith(".github/")
        or path.startswith("scripts/agent_tests/")
        for path in normalized
    )
    needs_dependency_review = any(
        path in PYTHON_DEPENDENCIES
        or path in {"website/package.json", "website/package-lock.json"}
        or path.startswith("requirements")
        for path in normalized
    )

    return {
        "python": is_python,
        "compatibility": is_compatibility,
        "package": is_package,
        "website": is_website,
        "agent": is_agent,
        "dependency": needs_dependency_review,
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
