# Versioned OpenAPI contract example

This executable consumer project uses the public VersionedRouter API and the
same URLconf for runtime requests and drf-spectacular schema generation.

The V1-only `legacy/export/` action is explicitly removed from V2. The verifier checks that it remains available and present in the V1 schema, while returning 404 and disappearing from the V2 schema.

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
checks serializer fields, compares two generations byte-for-byte, and requires
the output to match the committed per-version snapshots. CI then runs oasdiff
against each matching baseline. A deliberate fixture check confirms that an
optional response field is accepted while removing an operation is rejected.

You can also generate a schema directly:

~~~bash
python manage.py spectacular --api-version 1 --validate --file /tmp/openapi-v1.yaml
python manage.py spectacular --api-version 2 --validate --file /tmp/openapi-v2.yaml
~~~

To deliberately propose a new contract baseline after reviewing the generated
diff, run this from the example directory:

~~~bash
python generate_schemas.py --output-dir schemas
git diff -- schemas/
python verify.py
~~~

Do not refresh a baseline merely to make CI green. Review the API change,
classify it as additive or breaking, and update the migration/release notes
before committing the snapshot.

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

The committed schemas under schemas/v1/ and schemas/v2/ are the example's
reviewed contract baselines. The verifier refuses unreviewed drift. Pull
requests generate candidate schemas in a temporary directory and compare each
version with its matching baseline using oasdiff breaking.

Schema diffs, route-matrix checks, and request-level behavior tests are separate
gates. Neither drf-spectacular nor oasdiff is a runtime dependency.
