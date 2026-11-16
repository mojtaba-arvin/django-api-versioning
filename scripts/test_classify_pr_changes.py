"""Unit tests for the pull-request path classifier."""

import unittest

from scripts.classify_pr_changes import classify_paths


class ClassifyPullRequestChangesTests(unittest.TestCase):
    def test_package_source_runs_python_compatibility_and_artifacts(self):
        result = classify_paths(["django_api_versioning/registry.py"])
        self.assertTrue(result["python"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["package"])
        self.assertFalse(result["website"])

    def test_article_change_runs_only_website(self):
        result = classify_paths(["docs/articles/versioning.md"])
        self.assertTrue(result["website"])
        self.assertFalse(result["python"])
        self.assertFalse(result["package"])

    def test_website_manifest_runs_website_and_dependency_review(self):
        result = classify_paths(["website/package.json"])
        self.assertTrue(result["website"])
        self.assertTrue(result["dependency"])
        self.assertFalse(result["python"])

    def test_agent_and_workflow_changes_run_agent_validation(self):
        result = classify_paths(
            ["AGENTS.md", ".github/workflows/pull-request-gate.yml"]
        )
        self.assertTrue(result["agent"])
        self.assertFalse(result["python"])

    def test_pyproject_runs_all_python_release_checks_and_dependency_review(self):
        result = classify_paths(["pyproject.toml"])
        self.assertTrue(result["python"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["package"])
        self.assertTrue(result["dependency"])

    def test_workflow_policy_updates_run_agent_validation(self):
        result = classify_paths([".github/dependabot.yml"])
        self.assertTrue(result["agent"])

    def test_unknown_markdown_does_not_trigger_unrelated_workflows(self):
        result = classify_paths(["docs/notes/internal-design.md"])
        self.assertFalse(any(result.values()))


if __name__ == "__main__":
    unittest.main()
