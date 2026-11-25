#!/usr/bin/env python3
"""Validate Conventional Commit messages and squash-merge pull-request titles.

The subject format is intentionally strict and deterministic. Imperative mood is
a writing convention documented for human review; it is not guessed with regex.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MAX_SUBJECT_LENGTH = 100
ALLOWED_TYPES = frozenset(
    {"feat", "fix", "docs", "test", "refactor", "perf", "build", "ci", "chore", "revert"}
)
HEADER = re.compile(
    r"^(?P<type>[a-z][a-z0-9-]*)"
    r"(?:\((?P<scope>[a-z0-9]+(?:[./-][a-z0-9]+)*)\))?"
    r"(?P<breaking>!)?: (?P<subject>.+)$"
)
BREAKING_FOOTER = "BREAKING CHANGE:"


def validate_commit_message(message: str) -> list[str]:
    """Return actionable validation errors for a Conventional Commit message."""
    lines = message.splitlines()
    if not lines:
        return ["commit message is empty"]

    subject = lines[0]
    if not subject.strip():
        return ["commit subject must be the first line"]

    errors: list[str] = []
    if len(subject) > MAX_SUBJECT_LENGTH:
        errors.append(
            f"subject is {len(subject)} characters; maximum is {MAX_SUBJECT_LENGTH}"
        )

    match = HEADER.fullmatch(subject)
    if match is None:
        errors.append(
            "subject must match 'type(scope): lowercase imperative summary'; "
            "scope and the breaking '!' marker are optional"
        )
    else:
        commit_type = match.group("type")
        if commit_type not in ALLOWED_TYPES:
            allowed = ", ".join(sorted(ALLOWED_TYPES))
            errors.append(f"unknown commit type '{commit_type}'; allowed types: {allowed}")

        summary = match.group("subject")
        if summary != summary.strip():
            errors.append("summary must not have leading or trailing whitespace")
        if not re.match(r"^[a-z0-9]", summary):
            errors.append("summary must start with a lowercase letter or digit")
        if summary != summary.lower():
            errors.append("summary must use lowercase letters throughout")
        if summary.endswith("."):
            errors.append("subject must not end with a period")

    footer_indexes = [
        index for index, line in enumerate(lines[1:], start=1)
        if line.startswith(BREAKING_FOOTER)
    ]
    for index in footer_indexes:
        description = lines[index][len(BREAKING_FOOTER):].strip()
        if not description:
            errors.append("BREAKING CHANGE footer must include a non-empty description")
        if index < 2 or lines[index - 1].strip():
            errors.append("BREAKING CHANGE footer must be separated from the body by a blank line")

    return errors


def validate_commit_subjects(subjects: list[str]) -> list[str]:
    """Validate every subject returned for a pull request's commits."""
    if not subjects:
        return ["pull request contains no commits to validate"]

    errors: list[str] = []
    for index, subject in enumerate(subjects, start=1):
        errors.extend(
            f"commit {index}: {error}" for error in validate_commit_message(subject)
        )
    return errors


def _report_errors(errors: list[str]) -> int:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    print("Example: feat(router): support nested route prefixes", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--message", help="commit message text")
    source.add_argument(
        "--subjects-file",
        type=Path,
        help="file containing one commit subject per line",
    )
    source.add_argument("message_file", nargs="?", type=Path)
    args = parser.parse_args()

    try:
        if args.subjects_file is not None:
            subjects = args.subjects_file.read_text(encoding="utf-8").splitlines()
            errors = validate_commit_subjects(subjects)
            if errors:
                return _report_errors(errors)
            print("All commit subjects are valid.")
            return 0

        message = (
            args.message
            if args.message is not None
            else args.message_file.read_text(encoding="utf-8")
        )
    except OSError as exc:
        print(f"ERROR: cannot read commit message: {exc}", file=sys.stderr)
        return 2

    errors = validate_commit_message(message)
    if errors:
        return _report_errors(errors)

    print("Commit subject is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
