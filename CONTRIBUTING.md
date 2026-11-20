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

Stage explicit paths, inspect the staged diff, and verify the commit identity. Never commit credentials, local environment files, non-canonical generated files, or unrelated user work. When pre-commit is installed, activate both the commit and push hooks with `pre-commit install` and `pre-commit install --hook-type pre-push`. The commit hooks format and check changed Python files; the pre-push hook runs `tox run -e lint` when Python or lint configuration changes. They provide local feedback, while the required PR gate remains authoritative.

## Pull requests to main

Push the task branch and open a pull request targeting `main`. Describe the problem, intended result, design/behavior and compatibility impact, exact tests/checks run, and any documentation or changelog implications.

All changes to `main` go through a PR. Do not push directly to `main`, force-push shared history, or merge before the required `PR gate` has completed successfully for the latest PR head SHA. The gate always runs and invokes only path-relevant test, compatibility, packaging, website, agent-tooling, and dependency-review workflows. A skipped individual workflow is not itself a pass—the gate must report success.

This is a single-maintainer repository; requiring an approval from the same maintainer is not useful. Keep the PR gate and relevant CI checks, but don't impose a self-approval requirement.

## Merge and branch cleanup

Use **squash merge only**: one PR becomes one coherent commit on `main`, while the PR retains its discussion and detailed commit history. Merge commits and rebase merges are disabled in repository settings and rejected by the `main` ruleset. Keep the PR title in Conventional Commit format because it becomes the subject of the squash commit.

Branches are disposable task workspaces, not records of completed work:

- **Merged PR:** GitHub's **Automatically delete head branches** setting removes the head branch. The agent must verify that it disappeared; if it remains, the cleanup workflow retries.
- **Closed without merge:** the branch is not covered by GitHub's auto-delete setting. The branch-cleanup workflow deletes it automatically when no other open PR uses it.
- **Open PR:** preserve its branch.
- **No PR:** do not guess that the branch is disposable. Keep it until its owner/task is established; delete only after verifying it is stale and has no open PR or recovery purpose.
- **Fork PR:** never delete a branch in another repository.

The `.github/workflows/branch-cleanup.yml` workflow runs when a PR closes, after every update to `main`, and on a weekly schedule. It also supports manual dispatch. It only deletes same-repository branches referenced by closed PRs, excludes `main`, and rechecks that no open PR uses the branch. Its cleanup job receives `contents: write`; no repository code is checked out or executed in that job.

Agents must finish every task by checking the PR state and remote branch state. After merge or closure, verify deletion; if a branch remains and the workflow cannot delete it, report the exact permission or protection error and leave no silent cleanup TODO. Never ask the maintainer to delete a branch that the agent or workflow can safely remove. Do not keep long-lived audit, staging, integration, or release branches. A release branch exists only while its release PR is reviewed.

Review Dependabot PRs promptly; merge useful dependency updates or close obsolete PRs. Their closed-PR branches are cleaned by the same workflow.

## Package release

A package release is separate from a website deployment. A website deployment does not publish the Python package.

A release requires explicit authorization for a specific version. Prepare the version bump, dated `CHANGELOG.md` entry, and approved documentation changes on one short-lived `release/vX.Y.Z` branch. Open a PR to `main`; do not tag or publish from that branch.

Before opening the release PR, regenerate and validate the Python lockfile—even when the only `pyproject.toml` change is the package version:

```bash
uv lock
uv lock --check
```

Commit the generated `uv.lock` alongside the metadata change. Never hand-edit it. Confirm that its editable `django-api-versioning` package entry has the same version as `[project].version` in `pyproject.toml`. Also build and validate the wheel and sdist when package metadata or build configuration changes.

A release PR is blocked until the required `PR gate` succeeds for its **latest head SHA**. Inspect actual failed job/step logs; fix failures on the release branch and wait for the new run to finish. A majority of green checks, skipped checks, a previous green run, or a mergeability hint does not override a failed/pending required gate. Do not use `--admin` or any other bypass to merge around branch protection. Merge only after the gate reports success.

After the release PR is merged, open a terminal in the repository directory and run this single, memorable command:

```bash
make release
```

No version number or subcommand is needed. The command reads the package version directly from `pyproject.toml`, checks that the working tree is clean, switches to `main` when safe, fast-forwards it from `origin`, validates the changelog and lockfile, and displays a release preview. It asks for explicit confirmation before creating or pushing a tag. After confirmation it waits for the exact-commit compatibility workflow, creates or safely resumes the annotated tag, waits for the tag-triggered `publish.yml` workflow, and verifies both the PyPI version and GitHub Release URL. It stops on any failed gate and never bypasses repository rulesets. The protected `v*` tag ruleset still requires an account authorized to create tags.

If the working tree is dirty, switching branches is not possible, or the required tools/authentication are missing, the command stops with a specific explanation without discarding local work. If interrupted after the tag is pushed, run `make release` again; the operation safely resumes. The default confirmation is **No**.

The default workflow wait timeout is 60 minutes. Set `RELEASE_WAIT_TIMEOUT_SECONDS` to override it; `RELEASE_POLL_INTERVAL_SECONDS` controls polling frequency. If the command is interrupted after pushing the tag, rerun `make release` to resume and verify the existing release rather than creating another tag.

The lower-level `preflight`, `tag`, `finish`, `create`, and `status` actions remain available for diagnosis and legacy recovery, but the supported human release path is `make release`. GitHub Release creation is performed by `publish.yml` only after successful PyPI publication; do not manually create the Release during a normal release.

For branch hygiene, `bash scripts/maintain.sh branches` reports safe deletion candidates without changing anything. Add `--apply` to delete only unprotected branches whose commits are already reachable from `main` and which have no open PR. Unmerged branches are always retained for manual review.

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
