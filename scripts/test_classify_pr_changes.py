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

    def test_developer_requirements_change_runs_agent_and_dependency_checks(self):
        result = classify_paths(["requirements-dev.txt"])
        self.assertTrue(result["python"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["dependency"])
        self.assertTrue(result["agent"])

    def test_requirements_dev_runs_all_applicable_checks(self):
        result = classify_paths(["requirements-dev.txt"])
        self.assertTrue(result["python"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["package"])
        self.assertTrue(result["agent"])
        self.assertTrue(result["dependency"])

    def test_all_requirements_files_run_python_and_compatibility_checks(self):
        result = classify_paths(["requirements-extra.txt"])
        self.assertTrue(result["python"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["dependency"])

    def test_package_support_files_run_python_and_artifact_checks(self):
        result = classify_paths(
            [
                "tests/test_example.py",
                "pytest.ini",
                "scripts/verify_distribution_contents.py",
                "scripts/smoke_installed_wheel.py",
            ]
        )
        self.assertTrue(result["python"])
        self.assertTrue(result["package"])

    def test_reusable_workflow_files_trigger_their_matching_checks(self):
        cases = {
            ".github/workflows/tests.yml": "python",
            ".github/workflows/compatibility.yml": "compatibility",
            ".github/workflows/publish.yml": "compatibility",
            ".github/workflows/package-artifacts.yml": "package",
            ".github/workflows/website-data-preflight.yml": "website",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                result = classify_paths([path])
                self.assertTrue(result[expected])
                self.assertTrue(result["agent"])

    def test_github_settings_script_runs_agent_validation(self):
        result = classify_paths(["scripts/configure_github_repository.sh"])
        self.assertTrue(result["agent"])

    def test_unknown_markdown_does_not_trigger_unrelated_workflows(self):
        result = classify_paths(["docs/notes/internal-design.md"])
        self.assertFalse(any(result.values()))


if __name__ == "__main__":
    unittest.main()
