"""Enforce separate line and branch coverage thresholds from coverage.py JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def coverage_percentages(totals: dict[str, Any]) -> tuple[float, float]:
    """Return statement and branch coverage, rejecting missing denominators."""
    statements = int(totals["num_statements"])
    lines_covered = int(totals["covered_lines"])
    branches = int(totals.get("num_branches", 0))
    branches_covered = int(totals.get("covered_branches", 0))

    if statements <= 0:
        raise ValueError("Coverage report contains no executable statements.")
    if branches <= 0:
        raise ValueError("Coverage report contains no branch opportunities.")

    line_percent = 100.0 * lines_covered / statements
    branch_percent = 100.0 * branches_covered / branches
    return line_percent, branch_percent


def verify_thresholds(
    totals: dict[str, Any],
    *,
    line_threshold: float,
    branch_threshold: float,
) -> tuple[float, float]:
    """Validate independent statement and branch coverage minimums."""
    line_percent, branch_percent = coverage_percentages(totals)
    failures = []
    if line_percent < line_threshold:
        failures.append(
            f"line coverage {line_percent:.2f}% is below {line_threshold:.2f}%"
        )
    if branch_percent < branch_threshold:
        failures.append(
            f"branch coverage {branch_percent:.2f}% is below {branch_threshold:.2f}%"
        )
    if failures:
        raise ValueError("; ".join(failures))
    return line_percent, branch_percent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="coverage.py JSON report")
    parser.add_argument("--line-threshold", type=float, default=95.0)
    parser.add_argument("--branch-threshold", type=float, default=95.0)
    args = parser.parse_args()

    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        line_percent, branch_percent = verify_thresholds(
            report["totals"],
            line_threshold=args.line_threshold,
            branch_threshold=args.branch_threshold,
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        parser.exit(1, f"Coverage threshold check failed: {error}\n")

    print(f"Line coverage:   {line_percent:.2f}% (minimum {args.line_threshold:.2f}%)")
    print(
        f"Branch coverage: {branch_percent:.2f}% "
        f"(minimum {args.branch_threshold:.2f}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
