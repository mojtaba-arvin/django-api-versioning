#!/usr/bin/env python3
"""Validate commit subjects and squash-merge pull-request titles."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MAX_SUBJECT_LENGTH = 100
HEADER = re.compile(
    r"^(?P<type>[a-z][a-z0-9-]*)"
    r"(?:\((?P<scope>[a-z0-9]+(?:[./-][a-z0-9]+)*)\))?"
    r"(?P<breaking>!)?: (?P<subject>.+)$"
)


def validate_commit_message(message: str) -> list[str]:
    """Return actionable validation errors for a Conventional Commit message."""
    errors: list[str] = []
    lines = message.splitlines()
    if not lines:
        return ["commit message is empty"]

    subject = lines[0]
    if not subject.strip():
        return ["commit subject must be the first line"]

    if len(subject) > MAX_SUBJECT_LENGTH:
        errors.append(
            f"subject is {len(subject)} characters; maximum is {MAX_SUBJECT_LENGTH}"
        )

    match = HEADER.fullmatch(subject)
    if match is None:
        errors.append(
            "subject must match Conventional Commits: "
            "'type(scope): lowercase imperative summary' (scope is optional)"
        )
        return errors

    summary = match.group("subject")
    if summary.endswith("."):
        errors.append("subject must not end with a period")
    if not re.match(r"^[a-z0-9]", summary):
        errors.append("summary must start with a lowercase letter or digit")
    if summary != summary.strip():
        errors.append("summary must not have leading or trailing whitespace")

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--message", help="commit subject/message text")
    source.add_argument(
        "--subjects-file",
        type=Path,
        help="file containing one commit subject per line",
    )
    source.add_argument("message_file", nargs="?", type=Path)
    args = parser.parse_args()

    try:
        if args.subjects_file is not None:
            errors = validate_commit_subjects(
                args.subjects_file.read_text(encoding="utf-8").splitlines()
            )
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                print(
                    "Example: feat(router): support nested route prefixes",
                    file=sys.stderr,
                )
                return 1
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
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            "Example: feat(router): support nested route prefixes",
            file=sys.stderr,
        )
        return 1

    print("Commit subject is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
