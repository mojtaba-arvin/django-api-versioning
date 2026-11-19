# Contributing

This repository follows a **main-based, short-lived-branch workflow**. `main` is the only long-lived development and release line. There is no permanent `develop`, audit, staging, integration, or release branch.

The goals are to keep `main` releasable, make every change reviewable, and avoid long-lived branches that drift away from the current source of truth.

## Start from the latest main

Inspect the working tree first. Preserve unrelated or uncommitted work; do not reset or clean it to make switching branches easier.

```bash
git status --short
test -z "$(git status --porcelain)" || { echo "Working tree must be clean before switching branches." >&2; exit 1; }
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

All changes to `main` go through a PR. Do not push directly to `main`, force-push shared history, or merge before the required `PR gate` has completed successfully for the latest PR head SHA. The gate always runs and invokes only path-relevant test, compatibility, packaging, website, agent-tooling, and dependency-review workflows. A skipped individual workflow is not itself a pass—the gate must report success.

This is a single-maintainer repository; requiring an approval from the same maintainer is not useful. Keep the PR gate and relevant CI checks, but don't impose a self-approval requirement.

## Merge and branch cleanup

Use **squash merge only**: one PR becomes one coherent commit on `main`, while the PR retains its discussion and detailed commit history. Merge commits and rebase merges are disabled in repository settings and rejected by the `main` ruleset. Keep the PR title in Conventional Commit format because it becomes the subject of the squash commit.

Delete a task branch after its PR is merged or closed. Enable GitHub's **Automatically delete head branches** setting. Do not keep long-lived audit, staging, integration, or release branches. A release branch exists only while its release PR is reviewed.

Review Dependabot PRs promptly; merge useful dependency updates or close obsolete PRs and remove their branches.

## Package release

A package release is separate from a website deployment. A website deployment does not publish the Python package.

A release requires explicit authorization for a specific version. Prepare the version bump, dated `CHANGELOG.md` entry, and approved documentation changes on one short-lived `release/vX.Y.Z` branch. Open a PR to `main`; do not tag or publish from that branch.

After the PR is merged, verify that its exact merge commit is on `origin/main` and contains the requested `pyproject.toml` version. Create an annotated `vX.Y.Z` tag on that exact commit and push only that tag. The `Protect release tags` ruleset restricts creation, updates, and deletion of `v*` tags to repository administrators. The tag workflow verifies that the tag is annotated, matches the package version, and points to a commit reachable from `main`; it is the final compatibility, build, distribution-validation, and PyPI publication gate. Verify the version-specific PyPI endpoint before announcing success.

### Version policy

Follow Semantic Versioning and Keep a Changelog. While the package is below `1.0.0`, a compatible bug fix increments the patch version, a backward-compatible feature increments the minor version, and an intentional public-contract breaking change also increments the minor version with clear migration notes. After `1.0.0`, breaking public API changes require a major increment.

Changelog entries describe user-visible changes. Do not add transient CI logs, test counts, internal task status, or empty categories. Update article examples and pinned package versions only when they actually refer to the package version being released.

## Repository settings

The `main` branch must have an **active** ruleset that requires a PR, prevents force-push and branch deletion, requires linear history, dismisses stale approvals, and requires review-thread resolution. This is a single-maintainer repository, so do not require approval from the PR author.

The only required status context is `PR gate`. It runs on every PR to `main` without workflow-level path filters and reports success only after every applicable reusable check passes. Do not add path-filtered workflows as separate required status checks. Squash is the only permitted merge method. Enable automatic deletion of merged head branches.

Protect `v*` release tags with an active tag ruleset; only repository administrators may create, update, or delete them. Keep Actions default token permissions read-only; grant write permissions only to the specific job that needs them. All third-party Actions must be pinned to full commit SHAs.

## Scope-specific verification

Follow `AGENTS.md` and the relevant canonical skill in `.agents/skills/`. The package contract is in `docs/reference/versioning-contract.md`; the editable article corpus is `docs/articles/`.

- Package behavior: focused unit tests and integration tests when framework wiring changes.
- Compatibility: `tox.ini` is authoritative; `scripts/check_tox_workflow_matrix.py` checks parity with GitHub Actions.
- Packaging: build wheel and sdist and verify their contents.
- Website: run checks from `website/`; a website-only deployment does not change the Python package release.
- Edit website articles only in `docs/articles/`; generated article copies and RSS output are build products and must not be committed.
- Update `website/pnpm-lock.yaml` from `website/package.json` with the pinned pnpm version on the active topic branch. Do not use npm lockfiles or update dependency locks directly on `main`.

## Dependency lockfiles

- Treat `uv.lock` and `website/pnpm-lock.yaml` as generated artifacts. Never hand-edit either file.
- When `pyproject.toml` changes, regenerate the Python lock with `uv lock` and verify it with `uv lock --check`. Use the same `uv` CLI provided by the repository's `tox-uv` toolchain.
- When `website/package.json` changes, use Node `22.23.4`, Corepack, and the pinned `pnpm@10.12.1`; regenerate with `pnpm install --lockfile-only --ignore-scripts` from `website/`.
- Dependency branches under `deps/` use the guarded lock-refresh path in `.github/workflows/generate-evidence.yml`: generation runs with read-only permissions, and only the isolated commit job can push the generated lockfiles. It does not execute package lifecycle scripts.
- A generated lockfile is not sufficient validation. The PR gate must pass for the final branch head after the lockfile commit.



## Security and dependency policy

- Report vulnerabilities privately through GitHub's **Report a vulnerability** flow. Do not publish exploit details in an issue or pull request. See [SECURITY.md](SECURITY.md).
- Keep Dependabot version updates and security updates enabled for GitHub Actions, Python dependencies, and website npm dependencies. Review grouped updates; do not blindly merge major-version changes.
- Dependency review blocks new high- and critical-severity advisories. Investigate transitive upgrades and license changes; document temporary exceptions in the PR.
- CodeQL analyzes the Python package and TypeScript/JavaScript website on pull requests, `main`, and weekly. Fix newly introduced actionable findings before merging.
- Enable secret scanning and push protection. Never place real credentials in examples, fixtures, commits, or workflow output; use clearly fake values.
- GitHub Actions receive read-only token permissions by default. Grant narrow write permissions only where required. PyPI publication is the only job allowed `id-token: write`.

Repository settings are managed by the idempotent maintainer script `scripts/configure_github_repository.sh`. Run it with authenticated `gh` and repository-admin permissions after the PR gate is available. It configures GitHub rulesets and security settings; it does not change package code or publish releases.
