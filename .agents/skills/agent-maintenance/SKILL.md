---
name: agent-maintenance
description: Change repository coding-agent instructions, skills, adapters, helper scripts, evaluation scenarios, or agent-tooling CI.
---


# Agent maintenance

Use only when changing the agent system itself: shared instructions, skill metadata/content, client adapters, helper scripts, evaluation scenarios, or agent CI.

## Workflow

1. Run `python scripts/agent.py context agent-maintenance` and inspect the current branch, complete diff, canonical skill inventory, and helper tests.
2. Change each policy or workflow in one canonical location. Client-specific files are discovery adapters only; do not copy policy or skill bodies.
3. Keep always-loaded files within the configured character budgets. Put task detail in the matching on-demand skill and deterministic repeated work in dependency-free scripts.
4. Keep tool permissions narrow. Diagnostics must be read-only; no helper should silently install tools, modify Git state, push, publish, or execute destructive actions.
5. Add or update deterministic tests for frontmatter, adapters, path targets, context profiles, scenario metadata, and budget constraints.
6. Update representative scenarios in `.agents/evals/scenarios.json` when an observed agent failure or important workflow is added. Scenarios are human/model-run acceptance tests, not automated proof of model quality.
7. Run `python scripts/agent.py verify`, inspect its exact output, parse changed workflows, and review the full diff.

## Performance acceptance

- One canonical skill body per workflow.
- Small always-loaded policy files with an explicit measured character budget and approximate token estimate.
- Skill metadata is concise and task-specific for reliable discovery.
- Context profiles recommend only the files needed for that task and explicitly identify what to avoid.
- No model pin or unnecessary external dependency.
- CI for agent tooling runs independently from package compatibility tests.

Do not claim a model's task accuracy or token savings without executing the same versioned scenarios on the relevant agent/model and recording the prompt, context, tool versions, output, and human-reviewed result.
