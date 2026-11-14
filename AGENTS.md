# Repository instructions for documentation-site work

## Repository map and ownership

- `django_api_versioning/`: the distributable Python package. Do not move website or lab code into this directory.
- `tests/`: the package's unit-test suite. Keep package regression tests here.
- `integration_test_project/`: the existing standalone Django integration project. Preserve it; do not create a second top-level Django project.
- `docs/articles/`: the canonical source of the 25 Markdown articles already tracked in this repository. Read and publish these files; do not download a second copy from GitHub or maintain a mirrored article corpus.
- `docs/reference/`: package reference material. Preserve its source ownership.
- `website/`: the dedicated Astro application root. All Node dependencies, Astro configuration, components, layouts, pages, static assets, and frontend build output belong here.
- `docs/website/`: architecture decisions, content provenance, and handoff instructions for the website.

## Package baseline and evidence

The package metadata on the branch used to establish this contract declares version `0.3.7`. Before generating or changing any behavioural evidence, read the actual checked-out `pyproject.toml` version and record the full Git commit SHA used for the evidence.

Never reuse the Netlify Agent log's old package pin `e5a5466ac0fab1eb1ef41d8d570ccac1301f2cd9` as current evidence. That log was generated against package version 0.3.5. Do not combine its recorded outputs with evidence for another package version.

Evidence must be reproducible from the package source at one immutable commit. Record at least:
- repository URL;
- full source commit SHA;
- package version read from `pyproject.toml`;
- Python, Django, and DRF versions actually used;
- commands/scenarios executed;
- generated timestamp and hashes for source files or generated artifacts where practical.

Do not invent, manually repair, or silently normalize observed output. If a scenario cannot be executed against the selected baseline, report it as unverified rather than presenting it as package behaviour.

The existing `integration_test_project/` is the home for additional executable integration scenarios and evidence-generation tooling. First inspect and reuse its settings, URL configuration, and tests. A separate evidence harness may be added below it only when isolation is technically necessary and documented. Do not overwrite or duplicate `test_integration.py`.

## Website implementation

- Astro project root: `website/`.
- Canonical article source: `../docs/articles/` from the website project; do not create a second tracked copy of the articles.
- Generated behavioural data belongs under `website/src/data/generated/` and must be reproducible by a documented command.
- Keep generated evidence distinct from authored presentation code.
- Build a fully static site. The generated `website/dist/` must work on a generic static host and must not require Netlify runtime functions.
- Support GitHub Pages project-site base paths as well as a custom domain. Do not hard-code root-relative asset paths that break under a Pages base path.
- Netlify's future Base directory is `website`; its publish directory is `dist` relative to that base directory. Do not claim the site is deploy-ready until the Astro application, lockfile, build, and static-output checks actually exist and pass.
- Keep Node dependencies and all website assets inside `website/`.

## Content and technical accuracy

The site is a developer-facing explanation and evidence viewer, not a promotional landing page. Preserve the agreed ten-section homepage plan and the Segment Point visual identity.

Explain terms before using them in examples. The routing diagram/explorer is an explanatory visualization, not Python execution; label it accordingly and provide a useful static fallback without JavaScript.

Do not claim that `API_VERSIONING_CHANNELS` or `API_EFFECTIVE_VERSION_RESOLVER` participates in endpoint routing, header/query negotiation, or tenant-specific routing unless new source inspection and executed tests prove that claim.

Keep these distinctions explicit:
- segment-point expansion is registration/import-time behaviour, not a per-request version decision;
- the package registers/routes endpoint implementations; it is not an API response-contract enforcement system;
- package-generated URL routing does not automatically populate DRF's `request.version`;
- DRF `URLPathVersioning` requires a matching URL kwarg/configuration and must be evaluated separately;
- a DRF ViewSet class requires an action map through `as_view()`; do not imply that decorating a bare ViewSet class is supported;
- a DRF router mounted alongside package-generated routes is a separate routing mechanism.

Do not infer behaviour from article wording alone. Verify package claims against the exact source baseline and executable evidence. Preserve known limitations and negative findings.

## CI execution policy

- `.github/workflows/tests.yml` runs the Python unit and integration suites only when package, test, integration-project, Python dependency, or test-workflow files change. Documentation-only and website-only changes do not run Python CI.
- `.github/workflows/package-artifacts.yml` builds and validates wheel/sdist only when package source or packaging inputs change. It runs independently from the Python tests.
- `.github/workflows/compatibility.yml` runs the full 15-environment Python/Django tox matrix plus lint as a manual `workflow_dispatch` checkpoint. Keep it out of routine push/PR triggers; use it before compatibility-sensitive releases or major package changes.
- Both workflows use native GitHub-hosted Python with `setup-python` pip caching; CI must not build the development Docker image.
- Pull-request checks run when a PR is opened/reopened or marked ready for review, not on every synchronization commit. Use the Actions `workflow_dispatch` entry to run explicit validation checkpoints after a batch of commits. Pushes to `main` remain automatic.
- `requirements-ci.txt` contains only dependencies needed by pytest and the integration project. Do not add formatter/type-checker/pre-commit dependencies to it unless CI actually runs those tools.
- `requirements-build.txt` contains only wheel/sdist build and metadata-validation tools.
- The root `Dockerfile` and `entrypoint.sh` remain the full local development workflow; BuildKit pip caching is enabled and pre-commit hook environments are installed lazily only when requested.
- When the Astro application is complete, add a separate website workflow triggered by `website/**` and `docs/articles/**`. It should run Node/Astro checks and static-output tests, never the Python Docker image. Until then, do not claim website CI has been established.

## Quality gates

Before calling website work complete:
1. run the package's relevant tests without changing their meaning;
2. run the evidence generator in check mode and confirm it is deterministic;
3. run Astro type/content checks and production build;
4. test the built `dist/` from a generic static server, including nested article routes and asset paths;
5. check internal links, article count, keyboard navigation, visible focus, reduced motion, responsive layout, and no-JavaScript fallbacks;
6. verify that `website/`, `docs/`, and `integration_test_project/` are absent from both wheel and sdist unless a deliberate, documented packaging change says otherwise.

Do not mark a gate as passed unless it was actually run. Do not deploy from an incomplete or failing build.
