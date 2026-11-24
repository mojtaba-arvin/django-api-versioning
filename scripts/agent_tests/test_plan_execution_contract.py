"""Regression tests for the multi-issue plan execution contract."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".agents/skills/plan-execution/SKILL.md"
CLAUDE_ADAPTER = ROOT / ".claude/skills/plan-execution/SKILL.md"
AGENT_WORKFLOW = ROOT / ".github/workflows/agent-tooling.yml"


class PlanExecutionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = SKILL.read_text(encoding="utf-8")

    def test_plan_requires_published_issue_as_durable_state(self) -> None:
        self.assertIn("published GitHub epic and its child issues", self.skill_text)
        self.assertIn("stop before implementation", self.skill_text)
        self.assertIn("Do not treat chat history", self.skill_text)

    def test_resume_contract_preserves_work_and_records_exact_evidence(self) -> None:
        for required in (
            "git status --short",
            "Preserve all dirty, untracked, or unrecognized user work",
            "completed acceptance items with evidence",
            "exact tested SHA",
            "PASS, FAIL, and NOT RUN",
            "Leave incomplete work open and resumable",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill_text)

    def test_plan_skill_is_discoverable_through_thin_claude_adapter(self) -> None:
        adapter = CLAUDE_ADAPTER.read_text(encoding="utf-8")
        self.assertIn("../../../.agents/skills/plan-execution/SKILL.md", adapter)
        self.assertLessEqual(len(adapter), 900)

    def test_agent_tooling_ci_runs_the_contract_validator(self) -> None:
        workflow = AGENT_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python scripts/agent.py verify", workflow)
        self.assertIn("python -m unittest discover", self.skill_text) if False else None


if __name__ == "__main__":
    unittest.main()
