"""Deterministic checks for the fresh-session plan execution contract."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import agent  # noqa: E402
import classify_pr_changes  # noqa: E402

SKILL = ROOT / ".agents/skills/plan-execution/SKILL.md"
CLAUDE_ADAPTER = ROOT / ".claude/skills/plan-execution/SKILL.md"
AGENT_WORKFLOW = ROOT / ".github/workflows/agent-tooling.yml"
SCENARIOS = ROOT / ".agents/evals/scenarios.json"


class PlanExecutionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = SKILL.read_text(encoding="utf-8")
        cls.scenario_suite = json.loads(SCENARIOS.read_text(encoding="utf-8"))

    def test_plan_requires_published_github_state_before_implementation(self) -> None:
        for required in (
            "published GitHub epic and its child issues",
            "stop before implementation",
            "Do not treat chat history",
            "Select and claim exactly one child",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill_text)

    def test_resume_contract_preserves_work_and_records_exact_evidence(self) -> None:
        for required in (
            "git status --short",
            "Preserve all dirty, untracked, or unrecognized user work",
            "completed acceptance items with evidence",
            "Current full SHA",
            "Commands run (exact command, exit code, tested SHA)",
            "Checks not run:",
            "Leave incomplete work open and resumable",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill_text)

    def test_plan_skill_has_a_dedicated_bounded_context_profile(self) -> None:
        profile = agent.context_profile("plan-execution")
        self.assertEqual(
            profile["skill"],
            ".agents/skills/plan-execution/SKILL.md",
        )
        self.assertIn(
            "the identified GitHub epic and selected child issue", profile["read"]
        )
        self.assertIn(
            "duplicate roadmap, handoff, progress, or generated status documents",
            profile["avoid"],
        )
        self.assertLessEqual(len(profile["read"]), 6)

    def test_plan_skill_has_a_consistent_thin_adapter(self) -> None:
        canonical = agent.parse_frontmatter(self.skill_text)
        adapter_text = CLAUDE_ADAPTER.read_text(encoding="utf-8")
        self.assertEqual(agent.parse_frontmatter(adapter_text), canonical)
        self.assertIn("../../../.agents/skills/plan-execution/SKILL.md", adapter_text)
        self.assertLessEqual(len(adapter_text), 900)

    def test_fresh_session_plan_scenarios_are_registered_and_valid(self) -> None:
        scenarios = self.scenario_suite["scenarios"]
        by_id = {scenario["id"]: scenario for scenario in scenarios}
        required_ids = {
            "plan-execution-unpublished-issue",
            "plan-execution-fresh-session-resume",
            "plan-execution-dependency-and-scope-selection",
            "plan-execution-dynamic-ci-and-document-ownership",
        }
        self.assertTrue(required_ids.issubset(by_id))
        for scenario_id in required_ids:
            with self.subTest(scenario=scenario_id):
                scenario = by_id[scenario_id]
                self.assertEqual(scenario["profile"], "plan-execution")
                self.assertTrue(scenario["checks"])
                self.assertTrue(scenario["failure_modes"])
        self.assertEqual(agent._validate_evaluation_suite(ROOT), [])

    def test_plan_policy_covers_docs_and_dynamic_ci(self) -> None:
        for required in (
            "GitHub child issue + its linked PR are the only "
            "durable task/progress records",
            "Generated files must be rebuilt by their owning generator",
            "scripts/classify_pr_changes.py",
            "exact PR head SHA",
            "A skipped job is not a pass",
            "Do not create no-op commits",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill_text)

    def test_agent_tooling_ci_and_path_classifier_cover_the_contract(self) -> None:
        workflow = AGENT_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python scripts/agent.py verify", workflow)
        classification = classify_pr_changes.classify_paths(
            [
                ".agents/skills/plan-execution/SKILL.md",
                ".agents/evals/scenarios.json",
                ".claude/skills/plan-execution/SKILL.md",
                "scripts/agent.py",
                "scripts/agent_tests/test_plan_execution_contract.py",
            ]
        )
        self.assertTrue(classification["agent"])
        self.assertTrue(classification["compatibility"])
        self.assertTrue(classification["compatibility_full"])
        self.assertFalse(classification["python"])
        self.assertFalse(classification["deep"])
        self.assertFalse(classification["package"])

    def test_agent_tooling_workflow_remains_a_separate_validation_job(self) -> None:
        workflow = AGENT_WORKFLOW.read_text(encoding="utf-8")
        pr_gate = (ROOT / ".github/workflows/pull-request-gate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python scripts/agent.py verify", workflow)
        self.assertIn("agent-tooling:", pr_gate)
        self.assertIn("needs.changes.outputs.agent == 'true'", pr_gate)


if __name__ == "__main__":
    unittest.main()
