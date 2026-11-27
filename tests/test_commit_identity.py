"""Tests for commit author identity and attribution policy."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "check_commit_identity.py"
)
spec = importlib.util.spec_from_file_location("check_commit_identity", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)  # type: ignore[union-attr]


def commit(
    name: str,
    email: str,
    login: str | None,
    account_type: str | None = "User",
    message: str = "feat: add behavior",
    committer_login: str | None = None,
    committer_type: str | None = None,
) -> dict:
    return {
        "sha": "a" * 40,
        "commit": {
            "author": {"name": name, "email": email},
            "committer": {"name": "web-flow", "email": "noreply@github.com"},
            "message": message,
        },
        "author": {"login": login, "type": account_type} if login else None,
        "committer": (
            {"login": committer_login, "type": committer_type}
            if committer_login
            else None
        ),
    }


def pr(body: str = "", labels: list[str] | None = None) -> dict:
    return {"body": body, "labels": [{"name": label} for label in (labels or [])]}


def test_accepts_verified_maintainer_identity_for_declared_ai_work() -> None:
    item = commit(module.NAME, module.EMAIL, module.MAINTAINER_LOGIN, "User")
    assert module.validate(pr(module.MARKER), [item]) == []


def test_rejects_wrong_name_for_maintainer_account() -> None:
    item = commit("Mojtaba", module.EMAIL, module.MAINTAINER_LOGIN)
    assert any(
        "maintainer account must use" in error
        for error in module.validate(pr(), [item])
    )


def test_rejects_wrong_email_for_maintainer_account() -> None:
    item = commit(module.NAME, "wrong@example.org", module.MAINTAINER_LOGIN)
    assert any(
        "maintainer account must use" in error
        for error in module.validate(pr(), [item])
    )


def test_rejects_maintainer_email_attributed_to_another_account() -> None:
    item = commit(module.NAME, module.EMAIL, "someone-else")
    assert any(
        "must resolve to" in error for error in module.validate(pr(), [item])
    )


def test_preserves_and_accepts_external_human_contributor_identity() -> None:
    item = commit("External Contributor", "external@example.org", "contributor")
    assert module.validate(pr(), [item]) == []
    assert item["commit"]["author"] == {
        "name": "External Contributor",
        "email": "external@example.org",
    }


@pytest.mark.parametrize(
    ("name", "email", "login", "account_type"),
    [
        ("Copilot", "copilot@example.org", "copilot[bot]", "Bot"),
        ("Claude Code", "claude@example.org", None, None),
        ("OpenAI Agent", "agent@example.org", None, None),
        ("Renovate", "renovate@example.org", "renovate[bot]", "Bot"),
        ("Assistant Bot", "assistant@example.org", None, None),
    ],
)
def test_rejects_bot_and_agent_authors(name, email, login, account_type) -> None:
    item = commit(name, email, login, account_type)
    assert any(
        "bot/agent author rejected" in error
        for error in module.validate(pr(), [item])
    )


def test_preserves_human_names_that_overlap_ai_product_names() -> None:
    for name in ("Claude Martin", "Cursor Smith", "Gemini Patel"):
        item = commit(name, "human@example.org", "human-contributor")
        assert module.validate(pr(), [item]) == []


def test_human_author_with_web_flow_committer_remains_human() -> None:
    item = commit(
        "External Contributor",
        "external@example.org",
        "contributor",
        committer_login="web-flow",
        committer_type="Bot",
    )
    assert module.validate(pr(), [item]) == []


def test_rejects_bot_coauthor_trailer_case_insensitively() -> None:
    message = (
        "feat: add behavior\n\n"
        "  cO-aUtHoReD-bY: Copilot <copilot[bot]@users.noreply.github.com>"
    )
    item = commit(
        "External Contributor", "external@example.org", "contributor", message=message
    )
    assert any(
        "Co-authored-by trailer rejected" in error
        for error in module.validate(pr(), [item])
    )


def test_allows_human_coauthor_trailer() -> None:
    message = "feat: add behavior\n\nCo-authored-by: Another Human <human@example.org>"
    item = commit(
        "External Contributor", "external@example.org", "contributor", message=message
    )
    assert module.validate(pr(), [item]) == []


def automation_commit(login: str = "github-actions[bot]") -> dict:
    name, email = module.AUTOMATION_IDENTITIES[login]
    item = commit(name, email, login, "Bot")
    item["commit"]["committer"] = {"name": name, "email": email}
    item["committer"] = {"login": login, "type": "Bot"}
    return item


@pytest.mark.parametrize("login", ["github-actions[bot]", "dependabot[bot]"])
def test_allows_only_canonical_automation_author_with_explicit_label(login) -> None:
    item = automation_commit(login)
    assert module.validate(pr(labels=[module.AUTO_LABEL]), [item]) == []


def test_rejects_automation_without_explicit_label() -> None:
    item = automation_commit()
    assert any(
        "bot/agent author rejected" in error
        for error in module.validate(pr(), [item])
    )


def test_rejects_automation_with_a_different_committer() -> None:
    item = automation_commit()
    item["commit"]["committer"] = {
        "name": "web-flow",
        "email": "noreply@github.com",
    }
    item["committer"] = {"login": "web-flow", "type": "Bot"}
    assert any(
        "bot/agent author rejected" in error
        for error in module.validate(pr(labels=[module.AUTO_LABEL]), [item])
    )


def test_automation_label_does_not_allow_noncanonical_bot_identity() -> None:
    item = commit(
        "github-actions[bot]", "wrong@example.org", "github-actions[bot]", "Bot"
    )
    assert any(
        "bot/agent author rejected" in error
        for error in module.validate(pr(labels=[module.AUTO_LABEL]), [item])
    )


def test_automation_label_does_not_allow_unlisted_bot_account() -> None:
    item = commit("renovate[bot]", "renovate@example.org", "renovate[bot]", "Bot")
    assert any(
        "bot/agent author rejected" in error
        for error in module.validate(pr(labels=[module.AUTO_LABEL]), [item])
    )


def test_automation_exception_never_allows_bot_coauthor_trailer() -> None:
    item = automation_commit()
    item["commit"]["message"] += (
        "\n\nCo-authored-by: Copilot <copilot[bot]@users.noreply.github.com>"
    )
    assert any(
        "Co-authored-by trailer rejected" in error
        for error in module.validate(pr(labels=[module.AUTO_LABEL]), [item])
    )


def test_marker_requires_a_maintainer_authored_commit() -> None:
    item = commit("External Contributor", "external@example.org", "contributor")
    assert any(
        "requires at least one commit"
        in error
        for error in module.validate(pr(module.MARKER), [item])
    )


@pytest.mark.parametrize(
    ("name", "email"),
    [("", "human@example.org"), ("Human", "")],
)
def test_rejects_missing_author_metadata(name, email) -> None:
    item = commit(name, email, "human")
    assert any(
        "missing author name/email" in error
        for error in module.validate(pr(), [item])
    )


def test_does_not_misclassify_gpt_as_part_of_an_ordinary_word() -> None:
    assert not module.is_bot("Egyptian Developer", "egypt@example.org")
