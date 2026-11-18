"""Verify runtime migration behavior and generated per-version contracts."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
PATHS = {
    "1": "/api/v1/orders/",
    "2": "/api/v2/orders/",
    "3": "/api/v3/orders/",
}
AVAILABILITY = {
    version: f"/api/v{version}/orders/availability/" for version in ("1", "2", "3")
}
LEGACY_EXPORT = {
    version: f"/api/v{version}/orders/legacy/export/" for version in ("1", "2", "3")
}
RISK_SUMMARY = "/api/v3/orders/{id}/risk-summary/"
RISK_SUMMARY_RUNTIME = "/api/v3/orders/101/risk-summary/"


def _setup_django():
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "consumer_migration_project.settings"
    )
    import django

    django.setup()

    from django.test import override_settings
    from rest_framework.test import APIClient

    return APIClient, override_settings


def verify_runtime() -> None:
    APIClient, override_settings = _setup_django()
    client = APIClient()

    v1 = client.get(PATHS["1"])
    assert v1.status_code == 200, v1.content
    assert v1.json()[0]["total"] == "19.95"
    assert "currency" not in v1.json()[0]
    assert v1["Deprecation"] == "@1767225600"
    assert v1["Sunset"] == "Wed, 30 Jun 2027 00:00:00 GMT"

    v2 = client.get(PATHS["2"])
    assert v2.status_code == 200, v2.content
    assert v2.json()[0]["currency"] == "USD"
    assert "fulfillment_state" not in v2.json()[0]
    assert "Deprecation" not in v2
    assert "Sunset" not in v2

    v3 = client.get(PATHS["3"])
    assert v3.status_code == 200, v3.content
    assert v3.json()[0]["currency"] == "USD"
    assert v3.json()[0]["fulfillment_state"] == "ready"
    assert "Deprecation" not in v3

    for version in ("1", "2", "3"):
        response = client.get(AVAILABILITY[version])
        assert response.status_code == 200, (version, response.content)
        assert response.json()["available"] is True

    assert client.get(LEGACY_EXPORT["1"]).status_code == 200
    assert client.get(LEGACY_EXPORT["2"]).status_code == 200
    assert client.get(LEGACY_EXPORT["3"]).status_code == 404

    assert client.get(RISK_SUMMARY_RUNTIME).status_code == 200
    assert client.get("/api/v1/orders/101/risk-summary/").status_code == 404
    assert client.get("/api/v2/orders/101/risk-summary/").status_code == 404

    # Prove the eventual retirement behavior without depending on wall-clock time.
    with override_settings(
        API_VERSION_LIFECYCLE={
            1: {"status": "retired", "sunset": "2000-01-01"},
            2: {"status": "active"},
            3: {"status": "active"},
        }
    ):
        retired = client.get(PATHS["1"])
    assert retired.status_code == 410, retired.content


def _component(document: dict, schema: dict) -> dict:
    reference = schema["$ref"]
    name = reference.rsplit("/", 1)[-1]
    return document["components"]["schemas"][name]


def _response_schema(document: dict, path: str) -> dict:
    schema = document["paths"][path]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    return schema["items"] if schema.get("type") == "array" else schema


def verify_schemas(schema_dir: Path) -> None:
    for version in ("1", "2", "3"):
        generated = schema_dir / f"v{version}" / "openapi.yaml"
        assert generated.is_file(), f"Missing generated V{version} schema: {generated}"
        document = yaml.safe_load(generated.read_text(encoding="utf-8"))

        # Each document contains only the selected API version's URL space.
        assert PATHS[version] in document["paths"]
        for other in (v for v in ("1", "2", "3") if v != version):
            assert PATHS[other] not in document["paths"]

        availability_path = AVAILABILITY[version]
        assert availability_path in document["paths"]
        assert (LEGACY_EXPORT[version] in document["paths"]) is (version != "3")
        assert (RISK_SUMMARY in document["paths"]) is (version == "3")

        order_schema = _component(document, _response_schema(document, PATHS[version]))
        properties = order_schema["properties"]
        if version == "1":
            assert properties["total"]["type"] == "string"
            assert "currency" not in properties
            assert "fulfillment_state" not in properties
        elif version == "2":
            assert properties["total"]["type"] == "string"
            assert properties["total"].get("format") == "decimal"
            assert "currency" in order_schema.get("required", [])
            assert "fulfillment_state" not in properties
        else:
            assert properties["total"]["type"] == "string"
            assert properties["total"].get("format") == "decimal"
            assert "currency" in order_schema.get("required", [])
            assert "fulfillment_state" in properties

        inherited = _component(document, _response_schema(document, availability_path))
        assert set(inherited["properties"]) == {"available", "checked_at"}

        baseline = ROOT / "schemas" / f"v{version}" / "openapi.yaml"
        assert (
            baseline.is_file()
        ), f"Missing committed V{version} baseline: {baseline}"
        assert generated.read_bytes() == baseline.read_bytes(), (
            f"Generated V{version} schema differs from the committed baseline. "
            "Review the API contract change before updating the snapshot."
        )

        # A second generation must be byte-for-byte stable.
        with tempfile.TemporaryDirectory(prefix=f"consumer-migration-v{version}-") as d:
            import subprocess
            import sys

            target = Path(d) / "openapi.yaml"
            env = os.environ.copy()
            env["DJANGO_SETTINGS_MODULE"] = "consumer_migration_project.settings"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "manage.py"),
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
                capture_output=True,
                text=True,
            )
            assert (
                generated.read_bytes() == target.read_bytes()
            ), f"V{version} schema generation is not deterministic"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-dir", type=Path, required=True)
    args = parser.parse_args()

    verify_runtime()
    verify_schemas(args.schema_dir)
    print(
        "Consumer migration contract passed: V1/V2/V3 runtime, lifecycle, "
        "inheritance, explicit V3 removal, schema assertions, and "
        "deterministic generation."
    )


if __name__ == "__main__":
    main()
