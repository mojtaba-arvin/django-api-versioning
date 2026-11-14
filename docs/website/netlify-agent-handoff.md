# Netlify Agent handoff

Use this file together with the repository-root `AGENTS.md`.

## Where to find things

| Needed input | Exact path |
| --- | --- |
| Python package source | `django_api_versioning/` |
| Package version | `pyproject.toml` → `[project].version` |
| Package unit tests | `tests/` |
| Existing Django integration project | `integration_test_project/` |
| Existing long-form articles (25 files) | `docs/articles/` |
| Versioning contract | `docs/reference/versioning-contract.md` |
| Website architecture | `docs/website/architecture.md` |
| Website handoff rules | `AGENTS.md` and this file |
| Astro application root | `website/` |
| Generated evidence destination | `website/src/data/generated/` |
| Python-generated evidence source | Extend/reuse `integration_test_project/`; do not create another top-level lab |
| PyPI inclusion/exclusion policy | `pyproject.toml` and `MANIFEST.in` |

## Build/deploy configuration

The intended Netlify configuration is:
- Base directory: `website`
- Build command: `npm run build`
- Publish directory: `dist`

These values describe the target configuration. The repository currently contains only the website handoff scaffold; do not report a successful build or deployment until the Astro project and lockfile have been created and verified.

## Implementation constraints

1. Inspect the current source and integration project before writing code. Do not recreate the Django test project.
2. Use the checked-out package commit as the evidence baseline. Read the package version from `pyproject.toml`. Do not reuse the old 0.3.5 / `e5a5466...` evidence.
3. Preserve `docs/articles/` as the only tracked article corpus. Do not download or commit duplicate article copies.
4. Keep all Astro/Node code under `website/`.
5. Generate evidence from executable scenarios; include full commit provenance. Do not fabricate a missing JSON snapshot or CLI output.
6. Build static output only. No Netlify runtime functions.
7. Implement all ten homepage sections in the order defined by `docs/website/architecture.md`.
8. Keep explanatory diagrams clearly distinguished from actual Python execution.
9. Implement accessibility and no-JavaScript fallbacks before declaring completion.
10. Run package tests, evidence checks, Astro checks, production build, and static-host smoke tests. Report exact commands and results; never infer a pass.

## Recovered Agent work: reuse versus revalidate

A previous Netlify Agent session created useful Astro foundation code and a Django Segment Lab, but stopped before implementing pages or running an Astro build.

Useful design/code references from the captured session:
- Astro static output configuration and Markdown remark/rehype plugins.
- Typed data-access helpers for registry rows, request records, scenarios, and source references.
- Content collection design that uses Markdown file identity rather than assuming article slugs are unique.
- Segment Point logo concept and design tokens.
- Django scenarios covering basic forward inheritance, explicit version lists/ranges, minimum-version behaviour, import order, route-string identity, duplicate declarations, invalid declarations, lifecycle middleware, DRF defaults/URLPathVersioning, bare ViewSet decoration, and coexistence with a DRF router.
- A provenance-first generator design and a distribution comparison script.

Do not copy the old generator or output blindly. Its dependency pin targets 0.3.5 and its source-line assertions/output schema were authored for that package snapshot. Revalidate and adapt them against the current source before using them. The log did not contain the generated `routes.json` or generated `tools/README.md`; neither may be guessed.

The previous frontend was incomplete: it did not contain the homepage or article pages, and the log did not show successful Astro checks, production build, or static-output tests. Treat it as a source of implementation ideas, not a completed application.
