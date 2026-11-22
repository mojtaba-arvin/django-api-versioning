"""Tests for the machine-readable Mutmut report exporter."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location(
    "export_mutation_report", ROOT / "scripts" / "export_mutation_report.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

parse_survivor_count = MODULE.parse_survivor_count
summarize_statuses = MODULE.summarize_statuses


def test_summarize_statuses_uses_cache_outcomes():
    summary = summarize_statuses(
        [
            "ok_killed",
            "bad_survived",
            "bad_timeout",
            "bad_suspicious",
            "not_checked",
        ]
    )

    assert summary == {
        "completed": 5,
        "total": 5,
        "killed": 1,
        "survived": 1,
        "timed_out": 1,
        "suspicious": 1,
        "skipped": 1,
    }


def test_summarize_statuses_rejects_unknown_outcomes():
    try:
        summarize_statuses(["future_mutmut_status"])
    except ValueError as error:
        assert "Unrecognized Mutmut cache statuses" in str(error)
    else:
        raise AssertionError("Unknown Mutmut statuses must not be silently ignored")


def test_parse_survivor_count_reads_mutmut_results():
    assert parse_survivor_count("Survived 🙁 (344)\n") == 344


def test_parse_survivor_count_returns_none_when_no_survivors_line():
    assert parse_survivor_count("No surviving mutants.\n") is None
