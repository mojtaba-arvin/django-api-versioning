#!/usr/bin/env python3
"""Verify that public website examples still match executable package fixtures."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_docs_contracts import (
    verify_compatibility_article,
    verify_settings_and_endpoint_contract,
)
CONTENT = ROOT / "website" / "src" / "data" / "content.ts"
GENERATED = ROOT / "website" / "src" / "data" / "generated"
CLI_OUTPUT = GENERATED / "check_versions_output.txt"
ROUTES = GENERATED / "routes.json"
REFERENCE = ROOT / "docs" / "reference" / "index.md"
EXCEPTIONS = ROOT / "django_api_versioning" / "exceptions.py"
SETTINGS = ROOT / "django_api_versioning" / "settings.py"
DECORATORS = ROOT / "django_api_versioning" / "decorators.py"
COMPATIBILITY_ARTICLE = ROOT / "docs" / "articles" / "024-django-api-versioning-supported-versions.md"
PYPROJECT = ROOT / "pyproject.toml"
TOX = ROOT / "tox.ini"
MIGRATE_COMMAND = (
    ROOT / "django_api_versioning" / "management" / "commands" / "migrate_endpoints.py"
)


def snippet(source: str, key: str) -> str:
    delimiter = re.escape(chr(96))
    pattern = r"(?ms)^ *" + re.escape(key) + r": *" + delimiter + r"(.*?)" + delimiter
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


def markdown_fence(source: str, language: str, title: str) -> str:
    """Return a titled fenced code block from the canonical Reference Markdown."""
    lines = source.splitlines()
    opening = f'~~~{language} title="{title}"'
    try:
        start = lines.index(opening)
        end = lines.index("~~~", start + 1)
    except ValueError as exc:
        raise ValueError(f"Could not locate Reference code block {title!r}.") from exc
    return chr(10).join(lines[start + 1 : end])


def verify_reference(source: str, actual_output: str) -> None:
    """Check the human-facing Reference against package APIs and live evidence."""
    settings_source = SETTINGS.read_text(encoding="utf-8")
    for name in (
        "API_BASE_PATH",
        "API_MIN_VERSION",
        "API_MAX_VERSION",
        "API_VERSION_LIFECYCLE",
        "API_VERSIONING_CHANNELS",
        "API_EFFECTIVE_VERSION_RESOLVER",
    ):
        if name not in settings_source or f"`{name}`" not in source:
            raise ValueError(f"Reference settings entry {name!r} is missing or stale.")

    decorator_source = DECORATORS.read_text(encoding="utf-8")
    verify_settings_and_endpoint_contract(source, settings_source, decorator_source)
    syntax = ast.parse(decorator_source)
    endpoint = next(
        node
        for node in syntax.body
        if isinstance(node, ast.FunctionDef) and node.name == "endpoint"
    )
    for argument in ("postfix", "version", "versions", "app_name", "view_name"):
        if (
            argument not in [arg.arg for arg in endpoint.args.args]
            or f"`{argument}`" not in source
        ):
            raise ValueError(
                f"Reference @endpoint argument {argument!r} is missing or stale."
            )

    exception_source = EXCEPTIONS.read_text(encoding="utf-8")
    exception_names = [
        line.split()[1].split("(")[0]
        for line in exception_source.splitlines()
        if line.startswith("class ") and "(" in line
    ]
    for name in exception_names:
        if f"`{name}`" not in source:
            raise ValueError(f"Reference exception {name!r} is missing.")

    example = markdown_fence(source, "python", "views.py")
    try:
        ast.parse(example)
    except SyntaxError as exc:
        message = f"Reference endpoint example is not valid Python: {exc}"
        raise ValueError(message) from exc

    cli_block = markdown_fence(source, "text", "check_versions output")
    command, separator, displayed_output = cli_block.partition(chr(10))
    if not separator or command.strip() != "$ python manage.py check_versions":
        raise ValueError(
            "Reference check_versions block must include the documented command."
        )
    if displayed_output.rstrip(chr(10)) != actual_output.rstrip(chr(10)):
        raise ValueError(
            "Reference check_versions output differs from current "
            "package-generated output."
        )

    migration = markdown_fence(source, "bash", "migrate_endpoints")
    if migration.strip() != "$ python manage.py migrate_endpoints --dry-run":
        raise ValueError(
            "Reference migrate_endpoints block must use the non-writing "
            "preview command."
        )
    if not MIGRATE_COMMAND.is_file() or "--dry-run" not in MIGRATE_COMMAND.read_text(
        encoding="utf-8"
    ):
        raise ValueError(
            "Reference migrate_endpoints example has no matching package command."
        )


def main() -> int:
    if (
        not CONTENT.is_file()
        or not CLI_OUTPUT.is_file()
        or not ROUTES.is_file()
        or not REFERENCE.is_file()
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
        reference_source = REFERENCE.read_text(encoding="utf-8")
        verify_reference(
            reference_source,
            CLI_OUTPUT.read_text(encoding="utf-8").removeprefix(chr(10)),
        )
        verify_compatibility_article(
            COMPATIBILITY_ARTICLE.read_text(encoding="utf-8"),
            PYPROJECT.read_text(encoding="utf-8"),
            TOX.read_text(encoding="utf-8"),
        )
    except (ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    command, separator, displayed_output = cli_example.partition(chr(10))
    if not separator or command.strip() != "$ python manage.py check_versions":
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
        row.get("path"): row.get("status") for row in quick_start.get("requests", [])
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
