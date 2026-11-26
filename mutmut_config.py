"""Context-aware Mutmut selection plus focused domain contract probes.

Pytest-cov contexts identify tests that executed a mutated line. Those tests
are combined with every contract test for the mutated domain, so a survivor is
always checked against the focused regression suite even when coverage contexts
are broad or a test body changed without changing its node ID. Import-time and
otherwise uncontextualized mutations retain the complete-suite fallback.
"""

import os
import shlex
from pathlib import Path

ALL_TEST_MODULES = tuple(
    path.as_posix() for path in sorted(Path("tests").glob("test_*.py"))
)

CONTRACT_TEST_PREFIXES = {
    "decorators.py": ("test_mutation95_decorator", "test_mutation100_decorator"),
    "lifecycle.py": ("test_mutation95_lifecycle", "test_mutation100_lifecycle"),
    "negotiation.py": ("test_mutation95_negotiation", "test_mutation100_negotiation"),
    "__init__.py": ("test_mutation95_registry", "test_mutation100_registry"),
    "registry/lifecycle.py": ("test_registry_lifecycle_store",),
    "registry/matrix.py": ("test_registry_matrix_",),
    "registration.py": ("test_mutation95_registry", "test_mutation100_registry"),
    "removal.py": ("test_mutation95_registry", "test_mutation100_registry"),
    "routers.py": ("test_mutation95_router", "test_mutation100_router"),
}

CONTRACT_TEST_MODULE = "tests/test_mutation_survivor_contracts.py"
CONTRACT_TEST_MODULES = {
    "registry/lifecycle.py": "tests/test_registry_lifecycle_component.py",
    "registry/matrix.py": "tests/test_registry_matrix.py",
}
MAX_LINE_CONTEXTS = 500

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
        "tests/test_mutation_80_percent_contracts.py",
    ),
    "negotiation.py": (
        "tests/test_negotiation_middleware.py",
        "tests/test_negotiation_properties.py",
        "tests/test_adversarial_router_combinations.py",
        "tests/test_mutation_80_percent_contracts.py",
        "tests/test_mutation_survivor_contracts.py",
    ),
    "registry/lifecycle.py": (
        "tests/test_registry_lifecycle_component.py",
        "tests/test_registry.py",
        "tests/test_mutation_survivor_contracts.py",
    ),
    "registry/matrix.py": ("tests/test_registry_matrix.py",),
    "__init__.py": (
        "tests/test_registry.py",
        "tests/test_registry_lifecycle_component.py",
        "tests/test_registry_router_ownership.py",
        "tests/test_segment_model.py",
        "tests/test_route_removal.py",
        "tests/test_adversarial_router_combinations.py",
        "tests/test_decorators.py",
        "tests/test_lifecycle.py",
        "tests/test_lifecycle_integration.py",
        "tests/test_management_commands.py",
        "tests/test_negotiation_middleware.py",
        "tests/test_routers.py",
        "tests/test_settings.py",
        "tests/test_registry_mutation_contracts.py",
        "tests/test_mutation_80_percent_contracts.py",
        "tests/test_mutation_survivor_contracts.py",
    ),
    "registration.py": (
        "tests/test_registration_component.py",
        "tests/test_registry.py",
        "tests/test_registry_router_ownership.py",
        "tests/test_segment_model.py",
        "tests/test_route_removal.py",
        "tests/test_adversarial_router_combinations.py",
        "tests/test_decorators.py",
        "tests/test_mutation_80_percent_contracts.py",
        "tests/test_mutation_survivor_contracts.py",
    ),
    "removal.py": (
        "tests/test_route_removal.py",
        "tests/test_registry.py",
        "tests/test_registry_router_ownership.py",
        "tests/test_registry_mutation_contracts.py",
        "tests/test_adversarial_router_combinations.py",
        "tests/test_decorators.py",
        "tests/test_mutation_80_percent_contracts.py",
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
        "tests/test_registry.py",
        "tests/test_decorators.py",
        "tests/test_mutation_80_percent_contracts.py",
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


def _contract_test_node_ids(source_name):
    """Return all targeted test node IDs for a source domain."""
    prefixes = CONTRACT_TEST_PREFIXES.get(source_name, ())
    if not prefixes:
        return []

    test_file = Path(CONTRACT_TEST_MODULES.get(source_name, CONTRACT_TEST_MODULE))
    if not test_file.is_file():
        raise RuntimeError(f"Missing mutation contract test module: {test_file}")

    node_ids = []
    for line in test_file.read_text(encoding="utf-8").splitlines():
        if not line.startswith("def test_"):
            continue
        name = line[len("def ") :].split("(", 1)[0]
        if name.startswith(prefixes):
            node_ids.append(f"{test_file.as_posix()}::{name}")
    return sorted(node_ids)


def _fallback_targets(test_paths, contract_node_ids):
    targets = list(test_paths)
    if CONTRACT_TEST_MODULE not in targets:
        targets.extend(sorted(contract_node_ids))
    return targets


def pre_mutation(context):
    """Run line contexts and all focused tests for the mutated source domain."""
    source_path = Path(context.filename).as_posix()
    source_name = source_path.split("django_api_versioning/", 1)[-1]
    coverage_data = context.config.coverage_data or {}
    source_path = os.path.abspath(context.filename)
    contexts_by_line = coverage_data.get(source_path, {})
    # Mutmut's Context.current_line_index is zero-based; Coverage.py uses 1-based lines.
    line_contexts = contexts_by_line.get(context.current_line_index + 1, [])

    line_node_ids = {
        context_name.split("|", 1)[0] for context_name in line_contexts if context_name
    }
    contract_source_name = (
        source_name if source_name in CONTRACT_TEST_PREFIXES else Path(source_name).name
    )
    contract_node_ids = set(_contract_test_node_ids(contract_source_name))
    test_paths = TESTS_BY_SOURCE.get(source_name) or TESTS_BY_SOURCE.get(
        Path(source_name).name
    )
    if line_node_ids and len(line_node_ids) <= MAX_LINE_CONTEXTS:
        node_ids = sorted(line_node_ids | contract_node_ids)
        context.config.test_command = (
            "python -m pytest -x -q -p no:pytest_cov -o addopts= "
            + " ".join(shlex.quote(node_id) for node_id in node_ids)
        )
        return

    if not test_paths:
        return
    fallback_targets = _fallback_targets(test_paths, contract_node_ids)
    context.config.test_command = (
        "python -m pytest -x -q -p no:pytest_cov -o addopts= "
        + " ".join(shlex.quote(target) for target in fallback_targets)
    )
