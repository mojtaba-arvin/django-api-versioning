"""Regression tests for Mutmut's zero-based coverage-context selection."""

import os
import shlex
from types import SimpleNamespace

import pytest

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
    source_path = tmp_path / "registration.py"
    node_id = "tests/test_registry.py::test_selected_for_actual_line"
    context = _context(
        source_path,
        42,
        {os.path.abspath(source_path): {43: [node_id + "|run"]}},
    )

    pre_mutation(context)

    selected_node_ids = set(shlex.split(context.config.test_command))
    assert node_id in selected_node_ids
    assert set(_contract_test_node_ids("registration.py")) <= selected_node_ids


def test_pre_mutation_does_not_select_a_test_from_the_previous_line(tmp_path):
    source_path = tmp_path / "__init__.py"
    wrong_node_id = "tests/test_registry.py::test_previous_line_only"
    context = _context(
        source_path,
        42,
        {os.path.abspath(source_path): {42: [wrong_node_id + "|run"]}},
    )

    pre_mutation(context)

    assert wrong_node_id not in context.config.test_command
    assert "tests/test_mutation_survivor_contracts.py" in context.config.test_command


def test_pre_mutation_fallback_includes_survivor_contracts_for_every_domain(
    tmp_path,
):
    for source_name in (
        "decorators.py",
        "lifecycle.py",
        "negotiation.py",
        "__init__.py",
        "registration.py",
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


@pytest.mark.parametrize(
    "source_name",
    [
        "decorators.py",
        "lifecycle.py",
        "negotiation.py",
        "__init__.py",
        "registration.py",
        "routers.py",
    ],
)
def test_pre_mutation_uses_domain_fallback_for_excessive_contexts(
    tmp_path, source_name
):
    source_path = tmp_path / source_name
    broad_contexts = [
        f"tests/test_unrelated.py::test_context_{index}|run" for index in range(501)
    ]
    context = _context(
        source_path,
        0,
        {os.path.abspath(source_path): {1: broad_contexts}},
    )

    pre_mutation(context)

    selected = set(shlex.split(context.config.test_command))
    assert "tests/test_mutation_survivor_contracts.py" in selected
    assert "tests/test_unrelated.py::test_context_0" not in selected
    assert "tests/test_unrelated.py::test_context_500" not in selected


def test_pre_mutation_fallback_does_not_duplicate_contract_module(tmp_path):
    source_path = tmp_path / "registration.py"
    context = _context(source_path, 0, {os.path.abspath(source_path): {}})

    pre_mutation(context)

    selected = shlex.split(context.config.test_command)
    assert selected.count("tests/test_mutation_survivor_contracts.py") == 1
    assert not any("::test_mutation" in item for item in selected)


@pytest.mark.parametrize(
    "source_name",
    [
        "decorators.py",
        "lifecycle.py",
        "negotiation.py",
        "__init__.py",
        "registration.py",
        "routers.py",
    ],
)
def test_pre_mutation_selects_its_domain_contract_probes_for_covered_lines(
    tmp_path, source_name
):
    source_path = tmp_path / source_name
    context = _context(
        source_path,
        42,
        {
            os.path.abspath(source_path): {
                43: ["tests/test_probe.py::test_line_context|run"]
            }
        },
    )
    expected = set(_contract_test_node_ids(source_name))

    pre_mutation(context)

    selected = set(shlex.split(context.config.test_command))
    assert expected <= selected
    assert "tests/test_probe.py::test_line_context" in selected
