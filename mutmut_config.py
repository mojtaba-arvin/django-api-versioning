"""Line-level test selection for mutmut, with a full-suite safety net.

Pytest-cov contexts identify the exact test node IDs that executed each
mutated line. Static per-module test lists remain a conservative fallback.
The scheduled full campaign adds --rerun-all to verify surviving mutants.
"""

import os
import shlex
from pathlib import Path

TESTS_BY_SOURCE = {
    "decorators.py": (
        "tests/test_decorators.py",
        "tests/test_route_removal.py",
        "tests/test_routers.py",
        "tests/test_segment_model.py",
        "tests/test_adversarial_router_combinations.py",
    ),
    "lifecycle.py": (
        "tests/test_lifecycle.py",
        "tests/test_lifecycle_ascii_version.py",
        "tests/test_lifecycle_integration.py",
        "tests/test_lifecycle_route_identity.py",
        "tests/test_management_commands.py",
        "tests/test_adversarial_router_combinations.py",
    ),
    "negotiation.py": (
        "tests/test_negotiation_middleware.py",
        "tests/test_negotiation_properties.py",
        "tests/test_adversarial_router_combinations.py",
    ),
    "registry.py": (
        "tests/test_registry.py",
        "tests/test_registry_router_ownership.py",
        "tests/test_segment_model.py",
        "tests/test_route_removal.py",
        "tests/test_adversarial_router_combinations.py",
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
    """Run tests that executed this exact line; fall back to module-level tests."""
    source_name = Path(context.filename).name
    coverage_data = context.config.coverage_data or {}
    source_path = os.path.abspath(context.filename)
    contexts_by_line = coverage_data.get(source_path, {})
    line_contexts = contexts_by_line.get(context.current_line_index, [])

    node_ids = sorted(
        {
            context_name.split("|", 1)[0]
            for context_name in line_contexts
            if context_name
        }
    )
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        node_ids = node_ids[:1]
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
