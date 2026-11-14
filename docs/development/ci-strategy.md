# CI strategy

## Goals

CI is a set of scoped quality gates, not a command that rebuilds every environment for every file change. Keep the package, its integration project, packaging artifacts, and the future static website independently testable.

The workflows are deliberately separate:

| Workflow | What it validates | Trigger scope |
|---|---|---|
| `Python tests` | Package unit tests and the existing Django integration project, including Segment Lab | Package source, tests, integration project, Python runtime/test requirements, pytest configuration |
| `Python package artifacts` | Wheel and sdist creation, Twine metadata validation, and forbidden-content checks | Package source and packaging inputs |
| Future website workflow | Astro checks, static build, and built-site smoke tests | `website/**` and `docs/articles/**` |

Documentation-only edits under `docs/website/`, root agent instructions, and other editorial material must not invoke Python tests or package builds. The website workflow is intentionally deferred until the Astro application and its static-output checks are complete.

## Cost controls

- CI uses `actions/setup-python` and its pip cache. It does not build the local development Docker image.
- `requirements-ci.txt` contains only Django, DRF, pytest, pytest-django, and pytest-cov.
- `requirements-build.txt` contains only `build` and `twine`.
- Python tests and artifact validation run as independent workflows and can execute concurrently.
- A concurrency group cancels obsolete in-progress runs for the same PR/ref.
- Pull-request workflows run at review start (`opened`, `reopened`, `ready_for_review`), not for every commit pushed to a long-lived review branch. Use `workflow_dispatch` to run explicit checkpoints after a meaningful batch of changes.
- Pushes to `main` remain automatic and path-filtered.

Path filters are a cost boundary, not a replacement for testing. If a change crosses a boundary, update the corresponding path list in the workflow in the same commit.

## Local commands

Run the same focused suites without Docker:

```bash
python -m pip install -r requirements-ci.txt
python -m pytest --capture=no tests
python -m pytest --capture=no -c integration_test_project/pytest.ini integration_test_project
```

Validate packaging separately:

```bash
python -m pip install -r requirements-build.txt
python -m build --outdir dist
python -m twine check --strict dist/*
python scripts/verify_distribution_contents.py dist
```

The root `Dockerfile` and `entrypoint.sh` remain available for the complete local development workflow, including optional pre-commit execution. BuildKit caches pip downloads, and pre-commit hook environments are installed lazily only when requested.

## Current baseline measurement

The first native-Python run on this branch completed successfully:

- Unit tests: 185 passed in 0.99 seconds.
- Integration tests: 249 passed in 13.91 seconds.
- Python test workflow wall time: approximately 42 seconds, including runner setup and dependency installation.
- Package artifact workflow: approximately 22 seconds, including dependency installation, wheel/sdist build, Twine validation, and package-content verification.

These are one-run observations, not a guaranteed future duration. The pip cache should reduce repeated dependency download cost on subsequent runs. The previous Docker-based workflow took approximately 143 seconds for one combined run.

## Website workflow acceptance criteria

When the Astro project is complete, add a dedicated workflow with Node dependency caching and a lockfile-based install (`npm ci`). It should run:

1. Article synchronization in checkable/deterministic mode.
2. Astro content/type checks.
3. Production static build.
4. Static output smoke tests, including nested article URLs and base-path asset resolution.
5. Internal-link and generated-content consistency checks.

It must not install Python development tools, run Django tests, or build the Python development Docker image unless a website test explicitly needs a Python-generated evidence fixture. If evidence generation is required, run only the Segment Lab generator against the checked-out package commit and cache Python dependencies separately.

Do not enable this workflow against the current incomplete website scaffold. First implement its scripts and verify their contracts locally.
