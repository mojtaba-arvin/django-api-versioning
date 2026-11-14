---
slug: "024-django-api-versioning-supported-django-python-versions"
title: "Python and Django Compatibility"
description: "Understand django-api-versioning runtime requirements, package classifiers, the GitHub Actions Docker test job, and the separately configured tox compatibility matrix."
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

For `django-api-versioning`, Django is a runtime dependency, while Django REST Framework (DRF) is not required by the core package. DRF is used by the project's integration examples and development and testing setup.

The package is maintained by the author of this article. This guide explains how to distinguish declared requirements, package classifiers, and tested compatibility. For current release-specific values, consult the project's metadata and compatibility report.

This article examines the package's declared requirements, its package classifiers, and the environment used by its CI workflow. These represent different aspects of compatibility and should not be treated as interchangeable.

## Runtime Requirements

The package declares its runtime requirements in `pyproject.toml`. These declarations are the source of truth for the minimum Python version and required Django dependency.

See the current [package metadata](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/pyproject.toml) rather than relying on version-specific values copied into this article.

The package metadata declares these requirements in `pyproject.toml`:

```toml
requires-python = ">=3.10"

dependencies = [
    "Django>=4.2",
]
```

Django REST Framework is not included in the package's runtime dependencies.

If your application uses DRF, install it as an application dependency. Its required version depends on your application's needs and the compatibility of the DRF release with your Django version.

See the [current package metadata](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/pyproject.toml).

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
| 5.2 | Yes |
| 6.0 | Yes |
| 6.1 | Yes |

These classifiers describe the versions associated with the package metadata. They do not constitute a CI test matrix or independently prove compatibility with every listed release.

The actual Django version installed during a test run depends on the dependency constraints and the versions resolved by pip at that time.

## What Do GitHub Actions and tox Actually Test?

The repository has two separate testing mechanisms:

1. The GitHub Actions Docker workflow.
2. The local tox test matrix.

They serve different purposes and must not be treated as the same test configuration.

### GitHub Actions Docker workflow

The `.github/workflows/tests.yml` workflow:

1. Runs on pushes and pull requests targeting `main`.
2. Builds the project's Docker image.
3. Runs the container's default entrypoint.

The Dockerfile uses Python `3.15` by default through its `PYTHON_VERSION` build argument.

The image installs the development requirements and runs the default `pytest` command through `entrypoint.sh`.

The project's pytest configuration sets:

```ini
testpaths = ["tests"]
```

Consequently, the default Docker workflow runs the unit test directory. It does not execute the integration test directory or the complete tox matrix.

### Configured tox matrix

The repository separately defines the following environments in `tox.ini`:

| Django version | Python versions | Test environments |
| --- | --- | ---: |
| 4.2 | 3.10, 3.11, 3.12 | 3 |
| 5.2 | 3.10, 3.11, 3.12, 3.13, 3.14 | 5 |
| 6.0 | 3.12, 3.13, 3.14 | 3 |
| 6.1 | 3.12, 3.13, 3.14, 3.15 | 4 |

This results in 15 configured test environments.

Each tox test environment runs the unit and integration test directories separately:

```bash
python -m pytest tests --maxfail=1 --disable-warnings -q
python -m pytest integration_test_project --maxfail=1 --disable-warnings -q
```

The tox configuration also defines one lint environment that runs:

- flake8
- black --check
- isort --check-only

This produces 15 test environments plus one lint environment.

### Recorded test results

The project's 2026-11-14 compatibility report records a full tox run with:

- All 15 test environments passing.
- The lint environment passing.
- 175 unit tests and 245 integration tests passing per test environment.
- 88% code coverage.
- A tox exit code of 0.

These are project-recorded execution results. Raw per-environment logs and resolved dependency records are not retained in the repository for independent reproduction.

### Dependency resolution

The tox configuration installs Django using environment-specific version constraints.

DRF is installed as a development dependency. The tox configuration does not pin DRF to an exact version, so its resolved version may change between executions.

The recorded 2026-11-14 run reports DRF `3.18.3`. This historical result should not be interpreted as an exact version guarantee for future test runs.

For an accurate compatibility assessment, distinguish:

- Runtime dependency requirements.
- Package classifiers.
- GitHub Actions workflow behavior.
- Configured tox environments.
- Recorded test execution results.

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

Install the package with pip:

```bash
python -m pip install django-api-versioning
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
django-api-versioning
```

Pip resolves the package's declared runtime dependencies, including Django.

If your application also uses DRF, declare it separately:

```text
django-api-versioning
djangorestframework
```

You can specify an explicit DRF constraint based on your application's compatibility requirements:

```text
django-api-versioning
djangorestframework
```

The DRF constraint in this example is an application-level choice. It is not a runtime requirement declared by `django-api-versioning`.

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

These are the package's public imports. For the package's routing behavior and configuration semantics, see the [versioning contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Important Compatibility Considerations

When evaluating compatibility, keep these distinctions in mind:

- **Python requirement:** The package declares Python `>=3.10`.
- **Django requirement:** The package declares Django `>=4.2`.
- **DRF dependency:** DRF is not a runtime dependency of the package. It is included in the development dependencies.
- **Package classifiers:** Listed Python and Django versions are metadata, not proof of automated test coverage.
- **CI configuration:** The test workflow describes the environments used by automated tests. Consult the [compatibility report](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/COMPATIBILITY_REPORT.md) for the currently documented test matrix.
- **Dependency resolution:** Minimum-version constraints do not guarantee that every future build uses the same dependency versions.

Meeting the declared minimum requirements is necessary, but it does not prove that every possible combination of newer dependency versions has been tested.

For production deployments, verify the dependency combination used by your application and run your own integration tests.

## Conclusion

The package's runtime requirements are declared in its [project metadata](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/pyproject.toml). Django REST Framework is not required to install the core package; it is used by the project's integration examples and development and testing setup.

For tested Python and Django combinations, consult the [compatibility report](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/COMPATIBILITY_REPORT.md).

Package classifiers, dependency metadata, and CI configuration describe different aspects of compatibility. Review all three before drawing conclusions about supported and tested environments.

## Further Reading

- [Django documentation](https://docs.djangoproject.com/)
- [Django REST Framework documentation](https://www.django-rest-framework.org/)
- [Python documentation](https://docs.python.org/3/)

To inspect the package source, releases, and implementation details, visit the [django-api-versioning repository](https://github.com/mojtaba-arvin/django-api-versioning).
