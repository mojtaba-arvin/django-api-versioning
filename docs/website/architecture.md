# Documentation website contract

This file defines the complete set of hard requirements for the website. Historical handoffs, audits, status reports, previous designs, and implementation descriptions do not create additional requirements.

## Hard invariants

- **Static delivery:** the build produces static files for generic static hosting. The deployed site has no runtime dependency on Netlify, serverless functions, a database, or Python.
- **Base paths:** internal links, assets, and generated routes work both at the root and under a configured project-site base path.
- **Recorded evidence:** diagrams and explorers visualize recorded repository data; they do not execute Python in the browser or invent results. Generated evidence remains traceable to its recorded source and must not be hand-edited.
- **Article source:** `docs/articles/` is the sole editable article corpus. Any staged copies, collections, or indexes are derived build output, not independent sources.
- **Accessibility:** target WCAG 2.2 AA. Use semantic markup, keyboard-operable controls, visible focus, and reduced-motion support. Core content must remain useful when JavaScript is unavailable.
