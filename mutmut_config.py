"""Targeted test selection for mutmut, with a full-suite safety net.

The focused files are chosen to exercise each module's public and internal
contracts. mutmut is invoked with --rerun-all, so surviving mutants are
rechecked against the complete test suite before they are classified as
survivors.
"""

from pathlib import Path

TESTS_BY_SOURCE = {
    "decorators.py": (
        "tests/test_decorators.py",
        "tests/test_route_removal.py",
        "tests/test_routers.py",
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
    """Run the narrowest relevant tests first; mutmut reruns survivors fully."""
    source_name = Path(context.filename).name
    test_paths = TESTS_BY_SOURCE.get(source_name)
    if not test_paths:
        return

    context.config.test_command = (
        "python -m pytest -x -q -p no:pytest_cov -o addopts= "
        + " ".join(test_paths)
    )
