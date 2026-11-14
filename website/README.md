# Documentation website

The repository contains a static Astro application for the `django-api-versioning` package. It publishes the canonical article corpus, explains the package's routing model, and displays executable Segment Lab evidence.

The site has passed CI checks and production builds for both root hosting and a GitHub Pages project-site base path. It has **not** been deployed. Browser-level accessibility/performance review and external hosting smoke tests remain part of the delivery plan.

## Source inputs

- Articles: `../docs/articles/` (the only editable article source).
- Package implementation: `../django_api_versioning/`.
- Integration scenarios and evidence generation: `../integration_test_project/segment_lab/`.
- Versioning contract: `../docs/reference/versioning-contract.md`.
- Architecture and phase gates: `../docs/website/architecture.md` and `../docs/website/implementation-status.md`.

## Requirements

- Node.js 22.23.4 or newer.
- npm version bundled with the selected Node release.
- A clean repository checkout with Git metadata for source provenance.
- Python dependencies are required only when regenerating Segment Lab evidence; the static Astro build consumes the committed snapshot.

## Local development and verification

Run these commands from `website/`:

```bash
npm ci
npm run dev
```

Run the same checks used by the website workflow:

```bash
npm audit --audit-level=high
npm test
npm run check
npm run build
npm run test:dist
```

To build for a GitHub Pages project site:

```bash
PUBLIC_BASE_PATH=/django-api-versioning npm run build
PUBLIC_BASE_PATH=/django-api-versioning npm run test:dist
```

To serve the already-built output locally:

```bash
npm run serve:dist
```

For a project-site base path, set `PUBLIC_BASE_PATH` when starting the server as well.

The build synchronizes Markdown from `../docs/articles/` and copies the committed evidence snapshot into the static output. Do not edit files under `src/content/articles/` or `public/data/` as source files; they are generated.

## Netlify settings

- Base directory: `website`
- Build command: `npm run build`
- Publish directory: `dist` (relative to `website`)

The same static `dist/` output must work on GitHub Pages and generic static hosts. Netlify is not a runtime dependency.

## Evidence regeneration

The source-evidence workflow runs when package source, the existing integration project, package metadata, or Python requirements change. It executes the Segment Lab against the triggering checkout, records provenance and input hashes, commits the generated snapshot, and validates the website in the same workflow.

For local regeneration, install `requirements-ci.txt` from the repository root and run:

```bash
python integration_test_project/segment_lab/generate_routes.py
python integration_test_project/segment_lab/generate_routes.py --check
```

Do not hand-edit `src/data/generated/routes.json` or `check_versions_output.txt`.

## Hosting status

No Netlify or GitHub Pages deployment has been performed. Do not configure production publishing until the browser, accessibility, performance, content, and external static-host checks in `../docs/website/implementation-status.md` have passed.
