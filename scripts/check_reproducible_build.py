#!/usr/bin/env python3
"""Build wheel and sdist twice from clean copies of one Git commit and compare hashes."""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


class ReproducibilityError(RuntimeError):
    """Raised when independent builds do not produce identical artifacts."""


def artifact_hashes(directory: Path) -> dict[str, str]:
    """Return SHA-256 digests for exactly one wheel and one source archive."""
    artifacts = sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and (path.name.endswith(".whl") or path.name.endswith(".tar.gz"))
    )
    wheels = [path for path in artifacts if path.name.endswith(".whl")]
    sdists = [path for path in artifacts if path.name.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1:
        raise ReproducibilityError(
            f"Expected one wheel and one sdist in {directory}; "
            f"found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)."
        )

    digests: dict[str, str] = {}
    for artifact in artifacts:
        digest = hashlib.sha256()
        with artifact.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        digests[artifact.name] = digest.hexdigest()
    return digests


def compare_artifact_hashes(
    first: dict[str, str], second: dict[str, str]
) -> None:
    """Fail with an actionable diff when two artifact sets differ."""
    if first != second:
        names = sorted(first.keys() | second.keys())
        differences = [
            f"{name}: first={first.get(name, '<missing>')} "
            f"second={second.get(name, '<missing>')}"
            for name in names
            if first.get(name) != second.get(name)
        ]
        raise ReproducibilityError(
            "Independent package builds are not byte-for-byte reproducible:\n"
            + "\n".join(differences)
        )


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def extract_clean_source(archive_bytes: bytes, destination: Path) -> None:
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        archive.extractall(destination, filter="data")


def build_once(
    archive_bytes: bytes,
    root: Path,
    label: str,
    environment: dict[str, str],
) -> dict[str, str]:
    source = root / f"source-{label}"
    output = root / f"dist-{label}"
    extract_clean_source(archive_bytes, source)
    output.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--outdir",
            str(output),
            str(source),
        ],
        check=True,
        env=environment,
    )
    return artifact_hashes(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ref",
        default="HEAD",
        help="Git ref to build (default: HEAD)",
    )
    args = parser.parse_args()

    source_epoch = git_output("show", "-s", "--format=%ct", args.ref)
    archive_bytes = subprocess.run(
        ["git", "archive", "--format=tar", args.ref],
        check=True,
        capture_output=True,
    ).stdout

    environment = os.environ.copy()
    environment.update(
        {
            "SOURCE_DATE_EPOCH": source_epoch,
            "PYTHONHASHSEED": "0",
            "TZ": "UTC",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
        }
    )

    with tempfile.TemporaryDirectory(prefix="django-api-versioning-repro-") as temp:
        root = Path(temp)
        first = build_once(archive_bytes, root, "one", environment)
        second = build_once(archive_bytes, root, "two", environment)
        compare_artifact_hashes(first, second)

    print("PASS: independent clean builds are byte-for-byte reproducible.")
    for name, digest in sorted(first.items()):
        print(f"  sha256  {digest}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
