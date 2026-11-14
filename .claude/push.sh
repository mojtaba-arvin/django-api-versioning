#!/usr/bin/env bash
# .claude/push.sh — deterministic push for the configured repository branch.
# Usage: .claude/push.sh          push branch
#        .claude/push.sh --tag    push branch + latest tag
# Exit:  0 verified, 1 env, 2 push failed, 3 SHA mismatch

set -euo pipefail

BRANCH="audit/comprehensive-package-review"
REMOTE="origin"

if [ -z "${DAV_GITHUB_TOKEN:-}" ]; then
  echo "FAIL: DAV_GITHUB_TOKEN not set/exported" >&2
  exit 1
fi

CRED=$(mktemp /tmp/git-cred-XXXXXX)
cat > "$CRED" <<'HELPER'
#!/bin/sh
echo "username=x-access-token"
echo "password=$DAV_GITHUB_TOKEN"
HELPER
chmod +x "$CRED"
trap "rm -f '$CRED'" EXIT

echo "==> Pushing $BRANCH"
if ! git -c credential.helper="$CRED" push "$REMOTE" "$BRANCH"; then
  echo "FAIL: branch push failed" >&2
  exit 2
fi

if [ "${1:-}" = "--tag" ]; then
  TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)
  if [ -z "$TAG" ]; then
    echo "WARN: --tag requested but no tag exists" >&2
  else
    echo "==> Pushing tag $TAG"
    if ! git -c credential.helper="$CRED" push "$REMOTE" "$TAG"; then
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
