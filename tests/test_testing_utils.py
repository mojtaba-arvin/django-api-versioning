import json

import pytest

from django_api_versioning.exceptions import VersionMatrixError
from django_api_versioning.registry import registry
from django_api_versioning.testing import assert_version_matrix, build_version_matrix, _diff


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


class TestBuildVersionMatrixDeterminism:
    """Test determinism of build_version_matrix() within a single process.

    build_version_matrix() reads from registry.urlpatterns, which is populated
    by @endpoint decorators at module import time. The function is deterministic
    within a single process once all endpoints have been registered, but depends
    on imports being complete.
    """

    def test_empty_registry_returns_empty_matrix(self):
        """Verify that an empty registry produces an empty matrix."""
        registry.urlpatterns.clear()
        matrix = build_version_matrix()
        assert matrix == {}

    def test_multiple_calls_same_registry_return_identical_result(self):
        """Verify that build_version_matrix() returns identical result when called
        multiple times with the same registry state (deterministic in a single process)."""
        registry.urlpatterns.clear()

        # Create a pattern manually for testing
        from django.urls import path
        from django.http import HttpResponse

        def dummy_view(request):
            return HttpResponse()

        pattern = path("test/", dummy_view)
        setattr(pattern, registry._ROUTE_VERSION_ATTR, 1)
        registry.urlpatterns.append(pattern)

        # Call build_version_matrix multiple times
        matrix1 = build_version_matrix()
        matrix2 = build_version_matrix()
        matrix3 = build_version_matrix()

        # All should be identical
        assert matrix1 == matrix2
        assert matrix2 == matrix3

        # Clean up
        registry.urlpatterns.clear()

    def test_matrix_snapshot_remains_stable_across_calls(self):
        """Verify that the matrix content is stable - same calls produce same JSON.
        This ensures the snapshot test semantics work as expected."""
        registry.urlpatterns.clear()

        # Create multiple patterns
        from django.urls import path
        from django.http import HttpResponse

        def view_a(request):
            return HttpResponse()

        def view_b(request):
            return HttpResponse()

        pattern_a = path("users/", view_a)
        setattr(pattern_a, registry._ROUTE_VERSION_ATTR, 1)
        registry.urlpatterns.append(pattern_a)

        pattern_b = path("orders/", view_b)
        setattr(pattern_b, registry._ROUTE_VERSION_ATTR, 2)
        registry.urlpatterns.append(pattern_b)

        # Get matrix and serialize to JSON
        matrix = build_version_matrix()
        json_str1 = json.dumps(matrix, indent=2, sort_keys=True)

        # Call again and serialize
        json_str2 = json.dumps(build_version_matrix(), indent=2, sort_keys=True)

        # Serialized forms should be identical
        assert json_str1 == json_str2

        # Verify content
        assert "users/" in matrix
        assert "orders/" in matrix

        # Clean up
        registry.urlpatterns.clear()
