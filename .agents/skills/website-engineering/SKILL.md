---
name: website-engineering
description: Change or verify the static documentation website, content pipeline, generated evidence, accessibility, or deployment behavior.
---

# Website engineering

Use for website source, content-pipeline, generated evidence, accessibility, static output, or deployment work. This skill does not authorize deployment or publishing.

## Start and scope

1. Run `python scripts/agent.py context website`.
2. Read `docs/website/architecture.md`. It is the sole canonical source for website-specific hard requirements and design freedom.
3. Do not infer requirements from old handoffs, audits, status reports, screenshots, credit budgets, or the current page/component structure.
4. Inspect the affected website routes, components, scripts, and tests. Verify package claims against current source and executable evidence.

## Verification

Run the relevant website tests, static build, and root/base-path checks for the changed scope. Verify changed user-facing flows in a real browser, including responsive behavior, keyboard operation, focus visibility, reduced motion, and the no-JavaScript experience. Build success alone does not prove accessibility or deployment readiness.

Report PASS, FAIL, and NOT RUN accurately. Do not publish or deploy without explicit authorization.
