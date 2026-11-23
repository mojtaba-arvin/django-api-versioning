"""Unit tests for the pull-request path classifier."""

import unittest

from scripts.classify_pr_changes import classify_paths


class ClassifyPullRequestChangesTests(unittest.TestCase):
    def test_package_source_runs_python_compatibility_artifacts_and_website(self):
        result = classify_paths(["django_api_versioning/registry.py"])
        self.assertTrue(result["python"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["package"])
        self.assertTrue(result["website"])
        self.assertTrue(result["openapi"])

    def test_openapi_contract_runs_for_all_schema_affecting_runtime_modules(self):
        for path in (
            "django_api_versioning/routers.py",
            "django_api_versioning/registry.py",
            "django_api_versioning/decorators.py",
            "django_api_versioning/settings.py",
            "django_api_versioning/reverse.py",
            "django_api_versioning/urls.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(classify_paths([path])["openapi"])

    def test_openapi_example_and_design_changes_run_the_contract(self):
        for path in (
            "examples/openapi_contract/verify.py",
            "examples/openapi_contract/schemas/v1/openapi.yaml",
            "examples/consumer_migration/verify.py",
            "examples/consumer_migration/schemas/v3/openapi.yaml",
            "examples/consumer_migration/README.md",
            "docs/design/versioned-openapi-contract.md",
            ".github/workflows/openapi-contract.yml",
        ):
            with self.subTest(path=path):
                self.assertTrue(classify_paths([path])["openapi"])

    def test_integration_evidence_changes_run_website_verification(self):
        result = classify_paths(
            ["integration_test_project/segment_lab/scenario_catalog.py"]
        )
        self.assertTrue(result["python"])
        self.assertTrue(result["website"])

    def test_article_change_runs_only_website(self):
        result = classify_paths(["docs/articles/versioning.md"])
        self.assertTrue(result["website"])
        self.assertFalse(result["python"])
        self.assertFalse(result["package"])

    def test_reference_source_change_runs_website_checks(self):
        result = classify_paths(["docs/reference/index.md"])
        self.assertTrue(result["website"])
        self.assertFalse(result["python"])
        self.assertFalse(result["package"])

    def test_website_manifest_runs_website_and_dependency_review(self):
        result = classify_paths(["website/package.json"])
        self.assertTrue(result["website"])
        self.assertTrue(result["dependency"])
        self.assertFalse(result["python"])

    def test_website_agent_instructions_run_website_and_agent_validation(self):
        result = classify_paths(["website/AGENTS.md"])
        self.assertTrue(result["website"])
        self.assertTrue(result["agent"])

    def test_website_pnpm_lock_runs_dependency_review(self):
        result = classify_paths(["website/pnpm-lock.yaml"])
        self.assertTrue(result["website"])
        self.assertTrue(result["dependency"])

    def test_nested_example_requirements_run_dependency_review(self):
        result = classify_paths(["examples/consumer_migration/requirements.txt"])
        self.assertTrue(result["openapi"])
        self.assertTrue(result["dependency"])

    def test_nested_website_agent_files_run_agent_validation(self):
        result = classify_paths(["website/.agents/skills/obsolete/SKILL.md"])
        self.assertTrue(result["website"])
        self.assertTrue(result["agent"])

    def test_agent_and_workflow_changes_run_agent_validation(self):
        result = classify_paths(
            ["AGENTS.md", ".github/workflows/pull-request-gate.yml"]
        )
        self.assertTrue(result["agent"])
        self.assertTrue(result["python"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["openapi"])

    def test_pyproject_dependency_changes_run_deep_quality_and_release_checks(self):
        result = classify_paths(["pyproject.toml"])
        self.assertTrue(result["python"])
        self.assertTrue(result["deep"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["package"])
        self.assertTrue(result["dependency"])
        self.assertTrue(result["website"])
        self.assertTrue(result["openapi"])

    def test_version_only_release_metadata_skips_unrelated_deep_gates(self):
        result = classify_paths(
            ["pyproject.toml", "uv.lock", "CHANGELOG.md", "docs/reference/index.md"],
            release_metadata_only=True,
        )
        self.assertFalse(result["python"])
        self.assertFalse(result["deep"])
        self.assertFalse(result["compatibility"])
        self.assertTrue(result["metadata"])
        self.assertTrue(result["package"])
        self.assertFalse(result["dependency"])
        self.assertTrue(result["website"])
        self.assertFalse(result["openapi"])

    def test_python_test_and_coverage_gate_changes_run_openapi_coverage(self):
        for path in (
            "tests/test_public_api_contracts.py",
            "tests/test_coverage_thresholds.py",
            "scripts/check_coverage_thresholds.py",
            ".github/workflows/tests.yml",
        ):
            with self.subTest(path=path):
                result = classify_paths([path])
                self.assertTrue(result["python"])
                self.assertTrue(result["openapi"])

    def test_quality_pipeline_workflow_changes_run_their_own_quality_gates(self):
        for path in (
            ".github/workflows/tests.yml",
            ".github/workflows/adversarial-testing.yml",
            ".github/actions/mutation-shard/action.yml",
            ".github/workflows/mutation-shard.yml",
            ".github/workflows/pull-request-gate.yml",
            ".github/workflows/compatibility.yml",
            ".github/workflows/openapi-contract.yml",
            ".github/workflows/package-artifacts.yml",
            ".github/workflows/publish.yml",
        ):
            with self.subTest(path=path):
                result = classify_paths([path])
                self.assertTrue(result["python"])
                self.assertTrue(result["compatibility"])
                self.assertTrue(result["openapi"])

    def test_workflow_policy_updates_run_agent_validation(self):
        result = classify_paths([".github/dependabot.yml"])
        self.assertTrue(result["agent"])

    def test_requirements_dev_runs_all_applicable_checks(self):
        result = classify_paths(["requirements-dev.txt"])
        self.assertTrue(result["python"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["package"])
        self.assertTrue(result["agent"])
        self.assertTrue(result["dependency"])
        self.assertTrue(result["website"])

    def test_all_requirements_files_run_python_and_compatibility_checks(self):
        result = classify_paths(["requirements-extra.txt"])
        self.assertTrue(result["python"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["dependency"])
        self.assertTrue(result["website"])

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
        self.assertTrue(result["website"])

    def test_reusable_workflow_files_trigger_their_matching_checks(self):
        cases = {
            ".github/workflows/tests.yml": "python",
            ".github/workflows/compatibility.yml": "compatibility",
            ".github/workflows/package-artifacts.yml": "package",
            ".github/workflows/website-data-preflight.yml": "website",
            ".github/workflows/openapi-contract.yml": "openapi",
            ".github/workflows/publish.yml": "openapi",
            "scripts/release_bootstrap.sh": "compatibility",
            "Makefile": "compatibility",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                result = classify_paths([path])
                self.assertTrue(result[expected])
                self.assertTrue(result["agent"])

    def test_publish_workflow_runs_compatibility_and_openapi_checks(self):
        result = classify_paths([".github/workflows/publish.yml"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["openapi"])

    def test_reproducible_build_helper_runs_package_and_python_gates(self):
        result = classify_paths(["scripts/check_reproducible_build.py"])
        self.assertTrue(result["python"])
        self.assertTrue(result["compatibility"])
        self.assertTrue(result["package"])
        self.assertTrue(result["openapi"])

    def test_classifier_self_test_runs_agent_validation(self):
        result = classify_paths(["scripts/test_classify_pr_changes.py"])
        self.assertTrue(result["agent"])

    def test_github_settings_script_runs_agent_validation(self):
        result = classify_paths(["scripts/configure_github_repository.sh"])
        self.assertTrue(result["agent"])

    def test_maintainer_helper_runs_agent_validation(self):
        result = classify_paths(["scripts/maintain.sh"])
        self.assertTrue(result["agent"])
        self.assertFalse(result["python"])

    def test_release_bootstrap_files_run_agent_validation(self):
        result = classify_paths(["Makefile", "scripts/release_bootstrap.sh"])
        self.assertTrue(result["agent"])
        self.assertFalse(result["python"])

    def test_release_tag_helpers_run_agent_validation(self):
        result = classify_paths(
            ["scripts/release_tags.py", "scripts/test_release_tags.py"]
        )
        self.assertTrue(result["agent"])
        self.assertFalse(result["python"])

    def test_unknown_markdown_does_not_trigger_unrelated_workflows(self):
        result = classify_paths(["docs/notes/internal-design.md"])
        self.assertFalse(any(result.values()))


if __name__ == "__main__":
    unittest.main()
