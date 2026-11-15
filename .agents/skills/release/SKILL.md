---
name: release
description: Execute the repository release workflow for an explicitly authorized version. Never publish or tag unless the user authorizes that release.
---

# Skill: /release — cut a version

Triggered by "release X.Y.Z". Do exactly this. No improvisation.

## Preconditions
- Working tree clean (`git status`).
- On `audit/comprehensive-package-review`.
- User has authorized a PyPI release for THIS version.
- `docs/articles/` exists; enumerate the current article files at execution time rather than assuming a fixed count.

## Environment
- Git's configured credential helper is authenticated for the repository;
  verify with `git ls-remote origin HEAD` and `git push --dry-run` before release.
- Check whether `gh` is installed with `command -v gh`; do not assume an OS or architecture.
- Each Bash call runs in a fresh shell. Re-establish required PATH entries in every call.

## Authorized release procedure

Only after the user explicitly authorizes a specific version, read and follow [the complete release procedure](references/release-procedure.md). It contains the ordered commands, stop conditions, article handling, verification, and reporting steps. Do not load it for general release-readiness questions or when release authorization is absent.

## Never
- Never tag before branch push verifies.
- Never claim PyPI published without the curl check.
- Never fabricate test counts.
- Never rely on `PATH` exports from a previous Bash call.
- Never print `DAV_GITHUB_TOKEN`.
- Never edit article content without explicit user instruction.
- Never replace bare `$OLD_VERSION` mentions that are not adjacent
  to `django-api-versioning`.
- Never skip Step 5a — the technical-impact check is mandatory.
