# Segment Lab evidence harness

## Purpose

The recovered Netlify scenario code has been ported into this directory and adapted to the repository's existing Django integration project. The harness contains 18 executable scenarios. Test counts and pass/fail status belong to the linked GitHub Actions runs, not this operational guide; do not copy transient CI counts here.

The harness reuses:
- `../manage.py`
- `../project/settings.py` as its base settings
- `../project/urls.py` for the `existing_integration_project` scenario
- `../api/views.py` for that same scenario
- the package source at the repository root

It does not create a second `manage.py`, a second top-level Django project, or a second copy of the package.

## Scenarios

The catalogue contains the 17 scenarios recovered from the interrupted Netlify run, plus an `existing_integration_project` scenario that exercises the repository's real API views and DRF router (18 scenarios total). Scenarios run in fresh Python interpreters because package settings and the route registry are process-global.

The recovered scenario definitions are test inputs, not trusted results. All outputs must be regenerated against the current checkout.

## Generator and provenance

Run from the repository root:

```bash
python integration_test_project/segment_lab/generate_routes.py
python integration_test_project/segment_lab/generate_routes.py --check
```

The generator imports `django_api_versioning` directly from this repository checkout. It does not install 0.3.5, fetch a GitHub archive, or compare against PyPI. It records the full Git commit, package version, Python/Django/DRF versions, package source hashes, scenario observations, CLI output, and source references.

Generation fails when package source, unit tests, package/evidence inputs, or the executable `integration_test_project/` tree is dirty, when a source symbol/line locator is stale, or when a scenario probe fails. Provenance records SHA-256 hashes for package files and for `pyproject.toml`, test files, requirements, verification scripts, and every Python file in the integration project, so the evidence inputs are traceable. Python 3.10 uses the conditional `tomli` development dependency because `tomllib` is only in the standard library from Python 3.11 onward. Generated evidence belongs in `website/src/data/generated/`.

## Historical baseline

The captured Agent run used package commit `e5a5466ac0fab1eb1ef41d8d570ccac1301f2cd9` (version 0.3.5). Its generated output is historical only and must never be reused as evidence for the current package.

## Local validation

Run these commands from the repository root. Python 3.10 is supported; the
conditional `tomli` dependency supplies TOML parsing before Python 3.11.

```bash
python -m pip install -r requirements-ci.txt
python -m pytest --capture=no tests
python -m pytest --capture=no -c integration_test_project/pytest.ini integration_test_project
```

Generate the evidence only from a clean, committed checkout:

```bash
python integration_test_project/segment_lab/generate_routes.py
python integration_test_project/segment_lab/generate_routes.py --check
```

The generator records the checkout commit and hashes the package and executable
lab inputs. Do not set `SOURCE_COMMIT` to a different revision, and do not edit
generated evidence by hand.
