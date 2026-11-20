import json

import pytest
from django.views import View

from django_api_versioning.exceptions import (
    ContractSnapshotError,
    VersionMatrixError,
)
from django_api_versioning.registry import registry
from django_api_versioning.testing import (
    _diff,
    assert_version_matrix,
    assert_schema_snapshot,
    build_version_matrix,
)


def test_matrix_snapshot_created(tmp_path):
    registry.urlpatterns.clear()
    snapshot = tmp_path / "matrix.json"
    assert_version_matrix(snapshot=str(snapshot))
    assert snapshot.exists()


def test_matrix_snapshot_update_creates_non_empty_baseline(tmp_path):
    registry.urlpatterns.clear()
    registry.register("api/v1/x", lambda request: None, route_version=1)
    snapshot = tmp_path / "matrix.json"

    assert_version_matrix(snapshot=str(snapshot), update=True)

    assert json.loads(snapshot.read_text()) == {"api/v1/x": {"1": "<lambda>"}}
    assert_version_matrix(snapshot=str(snapshot), strict=True)


def test_strict_matrix_requires_existing_snapshot(tmp_path):
    registry.urlpatterns.clear()
    registry.register("api/v1/x", lambda request: None, route_version=1)
    snapshot = tmp_path / "matrix.json"

    with pytest.raises(VersionMatrixError, match="does not exist"):
        assert_version_matrix(snapshot=str(snapshot), strict=True)

    assert not snapshot.exists()


def test_strict_matrix_rejects_empty_registry(tmp_path):
    registry.urlpatterns.clear()
    snapshot = tmp_path / "matrix.json"

    with pytest.raises(VersionMatrixError, match="No endpoints are registered"):
        assert_version_matrix(snapshot=str(snapshot), strict=True)

    assert not snapshot.exists()


def test_strict_matrix_requires_snapshot_path():
    registry.urlpatterns.clear()

    with pytest.raises(VersionMatrixError, match="snapshot path is required"):
        assert_version_matrix(strict=True)


def test_matrix_without_snapshot_preserves_no_op_behavior():
    registry.urlpatterns.clear()

    assert_version_matrix() is None


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


def test_build_version_matrix_supports_callable_instances():
    class CallableView:
        def __call__(self, request):
            return None

    registry.register("api/v1/callable/", CallableView(), route_version=1)

    assert build_version_matrix() == {"api/v1/callable/": {"1": "CallableView"}}


def test_build_version_matrix_uses_class_name_for_class_based_views():
    class SampleView(View):
        def get(self, request):
            return None

    registry.register("api/v1/items/", SampleView, route_version=1)

    assert build_version_matrix() == {"api/v1/items/": {"1": "SampleView"}}


def test_schema_snapshot_is_created_and_verified(tmp_path):
    schema = {
        "openapi": "3.1.0",
        "paths": {"/api/v1/users/": {"get": {"responses": {"200": {}}}}},
    }
    snapshot = tmp_path / "contracts" / "v1.json"

    assert_schema_snapshot(schema, snapshot, update=True)
    assert snapshot.is_file()
    assert_schema_snapshot(schema, snapshot, strict=True)


def test_schema_snapshot_strict_mode_requires_a_reviewed_baseline(tmp_path):
    snapshot = tmp_path / "v1.json"

    with pytest.raises(ContractSnapshotError, match="does not exist"):
        assert_schema_snapshot({"openapi": "3.1.0"}, snapshot, strict=True)

    assert not snapshot.exists()


def test_schema_snapshot_detects_unreviewed_contract_drift(tmp_path):
    snapshot = tmp_path / "v1.json"
    assert_schema_snapshot({"openapi": "3.1.0"}, snapshot, update=True)

    with pytest.raises(ContractSnapshotError, match="differs from its reviewed"):
        assert_schema_snapshot(
            {"openapi": "3.1.0", "paths": {"/api/v1/new/": {}}},
            snapshot,
            strict=True,
        )


def test_schema_snapshot_rejects_non_mapping_input(tmp_path):
    with pytest.raises(ContractSnapshotError, match="must be a mapping"):
        assert_schema_snapshot([], tmp_path / "v1.json")
