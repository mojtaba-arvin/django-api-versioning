
# Claude Code adapter

Read the repository-root `AGENTS.md`; it owns shared policy. Do not duplicate it here.

- Claude discovers skills through `.claude/skills/`. Each project skill is a thin adapter to its canonical workflow in `.agents/skills/`.
- Before broad exploration, run `python scripts/agent.py context <profile>`. Use `doctor` for read-only diagnostics and `validate` after agent-configuration edits.
- Invoke only the matching skill: `/package-engineering`, `/package-audit`, `/manual-testing`, `/website-engineering`, `/agent-maintenance`, `/safe-checkpoint`, `/session-recovery`, or `/release`.
- A skill is not permission to publish, tag, perform destructive actions, make external writes, or push. Apply the current user's authorization and the shared repository policy.
- Do not force a project-level model choice; respect the user's model and execution environment.
