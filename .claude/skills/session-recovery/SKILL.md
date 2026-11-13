# Skill: Session Recovery - django-api-versioning

Re-establish state after a sandbox disconnect. Honest about what
git can and cannot tell us.

## Procedure

### 1. Sync with remote

```bash
pwd
git fetch origin
git status
git log --oneline -20
git rev-parse HEAD
git ls-remote --heads origin refs/heads/audit/comprehensive-package-review
```

- Local HEAD == remote SHA: no unpushed work. Proceed.
- Local ahead: unpushed commits. Run `.claude/push.sh` NOW.
- Diverged: STOP. Report before doing anything.

### 2. Re-create commit-msg hook if missing

```bash
if [ ! -x .git/hooks/commit-msg ]; then
  cat > .git/hooks/commit-msg <<'HOOK'
#!/bin/sh
TMP=$(mktemp)
grep -v -E '^(Co-[Aa]uthored-[Bb]y:.*(Claude|Anthropic)|🤖 Generated with|Generated with .?Claude)' "$1" > "$TMP"
mv "$TMP" "$1"
HOOK
  chmod +x .git/hooks/commit-msg
fi
```

### 3. Verify identity

```bash
git config --local user.name
git config --local user.email
```

Must be `Mojtaba Arvin` / `m.arvin@live.com`. Set if missing.

### 4. Verify auth

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $DAV_GITHUB_TOKEN" \
  https://api.github.com/user
```

- 200: proceed.
- 401/403: STOP, tell user to regenerate the PAT.
- 000: network, report and stop.

### 5. Detect in-progress task — with honest limitations

**If `git status` is dirty:** an edit happened without commit+push.
Commit and push via `/safe-checkpoint` FIRST, THEN resume.

**If `git status` is clean:** read `git log --oneline -10` and
match the pattern:

| Last commit(s) | Likely state | Resume |
|---|---|---|
| `test: matrix PY=X DJ=Y ...` | Matrix partial or done | Re-run `/compat-matrix`. `row_done` skips done rows. |
| `chore(release): prepare vX.Y.Z` + tag exists | Release mid-flight, tag not pushed | `.claude/push.sh --tag` then `/release` step 11+ |
| `chore(release): prepare vX.Y.Z` + no tag | Release mid-flight, tag not created | `/release` step 8 (create tag) |
| Single `fix: …` or `feat: …` | One fix done, maybe more planned | **Ask user** if more remained |
| Sequence of `fix:` / `test:` commits | Likely a batch | **Ask user** for the original task list and remaining items |
| `docs: …` | One doc change done | **Ask user** — unless the current user message contains a full task spec; in that case, proceed from the spec |
| Only `chore: initialize persistent...` | Initial setup | Ask user for next phase |
| Nothing beyond `main` merge | Idle | Ask user what to work on |
| Untracked files only | Scratch | Inspect filenames. Add to a task or delete. Never delete blind. |

### Critical limitation — state it explicitly

**Without an external tracker, this skill cannot know how many
items were in the user's batch.** It sees what was done, not what
was planned.

When the pattern suggests a batch (two or more `fix:`/`test:`
commits in a row) AND the current user message does NOT contain a
full task spec, STOP and ask the user:

> "I see these commits in the current session:
> <list with hashes and subjects>
> I cannot determine how many items were in the original task
> list or which items remain. Please state the original list and
> what is still pending."

Do NOT assume the batch is complete just because the last commit
looks self-contained. Do NOT guess remaining items. Do NOT invent
a task list. The user must confirm.

**Exception:** if the user's current message contains a complete
task specification (a full list of phases, issues, or acceptance
criteria), treat that as the authoritative task list. Do not ask
for confirmation. Proceed from the spec.

### 6. Report and resume

State in one block: local SHA, remote SHA (match/diverge),
detected pattern, files currently modified (if any), the user's
confirmed next action. Then execute.

## Never
- Never assume prior work completed without git evidence.
- Never read `DEVELOPMENT_LOG.md`, `HANDOFF.md`, `*_PROGRESS.md`
  (they do not exist — CLAUDE.md Section 8).
- Never `git reset --hard`, `git clean`, `git checkout .`.
- Never start new work while unpushed commits exist.
- Never pretend to know the remaining task list from git alone.
- Never ask the user for a task list if their current message
  already contains one.
  