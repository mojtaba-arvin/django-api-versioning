# django-api-versioning website

The project website for [django-api-versioning](https://github.com/mojtaba-arvin/django-api-versioning) ([PyPI](https://pypi.org/project/django-api-versioning/)), a decorator-based API versioning package for Django and Django REST Framework.

## What's on the site

- **Home (`/`)**: hero with a copyable install command, feature overview, a three-step quick start, registration patterns, an interactive **version-matrix playground**, a **lifecycle headers demo** (Deprecation, Sunset and 410 Gone), the reliability tooling, and caveats.
- **Reference (`/docs`)**: settings, `@endpoint` arguments, validation and collision rules, exceptions, management commands and development setup.

## Tech

- [TanStack Start](https://tanstack.com/start) + React 19, file-based routes
- Tailwind CSS v4 (theme tokens in `src/styles.css`)
- Vitest for unit tests
- Deployed on Netlify

## Run locally

```bash
pnpm install
pnpm dev          # http://localhost:3000
pnpm test
```

Or run `netlify dev` to use the Netlify dev proxy.

## Editing content

Most copy lives in `src/data/site.ts` (links, name) and `src/data/content.ts` (code snippets, features, patterns, caveats). The reference tables are in `src/components/DocsPage.tsx`.

The canonical article source is the repository-root `docs/articles/` directory. Edit articles there. `pnpm run sync:articles` copies that local corpus into `website/content/articles/`; `pnpm build` runs this sync automatically before building. The website build does not fetch article content from GitHub or depend on network access. Do not edit the generated copies under `website/content/articles/` directly.

When package behavior or the README changes, verify all package-specific claims and examples on the site against the implementation and canonical package documentation.
