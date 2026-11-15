# Skill: Session Recovery - django-api-versioning

Re-establish repository and task state after a sandbox disconnect. Git records repository state, not the ownership or intent of every edit; recover conservatively.

## 1. Inspect repository state

```bash
pwd
git fetch origin
git status --short
git log --oneline -20
git rev-parse HEAD
git ls-remote --heads origin refs/heads/audit/comprehensive-package-review
```

Classify local and remote state:

- Same SHA: branch is synchronized.
- Local ahead: inspect each unpushed commit and confirm it belongs to the current authorized task before pushing.
- Remote ahead: fetch and inspect the new commits before continuing.
- Diverged: stop; do not reset, rebase, force-push, or overwrite either side.

## 2. Protect dirty working trees

A dirty working tree does **not** authorize a commit or push.

For every modified, deleted, or untracked path:
1. Inspect the diff or file contents.
2. Compare it with the current task scope and known prior checkpoints.
3. Identify whether it is clearly part of the interrupted task.
4. Preserve unrelated, unknown, and user-owned changes untouched.
5. Ask the user before committing changes whose ownership or intent is uncertain.

Do not use `git clean`, `git reset --hard`, or `git checkout .` to make the tree clean.

## 3. Verify repository identity and hooks

```bash
git config --local user.name
git config --local user.email
```

Expected identity: `Mojtaba Arvin` / `m.arvin@live.com`.

Inspect the commit-msg hook if commit policy requires it. Recreate a missing hook only using the repository's documented safe procedure; do not overwrite an existing hook without inspection.

## 4. Verify authentication safely

Use the configured Git credential helper and the repository push helper. Never print, echo, trace, or place `DAV_GITHUB_TOKEN` in command-line arguments, URLs, logs, or diagnostics. If authentication fails, report only the status category and ask the user to repair credentials.

## 5. Recover task progress

Read the current task specification and compare it with:
- the latest commits and their diffs;
- the current working-tree state;
- relevant test and workflow results;
- explicit progress artifacts that actually exist in the repository.

Do not assume a batch is complete merely because the latest commit looks self-contained. Do not assume the remaining task list from Git history alone.

If the current user message contains a complete task specification, use it as the authoritative task list and resume from verified repository state. Otherwise, if the remaining scope cannot be determined, ask the user.

## 6. Report before resuming

State:
- local and remote branch SHAs and whether they match;
- unpushed commits, if any;
- modified/untracked paths and whether their ownership is known;
- the last verified task checkpoint;
- tests/workflows actually completed;
- the next safe action.

Then continue only within the current authorization.

## Never

- Never push merely because local commits are ahead; verify task ownership and authorization.
- Never commit merely because the working tree is dirty.
- Never discard or overwrite unknown changes.
- Never expose credentials.
- Never claim a task step or test completed without evidence.
- Never ask for a task list when the current user message already supplies it.
