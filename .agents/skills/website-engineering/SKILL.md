---
name: website-engineering
description: Change or verify the static documentation website, local article pipeline, static output, or deployment configuration.
---

# Website engineering

Use for website source, the repository-local article pipeline, static output, or deployment-configuration work. This skill does not authorize deployment or publishing.

## Start and scope

1. Run `python scripts/agent.py context website`.
2. Read `website/AGENTS.md` for website-specific constraints. Root `AGENTS.md` remains authoritative for shared policy.
3. Do not infer requirements from old handoffs, audits, status reports, screenshots, credit budgets, or the current page/component structure.
4. Inspect the affected website routes, components, scripts, and tests. Verify package claims against current source and executable evidence.

## Verification

Run the relevant website tests, type checks, static build, and root/base-path distribution checks for the changed scope. Inspect generated files and links against the current static-only architecture. Do not treat browser accessibility or responsive audits as required unless the user explicitly brings them into scope.

Report PASS, FAIL, and NOT RUN accurately. Do not publish or deploy without explicit authorization.
