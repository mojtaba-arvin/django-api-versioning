#!/usr/bin/env python3
"""Verify that public website examples still match executable package fixtures."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "website" / "src" / "data" / "content.ts"
GENERATED = ROOT / "website" / "src" / "data" / "generated"
CLI_OUTPUT = GENERATED / "check_versions_output.txt"
ROUTES = GENERATED / "routes.json"


def snippet(source: str, key: str) -> str:
    delimiter = re.escape(chr(96))
    pattern = (
        r"(?ms)^ *" + re.escape(key) + r": *" + delimiter + r"(.*?)" + delimiter
    )
    match = re.search(pattern, source)
    if match is None:
        raise ValueError(f"Could not locate snippets.{key} in website content.")
    return match.group(1)


def normalize_code(value: str) -> str:
    lines = [line.rstrip() for line in value.strip().splitlines()]
    if lines and lines[0] == "# isort: skip_file":
        lines = lines[1:]
    normalized = chr(10).join(lines)
    triple_newline = chr(10) * 3
    double_newline = chr(10) * 2
    while triple_newline in normalized:
        normalized = normalized.replace(triple_newline, double_newline)
    return normalized


def verify_package_symbols(source: str, evidence: dict) -> None:
    symbols = evidence.get("source_refs", {}).get("symbols", {})
    lines = evidence.get("source_refs", {}).get("lines", {})
    checks = {
        "settings": (
            "APISettings.from_django_settings",
            ("API_BASE_PATH", "API_MIN_VERSION", "API_MAX_VERSION"),
        ),
        "urls": (
            "registry_urlpatterns",
            ("django_api_versioning.urls", "urlpatterns"),
        ),
        "snapshot": ("assert_version_matrix", ("assert_version_matrix",)),
        "reverse": ("api_reverse", ("api_reverse",)),
        "lifecycle": (
            "LifecycleMiddleware.__call__",
            ("django_api_versioning.lifecycle.LifecycleMiddleware",),
        ),
        "checkVersions": ("check_versions.handle", ("manage.py check_versions",)),
    }
    for key, (reference, tokens) in checks.items():
        available = reference in symbols or reference in lines
        example = snippet(source, key)
        if not available or any(token not in example for token in tokens):
            raise ValueError(
                f"Website snippet {key!r} no longer matches its package API reference."
            )

    migrate_command = (
        ROOT
        / "django_api_versioning"
        / "management"
        / "commands"
        / "migrate_endpoints.py"
    )
    if not migrate_command.is_file() or "migrate_endpoints" not in snippet(
        source, "migrate"
    ):
        raise ValueError("Website migrate_endpoints example has no package command.")


def main() -> int:
    if (
        not CONTENT.is_file()
        or not CLI_OUTPUT.is_file()
        or not ROUTES.is_file()
    ):
        print(
            "Website example inputs or generated package evidence are missing.",
            file=sys.stderr,
        )
        return 1

    source = CONTENT.read_text(encoding="utf-8")
    try:
        cli_example = snippet(source, "checkVersions")
        hero_example = snippet(source, "heroView")
        evidence = json.loads(ROUTES.read_text(encoding="utf-8"))
        verify_package_symbols(source, evidence)
    except (ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    command, separator, displayed_output = cli_example.partition(chr(10))
    if (
        not separator
        or command.strip() != "$ python manage.py check_versions"
    ):
        print(
            "The website check_versions example must retain its documented command.",
            file=sys.stderr,
        )
        return 1

    actual_output = CLI_OUTPUT.read_text(encoding="utf-8").removeprefix(chr(10))
    newline = chr(10)
    if displayed_output.rstrip(newline) != actual_output.rstrip(newline):
        print(
            "The website check_versions example is stale. Update it only after "
            "reviewing the current package-generated output.",
            file=sys.stderr,
        )
        print("--- website example ---", file=sys.stderr)
        print(displayed_output, file=sys.stderr)
        print("--- current package output ---", file=sys.stderr)
        print(actual_output, file=sys.stderr)
        return 1

    scenarios = evidence.get("scenarios", {})
    quick_start = scenarios.get("website_quick_start", {})
    fixture = quick_start.get("views_source") or {}
    if normalize_code(hero_example) != normalize_code(fixture.get("code", "")):
        print(
            "The website hero endpoint snippet differs from its executable fixture.",
            file=sys.stderr,
        )
        return 1

    observed = {
        row.get("path"): row.get("status")
        for row in quick_start.get("requests", [])
    }
    expected = {
        "/api/v1/invoices/42/": 404,
        "/api/v2/invoices/42/": 200,
        "/api/v3/invoices/42/": 200,
    }
    if observed != expected:
        print(
            f"The website endpoint example produced unexpected responses: {observed!r}",
            file=sys.stderr,
        )
        return 1

    for row in quick_start.get("requests", []):
        if row.get("status") == 200 and row.get("body") != {
            "id": 42,
            "status": "paid",
        }:
            print(
                f"The website endpoint example returned an unexpected body for "
                f"{row.get('path')!r}: {row.get('body')!r}",
                file=sys.stderr,
            )
            return 1

    print(
        "Website CLI and endpoint examples match the current package's "
        "generated output and executable behavior."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
