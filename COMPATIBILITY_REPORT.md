# Django API Versioning - Compatibility Report

## Report Metadata

**Report Last Updated**: 2026-11-14 (this document)
**Package Version**: 0.3.6
**Current Repository HEAD**: febc13c (docs: audit and correct compatibility report for accuracy and evidence-based claims)
**Test Execution Status**: NOT VERIFIED — No execution logs found in working directory
**Report Purpose**: Document declared requirements, official compatibility ranges, tox configuration, and implementation features vs routing integration status

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

| Django Version | Official Python Range | Package Tests This Range |
|---|---|---|
| 4.2 | 3.8–3.12 | 3.10–3.12 only |
| 5.2 | 3.10–3.14 | 3.10–3.14 tested |
| 6.0 | 3.12–3.14 | 3.12–3.14 tested |
| 6.1 | 3.12–3.15 | 3.12–3.15 tested |

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

## Test Counts

Based on inspection of test source code:
- **Unit tests**: 176 test functions across 12 test files in `tests/`
- **Integration tests**: 245 test functions in `integration_test_project/test_integration.py`

These numbers represent the test functions defined in the source code, not the result of any particular test execution. Each test may contain parametrization or assertions that increase the count of individual assertions executed.

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

- Version lifecycle metadata (sunset dates, deprecation warnings)
- `LifecycleMiddleware` for injecting X-API-Lifecycle headers

**Status**: Fully implemented.

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

**Status**: Tested with DRF 3.18.3 for integrated endpoints. Native DRF versioning is not tested for compatibility with this package.

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
| Test execution | ❌ NOT VERIFIED | No execution logs, output files, or timestamps in repository |

---

## What Is NOT Tested or Verified

The following claims are explicitly **not** supported by evidence in this repository:

- **Operating System compatibility** — No OS-specific tests exist. The package contains no platform-specific code and uses only cross-platform Python and Django APIs, but specific OS compatibility is not verified.
- **Database compatibility** — The test suite uses SQLite in-memory databases. PostgreSQL, MySQL, MariaDB, Oracle, and other database compatibility is not verified, though the package does not include migrations or database-specific code.
- **Exact test execution results** — No logs, coverage reports, or execution timestamps are preserved in the repository to verify test execution status across all 16 environments (15 test + 1 lint).

---

## Summary

The package declares support for Python 3.10–3.15 and Django 4.2, 5.2–6.1. The tox matrix is configured to test six Python versions (3.10–3.15) against four Django versions (4.2, 5.2, 6.0, 6.1), resulting in 15 test environments plus a lint environment.

The implementation is feature-complete for path-based versioning, route registration, lifecycle management, and partial DRF integration. Helper functions exist for header and query version extraction but are not integrated into route selection.

**Test execution status cannot be verified from available repository evidence.** The tox configuration defines the intended test coverage, but actual execution results are not logged or preserved in the repository.

---

**Last Updated**: 2026-11-14
**Prepared By**: Audit and verification process
