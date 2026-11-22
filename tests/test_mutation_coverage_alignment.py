"""Tests for the coverage-context alignment used by mutation shards."""

import sqlite3

from coverage import CoverageData

from scripts.align_mutation_coverage import (
    align_survivor_contexts,
    prepare_survivors_for_rerun,
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
    diff = "\\n".join(
        [
            "--- django_api_versioning/lifecycle.py",
            "+++ django_api_versioning/lifecycle.py",
            "@@ -295,7 +295,7 @@",
            "",
            "",
            " def is_past(value):",
            "-    return value < 0",
            "+    return value <= 0",
            "",
            "",
            " def to_http_date(value):",
        ]
    )
    assert mutation_line_number(diff, 297) == 298


def test_mutation_report_falls_back_when_diff_has_no_hunk():
    assert mutation_line_number("mutmut show returned no diff", 17) == 17


def test_cache_preparation_resets_only_surviving_mutants(tmp_path):
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
        """
    )
    connection.commit()
    connection.close()

    assert prepare_survivors_for_rerun(cache) == [
        ("django_api_versioning/registry.py", 427)
    ]
    connection = sqlite3.connect(cache)
    statuses = connection.execute("SELECT status FROM Mutant ORDER BY id").fetchall()
    connection.close()
    assert statuses == [("not_checked",), ("ok_killed",)]


def test_cache_loader_handles_a_missing_cache(tmp_path):
    assert prepare_survivors_for_rerun(tmp_path / "missing-cache") == []
