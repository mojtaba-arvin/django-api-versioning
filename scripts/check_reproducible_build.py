#!/usr/bin/env python3
"""Build wheel and sdist twice from clean copies of one Git commit and compare hashes."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import os
import shutil
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


def normalize_sdist(path: Path, source_epoch: int) -> None:
    """Normalize tar and gzip metadata without changing source file contents."""
    normalized = io.BytesIO()
    with tarfile.open(path, mode="r:gz") as source:
        members = source.getmembers()
        with gzip.GzipFile(
            fileobj=normalized,
            mode="wb",
            filename="",
            mtime=source_epoch,
            compresslevel=9,
        ) as compressed:
            with tarfile.open(
                fileobj=compressed,
                mode="w",
                format=tarfile.PAX_FORMAT,
            ) as target:
                for original in sorted(members, key=lambda item: item.name):
                    member = copy.copy(original)
                    member.mtime = source_epoch
                    member.uid = 0
                    member.gid = 0
                    member.uname = ""
                    member.gname = ""
                    member.pax_headers = {}
                    if original.isfile():
                        content = source.extractfile(original)
                        if content is None:
                            raise ReproducibilityError(
                                f"Could not read source archive member {original.name}"
                            )
                        target.addfile(member, content)
                    else:
                        target.addfile(member)
    path.write_bytes(normalized.getvalue())


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def extract_clean_source(archive_bytes: bytes, destination: Path) -> None:
    destination.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        archive.extractall(destination, filter="data")


def build_once(
    archive_bytes: bytes,
    root: Path,
    label: str,
    environment: dict[str, str],
    source_epoch: int,
) -> Path:
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
    sdists = sorted(output.glob("*.tar.gz"))
    if len(sdists) != 1:
        raise ReproducibilityError(
            f"Expected one source archive from build {label}; found {len(sdists)}."
        )
    normalize_sdist(sdists[0], source_epoch)
    artifact_hashes(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ref",
        default="HEAD",
        help="Git ref to build (default: HEAD)",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("dist"),
        help="Directory to receive the verified artifacts (default: dist)",
    )
    args = parser.parse_args()

    source_epoch = int(git_output("show", "-s", "--format=%ct", args.ref))
    archive_bytes = subprocess.run(
        ["git", "archive", "--format=tar", args.ref],
        check=True,
        capture_output=True,
    ).stdout

    environment = os.environ.copy()
    environment.update(
        {
            "SOURCE_DATE_EPOCH": str(source_epoch),
            "PYTHONHASHSEED": "0",
            "TZ": "UTC",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
        }
    )

    with tempfile.TemporaryDirectory(prefix="django-api-versioning-repro-") as temp:
        root = Path(temp)
        first_dir = build_once(
            archive_bytes, root, "one", environment, source_epoch
        )
        second_dir = build_once(
            archive_bytes, root, "two", environment, source_epoch
        )
        first = artifact_hashes(first_dir)
        second = artifact_hashes(second_dir)
        compare_artifact_hashes(first, second)

        output = args.outdir.resolve()
        if output.exists() and any(output.iterdir()):
            raise ReproducibilityError(
                f"Output directory must be empty before verified artifacts are copied: {output}"
            )
        output.mkdir(parents=True, exist_ok=True)
        for artifact in first_dir.iterdir():
            if artifact.is_file():
                shutil.copyfile(artifact, output / artifact.name)

    print("PASS: independent clean builds are byte-for-byte reproducible.")
    for name, digest in sorted(first.items()):
        print(f"  sha256  {digest}  {name}")
    print(f"Verified artifacts copied to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
