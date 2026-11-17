#!/usr/bin/env python3
"""Verify that package-derived CLI output shown on the website is current."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "website" / "src" / "data" / "content.ts"
CLI_OUTPUT = (
    ROOT / "website" / "src" / "data" / "generated" / "check_versions_output.txt"
)


def main() -> int:
    if not CONTENT.is_file() or not CLI_OUTPUT.is_file():
        print(
            "Website example inputs or generated CLI evidence are missing.",
            file=sys.stderr,
        )
        return 1

    source = CONTENT.read_text(encoding="utf-8")
    delimiter = re.escape(chr(96))
    pattern = r"(?ms)^ *checkVersions: *" + delimiter + r"(.*?)" + delimiter
    match = re.search(pattern, source)
    if match is None:
        print(
            "Could not locate snippets.checkVersions in website content.",
            file=sys.stderr,
        )
        return 1

    displayed = match.group(1)
    command, separator, displayed_output = displayed.partition(chr(10))
    if not separator or command.strip() != "$ python manage.py check_versions":
        print(
            "The website check_versions example must retain its documented command.",
            file=sys.stderr,
        )
        return 1

    actual_output = CLI_OUTPUT.read_text(encoding="utf-8")
    newline = chr(10)
    if displayed_output.rstrip(newline) != actual_output.rstrip(newline):
        print(
            "The website check_versions example is stale. Regenerate the "
            "package-backed evidence, review the output, and update the snippet.",
            file=sys.stderr,
        )
        print("--- website example ---", file=sys.stderr)
        print(displayed_output, file=sys.stderr)
        print("--- current package output ---", file=sys.stderr)
        print(actual_output, file=sys.stderr)
        return 1

    print("Website check_versions example matches the current package output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
