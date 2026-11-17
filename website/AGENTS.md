# AGENTS.md

Static marketing and docs site for the `django-api-versioning` Python package. There's no backend, persistence or forms. Don't add any unless a feature really needs them. (Articles are rendered on the server from bundled markdown through TanStack server functions; that is not a separate backend.)

## Architecture

- TanStack Start (React 19) with file routes in `src/routes/`: `__root.tsx` (meta and Google Fonts links), `index.tsx` (home), `docs.tsx` (reference). `src/routeTree.gen.ts` is generated at build.
- `src/components/`
  - `HomePage.tsx`: all homepage sections as small local components.
  - `DocsPage.tsx`: reference tables and sections. Its table data is defined inline at the top of the file.
  - `Playground.tsx`: the interactive version-matrix editor.
  - `LifecycleDemo.tsx`: simulated HTTP responses per version.
  - `CodeBlock.tsx`: a dependency-free Python/bash highlighter plus a copy button.
  - `Layout.tsx`: header, footer, logo and GitHub icon.
- `src/lib/matrix.ts`: pure logic that models the package's routing rules (forward segments, explicit sets, ranges, min/max validation, collisions, gap detection) and lifecycle headers. It's covered by `matrix.test.ts`.
- `src/data/`: `site.ts` holds links and the name. `content.ts` holds snippets, features, patterns and caveats.
- Articles: the canonical source is the repository-root `docs/articles/*.md`. `content/articles/*.md` is a generated build input copied locally from that directory by `pnpm run sync:articles` (also run automatically before `pnpm build`). Never download articles from GitHub or another remote branch during a build, and never edit the generated copies by hand. Make article edits only in the root `docs/articles/` corpus. `src/lib/articles.ts` parses front matter and renders markdown with `marked` (tested in `articles.test.ts`). `src/server/articles.ts` bundles the files and exposes server functions. Routes: `/articles`, `/articles/$slug`, `/rss.xml`. Article styles live under `.prose-article` in `src/styles.css`. `src/lib/highlight.ts` is the shared code highlighter used by `CodeBlock` and articles.

## Conventions

- Dark theme. Colour and font tokens are defined in `@theme` in `src/styles.css` (`ink`, `paper`, `mute`, `line`, `leaf`, `amber`, `rose`). Use these tokens instead of raw hex values.
- Shared utility classes: `.btn`, `.btn-primary`, `.btn-ghost`, `.card`, `.eyebrow`, `.section-title`, `.inline-code`, `.tok-*`.
- Every factual claim about the package must match the upstream README at https://github.com/mojtaba-arvin/django-api-versioning. Don't invent APIs, return values or CLI output. For example, `assert_version_matrix` is imported from `django_api_versioning.testing`.
- The playground is an illustration of the documented rules, not the real implementation. Keep the copy saying so.
- `LifecycleDemo` starts with a fixed date so SSR and hydration render the same output, then switches to the real clock in an effect. Keep browser-only APIs inside effects and handlers.
