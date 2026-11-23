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

WORKFLOWS = {
    "deep": ("pull-request-gate.yml", "tests.yml"),
    "compatibility": ("compatibility.yml", "pull-request-gate.yml"),
}
ARTIFACTS = {
    "deep": ("deep-quality-evidence", "deep_quality_fingerprint"),
    "compatibility": ("compatibility-evidence", "compatibility_fingerprint"),
}


def command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, capture_output=True, text=True)


def successful_runs(repository: str, workflow: str) -> list[dict[str, object]]:
    result = command(
        [
            "gh", "run", "list", "--repo", repository, "--workflow", workflow,
            "--status", "success", "--json", "databaseId,status,conclusion,event,headSha",
            "--limit", "100",
        ]
    )
    runs = json.loads(result.stdout)
    return [
        run for run in runs
        if run.get("status") == "completed" and run.get("conclusion") == "success"
    ]


def find_matching_evidence(
    repository: str, scope: str, expected_fingerprint: str
) -> tuple[str, str] | None:
    artifact_name, field = ARTIFACTS[scope]
    for workflow in WORKFLOWS[scope]:
        for run in successful_runs(repository, workflow):
            run_id = str(run["databaseId"])
            with tempfile.TemporaryDirectory(prefix="release-evidence-") as directory:
                downloaded = command(
                    [
                        "gh", "run", "download", run_id, "--repo", repository,
                        "--name", artifact_name, "--dir", directory,
                    ],
                    check=False,
                )
                if downloaded.returncode:
                    continue
                candidates = list(Path(directory).rglob("*.json"))
                for candidate in candidates:
                    try:
                        evidence = json.loads(candidate.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
                    if (
                        evidence.get("schema") == 1
                        and evidence.get(field) == expected_fingerprint
                    ):
                        return run_id, workflow
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("deep", "compatibility", "all"), default="all")
    args = parser.parse_args()
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        raise SystemExit("GITHUB_REPOSITORY is required")
    files = tracked_files()
    expected = {
        "deep": fingerprint_files(files, scope="deep"),
        "compatibility": fingerprint_files(files, scope="compatibility"),
    }
    scopes = ("deep", "compatibility") if args.scope == "all" else (args.scope,)
    missing = []
    for scope in scopes:
        match = find_matching_evidence(repository, scope, expected[scope])
        if match is None:
            missing.append(scope)
            print(f"MISSING: no successful {scope} evidence matches {expected[scope]}")
        else:
            run_id, workflow = match
            print(
                f"REUSED: {scope} evidence from {workflow} run #{run_id}; "
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
