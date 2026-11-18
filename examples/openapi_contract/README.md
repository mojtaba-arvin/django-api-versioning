# Versioned OpenAPI contract example

This executable consumer project uses the public VersionedRouter API and the
same URLconf for runtime requests and drf-spectacular schema generation.

It deliberately tests:
- V1 and V2 implementations for the same list/detail routes.
- Different serializer contracts for the two versions.
- A V1-only custom action inherited by V2 because V2 does not redeclare it.

## Install

From the repository root:

~~~bash
python -m pip install -e ".[dev]"
python -m pip install -r examples/openapi_contract/requirements.txt
~~~

The example pins drf-spectacular 0.30.0. Its upstream project recommends
pinning the generator and reviewing schema diffs when upgrading.

## Verify

~~~bash
cd examples/openapi_contract
python verify.py
~~~

The verifier makes real API requests, generates each schema in a fresh Django
process, validates OpenAPI, fails on schema warnings, checks version isolation,
checks the serializer fields, and compares two generations byte-for-byte.

You can also generate a schema directly:

~~~bash
python manage.py spectacular --api-version 1 --validate --file /tmp/openapi-v1.yaml
python manage.py spectacular --api-version 2 --validate --file /tmp/openapi-v2.yaml
~~~

## Why VersionedRouterVersioning subclasses NamespaceVersioning

drf-spectacular explicitly recognizes DRF URLPathVersioning, NamespaceVersioning,
and AcceptHeaderVersioning when filtering operations by API version. A custom
class that only subclasses BaseVersioning is not recognized by that logic.

VersionedRouterVersioning obtains the active version from the resolver namespace
created by VersionedRouter. Subclassing NamespaceVersioning makes that contract
visible to schema tooling while preserving the package's namespace parsing and
reversal behavior. It does not change the public URL format or add a runtime
dependency on drf-spectacular.

## Released contract and breaking-change CI

This verifier proves schema generation and determinism; it does not silently
create or update released baselines. After reviewing the generated output,
commit immutable snapshots per stable API version. Pull requests should generate
candidate schemas without overwriting those baselines and compare each version
with its matching baseline using oasdiff breaking.

Schema diffs, route-matrix checks, and request-level behavior tests are separate
gates. Neither drf-spectacular nor oasdiff is a runtime dependency.
