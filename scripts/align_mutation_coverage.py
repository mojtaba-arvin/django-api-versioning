#!/usr/bin/env python3
"""Repair Mutmut's one-line AST-location offset in coverage-based test selection.

Mutmut 2.5.1 can store a mutation's enclosing AST line in its cache, while the
changed statement is the following physical source line. This mismatch can
leave mutants untested even though tests execute and assert the changed
statement. Copy missing per-test contexts from N+1 to N for unresolved mutants.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from coverage import CoverageData


def load_survivor_locations(cache_path: Path) -> list[tuple[str, int]]:
    """Load surviving and previously untested mutant locations."""
    if not cache_path.is_file():
        return []
    connection = sqlite3.connect(cache_path)
    try:
        rows = connection.execute("""
            SELECT DISTINCT source.filename, line.line_number
            FROM Mutant AS mutant
            JOIN Line AS line ON line.id = mutant.line
            JOIN SourceFile AS source ON source.id = line.sourcefile
            WHERE lower(mutant.status) LIKE '%survived%'
               OR lower(mutant.status) IN ('not_checked', 'not_run', 'skipped')
            ORDER BY source.filename, line.line_number
            """).fetchall()
    finally:
        connection.close()
    return [(str(filename), int(line_number)) for filename, line_number in rows]


def prepare_survivors_for_rerun(cache_path: Path) -> list[tuple[str, int]]:
    """Reset surviving mutants and retain unresolved mutants for context alignment."""
    locations = load_survivor_locations(cache_path)
    if not cache_path.is_file():
        return locations
    connection = sqlite3.connect(cache_path)
    try:
        connection.execute(
            "UPDATE Mutant SET status = 'not_checked', tested_against_hash = '' "
            "WHERE lower(status) LIKE '%survived%' "
            "OR lower(status) IN ('not_checked', 'not_run', 'skipped')"
        )
        connection.commit()
    finally:
        connection.close()
    return locations


def align_survivor_contexts(
    coverage_data: CoverageData,
    locations: list[tuple[str, int]],
) -> tuple[int, int]:
    """Merge N+1 test contexts into N for unresolved mutant locations.

    The cache may have contexts at N from other statements in the same AST
    node. Those contexts are not evidence that tests cover the changed
    statement on N+1, so merge the following line's contexts rather than
    skipping alignment whenever N already has any contexts.
    """
    aligned_lines = 0
    aligned_contexts = 0
    measured = sorted(coverage_data.measured_files())

    for source_filename, line_number in locations:
        suffix = "/" + source_filename.replace("\\", "/")
        matches = [
            path for path in measured if path.replace("\\", "/").endswith(suffix)
        ]
        if len(matches) != 1:
            continue

        filename = matches[0]
        contexts_by_line = coverage_data.contexts_by_lineno(filename)
        existing_contexts = set(contexts_by_line.get(line_number, ()))
        following_contexts = sorted(
            {
                context
                for offset in range(1, 7)
                for context in contexts_by_line.get(line_number + offset, ())
                if context and context not in existing_contexts
            }
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
    parser.add_argument("--cache", type=Path, default=Path(".mutmut-cache"))
    args = parser.parse_args()

    if not args.coverage.is_file():
        raise SystemExit(f"Coverage data file does not exist: {args.coverage}")

    coverage_data = CoverageData(basename=str(args.coverage))
    coverage_data.read()
    locations = prepare_survivors_for_rerun(args.cache)
    aligned_lines, aligned_contexts = align_survivor_contexts(coverage_data, locations)
    coverage_data.write()
    print(
        "Aligned per-test coverage contexts for "
        f"{aligned_lines}/{len(locations)} unresolved-mutant locations "
        f"({aligned_contexts} additional test contexts)."
    )


if __name__ == "__main__":
    main()
