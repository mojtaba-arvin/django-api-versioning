# CI strategy

## Goals

CI is a set of scoped quality gates, not a command that rebuilds every environment for every file change. Keep the Python package, its integration project, packaging artifacts, generated website evidence, and Astro application independently testable.

## Workflow boundaries

| Workflow | What it validates | Trigger scope |
| --- | --- | --- |
| `Python tests` | Package unit tests and the existing Django integration project | Package source, tests, integration project, Python runtime/test requirements, pytest configuration |
| `Python package artifacts` | Wheel/sdist creation, Twine metadata validation, and forbidden-content checks | Package source plus every tracked sdist input |
| `Compatibility matrix` | Full tox matrix: 15 Python/Django combinations plus lint | Manual `workflow_dispatch` checkpoint |
| `Website build and static verification` | Locked npm install, dependency audit, Node tests, Astro checks, root and project-base builds, static-output smoke tests | PR review-start checkpoint and relevant pushes to `main`; manual checkpoints |
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
- Pushes to `main` remain automatic and path-filtered.
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

The latest Python focused and compatibility checkpoints completed successfully at source commit `9b09d66c931f6e99687664da7442ddf9198595cb`:

- Unit tests: 211 passed; 96% package coverage.
- Integration tests: 249 passed.
- All 15 Python/Django compatibility environments and lint passed.
- Optimized Python workflow wall time: approximately 38–42 seconds.
- Package artifact workflow: approximately 19–22 seconds.

The latest recorded website checkpoint on implementation commit `330a9553310ae4c9d44fb9787f607ac2ba0c114a` ([GitHub Actions run 43638777904](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43638777904)) passed:
- 20 Node tests;
- Astro check with zero errors, warnings, and hints;
- `npm audit --audit-level=high`;
- root-hosted build and static-output verification;
- GitHub Pages project-base build and static-output verification.

These are observed runs, not guaranteed future durations. The previous Docker-based Python workflow took approximately 143 seconds for one combined run.

## Acceptance criteria and remaining gates

Static website build checks are established. The next website gate is browser-level verification: keyboard-only operation, focus visibility, mobile navigation, search, code copy, theme controls, reduced motion, no-JavaScript fallback, responsive layout, accessibility scan, and measured performance.

Do not deploy until the article corpus review and browser/accessibility/performance gates in `docs/website/implementation-status.md` are accepted. Netlify uses base directory `website`, command `npm run build`, and publish directory `dist`; GitHub Pages publishes only `website/dist/`.
