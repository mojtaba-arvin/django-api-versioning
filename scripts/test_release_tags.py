"""Unit tests for safe release-tag discovery and classification."""

import unittest

from scripts.release_tags import (
    ReleaseTagError,
    RemoteTag,
    parse_remote_tags,
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


if __name__ == "__main__":
    unittest.main()
