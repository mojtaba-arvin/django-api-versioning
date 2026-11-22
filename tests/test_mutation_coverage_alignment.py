"""Tests for the coverage-context alignment used by mutation shards."""

from coverage import CoverageData

from scripts.align_mutation_coverage import align_survivor_contexts
from scripts.export_mutation_report import mutation_line_number


def test_alignment_copies_contexts_from_the_changed_statement_to_mutmut_ast_line(
    tmp_path,
):
    source = tmp_path / "django_api_versioning" / "lifecycle.py"
    source.parent.mkdir()
    source.write_text("def is_past(value):\n    return value < 0\n")
    coverage_path = tmp_path / ".coverage"

    data = CoverageData(basename=str(coverage_path))
    test_context = "tests.test_lifecycle::test_boundary|run"
    data.set_context(test_context)
    data.add_lines({str(source): {2}})
    data.write()

    data = CoverageData(basename=str(coverage_path))
    data.read()
    location = [("django_api_versioning/lifecycle.py", 1)]
    assert align_survivor_contexts(data, location) == (1, 1)
    data.write()

    aligned = CoverageData(basename=str(coverage_path))
    aligned.read()
    contexts = aligned.contexts_by_lineno(str(source))
    assert test_context in contexts[1]
    assert test_context in contexts[2]


def test_alignment_is_idempotent_and_ignores_unrelated_files(tmp_path):
    target = tmp_path / "django_api_versioning" / "registry.py"
    unrelated = tmp_path / "other.py"
    target.parent.mkdir()
    target.write_text("def target():\n    return True\n")
    unrelated.write_text("def unrelated():\n    return True\n")
    coverage_path = tmp_path / ".coverage"

    data = CoverageData(basename=str(coverage_path))
    data.set_context("tests.test_registry::test_target|run")
    data.add_lines({str(target): {2}, str(unrelated): {2}})
    data.write()

    data = CoverageData(basename=str(coverage_path))
    data.read()
    locations = [("django_api_versioning/registry.py", 1)]
    assert align_survivor_contexts(data, locations) == (1, 1)
    assert align_survivor_contexts(data, locations) == (0, 0)


def test_mutation_report_uses_changed_line_from_unified_diff():
    diff = """--- django_api_versioning/lifecycle.py
+++ django_api_versioning/lifecycle.py
@@ -295,7 +295,7 @@
 
 
 def is_past(value):
-    return value < 0
+    return value <= 0
 
 
 def to_http_date(value):
"""
    assert mutation_line_number(diff, 297) == 298


def test_mutation_report_falls_back_when_diff_has_no_hunk():
    assert mutation_line_number("mutmut show returned no diff", 17) == 17
