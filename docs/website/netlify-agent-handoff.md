# Static website hosting handoff

## Redesign scope

Start from the current `main` branch. The previous `audit/comprehensive-package-review` branch is superseded by `main` and must not be used as the redesign base. This task is a redesign of the existing documentation website, not a request to preserve its current visual design or frontend implementation.

- Redesign the website freely: the current visual identity, page composition, component tree, layouts, navigation presentation, CSS, and frontend architecture are reference material, not mandatory design constraints.
- Preserve the agreed ten homepage content responsibilities, the canonical article corpus, verified package behavior, real Segment Lab evidence and provenance, required user-facing capabilities, accessibility expectations, and static-hosting behavior.
- The existing Astro application is the current implementation, not a required target architecture. It may be retained, reorganized, or replaced when justified. If retained, use a supported, security-reviewed dependency baseline.
- Preserve the existing Django integration project and Segment Lab. The recovered scenario code is already integrated into `integration_test_project/segment_lab/`; use its generator and tests. Do not create a parallel `tools/` Django project.
- `docs/articles/` is the only editable article source. The website must publish all 25 articles without maintaining a second independently editable corpus.
- The committed Segment Lab snapshot is generated from the repository checkout, not the historical Netlify package 0.3.5 run. Never reuse that historical output.
- Validate the redesigned site at browser level, including keyboard/mobile/accessibility checks, reduced motion, layout stability, and static-host behavior. Make evidence-backed technical claims and add focused tests for changed behavior.
- Do not run the full Python compatibility matrix for frontend-only changes. Run it only for package/runtime changes or the final release checkpoint.
- A version tag cannot publish to PyPI until the reusable 15-environment compatibility matrix and lint job pass. The release workflow builds, validates, and smoke-tests distributions in a job without OIDC permissions, then passes a short-lived artifact to a separate minimal publish job. Only that final job receives `id-token: write`; it must not check out source or run build scripts.
- Do not publish to PyPI or deploy to production without explicit approval.

### Framework security exception

The original brief requested Astro 6. The Astro 6.4.8 baseline is no longer acceptable for a release candidate: current advisories include critical issues fixed only in later Astro 7 releases. The branch therefore intentionally targets Astro 7.4.12. Its locked dependency tree resolves the patched `sharp` 0.35.5 release; no forced dependency overrides are needed. Do not downgrade to Astro 6 merely to match the original version line; any framework-major change must be justified by current security advisories and verified by the full website workflow.


Use this file together with the repository-root `AGENTS.md` and `architecture.md`.

## Current state

The Astro application is implemented and its CI checks have passed for:
- root-hosted static output;
- GitHub Pages project-site output with `PUBLIC_BASE_PATH=/django-api-versioning`;
- 25 article detail pages;
- 18 source-pinned Segment Lab scenarios;
- local HTML link targets and required output files.

The site has not been deployed. Do not describe a Netlify or GitHub Pages deployment as successful until the external hosting smoke test is actually run.

## Where to find things

| Needed input | Exact path |
| --- | --- |
| Python package source | `django_api_versioning/` |
| Package version | `pyproject.toml` → `[project].version` |
| Package unit tests | `tests/` |
| Existing Django integration project | `integration_test_project/` |
| Segment Lab and evidence generator | `integration_test_project/segment_lab/` |
| Canonical long-form articles | `docs/articles/` |
| Versioning contract | `docs/reference/versioning-contract.md` |
| Website architecture and handoff gates | `docs/website/architecture.md` and this file |
| Astro application root | `website/` |
| Generated evidence destination | `website/src/data/generated/` |
| PyPI inclusion/exclusion policy | `pyproject.toml` and `MANIFEST.in` |

## Netlify configuration

The Git-connected Netlify site deploys this repository from `main`.

- Base directory: `website`
- Build command: `npm run build`
- Publish directory: `dist` (relative to the base directory; repository path is `website/dist/`)
- Node requirement: 22.23.4 or newer
- Install command: `npm ci` (Netlify's dependency install should use the committed lockfile)
- Functions directory: leave unset/blank; this website has no Netlify Functions.
- Environment variables: none are required for the root-hosted Netlify build. Do not set `PUBLIC_BASE_PATH` for Netlify; that variable is only used for the GitHub Pages project-site build.

Netlify's `URL` environment variable may be used as the canonical site URL. The site must remain static and must not depend on Netlify runtime functions.

### Connected Netlify Agent workflow

- Use the Git-connected Netlify project and its checked-out repository workspace. Do not clone a second copy when the connected source is already available.
- Verify that the workspace contains this repository and the intended `main` revision before inspecting or editing files.
- Use Agent Runner **Build** mode for implementation; **Ask** mode is read-only and cannot deliver code changes.
- Keep redesign work isolated from `main`. Work on an Agent-managed feature branch and deliver a reviewable Deploy Preview and pull request where the Netlify workflow supports them.
- Do not merge the redesign, publish a production deployment, or change the production branch as part of the redesign task. Those actions require maintainer review and approval.
- The Netlify Agent must read this handoff, `AGENTS.md`, `docs/website/architecture.md`, `docs/reference/versioning-contract.md`, `integration_test_project/segment_lab/README.md`, and `website/README.md` from the connected checkout before implementation.
- The Agent must not claim repository access, tests, browser checks, or deployment results that it has not actually verified.

## GitHub Pages configuration

For the repository project site, build with:

```bash
PUBLIC_BASE_PATH=/django-api-versioning npm run build
PUBLIC_BASE_PATH=/django-api-versioning npm run test:dist
```

Publish only `website/dist/`. The same application and canonical article corpus are used; no second website implementation is permitted.

## Build and verification commands

From `website/`:

```bash
npm ci
npm audit --audit-level=high
npm test
npm run check
npm run build
npm run test:dist
```

The source-evidence workflow additionally runs the Python Segment Lab against the triggering source commit, verifies generator determinism, and then runs the website checks and both static builds.

## Non-negotiable product and technical constraints

1. The Python package source and its tests are the behavioral source of truth.
2. Keep `docs/articles/` as the only editable article corpus and publish all 25 articles in full.
3. Reuse the existing `integration_test_project/`; do not create a parallel Django project.
4. Do not reuse the Agent's old package 0.3.5 evidence.
5. Do not hand-edit generated route evidence or command output; preserve source commit, package version, hashes, and scenario provenance.
6. Keep the published site static and independent of Netlify runtime functions.
7. Preserve the ten homepage content responsibilities and their agreed order; visual layout and presentation are free to change.
8. Label Segment Diagram/Explorer as explanatory visualizations of recorded data, not actual Python execution. Preserve a useful no-JavaScript fallback.
9. Keep DRF request-version identification separate from package endpoint registration.
10. Preserve required site capabilities and target WCAG 2.2 AA. Do not claim accessibility, performance, or deployment acceptance until those checks have actually run.
11. The redesign may change frontend technology and implementation architecture; update build, test, and hosting instructions to match the resulting implementation.
