"""Tests for mutation report cache/progress reconciliation."""

from scripts.export_mutation_report import progress_disagrees_with_cache


def _summary():
    return {
        "completed": 10,
        "total": 10,
        "killed": 8,
        "timed_out": 0,
        "suspicious": 0,
        "survived": 2,
        "skipped": 0,
    }


def test_progress_summary_matching_cache_is_accepted():
    summary = _summary()

    assert progress_disagrees_with_cache(dict(summary), summary) is False


def test_progress_summary_with_different_mutant_outcome_is_rejected():
    summary = _summary()
    progress = dict(summary, killed=9, survived=1)

    assert progress_disagrees_with_cache(progress, summary) is True


def test_missing_progress_summary_is_not_misreported_as_a_disagreement():
    assert progress_disagrees_with_cache(None, _summary()) is False
