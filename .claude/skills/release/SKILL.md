# Skill: /release — cut a version

Triggered by "release X.Y.Z". Do exactly this. No improvisation.

## Preconditions
- Working tree clean (`git status`).
- On `audit/comprehensive-package-review`.
- User has authorized a PyPI release for THIS version.
- `docs/articles/` exists; enumerate the current article files at execution time rather than assuming a fixed count.

## Environment
- `DAV_GITHUB_TOKEN` set in the sandbox.
- Check whether `gh` is installed with `command -v gh`; do not assume an OS or architecture.
- Each Bash call runs in a fresh shell. Re-establish required PATH entries in every call.

## Steps

### 1. Confirm X.Y.Z and save old version

If ambiguous, stop and ask.

```bash
OLD_VERSION=$(git show HEAD:pyproject.toml \
  | grep -E '^version' | head -1 \
  | sed -E 's/.*"([^"]+)".*/\1/')
NEW_VERSION="X.Y.Z"
echo "OLD=$OLD_VERSION NEW=$NEW_VERSION"
```

If `$OLD_VERSION` is empty, stop and report — pyproject.toml has
no `version` line.

### 2. Full test suite via tox

Before running Full, use the current `tox.ini` as the source of truth.
Verify that it declares `tox-uv`, that the integration test settings
file exists, and that every Python interpreter required by the matrix
is installed. The current matrix requires Python 3.10–3.15:

```bash
command -v uv >/dev/null || { echo "uv is required"; exit 1; }
uv python install 3.10 3.11 3.12 3.13 3.14 3.15
for v in 3.10 3.11 3.12 3.13 3.14 3.15; do
  uv python list | grep -q "cpython-$v" || { echo "missing Python $v"; exit 1; }
done
grep -q 'requires = tox-uv' tox.ini || { echo "tox.ini does not declare tox-uv"; exit 1; }
[ -f integration_test_project/pytest.ini ] || { echo "missing integration_test_project/pytest.ini"; exit 1; }

if [ ! -x /tmp/tox/bin/tox ]; then
  uv venv /tmp/tox --python 3.15
  uv pip install --python /tmp/tox/bin/python tox tox-uv
fi
/tmp/tox/bin/tox --version
```

Do not start tox if any interpreter or prerequisite is missing.
Do not accept a partial matrix or `NOT-RUN` environments as a
successful release test. Re-read `tox.ini` and derive the expected
environment count from its current envlist rather than hardcoding
an old count.

Run the complete matrix and preserve tox's real exit code:

```bash
set -o pipefail
PATH="$HOME/.local/bin:$PATH" /tmp/tox/bin/tox 2>&1 | tee /tmp/tox-release.log
TOX_EXIT=${PIPESTATUS[0]}
echo "TOX_EXIT=$TOX_EXIT"
```

If `TOX_EXIT` is non-zero, STOP. Parse `/tmp/tox-release.log` for
failing and `NOT-RUN` envs. Do not bump version. Do not tag.
Report the exact failing or unrun env names and classify test failures
separately from environment/setup failures.

Do NOT run `/compat-matrix` — that skill was removed. tox is the
only matrix.

### 3. Bump `pyproject.toml`

Edit the `version = "X.Y.Z"` line.

```bash
git add pyproject.toml
git commit -m "chore: bump version to $NEW_VERSION"
.claude/push.sh
```

If `.claude/push.sh` exits non-zero: STOP. Do not continue.

### 4. Update `CHANGELOG.md`

Add a dated section for `X.Y.Z`. Use only the Keep a Changelog
categories that actually apply; do not add empty headings merely
to include every category. Record the unit and integration test
counts observed in the successful Step 2 log. Never infer or reuse
historical counts.

```bash
git add CHANGELOG.md
git commit -m "docs: update changelog for v$NEW_VERSION"
.claude/push.sh
```

If push fails: STOP.

### 5. Articles in `docs/articles/`

#### 5a. Detect technical impact since last tag

```bash
LAST_TAG=$(git describe --tags --abbrev=0 HEAD 2>/dev/null || echo "")
if [ -z "$LAST_TAG" ]; then
  TECH=yes
  REASON="no previous tag — inspect the full release diff"
else
  echo "Commits since $LAST_TAG:"
  git log --oneline "$LAST_TAG"..HEAD
  echo "Changed paths since $LAST_TAG:"
  git diff --name-status "$LAST_TAG"..HEAD
fi
```

Do not decide technical impact from commit prefixes alone. Inspect the
actual diffs for every `feat:` and `fix:` commit and any other
package-facing changes. Set `TECH=yes` only when package runtime
behavior, public API, supported configuration, or user-facing
integration examples changed. Test-only changes, import cleanup,
formatting, CI changes, and documentation-only corrections do not
by themselves make `TECH=yes`. Record the relevant commits and
the evidence for the classification. If there is no previous tag,
inspect the complete diff and default to asking rather than silently
assuming that all articles need content changes.

#### 5b. If TECH=yes: STOP and ask

Report:

- `TECH=yes` and the reason
- The list of feat/fix commits:
  ```bash
  git log --oneline "$LAST_TAG"..HEAD | grep -E '^(feat|fix)(\(|:)'
  ```
- The article file list:
  ```bash
  ls docs/articles/*.md
  ```

Ask exactly this:

> "The release includes technical changes. These are the current article files
> that reference the package: <list>. I will update package version
> strings in all articles. If any article needs CONTENT updates
> (examples, API, behavior), tell me which article and what to
> change. Otherwise reply 'proceed' and I will only update
> version strings."

Wait for a single response:
- `"proceed"` or equivalent → go to 5c
- A specific list of articles → record them, go to 5c, then
  handle content edits in 5e

If TECH=no: skip the question, go directly to 5c.

#### 5c. Update package version strings (all articles)

Use Python for safe literal replacement — avoids sed regex
escaping problems with version dots.

```bash
OLD_VERSION="$OLD_VERSION" NEW_VERSION="$NEW_VERSION" python3 <<'PYEOF'
import os, pathlib
OLD = os.environ["OLD_VERSION"]; NEW = os.environ["NEW_VERSION"]
patterns = [
    (f"django-api-versioning=={OLD}", f"django-api-versioning=={NEW}"),
    (f"django-api-versioning>={OLD}", f"django-api-versioning>={NEW}"),
    (f"django-api-versioning~={OLD}", f"django-api-versioning~={NEW}"),
    (f"django-api-versioning<={OLD}", f"django-api-versioning<={NEW}"),
    (f'django-api-versioning = "{OLD}"', f'django-api-versioning = "{NEW}"'),
    (f"django-api-versioning = '{OLD}'", f"django-api-versioning = '{NEW}'"),
]
changed = []
for p in pathlib.Path("docs/articles").rglob("*.md"):
    c = p.read_text()
    nc = c
    for a, b in patterns:
        nc = nc.replace(a, b)
    if nc != c:
        p.write_text(nc); changed.append(str(p))
print(f"Changed {len(changed)} files:")
for f in changed: print(f"  {f}")
PYEOF
```

Do not touch any other version-like string. Bare mentions of
`$OLD_VERSION` (not adjacent to the package name) might refer to
Django versions and must not be replaced.

#### 5d. Report remaining old-version mentions

```bash
grep -rn "$OLD_VERSION" docs/articles/ 2>/dev/null \
  | grep -v "django-api-versioning" \
  || echo "No other mentions of $OLD_VERSION in articles"
```

If any remaining mention exists, report each line to the user
verbatim. Do NOT auto-replace them — they are ambiguous.

#### 5e. Commit article changes

If only version strings were updated (no content edits):

```bash
if [ -n "$(git diff --name-only docs/articles/)" ]; then
  git add docs/articles/
  git commit -m "docs: bump package version to $NEW_VERSION in articles"
  .claude/push.sh
fi
```

If content edits were authorized in 5b: after the version-only
commit, edit the specified articles, then for each one:

```bash
git add docs/articles/<article>.md
git commit -m "docs: update <article> for $NEW_VERSION"
.claude/push.sh
```

If `.claude/push.sh` exits non-zero at any point: STOP.

### 6. Update `README.md` if compatibility or counts changed

```bash
grep -rn "$OLD_VERSION" README.md 2>/dev/null || echo "No old version in README"
```

If changed:

```bash
git add README.md
git commit -m "docs: update README for v$NEW_VERSION"
.claude/push.sh
```

If README does not need changes, skip this step.

### 7. Build (no commit of artifacts)

```bash
uv venv /tmp/build --python 3.15 && \
  source /tmp/build/bin/activate && \
  python -m pip install --quiet build && \
  python -m build --outdir /tmp/dist && \
  ls -lh /tmp/dist/ && \
  rm -rf /tmp/build
```

Expected artifacts:
- `django_api_versioning-$NEW_VERSION-py3-none-any.whl`
- `django_api_versioning-$NEW_VERSION.tar.gz`

If build fails, fix the cause in a new commit, push, then retry.
Do not tag until build succeeds.

### 8. Create tag

```bash
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
```

### 9. Push tag

```bash
.claude/push.sh --tag
```

If exit != 0: STOP. Do not create GitHub release.

Verify that the annotated tag object was pushed to the remote:

```bash
LOCAL_TAG_SHA=$(git rev-parse "refs/tags/v$NEW_VERSION")
REMOTE_TAG_SHA=$(git ls-remote origin "refs/tags/v$NEW_VERSION" | awk '{print $1}')
echo "LOCAL_TAG_SHA=$LOCAL_TAG_SHA REMOTE_TAG_SHA=$REMOTE_TAG_SHA"
[ -n "$REMOTE_TAG_SHA" ] && [ "$LOCAL_TAG_SHA" = "$REMOTE_TAG_SHA" ] || {
  echo "Tag push verification failed"; exit 1;
}
```

Do not proceed if the remote tag is absent or its SHA differs.

### 10. Install `gh` if missing (best-effort)

Use the installed binary when available. Otherwise detect the OS and
architecture; do not assume Linux x86_64:

```bash
GH_BIN=$(command -v gh || true)
if [ -z "$GH_BIN" ]; then
  OS=$(uname -s)
  ARCH=$(uname -m)
  case "$OS:$ARCH" in
    Darwin:x86_64) PLATFORM="macOS_amd64" ;;
    Darwin:arm64) PLATFORM="macOS_arm64" ;;
    Linux:x86_64) PLATFORM="linux_amd64" ;;
    Linux:aarch64|Linux:arm64) PLATFORM="linux_arm64" ;;
    *) echo "Unsupported gh platform: $OS $ARCH"; exit 1 ;;
  esac
  LATEST=$(curl -fsSL https://api.github.com/repos/cli/cli/releases/latest \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))')
  mkdir -p "$HOME/.local/bin"
  curl -fsSL "https://github.com/cli/cli/releases/download/v${LATEST}/gh_${LATEST}_${PLATFORM}.tar.gz" \
    -o /tmp/gh.tar.gz
  tar -xzf /tmp/gh.tar.gz -C /tmp
  cp "/tmp/gh_${LATEST}_${PLATFORM}/bin/gh" "$HOME/.local/bin/gh"
  chmod +x "$HOME/.local/bin/gh"
  rm -f /tmp/gh.tar.gz
  GH_BIN="$HOME/.local/bin/gh"
fi
"$GH_BIN" --version
```

If installation exits non-zero, do not retry. Skip GitHub release
creation, report the manual release URL, and continue to Step 12.

### 11. Create GitHub release

```bash
GH_TOKEN="$DAV_GITHUB_TOKEN" "$HOME/.local/bin/gh" release create "v$NEW_VERSION" \
  --title "v$NEW_VERSION" \
  --generate-notes
```

Verify:

```bash
GH_TOKEN="$DAV_GITHUB_TOKEN" "$HOME/.local/bin/gh" release view "v$NEW_VERSION" \
  --json tagName,isDraft,url
```

If creation failed, report:

    https://github.com/mojtaba-arvin/django-api-versioning/releases/new?tag=vX.Y.Z

and continue to Step 12.

### 12. Verify PyPI

Tag push triggers `.github/workflows/publish.yml` (trigger:
`push: tags: v*`).

```bash
for i in $(seq 1 6); do
  sleep 30
  V=$(curl -fsS "https://pypi.org/pypi/django-api-versioning/$NEW_VERSION/json" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])") || V=""
  echo "attempt $i: PyPI release endpoint shows ${V:-not available}"
  [ "$V" = "$NEW_VERSION" ] && break
done
```

If after 3 minutes PyPI does not show `$NEW_VERSION`, report:

    https://github.com/mojtaba-arvin/django-api-versioning/actions

Do NOT claim publication success unless the version-specific PyPI
endpoint returns `$NEW_VERSION`. Checking only the package's
latest-version endpoint is insufficient because a later release
could already have become the latest.

### 13. Report

State exactly:

- Version: `$NEW_VERSION`
- Tag: `v$NEW_VERSION`
- Tag SHA: `git rev-parse "v$NEW_VERSION"`
- Branch push: from `.claude/push.sh` exit code in Step 3
- Tag push: from `.claude/push.sh --tag` exit code in Step 9
- GitHub release URL: from Step 11 output, or the manual URL
- PyPI version: from Step 12 curl output
- Articles: version-only updates = N, content updates = M,
  remaining old-version mentions = K

## Never
- Never tag before branch push verifies.
- Never claim PyPI published without the curl check.
- Never fabricate test counts.
- Never rely on `PATH` exports from a previous Bash call.
- Never print `DAV_GITHUB_TOKEN`.
- Never edit article content without explicit user instruction.
- Never replace bare `$OLD_VERSION` mentions that are not adjacent
  to `django-api-versioning`.
- Never skip Step 5a — the technical-impact check is mandatory.
