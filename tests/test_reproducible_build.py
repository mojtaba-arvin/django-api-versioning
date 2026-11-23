from pathlib import Path

import pytest

from scripts.check_reproducible_build import (
    ReproducibilityError,
    artifact_hashes,
    compare_artifact_hashes,
)


def _write_artifacts(directory: Path, wheel: bytes, sdist: bytes) -> None:
    directory.mkdir()
    (directory / "package-1.0-py3-none-any.whl").write_bytes(wheel)
    (directory / "package-1.0.tar.gz").write_bytes(sdist)
    (directory / "ignored.txt").write_text("not a distribution", encoding="utf-8")


def test_artifact_hashes_include_one_wheel_and_one_sdist(tmp_path):
    output = tmp_path / "dist"
    _write_artifacts(output, b"wheel", b"source")

    result = artifact_hashes(output)

    assert set(result) == {
        "package-1.0-py3-none-any.whl",
        "package-1.0.tar.gz",
    }
    assert len(set(result.values())) == 2


def test_artifact_hashes_reject_missing_distribution(tmp_path):
    output = tmp_path / "dist"
    output.mkdir()
    (output / "package-1.0-py3-none-any.whl").write_bytes(b"wheel")

    with pytest.raises(ReproducibilityError, match="Expected one wheel and one sdist"):
        artifact_hashes(output)


def test_compare_artifact_hashes_accepts_identical_builds():
    expected = {"package.whl": "abc", "package.tar.gz": "def"}

    compare_artifact_hashes(expected, dict(expected))


def test_compare_artifact_hashes_reports_byte_differences():
    first = {"package.whl": "abc", "package.tar.gz": "def"}
    second = {"package.whl": "changed", "package.tar.gz": "def"}

    with pytest.raises(ReproducibilityError, match="not byte-for-byte reproducible"):
        compare_artifact_hashes(first, second)
