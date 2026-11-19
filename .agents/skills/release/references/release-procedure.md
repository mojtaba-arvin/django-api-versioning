# Package release procedure

This procedure applies only after the user explicitly authorizes a concrete version `X.Y.Z`. The only long-lived branch is `main`; a release uses one temporary `release/vX.Y.Z` branch and one reviewed PR.

## 1. Verify the release target and create the branch

Start from a clean checkout. Preserve unrelated work.

```bash
git status --short
test -z "$(git status --porcelain)" || { echo "Working tree must be clean before switching branches." >&2; exit 1; }
git fetch origin --prune --tags
git switch main
git pull --ff-only origin main
git status --short
```

Stop if the working tree is not clean or if local `main` cannot be fast-forwarded.

Read the old version, set the explicitly authorized version, reject an existing tag, and create the release branch from the latest main:

```bash
OLD_VERSION=$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' pyproject.toml | head -n 1)
[ -n "$OLD_VERSION" ] || { echo "Could not read package version from pyproject.toml"; exit 1; }
NEW_VERSION="X.Y.Z"
git show-ref --verify --quiet "refs/tags/v$NEW_VERSION" && {
  echo "Local tag already exists"; exit 1;
}
git ls-remote --exit-code --tags origin "refs/tags/v$NEW_VERSION" >/dev/null 2>&1 && {
  echo "Remote tag already exists"; exit 1;
}
echo "OLD=$OLD_VERSION NEW=$NEW_VERSION"
git switch -c "release/v$NEW_VERSION" origin/main
```

Never overwrite or move an existing release tag.

## 2. Determine release impact

Identify the previous release tag and inspect actual changes since it:

```bash
LAST_TAG=$(git describe --tags --abbrev=0 HEAD 2>/dev/null || true)
if [ -z "$LAST_TAG" ]; then
  echo "No previous tag: inspect the complete history and diff manually."
else
  git log --oneline "$LAST_TAG"..HEAD
  git diff --name-status "$LAST_TAG"..HEAD
fi
```

Do not classify technical impact from commit prefixes alone. Inspect source and tests. Runtime behavior, public API, supported configuration, dependencies, or user-facing integration examples count as technical impact. Test-only, formatting, CI-only, and editorial changes are not automatically technical changes. Compare the workflow definitions at the previous release tag with current `main`: a release gate added after a tag must not be reported as having run for that release. Inspect the actual tag tree and built wheel to distinguish package runtime APIs from repository-only examples and CI tooling.

Apply the version policy in [CONTRIBUTING.md](../../../../CONTRIBUTING.md). Update the dated `CHANGELOG.md` section using only categories that apply. Changelog entries describe user-visible changes; do not copy test counts, CI logs, task status, or internal implementation notes into the changelog.

## 3. Handle article updates carefully

Enumerate the current article corpus at execution time:

```bash
find docs/articles -maxdepth 1 -type f -name '*.md' -print | sort
```

If technical behavior changed, identify affected articles and ask the user whether any article CONTENT needs to change. Release authorization does not authorize rewriting article prose or examples.

Update only exact package-version references, such as `django-api-versioning==OLD`, `>=OLD`, `~=OLD`, or package dependency declarations. Do not replace unrelated Django, Python, DRF, or API version numbers. Report remaining occurrences of `OLD_VERSION` not adjacent to the package name; do not auto-rewrite ambiguous references.

Update `README.md` only when its actual content is stale and available evidence supports the correction. Historical compatibility reports under `docs/reports/` are immutable evidence; do not rewrite them to reflect current matrix configuration or results. Configured environments are not evidence that they passed.

## 4. Prepare one coherent release change

Update package version in `pyproject.toml`, the dated changelog entry, and any approved documentation/version pins. Stage explicit paths only.

```bash
git diff --check
git status --short
git diff
git add pyproject.toml CHANGELOG.md
# Add only documentation paths that were actually changed and reviewed.
git diff --cached --check
git diff --cached
```

Commit the release preparation as one logical change, not one commit per file:

```bash
git commit -m "chore(release): prepare v$NEW_VERSION"
.claude/push.sh
```

The push helper pushes the current short-lived branch and refuses `main`. If push verification fails, stop and inspect remote state; do not force-push.

## 5. Open the release PR and validate its exact head

Open a PR from `release/vX.Y.Z` to `main`. Include the version, changelog summary, technical-impact classification, approved article changes, and verification plan.

Require successful results for every workflow relevant to the PR's changed paths. Because `pyproject.toml` changes, inspect at least:

- Python unit and integration tests;
- the complete compatibility matrix, including every environment configured by current `tox.ini`;
- wheel/sdist build, metadata validation, installed-wheel smoke test, and distribution-content checks.

If website/article files changed, also inspect Website build and static verification. If agent instructions or skills changed, inspect Agent tooling.

Require the always-running `PR gate` to pass for the exact latest PR head SHA. The gate invokes every path-relevant reusable workflow; a child workflow may be skipped only when the path classifier marks its scope unchanged. Independently inspect CodeQL results for package or website source changes. A failed, pending, or stale applicable check is not a pass. Fix failures on the same release branch; do not bypass a relevant failing check.

Merge the PR through GitHub only after relevant checks pass. Never push the release branch directly to `main`.

## 6. Tag the exact merged commit

After merge, fetch `main` and obtain the PR merge commit SHA:

```bash
PR_NUMBER="123"
git fetch origin main --tags
MERGE_SHA=$(gh pr view "$PR_NUMBER" --json mergeCommit --jq '.mergeCommit.oid')
test -n "$MERGE_SHA"
git merge-base --is-ancestor "$MERGE_SHA" origin/main || {
  echo "Release PR merge commit is not on origin/main; stop."
  exit 1
}
```

Verify that the exact merge commit contains the requested package version:

```bash
git show "$MERGE_SHA:pyproject.toml" | grep -E '^version[[:space:]]*='
```

If it does not equal `NEW_VERSION`, stop. Verify the tag remains absent, then create an annotated tag on the exact merge commit:

```bash
git tag -a "v$NEW_VERSION" "$MERGE_SHA" -m "Release v$NEW_VERSION"
git push origin "refs/tags/v$NEW_VERSION"
```

Push only this explicit tag. Do not use `git push --tags`. The active `Protect release tags` ruleset must reject tag updates/deletion and restrict bypass to repository administrators.

Verify the remote annotated tag object:

```bash
LOCAL_TAG_SHA=$(git rev-parse "refs/tags/v$NEW_VERSION")
REMOTE_TAG_SHA=$(git ls-remote origin "refs/tags/v$NEW_VERSION" | awk '{print $1}')
test -n "$REMOTE_TAG_SHA" && test "$LOCAL_TAG_SHA" = "$REMOTE_TAG_SHA" || {
  echo "Remote tag verification failed"; exit 1;
}
```

## 7. Verify publication and create the GitHub release

The v* tag triggers .github/workflows/publish.yml. The main-branch push must already have completed the full compatibility matrix successfully for the exact tagged commit. The tag workflow verifies and reuses that run instead of running the full matrix a second time, then runs the OpenAPI contract, builds and validates wheel/sdist, smoke-tests the installed wheel, verifies distribution boundaries, and publishes the verified artifact to PyPI using trusted publishing. Create the tag only after the exact main-branch compatibility run is successful. The publish job alone receives `id-token: write`.

Do not announce success while the workflow is pending or failed. Verify the exact version endpoint:

```bash
curl -fsS "https://pypi.org/p/django-api-versioning/$NEW_VERSION/json" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["info"]["version"])'
```

The returned version must equal `NEW_VERSION`. Checking only the package's latest-version endpoint is insufficient.

After PyPI confirms the version, create and verify the GitHub release if `gh` is authenticated:

```bash
gh release create "v$NEW_VERSION" --title "v$NEW_VERSION" --generate-notes
gh release view "v$NEW_VERSION" --json tagName,isDraft,url
```

If GitHub Release creation is unavailable, report the manual URL:
`https://github.com/mojtaba-arvin/django-api-versioning/releases/new?tag=vX.Y.Z`

## 8. Report

Report only verified facts: package version and tag; tagged merge commit and annotated tag object SHAs; PR number and merged state; relevant CI results and exact PR head SHA; tag workflow result; GitHub Release URL; version-specific PyPI endpoint result; and article version-pin/content changes plus ambiguous old-version mentions.

Never invent test counts, claim skipped matrix environments passed, or claim PyPI publication before the exact version endpoint confirms it.
