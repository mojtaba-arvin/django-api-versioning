#!/usr/bin/env bash
set -Eeuo pipefail
REPO="mojtaba-arvin/django-api-versioning"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "Run from a repository clone." >&2; exit 2; }
cd "$ROOT"
die() { echo "ERROR: $*" >&2; exit 2; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"; }
auth() {
  need gh
  gh auth status >/dev/null 2>&1 || die "Run gh auth login first."
  [[ "$(gh repo view "$REPO" --json nameWithOwner --jq .nameWithOwner)" == "$REPO" ]] || die "Wrong GitHub repository context."
  local origin_url
  origin_url="$(git remote get-url origin)"
  case "$origin_url" in
    "https://github.com/$REPO"|"https://github.com/$REPO.git"|"git@github.com:$REPO"|"git@github.com:$REPO.git"|"ssh://git@github.com/$REPO"|"ssh://git@github.com/$REPO.git") ;;
    *) die "origin remote '$origin_url' is not the canonical repository $REPO." ;;
  esac
}
version_check() {
  [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || die "Expected a SemVer version such as 1.3.0."
}
preflight() {
  local v="$1" tag="v$1"
  release_source_check "$v"
  ! git show-ref --verify --quiet "refs/tags/$tag" || die "Local tag $tag already exists."
  ! git ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null 2>&1 || die "Remote tag $tag already exists."
  echo "PASS: clean main, package version, changelog entry, current uv.lock, and unused tag."
}
create_github_release() {
  local v="$1" tag="v$1" tag_type published run_json notes_file
  version_check "$v"; auth; need curl; need jq; need python3
  tag_type="$(gh api "repos/$REPO/git/ref/tags/$tag" --jq '.object.type')" || die "Remote tag $tag does not exist."
  [[ "$tag_type" == tag ]] || die "$tag is not an annotated tag."
  run_json="$(gh run list --repo "$REPO" --workflow publish.yml --branch "$tag" --limit 10 --json status,conclusion)"
  echo "$run_json" | jq -e 'any(.[]; .status == "completed" and .conclusion == "success")' >/dev/null ||
    die "No successful Publish to PyPI workflow run found for $tag."
  published="$(curl --fail --silent --show-error "https://pypi.org/pypi/django-api-versioning/$v/json" | jq -r '.info.version')"
  [[ "$published" == "$v" ]] || die "PyPI does not report the requested version $v."
  if gh release view "$tag" --repo "$REPO" >/dev/null 2>&1; then
    echo "GitHub Release $tag already exists; leaving it unchanged."
    return
  fi
  notes_file="$(mktemp)"
  trap 'rm -f "$notes_file"' RETURN
  RELEASE_VERSION="$v" NOTES_FILE="$notes_file" python3 - <<'PY'
import os
import re
from pathlib import Path

version = os.environ["RELEASE_VERSION"]
lines = Path("CHANGELOG.md").read_text(encoding="utf-8").splitlines()
heading = re.compile(rf"^## \[{re.escape(version)}\](?: - .*)?$")
start = next((i for i, line in enumerate(lines) if heading.match(line)), None)
if start is None:
    raise SystemExit(f"No dated CHANGELOG.md section found for {version}.")
end = next(
    (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
    len(lines),
)
notes = "\n".join(lines[start + 1:end]).strip()
if not notes:
    raise SystemExit(f"CHANGELOG.md section for {version} is empty.")
Path(os.environ["NOTES_FILE"]).write_text(notes + "\n", encoding="utf-8")
PY
  gh release create "$tag" --repo "$REPO" --verify-tag \
    --title "django-api-versioning $v" --notes-file "$notes_file"
}

wait_for_workflow() {
  local workflow="$1" commit="$2" description="$3"
  local timeout="${RELEASE_WAIT_TIMEOUT_SECONDS:-3600}" interval="${RELEASE_POLL_INTERVAL_SECONDS:-15}"
  local deadline runs run_id status conclusion run_url

  [[ "$timeout" =~ ^[0-9]+$ && "$interval" =~ ^[0-9]+$ ]] || die "Release wait timeout and poll interval must be integers."
  (( timeout > 0 && interval > 0 )) || die "Release wait timeout and poll interval must be greater than zero."
  deadline=$((SECONDS + timeout))
  echo "Waiting for $description (timeout: ${timeout}s)..."
  while (( SECONDS < deadline )); do
    runs="$(gh run list --repo "$REPO" --workflow "$workflow" --commit "$commit" --limit 20 --json databaseId,status,conclusion,event,headSha,url)"
    run_id="$(printf '%s' "$runs" | jq -r --arg sha "$commit" '[.[] | select(.headSha == $sha and .event == "push")][0].databaseId // empty')"
    if [[ -n "$run_id" ]]; then
      status="$(printf '%s' "$runs" | jq -r --argjson id "$run_id" '.[] | select(.databaseId == $id) | .status')"
      conclusion="$(printf '%s' "$runs" | jq -r --argjson id "$run_id" '.[] | select(.databaseId == $id) | .conclusion // empty')"
      run_url="$(printf '%s' "$runs" | jq -r --argjson id "$run_id" '.[] | select(.databaseId == $id) | .url')"
      if [[ "$status" == completed ]]; then
        [[ "$conclusion" == success ]] || die "$description failed ($conclusion): $run_url"
        echo "PASS: $description ($run_url)"
        return 0
      fi
      echo "Workflow run #$run_id is $status: $run_url"
      sleep "$interval"
    else
      echo "No $description run found yet for commit $commit; checking again..."
      sleep "$interval"
    fi
  done
  die "Timed out waiting for $description after ${timeout}s. Existing release state was left intact; rerun the same command to resume."
}

release_source_check() {
  local v="$1" actual
  version_check "$v"; auth; need git; need python3; need jq; need uv
  [[ "$(git branch --show-current)" == main ]] || die "Switch to main first."
  [[ -z "$(git status --porcelain)" ]] || die "Working tree must be clean."
  git fetch origin --prune
  [[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || die "Local main must exactly match origin/main."
  actual="$(package_version)"
  [[ "$actual" == "$v" ]] || die "pyproject.toml version is $actual, not $v."
  grep -Fq "## [$v] - " CHANGELOG.md || die "Missing dated CHANGELOG.md section for [$v]."
  uv lock --check || die "uv.lock is stale or inconsistent; run uv lock, commit uv.lock, and retry."
}

package_version() {
  need python3
  python3 - <<'PY'
from pathlib import Path
import re

source = Path("pyproject.toml").read_text(encoding="utf-8")
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        project = re.search(r"(?ms)^\[project\]\s*$(.*?)(?=^\[|\Z)", source)
        match = re.search(r"(?m)^version\s*=\s*['\"]([^'\"]+)['\"]\s*$", project.group(1) if project else "")
        if not match:
            raise SystemExit("Could not read [project].version from pyproject.toml")
        print(match.group(1))
    else:
        print(tomllib.loads(source)["project"]["version"])
else:
    print(tomllib.loads(source)["project"]["version"])
PY
}

release_interactive() {
  local v current_branch answer
  need git
  [[ -z "$(git status --porcelain)" ]] || die "Working tree is not clean. Commit or safely stash your changes before releasing."
  current_branch="$(git branch --show-current)"
  if [[ "$current_branch" != main ]]; then
    echo "Switching from $current_branch to main (working tree is clean)..."
    git switch main
  fi
  echo "Updating main from origin..."
  git pull --ff-only origin main
  v="$(package_version)"
  version_check "$v"
  echo
  echo "Release preview"
  echo "  Package: django-api-versioning"
  echo "  Version: $v (read automatically from pyproject.toml)"
  echo "  Tag:     v$v"
  echo "  Source:  $(git rev-parse --short HEAD) on main"
  echo "  Changelog: $(grep -F "## [$v] - " CHANGELOG.md | head -n 1 || true)"
  echo
  release_source_check "$v"
  echo "Pre-release checks passed."
  if [[ ! -t 0 ]]; then
    die "Interactive confirmation is required. Run 'make release' in a terminal."
  fi
  read -r -p "Publish version $v to PyPI and create its GitHub Release? [y/N] " answer
  case "$answer" in
    y|Y|yes|YES) ;;
    *) echo "Release cancelled; no tag was created and nothing was published."; return 0 ;;
  esac
  release_finish "$v"
}

release_finish() {
  local v="$1" tag="v$1" commit local_type remote_ref remote_type remote_tag_sha remote_commit
  version_check "$v"; auth; need git; need jq; need curl; need python3
  release_source_check "$v"
  commit="$(git rev-parse HEAD)"

  # Resume safely if a previous attempt already created or pushed this exact tag.
  if git show-ref --verify --quiet "refs/tags/$tag"; then
    local_type="$(git cat-file -t "refs/tags/$tag")"
    [[ "$local_type" == tag ]] || die "Local $tag is lightweight; refusing to publish."
    [[ "$(git rev-parse "$tag^{commit}")" == "$commit" ]] || die "Local $tag does not point to current main."
  fi
  remote_ref="$(gh api "repos/$REPO/git/ref/tags/$tag" 2>/dev/null || true)"
  if [[ -n "$remote_ref" ]]; then
    remote_type="$(printf '%s' "$remote_ref" | jq -r '.object.type')"
    remote_tag_sha="$(printf '%s' "$remote_ref" | jq -r '.object.sha')"
    [[ "$remote_type" == tag ]] || die "Remote $tag is not annotated; refusing to publish."
    remote_commit="$(gh api "repos/$REPO/git/tags/$remote_tag_sha" --jq '.object.sha')"
    [[ "$remote_commit" == "$commit" ]] || die "Remote $tag points to $remote_commit, not current main $commit."
    if ! git show-ref --verify --quiet "refs/tags/$tag"; then
      git fetch origin "refs/tags/$tag:refs/tags/$tag"
    fi
    echo "Existing remote tag $tag is valid; resuming release."
  else
    if git show-ref --verify --quiet "refs/tags/$tag"; then
      echo "Pushing existing local annotated tag $tag..."
    else
      ! git ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null 2>&1 || die "Tag $tag exists remotely but could not be resolved through GitHub API."
      git tag -a "$tag" -m "Release $tag"
    fi
    git push origin "refs/tags/$tag" || die "Could not push $tag. Check the v* tag ruleset and your GitHub permissions; no PyPI publication was started."
  fi

  wait_for_workflow publish.yml "$commit" "the complete release workflow (build, PyPI publication, and GitHub Release)"
  local published release_url
  published="$(curl --fail --silent --show-error "https://pypi.org/pypi/django-api-versioning/$v/json" | jq -r '.info.version')"
  [[ "$published" == "$v" ]] || die "Release workflow succeeded but PyPI does not report version $v."
  release_url="$(gh release view "$tag" --repo "$REPO" --json url --jq .url)" || die "PyPI publication succeeded, but GitHub Release $tag is not visible yet."
  echo
  echo "RELEASE COMPLETE"
  echo "  Version:        $v"
  echo "  Commit:         $commit"
  echo "  Git tag:        $tag"
  echo "  PyPI:           https://pypi.org/project/django-api-versioning/$v/"
  echo "  GitHub Release: $release_url"
}

release() {
  local action="$1" v="$2" tag="v$2"
  case "$action" in
    preflight) preflight "$v" ;;
    tag)
      preflight "$v"
      git tag -a "$tag" -m "Release $tag"
      git push origin "refs/tags/$tag"
      echo "Pushed $tag. Use 'release finish' to wait for and verify the complete publication."
      ;;
    finish) release_finish "$v" ;;
    create) create_github_release "$v" ;;
    status)
      version_check "$v"; auth; need curl; need jq
      echo "== Tag =="; gh api "repos/$REPO/git/ref/tags/$tag" --jq '.object | {type,sha}' || true
      echo "== GitHub Release =="; gh api "repos/$REPO/releases/tags/$tag" --jq '{html_url,published_at}' || true
      echo "== Publish workflow =="; gh run list --repo "$REPO" --workflow publish.yml --branch "$tag" --limit 3 --json databaseId,status,conclusion,url
      echo "== PyPI =="
      curl --fail --silent --show-error "https://pypi.org/pypi/django-api-versioning/$v/json" | jq -r '"PUBLISHED: " + .info.version'
      ;;
    *) die "Unknown release action: $action" ;;
  esac
}
branches() {
  local apply=false
  [[ "$#" -eq 0 ]] || { [[ "$1" == --apply ]] || die "Only supported option: --apply"; apply=true; }
  auth; need git; need jq
  [[ "$(gh repo view "$REPO" --json defaultBranchRef --jq .defaultBranchRef.name)" == main ]] || die "Default branch is not main; refusing cleanup."
  git fetch origin --prune
  local open_file refs_file name protected ahead safe=0 kept=0
  open_file="$(mktemp)"; refs_file="$(mktemp)"
  trap 'rm -f "$open_file" "$refs_file"' RETURN
  gh pr list --repo "$REPO" --state open --limit 1000 --json headRefName --jq '.[].headRefName' > "$open_file"
  gh api --paginate "repos/$REPO/branches?per_page=100" --jq '.[] | [.name,(.protected|tostring)] | @tsv' > "$refs_file"
  while IFS=$'\t' read -r name protected; do
    [[ -n "$name" && "$name" != main ]] || continue
    if [[ "$protected" == true ]] || grep -Fxq -- "$name" "$open_file"; then
      printf 'KEEP protected/open PR: %s\n' "$name"; ((kept+=1)); continue
    fi
    if ! git show-ref --verify --quiet "refs/remotes/origin/$name"; then
      printf 'KEEP unavailable locally: %s\n' "$name"; ((kept+=1)); continue
    fi
    if git merge-base --is-ancestor "origin/$name" origin/main; then
      if [[ "$apply" == true ]]; then git push origin --delete "$name"; printf 'DELETED: %s\n' "$name"
      else printf 'DELETE CANDIDATE (merged): %s\n' "$name"; fi
      ((safe+=1))
    else
      ahead="$(git rev-list --count "origin/main..origin/$name")"
      printf 'KEEP unmerged (%s unique commits): %s\n' "$ahead" "$name"; ((kept+=1))
    fi
  done < "$refs_file"
  if [[ "$apply" == true ]]; then printf 'Cleanup complete: %s deleted, %s retained.\n' "$safe" "$kept"
  else printf 'Dry run: %s candidate(s), %s retained. Use --apply to delete only merged branches.\n' "$safe" "$kept"; fi
}
case "${1:-}" in
  release)
    if [[ "$#" -eq 1 ]]; then
      release_interactive
    elif [[ "$#" -eq 3 ]]; then
      release "$2" "$3"
    else
      die "Usage: make release (recommended), or scripts/maintain.sh release {preflight|tag|finish|create|status} VERSION"
    fi
    ;;
  branches) [[ "$#" -le 2 ]] || die "Usage: scripts/maintain.sh branches [--apply]"; if [[ "${2:-}" == --apply ]]; then branches --apply; else branches; fi ;;
  -h|--help|help) echo "Recommended: make release (auto-detect version, sync main, confirm, publish, and verify)."; echo "Advanced: scripts/maintain.sh release {preflight|tag|finish|create|status} VERSION | branches [--apply]" ;;
  *) die "Unknown command. Use --help." ;;
esac
