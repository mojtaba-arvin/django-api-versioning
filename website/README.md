# Documentation website

This directory is the reserved project root for the Astro documentation website.

The Astro application has not yet been scaffolded. Do not treat this directory as deployable until it contains its package manifest and lockfile, Astro configuration, application source, and verified production build.

## Inputs

- Articles: `../docs/articles/` (canonical source; do not create a second tracked article corpus).
- Package implementation: `../django_api_versioning/`.
- Integration scenarios and evidence generation: reuse `../integration_test_project/`.
- Architecture and requirements: `../docs/website/architecture.md`.
- Agent implementation rules: `../AGENTS.md`.

## Intended Netlify settings

- Base directory: `website`
- Build command: `npm run build`
- Publish directory: `dist` (relative to this directory)

The same static `dist/` output must also be publishable through GitHub Pages. Netlify must not be a runtime dependency.
