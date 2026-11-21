"""Fail closed when a mutmut run is incomplete or below its score floor."""
from __future__ import annotations

import json
import sys
from pathlib import Path

STATS = Path("mutants/mutmut-cicd-stats.json")
MINIMUM_SCORE = 70.0


def main() -> int:
    if not STATS.is_file():
        print(f"Missing mutmut report: {STATS}", file=sys.stderr)
        return 2
    try:
        data = json.loads(STATS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read mutmut report: {exc}", file=sys.stderr)
        return 2

    required = ("total", "killed", "survived", "skipped")
    if not isinstance(data, dict) or any(
        not isinstance(data.get(key), int) for key in required
    ):
        print(f"Malformed mutmut report: {data!r}", file=sys.stderr)
        return 2

    total, killed = data["total"], data["killed"]
    survived, skipped = data["survived"], data["skipped"]
    typed = data.get("caught_by_type_check", 0)
    unresolved = {
        key: data.get(key, 0) for key in ("no_tests", "suspicious", "timeout")
    }
    denominator = total - skipped - typed
    if total <= 0 or denominator <= 0 or killed + survived > denominator:
        print(f"Invalid or empty mutation population: {data!r}", file=sys.stderr)
        return 2

    score = 100.0 * killed / denominator
    print(
        f"Mutation score: {score:.2f}% ({killed} killed / {survived} survived; "
        f"{total} total, {skipped} skipped, {typed} type-checked)."
    )
    print("Unresolved mutant states: " + json.dumps(unresolved, sort_keys=True))

    failures = []
    if score < MINIMUM_SCORE:
        failures.append(f"score below {MINIMUM_SCORE:.1f}%")
    failures.extend(f"{key}={value}" for key, value in unresolved.items() if value)
    if failures:
        print("Mutation gate failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
