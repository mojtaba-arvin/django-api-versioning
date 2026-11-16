# Documentation website

Static documentation website for `django-api-versioning`.

The sole source of website requirements and design freedom is [the website contract](../docs/website/architecture.md). This README contains local development and verification commands only.

## Requirements

- Node.js 22.23.4 or newer.
- npm bundled with the selected Node.js release.

## Development

Run from `website/`:

```bash
npm ci
npm run dev
```

## Verification

Run from `website/`:

```bash
npm audit --audit-level=high
npm test
npm run check
npm run build
npm run test:dist
```

To verify a GitHub Pages-style project base path:

```bash
PUBLIC_BASE_PATH=/django-api-versioning npm run build
PUBLIC_BASE_PATH=/django-api-versioning npm run test:dist
```

To serve the built output locally:

```bash
npm run serve:dist
```

Set `PUBLIC_BASE_PATH` when serving a project-site build as well.

## Regenerating recorded evidence

From the repository root, install `requirements-ci.txt` and run:

```bash
python integration_test_project/segment_lab/generate_routes.py
python integration_test_project/segment_lab/generate_routes.py --check
```
