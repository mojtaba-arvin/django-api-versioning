# Skill: Manual Testing - django-api-versioning

Comprehensive manual testing procedures for the django-api-versioning package in isolated local environments.

## Overview

All project tests must be executed manually in isolated local environments. This skill defines procedures for:
- Python interpreter selection
- Isolated virtual environment setup
- Django compatibility testing
- Django REST Framework compatibility testing
- Unit test execution
- Integration test execution
- Type checking (where configured)
- Package build verification

## Environment Setup

### Python Version Selection

Required: Python 3.10+

**Available interpreters** (check which are present):
```bash
which python3.10
which python3.11
which python3.12
which python3.13
```

**Recommended approach** using `uv`:
```bash
uv python install 3.12
uv python list
```

### Create Isolated Virtual Environment

Using `uv` (recommended):
```bash
cd /path/to/django-api-versioning
uv venv --python 3.12 venv
source venv/bin/activate
```

Using standard `venv`:
```bash
python3.12 -m venv venv
source venv/bin/activate
```

**Verify activation**:
```bash
which python
python --version
```

### Install Test Dependencies

```bash
cd /path/to/django-api-versioning
pip install -e ".[dev]"
```

Or explicitly:
```bash
pip install django>=4.2 djangorestframework>=3.14
pip install pytest pytest-django pytest-cov
pip install -e .
```

**Verify installations**:
```bash
python -c "import django; print(django.VERSION)"
python -c "import rest_framework; print(rest_framework.VERSION)"
python -c "import pytest; print(pytest.__version__)"
```

## Unit Test Execution

### Run All Unit Tests

```bash
cd /path/to/django-api-versioning
pytest tests/ -v --tb=short
```

### Run Specific Test File

```bash
pytest tests/test_decorators.py -v
pytest tests/test_reverse.py -v
pytest tests/test_settings.py -v
```

### Run Specific Test Function

```bash
pytest tests/test_decorators.py::test_endpoint_decorator_basic -v
```

### Run with Coverage Report

```bash
pytest tests/ --cov=django_api_versioning --cov-report=term-missing
```

**Expected output format**:
```
======================== test session starts ========================
collected 104 items

tests/test_decorators.py::test_endpoint_basic PASSED            [10%]
tests/test_decorators.py::test_endpoint_version_range PASSED    [20%]
...
tests/test_settings.py::test_invalid_version_range FAILED       [95%]

======================== FAILURES ========================
test_settings.py::test_invalid_version_range
...

======================== short test summary info ========================
FAILED tests/test_settings.py::test_invalid_version_range

======================== 103 passed, 1 failed in 0.42s ========================
```

### Record Results

Document:
- Command executed
- Python version used
- Django version used
- Total tests collected
- Tests passed
- Tests failed
- Tests skipped
- Test duration
- Coverage percentage (if measured)

**Example record**:
```
Date: 2026-11-10
Environment:
  - Python: 3.12.16
  - Django: 6.1.3
  - pytest: 9.2.0

Command: pytest tests/ -v --cov=django_api_versioning

Results:
  - Collected: 104
  - Passed: 104
  - Failed: 0
  - Skipped: 0
  - Duration: 0.42s
  - Coverage: 94%
```

## Integration Test Execution

### Run Integration Tests

The repository includes a Django integration test project:

```bash
cd /path/to/django-api-versioning
cd integration_test_project

# Install test project dependencies
pip install -e .

# Run integration tests
pytest -v
```

Or from the main directory:
```bash
pytest integration_test_project/tests/ -v
```

### Expected Integration Test Output

```
tests/test_versioning.py::test_forward_versioning PASSED
tests/test_versioning.py::test_inheritance PASSED
tests/test_drf_apiview.py::test_drf_apiview_versioning PASSED
tests/test_drf_viewset.py::test_viewset_routing PASSED
...
======================== 222 passed in X.XXs ========================
```

### Individual Integration Test Scenarios

**Test 1: Basic Versioning**
```bash
pytest integration_test_project/tests/test_versioning.py::test_forward_versioning -v
```

**Test 2: Endpoint Inheritance**
```bash
pytest integration_test_project/tests/test_versioning.py::test_inheritance -v
```

**Test 3: DRF APIView Integration**
```bash
pytest integration_test_project/tests/test_drf_apiview.py -v
```

**Test 4: DRF ViewSet Integration**
```bash
pytest integration_test_project/tests/test_drf_viewset.py -v
```

**Test 5: URL Reversal**
```bash
pytest integration_test_project/tests/test_url_reversal.py -v
```

## Django Compatibility Testing

### Test Matrix: Django Versions

| Django Version | Python 3.10 | Python 3.11 | Python 3.12 | Status |
|---|---|---|---|---|
| 4.2 LTS | ✅ | ✅ | ✅ | Supported |
| 5.0 | ✅ | ✅ | ✅ | Supported |
| 5.1 | ✅ | ✅ | ✅ | Supported |
| 5.2 LTS | ✅ | ✅ | ✅ | Supported |
| 6.0 | ⚠️ | ✅ | ✅ | Supported |
| 6.1 | ⚠️ | ✅ | ✅ | Supported |

**Test a specific Django version**:
```bash
pip install django==5.2
pytest tests/ -v
# Record results
```

### Verify Django Integration

```bash
python -c "
from django.conf import settings
from django_api_versioning import endpoint

print('Django installed:', settings.VERSION)
print('django-api-versioning imported successfully')
"
```

## Django REST Framework Compatibility Testing

### Test with DRF Installed

```bash
pip install djangorestframework>=3.14
pytest integration_test_project/tests/test_drf_apiview.py -v
pytest integration_test_project/tests/test_drf_viewset.py -v
```

### Test without DRF (Optional Dependency)

```bash
pip uninstall djangorestframework -y
pytest tests/ -v
# Should still pass (DRF is optional)
```

### Verify DRF Integration

```bash
python -c "
from rest_framework import viewsets
from django_api_versioning import endpoint

print('DRF available:', True)
print('DRF integration works')
"
```

## Type Checking

### Run Type Checking with mypy

```bash
pip install mypy
mypy django_api_versioning/ --strict
```

**Expected**: Zero type errors for production code.

### Check Type Annotations

```bash
python -c "
import django_api_versioning
print('py.typed marker present:', hasattr(django_api_versioning, 'py.typed'))
"
```

## Package Build Verification

### Build Wheel Package

```bash
pip install build
python -m build --wheel
```

**Expected output**:
```
Successfully built django_api_versioning-0.3.1-py3-none-any.whl
```

**Verify wheel contents**:
```bash
unzip -l dist/django_api_versioning-*.whl | head -20
```

### Build Source Distribution

```bash
python -m build --sdist
```

**Expected output**:
```
Successfully built django_api_versioning-0.3.1.tar.gz
```

### Test Installation from Built Wheel

```bash
python -m venv test_venv
source test_venv/bin/activate
pip install dist/django_api_versioning-*.whl
python -c "from django_api_versioning import endpoint; print('Installation successful')"
```

## Test Output Verification Checklist

For every test execution, verify:
- [ ] Command is documented
- [ ] Environment versions recorded
- [ ] Actual test output captured
- [ ] Number of tests collected, passed, failed documented
- [ ] Coverage percentage recorded (if applicable)
- [ ] No fabricated or assumed results
- [ ] Actual errors captured (not paraphrased)

## Troubleshooting

### Python Version Not Available
```bash
# Check available versions
python3 --version
python3.10 --version
python3.11 --version
python3.12 --version

# Install using uv
uv python install 3.12
```

### Django Import Errors
```bash
# Verify Django installation
python -c "import django; print(django.VERSION)"

# Reinstall
pip install --upgrade django
```

### pytest Not Finding Tests
```bash
# Verify pytest discovers tests
pytest --collect-only

# Run from project root
cd /path/to/django-api-versioning
pytest tests/ -v
```

### Coverage Report Issues
```bash
# Install coverage
pip install pytest-cov

# Run with coverage
pytest --cov=django_api_versioning --cov-report=html
```

## Test Execution Workflow

1. **Setup isolated environment** with correct Python version
2. **Install dependencies** from pyproject.toml
3. **Run unit tests** and record results
4. **Run integration tests** and record results
5. **Test Django compatibility** by testing multiple versions
6. **Test DRF integration** if applicable
7. **Document all results** with exact commands and outputs
8. **Do NOT fabricate test results** - capture actual outputs

## When to Run Tests

- Before committing any code change
- After updating dependencies
- Before publishing a release
- When investigating a reported bug
- When verifying compatibility with new Django/Python versions
- When making architectural changes

## Never Do These Things

- ❌ Skip tests and assume they pass
- ❌ Report inflated test counts or coverage
- ❌ Invent successful results for failed tests
- ❌ Skip integration tests to save time
- ❌ Test in system-wide Python (always use virtual environment)
- ❌ Report test results without running actual commands
- ❌ Assume test results from previous sessions
