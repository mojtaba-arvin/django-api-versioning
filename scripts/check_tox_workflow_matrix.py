#!/usr/bin/env python3
"""Fail when the GitHub Actions tox matrix drifts from tox.ini."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "compatibility.yml"


def main() -> int:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tox",
            "config",
            "-k",
            "type",
            "--format",
            "json",
        ],
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
    matrix_entries = re.findall(
        r"^\s+- env:\s*([A-Za-z0-9_.-]+)\s*$",
        workflow_text,
        flags=re.MULTILINE,
    )
    workflow_environments = set(matrix_entries)

    if len(matrix_entries) != len(workflow_environments):
        print(
            "Duplicate environment names found in compatibility.yml.",
            file=sys.stderr,
        )
        return 1

    missing_from_workflow = sorted(tox_environments - workflow_environments)
    missing_from_tox = sorted(workflow_environments - tox_environments)
    if missing_from_workflow or missing_from_tox:
        print(
            "tox.ini and compatibility.yml define different environments.",
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

    print(f"Verified {len(tox_environments)} tox environments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
