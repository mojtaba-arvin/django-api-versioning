# django-api-versioning reference

## Installation

~~~bash title="terminal"
$ pip install django-api-versioning
~~~

Requires Python ≥ 3.10 and Django ≥ 4.2. Django REST Framework is optional. CI covers Django 4.2, 5.2, 6.0 and 6.1 (5.0 and 5.1 are not covered).

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `API_BASE_PATH` | `"api/v{version}/"` | URL prefix for versioned routes. Must contain exactly one plain ``{version}`` field. |
| `API_MIN_VERSION` | `1` | Lowest version served. Declarations below it are skipped with a warning. |
| `API_MAX_VERSION` | `1` | Highest version served. Declarations above it raise `InvalidVersionError`. |
| `API_VERSION_LIFECYCLE` | `{}` | Per-version status, `deprecated_at` and `sunset` used by `LifecycleMiddleware`. |
| `API_VERSIONING_CHANNELS` | `["path"]` | Validated, but not used to select routes. |
| `API_EFFECTIVE_VERSION_RESOLVER` | `None` | Validated, but not used to select routes. |

## @endpoint arguments

| Argument | Default | Purpose |
| --- | --- | --- |
| `postfix` | required | Resource path, positional. e.g. `invoices/<int:invoice_id>/` |
| `version` | `None` | Start of a forward segment. |
| `versions` | `None` | Explicit list of versions, or `ver_range(a, b)`. |
| `app_name` | `None` | Optional grouping path segment. |
| `view_name` | `None` | Name used by `api_reverse()`. |

~~~python title="views.py"
from django_api_versioning import endpoint, ver_range

@endpoint("reports/", version=3)                      # v3 → max
@endpoint("ranking/", versions=[2, 4])                # v2 and v4 only
@endpoint("legacy/", versions=ver_range(1, 3))        # v1, v2, v3
@endpoint("health/")                                  # unversioned: /health/
~~~

Each line above is a separate example. When a route has several forward declarations (for example `version=1` and `version=3`), each serves from its own version until the next declaration takes over.

## Validation & collisions

- Combining `version` and `versions` raises `VersionRangeError`.
- A version above `API_MAX_VERSION` raises `InvalidVersionError`.
- Versions below `API_MIN_VERSION` trigger a warning and are skipped.
- Booleans are rejected as version values.
- On collision the higher `source_version` wins.
- If source versions are equal, or either is `None`, the last registration wins.
- The package does not set `request.version`; configure DRF versioning separately if you need it.
- Route settings are read at import time, so `override_settings` will not rebuild URL patterns.
- ViewSets cannot be decorated directly. Pass a pre-configured callable such as `MyViewSet.as_view({"get": "list"})`, or use a DRF router for standard ViewSet routing.

For the complete routing contract—including import order, URL construction, route precedence, `api_reverse()`, ViewSet limitations and lifecycle behavior—see [the canonical routing contract](https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/reference/versioning-contract.md).

## Exceptions

| Exception | Raised when |
| --- | --- |
| `VersioningError` | Base exception for package versioning errors. |
| `VersionRangeError` | The endpoint arguments or configured version boundaries define an invalid range. |
| `InvalidVersionError` | A declared version exceeds `API_MAX_VERSION`. |
| `VersionTypeError` | A version value is not an integer; booleans are rejected. |
| `AmbiguousVersionError` | `api_reverse()` has multiple matches and no version was supplied. |
| `VersionMatrixError` | `assert_version_matrix()` detects a difference from the saved route snapshot. |

## Management commands

`check_versions` prints the registered logical route matrix and warns about gaps within each endpoint's registered span.

~~~text title="check_versions output"
$ python manage.py check_versions
users/:
  v1           → users_list_v1
  v2           → users_list_v2
  v3           → users_list_v2
  v4           → users_list_v2
~~~

Upgrading from 0.2.0, which used `forward`/`backward` flags? Preview the rewrite first and review every change. The command defaults to a non-writing preview; use `--write` only after reviewing the output.

~~~bash title="migrate_endpoints"
$ python manage.py migrate_endpoints --dry-run
~~~

## Development

~~~bash title="terminal"
$ pip install -e ".[dev]" && pre-commit install
$ python -m pytest tests
$ python -m pytest integration_test_project
$ tox run-parallel -p auto
~~~

Contributions are welcome on [GitHub](https://github.com/mojtaba-arvin/django-api-versioning).
