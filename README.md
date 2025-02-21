# Django API Versioning

[![PyPI version](https://badge.fury.io/py/django-api-versioning.svg)](https://badge.fury.io/py/django-api-versioning)
[![Build Status](https://github.com/mojtaba-arvin/django-api-versioning/actions/workflows/tests.yml/badge.svg)](https://github.com/mojtaba-arvin/django-api-versioning/actions)
[![codecov](https://codecov.io/gh/mojtaba-arvin/django-api-versioning/branch/main/graph/badge.svg)](https://codecov.io/gh/mojtaba-arvin/django-api-versioning)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Django API Versioning** is a powerful and flexible library for managing [API versioning in Django](https://github.com/mojtaba-arvin/django-api-versioning) projects. It allows you to easily define and manage different versions of your API endpoints using decorators, ensuring backward compatibility and clean code organization.

## Features

- **Easy Versioning**: Define API versions using simple decorators.
- **Backward Compatibility**: Automatically register routes for all versions up to the specified version.
- **Automatic Registration:** Views are **automatically** registered for each version specified, so there is no need to manually register each version in your `urls.py`.
- **Customizable Settings**: Configure API base path, minimum and maximum versions, and more.
- **Type Checking**: Full support for type hints and static type checking with `mypy`.
- **Testing Ready**: Includes comprehensive test suite and pre-commit hooks for code quality.

## Installation

You can [install Django API Versioning](https://pypi.org/project/django-api-versioning/) via pip:

```bash
pip install django-api-versioning
```

## Quick Start

1. ### Add to Django Settings:

```python
INSTALLED_APPS = [
    ...
    'django_api_versioning',
    ...
]
```

2. ### Define API Settings:

```python

API_BASE_PATH = "api/v{version}/"
API_MIN_VERSION = 1
API_MAX_VERSION = 3
```

3. ### Register API urls:

if you don't use any `ROOT_URLCONF` in settings you can use this:

```python
ROOT_URLCONF = 'django_api_versioning.urls'
```

or you have already have a `ROOT_URLCONF` in settings, you only need to import them into your root `urls.py`:

```python
   from django.urls import path, include
   from django_api_versioning.urls import urlpatterns as api_urlpatterns

   urlpatterns = [
       # other paths here

       # use empty `route` param and use `API_BASE_PATH` in settings as prefix
       path('', include(api_urlpatterns)),
   ]

```

3. ### Use the Decorator:

The `endpoint` decorator can be used in both function-based views (FBVs) and class-based views (CBVs). It's also fully compatible with `Django Rest Framework (DRF)`. The decorator allows you to define versioning for your API views and supports backward compatibility by default and you don't need to pass `backward=True` flag to the `endpoint` decorator.

#### Example for Function-Based Views (FBVs):

```python
from django_api_versioning.decorators import endpoint
from django.http import HttpResponse

@endpoint("users", version=2, app_name='account_app', view_name="users_list_api")
def users_view(request):
    return HttpResponse("API Version 2 Users")
```

In this example, the `users_view` function is decorated with the endpoint decorator. This specifies that the view is accessible under version `2` of the API and **supports backward compatibility**. The `backward=True` flag as default ensures that users can also access the previous version (version `1`) at `/api/v1/account_app/users`.

#### Example for Class-Based Views (CBVs):

For class-based views, you can apply the decorator to methods such as `get`, `post`, or any other HTTP method you need to handle. Here’s an example:

```python

from django_api_versioning.decorators import endpoint
from django.http import JsonResponse
from django.views import View

@endpoint("users", version=2, app_name='account_app', view_name="users_list_api")
class UsersView(View):

    def get(self, request):
        return JsonResponse({"message": "API Version 2 Users"})

```

#### Integration with Django Rest Framework (DRF):

If you have already installed [Django Rest Framework](https://www.django-rest-framework.org/#installation), the `endpoint` decorator can be easily applied to APIView or viewsets. Here’s an example with a DRF APIView:

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django_api_versioning.decorators import endpoint

@endpoint("users", version=2, app_name='account_app', view_name="users_list_api")
class UsersAPIView(APIView):

    def get(self, request):
        return Response({"message": "API Version 2 Users"})
```

#### URL Generation Based on Versioning:

Once the decorator is applied, the URLs for your API will be generated based on the version specified in the decorator. For example, if the `API_MIN_VERSION` in your settings.py is set to `1` and the version in the decorator is set to `2`, the following URLs will be available:

- `/api/v1/account_app/users`
- `/api/v2/account_app/users`

The `API_MIN_VERSION` setting ensures that users can access the API using different versions, providing backward compatibility. You can adjust which versions are considered valid by modifying the `API_MIN_VERSION` and `version` numbers in the decorators.

#### Additional Configuration Options:

**Without `app_name`:** If you don't pass `app_name` in the decorator, like this:

```python
@endpoint("users", version=2, view_name="users_list_api")
```

The generated URLs will be:

- `/api/v1/users`
- `/api/v2/users`

**Without `version`:** If you don't pass `version` in the decorator, like this:

```python
@endpoint("users", view_name="users_list_api")
```

API versioning will be disabled (`API_BASE_PATH` as prefix will be removed) for that view. The only URL generated will be:

- `/users`

**Setting `backward=False`:** By default, the `backward` parameter is set to `True`, which ensures backward compatibility. If you explicitly set `backward=False`, like this:

```python
@endpoint("users", version=2, backward=False, view_name="users_list_api")
```

The generated URL will be only version 2:

- `api/v2/users`

4. Run the Server:

```bash
python manage.py runserver
```

## Notes

### 1. `API_BASE_PATH` in settings Must Include ‍‍`{version}`:

The `API_BASE_PATH` should always include `{version}` to ensure proper API versioning. This is important for correctly mapping API routes to different versions.

### 2. Using `app_name` in the `endpoint` decorator:

It's recommended to fill in the `app_name` in the `endpoint` decorator to make the API URLs **more unique and organized**. This ensures that the routes are scoped under the correct app, avoiding potential conflicts and making them easier to manage.

### 3. Views with Version Less Than `API_MIN_VERSION` Are Automatically Ignored:

Any view whose `version` is less than the `API_MIN_VERSION` will be automatically ignored. This means clients will no longer have access to these older versions, **without the need to manually edit or remove code**. This is handled automatically by the package.

### 4. URLs for Versions Between `API_MIN_VERSION` <= `version` <= `API_MAX_VERSION`:

Endpoints that have versions within the range defined by `API_MIN_VERSION` <= `version` <= `API_MAX_VERSION` will always have a corresponding URL generated. This ensures that only valid versions will be accessible, providing flexibility in version management.

### `endpoint` Decorator Function Definition

The `endpoint` decorator is designed to register API views with versioning support in a Django application. It provides flexibility in managing versioned endpoints and ensures backward compatibility with previous versions of the API.

```python
def endpoint(
    postfix: str,
    version: Optional[int] = None,
    backward: bool = True,
    app_name: Optional[str] = None,
    view_name: Optional[str] = None,
) -> Callable:
    """
    Decorator to register API views with versioning support.

    - Uses `API_MIN_VERSION` and `API_MAX_VERSION` from Django settings.
    - Supports backward compatibility by registering multiple versions if needed.
    - Ensures that no version lower than `API_MIN_VERSION` is registered.

    Args:
        postfix (str): The endpoint suffix (e.g., "users" → "api/v1/users").
        version (Optional[int]): The version of the API. Defaults to None (unversioned).
        backward (bool): If True, registers routes for all versions from `API_MIN_VERSION` up to the current version, which is less than or equal to `API_MAX_VERSION`. Defaults to True.
        app_name (Optional[str]): The app name to be prefixed to the route.
        view_name (Optional[str]): The custom view name for Django.

    Returns:
        Callable: The decorated view function.

    Raises:
        VersionTypeError: If the provided `version` is not an integer.
        VersionRangeError: If `API_MIN_VERSION` or `API_MAX_VERSION` are not properly set.
    """
```

## Contributing

Feel free to open an issue or submit a pull request with any improvements or bug fixes. We appreciate contributions to enhance this package!

## License

This package is open-source and available under the MIT license.
