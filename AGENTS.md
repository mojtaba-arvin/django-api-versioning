# Repository-wide engineering instructions

## Repository map and ownership

- `django_api_versioning/`: the distributable Python package. Do not move website or lab code into this directory.
- `tests/`: the package's unit-test suite. Keep package regression tests here.
- `integration_test_project/`: the existing standalone Django integration project. Preserve it; do not create a second top-level Django project.
- `docs/articles/`: the canonical source of the 25 Markdown articles already tracked in this repository. Read and publish these files; do not download a second copy from GitHub or maintain a mirrored article corpus.
- `docs/reference/`: package reference material. Preserve its source ownership.
- `website/`: the current website application and its build assets. The existing implementation uses Astro, but a redesign may replace or reorganize the frontend architecture when justified. Keep website-specific source, dependencies, assets, and generated output within the website boundary.
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

## Website implementation and redesign

Current website implementation and redesign boundaries:
- The existing implementation is an Astro application rooted at `website/`. This describes the current state; it does not require the redesign to retain Astro, the current component tree, layouts, pages, scripts, CSS architecture, or visual system.
- The redesign may replace or reorganize the frontend framework and implementation when there is a sound technical reason. If Astro is retained, preserve the supported and security-reviewed dependency baseline rather than downgrading it without current advisory review.
- Keep the canonical article source at `docs/articles/`; do not create a second tracked or independently editable article corpus.
- Generated behavioural evidence must remain reproducible from the package source and separate from authored presentation code. Its storage location may follow the chosen frontend architecture, but its provenance and integrity must be preserved.
- Build a fully static site. The published output must work on generic static hosts and must not require Netlify runtime functions.
- Support GitHub Pages project-site base paths as well as a custom domain. Do not hard-code root-relative asset paths that break under a Pages base path.
- The current Netlify configuration uses Base directory `website` and Publish directory `dist` relative to that directory. Update hosting configuration if the chosen build architecture changes.
- Do not claim production deploy-readiness until the selected application build, static-output checks, browser-level keyboard/accessibility checks, reduced-motion behavior, layout-shift/performance review, and external-host smoke test all pass.
- Keep website-specific source, dependencies, assets, and generated output within the website boundary.

## Content and technical accuracy

The website serves three complementary purposes: product introduction, technical documentation, and presentation of verifiable implementation evidence. It must communicate technical credibility while allowing a compelling, polished product presentation. Preserve the agreed ten content responsibilities and the technical meaning of Segment Point; the current visual identity, styling, composition, and diagram design may be redesigned freely.

Explain terms before using them in examples. The routing diagram and explorer are explanatory visualizations of recorded registry data, not live Python execution; label them accurately. Their visual design and interaction model may change, but retain an accessible and useful no-JavaScript fallback.

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

- `.github/workflows/tests.yml` runs the Python unit and integration suites on relevant pushes to `main` and `audit/comprehensive-package-review`, PR review-start checkpoints, and manual dispatch when package, test, integration-project, Python dependency, or test-workflow files change. Documentation-only and website-only changes do not run Python CI.
- `.github/workflows/package-artifacts.yml` builds and validates wheel/sdist on relevant pushes to `main` and `audit/comprehensive-package-review`, PR review-start checkpoints, and manual dispatch when package source or packaging inputs change. It runs independently from the Python tests.
- `.github/workflows/compatibility.yml` runs the full 15-environment Python/Django tox matrix plus lint on relevant package, test, integration-project, dependency, tox, and verification-script pushes to `main` and `audit/comprehensive-package-review`, and on PR review-start events. It also supports manual `workflow_dispatch` and reusable `workflow_call`; the tag-based PyPI workflow calls it before building or publishing a release. The `validate-matrix` job runs `scripts/check_tox_workflow_matrix.py` before the matrix and fails if the explicit GitHub job list drifts from the environments resolved by tox.
- Both workflows use native GitHub-hosted Python with `setup-python` pip caching; CI must not build the development Docker image.
- Pull-request checks run when a PR is opened/reopened or marked ready for review, not on every synchronization commit. Package/test changes pushed to the active review branch run the compatibility matrix automatically. Use `workflow_dispatch` for an explicit rerun or a checkpoint when automatic triggers do not apply. Pushes to `main` remain automatic.
- `requirements-ci.txt` contains only dependencies needed by pytest and the integration project. Do not add formatter/type-checker/pre-commit dependencies to it unless CI actually runs those tools.
- `requirements-build.txt` contains only wheel/sdist build and metadata-validation tools.
- The root `Dockerfile` and `entrypoint.sh` remain the full local development workflow; BuildKit pip caching is enabled and pre-commit hook environments are installed lazily only when requested.
- `.github/workflows/website-data-preflight.yml` runs Node/Astro checks and static-output tests for `website/**` and `docs/articles/**` on relevant pushes to `main` and `audit/comprehensive-package-review`, PR review-start checkpoints, and manual dispatch; it never builds the Python development Docker image.
- `.github/workflows/website-lock.yml` regenerates the npm lockfile when `website/package.json` changes and runs the complete website verification sequence.
- `.github/workflows/generate-evidence.yml` runs when package/integration evidence inputs change, regenerates source-pinned Segment Lab evidence, then runs website checks and both static builds in the same workflow because a GITHUB_TOKEN-created commit does not trigger another workflow.
- Keep these website workflows separate from Python tests and PyPI artifact workflows.

## Quality gates

Before calling website work complete:
1. run the package's relevant tests without changing their meaning;
2. run the evidence generator in check mode and confirm it is deterministic;
3. run Astro type/content checks, npm audit, and production builds for root and project base paths;
4. test the built `dist/` from a generic static server, including nested article routes, assets, path traversal, and base-path behavior;
5. verify internal links, article count, keyboard navigation, visible focus, reduced motion, responsive layout, and no-JavaScript fallbacks;
6. complete browser-level WCAG 2.2 AA and measured performance review;
7. verify that `website/`, `docs/`, and `integration_test_project/` are absent from both wheel and sdist unless a deliberate, documented packaging change says otherwise.

Do not mark a gate as passed unless it was actually run. Do not deploy from an incomplete or failing build.


## GitHub Actions cost and capacity

This repository is public and its workflows use standard GitHub-hosted runners such as `ubuntu-latest`. GitHub documents standard hosted-runner use as free and unlimited for public repositories. Do not reduce test coverage or suppress relevant CI runs merely to conserve included Actions minutes.

This does not mean every Actions feature or resource is unlimited:
- Larger runners may be billable, including for public repositories.
- Artifact storage and cache storage have separate limits and retention/eviction policies.
- The account still has workflow/job concurrency and queue limits; this workflow has 17 jobs (one matrix validator plus 16 tox environments) and may queue alongside other workflows.
- Third-party services, package registries, network egress, and self-hosted infrastructure may have their own costs.

Keep standard runners unless a documented technical need justifies a larger runner. Upload only artifacts needed for diagnosis or release, set finite retention, avoid caching generated build output unnecessarily, and monitor cache/artifact usage. Do not treat public-repository runner minutes as a reason to avoid the full compatibility matrix.

The tox matrix is authoritative for configured Python/Django environments. The explicit matrix in `.github/workflows/compatibility.yml` must remain in sync with `tox.ini`; review both whenever either changes. A configured environment is not a passing environment: report only results from actual workflow logs and exit conclusions.


## Dependency and GitHub Actions updates

External GitHub Actions must be pinned to full commit SHAs, with the corresponding release tag in a trailing comment. Do not use mutable major-version tags or branches in workflow `uses:` references. The current pins are managed by Dependabot.

Dependabot is configured to open weekly grouped update pull requests for GitHub Actions, Python dependencies, and the website's npm dependencies. Review the upstream release notes and diff, confirm action permissions and runtime changes, and run the workflows relevant to each update. Do not enable automatic merging for dependency or action updates; the checks and review remain required.
