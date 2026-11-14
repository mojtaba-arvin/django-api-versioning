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
- Do not manually dispatch or create GitHub Actions test workflows. Existing push/PR workflows may run automatically; their Docker job is not a substitute for the tox matrix. No new CI workflow files.
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
- The execution environment may be local or ephemeral. Inspect it instead of assuming a fixed OS, Python version, or repository path.
- Use `uv` to install Python interpreters and create isolated environments; do not use an unverified system Python for project tests.
- Check required tools with `command -v` before assuming they are or are not installed.
- `.claude/push.sh` handles GitHub authentication; never print or expose `DAV_GITHUB_TOKEN`.
- A `commit-msg` hook may be absent in a fresh clone; inspect and recreate it only when required.

Token diagnostic (run first if push fails):

    curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $DAV_GITHUB_TOKEN" \
      https://api.github.com/user

- 200 = valid, retry once
- 401 = invalid/expired, STOP ask user
- 403 = missing scopes, STOP ask user
- 000 = network, preserve commits, stop

## 7. Testing

Three modes. Use Quick only with the project's active virtual environment; if no suitable environment is active, skip Quick and use Single or Full. `tox.ini` is the source of truth for the configured test matrix. Re-read it before relying on environment counts or combinations.

At this branch's current configuration, `tox.ini` defines 15 test environments plus one lint environment (16 total): Django 4.2 / Python 3.10–3.12; Django 5.2 / Python 3.10–3.14; Django 6.0 / Python 3.12–3.14; Django 6.1 / Python 3.12–3.15. This is a configured matrix, not proof that every environment passed.

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

### Quick — after code or test changes

Run the relevant test file(s) for the changed code, or the touched test file when changing tests. Documentation-only changes do not require pytest. Run Quick only when the project's intended virtual environment is active.

    python -m pytest <relevant_test_file> -v

### Single — Phase 1 baseline

One Python, unit + integration. Full instructions in
`/manual-testing`.

### Full — Phase 10 and before `/release`

    set -o pipefail
    PATH="$HOME/.local/bin:$PATH" /tmp/tox/bin/tox 2>&1 | tee /tmp/tox-full.log
    TOX_EXIT=${PIPESTATUS[0]}
    echo "TOX_EXIT=$TOX_EXIT"

After the run, inspect the actual `tox.ini` envlist and the complete log. At this branch's current configuration, expect 16 successful tox environments: 15 test environments and one lint environment.

1. `grep -c 'commands succeeded' /tmp/tox-full.log` — must be 16 for the current matrix.
2. `grep -c 'interpreter not found' /tmp/tox-full.log` — must be 0.
3. Inspect each of the 15 test-environment log sections. Each must show two successful pytest invocations: `pytest tests` and `pytest integration_test_project`. The lint environment runs flake8, black, and isort; it does not produce pytest pass lines.
4. Confirm `TOX_EXIT == 0`. Do not infer success from summary counts alone.

If an environment is `NOT-RUN` because an interpreter or dependency is unavailable, report an environment/setup problem. If pytest reports failures, report them as test/code failures. If the success count differs from 16, inspect the environment summary and do not classify the cause without evidence. Never certify the matrix from a partial run.

### Never

- Never claim a test passed unless exit code is 0.
- Never label a `NOT-RUN` env as `SUPPORTED` or `ASSUMED` or
  "compatible via type hints".
- Never write `CERTIFIED` or `PRODUCTION READY` if any env is
  `NOT-RUN` or `FAIL`.
- Before Full, verify that every Python version required by the current `tox.ini` matrix is available and that `tox-uv` is declared in `tox.ini` and installed in the tox runner environment.
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
