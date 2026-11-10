# Skill: Safe Checkpoint - django-api-versioning

Procedure to preserve completed work after EACH meaningful step.

## Quick Summary

After completing any independently verifiable piece of work, follow this 12-step checkpoint procedure to safely commit and push to GitHub.

## Checkpoint Steps

### Step 1: Inspect Entire Git Diff

```bash
git status
git diff --stat
git diff
```

**Action**: Review all changes to understand scope and ensure they are complete and correct.

### Step 2: Inspect All Untracked Files

```bash
git ls-files --others --exclude-standard
```

**Action**: Identify and categorize untracked files:
- Valuable work to commit
- Temporary files to ignore
- Secrets or credentials to exclude

### Step 3: Identify Unrelated Changes

Review the diff to identify:
- Changes related to the completed task (should be committed)
- Changes unrelated to this task (hold for separate commits)
- Temporary files (remove or exclude)
- Sensitive files (.env, credentials, tokens) (never commit)

**Action**: Do NOT mix unrelated changes into a single commit. Each commit should be logically coherent.

### Step 4: Run Relevant Manual Tests

Based on the type of change:

**For code changes**:
```bash
cd tests && pytest -v
```

**For documentation changes**:
- Verify markdown syntax
- Check links are correct
- Verify no broken references

**For configuration changes**:
- Verify YAML/JSON syntax
- Validate against schema if applicable

**Action**: Run tests and verify they pass before committing.

### Step 5: Verify Test Results Are Relevant

**Verify**:
- Did the tests actually run?
- Are all tests passing?
- Did you run the CORRECT tests for this change?

**Document**:
- Exact command used
- Output showing all tests passed
- Any warnings or issues noted

### Step 6: Update DEVELOPMENT_LOG.md

Append a new entry to DEVELOPMENT_LOG.md with:
- Date and session identifier
- Completed task description
- Files modified (with line ranges if applicable)
- Test commands run and actual results
- Commit hash (after you create it)
- Push status (pending/successful)

**Example format**:
```markdown
## Session X: YYYY-MM-DD - [Task Description]

### Changes
1. File: path/to/file.py
   - Lines: 10-20
   - Description: [specific change]

### Tests Executed
- Command: `pytest tests/test_module.py -v`
- Result: 15/15 PASSED
- Coverage: 95%

### Verification
- [x] Manual tests passed
- [x] No regression in existing functionality
- [x] Documentation updated

### Commit
- Hash: abc1234
- Message: [commit message]
- Status: Pushed ✅
```

### Step 7: Update DEVELOPMENT_PROGRESS.md

Update the status of the current task or phase:
- Mark task as Completed if done
- Record any findings or metrics
- Update any status descriptions
- Preserve historical entries

### Step 8: Update HANDOFF.md

Update the latest checkpoint record with:
- Current working branch
- Latest verified remote commit hash (AFTER push)
- Current task status
- What was just completed
- What is outstanding
- Exact next action

### Step 9: Stage Only Reviewed Files

Stage files explicitly (do NOT use `git add .` or `git add -A`):

```bash
git add DEVELOPMENT_LOG.md
git add DEVELOPMENT_PROGRESS.md
git add HANDOFF.md
git add path/to/modified/file.py
# ... repeat for each reviewed file
```

**Critical**: Never blindly stage entire directories or the whole repository. Always review each file individually.

### Step 10: Verify Staging Area

```bash
git status
git diff --cached --stat
git diff --cached
```

**Verify**:
- Only intended files are staged
- No secrets or credentials included
- No temporary files included
- All changes are correct and complete

### Step 11: Create Focused Logical Commit

Use a semantic commit message that clearly describes the work:

```bash
git commit -m "$(cat <<'EOF'
<type>: <short description>

<optional detailed explanation of why this change was made>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

**Commit types**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Configuration, tooling, or build changes

**Examples**:
- `docs: consolidate session audit documentation`
- `fix: correct test count in release notes`
- `docs: clarify DRF ViewSet integration patterns`

### Step 12: Push Immediately to Working Branch

```bash
git push origin audit/comprehensive-package-review
```

**Verify push succeeded**:
```bash
git log origin/audit/comprehensive-package-review --oneline -1
```

**Expected**: Last commit hash should match your local commit hash.

## Post-Push Verification

After pushing, verify:
1. Remote commit hash matches local commit hash
2. GitHub shows branch is up to date
3. No unpushed commits remain locally
4. Working tree is clean

```bash
git status
git log --oneline -1
git log origin/audit/comprehensive-package-review --oneline -1
```

## Handling Push Failures

If `git push` fails:

1. **Diagnose the failure**:
   - Network error? Check internet connection
   - Authentication error? Verify credential helper is set correctly
   - Branch divergence? Run `git log origin/audit/comprehensive-package-review..HEAD`
   - Protected branch? Verify you're pushing to correct branch

2. **Preserve all work**:
   - Do NOT reset, clean, or discard commits
   - Document the exact error in HANDOFF.md
   - Document all unpushed commit hashes

3. **Update HANDOFF.md**:
   - Document exact error message
   - List unpushed commits with hashes
   - Record diagnosis
   - Specify next recovery step

4. **Report and stop**:
   - Do NOT proceed with further work
   - Report the blocker to the user
   - Preserve all local commits for recovery

## Never Do These Things

- ❌ Use `git add .` or `git add -A` (stage selectively)
- ❌ Commit without reviewing changes (always review diff first)
- ❌ Mix unrelated changes into one commit (keep commits focused)
- ❌ Include credentials, secrets, or sensitive files (check diff for secrets)
- ❌ Rewrite or amend published commits (always create new commits)
- ❌ Force-push (never use --force or --force-with-lease)
- ❌ Commit without meaningful test verification
- ❌ Leave valuable uncommitted work (checkpoint early and often)

## When to Create a Checkpoint

Create a checkpoint after:
- Completing a bug fix (and running relevant tests)
- Completing a documentation update
- Adding a new feature or capability
- Creating or improving tests
- Fixing any issue or resolving any blocker
- Updating configuration or tooling

**Rule of thumb**: If you would feel sad to lose this work due to a disconnection, it's time for a checkpoint.

## Checkpoint Checklist

Before pushing, verify:
- [ ] All changes reviewed and correct
- [ ] Unrelated changes separated
- [ ] No secrets or credentials included
- [ ] Relevant tests executed and passing
- [ ] Documentation files updated
- [ ] Only reviewed files staged
- [ ] Commit message is semantic and clear
- [ ] Ready to push to remote

## Success Criteria

After a successful checkpoint:
- [ ] `git status` shows "nothing to commit, working tree clean"
- [ ] Remote commit hash matches local commit hash
- [ ] All canonical documentation updated
- [ ] No valuable work remains uncommitted
- [ ] Exact next action documented in HANDOFF.md
