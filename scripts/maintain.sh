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
}
version_check() {
  [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || die "Expected a SemVer version such as 1.3.0."
}
preflight() {
  local v="$1" tag="v$1" actual
  version_check "$v"; auth; need git; need python3
  [[ "$(git branch --show-current)" == main ]] || die "Switch to main first."
  [[ -z "$(git status --porcelain)" ]] || die "Working tree must be clean."
  git fetch origin --prune
  [[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || die "Local main must exactly match origin/main."
  actual="$(python3 -c 'import tomllib; from pathlib import Path; print(tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"])')"
  [[ "$actual" == "$v" ]] || die "pyproject.toml version is $actual, not $v."
  grep -Eq "^## \[$v\] - " CHANGELOG.md || die "Missing dated CHANGELOG.md section for [$v]."
  ! git show-ref --verify --quiet "refs/tags/$tag" || die "Local tag $tag already exists."
  ! git ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null 2>&1 || die "Remote tag $tag already exists."
  echo "PASS: clean main, package version, changelog entry, and unused tag."
}
release() {
  local action="$1" v="$2" tag="v$2"
  case "$action" in
    preflight) preflight "$v" ;;
    tag)
      preflight "$v"
      git tag -a "$tag" -m "Release $tag"
      git push origin "refs/tags/$tag"
      echo "Pushed $tag. GitHub Actions will publish to PyPI and create the GitHub Release."
      ;;
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
  release) [[ "$#" -eq 3 ]] || die "Usage: scripts/maintain.sh release {preflight|tag|status} VERSION"; release "$2" "$3" ;;
  branches) [[ "$#" -le 2 ]] || die "Usage: scripts/maintain.sh branches [--apply]"; if [[ "${2:-}" == --apply ]]; then branches --apply; else branches; fi ;;
  -h|--help|help) echo "Usage: scripts/maintain.sh release {preflight|tag|status} VERSION | branches [--apply]" ;;
  *) die "Unknown command. Use --help." ;;
esac
