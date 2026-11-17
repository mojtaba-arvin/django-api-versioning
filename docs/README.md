# Project documentation

The repository README is the human-friendly entry point: it explains the problem, shows the package in context, and includes installation and a Quick Start. It is also the README distributed on PyPI.

## Reference

- [Reference page source](reference/index.md): the canonical Markdown content rendered by the website's `/docs` page. Edit this file to update the page; do not maintain a second copy in React.
- [Canonical routing contract](reference/versioning-contract.md): the detailed technical contract for URL construction, registration semantics, collisions, URL reversal, Django REST Framework integration, and lifecycle behavior. Verify changes against package source and tests.

## Articles

- [Articles](articles/): the canonical article corpus used by the website and generated RSS feed.

## Website

The static website renders the Reference source from `docs/reference/index.md`. During local development and builds, `website/scripts/sync-reference.mjs` copies it into the generated `website/content/reference/` input directory. Never edit that generated copy directly.

## Source-of-truth rules

- The root README is the package landing page and onboarding guide; it is not the complete API reference.
- `docs/reference/index.md` owns the human-facing content of the website Reference page.
- `docs/reference/versioning-contract.md` owns the detailed written routing contract.
- Package implementation and executable tests remain the ultimate authority for behavior. Documentation must be corrected when it diverges from them.
