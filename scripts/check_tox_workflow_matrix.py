#!/usr/bin/env python3
"""Fail when the GitHub Actions tox matrix drifts from tox.ini."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "compatibility.yml"


def matrix_entries_for_job(workflow_text: str, job_id: str) -> list[str]:
    """Return environment names from one job's matrix include list."""
    match = re.search(
        rf"(?ms)^  {re.escape(job_id)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
        workflow_text,
    )
    if match is None:
        raise ValueError(f"Could not find the {job_id!r} job in compatibility.yml.")

    return re.findall(
        r"^\s+- env:\s*([A-Za-z0-9_.-]+)\s*$",
        match.group(1),
        flags=re.MULTILINE,
    )


def main() -> int:
    tox_executable = shutil.which("tox")
    command = (
        [tox_executable, "config", "-k", "type", "--format", "json"]
        if tox_executable
        else [
            sys.executable,
            "-m",
            "tox",
            "config",
            "-k",
            "type",
            "--format",
            "json",
        ]
    )
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        return result.returncode

    try:
        configuration = json.loads(result.stdout)
        tox_environments = set(configuration["env"])
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        print(
            f"Could not read tox environments from tox config: {exc}",
            file=sys.stderr,
        )
        return 2

    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    try:
        full_entries = matrix_entries_for_job(workflow_text, "tox")
        smoke_entries = matrix_entries_for_job(workflow_text, "tox-pr-smoke")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    full_environments = set(full_entries)
    smoke_environments = set(smoke_entries)
    if len(full_entries) != len(full_environments):
        print(
            "Duplicate environment names found in the full tox matrix.",
            file=sys.stderr,
        )
        return 1
    if len(smoke_entries) != len(smoke_environments):
        print(
            "Duplicate environment names found in the PR smoke matrix.",
            file=sys.stderr,
        )
        return 1

    smoke_only = sorted(smoke_environments - full_environments)
    if smoke_only:
        print(
            "PR smoke environments are absent from the full matrix: "
            f"{', '.join(smoke_only)}",
            file=sys.stderr,
        )
        return 1

    missing_from_workflow = sorted(tox_environments - full_environments)
    missing_from_tox = sorted(full_environments - tox_environments)
    if missing_from_workflow or missing_from_tox:
        print(
            "tox.ini and the full compatibility matrix define different environments.",
            file=sys.stderr,
        )
        if missing_from_workflow:
            print(
                f"Missing from workflow matrix: {', '.join(missing_from_workflow)}",
                file=sys.stderr,
            )
        if missing_from_tox:
            print(
                f"Not configured in tox.ini: {', '.join(missing_from_tox)}",
                file=sys.stderr,
            )
        return 1

    print(
        f"Verified {len(tox_environments)} full tox environments and "
        f"{len(smoke_environments)} PR smoke environments."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
