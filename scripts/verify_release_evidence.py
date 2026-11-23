#!/usr/bin/env python3
"""Fail closed unless successful CI artifacts match the release source fingerprints."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from quality_fingerprint import fingerprint_files, tracked_files

ARTIFACTS = {
    "deep": ("deep-quality-evidence", "deep_quality_fingerprint"),
    "compatibility": ("compatibility-evidence", "compatibility_fingerprint"),
    "openapi": ("openapi-contract-evidence", "deep_quality_fingerprint"),
}


def command(
    args: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, capture_output=True, text=True)


def artifact_run_ids(repository: str, artifact_name: str) -> list[str]:
    jq_filter = (
        f'.artifacts[] | select(.name == "{artifact_name}" '
        'and .expired == false) | .workflow_run.id'
    )
    result = command(
        [
            "gh",
            "api",
            "--paginate",
            "--jq",
            jq_filter,
            f"repos/{repository}/actions/artifacts?per_page=100",
        ]
    )
    run_ids = (line.strip() for line in result.stdout.splitlines() if line.strip())
    return list(dict.fromkeys(run_ids))


def run_succeeded(repository: str, run_id: str) -> bool:
    result = command(
        [
            "gh",
            "run",
            "view",
            run_id,
            "--repo",
            repository,
            "--json",
            "status,conclusion",
        ],
        check=False,
    )
    if result.returncode:
        return False
    try:
        run = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return run.get("status") == "completed" and run.get("conclusion") == "success"


def find_matching_evidence(
    repository: str, scope: str, expected_fingerprint: str
) -> str | None:
    artifact_name, field = ARTIFACTS[scope]
    for run_id in artifact_run_ids(repository, artifact_name):
        if not run_succeeded(repository, run_id):
            continue
        with tempfile.TemporaryDirectory(prefix="release-evidence-") as directory:
            downloaded = command(
                [
                    "gh",
                    "run",
                    "download",
                    run_id,
                    "--repo",
                    repository,
                    "--name",
                    artifact_name,
                    "--dir",
                    directory,
                ],
                check=False,
            )
            if downloaded.returncode:
                continue
            for candidate in Path(directory).rglob("*.json"):
                try:
                    evidence = json.loads(candidate.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if (
                    evidence.get("schema") == 1
                    and evidence.get(field) == expected_fingerprint
                ):
                    return run_id
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope", choices=("deep", "compatibility", "openapi", "all"), default="all"
    )
    args = parser.parse_args()
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        raise SystemExit("GITHUB_REPOSITORY is required")
    files = tracked_files()
    expected = {
        "deep": fingerprint_files(files, scope="deep"),
        "compatibility": fingerprint_files(files, scope="compatibility"),
    }
    scopes = (
        ("deep", "compatibility", "openapi")
        if args.scope == "all"
        else (args.scope,)
    )
    missing = []
    for scope in scopes:
        run_id = find_matching_evidence(repository, scope, expected[scope])
        if run_id is None:
            missing.append(scope)
            print(f"MISSING: no successful {scope} evidence matches {expected[scope]}")
        else:
            print(
                f"REUSED: {scope} evidence from successful run #{run_id}; "
                f"fingerprint={expected[scope]}"
            )
    if missing:
        raise SystemExit(
            "Release evidence is incomplete for: "
            + ", ".join(missing)
            + ". Run the corresponding full quality workflow on a source tree "
            "with matching fingerprints before tagging."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
