# Static website hosting handoff

## Final-agent scope

Continue on `audit/comprehensive-package-review`. This is a final review of an existing implementation, not a greenfield build.

- Do not recreate the Astro app, the Django mini-project, the article corpus, route evidence, or the original Netlify Agent's generated files.
- The recovered scenario code is already integrated into `integration_test_project/segment_lab/`; use its generator and tests. Do not create a parallel `tools/` Django project.
- `docs/articles/` is the only editable article source. The website synchronizes all 25 articles automatically.
- The committed Segment Lab snapshot is generated from the repository checkout, not the historical Netlify package 0.3.5 run. Never reuse that historical output.
- Review the existing site against the ten-section homepage contract, then focus on browser-level keyboard/mobile/accessibility checks, reduced motion, layout shift, and static-host behavior. Make only evidence-backed corrections and add focused tests.
- Do not run the full Python compatibility matrix for CSS/content-only changes. Run it only for package/runtime changes or the final release checkpoint.
- Do not publish to PyPI or deploy to production without explicit approval.

### Framework security exception

The original brief requested Astro 6. The Astro 6.4.8 baseline is no longer acceptable for a release candidate: current advisories include critical issues fixed only in later Astro 7 releases. The branch therefore intentionally targets Astro 7.4.12, with patched `esbuild` 0.28.1 and `sharp` 0.35.5 overrides. Do not downgrade to Astro 6 merely to match the original version line; any framework-major change must be justified by current security advisories and verified by the full website workflow.


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
| Website architecture and phase gates | `docs/website/architecture.md` and `docs/website/implementation-status.md` |
| Astro application root | `website/` |
| Generated evidence destination | `website/src/data/generated/` |
| PyPI inclusion/exclusion policy | `pyproject.toml` and `MANIFEST.in` |

## Netlify configuration

- Base directory: `website`
- Build command: `npm run build`
- Publish directory: `dist` (relative to the base directory)
- Node requirement: 22.23.4 or newer
- Install command: `npm ci` (Netlify's dependency install should use the committed lockfile)

Netlify's `URL` environment variable may be used as the canonical site URL. The site must remain static and must not depend on Netlify runtime functions.

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

## Non-negotiable implementation constraints

1. The Python package source is the behavioral source of truth.
2. Keep `docs/articles/` as the only editable article corpus.
3. Reuse the existing `integration_test_project/`; do not create a parallel Django project.
4. Do not reuse the Agent's old package 0.3.5 evidence.
5. Do not hand-edit generated route evidence or command output.
6. Keep static output independent of Netlify runtime functions.
7. Preserve the ten-section homepage contract.
8. Label Segment Diagram/Explorer as explanatory visualization, not actual Python execution, and preserve no-JavaScript fallback.
9. Keep DRF request-version identification separate from package endpoint registration.
10. Do not claim accessibility, performance, or deployment acceptance until those checks have actually run.
