#!/usr/bin/env python3
"""Validate repository-level GitHub Actions governance invariants."""

from __future__ import annotations

import re
import sys
from pathlib import Path

WORKFLOWS = Path(".github/workflows")
ACTION_REF = re.compile(r"^[^\s#]+@[0-9a-f]{40}(?:\s+#.*)?$")


def validate() -> list[str]:
    errors: list[str] = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        for line_number, line in enumerate(
            workflow.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = re.match(r"^\s*uses:\s*(.+?)\s*$", line)
            if not match:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            if not ACTION_REF.fullmatch(reference):
                errors.append(
                    f"{workflow}:{line_number}: external Action is not pinned "
                    "to a full 40-character commit SHA"
                )

    gate = WORKFLOWS / "pull-request-gate.yml"
    if not gate.exists():
        errors.append("Missing .github/workflows/pull-request-gate.yml")
    else:
        content = gate.read_text(encoding="utf-8")
        trigger = content.split("\npermissions:", maxsplit=1)[0]
        if "pull_request:" not in trigger:
            errors.append("PR gate must subscribe to pull_request")
        if re.search(r"^\s+paths(-ignore)?:", trigger, flags=re.MULTILINE):
            errors.append("PR gate must not use workflow-level path filters")
        if not re.search(r"^  gate:\n", content, flags=re.MULTILINE):
            errors.append("PR gate must define the final gate job")
        if not re.search(r"^    name: PR gate$", content, flags=re.MULTILINE):
            errors.append("The final required check context must be named 'PR gate'")

    for filename in (
        "tests.yml",
        "compatibility.yml",
        "package-artifacts.yml",
        "agent-tooling.yml",
        "website-data-preflight.yml",
    ):
        workflow = WORKFLOWS / filename
        if workflow.exists():
            content = workflow.read_text(encoding="utf-8")
            if "workflow_call:" not in content:
                errors.append(f"{workflow} must support workflow_call")
            if re.search(r"^  pull_request:", content, flags=re.MULTILINE):
                errors.append(
                    f"{workflow} must be called by the PR gate, not run as "
                    "a separate path-filtered PR workflow"
                )

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print("Repository workflow governance checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
