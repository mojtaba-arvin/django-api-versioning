"""Tests for the dependency-free coding-agent helper."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import agent  # noqa: E402


class AgentToolingTests(unittest.TestCase):
    def test_frontmatter_requires_delimited_metadata(self) -> None:
        expected = {"name": "demo", "description": "Do a thing"}
        source = "---\nname: demo\ndescription: Do a thing\n---\nbody"
        self.assertEqual(agent.parse_frontmatter(source), expected)
        self.assertEqual(
            agent.parse_frontmatter("name: demo\ndescription: Do a thing"),
            {},
        )

    def test_task_profiles_are_small_and_specific(self) -> None:
        profile = agent.context_profile("testing")
        self.assertEqual(
            profile["skill"],
            ".agents/skills/manual-testing/SKILL.md",
        )
        self.assertIn("tox.ini", profile["read"])
        self.assertNotIn("package source", profile["read"])

    def test_unknown_profile_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            agent.context_profile("everything")

    def test_all_canonical_skills_have_consistent_adapters(self) -> None:
        self.assertEqual(agent.validate_tree(ROOT), [])

    def test_doctor_reports_configuration_without_environment_values(self) -> None:
        report = agent.doctor_report(ROOT)
        self.assertEqual(report["package_version"], "0.3.7")
        self.assertTrue(report["configuration"]["integration_pytest_config"])
        self.assertIn(
            report["working_tree"],
            {"clean", "dirty", "unknown"},
        )


if __name__ == "__main__":
    unittest.main()
