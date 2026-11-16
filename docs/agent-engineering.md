
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


## Comparing agent behavior

`python scripts/agent.py evals --json` lists the versioned task scenarios and acceptance checks. Use them as a controlled, model-agnostic benchmark:

1. Compare baseline and candidate setups at the same repository commit, with fresh sessions and identical task prompts. Record agent/client version and model/provider identifiers.
2. Run every scenario independently. Do not carry hidden context or prior answers between runs.
3. Score each dimension from 0 (fail) to 2 (fully satisfies): correctness, source evidence, scope discipline, context/tool efficiency, and safety/honest reporting. A human reviews ambiguous results.
4. Record actual input/output token counts and tool-call counts only when the client exposes them. Also record files read, checks executed, elapsed time if relevant, and the exact scenario revision.
5. Compare per-scenario scores and total token/tool usage. Do not claim a model is more accurate or cheaper from one task or from character-count estimates. The helper's chars/4 figures are rough instruction-budget estimates, not provider tokenization or end-to-end usage.

The suite is intentionally not an LLM-as-judge pipeline. It can be used across clients and models without provider SDKs, secrets, or non-deterministic network calls in package CI.

## Historical behavior lessons

The historical review of 418 commits from 2026-11-14 through 2026-11-15 on `audit/comprehensive-package-review` is recorded in [docs/agent-history-audit-418.md](agent-history-audit-418.md). It is a bounded interval, not a review of the complete repository history. Its recurring findings are now guardrails: avoid duplicate status trackers, batch formatting and related workflow edits, preserve generated-evidence timestamps when content is unchanged, and attribute automation commits to the GitHub Actions bot. The broader 651-commit repository evolution review is recorded in [docs/repository-evolution-audit.md](repository-evolution-audit.md).

## Format references

- [Agent Skills specification](https://agentskills.io/specification)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Codex skills](https://developers.openai.com/codex/skills/)
- [GitHub Copilot code-review skills](https://github.blog/changelog/2026-07-29-copilot-code-review-agent-skills-and-mcp-now-generally-available/)
