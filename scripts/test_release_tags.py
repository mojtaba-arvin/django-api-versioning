"""Unit tests for safe release-tag discovery and classification."""

import unittest
from unittest.mock import patch

from scripts.release_tags import (
    ReleaseTagError,
    RemoteTag,
    ensure_release_tag,
    parse_remote_tags,
    verify_origin_urls,
)


class ParseRemoteTagsTests(unittest.TestCase):
    def test_absent_tag_is_none_not_a_lightweight_tag(self):
        self.assertIsNone(
            parse_remote_tags(
                "1111111111111111111111111111111111111111 refs/tags/v1.2.2\n",
                "v1.3.0",
            )
        )

    def test_lightweight_tag_has_no_peeled_ref(self):
        tag = "v1.3.0"
        object_sha = "a" * 40
        self.assertEqual(
            parse_remote_tags(f"{object_sha} refs/tags/{tag}\n", tag),
            RemoteTag(object_sha=object_sha, peeled_sha=None),
        )

    def test_annotated_tag_has_tag_object_and_peeled_commit(self):
        tag = "v1.3.0"
        object_sha = "a" * 40
        commit_sha = "b" * 40
        output = (
            f"{object_sha} refs/tags/{tag}\n"
            f"{commit_sha} refs/tags/{tag}^{{}}\n"
        )
        self.assertEqual(
            parse_remote_tags(output, tag),
            RemoteTag(object_sha=object_sha, peeled_sha=commit_sha),
        )

    def test_similarly_prefixed_tags_do_not_match(self):
        self.assertIsNone(
            parse_remote_tags(
                "a" * 40 + " refs/tags/v1.3.0-rc1\n",
                "v1.3.0",
            )
        )

    def test_orphaned_peeled_ref_is_rejected(self):
        with self.assertRaisesRegex(ReleaseTagError, "without its tag ref"):
            parse_remote_tags(
                "b" * 40 + " refs/tags/v1.3.0^{}\n",
                "v1.3.0",
            )

    def test_malformed_ls_remote_line_is_rejected(self):
        with self.assertRaisesRegex(ReleaseTagError, "Unexpected git ls-remote"):
            parse_remote_tags("not-a-valid-ref-line", "v1.3.0")

    def test_invalid_object_id_is_rejected(self):
        with self.assertRaisesRegex(ReleaseTagError, "Invalid object ID"):
            parse_remote_tags(
                "not-a-sha refs/tags/v1.3.0\n",
                "v1.3.0",
            )

    def test_conflicting_duplicate_refs_are_rejected(self):
        with self.assertRaisesRegex(ReleaseTagError, "multiple objects"):
            parse_remote_tags(
                "a" * 40 + " refs/tags/v1.3.0\n"
                + "b" * 40 + " refs/tags/v1.3.0\n",
                "v1.3.0",
            )


class EnsureReleaseTagTests(unittest.TestCase):
    @patch("scripts.release_tags.verify_origin_urls")
    @patch("scripts.release_tags._ref_exists", return_value=False)
    @patch("scripts.release_tags._git")
    def test_absent_remote_tag_is_created_as_annotated_and_pushed(
        self, git, _ref_exists, _verify_urls
    ):
        tag = "v1.3.0"
        tag_object = "a" * 40
        commit = "b" * 40
        advertised_after_push = (
            f"{tag_object} refs/tags/{tag}\n"
            f"{commit} refs/tags/{tag}^{{}}\n"
        )
        git.side_effect = ["", "", tag_object, "", advertised_after_push]

        ensure_release_tag(tag, commit, "mojtaba-arvin/django-api-versioning")

        git.assert_any_call("tag", "-a", tag, "-m", f"Release {tag}")
        git.assert_any_call(
            "push", "origin", f"refs/tags/{tag}:refs/tags/{tag}"
        )
        self.assertEqual(git.call_count, 5)

    @patch("scripts.release_tags.verify_origin_urls")
    @patch("scripts.release_tags._ref_exists")
    @patch("scripts.release_tags._git")
    def test_existing_lightweight_remote_tag_is_never_overwritten(
        self, git, ref_exists, _verify_urls
    ):
        tag = "v1.3.0"
        git.return_value = "a" * 40 + f" refs/tags/{tag}\n"

        with self.assertRaisesRegex(ReleaseTagError, "Remote v1.3.0 is lightweight"):
            ensure_release_tag(
                tag, "b" * 40, "mojtaba-arvin/django-api-versioning"
            )

        ref_exists.assert_not_called()
        git.assert_called_once_with("ls-remote", "--tags", "origin")

    @patch("scripts.release_tags._git")
    def test_noncanonical_push_url_is_rejected(self, git):
        git.side_effect = [
            "https://github.com/mojtaba-arvin/django-api-versioning",
            "https://github.com/somewhere-else/another-repo",
        ]
        with self.assertRaisesRegex(ReleaseTagError, "origin push URL"):
            verify_origin_urls("mojtaba-arvin/django-api-versioning")


if __name__ == "__main__":
    unittest.main()
