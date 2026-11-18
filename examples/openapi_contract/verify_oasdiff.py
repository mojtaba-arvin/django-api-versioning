"""Verify oasdiff's compatibility policy against focused OpenAPI fixtures."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml


def _document(
    openapi: str, property_schema: dict[str, Any], direction: str
) -> dict[str, Any]:
    payload = {
        "type": "object",
        "properties": {"value": property_schema},
    }
    response_payload = (
        payload
        if direction == "response"
        else {"type": "object", "properties": {"value": {"type": "string"}}}
    )
    operation: dict[str, Any] = {
        "responses": {
            "200": {
                "description": "OK",
                "content": {"application/json": {"schema": response_payload}},
            }
        }
    }
    if direction == "request":
        operation["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": payload}},
        }
    return {
        "openapi": openapi,
        "info": {"title": "Nullability fixture", "version": "1.0.0"},
        "paths": {"/test/": {"post": operation}},
        "components": {
            "schemas": {
                "Scalar": {"type": "string"},
            }
        },
    }


def _write(document: dict[str, Any], path: Path) -> None:
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _run(
    binary: Path,
    base: Path,
    revision: Path,
    *,
    flatten_allof: bool = False,
    severity_levels: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [str(binary), "breaking", "--fail-on", "WARN"]
    if flatten_allof:
        command.append("--flatten-allof")
    if severity_levels is not None:
        command.extend(["--severity-levels", str(severity_levels)])
    command.extend([str(base), str(revision)])
    return subprocess.run(command, text=True, capture_output=True, check=False)


def _assert_case(
    binary: Path,
    root: Path,
    name: str,
    *,
    openapi: str,
    before: dict[str, Any],
    after: dict[str, Any],
    direction: str,
    expected_exit: int,
    expected_check: str | None = None,
    flatten_allof: bool = False,
) -> None:
    case_dir = root / name
    case_dir.mkdir()
    base_path = case_dir / "base.yaml"
    revision_path = case_dir / "revision.yaml"
    _write(_document(openapi, before, direction), base_path)
    _write(_document(openapi, after, direction), revision_path)

    result = _run(
        binary,
        base_path,
        revision_path,
        flatten_allof=flatten_allof,
    )
    output = result.stdout + result.stderr
    if result.returncode != expected_exit:
        raise SystemExit(
            f"{name}: expected exit {expected_exit}, got {result.returncode}:\n{output}"
        )
    if expected_check is not None and expected_check not in output:
        raise SystemExit(
            f"{name}: expected check {expected_check!r} in oasdiff output:\n{output}"
        )


def _nullable_31() -> dict[str, Any]:
    return {"type": ["string", "null"]}


def _nonnull_31() -> dict[str, Any]:
    return {"type": "string"}


def _nullable_oneof() -> dict[str, Any]:
    return {"oneOf": [{"type": "string"}, {"type": "null"}]}


def _nullable_anyof() -> dict[str, Any]:
    return {"anyOf": [{"type": "string"}, {"type": "null"}]}


def _nullable_allof_30() -> dict[str, Any]:
    return {
        "type": "string",
        "nullable": True,
        "allOf": [{"$ref": "#/components/schemas/Scalar"}],
    }


def _nonnull_allof_30() -> dict[str, Any]:
    return {
        "type": "string",
        "allOf": [{"$ref": "#/components/schemas/Scalar"}],
    }


def verify_nullability(binary: Path, root: Path) -> None:
    # OpenAPI 3.0 nullable:true -> non-nullable.
    _assert_case(
        binary, root, "oas30-request-became-nonnullable",
        openapi="3.0.3", before={"type": "string", "nullable": True},
        after={"type": "string"}, direction="request", expected_exit=1,
        expected_check="request-property-became-not-nullable",
    )
    _assert_case(
        binary, root, "oas30-response-became-nonnullable",
        openapi="3.0.3", before={"type": "string", "nullable": True},
        after={"type": "string"}, direction="response", expected_exit=0,
    )

    # OpenAPI 3.1 type unions: narrowing requests is breaking; narrowing
    # responses is not. Widening responses is breaking; widening requests is not.
    _assert_case(
        binary, root, "oas31-request-became-nonnullable",
        openapi="3.1.0", before=_nullable_31(), after=_nonnull_31(),
        direction="request", expected_exit=1,
        expected_check="request-property-became-not-nullable",
    )
    _assert_case(
        binary, root, "oas31-response-became-nonnullable",
        openapi="3.1.0", before=_nullable_31(), after=_nonnull_31(),
        direction="response", expected_exit=0,
    )
    _assert_case(
        binary, root, "oas31-request-became-nullable",
        openapi="3.1.0", before=_nonnull_31(), after=_nullable_31(),
        direction="request", expected_exit=0,
    )
    _assert_case(
        binary, root, "oas31-response-became-nullable",
        openapi="3.1.0", before=_nonnull_31(), after=_nullable_31(),
        direction="response", expected_exit=1,
        expected_check="response-property-became-nullable",
    )

    # Composition forms. The pure oneOf wrapper is intentionally kept to
    # oasdiff's documented two-branch recognition contract.
    composition_cases = (
        (
            "oneof",
            _nullable_oneof(),
            "request-property-became-not-nullable",
            "response-property-became-nullable",
        ),
        (
            "anyof",
            _nullable_anyof(),
            "request-property-list-of-types-narrowed",
            "response-property-list-of-types-widened",
        ),
    )
    for name, nullable, request_check, response_check in composition_cases:
        _assert_case(
            binary, root, f"{name}-request-became-nonnullable",
            openapi="3.1.0", before=nullable, after=_nonnull_31(),
            direction="request", expected_exit=1,
            expected_check=request_check,
        )
        _assert_case(
            binary, root, f"{name}-response-became-nullable",
            openapi="3.1.0", before=_nonnull_31(), after=nullable,
            direction="response", expected_exit=1,
            expected_check=response_check,
        )

    # v1.38.0 specifically fixed nullable:true next to an allOf/$ref when
    # allOf flattening is enabled. Exercise that exact regression surface.
    _assert_case(
        binary, root, "allof-request-became-nonnullable",
        openapi="3.0.3", before=_nullable_allof_30(),
        after=_nonnull_allof_30(), direction="request", expected_exit=1,
        expected_check="request-property-became-not-nullable",
        flatten_allof=True,
    )


def verify_warn_policy(binary: Path, root: Path) -> None:
    # A request becoming nullable is normally INFO. Promote that known rule
    # to WARN in a fixture to prove that --fail-on WARN actually blocks WARN
    # findings, rather than merely documenting the intended policy.
    case_dir = root / "warn-policy"
    case_dir.mkdir()
    base_path = case_dir / "base.yaml"
    revision_path = case_dir / "revision.yaml"
    severity_path = case_dir / "severity-levels.txt"
    _write(_document("3.1.0", _nonnull_31(), "request"), base_path)
    _write(_document("3.1.0", _nullable_31(), "request"), revision_path)
    severity_path.write_text(
        "request-property-became-nullable warn\n", encoding="utf-8"
    )

    result = _run(
        binary,
        base_path,
        revision_path,
        severity_levels=severity_path,
    )
    output = result.stdout + result.stderr
    if result.returncode != 1 or "request-property-became-nullable" not in output:
        raise SystemExit(
            "WARN policy fixture did not fail as required by --fail-on WARN:\n"
            + output
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oasdiff", type=Path, default=Path("oasdiff"))
    parser.add_argument("--schema-dir", type=Path, required=True)
    args = parser.parse_args()

    base_path = args.schema_dir / "v1" / "openapi.yaml"
    base = yaml.safe_load(base_path.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="oasdiff-contract-") as directory:
        root = Path(directory)

        additive = yaml.safe_load(yaml.safe_dump(base, sort_keys=False))
        product = additive["components"]["schemas"]["ProductV1"]
        product["properties"]["optional_note"] = {
            "type": "string",
            "description": "An additive optional response field.",
        }
        additive_path = root / "additive.yaml"
        _write(additive, additive_path)

        breaking = yaml.safe_load(yaml.safe_dump(base, sort_keys=False))
        del breaking["paths"]["/api/v1/products/"]
        breaking_path = root / "breaking.yaml"
        _write(breaking, breaking_path)

        additive_result = _run(args.oasdiff, base_path, additive_path)
        if additive_result.returncode != 0:
            raise SystemExit(
                "oasdiff rejected an additive optional response field:\n"
                + additive_result.stdout
                + additive_result.stderr
            )

        breaking_result = _run(args.oasdiff, base_path, breaking_path)
        if breaking_result.returncode != 1:
            raise SystemExit(
                "oasdiff did not reject a deliberately removed operation "
                f"(exit={breaking_result.returncode}):\n"
                + breaking_result.stdout
                + breaking_result.stderr
            )

        verify_nullability(args.oasdiff, root)
        verify_warn_policy(args.oasdiff, root)

    print("oasdiff accepted an additive optional response field.")
    print("oasdiff rejected a deliberately removed API operation.")
    print("oasdiff nullability direction and composition fixtures passed.")
    print("oasdiff WARN findings are enforced by the CI failure policy.")


if __name__ == "__main__":
    main()
