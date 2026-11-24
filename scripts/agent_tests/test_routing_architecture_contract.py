"""Deterministic checks for the routing architecture agent contract."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import agent  # noqa: E402

SKILL = ROOT / ".agents/skills/routing-architecture/SKILL.md"
ADAPTER = ROOT / ".claude/skills/routing-architecture/SKILL.md"
CLAUDE = ROOT / "CLAUDE.md"
COPILOT = ROOT / ".github/copilot-instructions.md"
SCENARIOS = ROOT / ".agents/evals/scenarios.json"


class RoutingArchitectureSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = SKILL.read_text(encoding="utf-8")
        cls.scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))

    def test_profile_is_registered_and_bounded(self) -> None:
        profile = agent.context_profile("routing-architecture")
        self.assertEqual(
            profile["skill"],
            ".agents/skills/routing-architecture/SKILL.md",
        )
        self.assertLessEqual(len(profile["read"]), 8)
        self.assertLessEqual(len(profile["avoid"]), 6)
        self.assertIn(
            "tests/test_registry.py and directly related state/ownership tests",
            profile["read"],
        )

    def test_skill_delegates_to_existing_execution_and_package_contracts(self) -> None:
        self.assertIn("../plan-execution/SKILL.md", self.skill_text)
        self.assertIn("../package-engineering/SKILL.md", self.skill_text)
        self.assertIn("one child issue, one focused branch", self.skill_text)

    def test_skill_covers_single_owner_immutable_state_and_compatibility_facade(self) -> None:
        for required in (
            "One authoritative state owner",
            "Immutable means deeply immutable",
            "Import/reload behavior is a contract",
            "Compatibility facade first",
            "A published snapshot never changes",
            "Successful transactions atomically publish a new generation",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill_text)

    def test_skill_preserves_optional_framework_and_diagnostics_boundaries(self) -> None:
        for required in (
            "Core package imports must work without DRF",
            "one narrow optional adapter",
            "Diagnostics are read-only",
            "Public APIs require a lifecycle contract",
            "One canonical documentation owner",
            "current path classifier and PR gate",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill_text)

    def test_claude_adapter_matches_canonical_metadata_and_is_thin(self) -> None:
        canonical = agent.parse_frontmatter(self.skill_text)
        adapter_text = ADAPTER.read_text(encoding="utf-8")
        self.assertEqual(agent.parse_frontmatter(adapter_text), canonical)
        self.assertIn(
            "../../../.agents/skills/routing-architecture/SKILL.md",
            adapter_text,
        )
        self.assertLessEqual(len(adapter_text), 900)

    def test_client_entrypoints_discover_the_skill(self) -> None:
        self.assertIn("/routing-architecture", CLAUDE.read_text(encoding="utf-8"))
        self.assertIn(
            ".agents/skills/routing-architecture/SKILL.md",
            COPILOT.read_text(encoding="utf-8"),
        )

    def test_model_agnostic_scenarios_are_present_and_valid(self) -> None:
        expected = {
            "routing-architecture-state-ownership",
            "routing-architecture-immutable-snapshot",
            "routing-architecture-optional-drf-boundary",
            "routing-architecture-safe-incremental-migration",
        }
        by_id = {item["id"]: item for item in self.scenarios["scenarios"]}
        self.assertTrue(expected.issubset(by_id))
        for scenario_id in expected:
            with self.subTest(scenario=scenario_id):
                item = by_id[scenario_id]
                self.assertEqual(item["profile"], "routing-architecture")
                self.assertTrue(item["checks"])
                self.assertTrue(item["failure_modes"])
        self.assertEqual(agent._validate_evaluation_suite(ROOT), [])

    def test_repository_agent_configuration_remains_valid(self) -> None:
        self.assertEqual(agent.validate_tree(ROOT), [])


if __name__ == "__main__":
    unittest.main()
