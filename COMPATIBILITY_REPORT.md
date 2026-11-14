# Django API Versioning - Compatibility Report

## Report Metadata

**Report Last Updated**: 2026-11-14
**Package Version**: 0.3.6
**Audited Branch**: `audit/comprehensive-package-review`
**Audited Source Revision**: `bb8e512a1ea89cc1eccdc4c5c27b8c93b7d0b9be`
**Recorded Test Run**: 2026-11-14, source commit `06f2867`
**Recorded Test Result**: tox exit code 0; 15 test environments and 1 lint environment passed
**Evidence Qualification**: The test results are recorded in the project compatibility report. Raw per-environment execution logs are not retained in the repository.
**Report Purpose**: Document declared requirements, official compatibility ranges, configured test environments, recorded test results, and implementation boundaries.

---

## Package Requirements

The package declares the following requirements:

| Component | Declared Requirement |
|-----------|---------------------|
| Python | >= 3.10 |
| Django | >= 4.2 |
| DRF | Optional (development dependency only) |

**Type Annotations**: Uses PEP 604 union syntax (`int | None`), which requires Python 3.10+. No support for Python 3.9 or earlier.

---

## Official Django/Python Compatibility Ranges

The following ranges are based on official Django documentation and represent the combinations officially supported by Django itself:

| Django Version | Official Python Range | Configured tox Python Versions |
| --- | --- | --- |
| 4.2 | 3.8–3.12 | 3.10–3.12 |
| 5.2 | 3.10–3.14 | 3.10–3.14 |
| 6.0 | 3.12–3.14 | 3.12–3.14 |
| 6.1 | 3.12–3.15 | 3.12–3.15 |

**Note**: Django 4.2 supports Python 3.8–3.12 officially, but this package requires Python >= 3.10. The package does not test Django 4.2 with Python 3.8–3.9 because the minimum declared requirement (Python 3.10) excludes them. Django 5.0 and 5.1 are not declared as supported by this package.

---

## Configured Test Matrix (tox.ini)

The following test environments are defined in `tox.ini` and represent what has been explicitly configured for testing:

### Django 4.2 Environments
- py310-django42 (Python 3.10.x with Django 4.2.x)
- py311-django42 (Python 3.11.x with Django 4.2.x)
- py312-django42 (Python 3.12.x with Django 4.2.x)

### Django 5.2 Environments
- py310-django52 (Python 3.10.x with Django 5.2.x)
- py311-django52 (Python 3.11.x with Django 5.2.x)
- py312-django52 (Python 3.12.x with Django 5.2.x)
- py313-django52 (Python 3.13.x with Django 5.2.x)
- py314-django52 (Python 3.14.x with Django 5.2.x)

### Django 6.0 Environments
- py312-django60 (Python 3.12.x with Django 6.0.x)
- py313-django60 (Python 3.13.x with Django 6.0.x)
- py314-django60 (Python 3.14.x with Django 6.0.x)

### Django 6.1 Environments
- py312-django61 (Python 3.12.x with Django 6.1.x)
- py313-django61 (Python 3.13.x with Django 6.1.x)
- py314-django61 (Python 3.14.x with Django 6.1.x)
- py315-django61 (Python 3.15.x with Django 6.1.x)

### Lint Environment
- lint (flake8, black, isort checks)

**Total**: 15 test environments + 1 lint environment = 16 configured

---

## Test Counts and Execution Evidence

Based on inspection of test source code:

- **Unit tests**: 176 test functions across 12 test files in `tests/`
- **Integration tests**: 245 test functions in `integration_test_project/test_integration.py`

These numbers represent test functions defined in the source code. They are not execution results.

The recorded 2026-11-14 tox run reports the following results for each test environment:

- **Unit tests**: 175 passed
- **Integration tests**: 245 passed
- **Code coverage**: 88%

The source-level unit test function count and the reported unit test execution count differ by one. The repository does not preserve the detailed pytest collection, skip, or deselection output needed to reconcile this difference.

The v0.3.6 CHANGELOG separately reports 160 unit tests and 236 integration tests during release verification. Those figures describe an earlier release verification record and must not be combined with the later tox matrix results.

The recorded tox run completed with exit code 0 across 15 test environments and one lint environment. Raw per-environment execution logs are not retained in the repository, so the historical results cannot be independently reproduced from committed logs alone.

---

## Implementation Features

### Version Extraction (Implemented)

The `extract_version()` function in `django_api_versioning/channels.py` provides helper functions to extract version information from multiple sources:

- **Path-based**: `_from_path()` — extracts version from `request.resolver_match.kwargs["version"]` or `request.version` attribute
- **Header-based**: `_from_header()` — extracts from `Accept-Version` header
- **Query-based**: `_from_query()` — extracts from `?version=` query parameter

**Status**: Implemented as helper functions.
**Usage in Routing**: NOT integrated into the route registry. The registry uses only path-based versioning (the `{version}` placeholder in `API_BASE_PATH`).

### Settings Configuration (Validated)

The package validates the following configuration options but does not currently use them for route selection:

- **`API_VERSIONING_CHANNELS`** — Validated list of channel names (path, header, query); not currently used by the route registry
- **`API_EFFECTIVE_VERSION_RESOLVER`** — Validated callable; not currently used for route selection

**Status**: Configuration is validated for correctness. Implementation hooks exist but are not active for routing.

### Route Registration and Versioning (Implemented and Tested)

The `@endpoint` decorator and `UrlRegistry` provide:

- Automatic URL pattern generation with version interpolation
- Forward segment inheritance (a view registered for version N serves versions N through `API_MAX_VERSION` unless overridden)
- Path-based version routing (`api/v{version}/...` pattern)
- Support for path converters (`<int:pk>`, `<slug:name>`, etc.)
- Logical endpoint grouping for validation

**Status**: Fully implemented and integrated with Django URL routing.

### Lifecycle Management (Implemented)

- Version lifecycle metadata through `API_VERSION_LIFECYCLE`
- `LifecycleMiddleware` for version-level deprecation and sunset handling
- `Deprecation: true` response header for deprecated versions
- `Sunset` response header when a sunset date is configured
- `410 Gone` response when the configured sunset date has passed

**Status**: Implemented. The middleware emits the legacy boolean value
`Deprecation: true`, not the date-valued Structured Field defined by RFC 9745.
It does not automatically generate migration or successor-version Link headers.

### Management Command (Implemented)

- `check_versions` — displays the registered version matrix for inspection

**Status**: Implemented.

### Django REST Framework Integration (Partial)

**Supported**:
- APIView-based endpoints
- GenericAPIView subclasses (ListAPIView, RetrieveAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView, etc.)
- DRF routers (DefaultRouter, SimpleRouter)
- ViewSet action decorators (@action)
- APIClient for testing
- Serializers
- Authentication and Permission classes

**Not Supported**:
- Direct decoration of ViewSet classes with `@endpoint` — use explicit `as_view()` calls or router registration
- Combination with DRF's native versioning strategies (URLPathVersioning, HeaderVersioning, QueryParameterVersioning, AcceptHeaderVersioning, HostNameVersioning)

**Status**: DRF integration was included in the recorded 2026-11-14 tox run, which reports DRF 3.18.3 as the resolved version.

The `tox.ini` configuration does not pin DRF to an exact version. It installs DRF as a development dependency without an exact version constraint, so later executions may resolve a different release.

The repository does not preserve per-environment dependency-resolution logs needed to independently confirm the resolved DRF version for every historical environment.

Compatibility with DRF's native versioning strategies has not been established by the available test evidence.

---

## Django and Python Compatibility Summary

### Declared Support
The package declares support for:
- Python 3.10, 3.11, 3.12, 3.13, 3.14, 3.15 (via classifiers)
- Django 4.2, 5.2, 6.0, 6.1 (via classifiers)

### Configured Testing Coverage
The tox matrix configures testing for:
- Python: 3.10, 3.11, 3.12, 3.13, 3.14, 3.15
- Django: 4.2, 5.2, 6.0, 6.1

### Note on Django 5.0 and 5.1
Django 5.0 and 5.1 are not declared as supported by this package. The tox matrix includes Django 5.2 as the earliest Django 5.x release supported.

---

## Code Quality Tooling

The package is configured for use with:

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | 9.2.0+ | Unit and integration testing |
| pytest-django | 4.14.0+ | Django integration for pytest |
| pytest-cov | 7.1.0+ | Code coverage measurement |
| flake8 | 7.4.1+ | PEP 8 style checking |
| black | 26.10.1+ | Code formatting |
| isort | 9.0.2+ | Import sorting |

These tools are configured in `pyproject.toml` and are part of the development dependencies.

---

## Known Limitations

### 1. ViewSet Direct Decoration
ViewSets cannot be directly decorated with `@endpoint`. Use explicit `as_view()` calls or router registration instead.

### 2. DRF Native Versioning Not Tested
This package is not tested for compatibility with DRF's native versioning strategies. If your application requires both package-based routing AND DRF's request.version, configure DRF versioning separately and manage version injection at the request level.

### 3. Header and Query Version Extraction Not Integrated
While helper functions exist to extract version from headers and query parameters, they are not integrated into the route registry. The registry uses only path-based versioning. To use header or query versioning, custom middleware or application logic is required.

---

## Verification Status by Component

| Component | Status | Evidence |
|-----------|--------|----------|
| Source code syntax | ✅ Valid | Inspected Python source files |
| PEP 604 type hints | ✅ Requires Python 3.10+ | Present in `channels.py`, `settings.py`, `registry.py` |
| Test count | ✅ 176 unit + 245 integration | Counted `def test_` functions in source |
| tox configuration | ✅ 15 test + 1 lint environments | Inspected `tox.ini` |
| Implementation features | ✅ Verified | Inspected source code for channels, registry, decorators, lifecycle |
| Routing integration | ✅ Path-based only | Confirmed in `registry.py` and `channels.py` usage patterns |
| DRF integration | ⚠️ Partial (no native versioning) | Noted in README and reflected in code inspection |
| Test execution | ⚠️ Historically reported | The 2026-11-14 tox report records 15 passing test environments and 1 passing lint environment; raw per-environment logs are not retained |

---

## What Is NOT Tested or Verified

The following claims are explicitly **not** supported by evidence in this repository:

- **Operating System compatibility** — No OS-specific tests exist. The package contains no platform-specific code and uses only cross-platform Python and Django APIs, but specific OS compatibility is not verified.
- **Database compatibility** — The test suite uses SQLite in-memory databases. PostgreSQL, MySQL, MariaDB, Oracle, and other database compatibility is not verified, though the package does not include migrations or database-specific code.
- **Independent reproduction of historical test results** — The project records a successful 2026-11-14 tox run across 15 test environments and one lint environment. However, raw per-environment logs and dependency-resolution records are not preserved, so those historical results cannot be independently reproduced from the repository alone.

---

## Summary

The package declares support for Python 3.10–3.15 and Django 4.2, 5.2, 6.0, and 6.1.

The tox matrix configures six Python versions across four Django versions, resulting in 15 test environments plus one lint environment.

The recorded 2026-11-14 tox run reports:

- All 15 test environments passed.
- The lint environment passed.
- 175 unit tests and 245 integration tests passed in each test environment.
- 88% code coverage was reported.
- The tox process exited with code 0.

The recorded run identifies DRF 3.18.3 as the resolved version. However, DRF is not pinned to an exact version in `tox.ini`, so future executions may resolve a different release.

The v0.3.6 CHANGELOG reports an earlier release verification result of 160 unit tests and 236 integration tests. These figures represent a different test-suite snapshot from the later tox run.

The source-level test function counts are 176 unit functions and 245 integration functions. These are definitions in the repository, not execution counts.

The implementation provides path-based versioned route registration, forward segment inheritance, lifecycle management, and partial DRF integration. Header and query version extraction helpers exist but are not integrated into route selection.

**Evidence limitation:** The successful historical tox run is recorded by the project, but raw per-environment logs and resolved dependency records are not retained for independent reproduction.

---

**Last Updated**: 2026-11-14
**Prepared By**: Audit and verification process
