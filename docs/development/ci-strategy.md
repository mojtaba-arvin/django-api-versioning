# CI strategy

## Goals

CI is a set of scoped quality gates, not a command that rebuilds every environment for every file change. Keep the Python package, its integration project, packaging artifacts, generated website evidence, and Astro application independently testable.

## Workflow boundaries

| Workflow | What it validates | Trigger scope |
| --- | --- | --- |
| `Python tests` | Package unit tests and the existing Django integration project | Relevant pushes to `main` and `audit/comprehensive-package-review`, PR review-start checkpoint, and manual dispatch; package/test/integration paths only |
| `Python package artifacts` | Wheel/sdist creation, Twine metadata validation, and forbidden-content checks | Relevant pushes to `main` and `audit/comprehensive-package-review`, PR review-start checkpoint, and manual dispatch; package/distribution inputs only |
| `Compatibility matrix` | Full tox matrix: 15 Python/Django combinations plus lint | Manual `workflow_dispatch` checkpoint |
| `Website build and static verification` | Locked npm install, dependency audit, Node tests, Astro checks, root and project-base builds, static-output smoke tests | Relevant pushes to `main` and `audit/comprehensive-package-review`, PR review-start checkpoint, and manual checkpoints |
| `Generate source-pinned website evidence` | Segment Lab generation/check, source provenance, website tests, Astro checks, and both static builds | Package source, integration project, `pyproject.toml`, Python requirements, or evidence workflow |
| `Generate website npm lockfile and verify the site` | Lockfile generation, `npm ci`, dependency audit, Node/Astro checks, and both static builds | `website/package.json` or lock workflow |

Documentation-only edits under `docs/website/`, root agent instructions, and other editorial material do not invoke Python tests or package builds. Website-only work does not invoke Python package tests. Evidence generation runs Python only when package/integration inputs change.

## Cost controls

- Python CI uses `actions/setup-python` and pip caching. It does not build the local development Docker image.
- `requirements-ci.txt` contains only Django, DRF, pytest, pytest-django, and pytest-cov.
- `requirements-build.txt` contains only `build` and `twine`.
- Python tests and artifact validation are independent workflows and can execute concurrently.
- Website dependencies are installed from `package-lock.json` with `npm ci`; npm cache is keyed to the lockfile.
- The website audit fails on High or Critical dependency vulnerabilities.
- Website checks and Python tests use separate workflows and runner environments.
- Concurrency groups cancel obsolete in-progress runs for the same branch/ref.
- Python and website PR workflows run when review starts (`opened`, `reopened`, `ready_for_review`), not for every synchronization commit. Use explicit `workflow_dispatch` checkpoints after a meaningful batch.
- These PR runs are review checkpoints, not a green status for every later commit SHA. Do not mark them as required merge checks unless a per-synchronization gate or final-SHA manual checkpoint is introduced.
- Pushes to `main` and the active `audit/comprehensive-package-review` branch remain automatic and path-filtered for the corresponding Python, package-artifact, website, and article inputs.
- The full compatibility matrix is manual-only; run it at deliberate compatibility/release checkpoints rather than on every commit.
- The website preflight does not run on every documentation correction in a long-lived review branch. Its PR checkpoint validates the reviewed snapshot; the `main` push validates merged website/article changes.

Path filters are a cost boundary, not a replacement for testing. If a change crosses a boundary, update the corresponding path list in the workflow in the same commit.

## Local commands

Python tests:

```bash
python -m pip install -r requirements-ci.txt
python -m pytest --capture=no tests
python -m pytest --capture=no -c integration_test_project/pytest.ini integration_test_project
```

Package artifacts:

```bash
python -m pip install -r requirements-build.txt
python -m build --outdir dist
python -m twine check --strict dist/*
python scripts/verify_distribution_contents.py dist
```

Website checks (from `website/`):

```bash
npm ci
npm audit --audit-level=high
npm test
npm run check
npm run build
npm run test:dist
```

For GitHub Pages project-site verification, set `PUBLIC_BASE_PATH=/django-api-versioning` for both the build and static-output check.

The root `Dockerfile` and `entrypoint.sh` remain the complete local development workflow, including optional pre-commit execution. BuildKit caches pip downloads, and pre-commit hook environments are installed lazily only when requested.

## Observed baselines

The full tox compatibility checkpoint completed successfully at source commit `9b09d66c931f6e99687664da7442ddf9198595cb`:

- 211 unit tests and 249 integration tests passed.
- All 15 Python/Django compatibility environments and lint passed.

The latest focused Python workflow on the active audit branch completed successfully at source `1580abca5ceae639d55fdb12f94177c5239aebdb` ([run 43642849997](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43642849997)):

- 211 unit tests passed.
- 252 integration tests passed.
- 96% package coverage.

The package artifact workflow completed successfully at source `46399121b551f45301d73ff7e53100f5f39d69ef` ([run 43642742970](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43642742970)); wheel/sdist creation, Twine validation, and package-content checks passed.

The latest website build and dependency verification completed in [GitHub Actions run 43643275918](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43643275918), triggered by package configuration commit `417ee4a14878f9e6e29bba5c6c203dcb65f317df` and using generated lockfile commit `f2a6afc07ba7a1a955f75afb886908b6fc93c89c`. It passed:
- 20 Node tests;
- Astro check with zero errors, warnings, and hints;
- `npm audit --audit-level=high`;
- root-hosted build and static-output verification;
- GitHub Pages project-base build and static-output verification.

These are observed runs, not guaranteed future durations. The previous Docker-based Python workflow took approximately 143 seconds for one combined run.

## Acceptance criteria and remaining gates

Static website build checks are established. The next website gate is browser-level verification: keyboard-only operation, focus visibility, mobile navigation, search, code copy, theme controls, reduced motion, no-JavaScript fallback, responsive layout, accessibility scan, and measured performance.

Do not deploy until the article corpus review and browser/accessibility/performance gates in `docs/website/implementation-status.md` are accepted. Netlify uses base directory `website`, command `npm run build`, and publish directory `dist`; GitHub Pages publishes only `website/dist/`.

## Frontend dependency audit finding

The 2026-11-14 website dependency workflow found one low-severity advisory in the resolved `esbuild` dependency: [GHSA-g7r4-m6w7-qqqr](https://github.com/advisories/GHSA-g7r4-m6w7-qqqr). Versions `>=0.27.3` and `<0.28.1` are affected by a Windows-only path traversal in the esbuild development server; `0.28.1` is patched.

The lockfile resolved `esbuild@0.27.7`. Vite `8.3.8` declares an optional peer range of `^0.27.0 || ^0.28.0`, so the website now uses an explicit npm override to `esbuild@0.28.1`. The lockfile was regenerated by the workflow rather than hand-edited.

Validation at source commit `417ee4a14878f9e6e29bba5c6c203dcb65f317df` completed successfully in [GitHub Actions run 43643275918](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43643275918):

- `npm ci` installed the exact lockfile.
- `npm audit` reported zero vulnerabilities.
- All 31 Node tests passed.
- Astro content/type checks passed.
- Root-hosted and GitHub Pages builds and static-output checks passed.

Keep the override while the resolved dependency graph requires it. Reassess it when Vite or Astro changes, and remove it only after the lockfile resolves to a patched version without the override.
