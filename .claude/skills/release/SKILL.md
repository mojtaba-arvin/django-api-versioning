# Skill: /release — cut a version

Triggered by "release X.Y.Z". Do exactly this. No improvisation.

## Preconditions
- Working tree clean (`git status`).
- On `audit/comprehensive-package-review`.
- User has authorized a PyPI release for THIS version.
- `docs/articles/` exists (25 user-authored articles).

## Environment
- `DAV_GITHUB_TOKEN` set in the sandbox.
- `gh` is NOT pre-installed. Install at Step 11.
- Each Bash call runs in a fresh shell. Use full paths:
  `$HOME/.local/bin/gh`.

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

### 2. Full test on Python 3.15 (unit + integration)

```bash
V=3.15
uv venv /tmp/rel --python $V
uv pip install --python /tmp/rel/bin/python \
  -e . pytest pytest-django djangorestframework

/tmp/rel/bin/python --version
/tmp/rel/bin/python -m pytest tests/ -v --tb=short 2>&1 | tee /tmp/rel-unit.log
/tmp/rel/bin/python -m pytest integration_test_project/tests/ -v --tb=short 2>&1 | tee /tmp/rel-integ.log

rm -rf /tmp/rel
```

Record: Python version, Django version, DRF version, unit
passed/failed, integration passed/failed.

If any test fails, STOP. Do not bump version. Do not tag.

For the full Python × Django matrix, this skill does NOT run it.
If the user wants the release to carry a verified matrix, ask:

> "Run `/compat-matrix` first? It takes ~60 min."

If yes: run `/compat-matrix` before Step 3.
If no: proceed and state in the release notes that only
Python 3.15 was tested for this release.

### 3. Bump `pyproject.toml`

Edit the `version = "X.Y.Z"` line.

```bash
git add pyproject.toml
git commit -m "chore: bump version to $NEW_VERSION"
.claude/push.sh
```

If `.claude/push.sh` exits non-zero: STOP. Do not continue.

### 4. Update `CHANGELOG.md`

Add a dated section for `X.Y.Z`. Include Added / Changed / Fixed /
Removed. Include the unit and integration test counts recorded
in Step 2.

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
  REASON="no previous tag — assuming full impact"
else
  N=$(git log --oneline "$LAST_TAG"..HEAD \
    | grep -cE '^(feat|fix)(\(|:)' || true)
  if [ "$N" -gt 0 ]; then
    TECH=yes
    REASON="$N feat/fix commits since $LAST_TAG"
  else
    TECH=no
    REASON="no feat/fix commits since $LAST_TAG"
  fi
fi
echo "TECH=$TECH REASON=$REASON"
```

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

> "The release includes technical changes. These 25 articles
> reference the package: <list>. I will update package version
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

### 10. Install `gh` if missing (best-effort)

```bash
if ! [ -x "$HOME/.local/bin/gh" ]; then
  mkdir -p "$HOME/.local/bin"
  LATEST=$(curl -s https://api.github.com/repos/cli/cli/releases/latest \
    | grep -oP '(?<=tag_name": "v)[^"]+')
  curl -fsSL "https://github.com/cli/cli/releases/download/v${LATEST}/gh_${LATEST}_linux_amd64.tar.gz" \
    -o /tmp/gh.tar.gz
  tar -xzf /tmp/gh.tar.gz -C /tmp
  cp "/tmp/gh_${LATEST}_linux_amd64/bin/gh" "$HOME/.local/bin/gh"
  chmod +x "$HOME/.local/bin/gh"
  rm -f /tmp/gh.tar.gz
fi
"$HOME/.local/bin/gh" --version
```

If install exits non-zero, skip to Step 12 and report the URL
only. Do not retry more than once.

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
  V=$(curl -s https://pypi.org/pypi/django-api-versioning/json \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])")
  echo "attempt $i: PyPI shows $V"
  [ "$V" = "$NEW_VERSION" ] && break
done
```

If after 3 minutes PyPI does not show `$NEW_VERSION`, report:

    https://github.com/mojtaba-arvin/django-api-versioning/actions

Do NOT claim publication success unless the curl output shows
`$NEW_VERSION`.

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
