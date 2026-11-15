# Django API Versioning - Integration Test Project

This directory contains the repository's existing Django integration project and the executable scenarios used to verify package behavior and generate Segment Lab evidence.

## Purpose and boundaries

The integration project exercises `django-api-versioning` through real Django URL configuration and request handling. It is also reused by the Segment Lab evidence harness.

Keep this project as the single integration-test project. Do not create a parallel top-level Django project or duplicate its settings, URL configuration, API views, or package source.

## Current structure

```text
integration_test_project/
├── manage.py
├── pytest.ini
├── test_integration.py
├── test_segment_lab_generator.py
├── project/
│   ├── settings.py
│   └── urls.py
├── api/
│   ├── nested_urls.py
│   └── views.py
└── segment_lab/
    ├── README.md
    ├── generate_routes.py
    ├── probe.py
    ├── scenario_catalog.py
    ├── settings.py
    ├── urls.py
    ├── test_generator.py
    └── scenarios/
```

The Segment Lab contains 18 executable scenarios. Its detailed operating instructions, provenance rules, and evidence-generation commands are documented in [`segment_lab/README.md`](segment_lab/README.md).

## Run the integration tests

From the repository root, install the CI/test dependencies if they are not already available, then run:

```bash
python -m pytest --capture=no -c integration_test_project/pytest.ini integration_test_project
```

This runs the integration project and its Segment Lab generator tests using the repository's pytest configuration. Do not rely on historical test counts or copied terminal output as current evidence; use the actual test run.

## What the integration coverage verifies

The integration tests exercise package behavior through Django, including:

- Unversioned and versioned endpoint registration.
- Version-specific route resolution and forward segment registration.
- URL reversal and named path parameters.
- Route registry behavior and collision/ordering cases.
- DRF integration boundaries, including router/ViewSet behavior where covered by the executable scenarios.

The exact supported behavior is defined by the package source, tests, and [canonical versioning contract](../docs/reference/versioning-contract.md). This README is an operational overview, not an independent specification.

## Evidence generation

Use the existing Segment Lab generator; do not hand-edit generated route evidence or command output.

From the repository root:

```bash
python integration_test_project/segment_lab/generate_routes.py
python integration_test_project/segment_lab/generate_routes.py --check
```

The generator's README explains its clean-checkout requirements, source commit pinning, package/version metadata, hashes, and scenario provenance. The historical Netlify Agent output was produced against package 0.3.5 and must not be reused as evidence for the current package.

## Related documentation

- [Segment Lab operating guide](segment_lab/README.md)
- [Canonical package behavior contract](../docs/reference/versioning-contract.md)
- [Repository README](../README.md)
