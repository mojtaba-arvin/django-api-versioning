#!/usr/bin/env python3
"""Repair Mutmut's one-line AST-location offset in coverage-based test selection.

Mutmut 2.5.1 can store a mutation's enclosing AST line in its cache, while the
changed statement is the following physical source line. With --use-coverage,
that mismatch can leave a mutant with no selected tests even though tests
execute and assert the changed statement. Copy only the missing per-test
contexts from N+1 to N for the five mutation targets; never discard contexts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from coverage import CoverageData

TARGET_SUFFIXES = (
    "/django_api_versioning/decorators.py",
    "/django_api_versioning/lifecycle.py",
    "/django_api_versioning/negotiation.py",
    "/django_api_versioning/registry.py",
    "/django_api_versioning/routers.py",
)


def align_adjacent_contexts(
    coverage_data: CoverageData,
    target_suffixes: tuple[str, ...] = TARGET_SUFFIXES,
) -> tuple[int, int]:
    """Copy N+1's test contexts to N only when N has no test context.

    Returns (number of aligned source lines, number of copied test contexts).
    """
    aligned_lines = 0
    aligned_contexts = 0

    for filename in sorted(coverage_data.measured_files()):
        normalized = filename.replace("\\", "/")
        if not any(normalized.endswith(suffix) for suffix in target_suffixes):
            continue

        contexts_by_line = coverage_data.contexts_by_lineno(filename)
        for line_number, contexts in sorted(contexts_by_line.items()):
            if any(context for context in contexts):
                continue

            following_contexts = sorted(
                {context for context in contexts_by_line.get(line_number + 1, ()) if context}
            )
            if not following_contexts:
                continue

            for context in following_contexts:
                coverage_data.set_context(context)
                coverage_data.add_lines({filename: {line_number}})
                aligned_contexts += 1
            aligned_lines += 1

    return aligned_lines, aligned_contexts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", type=Path, default=Path(".coverage"))
    args = parser.parse_args()

    if not args.coverage.is_file():
        raise SystemExit(f"Coverage data file does not exist: {args.coverage}")

    coverage_data = CoverageData(basename=str(args.coverage))
    coverage_data.read()
    aligned_lines, aligned_contexts = align_adjacent_contexts(coverage_data)
    coverage_data.write()
    print(
        "Aligned per-test coverage contexts for "
        f"{aligned_lines} mutation locations ({aligned_contexts} test contexts)."
    )


if __name__ == "__main__":
    main()
