---
slug: "024-django-api-versioning-supported-django-python-versions"
title: "Python and Django Compatibility"
description: "Review django-api-versioning Python and Django requirements, package classifiers, GitHub Actions tests, and the separately configured tox compatibility matrix."
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

The repository has separate workflows for the focused Python test suites and the broader Python/Django compatibility matrix. They serve different purposes and should not be treated as the same test configuration.

### GitHub Actions Python test workflow

The `.github/workflows/tests.yml` workflow runs on a GitHub-hosted Ubuntu runner. It does not build the project's development Docker image.

For its focused test job, the workflow:

1. Checks out the exact commit associated with the event.
2. Sets up Python 3.15.
3. Installs the test dependencies from `requirements-ci.txt`.
4. Runs the package unit-test directory.
5. Runs the standalone Django integration-test project.

The commands executed by the workflow are:

```bash
python -m pytest --capture=no tests
python -m pytest --capture=no -c integration_test_project/pytest.ini integration_test_project
```

The integration suite uses its own pytest configuration. The root `pytest.ini` points to `tests`, so running the root pytest command alone is not equivalent to running both suites.

The workflow is configured for manual `workflow_dispatch`, relevant pushes to `main`, and pull-request review checkpoints when a PR is opened, reopened, or marked ready for review. Its path filters limit automatic runs to package source, tests, the integration project, Python test requirements, pytest configuration, and the workflow itself. It does not run on every synchronization commit to an already-open pull request; deliberate follow-up checks can be started with the manual workflow trigger.

The repository's root `Dockerfile` and `entrypoint.sh` remain part of the local development workflow. The default entrypoint runs the unit and integration suites and validates built package artifacts, but the current GitHub Actions Python test workflow does not invoke that Docker entrypoint.

### Configured tox compatibility matrix

The repository separately defines the following environments in `tox.ini`:

| Django version | Python versions | Test environments |
| --- | --- | ---: |
| 4.2 | 3.10, 3.11, 3.12 | 3 |
| 5.2 | 3.10, 3.11, 3.12, 3.13, 3.14 | 5 |
| 6.0 | 3.12, 3.13, 3.14 | 3 |
| 6.1 | 3.12, 3.13, 3.14, 3.15 | 4 |

This results in 15 configured test environments.

Each tox test environment runs both the package unit tests and the Django integration tests:

```bash
python -m pytest tests --maxfail=1 --disable-warnings -q
python -m pytest integration_test_project --maxfail=1 --disable-warnings -q
```

The `.github/workflows/compatibility.yml` workflow runs this matrix automatically for relevant package, test, integration-project, dependency, tox, and verification-script pushes to `main`, and when a pull request is opened, reopened, or marked ready for review. It also supports deliberate manual `workflow_dispatch` runs and reusable `workflow_call` from the tag-based publish workflow. It uses a separate GitHub Actions job for each tox environment. Documentation-only and website-only edits do not trigger this Python compatibility matrix.

The tox configuration also defines one lint environment that runs:

- flake8
- black --check
- isort --check-only

This produces 15 test environments plus one lint environment.

### Recorded test results

The latest focused Python workflow completed successfully at source revision `ef664d343b53e16bd121b0d564379bdbe0e89b72`:

- 247 unit tests passed.
- 258 Django integration tests passed.
- 96% package code coverage was reported.

The full compatibility matrix completed successfully in GitHub Actions run [#33](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43761660736), executed at workflow commit `1d3538135a9f1b2a11c0d4f830cf9a4a1eed3a7f`. All 17 jobs passed, including tox-matrix drift validation and YAML parsing of every workflow and Dependabot file. The package implementation is unchanged from source baseline `035a4054f3e0d7e3e47adfeef1889e89e0660443`; test revision `e9e1c545aa6bfe3f3ee67a174c11a8d580d7eb21` adds coverage for custom path-converter formatting:

- All 15 configured Python/Django environments passed.
- Each environment passed 247 unit tests and 258 integration tests.
- Each environment reported 96% package coverage.
- The separate lint environment passed flake8, Black, and isort.

See [the full compatibility matrix run](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43651972913) for the execution result and [the compatibility report](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/COMPATIBILITY_REPORT.md) for the tested combinations.

The package-artifact workflow also passed in [run #85](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43761401257) at commit `8b5514c4d3bff287953f70ac18d4844edf16a7bc`: it built the wheel and source distribution, passed strict Twine checks, validated distribution contents, and smoke-tested the installed wheel. The package source and packaging inputs were unchanged from the verified source baseline.

These results are tied to the cited source revisions. They are not a guarantee for Python/Django combinations absent from the tox matrix or for future dependency resolutions.

### Dependency resolution

The tox configuration installs Django using environment-specific version constraints.

DRF is installed as a development dependency. The tox configuration does not pin DRF to an exact version, so its resolved version may change between executions.

The compatibility report records DRF `3.18.3` as the resolved version for the 2026-11-14 checkpoint. This historical result should not be interpreted as an exact version guarantee for future test runs. The repository does not retain a complete per-environment resolved-dependency record for every matrix job.

For an accurate compatibility assessment, distinguish:

- Runtime dependency requirements.
- Package classifiers.
- Focused GitHub Actions test execution.
- Configured tox environments.
- Recorded test execution results.
- Package artifact validation.

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
- **CI configuration:** The focused Python workflow runs the unit and integration suites on a GitHub-hosted runner; the compatibility workflow runs the configured tox matrix on relevant package/test changes and PR review-start checkpoints, with manual reruns also available. Consult the [compatibility report](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/COMPATIBILITY_REPORT.md) for the recorded source revision and results.
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
