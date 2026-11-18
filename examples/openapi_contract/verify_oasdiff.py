"""Exercise oasdiff with a safe additive change and a deliberate breaking change."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oasdiff", type=Path, default=Path("oasdiff"))
    parser.add_argument("--schema-dir", type=Path, required=True)
    args = parser.parse_args()

    base_path = args.schema_dir / "v1" / "openapi.yaml"
    base = yaml.safe_load(base_path.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="oasdiff-contract-") as directory:
        root = Path(directory)
        additive_path = root / "additive.yaml"
        breaking_path = root / "breaking.yaml"

        additive = yaml.safe_load(yaml.safe_dump(base, sort_keys=False))
        product = additive["components"]["schemas"]["ProductV1"]
        product["properties"]["optional_note"] = {
            "type": "string",
            "description": "An additive optional response field.",
        }
        additive_path.write_text(
            yaml.safe_dump(additive, sort_keys=False), encoding="utf-8"
        )

        breaking = yaml.safe_load(yaml.safe_dump(base, sort_keys=False))
        del breaking["paths"]["/api/v1/products/"]
        breaking_path.write_text(
            yaml.safe_dump(breaking, sort_keys=False), encoding="utf-8"
        )

        additive_result = subprocess.run(
            [
                str(args.oasdiff),
                "breaking",
                "--fail-on",
                "ERR",
                str(base_path),
                str(additive_path),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if additive_result.returncode != 0:
            raise SystemExit(
                "oasdiff rejected an additive optional response field:\n"
                + additive_result.stdout
                + additive_result.stderr
            )

        breaking_result = subprocess.run(
            [
                str(args.oasdiff),
                "breaking",
                "--fail-on",
                "ERR",
                str(base_path),
                str(breaking_path),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if breaking_result.returncode != 1:
            raise SystemExit(
                "oasdiff did not reject a deliberately removed operation "
                f"(exit={breaking_result.returncode}):\n"
                + breaking_result.stdout
                + breaking_result.stderr
            )

        print("oasdiff accepted an additive optional response field.")
        print("oasdiff rejected a deliberately removed API operation.")


if __name__ == "__main__":
    main()
