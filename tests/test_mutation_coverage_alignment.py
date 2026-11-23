"""Regression tests for Mutmut's zero-based coverage-context selection."""

import os
import shlex
from types import SimpleNamespace

from mutmut_config import _contract_test_node_ids, pre_mutation


def _context(source_path, current_line_index, coverage_data):
    config = SimpleNamespace(
        coverage_data=coverage_data,
        test_command="python -m pytest",
    )
    return SimpleNamespace(
        filename=str(source_path),
        current_line_index=current_line_index,
        config=config,
    )


def test_pre_mutation_reads_the_one_based_coverage_line(tmp_path):
    source_path = tmp_path / "registry.py"
    node_id = "tests/test_registry.py::test_selected_for_actual_line"
    context = _context(
        source_path,
        42,
        {os.path.abspath(source_path): {43: [node_id + "|run"]}},
    )

    pre_mutation(context)

    selected_node_ids = set(shlex.split(context.config.test_command))
    assert node_id in selected_node_ids
    assert set(_contract_test_node_ids("registry.py")) <= selected_node_ids


def test_pre_mutation_does_not_select_a_test_from_the_previous_line(tmp_path):
    source_path = tmp_path / "registry.py"
    wrong_node_id = "tests/test_registry.py::test_previous_line_only"
    context = _context(
        source_path,
        42,
        {os.path.abspath(source_path): {42: [wrong_node_id + "|run"]}},
    )

    pre_mutation(context)

    assert wrong_node_id not in context.config.test_command
    assert "tests/test_mutation_survivor_contracts.py" in (
        context.config.test_command
    )


def test_pre_mutation_fallback_includes_survivor_contracts_for_every_domain(
    tmp_path,
):
    for source_name in (
        "decorators.py",
        "lifecycle.py",
        "negotiation.py",
        "registry.py",
        "routers.py",
    ):
        source_path = tmp_path / source_name
        context = _context(
            source_path,
            0,
            {os.path.abspath(source_path): {}},
        )

        pre_mutation(context)

        assert "tests/test_mutation_survivor_contracts.py" in (
            context.config.test_command
        )


def test_pre_mutation_runs_every_context_recorded_for_the_mutated_line(tmp_path):
    source_path = tmp_path / "negotiation.py"
    node_ids = (
        "tests/test_negotiation_middleware.py::test_query_version",
        "tests/test_mutation_survivor_contracts.py::test_header_conflict",
    )
    context = _context(
        source_path,
        17,
        {
            os.path.abspath(source_path): {
                18: [node_id + "|run" for node_id in node_ids]
            }
        },
    )

    pre_mutation(context)

    for node_id in node_ids:
        assert node_id in context.config.test_command
