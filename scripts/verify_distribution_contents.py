#!/usr/bin/env python3
"""Fail a release build if repository-only assets leak into PyPI artifacts.

Usage: python scripts/verify_distribution_contents.py [dist-directory]
"""
from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

FORBIDDEN_PARTS = {
    "website",
    "docs",
    "integration_test_project",
    ".github",
    ".claude",
    "node_modules",
    ".astro",
    ".netlify",
}
PACKAGE_PREFIX = "django_api_versioning/"


def normalized_parts(name: str) -> tuple[str, ...]:
    return tuple(part for part in PurePosixPath(name).parts if part not in ("", "."))


def assert_no_repository_assets(names: list[str], artifact: Path) -> None:
    leaked = []
    for name in names:
        parts = normalized_parts(name)
        if FORBIDDEN_PARTS.intersection(parts):
            leaked.append(name)
    if leaked:
        sample = "\n".join(f"  - {name}" for name in leaked[:30])
        raise SystemExit(
            f"{artifact.name} contains repository-only files that must not ship:\n{sample}"
        )


def check_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    assert_no_repository_assets(names, path)
    if not any(name == f"{PACKAGE_PREFIX}__init__.py" for name in names):
        raise SystemExit(f"{path.name} does not contain {PACKAGE_PREFIX}__init__.py")
    unexpected = [
        name
        for name in names
        if name and not name.startswith(PACKAGE_PREFIX) and ".dist-info/" not in name
    ]
    if unexpected:
        sample = "\n".join(f"  - {name}" for name in unexpected[:30])
        raise SystemExit(f"{path.name} contains unexpected top-level files:\n{sample}")
    print(f"PASS {path.name}: package files and dist-info only ({len(names)} entries)")


def check_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = [member.name for member in archive.getmembers() if member.isfile()]
    assert_no_repository_assets(names, path)
    if not any(name.endswith(f"/{PACKAGE_PREFIX}__init__.py") for name in names):
        raise SystemExit(f"{path.name} does not contain the Python package")
    required = ("README.md", "LICENSE", "pyproject.toml", "MANIFEST.in")
    missing = [
        filename
        for filename in required
        if not any(name.endswith("/" + filename) for name in names)
    ]
    if missing:
        raise SystemExit(f"{path.name} is missing expected source files: {', '.join(missing)}")
    print(f"PASS {path.name}: source package present; repository-only trees excluded ({len(names)} files)")


def main() -> int:
    dist_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist")
    if not dist_dir.is_dir():
        raise SystemExit(f"Distribution directory does not exist: {dist_dir}")

    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit(
            "Expected exactly one wheel and one .tar.gz sdist; "
            f"found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)."
        )

    check_wheel(wheels[0])
    check_sdist(sdists[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
