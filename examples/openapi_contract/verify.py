"""Verify runtime behavior and deterministic, version-filtered OpenAPI output."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parent
MANAGE = ROOT / "manage.py"
PRODUCT_PATHS = {"1": "/api/v1/products/", "2": "/api/v2/products/"}
ACTION_PATHS = {
    "1": "/api/v1/products/availability/",
    "2": "/api/v2/products/availability/",
}


def generate(version: str, output: Path) -> bytes:
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "contract_project.settings"
    subprocess.run(
        [sys.executable, str(MANAGE), "spectacular", "--api-version", version,
         "--validate", "--fail-on-warn", "--file", str(output)],
        cwd=ROOT, env=env, check=True,
    )
    return output.read_bytes()


def response_schema(document: dict, path: str) -> dict:
    schema = document["paths"][path]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    return schema["items"] if schema.get("type") == "array" else schema


def component(document: dict, schema: dict) -> dict:
    ref = schema["$ref"]
    name = ref.rsplit("/", 1)[-1]
    return document["components"]["schemas"][name]


def verify_runtime() -> None:
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "contract_project.settings"
    code = '''
import django
django.setup()
from rest_framework.test import APIClient

client = APIClient()
v1 = client.get("/api/v1/products/")
assert v1.status_code == 200, v1.content
assert v1.json()[0]["price"] == "12.50"
assert "currency" not in v1.json()[0]

v2 = client.get("/api/v2/products/")
assert v2.status_code == 200, v2.content
assert v2.json()[0]["currency"] == "USD"

inherited = client.get("/api/v2/products/availability/")
assert inherited.status_code == 200, inherited.content
assert inherited.json()["available"] is True
'''
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True)


def verify_schema(version: str) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"openapi-v{version}-") as directory:
        first = Path(directory) / "first.yaml"
        second = Path(directory) / "second.yaml"
        first_bytes = generate(version, first)
        second_bytes = generate(version, second)
        assert first_bytes == second_bytes, f"v{version} schema is not deterministic"

        baseline = ROOT / "schemas" / f"v{version}" / "openapi.yaml"
        assert baseline.is_file(), f"Missing released contract baseline: {baseline}"
        assert first_bytes == baseline.read_bytes(), (
            f"Generated v{version} schema differs from its committed baseline. "
            "Review the contract change and update the snapshot deliberately."
        )

        document = yaml.safe_load(first_bytes)
        product_path = PRODUCT_PATHS[version]
        action_path = ACTION_PATHS[version]
        other_version = "2" if version == "1" else "1"
        assert product_path in document["paths"]
        assert action_path in document["paths"]
        assert PRODUCT_PATHS[other_version] not in document["paths"]

        product = component(document, response_schema(document, product_path))
        fields = product["properties"]
        if version == "1":
            assert fields["price"]["type"] == "string"
            assert "currency" not in fields
        else:
            assert fields["price"]["type"] == "string"
            assert fields["price"].get("format") == "decimal"
            assert "currency" in fields
            assert "currency" in product.get("required", [])

        inherited_action = component(
            document, response_schema(document, action_path)
        )
        assert set(inherited_action["properties"]) == {"available", "checked_at"}
        return document


def main() -> None:
    verify_runtime()
    documents = {v: verify_schema(v) for v in ("1", "2")}
    print(json.dumps({
        "runtime": "passed",
        "schema_versions": sorted(documents),
        "deterministic": True,
        "version_specific_serializers": True,
        "inherited_custom_action": True,
    }, indent=2))


if __name__ == "__main__":
    main()
