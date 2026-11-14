# Documentation website

The repository contains a **partial Astro foundation**, not a completed or deployable website. Configuration, shared layout, design tokens, logo, content-collection setup, article synchronization, and typed evidence helpers have been recovered and adapted from the interrupted Netlify Agent session.

The application is incomplete. It currently lacks page routes, generated behavioral evidence, runtime scripts and styles imported by the layout, a dependency lockfile, and static-output smoke-test scripts. No successful Astro production build or deployment has been recorded.

## Inputs

- Articles: `../docs/articles/` (canonical source; do not create a second editable article corpus).
- Package implementation: `../django_api_versioning/`.
- Integration scenarios and evidence generation: reuse `../integration_test_project/segment_lab/`.
- Architecture and requirements: `../docs/website/architecture.md`.
- Current implementation status and phase gates: `../docs/website/implementation-status.md`.
- Agent implementation rules: `../AGENTS.md`.

## Intended Netlify settings

- Base directory: `website`
- Build command: `npm run build`
- Publish directory: `dist` (relative to this directory)

The same static `dist/` output must also be publishable through GitHub Pages. Netlify must not be a runtime dependency.

Do not configure production deployment until the acceptance gates in `docs/website/implementation-status.md` have passed.
