---
name: safe-checkpoint
description: Create a reviewed, authorized Git commit and optionally push a completed logical change. Preserve unknown changes and never force-push.
---

# Skill: Safe Checkpoint - django-api-versioning

Create a reviewable Git checkpoint for a completed logical unit of work.

## Trigger

Use after a coherent change is complete and its applicable validation has run. Do not commit every individual edit or an incomplete intermediate state. A logical change may span multiple related files.

## Procedure

### 1. Establish ownership and scope

```bash
git status --short
git diff --stat
git diff
git ls-files --others --exclude-standard
```

Identify which changes were made for the current task. A dirty tree is not proof that every change belongs to this task. Preserve unknown, pre-existing, or user-owned changes and ask before including them.

Stop and inspect any credential, secret, private key, environment file, generated artifact, or out-of-scope path.

### 2. Validate the changed scope

- Python source/tests: run the relevant test suite according to `/manual-testing`.
- Markdown-only edits: run Markdown/front matter/link checks and review technical claims affected by the change; pytest is not required unless executable examples or runtime behavior changed.
- Workflow/configuration edits: validate syntax and inspect the affected workflow behavior.
- Do not claim validation that was not executed.

### 3. Stage explicit paths

```bash
git add path/to/related-file1 path/to/related-file2
```

Never use `git add .` or `git add -A`.

### 4. Review the staged diff

```bash
git diff --cached --stat
git diff --cached
```

Confirm that only intended, reviewed, safe files are staged. Check for secrets and generated files that should not be committed.

### 5. Commit

Use a concise domain-oriented message with one of: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.

Do not reference internal task-spec numbering. Do not add co-author trailers or generated-by signatures.

### 6. Verify identity

```bash
git log -1 --format='%an <%ae> | %cn <%ce>'
```

Expected author and committer: `Mojtaba Arvin <m.arvin@live.com>`.

### 7. Push only when authorized

Push to the task's authorized branch. Never force-push, rewrite remote history, or push to `main`. Verify the remote branch SHA after pushing.

If push fails, preserve the commit, inspect local and remote refs, do not expose credentials, and stop further edits until the failure is understood.

## Never

- Never commit unknown or user-owned changes without permission.
- Never stage the entire working tree.
- Never commit secrets, tokens, keys, or private environment files.
- Never use destructive reset/clean operations as a shortcut.
- Never push without task authorization.
- Never describe a commit as validated unless its required checks actually passed.
