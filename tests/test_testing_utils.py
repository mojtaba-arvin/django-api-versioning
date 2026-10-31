import json

import pytest

from django_api_versioning.exceptions import VersionMatrixError
from django_api_versioning.registry import registry
from django_api_versioning.testing import assert_version_matrix


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
