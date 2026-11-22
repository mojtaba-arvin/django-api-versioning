"""Regression tests for conservative Mutmut test selection."""

import shlex
from pathlib import Path
from types import SimpleNamespace

import mutmut_config


def _context(filename, coverage_data, line_index=17):
    return SimpleNamespace(
        filename=str(filename),
        current_line_index=line_index,
        config=SimpleNamespace(
            coverage_data=coverage_data,
            test_command="pytest",
        ),
    )


def test_pull_request_selection_runs_every_test_context_for_the_mutated_line(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    source = tmp_path / "decorators.py"
    node_a = "tests/test_decorators.py::test_first"
    node_b = "tests/test_decorators_survivor_contracts.py::test_second"
    coverage = {
        str(source): {
            17: [
                f"{node_b}|run",
                f"{node_a}|run",
                f"{node_a}|teardown",
            ]
        }
    }
    context = _context(source, coverage)

    mutmut_config.pre_mutation(context)

    command_args = shlex.split(context.config.test_command)
    assert command_args[-2:] == [node_a, node_b]
    assert command_args.count(node_a) == 1


def test_decorator_mutations_without_line_context_fall_back_to_all_package_tests(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    source = tmp_path / "decorators.py"
    context = _context(source, {})

    mutmut_config.pre_mutation(context)

    command_args = shlex.split(context.config.test_command)
    selected = set(command_args[command_args.index("addopts=") + 1 :])
    expected = set(mutmut_config.ALL_TEST_MODULES)
    assert expected
    assert expected <= selected


def test_decorator_fallback_includes_survivor_contract_and_registry_tests():
    selected = set(mutmut_config.TESTS_BY_SOURCE["decorators.py"])
    assert "tests/test_decorators_survivor_contracts.py" in selected
    assert "tests/test_decorators_mutation_contracts.py" in selected
    assert "tests/test_registry_router_ownership.py" in selected


def test_init_rejects_missing_fallback_test_modules(monkeypatch):
    monkeypatch.setattr(
        mutmut_config,
        "TESTS_BY_SOURCE",
        {"decorators.py": ("tests/does-not-exist.py",)},
    )

    try:
        mutmut_config.init()
    except RuntimeError as error:
        assert "does-not-exist.py" in str(error)
    else:
        raise AssertionError("Missing fallback tests must fail initialization")
