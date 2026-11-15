---
name: package-review
description: Review proposed changes to this repository for correctness, regressions, security, compatibility, packaging, and documentation accuracy. Use during GitHub Copilot code review.
---


# Copilot review adapter

Read root `AGENTS.md` and canonical `../../../.agents/skills/package-audit/SKILL.md`. Review the actual pull-request diff and trace changed behavior through implementation, callers, and tests. Report actionable findings only, with severity, exact location, impact, evidence, and the smallest safe recommendation. Do not duplicate the canonical audit checklist.
