
# Agent tooling architecture

This document records the integration map only. Shared repository rules live in `AGENTS.md`; task procedures live in canonical Agent Skills.

## One workflow, thin client adapters

| Client | Discovery entry point | Workflow source |
| --- | --- | --- |
| Codex and compatible Agent Skills clients | `.agents/skills/` | `.agents/skills/<skill>/SKILL.md` |
| Claude Code | `.claude/skills/<skill>/SKILL.md` | `.agents/skills/<skill>/SKILL.md` |
| GitHub Copilot review | `.github/skills/package-review/SKILL.md` | `.agents/skills/package-audit/SKILL.md` |

Client adapters carry only discovery metadata and a pointer. Do not copy workflow bodies between clients.

## Instruction ownership and scope

- Root `AGENTS.md` is the shared repository contract. Scoped instruction files such as `website/AGENTS.md` may add constraints for their subtree but cannot override root safety, Git, release, or contribution policy.
- All task skills are canonicalized in the repository-root `.agents/skills/`; Claude and Copilot entries are thin adapters. Do not create nested `.agents/skills/` or `.claude/skills/` registries inside projects.
- Website-specific implementation constraints live in `website/AGENTS.md`; website work uses the root `website-engineering` skill. Framework starter notes that describe removed integrations are not project policy and must not be copied into the repository.

## Workflow permissions and automation commits

- Every GitHub Actions workflow defaults to `contents: read`; third-party Actions are pinned to full commit SHAs.
- The manually dispatched evidence workflow generates and verifies artifacts in a read-only job with checkout credentials disabled. A separate commit-only job receives `contents: write`, does not run repository code, verifies that the branch still points to the triggering SHA, and uses a normal fast-forward push.
- Only the PyPI publication job receives `id-token: write`. Deterministic repository policy checks enforce these boundaries.

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

Historical review findings adopted as operating guardrails: avoid duplicate status trackers, batch formatting and related workflow edits, preserve generated-evidence timestamps when content is unchanged, and attribute automation commits to the GitHub Actions bot. The actionable rules belong in the root instructions, canonical skills, and deterministic checks—not in unmaintained audit snapshots.

## Format references

- [Agent Skills specification](https://agentskills.io/specification)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Codex skills](https://developers.openai.com/codex/skills/)
- [GitHub Copilot code-review skills](https://github.blog/changelog/2026-07-29-copilot-code-review-agent-skills-and-mcp-now-generally-available/)
