---
name: website-engineering
description: Change or verify the static documentation website, content pipeline, generated evidence, accessibility, or deployment behavior.
---


# Website engineering

Use for website source, content-pipeline, generated evidence, accessibility, static output, or deployment work. This skill does not authorize deployment or publishing.

## Start and scope

1. Run `python scripts/agent.py context website`.
2. Read `docs/website/architecture.md` before changing website structure, build tooling, routes, deployment, or evidence flow.
3. Inspect only the affected website routes/components/scripts and their tests. Keep `docs/articles/` as the only editable article source.
4. For package behavior displayed by the site, verify the exact source commit and executable evidence; generated route data is derived output, never hand-edited.

## Constraints

- The published site must be static and work on generic static hosts and GitHub Pages project paths.
- Do not introduce a runtime dependency on Netlify, serverless functions, a database, or Python.
- Preserve article provenance, generated-evidence integrity, and package distribution boundaries.
- Preserve keyboard operation, visible focus, reduced motion, semantic markup, and a useful no-JavaScript fallback.
- Treat diagrams and explorers as visualizations of recorded output, not live code execution.

## Verification

Run the relevant website preflight, static build(s), base-path checks, and browser-level checks required by the architecture document. Build success alone does not prove accessibility, performance, external-host behavior, or deploy readiness. Report every unrun browser/host gate explicitly.
