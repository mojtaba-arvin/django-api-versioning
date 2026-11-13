# Skill: Safe Checkpoint - django-api-versioning

Commit and push one file change. Use immediately after ANY edit
to the working tree — do not wait for "enough" changes.

## Trigger

Any change in `git status`. Even one line.

## Procedure

### 1. Review the change

```bash
git status
git diff --stat
git diff
git ls-files --others --exclude-standard
```

Stop and inspect if the change includes:
- `*.env`, `*token*`, `*secret*`, `*.pem`, `*.key`
- Files outside the current task scope

### 2. Quick test — only if the change is code or a test

Run only the touched test file:

```bash
pytest <touched_test_file> -v
```

If no venv is active, use the closest recent one:

```bash
/tmp/env-3.12/bin/python -m pytest <file> -v
```

Skip if the change is documentation, config, or a pure `.md` edit.
Full matrix is NOT run here — that is `/manual-testing` Full.

### 3. Stage explicit paths

```bash
git add path/to/file1 path/to/file2
```

Never `git add .` or `git add -A`.

### 4. Verify staging area

```bash
git diff --cached --stat
git diff --cached
```

Only intended files, no secrets.

### 5. Commit

Before writing the message, verify:
- Subject describes WHAT changed, not WHERE it came from.
- No spec numbers, no "as specified", no "requirement N".
- A future reader with no access to the original task can
  understand the change from the message alone.

Then:

```bash
git commit -m "<type>: <short description>"
```

Types: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
No co-author trailer. No "Generated with Claude Code".

### 6. Verify author

```bash
git log -1 --format='%an <%ae> | %cn <%ce>'
```

Both must be `Mojtaba Arvin <m.arvin@live.com>`.
If wrong and not yet pushed: `git commit --amend --reset-author`.

### 7. Push

```bash
.claude/push.sh
```

Exit 0 = verified. Non-zero = STOP, diagnose, do not edit another file.

## Never
- Never `git add .` or `git add -A`.
- Never add a co-author trailer.
- Never commit `*.env`, tokens, keys.
- Never use `git reset --hard` or `git clean`.
- Never run `/manual-testing` Full here — Quick only.
- Never batch multiple file changes into one commit unless coherent
  (see CLAUDE.md Section 4).
- Never reference internal task-spec numbering in the commit
  message ("Issue N", "Phase N", "Bug N", "ERR N"). Describe
  the behavior in domain terms. See CLAUDE.md Section 4
  "Commit message content rules".
