# Segment Lab evidence harness

## Current status

The recovered Netlify scenario code has been ported into this directory and adapted to run inside the repository's existing Django integration project. The harness is now code, not merely an inventory, but it is **not yet verified**: its first full run against the current package must pass before any generated output is treated as published evidence.

The harness reuses:
- `../manage.py`
- `../project/settings.py` as its base settings
- `../project/urls.py` for the `existing_integration_project` scenario
- `../api/views.py` for that same scenario
- the package source at the repository root

It does not create a second `manage.py`, a second top-level Django project, or a second copy of the package.

## Scenarios

The catalogue contains the 17 scenarios recovered from the interrupted Netlify run, plus an `existing_integration_project` scenario that exercises the repository's real API views and DRF router. Scenarios run in fresh Python interpreters because package settings and the route registry are process-global.

The recovered scenario definitions are test inputs, not trusted results. All outputs must be regenerated against the current checkout.

## Generator and provenance

Run from the repository root:

```bash
python integration_test_project/segment_lab/generate_routes.py
python integration_test_project/segment_lab/generate_routes.py --check
```

The generator imports `django_api_versioning` directly from this repository checkout. It does not install 0.3.5, fetch a GitHub archive, or compare against PyPI. It records the full Git commit, package version, Python/Django/DRF versions, package source hashes, scenario observations, CLI output, and source references.

Generation fails when package source or `pyproject.toml` is dirty, when a source symbol/line locator is stale, or when a scenario probe fails. Generated evidence belongs in `website/src/data/generated/`.

## Historical baseline

The captured Agent run used package commit `e5a5466ac0fab1eb1ef41d8d570ccac1301f2cd9` (version 0.3.5). Its generated output is historical only and must never be reused as evidence for the current package.
