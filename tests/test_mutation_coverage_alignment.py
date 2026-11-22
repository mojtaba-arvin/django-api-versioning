"""Tests for the coverage-context alignment used by mutation shards."""

import sqlite3

from coverage import CoverageData

from scripts.align_mutation_coverage import (
    align_survivor_contexts,
    load_survivor_locations,
)
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



def test_cache_loader_returns_survivors_and_previously_untested_locations(tmp_path):
    cache = tmp_path / ".mutmut-cache"
    connection = sqlite3.connect(cache)
    connection.executescript(
        """
        CREATE TABLE SourceFile (id INTEGER PRIMARY KEY, filename TEXT NOT NULL);
        CREATE TABLE Line (
            id INTEGER PRIMARY KEY,
            sourcefile INTEGER NOT NULL,
            line_number INTEGER NOT NULL
        );
        CREATE TABLE Mutant (
            id INTEGER PRIMARY KEY,
            line INTEGER NOT NULL,
            status TEXT NOT NULL
        );
        INSERT INTO SourceFile VALUES (1, 'django_api_versioning/registry.py');
        INSERT INTO Line VALUES (1, 1, 427);
        INSERT INTO Line VALUES (2, 1, 428);
        INSERT INTO Mutant VALUES (1, 1, 'bad_survived');
        INSERT INTO Mutant VALUES (2, 2, 'ok_killed');
        INSERT INTO Mutant VALUES (3, 2, 'not_checked');
        """
    )
    connection.commit()
    connection.close()

    assert load_survivor_locations(cache) == [
        ("django_api_versioning/registry.py", 427),
        ("django_api_versioning/registry.py", 428),
    ]


def test_cache_loader_handles_a_missing_cache(tmp_path):
    assert load_survivor_locations(tmp_path / "missing-cache") == []



def test_alignment_merges_following_contexts_even_when_ast_line_is_covered(
    tmp_path,
):
    source = tmp_path / "django_api_versioning" / "registry.py"
    source.parent.mkdir()
    source.write_text("def remove(value):\n    if value:\n        return True\n")
    coverage_path = tmp_path / ".coverage"

    data = CoverageData(basename=str(coverage_path))
    existing = "tests.test_registry::test_existing|run"
    changed = "tests.test_registry::test_changed_statement|run"
    data.set_context(existing)
    data.add_lines({str(source): {2}})
    data.set_context(changed)
    data.add_lines({str(source): {3}})
    data.write()

    data = CoverageData(basename=str(coverage_path))
    data.read()
    assert align_survivor_contexts(
        data, [("django_api_versioning/registry.py", 2)]
    ) == (1, 1)
    data.write()

    aligned = CoverageData(basename=str(coverage_path))
    aligned.read()
    contexts = aligned.contexts_by_lineno(str(source))
    assert existing in contexts[2]
    assert changed in contexts[2]



def test_alignment_looks_through_signature_and_docstring_to_function_body(
    tmp_path,
):
    source = tmp_path / "django_api_versioning" / "lifecycle.py"
    source.parent.mkdir()
    source.write_text(
        "def resolve(\n"
        "    request,\n"
        "    *,\n"
        "    allow_unmapped_method=False,\n"
        "):\n"
        '    """Resolve one operation."""\n'
        "    return request\n"
    )
    coverage_path = tmp_path / ".coverage"

    data = CoverageData(basename=str(coverage_path))
    context = "tests.test_lifecycle::test_signature_default|run"
    data.set_context(context)
    data.add_lines({str(source): {7}})
    data.write()

    data = CoverageData(basename=str(coverage_path))
    data.read()
    assert align_survivor_contexts(
        data, [("django_api_versioning/lifecycle.py", 1)]
    ) == (1, 1)
    data.write()

    aligned = CoverageData(basename=str(coverage_path))
    aligned.read()
    assert context in aligned.contexts_by_lineno(str(source))[1]
