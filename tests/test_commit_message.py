"""Tests for the repository's Conventional Commit validator."""

from scripts.check_commit_message import (
    ALLOWED_TYPES,
    validate_commit_message,
    validate_commit_subjects,
)


def test_accepts_every_documented_type():
    for commit_type in ALLOWED_TYPES:
        assert validate_commit_message(f"{commit_type}: update routing behavior") == []


def test_accepts_scoped_and_unscoped_subjects():
    assert validate_commit_message("fix(router): reject invalid prefixes") == []
    assert validate_commit_message("docs: explain version negotiation") == []


def test_accepts_breaking_marker_and_footer():
    assert validate_commit_message("feat(api)!: change the public contract") == []
    message = (
        "feat(api): change the public contract\n\n"
        "BREAKING CHANGE: clients must send the new version header"
    )
    assert validate_commit_message(message) == []


def test_accepts_multiline_message_without_footer():
    message = (
        "test(registry): cover concurrent registration\n\n"
        "Exercise the race between registration and lookup."
    )
    assert validate_commit_message(message) == []


def test_rejects_unknown_types():
    assert any(
        "unknown commit type" in error
        for error in validate_commit_message("banana: update routing behavior")
    )


def test_rejects_non_conventional_or_invalid_subjects():
    for subject in (
        "Update files",
        "Fix: reject invalid input",
        "feat(router) reject invalid prefixes",
        "feat(router): Reject invalid prefixes",
        "feat(router): reject API Versioning",
        "feat(router): reject invalid prefixes.",
        "feat(router):",
        "feat(router):  leading whitespace",
        "feat(router): trailing whitespace ",
        "feat(router): reject invalid prefixes\t",
        "Merge pull request #123",
    ):
        assert validate_commit_message(subject), subject


def test_rejects_subject_over_100_characters():
    subject = "chore: " + ("a" * 94)
    assert len(subject) == 101
    assert any("maximum is 100" in error for error in validate_commit_message(subject))


def test_rejects_invalid_scopes():
    for subject in (
        "fix(Invalid): correct behavior",
        "fix(invalid_scope): correct behavior",
        "fix(api/): correct behavior",
        "fix(/api): correct behavior",
    ):
        assert validate_commit_message(subject), subject


def test_rejects_empty_or_malformed_breaking_footer():
    for message in (
        "feat(api): change the contract\n\nBREAKING CHANGE:",
        "feat(api): change the contract\nBREAKING CHANGE: clients must migrate",
    ):
        assert any(
            "BREAKING CHANGE footer" in error
            for error in validate_commit_message(message)
        )


def test_accepts_multiple_valid_commit_subjects():
    assert validate_commit_subjects(
        [
            "feat(router): support nested route prefixes",
            "test(router): cover nested route prefixes",
        ]
    ) == []


def test_rejects_invalid_subject_in_pull_request_history():
    errors = validate_commit_subjects(
        [
            "feat(router): support nested route prefixes",
            "Update files",
        ]
    )
    assert len(errors) == 1
    assert errors[0].startswith("commit 2:")


def test_rejects_empty_pull_request_commit_list():
    assert validate_commit_subjects([]) == [
        "pull request contains no commits to validate"
    ]
