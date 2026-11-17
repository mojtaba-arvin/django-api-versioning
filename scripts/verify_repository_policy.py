#!/usr/bin/env python3
"""Validate repository-level GitHub Actions governance invariants."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKFLOWS = Path(".github/workflows")
ACTION_REF = re.compile(r"^[^\s#]+@[0-9a-f]{40}(?:\s+#.*)?$")


def _validate_action_pins(errors: list[str]) -> None:
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


def _validate_website_contract(errors: list[str]) -> None:
    website = Path("website")
    package_json = website / "package.json"
    lockfile = website / "pnpm-lock.yaml"
    if not package_json.is_file() or not lockfile.is_file():
        errors.append("Website must have package.json and its pnpm lockfile")
    else:
        try:
            package_manager = json.loads(package_json.read_text(encoding="utf-8")).get(
                "packageManager"
            )
        except (json.JSONDecodeError, OSError):
            package_manager = None
        if package_manager != "pnpm@10.12.1":
            errors.append("Website packageManager must be pinned to pnpm@10.12.1")

    if (website / "package-lock.json").exists() or (
        WORKFLOWS / "website-lock.yml"
    ).exists():
        errors.append("Obsolete npm website lockfile workflow/configuration remains")

    for nested in (website / ".agents" / "skills", website / ".claude" / "skills"):
        if nested.exists():
            errors.append(f"{nested} duplicates the repository-root skill registry")


def _validate_pr_gate(errors: list[str]) -> None:
    gate = WORKFLOWS / "pull-request-gate.yml"
    if not gate.exists():
        errors.append("Missing .github/workflows/pull-request-gate.yml")
        return

    content = gate.read_text(encoding="utf-8")
    trigger = content.split("\npermissions:", maxsplit=1)[0]
    if "pull_request:" not in trigger:
        errors.append("PR gate must subscribe to pull_request")
    if not re.search(r"^\s+branches:\s*\[main\]$", trigger, flags=re.MULTILINE):
        errors.append("PR gate must target pull requests to main")
    if re.search(r"^\s+paths(-ignore)?:", trigger, flags=re.MULTILINE):
        errors.append("PR gate must not use workflow-level path filters")
    if not re.search(r"^  gate:\n", content, flags=re.MULTILINE):
        errors.append("PR gate must define the final gate job")
    if not re.search(r"^    name: PR gate$", content, flags=re.MULTILINE):
        errors.append("The final required check context must be named 'PR gate'")


def _validate_oidc_permissions(errors: list[str]) -> None:
    id_token_workflows = [
        workflow.name
        for workflow in sorted(WORKFLOWS.glob("*.yml"))
        if "id-token: write" in workflow.read_text(encoding="utf-8")
    ]
    if id_token_workflows != ["publish.yml"]:
        errors.append("Only publish.yml may grant id-token: write")


def _has_root_contents_read(root_section: str) -> bool:
    lines = root_section.splitlines()
    try:
        permissions_index = lines.index("permissions:")
    except ValueError:
        return False

    for line in lines[permissions_index + 1:]:
        if line and not line[0].isspace():
            break
        if line == "  contents: read":
            return True
    return False


def _validate_workflow_permissions(errors: list[str]) -> None:
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        content = workflow.read_text(encoding="utf-8")
        if "pull_request_target:" in content:
            errors.append(f"{workflow} must not use pull_request_target")
        root_section = content.split("\njobs:", maxsplit=1)[0]
        if not _has_root_contents_read(root_section):
            errors.append(f"{workflow} must default to contents: read")

    evidence = WORKFLOWS / "generate-evidence.yml"
    if not evidence.exists():
        errors.append("Missing .github/workflows/generate-evidence.yml")
        return
    content = evidence.read_text(encoding="utf-8")

    def job_block(name: str) -> str:
        match = re.search(
            rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
            content,
        )
        return match.group(1) if match else ""

    generator = job_block("generate-and-verify")
    committer = job_block("commit-evidence")
    if not re.search(r"(?m)^    permissions:\n      contents: read$", generator):
        errors.append("Evidence generation must run with contents: read")
    if "persist-credentials: false" not in generator:
        errors.append("Evidence generation checkout must not persist its read token")
    if re.search(r"(?m)^      contents: write$", generator):
        errors.append("Evidence generation must not receive contents: write")
    if not re.search(r"(?m)^    permissions:\n      contents: write$", committer):
        errors.append(
            "Only the isolated evidence commit job may receive contents: write"
        )
    if "persist-credentials: true" not in committer:
        errors.append(
            "Evidence commit job must explicitly persist its write token for git push"
        )
    if not generator or not committer:
        errors.append(
            "Evidence workflow must separate generation and commit into distinct jobs"
        )
    if re.search(r"(?m)^\s*(?:python|node|npm|pnpm|uv|tox)\b", committer):
        errors.append("Evidence commit job must not execute repository or package code")
    if "--force" in committer or "git reset" in committer:
        errors.append("Evidence commit job must not rewrite or reset Git history")

    write_grants = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            if re.match(r"^\s*contents:\s*write\s*$", line):
                write_grants.append((workflow.name, len(line) - len(line.lstrip())))
    if write_grants != [("generate-evidence.yml", 6)]:
        errors.append("Only generate-evidence's commit job may grant contents: write")


def _validate_reusable_workflows(errors: list[str]) -> None:
    filenames = (
        "tests.yml",
        "compatibility.yml",
        "package-artifacts.yml",
        "agent-tooling.yml",
        "website-data-preflight.yml",
    )
    for filename in filenames:
        workflow = WORKFLOWS / filename
        if not workflow.exists():
            continue
        content = workflow.read_text(encoding="utf-8")
        if "workflow_call:" not in content:
            errors.append(f"{workflow} must support workflow_call")
        if re.search(r"^  pull_request:", content, flags=re.MULTILINE):
            errors.append(
                f"{workflow} must be called by the PR gate, not run as "
                "a separate path-filtered PR workflow"
            )


def validate() -> list[str]:
    errors: list[str] = []
    _validate_action_pins(errors)
    _validate_website_contract(errors)
    _validate_pr_gate(errors)
    _validate_oidc_permissions(errors)
    _validate_workflow_permissions(errors)
    _validate_reusable_workflows(errors)
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
