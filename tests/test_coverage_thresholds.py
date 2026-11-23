"""Tests for independent statement and branch coverage thresholds."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location(
    "check_coverage_thresholds", ROOT / "scripts" / "check_coverage_thresholds.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _totals(
    *,
    statements=100,
    covered_lines=95,
    branches=100,
    covered_branches=95,
):
    return {
        "num_statements": statements,
        "covered_lines": covered_lines,
        "num_branches": branches,
        "covered_branches": covered_branches,
    }


def test_coverage_thresholds_accept_exact_independent_minimums():
    assert MODULE.verify_thresholds(
        _totals(), line_threshold=95, branch_threshold=95
    ) == (95.0, 95.0)


def test_coverage_thresholds_reject_line_coverage_below_minimum():
    with pytest.raises(ValueError, match="line coverage 94.00%"):
        MODULE.verify_thresholds(
            _totals(covered_lines=94), line_threshold=95, branch_threshold=95
        )


def test_coverage_thresholds_reject_branch_coverage_below_minimum():
    with pytest.raises(ValueError, match="branch coverage 94.00%"):
        MODULE.verify_thresholds(
            _totals(covered_branches=94), line_threshold=95, branch_threshold=95
        )


def test_coverage_thresholds_reject_report_without_branch_data():
    with pytest.raises(ValueError, match="no branch opportunities"):
        MODULE.verify_thresholds(
            _totals(branches=0, covered_branches=0),
            line_threshold=95,
            branch_threshold=95,
        )
