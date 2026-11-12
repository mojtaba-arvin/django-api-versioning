---
slug: "024-django-api-versioning-supported-django-python-versions"
title: "Python and Django Compatibility"
description: "Understand django-api-versioning runtime requirements, optional DRF development dependencies, and the Python environment used by its CI workflow."
author:
  name: "Mojtaba Arvin"
  url: "https://www.linkedin.com/in/mojtabaarvin/"
keywords:
  - "django-api-versioning"
  - "Python compatibility"
  - "Django requirements"
  - "Django REST Framework"
  - "Dependency management"
---

# Python and Django Compatibility

Before installing a Django package, distinguish its declared runtime dependencies from the development tools and dependencies used by the package maintainers.

For `django-api-versioning` v0.3.4, Django is a runtime dependency, while Django REST Framework (DRF) is not. DRF appears in the package's development dependencies because the project uses it in its development and testing environment.

The package is maintained by the author of this article; implementation and metadata details below refer to v0.3.4.

This article examines the package's declared requirements, its package classifiers, and the environment used by its CI workflow. These represent different aspects of compatibility and should not be treated as interchangeable.

## Runtime Requirements

The runtime requirements declared by `django-api-versioning` v0.3.4 are:

| Requirement | Declared value |
| --- | --- |
| Python | `>=3.10` |
| Django | `>=4.2` |

The package metadata declares these requirements in `pyproject.toml`:

```toml
requires-python = ">=3.10"

dependencies = [
    "Django>=4.2",
]
```

Django REST Framework is not included in the package's runtime dependencies.

If your application uses DRF, install it as an application dependency. Its required version depends on your application's needs and the compatibility of the DRF release with your Django version.

See the [v0.3.4 package metadata](https://github.com/mojtaba-arvin/django-api-versioning/blob/v0.3.4/pyproject.toml).

## Runtime Dependencies vs. Development Dependencies

The package separates runtime dependencies from optional development dependencies.

| Dependency | Declaration | Purpose |
| --- | --- | --- |
| Python | `>=3.10` | Required Python interpreter |
| Django | `>=4.2` | Runtime dependency |
| Django REST Framework | `>=3.18` | Optional development dependency |

The development dependency group in `pyproject.toml` includes:

```toml
[project.optional-dependencies]
dev = [
    # Other development tools
    "djangorestframework>=3.18",
]
```

The repository's `requirements-dev.txt` specifies:

```text
djangorestframework>=3.18.3
```

The `requirements-dev.txt` file also includes the project's base requirements through:

```text
-r requirements.txt
```

The base `requirements.txt` declares:

```text
Django>=4.2
```

These DRF constraints describe the project's development and testing environment. They do not establish a minimum DRF version required by the published package.

If your application uses Django REST Framework, declare it in your own dependency configuration rather than treating it as a runtime requirement of `django-api-versioning`.

## Python Version Metadata

The package declares Python 3.10 or newer:

```toml
requires-python = ">=3.10"
```

Its package classifiers list the following Python versions:

| Python version | Listed in package classifiers? |
| --- | --- |
| 3.9 | No |
| 3.10 | Yes |
| 3.11 | Yes |
| 3.12 | Yes |
| 3.13 | Yes |
| 3.14 | Yes |
| 3.15 | Yes |

The `requires-python` field defines the minimum Python version accepted by the package metadata.

Classifiers provide additional package metadata. They should not be interpreted as proof that every listed Python version is covered by an automated test run.

In particular, declaring Python `>=3.10` does not establish that every future Python release has been tested.

## Django Version Metadata

The package declares Django 4.2 or newer:

```toml
dependencies = [
    "Django>=4.2",
]
```

Its package classifiers list these Django versions:

| Django version | Listed in package classifiers? |
| --- | --- |
| 4.2 | Yes |
| 5.0 | Yes |
| 5.1 | Yes |
| 5.2 | Yes |
| 6.0 | Yes |
| 6.1 | Yes |

These classifiers describe the versions associated with the package metadata. They do not constitute a CI test matrix or independently prove compatibility with every listed release.

The actual Django version installed during a test run depends on the dependency constraints and the versions resolved by pip at that time.

## What Does the CI Workflow Test?

Package metadata and automated test configuration answer different questions:

- Package metadata declares minimum runtime requirements and classifiers.
- CI configuration describes the environment in which automated tests are executed.

The v0.3.4 repository contains a GitHub Actions workflow that builds a Docker image and runs the test suite inside it.

The [v0.3.4 CI workflow](https://github.com/mojtaba-arvin/django-api-versioning/blob/v0.3.4/.github/workflows/tests.yml) does not define a separate matrix of Python, Django, and DRF versions.

The repository's Dockerfile defines the Python version using:

```dockerfile
ARG PYTHON_VERSION=3.15
FROM python:${PYTHON_VERSION}-slim
```

The workflow builds this Docker image and runs the test suite inside it.

The test image installs the development requirements, which include:

- Django `>=4.2`, through `requirements.txt`.
- Django REST Framework `>=3.18.3`, through `requirements-dev.txt`.

Because these are minimum-version constraints rather than exact pins, the versions resolved during a future image build may change as new compatible releases become available.

Consequently, the workflow does not establish that every Python, Django, and DRF combination listed in the package metadata has been tested.

For an accurate compatibility assessment, distinguish the declared minimum requirements, package classifiers, and the actual CI configuration.

## Checking Your Installed Versions

You can inspect the versions installed in your active Python environment.

Check Python:

```bash
python --version
```

Check Django:

```bash
python -m django --version
```

If your application uses DRF, check its installed version:

```bash
python -m pip show djangorestframework
```

You can also inspect the installed versions from a Python shell:

```python
import sys
import django

print(f"Python: {sys.version}")
print(f"Django: {django.get_version()}")

try:
    import rest_framework
    print(f"DRF: {rest_framework.VERSION}")
except ImportError:
    print("DRF is not installed")
```

The DRF check is optional because `django-api-versioning` does not require DRF as a runtime dependency.

## Installing the Package

The published package is available on [PyPI](https://pypi.org/project/django-api-versioning/).

Install v0.3.4 with pip:

```bash
python -m pip install django-api-versioning==0.3.4
```

Pip reads the package metadata and resolves its declared runtime dependencies, including Django.

You do not need to install Django REST Framework solely to install `django-api-versioning`.

If your application uses DRF, install it separately:

```bash
python -m pip install djangorestframework
```

Choose a DRF version compatible with the Django version used by your application.

## Declaring Application Dependencies

For an application that uses `django-api-versioning` but does not use Django REST Framework, a minimal `requirements.txt` can be:

```text
django-api-versioning==0.3.4
```

Pip resolves the package's declared runtime dependencies, including Django.

If your application also uses DRF, declare it separately:

```text
django-api-versioning==0.3.4
djangorestframework
```

You can specify an explicit DRF constraint based on your application's compatibility requirements:

```text
django-api-versioning==0.3.4
djangorestframework>=3.18
```

The DRF constraint in this example is an application-level choice. It is not a runtime requirement declared by `django-api-versioning`.

## Pinning the Package Version

A version constraint controls which package releases pip may select.

### Exact version

```text
django-api-versioning==0.3.4
```

Requests the `0.3.4` release of the package.

This constraint does not pin Django or other transitive dependencies.

### Compatible release

```text
django-api-versioning~=0.3.4
```

Allows compatible releases starting from `0.3.4` within the `0.3.x` series, excluding `0.4.0`.

### Version range

```text
django-api-versioning>=0.3,<1.0
```

Allows package releases from `0.3.0` up to, but not including, `1.0`.

A version constraint does not guarantee that every release in the selected range is compatible with your application.

For reproducible deployments, use a lock file or explicitly constrain the complete dependency set, not only `django-api-versioning`.

## Troubleshooting Compatibility Issues

### Unsupported Python Version

If your Python version is below `3.10`, it does not meet the package's declared minimum requirement.

Check the active interpreter:

```bash
python --version
```

Make sure your virtual environment uses Python `3.10` or newer.

### Dependency Resolution Errors

If pip reports a dependency conflict, inspect the installed versions:

```bash
python -m pip show Django djangorestframework django-api-versioning
```

You can also ask pip to check for incompatible installed dependencies:

```bash
python -m pip check
```

Remember that DRF is an application dependency when your application uses it, not a required runtime dependency of this package.

### Import Errors

If the package is installed but Python cannot import it, verify that it was installed in the same environment used to run Django:

```bash
python -m pip show django-api-versioning
```

Then test the public imports:

```python
from django_api_versioning import endpoint, ver_range, api_reverse
```

These are the public imports exposed by v0.3.4. For the package's routing behavior and configuration semantics, see the [versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Important Compatibility Considerations

When evaluating compatibility, keep these distinctions in mind:

- **Python requirement:** The package declares Python `>=3.10`.
- **Django requirement:** The package declares Django `>=4.2`.
- **DRF dependency:** DRF is not a runtime dependency of the package. It is included in the development dependencies.
- **Package classifiers:** Listed Python and Django versions are metadata, not proof of automated test coverage.
- **CI configuration:** The v0.3.4 test workflow builds a Docker image using Python `3.15` by default. It does not define a multi-version compatibility matrix.
- **Dependency resolution:** Minimum-version constraints do not guarantee that every future build uses the same dependency versions.

Meeting the declared minimum requirements is necessary, but it does not prove that every possible combination of newer dependency versions has been tested.

For production deployments, verify the dependency combination used by your application and run your own integration tests.

## Conclusion

For `django-api-versioning` v0.3.4, the declared runtime requirements are:

- Python `3.10` or newer.
- Django `4.2` or newer.

Django REST Framework is not a required runtime dependency. It is included in the package's development dependencies because the project uses it during development and testing.

Package classifiers, dependency metadata, and CI configuration describe different aspects of compatibility. Review all three before drawing conclusions about supported and tested environments.

## Further Reading

- [Django documentation](https://docs.djangoproject.com/)
- [Django REST Framework documentation](https://www.django-rest-framework.org/)
- [Python documentation](https://docs.python.org/3/)

To inspect the package source, releases, and implementation details, visit the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
