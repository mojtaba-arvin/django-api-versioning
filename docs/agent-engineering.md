
# Agent tooling architecture

This document records the integration map only. Shared repository rules live in `AGENTS.md`; task procedures live in canonical Agent Skills.

## One workflow, thin client adapters

| Client | Discovery entry point | Workflow source |
| --- | --- | --- |
| Codex and compatible Agent Skills clients | `.agents/skills/` | `.agents/skills/<skill>/SKILL.md` |
| Claude Code | `.claude/skills/<skill>/SKILL.md` | `.agents/skills/<skill>/SKILL.md` |
| GitHub Copilot review | `.github/skills/package-review/SKILL.md` | `.agents/skills/package-audit/SKILL.md` |

Client adapters carry only discovery metadata and a pointer. Do not copy workflow bodies between clients.

## Progressive disclosure

1. Load concise shared instructions and skill metadata.
2. Load only the matching skill body for the task.
3. Follow deeper references only when that subtask is reached.
4. Delegate repeated deterministic work to scripts; return concise structured facts rather than asking a model to re-derive them.

A skill must have a clear trigger, bounded responsibility, input requirements, verification criteria, and stop conditions.

## Local helpers

- `python scripts/agent.py doctor`: read-only repository and tool diagnostics.
- `python scripts/agent.py context <profile>`: task-specific reading list.
- `python scripts/agent.py validate`: validate skill metadata, adapters, and instruction budgets.
- `python scripts/agent.py verify`: validation plus the helper's standard-library tests.

The helper has no third-party dependencies and is excluded from the distributable package. Its independent CI workflow does not run the package compatibility matrix.

## Tool and model policy

The repository does not force a model selection. Use deterministic project tooling for correctness. MCP, agent frameworks, model APIs, hosted evaluations, and tracing backends are optional integrations—not defaults—and require an actual workflow need plus justified permissions, failure modes, and maintenance cost.

## Format references

- [Agent Skills specification](https://agentskills.io/specification)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Codex skills](https://developers.openai.com/codex/skills/)
- [GitHub Copilot code-review skills](https://github.blog/changelog/2026-07-29-copilot-code-review-agent-skills-and-mcp-now-generally-available/)
