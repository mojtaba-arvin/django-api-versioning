#!/usr/bin/env bash
#
# Package release helper — intentionally supports one public command:
#
#   make release
#
# Run it from anywhere inside a clean clone of this repository. It reads the
# version from pyproject.toml, safely switches to and updates main, checks the
# changelog and uv.lock, shows a release preview, and asks before publishing.
# After confirmation it creates (or resumes) the annotated Git tag, waits for
# the GitHub Actions release workflow, and verifies the PyPI package and
# GitHub Release.
#
# Requirements: git, make, Python 3, uv, GitHub CLI (gh, authenticated for
# this repository), jq, and curl. Your GitHub account must be allowed by the
# repository's protected v* tag ruleset.
#
# You do not need to remember or run version numbers, internal actions, tag
# commands, or GitHub/PyPI publishing commands. Do not invoke this script
# directly; use "make release".
#
# If checks fail, fix the reported issue and rerun "make release". If the
# process is interrupted after the tag was pushed, rerunning the same command
# safely resumes the release. No local changes are discarded.
#
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
  local origin_url push_url
  origin_url="$(git remote get-url origin)"
  case "$origin_url" in
    "https://github.com/$REPO"|"https://github.com/$REPO.git"|"git@github.com:$REPO"|"git@github.com:$REPO.git"|"ssh://git@github.com/$REPO"|"ssh://git@github.com/$REPO.git") ;;
    *) die "origin fetch remote '$origin_url' is not the canonical repository $REPO." ;;
  esac
  push_url="$(git remote get-url --push origin)"
  case "$push_url" in
    "https://github.com/$REPO"|"https://github.com/$REPO.git"|"git@github.com:$REPO"|"git@github.com:$REPO.git"|"ssh://git@github.com/$REPO"|"ssh://git@github.com:$REPO.git") ;;
    *) die "origin push remote '$push_url' is not the canonical repository $REPO. Check remote.origin.pushurl." ;;
  esac
}

version_check() {
  [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || die "Expected a SemVer version such as 1.3.0."
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
  local v="$1" tag="v$1" commit
  version_check "$v"; auth; need git; need jq; need curl; need python3
  release_source_check "$v"
  commit="$(git rev-parse HEAD)"

  # Git transport is authoritative for remote tag existence/type. The helper
  # verifies fetch and push URLs, rejects lightweight/mismatched tags, and
  # safely creates or resumes only the exact annotated release tag.
  python3 scripts/release_tags.py "$tag" "$commit" "$REPO"

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
# This file is an implementation detail of "make release", not a general
# repository maintenance command.
if [[ "$#" -ne 0 ]]; then
  die "No arguments are accepted. Run: make release"
fi
release_interactive

