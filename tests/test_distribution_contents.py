from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.verify_distribution_contents import check_sdist, check_wheel
from scripts.smoke_installed_wheel import digest_tree


def _write_wheel(path: Path, names: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, b"test")


def _write_sdist(path: Path, names: list[str]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name in names:
            payload = b"test"
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))


def test_wheel_accepts_package_and_dist_info_only(tmp_path: Path) -> None:
    wheel = tmp_path / "django_api_versioning-0.3.7-py3-none-any.whl"
    _write_wheel(
        wheel,
        [
            "django_api_versioning/__init__.py",
            "django_api_versioning/py.typed",
            "django_api_versioning-0.3.7.dist-info/METADATA",
        ],
    )

    check_wheel(wheel)


@pytest.mark.parametrize(
    "forbidden_path",
    [
        "website/index.html",
        "docs/articles/001-guide.md",
        "integration_test_project/manage.py",
        ".github/workflows/tests.yml",
    ],
)
def test_wheel_rejects_repository_only_assets(
    tmp_path: Path, forbidden_path: str
) -> None:
    wheel = tmp_path / "django_api_versioning-0.3.7-py3-none-any.whl"
    _write_wheel(
        wheel,
        [
            "django_api_versioning/__init__.py",
            "django_api_versioning/py.typed",
            "django_api_versioning-0.3.7.dist-info/METADATA",
            forbidden_path,
        ],
    )

    with pytest.raises(SystemExit, match="repository-only files"):
        check_wheel(wheel)


def test_wheel_requires_pep561_marker(tmp_path: Path) -> None:
    wheel = tmp_path / "django_api_versioning-0.3.7-py3-none-any.whl"
    _write_wheel(
        wheel,
        [
            "django_api_versioning/__init__.py",
            "django_api_versioning-0.3.7.dist-info/METADATA",
        ],
    )

    with pytest.raises(SystemExit, match="PEP 561 marker"):
        check_wheel(wheel)


def test_sdist_accepts_required_source_files(tmp_path: Path) -> None:
    sdist = tmp_path / "django_api_versioning-0.3.7.tar.gz"
    root = "django-api-versioning-0.3.7"
    _write_sdist(
        sdist,
        [
            f"{root}/django_api_versioning/__init__.py",
            f"{root}/django_api_versioning/py.typed",
            f"{root}/README.md",
            f"{root}/LICENSE",
            f"{root}/pyproject.toml",
            f"{root}/MANIFEST.in",
        ],
    )

    check_sdist(sdist)


def test_sdist_requires_pep561_marker(tmp_path: Path) -> None:
    sdist = tmp_path / "django_api_versioning-0.3.7.tar.gz"
    root = "django-api-versioning-0.3.7"
    _write_sdist(
        sdist,
        [
            f"{root}/django_api_versioning/__init__.py",
            f"{root}/README.md",
            f"{root}/LICENSE",
            f"{root}/pyproject.toml",
            f"{root}/MANIFEST.in",
        ],
    )

    with pytest.raises(SystemExit, match="PEP 561 marker"):
        check_sdist(sdist)


@pytest.mark.parametrize(
    "forbidden_path",
    [
        "website/src/pages/index.astro",
        "docs/articles/001-guide.md",
        "integration_test_project/test_integration.py",
        ".github/workflows/publish.yml",
    ],
)
def test_sdist_rejects_repository_only_assets(
    tmp_path: Path, forbidden_path: str
) -> None:
    sdist = tmp_path / "django_api_versioning-0.3.7.tar.gz"
    root = "django-api-versioning-0.3.7"
    _write_sdist(
        sdist,
        [
            f"{root}/django_api_versioning/__init__.py",
            f"{root}/README.md",
            f"{root}/LICENSE",
            f"{root}/pyproject.toml",
            f"{root}/MANIFEST.in",
            f"{root}/{forbidden_path}",
        ],
    )

    with pytest.raises(SystemExit, match="repository-only files"):
        check_sdist(sdist)


def test_installed_wheel_digest_includes_only_package_source_files(
    tmp_path: Path,
) -> None:
    package = tmp_path / "django_api_versioning"
    package.mkdir()
    (package / "__init__.py").write_text("VALUE = 1\\n")
    (package / "py.typed").write_text("")
    (package / "module.pyc").write_bytes(b"compiled")
    (package / "README.txt").write_text("not package code")

    assert set(digest_tree(package)) == {"__init__.py", "py.typed"}
