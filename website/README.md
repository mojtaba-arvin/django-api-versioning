# django-api-versioning website

The canonical project website for [django-api-versioning](https://github.com/mojtaba-arvin/django-api-versioning) ([PyPI](https://pypi.org/project/django-api-versioning/)), a decorator-based API versioning package for Django and Django REST Framework.

## What's on the site

- **Home (`/`)**: product overview, quick start, interactive version-matrix playground, lifecycle demo, reliability tooling, and caveats.
- **Reference (`/docs`)**: settings, `@endpoint` arguments, validation and collision rules, exceptions, management commands, and development setup.
- **Articles (`/articles`)**: the repository's canonical Markdown articles, rendered as individual static pages.
- **RSS (`/rss.xml`)**: generated from the same canonical article corpus during the build.

## Architecture

- TanStack Start + React 19 with file-based routes and static prerendering.
- Tailwind CSS v4; theme tokens live in `src/styles.css`.
- Vite emits a static deployable artifact under `dist/client/`.
- No Netlify adapter, Server Functions, API routes, or runtime server is required to serve the website.
- The site can be hosted on any static file host that supports the configured base path.

## Run locally

```bash
pnpm install
pnpm dev
pnpm test
pnpm typecheck
pnpm build
pnpm run test:dist:root
```

The default base path is `/`. To validate a GitHub Pages-style project site:

```bash
PUBLIC_BASE_PATH=/django-api-versioning SITE_URL=https://example.invalid pnpm build
pnpm run test:dist:subpath
```

Set `SITE_URL` to the final public origin when producing a production RSS feed. When omitted, the feed uses `http://localhost:3000` for local development.

## Editing content

Most site copy lives in `src/data/site.ts` (links and site identity) and `src/data/content.ts` (snippets, features, patterns, and caveats). Reference tables live in `src/components/DocsPage.tsx`.

The canonical article source is the repository-root `docs/articles/` directory. Edit articles there. `pnpm run sync:articles` copies the local corpus into `website/content/articles/` and generates `website/public/rss.xml`; `pnpm build` and `pnpm test` run this synchronization automatically. The build does not fetch article content from GitHub or another branch. Do not edit generated copies or the RSS feed directly.

When package behavior or the README changes, verify all package-specific claims and examples on the site against the implementation and canonical package documentation.
