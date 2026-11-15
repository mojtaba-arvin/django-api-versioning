# CLAUDE.md — django-api-versioning

## 1. Project
- Repo: https://github.com/mojtaba-arvin/django-api-versioning
- PyPI: https://pypi.org/project/django-api-versioning/
- Working branch: `audit/comprehensive-package-review`
- Main is off-limits. Never push to main.

## 2. Instruction precedence

Apply instructions in this order:

1. Platform and tool safety/security requirements. These cannot be overridden.
2. Explicit user instructions for the current task, including scope, constraints, and granted permissions, provided they do not conflict with level 1.
3. Repository-wide policy in `AGENTS.md`.
4. The applicable task skill under `.claude/skills/`.
5. Defaults and suggestions.

When two instructions at the same level conflict, prefer the more specific and more recent instruction. Do not silently guess when the conflict changes scope, data safety, external side effects, or release behavior; stop and ask. A task-specific instruction may refine a repository default, but must not silently weaken a safety boundary.

## 3. Non-Negotiable Safety
- Never print, echo, log, or expose `DAV_GITHUB_TOKEN`.
- Never force-push, rewrite remote history, or push to main.
- Never commit without reviewing the full diff. Stage explicit paths.
- Never run `git clean`, `git reset --hard`, `git checkout .`
  without per-occurrence approval.
- Existing GitHub Actions workflows may be dispatched when the task requires validation and the workflow's inputs/target ref have been inspected. A dispatch is not a test result: wait for the run and inspect its conclusion and jobs. Creating or materially changing workflows requires an explicit task scope; never add a workflow merely to avoid running an existing test command. Do not use Docker CI jobs as a substitute for the tox compatibility matrix.
- No tag push or PyPI release without explicit authorization.
- Never add `Co-authored-by`, `Co-Authored-By`, or "Generated with
  Claude Code". Author is always `Mojtaba Arvin <m.arvin@live.com>`.

## 4. Git checkpoints and remote writes

Use logical, reviewable commits. A single coherent change may span multiple related files; unrelated changes must not be bundled merely to reduce commit count. Do not create one commit per file when the files implement one atomic change.

Before committing:
1. Inspect `git status`, the complete unstaged and staged diffs, and untracked files.
2. Confirm every included path belongs to the current task and is safe to publish.
3. Run the applicable validation for the changed scope.
4. Stage explicit paths only; never use `git add .` or `git add -A`.
5. Review the staged diff, commit, and verify author identity.

A clean working tree is the desired checkpoint state after a completed logical unit, not an invariant that must hold between every edit and its commit. Do not interrupt a coherent multi-file change merely to commit an incomplete intermediate state.

Push only when the current user instruction or an applicable previously granted task authorization permits it. This task explicitly authorizes commits and pushes to `audit/comprehensive-package-review`. Never force-push, rewrite remote history, or push to `main`. After each push, verify that the remote branch points to the expected commit. If push fails, preserve local commits, diagnose without exposing credentials, and stop further edits until the remote state is understood.

Commit messages use `feat:`, `fix:`, `docs:`, `test:`, or `chore:` and describe the domain change, not internal task numbering. Do not add co-author trailers or generated-by signatures.

### Commit message content rules

Describe the change in domain terms. Never reference internal task-spec numbering. A future reader should understand the commit without access to a task prompt.

  ✅ test: reject boolean and string version values
  ❌ test: add comprehensive validation tests for Issues 3-6

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

Do not place the token in a command-line argument, shell trace, URL, log, or diagnostic output. Prefer the configured Git credential helper and `.claude/push.sh`. If authentication fails, report only the HTTP/status category and ask the user to repair the credential configuration; never print the token or a command that expands it into process arguments.

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
    for v in 3.10 3.11 3.12 3.13 3.14 3.15; do
      uv python list | grep -q "cpython-$v" || { echo "missing Python $v"; exit 1; }
    done

    uv venv /tmp/tox --python 3.15
    uv pip install --python /tmp/tox/bin/python tox tox-uv

    grep -q 'requires =' tox.ini && grep -q 'tox-uv' tox.ini \
      || { echo "tox.ini missing tox-uv"; exit 1; }
    
    [ -f integration_test_project/pytest.ini ] \
      || { echo "missing integration_test_project/pytest.ini";  exit 1; }

If any required Python version is missing, or `tox.ini` does not have
`tox-uv`, do NOT run tox. Fix first. Do not fabricate a
"NOT-RUN is infrastructure limitation" result.

### Quick — after code or test changes

Run the relevant test file(s) for the changed code, or the touched test file when changing tests. Documentation-only changes do not require pytest. Run Quick only when the project's intended virtual environment is active.

    python -m pytest <relevant_test_file> -v

### Single — Phase 1 baseline

One Python, unit + integration. Full instructions in
`/manual-testing`.

### Full — Phase 10 and before `/release`

    set -o pipefail
    PATH="$HOME/.local/bin:$PATH" /tmp/tox/bin/tox run-parallel -p auto 2>&1 | tee /tmp/tox-full.log
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
