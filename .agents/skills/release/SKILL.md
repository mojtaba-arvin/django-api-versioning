---
name: release
description: Prepare and publish an explicitly authorized package version through a reviewed main-branch pull request.
---

# Release

Use only when the user explicitly authorizes a concrete package version, such as `release 0.4.0`. This skill does not grant permission to choose a version, merge an unrelated PR, move an existing tag, or publish an unspecified release.

## Preconditions

- The requested version is explicit and follows the policy in [CONTRIBUTING.md](../../../CONTRIBUTING.md).
- `main` is the default branch and synchronized with `origin/main`.
- The working tree is clean before creating a release branch.
- The target version tag does not already exist locally or remotely.
- The release is authorized; changes still reach `main` through a pull request.

## Workflow

1. Read [the complete release procedure](references/release-procedure.md).
2. Create one short-lived `release/vX.Y.Z` branch from the latest `origin/main`.
3. Prepare the version bump, dated changelog entry, and approved documentation updates as one coherent change.
4. Push the release branch with `.claude/push.sh` and open a PR targeting `main`.
5. Require the always-running `PR gate` to pass for the exact latest PR head SHA. The gate invokes every path-relevant reusable workflow; a skipped child job is acceptable only when the path classifier marks that scope unchanged. Independently inspect CodeQL results for source changes and fix newly introduced actionable findings before merge.
6. After the PR is merged, create an annotated tag on the PR's exact merge commit on `main`, then push only that tag. The active `Protect release tags` ruleset permits the administrator role to create/update/delete `v*` tags; never bypass or weaken it.
7. Verify the GitHub release and version-specific PyPI endpoint before reporting publication success.

## Never

- Never use a permanent audit, development, or release branch; `main` is the only long-lived branch.
- Never push release-preparation commits directly to `main`.
- Never tag an unmerged branch or a commit that is not an ancestor of `origin/main`.
- Never bypass a failed compatibility, build, or publication gate.
- Never claim PyPI publication without verifying the version-specific PyPI JSON endpoint.
- Never expose credentials, tokens, private keys, or secret-bearing command output.
- Never edit article content without explicit user approval; release authorization alone does not authorize prose changes.
