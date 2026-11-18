"""Write versioned candidate schemas to a caller-selected directory."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
MANAGE = ROOT / "manage.py"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "contract_project.settings"

    for version in ("1", "2"):
        target = args.output_dir / f"v{version}" / "openapi.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                str(MANAGE),
                "spectacular",
                "--api-version",
                version,
                "--validate",
                "--fail-on-warn",
                "--file",
                str(target),
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
        print(f"Generated v{version}: {target}")


if __name__ == "__main__":
    main()
