import json

import pytest

from django_api_versioning.exceptions import VersionMatrixError
from django_api_versioning.registry import registry
from django_api_versioning.testing import _diff, assert_version_matrix


def test_matrix_snapshot_created(tmp_path):
    registry.urlpatterns.clear()
    snapshot = tmp_path / "matrix.json"
    assert_version_matrix(snapshot=str(snapshot))
    assert snapshot.exists()


def test_matrix_mismatch_raises(tmp_path):
    registry.urlpatterns.clear()
    snapshot = tmp_path / "matrix.json"
    snapshot.write_text(json.dumps({"api/v1/x": {"1": "old"}}))
    with pytest.raises(VersionMatrixError):
        assert_version_matrix(snapshot=str(snapshot))


class TestDiffFormatting:
    def test_diff_unversioned_label_not_prefixed_with_v(self):
        """Ensure unversioned routes use correct label without 'v' prefix."""
        expected = {"api/health/": {"unversioned": "old_view"}}
        current = {"api/health/": {"unversioned": "new_view"}}
        diff = _diff(expected, current)

        # Should NOT contain 'vunversioned' - that's the bug
        assert "vunversioned" not in diff
        # Should contain 'unversioned' without 'v' prefix
        assert "unversioned: old_view -> new_view" in diff

    def test_diff_versioned_label_has_v_prefix(self):
        """Ensure versioned routes use 'v' prefix correctly."""
        expected = {"api/v1/users/": {"1": "old_view"}}
        current = {"api/v1/users/": {"1": "new_view"}}
        diff = _diff(expected, current)

        # Should contain 'v1' with the 'v' prefix
        assert "v1: old_view -> new_view" in diff

    def test_diff_mixed_versioned_and_unversioned(self):
        """Ensure mixed versioned and unversioned routes format correctly."""
        expected = {
            "api/v1/users/": {"1": "old_users"},
            "api/health/": {"unversioned": "old_health"},
        }
        current = {
            "api/v1/users/": {"1": "new_users"},
            "api/health/": {"unversioned": "new_health"},
        }
        diff = _diff(expected, current)

        # Check both labels appear correctly
        assert "v1: old_users -> new_users" in diff
        assert "unversioned: old_health -> new_health" in diff
        # Make sure bug (vunversioned) doesn't appear
        assert "vunversioned" not in diff

    def test_diff_no_changes_when_identical(self):
        """Ensure no diff is output when matrices are identical."""
        matrix = {"api/v1/users/": {"1": "view_func"}}
        diff = _diff(matrix, matrix)

        assert diff == ""

    def test_diff_route_missing_in_current(self):
        """Ensure missing routes are shown in diff."""
        expected = {"api/v1/users/": {"1": "old_view"}}
        current = {}
        diff = _diff(expected, current)

        assert "api/v1/users/" in diff
        assert "<missing>" in diff
