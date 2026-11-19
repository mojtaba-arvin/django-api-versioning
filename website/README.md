# django-api-versioning website

The canonical project website for [django-api-versioning](https://github.com/mojtaba-arvin/django-api-versioning) ([PyPI](https://pypi.org/project/django-api-versioning/)), a declarative URL-path API versioning package for Django and Django REST Framework, with `@endpoint` registration and an optional `VersionedRouter` integration for DRF ViewSets.

## What's on the site

- **Home (`/`)**: product overview, quick start, interactive version-matrix playground, lifecycle demo, reliability tooling, and caveats.
- **Reference (`/reference/`)**: settings, `@endpoint` arguments, validation and collision rules, exceptions, management commands, and development setup.
- **Articles (`/articles/`)**: the repository's canonical Markdown articles, rendered as individual static pages.
- **RSS (`/rss.xml`)**: generated from the same canonical article corpus during the build.

## Architecture

- TanStack Start + React 19 with file-based routes and static prerendering.
- Tailwind CSS v4; theme tokens live in `src/styles.css`.
- Vite emits a static deployable artifact under `dist/client/`.
- No Netlify adapter, Server Functions, API routes, or runtime server is required to serve the website.
- The site can be hosted on any static file host that supports the configured base path.

## URL and search-discovery policy

- Page routes use one trailing slash: `/`, `/reference/`, `/articles/`, and `/articles/<slug>/`. This matches the static directory/index.html output and the article URLs already used by RSS.
- `/reference/` is the canonical Reference route. `/docs` and `/docs/` are legacy aliases: hosts that apply `_redirects` before existing files return 301; hosts where a static file shadows a non-forced redirect serve the HTML meta-refresh fallback. Use provider-specific redirect configuration if a host-level 301 is required.
- The build generates absolute canonical links, `sitemap.xml`, and `robots.txt` from `SITE_URL` and `PUBLIC_BASE_PATH`. `SITE_URL` must be the public origin only (scheme and host, no path); it is required for production builds. `PUBLIC_BASE_PATH` must be a root-relative path such as `/django-api-versioning`, without query/hash or unsafe segments. The repository does not guess the production domain.
- `sitemap.xml` contains only canonical page URLs, never legacy aliases. RSS article links use the same trailing-slash canonical URLs. On a project-subpath deployment, the generated `robots.txt` is also under that subpath; the Robots Exclusion Protocol only discovers a policy at the host root, so configure a host-root `robots.txt` separately or submit the subpath sitemap directly to search tools.

## Cache and deployment policy

The static artifact includes `public/_headers`, copied to `dist/client/_headers`. Hosts that support the `_headers` convention (including Netlify and Cloudflare Pages) apply these rules:

- HTML and unhashed public files (including `favicon.svg` and `rss.xml`) use `Cache-Control: public, max-age=0, must-revalidate`. They may be stored, but must be revalidated before reuse.
- Vite-generated files under `/assets/` use `Cache-Control: public, max-age=31536000, immutable`. Vite fingerprints their filenames, so changed content gets a new URL.

GitHub Pages and other hosts that do not implement `_headers` ignore this file. Configure equivalent response headers in that host's CDN or hosting settings; the repository cannot force HTTP cache behavior on a host that ignores its header configuration. The `test:dist` check ensures the header policy is present in every deployable artifact, but only a post-deployment HTTP check can confirm that the host actually sends it.

Deploy the complete `dist/client/` artifact as one release. Prefer atomic deployments, and retain old fingerprinted assets for a reasonable rollback/client-cache window rather than deleting them immediately. Do not apply long-lived immutable caching to HTML or unhashed public files.

## GitHub Pages deployment

The repository deploys the project site to `https://mojtaba-arvin.github.io/django-api-versioning/` through `.github/workflows/pages.yml`. The workflow runs on relevant changes to the website and its canonical article/reference content, and can also be started manually from the Actions tab.

The build uses `SITE_URL=https://mojtaba-arvin.github.io` and `PUBLIC_BASE_PATH=/django-api-versioning`, runs the website tests and type-check, then validates the complete static artifact before deployment. The build and deploy jobs are separate; only the deploy job receives `pages: write` and `id-token: write`.

GitHub Pages does not apply the generated `_headers` or `_redirects` files. The cache rules remain validated as part of the portable artifact contract, but GitHub Pages controls the actual HTTP cache headers. The static `/docs/` fallback remains available, while provider-level 301 redirects are not configured on GitHub Pages. The project sitemap is available at `/django-api-versioning/sitemap.xml`; submit that URL directly to search engines because the generated robots file lives under the project path, not the host root.

## Run locally

```bash
pnpm install
pnpm dev
pnpm test
pnpm typecheck
SITE_URL=https://example.com pnpm build
SITE_URL=https://example.com pnpm run test:dist:root
```

The default base path is `/`. To validate a GitHub Pages-style project site:

```bash
PUBLIC_BASE_PATH=/django-api-versioning SITE_URL=https://example.invalid pnpm build
PUBLIC_BASE_PATH=/django-api-versioning SITE_URL=https://example.invalid pnpm run test:dist:subpath
```

Set `SITE_URL` to the final public origin for production builds (scheme and host only, without a path). It is required for canonical URLs, RSS, sitemap, and robots metadata. Local development can omit it; the RSS feed then uses `http://localhost:3000`.

## Editing content

Homepage copy and snippets live in src/data/site.ts and src/data/content.ts.

The Reference page at `/reference/` is rendered from the canonical repository file ../docs/reference/index.md. Edit that Markdown file—not src/components/ReferencePage.tsx or the generated copy. pnpm run sync:reference copies it into website/content/reference/index.md; pnpm dev, pnpm test, and pnpm build run this synchronization automatically. The React page owns presentation, navigation, and styling only.

The detailed package behavior contract lives in ../docs/reference/versioning-contract.md. Package implementation and executable tests remain authoritative when checking technical claims.

The canonical article source is the repository-root docs/articles/ directory. Edit articles there. pnpm run sync:articles copies this local corpus into website/content/articles/ and generates website/public/rss.xml, sitemap.xml, robots.txt, and _redirects; pnpm build and pnpm test run this synchronization automatically. The build does not fetch article content from GitHub or another branch. Do not edit generated copies or the RSS feed directly.
