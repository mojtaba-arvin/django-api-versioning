# Documentation website contract

This file defines the complete set of hard requirements for the website. Historical handoffs, audits, status reports, previous designs, and implementation descriptions do not create additional requirements.

## Hard invariants

- **Static delivery:** the build produces static files for generic static hosting. The deployed site has no runtime dependency on Netlify, serverless functions, a database, or Python.
- **Base paths:** internal links, assets, and generated routes work both at the root and under a configured project-site base path.
- **Recorded evidence:** diagrams and explorers visualize recorded repository data; they do not execute Python in the browser or invent results. Generated evidence remains traceable to its recorded source and must not be hand-edited.
- **Article source:** `docs/articles/` is the sole editable article corpus. Any staged copies, collections, or indexes are derived build output, not independent sources.
- **Accessibility:** target WCAG 2.2 AA. Use semantic markup, keyboard-operable controls, visible focus, and reduced-motion support. Core content must remain useful when JavaScript is unavailable.
- **Technical accuracy:** package behavior and capability claims must be checked against current package source and executable tests, not inferred from website copy or historical records.

## Design and implementation freedom

Everything not listed under **Hard invariants** is intentionally open. This includes the framework, build tooling, visual direction, design system, page and route structure, homepage section count and order, information architecture, component tree, navigation, interactions, and content presentation.

Do not preserve or recreate the current website merely because it exists. Do not treat old briefs, screenshots, handoffs, audits, implementation trees, credit budgets, or previous section lists as design requirements.

## Verification

Verify static output at the root and at a non-root project base path. Test changed user-facing flows in a real browser, including keyboard use and accessibility. A successful build alone does not establish browser-level accessibility or deployment behavior.
