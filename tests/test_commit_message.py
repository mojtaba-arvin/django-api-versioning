"""Tests for the repository's Conventional Commit validator."""

from scripts.check_commit_message import validate_commit_message


def test_accepts_scoped_conventional_commit():
    assert validate_commit_message("fix(router): reject invalid prefixes") == []


def test_accepts_unscoped_and_breaking_commit():
    assert validate_commit_message("feat!: change the public routing contract") == []


def test_rejects_non_conventional_subjects():
    for subject in (
        "Update files",
        "Fix: reject invalid input",
        "feat(router) reject invalid prefixes",
        "feat(router): Reject invalid prefixes",
        "feat(router): reject invalid prefixes.",
        "feat(router):",
        "Merge pull request #123",
    ):
        assert validate_commit_message(subject), subject


def test_rejects_subject_over_100_characters():
    subject = "chore: " + ("a" * 94)
    assert len(subject) == 101
    assert any("maximum is 100" in error for error in validate_commit_message(subject))


def test_rejects_invalid_scope_characters():
    assert validate_commit_message("fix(Invalid_Scope): correct behavior")


def test_rejects_trailing_subject_whitespace():\n    assert validate_commit_message("fix(api): reject malformed headers ")\n\n\ndef test_rejects_scope_with_trailing_separator():\n    assert validate_commit_message("fix(api/): reject malformed headers")\n\n\ndef test_accepts_multiline_message_with_conventional_subject():
    message = (
        "test(registry): cover concurrent registration\n\n"
        "Exercise the race between registration and lookup."
    )
    assert validate_commit_message(message) == []
