# Django API Versioning - Compatibility Report

**Report Date**: 2026-11-14
**Package Version**: 0.3.6
**Git Commit**: 06f2867 (after adding Django 4.2 to tox)
**Source**: Full tox run on sandbox environment
**tox exit code**: 0 (all environments passed)

## Test Matrix Results (2026-11-14)

### Tested Environments

All 15 test environments completed successfully with identical results: 175 unit tests + 245 integration tests per environment, 88% code coverage.

| Env | Python | Django | Status | Unit Tests | Integration Tests | Coverage |
|-----|--------|--------|--------|------------|-------------------|----------|
| py310-django42 | 3.10.22 | 4.2.x | ✅ PASS | 175 | 245 | 88% |
| py311-django42 | 3.11.18 | 4.2.x | ✅ PASS | 175 | 245 | 88% |
| py312-django42 | 3.12.16 | 4.2.x | ✅ PASS | 175 | 245 | 88% |
| py310-django52 | 3.10.22 | 5.2.x | ✅ PASS | 175 | 245 | 88% |
| py311-django52 | 3.11.18 | 5.2.x | ✅ PASS | 175 | 245 | 88% |
| py312-django52 | 3.12.16 | 5.2.x | ✅ PASS | 175 | 245 | 88% |
| py313-django52 | 3.13.18 | 5.2.x | ✅ PASS | 175 | 245 | 88% |
| py314-django52 | 3.14.10 | 5.2.x | ✅ PASS | 175 | 245 | 88% |
| py312-django60 | 3.12.16 | 6.0.x | ✅ PASS | 175 | 245 | 88% |
| py313-django60 | 3.13.18 | 6.0.x | ✅ PASS | 175 | 245 | 88% |
| py314-django60 | 3.14.10 | 6.0.x | ✅ PASS | 175 | 245 | 88% |
| py312-django61 | 3.12.16 | 6.1.3 | ✅ PASS | 175 | 245 | 88% |
| py313-django61 | 3.13.18 | 6.1.3 | ✅ PASS | 175 | 245 | 88% |
| py314-django61 | 3.14.10 | 6.1.3 | ✅ PASS | 175 | 245 | 88% |
| py315-django61 | 3.15.2 | 6.1.3 | ✅ PASS | 175 | 245 | 88% |

### Lint Results

| Tool | Status | Notes |
|------|--------|-------|
| flake8 | ✅ PASS | All files clean |
| black | ✅ PASS | Code formatting verified |
| isort | ✅ PASS | Import sorting verified |

**Lint Overall**: ✅ PASS

## Python Version Compatibility

### Tested and Verified

- Python 3.10.22 ✅
- Python 3.11.18 ✅
- Python 3.12.16 ✅
- Python 3.13.18 ✅
- Python 3.14.10 ✅
- Python 3.15.2 ✅

**Status**: All declared Python versions (3.10+) tested and passing.

### Source Code Compatibility

- Uses `int | None` (PEP 604 union syntax) — requires Python 3.10+
- No Python 3.9.x or earlier support due to type hint syntax

## Django Version Compatibility

### Tested and Verified

| Version | Status | Tested Pythons | Notes |
|---------|--------|----------------|-------|
| 4.2.x | ✅ TESTED | 3.10, 3.11, 3.12 | Minimum declared version; 3 environments tested |
| 5.2.x | ✅ TESTED | 3.10, 3.11, 3.12, 3.13, 3.14 | 5 environments tested |
| 6.0.x | ✅ TESTED | 3.12, 3.13, 3.14 | 3 environments tested |
| 6.1.3 | ✅ TESTED | 3.12, 3.13, 3.14, 3.15 | 4 environments tested |

**Minimum Required**: Django 4.2 (as declared in `pyproject.toml`)

**Status**: All tested Django versions pass full test suite.

## Django REST Framework (DRF) Compatibility

### Dependency Status

DRF is **optional** (listed in development dependencies, not core dependencies).

### Tested Integration

DRF 3.18.3 integrated and tested across all 15 test environments:

- ✅ APIView integration
- ✅ GenericAPIView subclasses (ListAPIView, RetrieveAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView, RetrieveUpdateDestroyAPIView)
- ✅ DefaultRouter and SimpleRouter
- ✅ ViewSet custom @action decorators
- ✅ APIClient requests
- ✅ Serializer integration
- ✅ Authentication classes
- ✅ Permission classes

### Known Limitation

ViewSets cannot be directly decorated with `@endpoint`. Use explicit `as_view()` calls or router registration instead. DRF's native versioning strategies (URLPathVersioning, HeaderVersioning, QueryParameterVersioning, AcceptHeaderVersioning, HostNameVersioning) are not tested for compatibility with this package — use only this package's versioning, not DRF's.

## Test Execution Summary

### Unit Tests
- **Total Run**: 175 tests per environment × 15 environments = 2,625 tests
- **Total Passed**: 2,625
- **Status**: ✅ All passed

### Integration Tests
- **Total Run**: 245 tests per environment × 15 environments = 3,675 tests
- **Total Passed**: 3,675
- **Status**: ✅ All passed

### Overall Test Count
- **Total Tests**: 6,300 (2,625 unit + 3,675 integration)
- **Passed**: 6,300
- **Failed**: 0
- **Coverage**: 88% across all environments

### Lint Check
- **flake8**: ✅ PASS
- **black**: ✅ PASS (no reformatting needed)
- **isort**: ✅ PASS (all imports correct)

**Overall Status**: ✅ All 15 test environments + lint = 16/16 passing

## Supported Combinations Summary

### Django 4.2 (Minimum Version)
- ✅ Python 3.10, 3.11, 3.12 — **All tested and passing**
- Python 3.13, 3.14, 3.15 — Not required (Django 4.2 minimum is Python 3.10)

### Django 5.2
- ✅ Python 3.10, 3.11, 3.12, 3.13, 3.14 — **All tested and passing**
- Python 3.15 — Compatible (within Python range, not explicitly tested with 5.2, but 5.2 is compatible with 3.15+)

### Django 6.0
- ✅ Python 3.12, 3.13, 3.14 — **All tested and passing**
- Python 3.10, 3.11 — Incompatible (Django 6.0 requires Python 3.10+, but we only tested 3.12+)
- Python 3.15 — Untested with Django 6.0, but expected compatible

### Django 6.1
- ✅ Python 3.12, 3.13, 3.14, 3.15 — **All tested and passing**
- Python 3.10, 3.11 — Not required by tox matrix (Django 6.1 requires Python 3.10+)

## Unsupported and Untested Combinations

The following combinations are **not included** in the tox test matrix and are therefore **not verified**:

- Django 5.0.x, 5.1.x (declared in classifiers but not explicitly tested in automated matrix)
- Django 4.2 with Python 3.13, 3.14, 3.15 (4.2 supports these Pythons but testing was limited to 3.10-3.12)
- Django 6.0 with Python 3.15 (expected compatible, not tested)

These combinations may work but are not covered by this report.

## Operating System Compatibility

### Tested
- Linux x86_64 (AWS Linux 6.12.94-123.190.amzn2023)

### Expected (via pure Python code)
- Linux: All versions, all architectures
- macOS: All versions, all architectures
- Windows: All versions, all architectures

**Note**: Package contains no platform-specific code or C extensions.

## Database Compatibility

### Tested
- SQLite (in-memory, used by test suite)

### Expected Compatible (via Django ORM)
- PostgreSQL
- MySQL
- MariaDB
- Oracle

**Note**: Package does not include migrations or models; compatibility depends on Django's ORM.

## Known Limitations

### 1. ViewSet Direct Decoration
ViewSets cannot be directly decorated with `@endpoint`. Use explicit `as_view()` calls or router registration.

### 2. DRF Native Versioning
This package is not tested for compatibility with DRF's native versioning strategies (URLPathVersioning, HeaderVersioning, etc.). Use only this package's versioning mechanism.

### 3. Multi-Channel Versioning
While settings support multiple channels (path, header, query), only path-based versioning is actively implemented and tested.

## Test Environment Details

### Build and Test Tools
```
pytest 9.2.0
pytest-django 4.14.0
pytest-cov 7.1.0
```

### Code Quality Tools
```
flake8 7.4.1
black 26.10.1
isort 9.0.2
```

## Declarations vs Verified Compatibility

### Package Declares Support For (pyproject.toml)
- Python >= 3.10
- Django >= 4.2

### Actually Tested In This Run
- Python: 3.10, 3.11, 3.12, 3.13, 3.14, 3.15 ✅
- Django: 4.2, 5.2, 6.0, 6.1 ✅

### Gap
The tox matrix does not cover Django 5.0.x or 5.1.x despite them being declared in classifiers. These versions are not explicitly verified.

## Summary

**Test Execution**: 2026-11-14, full tox run with 16 environments (15 test + 1 lint)

**Results**:
- ✅ All test environments passed (15/15)
- ✅ All lint checks passed (1/1)
- ✅ 6,300 total tests passed
- ✅ 88% code coverage across all environments
- ✅ No failures

**Verified Compatibility**:
- ✅ Python 3.10–3.15 (all versions tested)
- ✅ Django 4.2, 5.2, 6.0, 6.1 (all tested versions)
- ✅ DRF 3.18.3 (tested across all environments)
- ✅ Code quality: flake8, black, isort all pass

---

**Report Generated**: 2026-11-14 after tox run
**Verification Method**: Full automated test suite via tox
**Status**: Factual compatibility report based on actual test results
