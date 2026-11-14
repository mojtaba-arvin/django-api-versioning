# Website implementation status and delivery plan

> **Status date:** 2026-11-14  
> **Audited branch:** `audit/comprehensive-package-review`  
> **Audited source commit:** `9b09d66c931f6e99687664da7442ddf9198595cb`  
> **Deployment status:** Not deployable; no successful Astro production build or static-host smoke test has been recorded.

This is a working engineering status document, not a claim that any unfinished gate has passed. Update it at each completed milestone using the exact commit and commands that were verified.

## 1. Current repository baseline

| Area | Current state | Delivery assessment |
| --- | --- | --- |
| Python package | Version 0.3.7; package source and tests are present | 211 unit tests, 249 integration tests, and 96% package coverage; all 15 tox environments and lint passed at the audited checkpoint |
| Package distribution | Package allowlist, sdist pruning, and artifact-content verification are present | Re-run wheel/sdist build and inspect actual artifacts before release |
| Django integration project | Existing project is retained and extended | Do not create a parallel integration project |
| Segment Lab | 18 executable scenario definitions and a generator/probe are present | Provenance and scenario tests passed across the full compatibility matrix; generated website evidence is not yet committed |
| Article corpus | 25 canonical Markdown articles under `docs/articles/` | Preserve as the only editable source |
| Astro application | Partial foundation: config, layout, styles, data helpers, article sync and logo | Incomplete; cannot yet build |
| Website deployment | No verified `dist/`, Netlify deployment, or GitHub Pages deployment | Not ready |

### 1.1 Concrete Astro build blockers

The audited tree currently has these gaps:

- No `website/src/pages/` routes: no homepage, article index/detail routes, evidence page, or explorer page.
- `website/src/layouts/Base.astro` imports `src/styles/site.css` and `src/scripts/site.ts`, but neither file exists.
- `website/src/lib/data.ts` imports `src/data/generated/routes.json`, but no generated evidence JSON exists in the tree.
- No `website/package-lock.json` is present, so dependency installation is not yet reproducibly locked.
- `package.json` exposes `serve:dist` and `test:dist`, but their referenced `scripts/serve-dist.mjs` and `scripts/check-dist.mjs` are absent.
- The layout preloads `/fonts/*.woff2` paths, while no corresponding `website/public/fonts/` assets are tracked.
- The layout and stylesheet use root-absolute paths. Astro's configurable `base` alone does not rewrite arbitrary authored `href="/..."`, `src="/..."`, or CSS `url("/...")` values for GitHub Pages project-site deployments.
- `website/README.md` previously described the Astro app as not scaffolded, which no longer matches the partial application files that are present.

These are blockers, not cosmetic cleanup. Do not configure a production deployment until the pages, evidence input, lockfile, scripts, assets, and base-path behavior are implemented and tested.

## 2. Segment Lab evidence integrity

The current lab contains 18 scenarios, including the existing integration project and DRF router, import-order behavior, explicit versions, minimum-version boundaries, route identity, DRF request-version behavior, ViewSet rejection, lifecycle middleware, and invalid declarations. The latest full matrix passed all 15 Python/Django environments plus lint at commit `9b09d66c931f6e99687664da7442ddf9198595cb`.

The generator runs each scenario in a fresh interpreter because the package registry and settings are process-global/import-time state. It reads the package version from `pyproject.toml`, records the checked-out commit, and derives source references from the checked-out package.

A provenance gap was found during this audit: before commit `34ffa802d9acbd94edd900e35287941a7779c42a`, the generator rejected dirty package files but did not reject dirty executable lab files, and it did not hash the scenario/generator inputs. That commit now:
- rejects uncommitted changes under `integration_test_project/` as well as package source and `pyproject.toml`;
- records SHA-256 hashes for `pyproject.toml` and Python files in the integration project as `source.evidence_files`;
- verifies those hashes in the generator tests; and
- updates the TypeScript data contract for the new provenance field.

The provenance hardening has now been exercised by the full compatibility matrix: the generator tests verify the package hashes and the `evidence_files` hashes for `pyproject.toml` and the executable integration project. The evidence snapshot itself has not yet been generated or committed.

Do not fabricate `routes.json` or copy the old Agent's 0.3.5 outputs. Generate the snapshot from one clean, committed checkout and commit the resulting data only after reviewing its provenance and scenario results.

## 3. Recovered Netlify Agent work

The captured Agent session was interrupted by exhausted credits. It did not complete a site, run an Astro build, or deploy. Its evidence was tied to package 0.3.5 and must not be reused as current behavior.

Useful code has been adapted into the current repository as follows:

| Captured Agent area | Current repository location | Treatment |
| --- | --- | --- |
| Astro config, layout, logo, global design tokens | `website/astro.config.mjs`, `website/src/layouts/`, `website/src/components/Logo.astro`, `website/src/styles/global.css` | Foundation retained; imports, paths, and runtime behavior still need completion |
| Content collection and article-link plugins | `website/src/content.config.ts`, `website/src/lib/`, `website/scripts/sync-articles.mjs` | Adapted to canonical `docs/articles/`; requires link and route tests |
| Typed evidence access | `website/src/lib/data.ts` | Adapted; generated JSON is not present yet |
| Django scenarios and probe | `integration_test_project/segment_lab/` | Adapted to current source and expanded to 18 scenarios |
| Evidence generator | `integration_test_project/segment_lab/generate_routes.py` | Reworked for current checkout provenance; package and lab input hashes are covered by passing matrix tests |
| Distribution verifier | `scripts/verify_distribution_contents.py` | Repository implementation is present; validate against actual build artifacts |

The temporary `s.py` scratch experiment is excluded. The missing old `routes.json` and `tools/README.md` were not reconstructed from guesses.

## 4. Delivery phases and acceptance gates

### Phase A — Baseline and source audit
- Re-read the current package, tests, integration project, articles, reference contract, workflows, and recovered Agent source.
- Resolve inconsistencies between code, tests, changelog, README, reference docs, and article claims.
- Keep findings classified as confirmed defect, documentation drift, compatibility decision, or unverified hypothesis.
- **Accept when:** every public behavior claim used by the site has an implementation/test locator or is explicitly marked unverified.

### Phase B — Package correctness and compatibility
- Audit registration precedence, route identity, URL reversal, import-order requirements, settings validation, lifecycle behavior, management commands, typing, and error paths.
- Audit Python/Django/DRF compatibility claims against the actual tox matrix and compatibility report.
- Add focused regression tests for confirmed defects; avoid tests that merely restate implementation details.
- **Accept when:** unit and integration suites pass at the chosen source commit, and all known defects are fixed or explicitly accepted with rationale.

### Phase C — Documentation and article corpus
- Audit all 25 articles against the canonical versioning contract and current source.
- Verify code examples, imports, URLconf patterns, DRF boundaries, package-version statements, internal links, metadata, and duplicate/colliding slugs.
- Preserve article meaning and useful editorial intent; do not silently replace a technical claim with generic guidance.
- **Accept when:** all blocking technical/editorial findings are resolved and corpus-wide consistency checks pass.

### Phase D — Reproducible evidence pipeline
- Execute every Segment Lab scenario against the same clean commit.
- Validate request results, registry rows, reverse lookups, command output, errors, logs, source references, and source hashes.
- Add deterministic `--check` validation and tests for expected failure scenarios as well as successful scenarios.
- **Accept when:** generated evidence is reproducible, provenance is complete, and no scenario output is hand-authored.

### Phase E — Astro application completion
- Add the ten homepage sections in the order defined by `architecture.md`.
- Add article index and detail routes, evidence route, and Segment Explorer.
- Complete the shared layout, site runtime, CSS, font strategy, search, theme, mobile navigation, reading progress, heading anchors, code copy, version/provenance panel, and reduced-motion behavior.
- Implement a shared base-path-aware URL strategy for internal links, public assets, and CSS assets.
- Add a committed lockfile and working local preview/static-server scripts.
- **Accept when:** clean dependency installation, Astro checks, and a production static build all pass.

### Phase F — Accessibility, correctness, and performance
- Test keyboard-only use, focus visibility, semantic landmarks, dialog behavior, mobile navigation, reduced motion, no-JavaScript fallbacks, and contrast.
- Verify all internal article links, heading anchors, search results, source permalinks, and route data.
- Smoke-test nested routes and assets from a generic static server under both root and non-root base paths.
- Measure build output, image/font loading, layout stability, and Core Web Vitals where a deployed environment is available.
- **Accept when:** WCAG 2.2 AA review has no unresolved blocker, static-host tests pass, and performance claims are measured rather than assumed.

### Phase G — CI/CD and hosting
- Add a separate Node/Astro workflow for `website/**` and `docs/articles/**`; keep it independent of Python tests and PyPI packaging.
- Preserve the optimized Python and artifact workflows, with explicit validation checkpoints and honest PR-status semantics.
- Add GitHub Pages deployment only after its base path and artifact have been tested; configure Netlify with base `website`, command `npm run build`, publish directory `dist`.
- **Accept when:** CI validates the same commands used locally and a deployment smoke test confirms the exact artifact.

### Phase H — Release readiness
- Verify package metadata, version, changelog, license, README links, wheel and sdist contents, installability from built artifacts, and compatibility claims.
- Run the complete release checklist from a clean checkout.
- Publish only after explicit final validation; verify the published artifact and release page.
- **Accept when:** PyPI artifacts and website deployment both correspond to documented, immutable source commits.

## 5. Working rules

1. A completed phase must have a commit trail and recorded validation evidence.
2. Prefer small, cohesive commits; do not create filler commits to inflate a count.
3. Run focused checks after each meaningful code change and broader checks at phase checkpoints.
4. Do not report a test, build, deployment, or release as successful unless it was actually executed.
5. Re-check the branch head before every Git write and use an expected-SHA update.
6. After each phase, define the next phase from the remaining confirmed work; do not stop at a status report.
