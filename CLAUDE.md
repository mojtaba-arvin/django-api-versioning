# CLAUDE.md — django-api-versioning

## 1. Project
- Repo: https://github.com/mojtaba-arvin/django-api-versioning
- PyPI: https://pypi.org/project/django-api-versioning/
- Working branch: `audit/comprehensive-package-review`
- Main is off-limits. Never push to main.

## 2. Priority When Rules Conflict
1. User instruction in the current message.
2. Section 3 safety rules — cannot be overridden.
3. Everything else.
4. Default behavior.

## 3. Non-Negotiable Safety
- Never print, echo, log, or expose `DAV_GITHUB_TOKEN`.
- Never force-push, rewrite remote history, or push to main.
- Never commit without reviewing the full diff. Stage explicit paths.
- Never run `git clean`, `git reset --hard`, `git checkout .`
  without per-occurrence approval.
- No GitHub Actions for testing. No new CI workflow files.
- No tag push or PyPI release without explicit authorization.
- Never add `Co-authored-by`, `Co-Authored-By`, or "Generated with
  Claude Code". Author is always `Mojtaba Arvin <m.arvin@live.com>`.

## 4. Commit and Push — zero tolerance

Every file change is its own commit, pushed immediately.
No batching. No "wait until complete". No judgment.

Triggers — commit and push after EACH of:
- Creating, editing, deleting, or renaming any file
- Running a formatter that changed files
- Adding one test case
- Completing one matrix row

If `git status` shows any change, you are out of compliance.
Commit and push NOW before the next action.

Sequence:

    edit → git add <path> → git commit → .claude/push.sh

If `.claude/push.sh` exits non-zero, STOP. Do not edit another file.
Diagnose auth first (Section 6), fix, retry.

**Exception:** a single logical change spanning N files (e.g.,
renaming a symbol used in 3 files) is ONE commit. Split only when
the intermediate state compiles and tests pass.

**Zero rule:** at any moment — unpushed commits = 0,
uncommitted files = 0.

Commit messages: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
One-line subject.

Verification (mandatory after every push): `.claude/push.sh` exit 0
means local SHA == remote SHA. Exit non-zero means STOP.

### Commit message content rules

Describe the change in domain terms. Never reference internal
task-spec numbering.

Forbidden in any commit message, including body:
- "Issue N", "Issues N-M", "Bug N", "ERR N", "Phase N",
  "Scenario N" as the primary descriptor
- "as specified in the task", "per the spec", "requirement N"
- Any wording whose meaning depends on a document outside the repo

If the change fixes a behavior, name the behavior:

  ✅ test: reject boolean and string version values
  ❌ test: add comprehensive validation tests for Issues 3-6

  ✅ test: verify override_settings does not mutate loaded config
  ❌ test: add regression tests for Issue 7

  ✅ feat: group check_versions output by logical endpoint
  ❌ feat: implement Phase 3 logical endpoint matrix

  ✅ feat: reject unconfigured ViewSet with actionable error
  ❌ feat: add ViewSet detection for Phase 6

This applies to subject and body. If a behavior is genuinely
hard to summarize in one line, use a descriptive subject and
expand in the body — still without spec numbers.

## 5. Author Identity
Set at session start if missing:

    git config --local user.name "Mojtaba Arvin"
    git config --local user.email "m.arvin@live.com"

Verify after every commit:

    git log -1 --format='%an <%ae> | %cn <%ce>'

Both must be `Mojtaba Arvin <m.arvin@live.com>`.

## 6. Environment
- Ephemeral sandbox. Sessions disconnect without warning.
- System `python3` is 3.8.10 — never use for tests.
- Use `uv` for Python installs and venv: `uv python install 3.15`.
- `ssh` not installed. `.claude/push.sh` handles auth.
- `commit-msg` hook may be lost on reset. Re-create at session start.

Token diagnostic (run first if push fails):

    curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $DAV_GITHUB_TOKEN" \
      https://api.github.com/user

- 200 = valid, retry once
- 401 = invalid/expired, STOP ask user
- 403 = missing scopes, STOP ask user
- 000 = network, preserve commits, stop

## 7. Testing

Three modes. Never use system `python3` (3.8.10) for Single or Quick.
`tox.ini` is the source of truth for the supported matrix.

### Required tooling (must exist before Full)

`tox-uv` bridges tox to uv-managed Pythons. Without it, tox only
sees interpreters already in PATH and reports every other env as
`NOT-RUN: interpreter not found` — which is a sandbox setup
failure, not a code failure.

Every session that will run Full must first verify:

    which uv || pip install uv
    export PATH="$HOME/.local/bin:$PATH"
    uv --version

    uv python install 3.10 3.11 3.12 3.13 3.14 3.15
    uv python list | grep -c 'cpython-'   # must print 6

    uv venv /tmp/tox --python 3.15
    uv pip install --python /tmp/tox/bin/python tox tox-uv

    grep -q 'requires =' tox.ini && grep -q 'tox-uv' tox.ini \
      || { echo "tox.ini missing tox-uv"; exit 1; }
    
    [ -f integration_test_project/pytest.ini ] \
      || { echo "missing integration_test_project/pytest.ini";  exit 1; }

If `uv python list` shows fewer than 6 versions, or `tox.ini` does
not have `tox-uv`, do NOT run tox. Fix first. Do not fabricate a
"NOT-RUN is infrastructure limitation" result.

### Quick — after EVERY file change

    python -m pytest <touched_test_file> -v

### Single — Phase 1 baseline

One Python, unit + integration. Full instructions in
`/manual-testing`.

### Full — Phase 10 and before `/release`

    PATH="$HOME/.local/bin:$PATH" /tmp/tox/bin/tox 2>&1 | tee /tmp/tox-full.log

After run, check BEFORE believing the result:

1. `grep -c 'commands succeeded' /tmp/tox-full.log` — must be 13.
2. `grep -c 'interpreter not found' /tmp/tox-full.log` — must be 0.
3. `grep -E '[0-9]+ passed' /tmp/tox-full.log | head -5` — each env
   must show a count large enough to include both unit and integration
   (300+ combined, not ~170).
4. Each env's log section must contain two `passed` lines — one from
   `pytest tests`, one from `pytest integration_test_project`.
   `tox.ini` commands split them so each uses its own `pytest.ini`.

If any check fails, the tox setup is broken — NOT the code. Report
the failure; do not certify the package. Do not claim "sandbox
limitation" as an excuse; the sandbox can install all Pythons via
`uv python install`.

### Never

- Never claim a test passed unless exit code is 0.
- Never label a `NOT-RUN` env as `SUPPORTED` or `ASSUMED` or
  "compatible via type hints".
- Never write `CERTIFIED` or `PRODUCTION READY` if any env is
  `NOT-RUN` or `FAIL`.
- Never run `tox` before confirming 6 Pythons installed and
  `tox-uv` present in `tox.ini`.
- Never run `tox` in Phase 1 — that is Single's job.

## 8. Documentation
- Allowed: `README.md`, `CHANGELOG.md`, `CLAUDE.md`,
  `COMPATIBILITY_REPORT.md`, existing technical docs.
- Forbidden: `DEVELOPMENT_LOG.md`, `HANDOFF.md`, `*_SESSION*.md`,
  `TEMP_*.md`, `*_PROGRESS.md`, any session-specific file.
- Git history IS the progress log. Commit messages are the narrative.
- Before any new `.md`: confirm the info is not already in an
  existing doc. Default: reuse, not create.

## 9. Release
When user says "release X.Y.Z", invoke `/release`. Do not improvise.

The repository contains user-authored articles in `docs/articles/`.
During release, `/release` detects whether the release includes
technical changes (commits with `feat:` or `fix:` since the last
tag). If yes, it announces and waits for user confirmation about
which articles need content updates. If no technical changes, it
silently updates package version strings in articles and proceeds.
Never edit article content without explicit user instruction.

## 10. Session Start
1. `git fetch origin`
2. `git status` and `git log --oneline -20`
3. Compare `git rev-parse HEAD` to
   `git ls-remote --heads origin refs/heads/audit/comprehensive-package-review`
4. If local ahead: push first. If diverged: stop, report.
5. Verify identity (Section 5), commit-msg hook, auth (Section 6).
6. Run `/session-recovery`. If it detects a multi-task batch,
   ask the user for the original list and remaining items.
7. Resume from git state, not conversation memory.
