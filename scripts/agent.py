#!/usr/bin/env python3
"""Dependency-free diagnostics, context selection, and validation for coding agents."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = {
    "AGENTS.md": 6500,
    "CLAUDE.md": 1800,
    ".github/copilot-instructions.md": 1400,
}
CONTEXT_PROFILES: dict[str, dict[str, Any]] = {
    "implementation": {
        "skill": ".agents/skills/package-engineering/SKILL.md",
        "read": [
            "pyproject.toml",
            "docs/reference/versioning-contract.md",
            "relevant package modules and callers",
            "matching unit tests",
            "integration_test_project/ only when framework wiring changes",
        ],
        "avoid": [
            "all articles",
            "full compatibility report",
            "unrelated website source",
        ],
    },
    "audit": {
        "skill": ".agents/skills/package-audit/SKILL.md",
        "read": [
            "pyproject.toml",
            "tox.ini",
            "docs/reference/versioning-contract.md",
            "package source",
            "relevant unit/integration tests",
            "packaging and CI",
        ],
        "avoid": [
            "website source unless a website claim is in scope",
            "historical test logs as current evidence",
        ],
    },
    "testing": {
        "skill": ".agents/skills/manual-testing/SKILL.md",
        "read": [
            "tox.ini",
            "pyproject.toml",
            "pytest.ini",
            "integration_test_project/pytest.ini",
            "scripts/check_tox_workflow_matrix.py",
        ],
        "avoid": [
            "package source unless diagnosing a failing test",
            "all test files when a focused test is sufficient",
        ],
    },
    "release": {
        "skill": ".agents/skills/release/SKILL.md",
        "read": [
            "pyproject.toml",
            "CHANGELOG.md",
            "COMPATIBILITY_REPORT.md",
            ".github/workflows/compatibility.yml",
            ".github/workflows/package-artifacts.yml",
            ".github/workflows/publish.yml",
        ],
        "avoid": [
            "all articles before the release workflow's technical-impact gate",
            "publishing without explicit version-specific authorization",
        ],
    },
    "website": {
        "skill": ".agents/skills/website-engineering/SKILL.md",
        "read": [
            "website/AGENTS.md",
            "affected website source and tests",
            "relevant website workflows",
        ],
        "avoid": [
            "package internals unless verifying a specific evidence claim",
            "all articles when only one page changes",
        ],
    },
    "agent-maintenance": {
        "skill": ".agents/skills/agent-maintenance/SKILL.md",
        "read": [
            "AGENTS.md",
            "CLAUDE.md",
            ".github/copilot-instructions.md",
            "scripts/agent.py",
            ".agents/skills/ metadata",
            "only the skill/adapter being changed",
            ".github/workflows/agent-tooling.yml",
        ],
        "avoid": [
            "all skill bodies",
            "package implementation and tests unless affected",
        ],
    },
}


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the small scalar metadata subset used by this repository's skills."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}

    values: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.fullmatch(r"(name|description):\s*(.*?)\s*", line)
        if not match:
            continue
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[match.group(1)] = value
    return values


def context_profile(name: str) -> dict[str, Any]:
    """Return a curated reading set without loading the referenced files."""
    if name not in CONTEXT_PROFILES:
        raise KeyError(name)
    return CONTEXT_PROFILES[name]


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_reference_links(skill_file: Path, root: Path = ROOT) -> list[str]:
    """Check local Markdown links in a skill without fetching external URLs."""
    errors: list[str] = []
    root = root.resolve()
    content = skill_file.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", content):
        if target.startswith(("#", "https://", "http://", "mailto:", "//")):
            continue
        local_target = target.split("#", 1)[0].split("?", 1)[0]
        if not local_target:
            continue
        resolved = (skill_file.parent / local_target).resolve()
        if not resolved.is_relative_to(root):
            errors.append(
                f"{skill_file.relative_to(root)} link escapes repository: {target}"
            )
        elif not resolved.is_file():
            errors.append(
                f"{skill_file.relative_to(root)} has a missing reference: {target}"
            )
    return errors


def _validate_instruction_budgets(root: Path) -> list[str]:
    """Enforce character budgets for always-loaded client instructions."""
    errors: list[str] = []
    for relative, maximum in BUDGETS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"Missing instruction entry point: {relative}")
            continue
        actual = len(path.read_text(encoding="utf-8"))
        if actual > maximum:
            errors.append(f"{relative}: {actual} characters exceeds budget {maximum}")
    return errors


def _validate_canonical_skills(
    root: Path,
) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Validate canonical skill names, frontmatter, and on-demand references."""
    errors: list[str] = []
    skills_root = root / ".agents" / "skills"
    if not skills_root.is_dir():
        return {}, ["Missing canonical .agents/skills directory"]

    canonical: dict[str, dict[str, str]] = {}
    for directory in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        slug = directory.name
        skill_file = directory / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{skill_file.relative_to(root)} is missing")
            continue

        metadata = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            errors.append(f"Invalid skill directory name: {slug}")
        if set(metadata) != {"name", "description"}:
            errors.append(
                f"{skill_file.relative_to(root)} needs name and description frontmatter"
            )
        if metadata.get("name") != slug:
            errors.append(
                f"{skill_file.relative_to(root)} name must match directory {slug}"
            )
        description = metadata.get("description", "")
        if not description or len(description) > 1024:
            errors.append(
                f"{skill_file.relative_to(root)} has an empty or overlong description"
            )
        errors.extend(validate_reference_links(skill_file, root))
        if metadata.get("name") in (item.get("name") for item in canonical.values()):
            errors.append(f"Duplicate canonical skill name: {metadata.get('name')}")
        canonical[slug] = metadata

    return canonical, errors


def _validate_claude_adapters(
    root: Path, canonical: dict[str, dict[str, str]]
) -> list[str]:
    """Keep Claude's discoverable skill stubs in sync with canonical skills."""
    errors: list[str] = []
    claude_root = root / ".claude" / "skills"
    if not claude_root.is_dir():
        return ["Missing Claude skill adapter directory"]

    for slug, metadata in canonical.items():
        adapter = claude_root / slug / "SKILL.md"
        if not adapter.is_file():
            errors.append(f"Missing Claude adapter: {adapter.relative_to(root)}")
            continue

        adapter_text = adapter.read_text(encoding="utf-8")
        if parse_frontmatter(adapter_text) != metadata:
            errors.append(
                f"Claude adapter metadata differs from canonical skill: {slug}"
            )
        target = f"../../../.agents/skills/{slug}/SKILL.md"
        resolved = (adapter.parent / target).resolve()
        if target not in adapter_text:
            errors.append(
                f"Claude adapter does not delegate to canonical skill: {slug}"
            )
        if not resolved.is_file() or not resolved.is_relative_to(root):
            errors.append(
                f"Claude adapter target is missing or escapes repository: {slug}"
            )
        if len(adapter_text) > 900:
            errors.append(f"Claude adapter is too large; keep it as a pointer: {slug}")

    for directory in sorted(path for path in claude_root.iterdir() if path.is_dir()):
        if directory.name not in canonical:
            errors.append(f"Claude adapter has no canonical skill: {directory.name}")
    return errors


def _validate_copilot_adapter(root: Path) -> list[str]:
    """Check the GitHub Copilot code-review adapter."""
    skill = root / ".github" / "skills" / "package-review" / "SKILL.md"
    if not skill.is_file():
        return ["Missing Copilot package-review skill"]

    content = skill.read_text(encoding="utf-8")
    metadata = parse_frontmatter(content)
    if metadata.get("name") != "package-review" or not metadata.get("description"):
        return ["Copilot review skill needs name/description frontmatter"]

    target = "../../../.agents/skills/package-audit/SKILL.md"
    resolved = (skill.parent / target).resolve()
    if target not in content:
        return ["Copilot review skill must delegate to canonical package-audit"]
    if not resolved.is_file() or not resolved.is_relative_to(root):
        return ["Copilot review target is missing or escapes repository"]
    return []


def _validate_model_settings(root: Path) -> list[str]:
    """Reject shared project settings that override collaborators' model choice."""
    settings = root / ".claude" / "settings.json"
    if not settings.is_file():
        return []
    try:
        configured = _read_json(settings)
    except (json.JSONDecodeError, ValueError):
        return [".claude/settings.json is invalid JSON"]
    if "model" in configured:
        return ["Do not pin a model in shared .claude/settings.json"]
    return []


def _validate_scenario(scenario: Any, seen: set[str]) -> list[str]:
    """Validate one evaluation scenario and update the unique-id set."""
    if not isinstance(scenario, dict):
        return ["Each evaluation scenario must be an object"]

    errors: list[str] = []
    scenario_id = scenario.get("id")
    label = scenario_id if isinstance(scenario_id, str) else "<missing id>"
    if not isinstance(scenario_id, str) or not scenario_id or scenario_id in seen:
        errors.append(f"Invalid or duplicate evaluation scenario id: {label}")
    else:
        seen.add(scenario_id)

    profile = scenario.get("profile")
    if not isinstance(profile, str) or profile not in CONTEXT_PROFILES:
        errors.append(f"Unknown profile in evaluation scenario: {label}")

    task = scenario.get("task")
    if not isinstance(task, str) or not task.strip():
        errors.append(f"Evaluation scenario {label} needs a non-empty task")

    for field in ("checks", "failure_modes"):
        values = scenario.get(field)
        valid_values = (
            isinstance(values, list)
            and bool(values)
            and all(isinstance(value, str) and value.strip() for value in values)
        )
        if not valid_values:
            errors.append(
                f"Evaluation scenario {label} needs non-empty string values for {field}"
            )
    return errors


def _validate_evaluation_suite(root: Path) -> list[str]:
    """Validate the versioned, model-agnostic Agent evaluation scenarios."""
    path = root / ".agents" / "evals" / "scenarios.json"
    if not path.is_file():
        return ["Missing .agents/evals/scenarios.json"]
    try:
        suite = _read_json(path)
    except (json.JSONDecodeError, ValueError) as exc:
        return [f"Invalid evaluation suite: {exc}"]

    scenarios = suite.get("scenarios")
    if suite.get("schema_version") != 1 or not isinstance(scenarios, list):
        return ["Agent evaluation suite has an invalid schema or no scenarios"]
    if not scenarios:
        return ["Agent evaluation suite has an invalid schema or no scenarios"]

    errors: list[str] = []
    seen: set[str] = set()
    for scenario in scenarios:
        errors.extend(_validate_scenario(scenario, seen))
    return errors


def validate_tree(root: Path = ROOT) -> list[str]:
    """Validate instructions, skills, client adapters, and evaluation cases."""
    root = root.resolve()
    errors = _validate_instruction_budgets(root)
    canonical, skill_errors = _validate_canonical_skills(root)
    errors.extend(skill_errors)
    errors.extend(_validate_claude_adapters(root, canonical))
    errors.extend(_validate_copilot_adapter(root))
    errors.extend(_validate_model_settings(root))
    errors.extend(_validate_evaluation_suite(root))
    return errors


def _run_version(command: str) -> dict[str, str]:
    executable = shutil.which(command)
    if not executable:
        return {"status": "not-installed"}

    try:
        result = subprocess.run(
            [executable, "--version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        output = (result.stdout or result.stderr).strip().splitlines()
        return {
            "status": "available" if result.returncode == 0 else "error",
            "version": output[0] if output else "no version output",
            "exit_code": str(result.returncode),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "error", "detail": type(exc).__name__}


def doctor_report(root: Path = ROOT) -> dict[str, Any]:
    """Gather read-only repository and tool diagnostics without exposing env values."""
    version = "unknown"
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        match = re.search(
            r"(?ms)^\[project\]\s*$.*?^\s*version\s*=\s*[\"']([^\"']+)",
            pyproject.read_text(encoding="utf-8"),
        )
        if match:
            version = match.group(1)

    def git_value(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None

    branch = git_value("branch", "--show-current")
    status = git_value("status", "--porcelain")
    sha = git_value("rev-parse", "HEAD")
    tox_file = root / "tox.ini"
    tox_text = tox_file.read_text(encoding="utf-8") if tox_file.is_file() else ""

    if status == "" and branch:
        working_tree = "clean"
    elif status:
        working_tree = "dirty"
    else:
        working_tree = "unknown"

    return {
        "repository_root": str(root),
        "branch": branch or "not-a-git-checkout",
        "commit": sha or "unknown",
        "working_tree": working_tree,
        "package_version": version,
        "python": sys.version.split()[0],
        "tools": {
            name: _run_version(name)
            for name in ("git", "uv", "tox", "pytest", "claude")
        },
        "configuration": {
            "tox_requires_tox_uv": bool(
                re.search(r"(?m)^\s*requires\s*=.*tox-uv", tox_text)
            ),
            "integration_pytest_config": (
                root / "integration_test_project" / "pytest.ini"
            ).is_file(),
        },
    }


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dependency-free repository helpers for coding agents."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="read-only repository and tool diagnostics")

    context_parser = subparsers.add_parser("context", help="task-specific reading set")
    context_parser.add_argument("profile", choices=sorted(CONTEXT_PROFILES))
    context_parser.add_argument("--json", action="store_true")

    validate_parser = subparsers.add_parser(
        "validate", help="validate skills, adapters, and budgets"
    )
    validate_parser.add_argument("--json", action="store_true")

    eval_parser = subparsers.add_parser(
        "evals", help="list model/agent evaluation scenarios"
    )
    eval_parser.add_argument("--json", action="store_true")

    subparsers.add_parser(
        "verify", help="validate agent configuration and run its unit tests"
    )
    args = parser.parse_args(argv)

    if args.command == "doctor":
        _print_json(doctor_report())
        return 0

    if args.command == "context":
        profile = context_profile(args.profile)
        if args.json:
            _print_json({"profile": args.profile, **profile})
        else:
            print(f"Profile: {args.profile}\nSkill: {profile['skill']}\nRead:")
            for item in profile["read"]:
                print(f"  - {item}")
            print("Avoid unless required:")
            for item in profile["avoid"]:
                print(f"  - {item}")
        return 0

    if args.command == "evals":
        suite = _read_json(ROOT / ".agents" / "evals" / "scenarios.json")
        if args.json:
            _print_json(suite)
        else:
            print(f"Agent evaluation scenarios: {len(suite['scenarios'])}")
            for scenario in suite["scenarios"]:
                print(f"\n[{scenario['id']}] profile={scenario['profile']}")
                print(scenario["task"])
                for check in scenario["checks"]:
                    print(f"  - {check}")
        return 0

    errors = validate_tree()
    if args.command == "validate":
        budgets = {
            name: {
                "characters": len((ROOT / name).read_text(encoding="utf-8")),
                "approx_tokens_chars_div_4": math.ceil(
                    len((ROOT / name).read_text(encoding="utf-8")) / 4
                ),
                "max_characters": maximum,
            }
            for name, maximum in BUDGETS.items()
            if (ROOT / name).is_file()
        }
        result = {
            "valid": not errors,
            "errors": errors,
            "always_loaded_budgets": budgets,
        }
        if args.json:
            _print_json(result)
        elif errors:
            print("Agent configuration validation failed:")
            for error in errors:
                print(f"- {error}")
        else:
            skill_count = len(list((ROOT / ".agents/skills").glob("*/SKILL.md")))
            print(f"Agent configuration valid; {skill_count} canonical skills.")
            print(
                "Always-loaded instruction budgets "
                "(token estimate is characters / 4):"
            )
            for name, item in budgets.items():
                print(
                    f"  {name}: {item['characters']} chars; "
                    f"about {item['approx_tokens_chars_div_4']} tokens"
                )
        return 1 if errors else 0

    if errors:
        print("Agent configuration validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "scripts/agent_tests",
            "-v",
        ],
        cwd=ROOT,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
