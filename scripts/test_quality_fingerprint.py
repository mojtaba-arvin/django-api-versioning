"""Tests for deterministic release-independent quality fingerprints."""

import unittest

from scripts.quality_fingerprint import fingerprint_files


class QualityFingerprintTests(unittest.TestCase):
    def test_package_version_only_changes_do_not_invalidate_quality_evidence(self):
        before = {
            "pyproject.toml": b'[project]\nname = "django-api-versioning"\nversion = "1.3.0"\ndependencies = ["Django>=4.2"]\n',
            "uv.lock": b'version = 1\ncontent-hash = "old"\n\n[[package]]\nname = "django-api-versioning"\nversion = "1.3.0"\n',
            "django_api_versioning/routers.py": b"class Router: pass\n",
            "tox.ini": b"[tox]\nenvlist = py312\n",
        }
        after = {
            "pyproject.toml": b'[project]\nname = "django-api-versioning"\nversion = "1.4.0"\ndependencies = ["Django>=4.2"]\n',
            "uv.lock": b'version = 1\ncontent-hash = "new"\n\n[[package]]\nname = "django-api-versioning"\nversion = "1.4.0"\n',
            "django_api_versioning/routers.py": b"class Router: pass\n",
            "tox.ini": b"[tox]\nenvlist = py312\n",
        }
        self.assertEqual(
            fingerprint_files(before, scope="deep"),
            fingerprint_files(after, scope="deep"),
        )

    def test_runtime_or_dependency_changes_invalidate_deep_evidence(self):
        before = {
            "pyproject.toml": b'[project]\nname = "django-api-versioning"\nversion = "1.3.0"\ndependencies = ["Django>=4.2"]\n',
            "django_api_versioning/routers.py": b"class Router: pass\n",
        }
        runtime_change = dict(before)
        runtime_change["django_api_versioning/routers.py"] = b"class Router: changed\n"
        dependency_change = dict(before)
        dependency_change["pyproject.toml"] = b'[project]\nname = "django-api-versioning"\nversion = "1.3.0"\ndependencies = ["Django>=5.0"]\n'
        baseline = fingerprint_files(before, scope="deep")
        self.assertNotEqual(
            baseline, fingerprint_files(runtime_change, scope="deep")
        )
        self.assertNotEqual(
            baseline, fingerprint_files(dependency_change, scope="deep")
        )

    def test_compatibility_fingerprint_tracks_matrix_and_dependency_inputs(self):
        before = {
            "tox.ini": b"[tox]\nenvlist = py312\n",
            "pyproject.toml": b'[project]\nname = "django-api-versioning"\nversion = "1.3.0"\n',
        }
        after = dict(before)
        after["tox.ini"] = b"[tox]\nenvlist = py313\n"
        self.assertNotEqual(
            fingerprint_files(before, scope="compatibility"),
            fingerprint_files(after, scope="compatibility"),
        )

    def test_documentation_is_not_part_of_runtime_quality_fingerprint(self):
        files = {
            "django_api_versioning/routers.py": b"class Router: pass\n",
            "docs/reference/index.md": b"Version 1.3.0",
        }
        with_docs = dict(files)
        with_docs["docs/reference/index.md"] = b"Version 1.4.0"
        self.assertEqual(
            fingerprint_files(files, scope="deep"),
            fingerprint_files(with_docs, scope="deep"),
        )


if __name__ == "__main__":
    unittest.main()
