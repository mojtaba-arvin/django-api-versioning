#!/usr/bin/env bash
# .claude/push.sh — deterministic push for the configured repository branch.
# Usage: .claude/push.sh          push branch
#        .claude/push.sh --tag    push branch + latest tag
# Exit:  0 verified, 2 push failed, 3 SHA mismatch

set -euo pipefail

BRANCH="audit/comprehensive-package-review"
REMOTE="origin"

echo "==> Pushing $BRANCH"
if ! git push "$REMOTE" "$BRANCH"; then
  echo "FAIL: branch push failed" >&2
  exit 2
fi

if [ "${1:-}" = "--tag" ]; then
  TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)
  if [ -z "$TAG" ]; then
    echo "WARN: --tag requested but no tag exists" >&2
  else
    echo "==> Pushing tag $TAG"
    if ! git push "$REMOTE" "$TAG"; then
      echo "FAIL: tag push failed" >&2
      exit 2
    fi
  fi
fi

LOCAL=$(git rev-parse HEAD)
REMOTE_SHA=$(git ls-remote --heads "$REMOTE" "$BRANCH" | awk '{print $1}')
if [ "$LOCAL" != "$REMOTE_SHA" ]; then
  echo "PUSH NOT VERIFIED: local=$LOCAL remote=$REMOTE_SHA" >&2
  exit 3
fi
echo "PUSH VERIFIED: $LOCAL"
exit 0
