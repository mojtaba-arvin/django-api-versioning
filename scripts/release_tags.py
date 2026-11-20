#!/usr/bin/env python3
"""Safely create or resume an annotated Git release tag.

Git's own remote transport is the source of truth for tag existence and type.
The GitHub REST API is intentionally not used here: a transient/API-context
mismatch must never turn an absent remote tag into a false lightweight-tag
error or trigger an unsafe overwrite.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass


class ReleaseTagError(RuntimeError):
    """A release tag cannot be safely created or resumed."""


@dataclass(frozen=True)
class RemoteTag:
    """A tag ref as advertised by git ls-remote --tags."""

    object_sha: str
    peeled_sha: str | None


def parse_remote_tags(output: str, tag: str) -> RemoteTag | None:
    """Parse only the exact tag and peeled-tag refs from git ls-remote.

    Annotated tags advertise both refs/tags/<tag> (the tag object) and
    refs/tags/<tag>^{} (the peeled target). Lightweight tags advertise only
    the direct ref. Similar prefixes, such as v1.3.0-rc1, are ignored.
    """
    ref_name = f"refs/tags/{tag}"
    object_sha: str | None = None
    peeled_sha: str | None = None

    for line in output.splitlines():
        fields = line.split()
        if len(fields) != 2:
            raise ReleaseTagError(
                f"Unexpected git ls-remote output while checking {tag!r}: {line!r}"
            )
        sha, advertised_ref = fields
        if not re.fullmatch(r"[0-9a-f]{40,64}", sha):
            raise ReleaseTagError(
                f"Invalid object ID in git ls-remote output for {tag!r}: {sha!r}"
            )
        if advertised_ref == ref_name:
            if object_sha is not None and object_sha != sha:
                raise ReleaseTagError(
                    f"Remote advertised multiple objects for tag {tag}."
                )
            object_sha = sha
        elif advertised_ref == f"{ref_name}^{{}}":
            if peeled_sha is not None and peeled_sha != sha:
                raise ReleaseTagError(
                    f"Remote advertised multiple peeled objects for tag {tag}."
                )
            peeled_sha = sha

    if object_sha is None:
        if peeled_sha is not None:
            raise ReleaseTagError(
                f"Remote returned a peeled ref for {tag} without its tag ref."
            )
        return None
    return RemoteTag(object_sha=object_sha, peeled_sha=peeled_sha)


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise ReleaseTagError(
            f"git {' '.join(args)} failed (exit {completed.returncode})"
            + (f": {detail}" if detail else ".")
        )
    return completed.stdout.strip()


def _ref_exists(ref: str) -> bool:
    completed = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", ref],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    detail = (completed.stderr or completed.stdout).strip()
    raise ReleaseTagError(
        f"Could not inspect local Git ref {ref}"
        + (f": {detail}" if detail else ".")
    )


def _canonical_repository(url: str) -> str | None:
    normalized = url.strip().rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]

    prefixes = (
        "https://github.com/",
        "git@github.com:",
        "ssh://git@github.com/",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return normalized[len(prefix) :].lower()
    return None


def verify_origin_urls(repository: str) -> None:
    """Reject fetch/push URL mismatches and non-canonical repositories."""
    fetch_urls = _git("remote", "get-url", "--all", "origin").splitlines()
    push_urls = _git("remote", "get-url", "--push", "--all", "origin").splitlines()

    if len(fetch_urls) != 1 or len(push_urls) != 1:
        raise ReleaseTagError(
            "origin must resolve to exactly one fetch URL and one push URL; "
            "multiple URLs are unsafe for a package release."
        )

    expected = repository.lower()
    fetch_repository = _canonical_repository(fetch_urls[0])
    push_repository = _canonical_repository(push_urls[0])
    if fetch_repository != expected:
        raise ReleaseTagError(
            f"origin fetch URL {fetch_urls[0]!r} is not the canonical "
            f"repository {repository}."
        )
    if push_repository != expected:
        raise ReleaseTagError(
            f"origin push URL {push_urls[0]!r} is not the canonical "
            f"repository {repository}. Check remote.origin.pushurl."
        )


def _local_tag_state(tag: str, expected_commit: str) -> str | None:
    local_ref = f"refs/tags/{tag}"
    if not _ref_exists(local_ref):
        return None

    object_type = _git("cat-file", "-t", local_ref)
    if object_type != "tag":
        raise ReleaseTagError(
            f"Local {tag} is lightweight; refusing to publish or overwrite it."
        )

    target_commit = _git("rev-parse", "--verify", f"{local_ref}^{{commit}}")
    if target_commit != expected_commit:
        raise ReleaseTagError(
            f"Local {tag} points to {target_commit}, not current main "
            f"{expected_commit}."
        )
    return _git("rev-parse", local_ref)


def _verify_remote_tag_object(
    tag: str, remote_tag: RemoteTag, expected_commit: str
) -> None:
    """Fetch a remote tag to a temporary ref and verify its actual Git object."""
    temporary_ref = f"refs/release-verification/{tag}"
    if _ref_exists(temporary_ref):
        raise ReleaseTagError(
            f"Temporary verification ref {temporary_ref} already exists; "
            "remove the stale ref and retry."
        )

    try:
        _git(
            "fetch",
            "--no-tags",
            "origin",
            f"refs/tags/{tag}:{temporary_ref}",
        )
        fetched_object_sha = _git("rev-parse", temporary_ref)
        object_type = _git("cat-file", "-t", temporary_ref)
        if object_type != "tag":
            raise ReleaseTagError(
                f"Remote {tag} is lightweight (Git reports object type "
                f"{object_type!r}); refusing to publish or overwrite it."
            )
        if fetched_object_sha != remote_tag.object_sha:
            raise ReleaseTagError(
                f"Remote {tag} changed while it was being inspected; retry "
                "the release command."
            )

        try:
            target_commit = _git(
                "rev-parse", "--verify", f"{temporary_ref}^{{commit}}"
            )
        except ReleaseTagError as exc:
            raise ReleaseTagError(
                f"Remote {tag} is annotated but does not ultimately point to "
                f"a commit: {exc}"
            ) from exc

        if target_commit != remote_tag.peeled_sha:
            raise ReleaseTagError(
                f"Remote {tag} changed while it was being inspected; retry "
                "the release command."
            )
        if target_commit != expected_commit:
            raise ReleaseTagError(
                f"Remote {tag} points to {target_commit}, not current main "
                f"{expected_commit}."
            )
    finally:
        subprocess.run(
            ["git", "update-ref", "-d", temporary_ref],
            check=False,
            capture_output=True,
            text=True,
        )


def ensure_release_tag(tag: str, expected_commit: str, repository: str) -> None:
    """Create/push a missing annotated tag or safely resume an existing one."""
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[.-][0-9A-Za-z.-]+)?", tag):
        raise ReleaseTagError(f"Invalid release tag: {tag!r}.")
    if not re.fullmatch(r"[0-9a-f]{40,64}", expected_commit):
        raise ReleaseTagError(f"Invalid expected commit SHA: {expected_commit!r}.")

    verify_origin_urls(repository)

    # One Git transport read is authoritative for whether the remote tag
    # exists. No REST API response or swallowed 404 is allowed to override it.
    remote_tags = _git("ls-remote", "--tags", "origin")
    remote_tag = parse_remote_tags(remote_tags, tag)
    local_ref = f"refs/tags/{tag}"

    if remote_tag is not None:
        if remote_tag.peeled_sha is None:
            raise ReleaseTagError(
                f"Remote {tag} is lightweight (no peeled tag object was "
                "advertised); refusing to publish or overwrite it."
            )

        _verify_remote_tag_object(tag, remote_tag, expected_commit)
        local_object_sha = _local_tag_state(tag, expected_commit)
        if local_object_sha is None:
            _git(
                "fetch",
                "--no-tags",
                "origin",
                f"refs/tags/{tag}:{local_ref}",
            )
            local_object_sha = _local_tag_state(tag, expected_commit)

        if local_object_sha != remote_tag.object_sha:
            raise ReleaseTagError(
                f"Local {tag} and remote {tag} are different annotated tag "
                "objects, even though their target commit may match. "
                "Inspect both refs before retrying."
            )
        print(f"Existing remote tag {tag} is annotated and targets current main.")
        return

    local_object_sha = _local_tag_state(tag, expected_commit)
    if local_object_sha is None:
        print(f"Remote tag {tag} is absent; creating an annotated local tag.")
        _git("tag", "-a", tag, "-m", f"Release {tag}")
        local_object_sha = _git("rev-parse", local_ref)
    else:
        print(f"Reusing existing local annotated tag {tag}.")

    try:
        _git("push", "origin", f"{local_ref}:{local_ref}")
    except ReleaseTagError as exc:
        raise ReleaseTagError(
            f"Could not push {tag}. Check the protected v* tag ruleset and "
            "GitHub permissions; no PyPI publication was started. "
            f"{exc}"
        ) from exc

    # Verify the exact remote tag object after push. A successful push alone
    # is not treated as proof that the expected tag is now advertised.
    pushed_remote = parse_remote_tags(_git("ls-remote", "--tags", "origin"), tag)
    if pushed_remote is None or pushed_remote.peeled_sha != expected_commit:
        raise ReleaseTagError(
            f"Push of {tag} returned successfully, but the remote does not "
            "advertise the expected annotated tag and commit. No PyPI "
            "publication was started; rerun make release to inspect/resume."
        )
    if pushed_remote.object_sha != local_object_sha:
        raise ReleaseTagError(
            f"Remote {tag} does not match the local annotated tag object "
            "after push. No PyPI publication was started."
        )
    print(f"Annotated tag {tag} was pushed and verified on origin.")


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: release_tags.py <tag> <commit-sha> <owner/repository>",
            file=sys.stderr,
        )
        return 2

    try:
        ensure_release_tag(sys.argv[1], sys.argv[2], sys.argv[3])
    except ReleaseTagError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
