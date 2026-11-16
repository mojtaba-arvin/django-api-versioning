# Contributing

This repository follows a **main-based, short-lived-branch workflow**. `main` is the only long-lived development and release line. There is no permanent `develop`, audit, staging, integration, or release branch.

The goals are to keep `main` releasable, make every change reviewable, and avoid long-lived branches that drift away from the current source of truth.

## Start from the latest main

Inspect the working tree first. Preserve unrelated or uncommitted work; do not reset or clean it to make switching branches easier.

```bash
git status --short
git fetch origin --prune
git switch main
git pull --ff-only origin main
git switch -c feat/short-description
```

Use one short-lived branch per coherent task, created from the latest `origin/main`. If the working tree is dirty or local `main` cannot be fast-forwarded, stop and resolve ownership before switching.

### Branch naming

| Work | Prefix | Example |
| --- | --- | --- |
| New behavior | `feat/` | `feat/route-introspection` |
| Bug fix | `fix/` | `fix/segment-boundary` |
| Documentation | `docs/` | `docs/release-workflow` |
| Tests | `test/` | `test/route-registration` |
| Refactoring | `refactor/` | `refactor/registry-resolution` |
| Maintenance | `chore/` | `chore/update-tooling` |
| Release preparation | `release/` | `release/v0.4.0` |

Do not reuse a completed branch for unrelated work. Dependabot branches are temporary automation branches.

## Commits

Prefer a small number of commits, each representing one coherent and independently understandable change. Do not create a commit for every edited file, formatter run, generated timestamp, or intermediate checkpoint.

Use the established Conventional Commit style:

- `feat:` — new user-visible behavior
- `fix:` — user-visible bug fix
- `docs:` — documentation-only change
- `test:` — tests without production behavior changes
- `refactor:` — behavior-preserving restructuring
- `chore:`, `build:`, `ci:` — maintenance, packaging, or automation

Add a scope where useful, such as `fix(registry): preserve endpoint precedence`. Mark an intentional breaking change with `!` or a `BREAKING CHANGE:` footer. Commit prefixes are for readable history; release impact must be determined from actual diffs, not prefixes alone.

Before committing:

```bash
git diff --check
git status --short
git diff
```

Stage explicit paths, inspect the staged diff, and verify the commit identity. Never commit credentials, local environment files, non-canonical generated files, or unrelated user work.

## Pull requests to main

Push the task branch and open a pull request targeting `main`. Describe the problem, intended result, design/behavior and compatibility impact, exact tests/checks run, and any documentation or changelog implications.

All changes to `main` go through a PR. Do not push directly to `main`, force-push shared history, or merge before the relevant checks for the latest PR head have completed successfully.

This is a single-maintainer repository; requiring an approval from the same maintainer is not useful. Keep the PR gate and relevant CI checks, but don't impose a self-approval requirement.

## Merge and branch cleanup

Use **squash merge by default**: one PR becomes one coherent commit on `main`, while the PR retains its discussion and detailed commit history. Rebase merge is an acceptable exception when preserving a carefully curated sequence is materially useful. Avoid merge commits that add no useful history.

Delete a task branch after its PR is merged or closed. Enable GitHub's **Automatically delete head branches** setting. Do not keep long-lived audit, staging, integration, or release branches. A release branch exists only while its release PR is reviewed.

Review Dependabot PRs promptly; merge useful dependency updates or close obsolete PRs and remove their branches.

## Package release

A package release is separate from a website deployment. A Netlify deployment does not publish the Python package.

A release requires explicit authorization for a specific version. Prepare the version bump, dated `CHANGELOG.md` entry, and approved documentation changes on one short-lived `release/vX.Y.Z` branch. Open a PR to `main`; do not tag or publish from that branch.

After the PR is merged, verify that its exact merge commit is on `origin/main` and contains the requested `pyproject.toml` version. Create an annotated `vX.Y.Z` tag on that exact commit and push only that tag. The tag workflow is the final compatibility, build, distribution-validation, and PyPI publication gate. Verify the version-specific PyPI endpoint before announcing success.

### Version policy

Follow Semantic Versioning and Keep a Changelog. While the package is below `1.0.0`, a compatible bug fix increments the patch version, a backward-compatible feature increments the minor version, and an intentional public-contract breaking change also increments the minor version with clear migration notes. After `1.0.0`, breaking public API changes require a major increment.

Changelog entries describe user-visible changes. Do not add transient CI logs, test counts, internal task status, or empty categories. Update article examples and pinned package versions only when they actually refer to the package version being released.

## Repository settings

The `main` branch should have an **active** ruleset that requires a PR, prevents force-push and branch deletion, and requires linear history. Do not require a self-approval from the sole maintainer.

Enable automatic deletion of merged head branches. Squash merge should be the normal merge method.

Do not make each existing path-filtered workflow an individually required status check. A workflow skipped at the workflow level by path/branch filters can leave a required check pending and block a PR. Before making CI mandatory, introduce one always-running PR gate that reports success only after the relevant path-specific jobs pass.

## Scope-specific verification

Follow `AGENTS.md` and the relevant canonical skill in `.agents/skills/`. The package contract is in `docs/reference/versioning-contract.md`; the editable article corpus is `docs/articles/`.

- Package behavior: focused unit tests and integration tests when framework wiring changes.
- Compatibility: `tox.ini` is authoritative; `scripts/check_tox_workflow_matrix.py` checks parity with GitHub Actions.
- Packaging: build wheel and sdist and verify their contents.
- Website: run checks from `website/`; a website-only deployment does not change the Python package release.
- Generated Segment Lab evidence and website lockfiles must be generated on the active topic branch, never committed directly to `main`.
