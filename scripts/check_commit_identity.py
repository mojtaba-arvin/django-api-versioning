#!/usr/bin/env python3
"""Validate commit authors and co-author trailers for a GitHub pull request."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

NAME = "Mojtaba Arvin"
EMAIL = "m.arvin@live.com"
MAINTAINER_LOGIN = "mojtaba-arvin"
MARKER = "<!-- maintainer-directed-ai-work -->"
AUTO_LABEL = "allow-automation-commits"
AUTOMATION_IDENTITIES = {
    "github-actions[bot]": (
        "github-actions[bot]",
        "41898282+github-actions[bot]@users.noreply.github.com",
    ),
    "dependabot[bot]": (
        "dependabot[bot]",
        "49699333+dependabot[bot]@users.noreply.github.com",
    ),
}
BOT_MARKERS = (
    "[bot]",
    "ai agent",
    "ai-agent",
    "agent bot",
    "assistant bot",
    "ai assistant",
    "github actions",
    "dependabot",
    "renovate",
    "copilot",
    "claude code",
    "cursor agent",
    "windsurf",
    "codex cli",
    "openai codex",
    "chatgpt",
    "gemini cli",
    "openai agent",
    "openai assistant",
    "openai codex",
    "gpt",
)


def _contains_marker(value, marker):
    if marker in {"gpt", "openai"}:
        pattern = r"(?<![a-z0-9])" + re.escape(marker) + r"(?![a-z0-9])"
        return re.search(pattern, value) is not None
    return marker in value


def is_bot(name, email, login=None, account_type=None):
    """Identify known bot/agent labels without matching ordinary substrings."""
    if (account_type or "").lower() == "bot":
        return True
    if login and login.lower().endswith("[bot]"):
        return True
    value = (name + " " + email + " " + (login or "")).lower()
    return any(_contains_marker(value, marker) for marker in BOT_MARKERS)


def _is_allowed_automation(item, allow_automation):
    """Allow only explicitly labelled commits with canonical GitHub bot authors."""
    if not allow_automation:
        return False
    author = item.get("author") or {}
    login = author.get("login")
    expected = AUTOMATION_IDENTITIES.get(login)
    if expected is None or author.get("type") != "Bot":
        return False
    commit = item.get("commit") or {}
    commit_author = commit.get("author") or {}
    commit_committer = commit.get("committer") or {}
    github_committer = item.get("committer") or {}
    expected_name, expected_email = expected
    return (
        github_committer.get("login") == login
        and github_committer.get("type") == "Bot"
        and commit_author.get("name") == expected_name
        and (commit_author.get("email") or "").lower() == expected_email.lower()
        and commit_committer.get("name") == expected_name
        and (commit_committer.get("email") or "").lower() == expected_email.lower()
    )


def validate(pr, commits):
    """Return policy violations for a PR and its complete commit list."""
    errors = []
    labels = {x.get("name", "") for x in pr.get("labels", [])}
    allow_automation = AUTO_LABEL in labels
    maintainer_work = MARKER in (pr.get("body") or "")
    maintainer_commit_seen = False

    for item in commits:
        commit = item.get("commit") or {}
        author = commit.get("author") or {}
        github_author = item.get("author") or {}
        name = author.get("name") or ""
        email = author.get("email") or ""
        login = github_author.get("login")
        account_type = github_author.get("type")
        sha = (item.get("sha") or "unknown")[:12]

        if not name or not email:
            errors.append(sha + ": missing author name/email")

        allowed_automation = _is_allowed_automation(item, allow_automation)
        if is_bot(name, email, login, account_type) and not allowed_automation:
            errors.append(
                f"{sha}: bot/agent author rejected: {name!r} <{email}> "
                f"login={login!r}"
            )

        if login == MAINTAINER_LOGIN:
            maintainer_commit_seen = True
            if name != NAME or email.lower() != EMAIL.lower():
                errors.append(
                    f"{sha}: maintainer account must use {NAME} <{EMAIL}>, "
                    f"got {name!r} <{email}>"
                )
        elif email.lower() == EMAIL.lower():
            errors.append(
                f"{sha}: maintainer email must resolve to {MAINTAINER_LOGIN}, "
                f"not {login!r}"
            )

        for line in (commit.get("message") or "").splitlines():
            trailer = line.strip()
            if trailer.lower().startswith("co-authored-by:"):
                identity = trailer.split(":", 1)[1].strip()
                if is_bot(identity, ""):
                    errors.append(
                        f"{sha}: bot/AI Co-authored-by trailer rejected: {identity!r}"
                    )

    if maintainer_work and not maintainer_commit_seen:
        errors.append(
            "maintainer-directed AI work marker requires at least one commit "
            f"authored by {MAINTAINER_LOGIN}"
        )
    return errors


def get_json(url, token):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "commit-identity-policy-check",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def self_test():
    """Small standard-library smoke suite; detailed cases live in pytest."""

    def item(name, email, login, account_type, message="feat: test"):
        return {
            "sha": "a" * 40,
            "commit": {
                "author": {"name": name, "email": email},
                "committer": {"name": "web-flow", "email": "noreply@github.com"},
                "message": message,
            },
            "author": {"login": login, "type": account_type},
            "committer": {"login": "web-flow", "type": "Bot"},
        }

    human = item(NAME, EMAIL, MAINTAINER_LOGIN, "User")
    assert not validate({"body": MARKER, "labels": []}, [human])
    external = item("External Human", "x@example.org", "human", "User")
    assert not validate({"body": "", "labels": []}, [external])
    copilot = item("Copilot", "bot@example.org", "copilot[bot]", "Bot")
    assert validate({"body": "", "labels": []}, [copilot])
    bot_trailer = (
        "feat: test\n"
        "Co-authored-by: Copilot <copilot[bot]@users.noreply.github.com>"
    )
    assert validate(
        {"body": "", "labels": []},
        [item("Human", "h@example.org", "human", "User", bot_trailer)],
    )
    github_actions = item(
        "github-actions[bot]",
        "41898282+github-actions[bot]@users.noreply.github.com",
        "github-actions[bot]",
        "Bot",
    )
    github_actions["commit"]["committer"] = github_actions["commit"]["author"]
    github_actions["committer"] = {"login": "github-actions[bot]", "type": "Bot"}
    assert validate({"body": "", "labels": []}, [github_actions])
    assert not validate(
        {"body": "", "labels": [{"name": AUTO_LABEL}]}, [github_actions]
    )
    assert validate({"body": MARKER, "labels": []}, [external])
    print("PASS: commit identity policy self-tests")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument(
        "--pr-number", type=int, default=int(os.getenv("PR_NUMBER", "0"))
    )
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
    if not (args.repository and args.pr_number and args.token):
        if args.self_test and not args.pr_number:
            return 0
        parser.error("--repository, --pr-number and --token are required")

    base = "https://api.github.com/repos/" + args.repository
    pr = get_json(base + "/pulls/" + str(args.pr_number), args.token)
    commits = []
    page = 1
    while True:
        batch = get_json(
            base + f"/pulls/{args.pr_number}/commits?per_page=100&page={page}",
            args.token,
        )
        if not isinstance(batch, list):
            raise RuntimeError("GitHub API returned a non-list commit response")
        commits.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    if not commits:
        print("ERROR: empty PR commit list; refusing to pass")
        return 2

    errors = validate(pr, commits)
    print(f"Checked {len(commits)} commits in {args.repository}#{args.pr_number}")
    if errors:
        print("\n".join("ERROR: " + error for error in errors))
        return 1
    print("PASS: no prohibited bot/agent authors or co-author trailers")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as error:
        print(f"ERROR: GitHub API HTTP {error.code}: {error.reason}", file=sys.stderr)
        sys.exit(2)
    except (urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as error:
        print(f"ERROR: identity validation incomplete: {error}", file=sys.stderr)
        sys.exit(2)
