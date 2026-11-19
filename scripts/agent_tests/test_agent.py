"""Tests for the dependency-free coding-agent helper."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import agent  # noqa: E402
import verify_repository_policy  # noqa: E402


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

    def test_website_profile_uses_the_canonical_contract(self) -> None:
        profile = agent.context_profile("website")
        self.assertIn("website/AGENTS.md", profile["read"])
        self.assertNotIn("docs/website/architecture.md", profile["read"])
        self.assertFalse(
            any("netlify-agent-handoff.md" in item for item in profile["read"])
        )

    def test_nested_website_skill_registries_are_rejected(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = root / "website/.agents/skills"
            nested.mkdir(parents=True)
            errors = agent._validate_nested_website_skills(root)
            self.assertEqual(len(errors), 1)
            self.assertIn("website/.agents/skills", errors[0])

    def test_unknown_profile_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            agent.context_profile("everything")

    def test_release_provenance_eval_covers_artifact_boundary(self) -> None:
        evaluation = json.loads(
            (ROOT / ".agents/evals/scenarios.json").read_text(encoding="utf-8")
        )
        scenario = next(
            item
            for item in evaluation["scenarios"]
            if item["id"] == "published-artifact-provenance"
        )
        checks = " ".join(scenario["checks"]).lower()
        self.assertIn("annotated tag", checks)
        self.assertIn("current main", checks)
        self.assertIn("published", checks)
        self.assertIn("repository-level", checks)

    def test_release_context_does_not_reference_the_old_report_path(self) -> None:
        profile = agent.context_profile("release")
        self.assertNotIn("COMPATIBILITY_REPORT.md", profile["read"])

    def test_workflow_security_policy_passes(self) -> None:
        self.assertEqual(verify_repository_policy.validate(), [])

    def test_root_permissions_parser_is_bounded_and_exact(self) -> None:
        self.assertTrue(
            verify_repository_policy._has_root_contents_read(
                "name: Check\npermissions:\n  contents: read\njobs:\n  test:"
            )
        )
        self.assertFalse(
            verify_repository_policy._has_root_contents_read(
                "name: Check\npermissions:\n  contents: write\njobs:\n  test:"
            )
        )
        self.assertFalse(
            verify_repository_policy._has_root_contents_read(
                "name: Check\npermissions:\n" + ("\t\t\n" * 10000) + "jobs:"
            )
        )

    def test_skill_reference_links_must_exist_and_stay_inside_repository(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / ".agents/skills/demo/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "[present](references/guide.md) [missing](references/missing.md) "
                "[outside](../../../../outside.md) [external](https://example.com) "
                "[protocol-relative](//example.com)",
                encoding="utf-8",
            )
            reference = skill.parent / "references/guide.md"
            reference.parent.mkdir()
            reference.write_text("guide", encoding="utf-8")
            errors = agent.validate_reference_links(skill, root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("missing reference" in error for error in errors))
            self.assertTrue(any("escapes repository" in error for error in errors))

    def test_evaluation_scenario_rejects_unhashable_profile(self) -> None:
        scenario = {
            "id": "invalid-profile",
            "profile": [],
            "task": "Exercise malformed profile metadata.",
            "checks": ["The invalid profile is rejected."],
            "failure_modes": ["The validator raises a TypeError."],
        }
        errors = agent._validate_scenario(scenario, set())
        self.assertTrue(any("Unknown profile" in error for error in errors))

    def test_all_canonical_skills_have_consistent_adapters(self) -> None:
        self.assertEqual(agent.validate_tree(ROOT), [])

    def test_doctor_reports_configuration_without_environment_values(self) -> None:
        report = agent.doctor_report(ROOT)
        metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        version_line = next(
            line for line in metadata.splitlines() if line.startswith("version = ")
        )
        expected_version = (
            version_line.partition("=")[2].strip().strip(chr(34)).strip(chr(39))
        )
        self.assertEqual(report["package_version"], expected_version)
        self.assertTrue(report["configuration"]["integration_pytest_config"])
        self.assertIn(
            report["working_tree"],
            {"clean", "dirty", "unknown"},
        )


if __name__ == "__main__":
    unittest.main()
