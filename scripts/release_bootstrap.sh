#!/usr/bin/env bash
set -Eeuo pipefail

REPO="mojtaba-arvin/django-api-versioning"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "ERROR: Run this command from a repository clone." >&2
  exit 2
}
cd "$ROOT"

die() {
  echo "ERROR: $*" >&2
  exit 2
}

reexec_after_sync="yes"
if [[ "$#" -eq 1 && "$1" == "--after-sync" ]]; then
  reexec_after_sync="no"
elif [[ "$#" -ne 0 ]]; then
  die "No arguments are accepted. Run: make release"
fi

[[ -z "$(git status --porcelain)" ]] || die \
  "Working tree must be clean before synchronizing main. Commit or safely stash your changes first."

current_branch="$(git branch --show-current)"
if [[ "$current_branch" != main ]]; then
  echo "Switching from $current_branch to main (working tree is clean)..."
  git switch main
fi

origin_url="$(git remote get-url origin)" || die "Remote 'origin' is not configured."
push_url="$(git remote get-url --push origin)" || die "Could not resolve origin push URL."

case "$origin_url" in
  "https://github.com/$REPO"|"https://github.com/$REPO.git"|"git@github.com:$REPO"|"git@github.com:$REPO.git"|"ssh://git@github.com/$REPO"|"ssh://git@github.com/$REPO.git") ;;
  *) die "origin fetch remote '$origin_url' is not the canonical repository $REPO." ;;
esac
case "$push_url" in
  "https://github.com/$REPO"|"https://github.com/$REPO.git"|"git@github.com:$REPO"|"git@github.com:$REPO.git"|"ssh://git@github.com/$REPO"|"ssh://git@github.com/$REPO.git") ;;
  *) die "origin push remote '$push_url' is not the canonical repository $REPO. Check remote.origin.pushurl." ;;
esac

echo "Fetching origin/main..."
git fetch origin --prune

# Use an explicit remote-tracking ref rather than git pull. This avoids
# branch.main.merge ambiguity when local Git config contains multiple merge refs.
echo "Fast-forwarding local main..."
git merge --ff-only refs/remotes/origin/main

# Re-execute the bootstrap after synchronization so even this launcher is
# reloaded from the newly fetched checkout. The second pass then loads the
# current maintain.sh, avoiding stale in-memory release code.
if [[ "$reexec_after_sync" == yes ]]; then
  exec bash scripts/release_bootstrap.sh --after-sync
fi
exec bash scripts/maintain.sh
