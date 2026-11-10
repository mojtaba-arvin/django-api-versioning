# Skill: Session Recovery - django-api-versioning

Procedure to recover project state after a session reset in the temporary DataCamp sandbox.

## Quick Summary

After every session interruption, follow this 12-step recovery procedure to re-establish context and identify the exact next task.

## Recovery Steps

### Step 1: Verify Working Directory and Git Setup

```bash
pwd
git branch --show-current
git remote get-url origin
```

**Expected**: Working directory should contain .git/config, branch should be `audit/comprehensive-package-review`, remote should be clean HTTPS URL without credentials.

### Step 2: Fetch Latest Remote References

```bash
git fetch origin
```

**Expected**: Latest commits downloaded from GitHub without errors.

### Step 3: Verify Branch Status

```bash
git log --oneline -5
git log origin/audit/comprehensive-package-review --oneline -5
```

**Expected**: Local and remote logs should show same or newer commits on working branch.

### Step 4: Inspect Local Git Status

```bash
git status
git diff --stat
git diff
```

**Expected**: Working tree clean. If uncommitted changes exist, document them immediately in HANDOFF.md and preserve them before proceeding.

### Step 5: List Untracked Files

```bash
git ls-files --others --exclude-standard
```

**Expected**: No untracked files, or document any important ones in HANDOFF.md.

### Step 6: Read Canonical Project Documentation

Read these three files in order:
1. `DEVELOPMENT_LOG.md` - Chronological history of completed work
2. `DEVELOPMENT_PROGRESS.md` - Current status of all phases
3. `HANDOFF.md` - Latest recovery state and exact next action

### Step 7: Verify Latest Remote Commit Hash

After reading HANDOFF.md, verify that the documented remote commit hash matches actual remote:

```bash
git rev-parse origin/audit/comprehensive-package-review
```

**Expected**: Hash should match the value documented in HANDOFF.md under "Latest Verified Remote Commit Hash".

### Step 8: Inspect Recent Commits

Look at the most recent relevant commits:

```bash
git log --oneline -20 -- DEVELOPMENT_LOG.md DEVELOPMENT_PROGRESS.md HANDOFF.md
git log --oneline -20 -- <relevant changed files>
```

**Expected**: See the documented work history. Cross-reference with DEVELOPMENT_LOG.md.

### Step 9: Identify Unfinished Work

Based on reading the three canonical files, identify:
1. What work was completed and pushed?
2. What work was in-progress?
3. What work is pending?
4. Are there any blockers or issues?
5. What is the exact next task?

### Step 10: Reconcile Local and Remote State

If local branch has commits that remote doesn't have:

```bash
git log --oneline origin/audit/comprehensive-package-review..HEAD
```

**Expected**: Should be empty (all local work is pushed). If not, verify and push these commits.

### Step 11: Preserve All Valuable Work

Before proceeding with any new work:
- Never use `git reset --hard`, `git clean`, or `git checkout .`
- Never blindly discard local commits or files
- If there is untracked work, document it in HANDOFF.md
- If there are uncommitted changes, decide whether to commit or preserve them

### Step 12: Determine Exact Next Action

Based on documentation review:
1. Identify the specific, actionable next task
2. Document this in your working notes
3. Begin implementation or investigation
4. Follow the standard workflow: Implement → Test → Document → Commit → Push

## Verification Checklist

After completing recovery steps, verify:
- [ ] Working directory correct
- [ ] Branch is audit/comprehensive-package-review
- [ ] Remote URL is clean (no credentials)
- [ ] Latest remote commit hash verified
- [ ] All three canonical files read and understood
- [ ] Local and remote state reconciled
- [ ] All valuable work preserved or accounted for
- [ ] Exact next task identified and documented

## If Problems Detected

If recovery reveals any of these situations:
- **Diverged branches**: Inspect both histories before merging
- **Uncommitted changes**: Document in HANDOFF.md with exact file paths
- **Unpushed commits**: Verify all commits are on working branch, push immediately
- **Remote changes not pulled**: Review diff carefully before pulling
- **Merge conflicts**: Preserve all work, resolve conflicts manually
- **Unknown files**: Inspect before deleting, document if valuable

## When to Use This Skill

- At the beginning of every new Claude session
- After any interruption or context loss
- When unsure about current project state
- Before starting any new implementation task

## Output

After completing this skill, you should have:
1. Clear understanding of current project state
2. Latest remote commit hash verified
3. Identification of any unfinished work
4. Documentation of any blockers or issues
5. Exact specification of the next actionable task
