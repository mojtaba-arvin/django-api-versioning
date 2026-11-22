#!/usr/bin/env python3
"""Export exact Mutmut outcomes and surviving-mutant evidence from its cache."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from coverage import CoverageData


def status_bucket(status: str) -> str:
    value = status.lower()
    if "killed" in value:
        return "killed"
    if "survived" in value:
        return "survived"
    if "timeout" in value:
        return "timed_out"
    if "suspicious" in value:
        return "suspicious"
    if "skipped" in value or value in {"not_checked", "not_run"}:
        return "skipped"
    return "unknown"


def summarize_statuses(statuses: list[str]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    unknown: Counter[str] = Counter()
    for status in statuses:
        bucket = status_bucket(status)
        if bucket == "unknown":
            unknown[status] += 1
        else:
            counts[bucket] += 1
    if unknown:
        raise ValueError(f"Unrecognized Mutmut cache statuses: {dict(unknown)}")
    total = len(statuses)
    completed = sum(counts.values())
    return {
        "completed": completed,
        "total": total,
        "killed": counts["killed"],
        "survived": counts["survived"],
        "timed_out": counts["timed_out"],
        "suspicious": counts["suspicious"],
        "skipped": counts["skipped"],
    }


def parse_survivor_count(results_text: str) -> int | None:
    match = re.search(r"(?m)^Survived 🙁 \((\d+)\)$", results_text)
    return int(match.group(1)) if match else None


def parse_progress_summary(run_log: str) -> dict[str, int] | None:
    matches = re.findall(
        r"(\d+)/(\d+)\s+🎉\s+(\d+)\s+⏰\s+(\d+)\s+🤔\s+(\d+)\s+🙁\s+(\d+)\s+🔇\s+(\d+)",
        run_log,
    )
    if not matches:
        return None
    completed, total, killed, timed_out, suspicious, survived, skipped = map(
        int, matches[-1]
    )
    return {
        "completed": completed,
        "total": total,
        "killed": killed,
        "timed_out": timed_out,
        "suspicious": suspicious,
        "survived": survived,
        "skipped": skipped,
    }


def load_mutants(cache_path: Path) -> list[dict[str, Any]]:
    connection = sqlite3.connect(cache_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute("""
            SELECT
                mutant.id AS mutant_id,
                mutant."index" AS mutation_index,
                mutant.status AS status,
                source.filename AS filename,
                line.line_number AS line_number,
                line.line AS source_line
            FROM Mutant AS mutant
            JOIN Line AS line ON line.id = mutant.line
            JOIN SourceFile AS source ON source.id = line.sourcefile
            ORDER BY source.filename, line.line_number, mutant.id
            """).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def executing_tests(
    coverage_data: CoverageData, filename: str, line_number: int
) -> list[str]:
    suffix = "/" + filename.replace("\\", "/")
    matches = [
        path
        for path in coverage_data.measured_files()
        if path.replace("\\", "/").endswith(suffix)
    ]
    if len(matches) != 1:
        return []
    contexts = coverage_data.contexts_by_lineno(matches[0]).get(line_number, [])
    tests = set()
    for context in contexts:
        if not context:
            continue
        if context.endswith("|run"):
            tests.add(context[:-4])
        elif not context.endswith(("|setup", "|teardown")):
            tests.add(context)
    return sorted(tests)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--run-log", type=Path, required=True)
    parser.add_argument("--runner-exit", type=int, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args()

    mutants = load_mutants(args.cache)
    summary = summarize_statuses([item["status"] for item in mutants])
    if summary["total"] == 0 or summary["completed"] != summary["total"]:
        raise SystemExit("Mutmut cache is incomplete or contains no generated mutants")

    results_text = args.results.read_text(encoding="utf-8", errors="replace")
    reported_survivors = parse_survivor_count(results_text)
    if reported_survivors is None:
        if summary["survived"] != 0:
            raise SystemExit("mutmut results did not report the cache survivor count")
    elif reported_survivors != summary["survived"]:
        raise SystemExit(
            "Mutmut results/cache disagreement: "
            f"results={reported_survivors}, cache={summary['survived']}"
        )

    if args.runner_exit not in {0, 2}:
        raise SystemExit(f"Unexpected mutmut runner exit code: {args.runner_exit}")
    if args.runner_exit == 2 and summary["survived"] == 0:
        raise SystemExit(
            "mutmut returned survivor exit code 2 but cache has no survivors"
        )

    progress = parse_progress_summary(
        args.run_log.read_text(encoding="utf-8", errors="replace")
    )
    summary.update(
        {
            "target": args.target,
            "runner_exit": args.runner_exit,
            "progress_summary": progress,
            "progress_disagrees_with_cache": (
                progress is not None
                and any(
                    progress[key] != summary[key]
                    for key in (
                        "completed",
                        "total",
                        "killed",
                        "timed_out",
                        "suspicious",
                        "survived",
                        "skipped",
                    )
                )
            ),
        }
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    survivors = [
        item for item in mutants if status_bucket(item["status"]) == "survived"
    ]
    if args.details:
        coverage_data = CoverageData(basename=str(args.coverage))
        coverage_data.read()
        with args.report.open("w", encoding="utf-8") as report_file:
            for mutant in survivors:
                shown = subprocess.run(
                    ["mutmut", "show", str(mutant["mutant_id"])],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                record = {
                    "target": args.target,
                    "mutant_id": mutant["mutant_id"],
                    "mutation_index": mutant["mutation_index"],
                    "source_location": (
                        f"{mutant['filename']}:{mutant['line_number']}"
                    ),
                    "source_line": mutant["source_line"],
                    "mutation_type": "review mutation_diff",
                    "mutation_diff": shown.stdout,
                    "mutation_diff_error": shown.stderr if shown.returncode else None,
                    "executing_tests": executing_tests(
                        coverage_data, mutant["filename"], mutant["line_number"]
                    ),
                    "classification": "unclassified",
                }
                report_file.write(json.dumps(record, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
