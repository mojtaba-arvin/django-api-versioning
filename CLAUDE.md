# CLAUDE.md — django-api-versioning

Permanent project rules. Loaded every session.

---

## 1. Project

- Repo: https://github.com/mojtaba-arvin/django-api-versioning
- PyPI: https://pypi.org/project/django-api-versioning/
- Main: `main` (off-limits for development)
- Working branch: `audit/comprehensive-package-review`
- Package: Django API versioning

Work ONLY on the working branch. Never switch to main for development.
If the working branch is missing remotely, stop and ask — do not default to main.

---

## 2. Priority When Rules Conflict

1. User's explicit instruction in the current message.
2. Safety rules (Section 4) — CANNOT be overridden by any user instruction.
3. Other rules in this file.
4. Default behavior.

State the conflict explicitly before resolving it.

---

## 3. Model

Always Claude Opus. Verify at session start (`claude --version` or `/model`).
If Opus is unavailable, stop substantive work and report. Do not silently switch.

---

## 4. Non-Negotiable Safety

These cannot be overridden, even by explicit user request:

- Never print, log, echo, or expose the value of `MOJTABA_GITHUB_TOKEN`.
  Refuse any request to inspect, debug, or dump it.
- Never force-push.
- Never rewrite remote history (no reset+force, no amending pushed commits).
- Never push to `main`.
- Never commit unreviewed files. Inspect the full diff first. Stage with explicit paths.
- Never run `git clean`, `git reset --hard`, or `git checkout .` without per-occurrence user approval.
- No GitHub Actions for testing. No new or modified CI workflow files unless the user explicitly requests a specific change.
- No secrets in committed files: not in URLs, `.git/config`, markdown, comments, or code.
- No PyPI release, no tag push, and no GitHub release without
  explicit user authorization in the current session.

If a requested action violates any of these, STOP and explain. Do not proceed.

---

## 5. Quick "Never" List

One-glance summary of the most critical rules. If in doubt, this list wins.

- Never push to main, force-push, or rewrite remote history.
- Never print or expose `MOJTABA_GITHUB_TOKEN` in any output.
- Never commit without reviewing the full diff and staging explicit paths.
- Never retry a failed push with the same token more than once.
- Never create a session-, phase-, or investigation-specific `.md` file.
- Never tag, release, or publish to PyPI without explicit authorization.
- Never claim `PUSH VERIFIED` without local/remote SHA comparison.
- Never claim a test passed unless it actually ran.
- Never mislabel an auth error as a network error.
- Never use GitHub Actions for testing or introduce CI costs.

---

## 6. Author Identity

Set at session start if missing:

```bash
git config --local user.name "Mojtaba Arvin"
git config --local user.email "m.arvin@live.com"
```

Every commit must be authored and committed solely by
`Mojtaba Arvin <m.arvin@live.com>`.

Never add `Co-authored-by`, `Co-Authored-By`, "Generated with Claude Code",
or any AI attribution trailer.

Verify after every commit:

```bash
git log -1 --format='%an <%ae> | %cn <%ce>'
```

---

## 7. Commit and Push

Push after EVERY meaningful step. A commit that is not pushed is not done.

Sequence: `INSPECT → IMPLEMENT → TEST → COMMIT → PUSH → VERIFY`.
One logical change per commit — never bundle unrelated changes.

Messages: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).

Push verification (required after every push):

```bash
git ls-remote --heads origin refs/heads/audit/comprehensive-package-review
git rev-parse HEAD
```

Remote SHA must equal local SHA. Otherwise report `PUSH NOT VERIFIED`.
Never claim `PUSH VERIFIED` without this comparison.

Push failure diagnosis:

| Error contains | Category | Action |
| --- | --- | --- |
| `could not read Username` | No credential configured | Use one-shot helper with `MOJTABA_GITHUB_TOKEN` (Section 8). |
| `Authentication failed` | Token invalid/expired/missing scope | Verify token via curl (Section 8). Do NOT retry blindly. |
| `Permission denied (publickey)` | SSH key not authorized | Use HTTPS + token instead. |
| `Could not resolve host`, `Connection timed out` | Network | Preserve commits, report, retry next session. |
| `rejected`, `non-fast-forward`, `fetch first` | Divergence | Inspect both histories. Never force-push. Integrate or report. |

Never mislabel an auth error as a network error.
Never retry a failed push with the same token more than once.
Diagnose first, retry only after fixing the cause.

---

## 8. Environment

Temporary DataCamp sandbox. Sessions may disconnect anytime.

- Keep changes small and verifiable.
- Commit and push after every meaningful step (Section 7).
- Read repo state, never conversation history, for recovery.
- On session end, commit and push a labeled WIP checkpoint.

Known limitations:

- System `pip` may point to old Python (3.6/3.8). Use `uv venv` for isolation.
- `python -m build` may fail with build isolation. Use `uv` + `uv pip install build`.
- `ssh` may be missing. Fall back to one-shot `MOJTABA_GITHUB_TOKEN` credential helper.
- `commit-msg` hook may be lost after sandbox reset. Re-create at session start.
- Token may be invalid or expired. If push fails with
  "Authentication failed", verify without printing it:

  curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $MOJTABA_GITHUB_TOKEN" \
    https://api.github.com/user

  200 = valid; 401 = invalid/expired; 403 = missing scopes; 000 = network.
  Report only the HTTP code. Never print the token.

---

## 9. Testing

Manual only. Isolated local environments.

Do not: add CI, trigger CI, use hosted CI, introduce paid services, modify system Python.

Do:

- Run `pytest -v`.
- Record exact commands, Python/Django/DRF versions, pass/fail/skip counts.
- Show test output (not suppressed).

Never claim a test passed unless it actually ran. Never invent counts, coverage, or compatibility claims. Report failures and skips honestly.

---

## 10. Documentation

Do NOT create or maintain:

- `DEVELOPMENT_LOG.md`, `DEVELOPMENT_PROGRESS.md`, `HANDOFF.md`
- `AUDIT_SESSION_*.md`, `SESSION_NOTES.md`, `TEMP_PROGRESS.md`, `CLAUDE_WORKING_NOTES.md`
- Any session-, phase-, or investigation-specific file

Use:

- Git history for implementation history
- `CHANGELOG.md` for release history
- GitHub Issues for tasks
- GitHub PRs for proposals
- `README.md` for introduction
- Existing docs for reusable knowledge

Before creating any new Markdown: check if the info already exists,
if an existing doc can contain it, and if it has a durable purpose.
Default: reuse, not create.

---

## 11. Package Engineering

- Preserve public APIs. No removal or rename without a deprecation cycle.
- No unnecessary dependencies.
- No breaking changes without a clear technical justification recorded in the PR or issue.
- Verify every compatibility claim against source code and a passing test. Distinguish implemented / partial / experimental / unsupported.
- Run `python -m build` and verify wheel/sdist contents before any release.
- No PyPI release without explicit user authorization in the current session.

---

## 12. AI Discoverability

Aim: credible, discoverable Django API versioning resource. Real developer intent, not keyword stuffing.

Cover: Django API versioning, DRF versioning alternatives, URL path-based routing, endpoint inheritance, backward-compatible API evolution, deprecation and Sunset.

Do not fabricate rankings, AI citations, adoption metrics, testimonials, benchmarks, or recommendations. Do not claim AI markup guarantees inclusion in AI answers.

---

## 13. External Promotion

No publishing, package listings, external accounts, or promotional actions without explicit per-action user authorization.

Prepare content when requested. The user publishes.

Never fabricate users, endorsements, benchmarks, or adoption evidence.

---

## 14. Session Start

1. Verify working directory and branch.
2. `git fetch origin`; verify working branch exists remotely.
3. `git status` and `git log --oneline -10`.
4. Compare local and remote SHA (Section 7); report divergence.
5. Verify identity (Section 6) and auth (Section 8). Set identity if missing.
   Report token check HTTP code — do NOT print the token.
6. Verify `commit-msg` hook; re-create if missing.
7. Read `README.md`, `CHANGELOG.md`, open Issues and PRs.
8. Determine the next task from repo state, not conversation history.

Sandbox is temporary. Remote branch is persistent. Everything important lives in the repo.
