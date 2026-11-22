"""Line-level test selection for mutmut, with a full-suite safety net.

Pytest-cov contexts identify every test node ID that executed a mutated line.
All recorded contexts are run: selecting an arbitrary first test can produce
false survivors because line coverage does not identify which assertion checks
the mutated behavior. Import-time and otherwise uncontextualized mutations use
the complete package test suite as a conservative fallback.
"""

import os
import shlex
from pathlib import Path

ALL_TEST_MODULES = tuple(
    path.as_posix() for path in sorted(Path("tests").glob("test_*.py"))
)

TESTS_BY_SOURCE = {
    "decorators.py": ALL_TEST_MODULES,
    "lifecycle.py": (
        "tests/test_lifecycle.py",
        "tests/test_lifecycle_ascii_version.py",
        "tests/test_lifecycle_integration.py",
        "tests/test_lifecycle_route_identity.py",
        "tests/test_management_commands.py",
        "tests/test_adversarial_router_combinations.py",
        "tests/test_mutation_survivor_contracts.py",
    ),
    "negotiation.py": (
        "tests/test_negotiation_middleware.py",
        "tests/test_negotiation_properties.py",
        "tests/test_adversarial_router_combinations.py",
        "tests/test_mutation_survivor_contracts.py",
    ),
    "registry.py": (
        "tests/test_registry.py",
        "tests/test_registry_router_ownership.py",
        "tests/test_segment_model.py",
        "tests/test_route_removal.py",
        "tests/test_adversarial_router_combinations.py",
        "tests/test_mutation_survivor_contracts.py",
    ),
    "routers.py": (
        "tests/test_routers.py",
        "tests/test_default_routers.py",
        "tests/test_registry_router_ownership.py",
        "tests/test_lifecycle_integration.py",
        "tests/test_reverse.py",
        "tests/test_urls.py",
        "tests/test_route_removal.py",
        "tests/test_adversarial_router_combinations.py",
        "tests/test_mutation_survivor_contracts.py",
    ),
}


def init():
    """Fail early if a mapped test module is missing."""
    missing = [
        test_path
        for test_paths in TESTS_BY_SOURCE.values()
        for test_path in test_paths
        if not Path(test_path).is_file()
    ]
    if missing:
        raise RuntimeError(f"mutmut test selection references missing files: {missing}")


def pre_mutation(context):
    """Run every test covering this line; fall back to conservative test modules."""
    source_name = Path(context.filename).name
    coverage_data = context.config.coverage_data or {}
    source_path = os.path.abspath(context.filename)
    contexts_by_line = coverage_data.get(source_path, {})
    # Mutmut's Context.current_line_index is zero-based; Coverage.py uses 1-based lines.
    line_contexts = contexts_by_line.get(context.current_line_index + 1, [])

    node_ids = sorted(
        {
            context_name.split("|", 1)[0]
            for context_name in line_contexts
            if context_name
        }
    )
    if node_ids:
        context.config.test_command = (
            "python -m pytest -x -q -p no:pytest_cov -o addopts= "
            + " ".join(shlex.quote(node_id) for node_id in node_ids)
        )
        return

    test_paths = TESTS_BY_SOURCE.get(source_name)
    if not test_paths:
        return
    context.config.test_command = (
        "python -m pytest -x -q -p no:pytest_cov -o addopts= " + " ".join(test_paths)
    )
