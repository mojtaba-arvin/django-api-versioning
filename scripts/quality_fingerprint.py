#!/usr/bin/env python3
"""Fingerprint the source and effective CI configuration behind quality evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path
from typing import Mapping

QUALITY_PREFIXES = (
    "django_api_versioning/",
    "tests/",
    "integration_test_project/",
    "examples/openapi_contract/",
    "examples/consumer_migration/",
)
COMPATIBILITY_FILES = {
    "pyproject.toml",
    "uv.lock",
    "tox.ini",
    "scripts/check_tox_workflow_matrix.py",
    ".github/workflows/compatibility.yml",
}
QUALITY_FILES = COMPATIBILITY_FILES | {
    "pytest.ini",
    "mutmut_config.py",
    "setup.cfg",
    "scripts/check_coverage_thresholds.py",
    ".github/workflows/tests.yml",
    ".github/workflows/adversarial-testing.yml",
    ".github/workflows/openapi-contract.yml",
    ".github/workflows/pull-request-gate.yml",
    ".github/workflows/mutation-shard.yml",
    ".github/actions/mutation-shard/action.yml",
    "scripts/quality_fingerprint.py",
    "scripts/verify_release_evidence.py",
    ".github/workflows/publish.yml",
}


def _normalize(path: str, content: bytes) -> bytes:
    """Remove only the release version fields that do not affect runtime quality."""
    if path not in {"pyproject.toml", "uv.lock"}:
        return content
    data = tomllib.loads(content.decode("utf-8"))
    if path == "pyproject.toml":
        data["project"]["version"] = "<PACKAGE_VERSION>"
    else:
        data.pop("content-hash", None)
        for package in data.get("package", []):
            if package.get("name") == "django-api-versioning":
                package["version"] = "<PACKAGE_VERSION>"
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint_files(files: Mapping[str, bytes], *, scope: str) -> str:
    """Hash a deterministic set of relevant file paths and normalized contents."""
    if scope not in {"deep", "compatibility"}:
        raise ValueError(f"Unsupported fingerprint scope: {scope}")
    selected = {}
    for path, content in files.items():
        if scope == "compatibility":
            include = path in COMPATIBILITY_FILES or (
                path.startswith("requirements") and path.endswith(".txt")
            )
        else:
            include = (
                path.startswith(QUALITY_PREFIXES)
                or path in QUALITY_FILES
                or (path.startswith("requirements") and path.endswith(".txt"))
            )
        if include:
            selected[path] = content
    if not selected:
        raise ValueError(f"No files selected for {scope} fingerprint")
    digest = hashlib.sha256()
    for path in sorted(selected):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_normalize(path, selected[path]))
        digest.update(b"\0")
    return digest.hexdigest()


def tracked_files() -> dict[str, bytes]:
    paths = subprocess.run(
        ["git", "ls-files", "-z"], check=True, capture_output=True
    ).stdout.split(b"\0")
    files: dict[str, bytes] = {}
    for raw_path in paths:
        if not raw_path:
            continue
        path = raw_path.decode("utf-8")
        if (
            path.startswith(QUALITY_PREFIXES)
            or path in QUALITY_FILES
            or path in COMPATIBILITY_FILES
            or (path.startswith("requirements") and path.endswith(".txt"))
        ):
            files[path] = Path(path).read_bytes()
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {
        "schema": 1,
        "commit_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip(),
        "tree_sha": subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"], check=True, capture_output=True, text=True
        ).stdout.strip(),
        "deep_quality_fingerprint": fingerprint_files(tracked_files(), scope="deep"),
        "compatibility_fingerprint": fingerprint_files(
            tracked_files(), scope="compatibility"
        ),
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
