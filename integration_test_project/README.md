# Django API Versioning - Integration Test Project

This directory contains a realistic Django test project that demonstrates and verifies the `django-api-versioning` package in a real-world scenario.

## Overview

The integration test project is a standalone Django application that uses the package to manage API versioning across multiple endpoints with different version-specific implementations.

## Project Structure

```
integration_test_project/
├── manage.py                 # Django management script
├── test_integration.py      # Integration test suite
├── README.md               # This file
├── project/               # Django project configuration
│   ├── __init__.py
│   ├── settings.py       # Django settings with API versioning config
│   └── urls.py           # URL routing (includes versioned endpoints)
└── api/                  # API application
    ├── __init__.py
    └── views.py          # Versioned endpoint implementations
```

## Endpoints Tested

### Health Check (Unversioned)
- `GET /health/` - Returns status

### User Endpoints (Versioned)
- `GET /api/v1/users/` - v1 with basic user info
- `GET /api/v2/users/` - v2 with email field
- `GET /api/v3/users/` - v3 with pagination
- `GET /api/v1/users/<id>/` - v1 user detail
- `GET /api/v2/users/<id>/` - v2 user detail with email

### Post Endpoints (Versioned)
- `GET /api/v1/posts/` - v1 with basic post info
- `GET /api/v2/posts/` - v2 with content field
- `GET /api/v1/posts/<id>/` - v1 post detail
- `GET /api/v2/posts/<id>/` - v2 post detail with content

## Running the Tests

### Prerequisites
- Python 3.10+ (tested with 3.12)
- Django 5.2+
- django-api-versioning package installed

### Execution

```bash
# From the integration_test_project directory
source ../../.venv/bin/activate
PYTHONPATH=/home/repl/django-api-versioning:$PYTHONPATH python test_integration.py
```

### Expected Output

```
Ran 11 tests in X.XXXs

OK
```

## Test Coverage

The integration test suite verifies:

1. **Unversioned Endpoints** - Health check works independently
2. **Versioned Endpoints** - Multiple versions serve correct responses
3. **Version Inheritance** - Newer versions inherit from older ones when not explicitly defined
4. **URL Reversal** - `api_reverse()` generates correct URLs for all versions
5. **URL Parameters** - Path parameters are correctly substituted in reversed URLs
6. **Registry** - Expected routes are registered in the version registry
7. **Special Characters** - URL parameters with special characters pass through correctly
8. **Forward Inheritance** - Requesting a version higher than defined serves the highest available version

## API Versioning Configuration

The project demonstrates the recommended configuration:

```python
# settings.py
API_BASE_PATH = "api/v{version}/"      # URL pattern with "v" prefix
API_MIN_VERSION = 1                      # Earliest supported version
API_MAX_VERSION = 3                      # Latest supported version
API_VERSIONING_CHANNELS = ["path"]      # Path-based versioning only
API_DEPRECATED_VERSIONS = {
    2: {
        "deprecated_date": "2026-01-01",
        "sunset_date": "2026-06-01",
    }
}
```

## Key Implementation Details

### URL Configuration
The package automatically registers versioned routes when views are decorated with `@endpoint()`. The `urls.py` only needs to:
1. Import the views to trigger decorator execution
2. Include the package's `urlpatterns` once

### View Definition
Views use the `@endpoint()` decorator to declare which version they serve:

```python
@endpoint("users/", version=1, view_name="user-list-v1")
def user_list(request):
    return JsonResponse({"version": 1, ...})

@endpoint("users/", version=2, view_name="user-list-v2")
def user_list_v2(request):
    return JsonResponse({"version": 2, ...})
```

### Forward Inheritance
When a client requests `/api/v3/users/` but only v1 and v2 are defined, v2 is served. This "forward inheritance" automatically handles version transitions.

## Test Results Summary

| Category | Status | Details |
|----------|--------|---------|
| Unversioned endpoints | ✅ Pass | Health check works |
| Versioned endpoints v1 | ✅ Pass | Correct response for v1 |
| Versioned endpoints v2 | ✅ Pass | Correct response for v2 |
| Versioned endpoints v3 | ✅ Pass | Forward inherited from v2 |
| URL reversal | ✅ Pass | Correct URLs generated |
| Parameters | ✅ Pass | Path parameters substituted |
| Registry | ✅ Pass | All routes registered |
| Special chars | ✅ Pass | Characters pass through correctly |
| Forward inheritance | ✅ Pass | Higher versions inherited |

## Compatibility Notes

- Tested with Python 3.12.16
- Tested with Django 6.1.3
- Requires django-api-versioning 0.3.0+

## Extending the Tests

To add new test cases:

1. Add new view functions with `@endpoint()` decorator in `api/views.py`
2. Add corresponding test methods in `BasicIntegrationTestCase` class
3. Update settings if additional versions or configurations are needed
4. Run the test suite to verify

## Related Documentation

- [django-api-versioning GitHub](https://github.com/mojtaba-arvin/django-api-versioning)
- [Django URL dispatcher](https://docs.djangoproject.com/en/stable/topics/http/urls/)
- [Django testing documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
