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

## Cache and deployment policy

The static artifact includes `public/_headers`, copied to `dist/client/_headers`. Hosts that support the `_headers` convention (including Netlify and Cloudflare Pages) apply these rules:

- HTML and unhashed public files (including `favicon.svg` and `rss.xml`) use `Cache-Control: public, max-age=0, must-revalidate`. They may be stored, but must be revalidated before reuse.
- Vite-generated files under `/assets/` use `Cache-Control: public, max-age=31536000, immutable`. Vite fingerprints their filenames, so changed content gets a new URL.

GitHub Pages and other hosts that do not implement `_headers` ignore this file. Configure equivalent response headers in that host's CDN or hosting settings; the repository cannot force HTTP cache behavior on a host that ignores its header configuration. The `test:dist` check ensures the header policy is present in every deployable artifact, but only a post-deployment HTTP check can confirm that the host actually sends it.

Deploy the complete `dist/client/` artifact as one release. Prefer atomic deployments, and retain old fingerprinted assets for a reasonable rollback/client-cache window rather than deleting them immediately. Do not apply long-lived immutable caching to HTML or unhashed public files.

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

Homepage copy and snippets live in src/data/site.ts and src/data/content.ts.

The Reference page is rendered from the canonical repository file ../docs/reference/index.md. Edit that Markdown file—not src/components/DocsPage.tsx or the generated copy. pnpm run sync:reference copies it into website/content/reference/index.md; pnpm dev, pnpm test, and pnpm build run this synchronization automatically. The React page owns presentation, navigation, and styling only.

The detailed package behavior contract lives in ../docs/reference/versioning-contract.md. Package implementation and executable tests remain authoritative when checking technical claims.

The canonical article source is the repository-root docs/articles/ directory. Edit articles there. pnpm run sync:articles copies this local corpus into website/content/articles/ and generates website/public/rss.xml; pnpm build and pnpm test run this synchronization automatically. The build does not fetch article content from GitHub or another branch. Do not edit generated copies or the RSS feed directly.
