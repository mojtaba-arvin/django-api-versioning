#!/usr/bin/env bash
# Push the current short-lived task branch to origin and verify its remote SHA.
# Usage: .claude/push.sh
# Exit: 0 verified, 2 push failed, 3 SHA mismatch, 4 unsafe branch/checkout

set -euo pipefail

REMOTE="origin"
BRANCH="$(git branch --show-current)"

if [ -z "$BRANCH" ]; then
  echo "FAIL: detached HEAD; checkout a task branch first." >&2
  exit 4
fi

if [ "$BRANCH" = "main" ]; then
  echo "FAIL: direct pushes to main are not allowed; open a pull request." >&2
  exit 4
fi

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "FAIL: remote '$REMOTE' is not configured." >&2
  exit 4
fi

echo "==> Pushing current task branch: $BRANCH"
if ! git push --set-upstream "$REMOTE" "HEAD:refs/heads/$BRANCH"; then
  echo "FAIL: branch push failed; inspect the remote state. Do not force-push." >&2
  exit 2
fi

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git ls-remote --heads "$REMOTE" "refs/heads/$BRANCH" | awk '{print $1}')"

if [ -z "$REMOTE_SHA" ] || [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  echo "PUSH NOT VERIFIED: local=$LOCAL_SHA remote=${REMOTE_SHA:-missing}" >&2
  exit 3
fi

echo "PUSH VERIFIED: $BRANCH $LOCAL_SHA"
