#!/usr/bin/env bash
# Configure GitHub governance for mojtaba-arvin/django-api-versioning.
# Safe to re-run. Requires gh authenticated as a repository administrator.
# This script changes GitHub settings/rulesets; it does not change Git refs.

set -Eeuo pipefail

REPO="mojtaba-arvin/django-api-versioning"
EXPECTED_GATE="PR gate"
MAIN_RULESET_NAME="Protect main"
TAG_RULESET_NAME="Protect release tags"

command -v gh >/dev/null 2>&1 || {
  echo "ERROR: GitHub CLI (gh) is required." >&2
  exit 2
}
gh auth status >/dev/null 2>&1 || {
  echo "ERROR: Authenticate with 'gh auth login' first." >&2
  exit 2
}

ADMIN="$(gh api "repos/$REPO" --jq '.permissions.admin')"
[[ "$ADMIN" == "true" ]] || {
  echo "ERROR: The authenticated account needs repository-admin permissions." >&2
  exit 2
}

echo "==> Configure merge and branch-cleanup settings"
gh api --method PATCH "repos/$REPO" --input - <<'JSON'
{
  "allow_squash_merge": true,
  "allow_merge_commit": false,
  "allow_rebase_merge": false,
  "allow_auto_merge": false,
  "delete_branch_on_merge": true,
  "use_squash_pr_title_as_default": true,
  "squash_merge_commit_title": "PR_TITLE",
  "squash_merge_commit_message": "COMMIT_MESSAGES"
}
JSON

echo "==> Set Actions default token permissions to read-only"
gh api --method PUT "repos/$REPO/actions/permissions/workflow" --input - <<'JSON'
{
  "default_workflow_permissions": "read",
  "can_approve_pull_request_reviews": false
}
JSON

echo "==> Enable Dependabot alerts and security updates"
gh api --method PUT "repos/$REPO/vulnerability-alerts" >/dev/null
gh api --method PUT "repos/$REPO/automated-security-fixes" >/dev/null

echo "==> Enable secret scanning and push protection"
gh api --method PATCH "repos/$REPO" --input - <<'JSON'
{
  "security_and_analysis": {
    "secret_scanning": {"status": "enabled"},
    "secret_scanning_push_protection": {"status": "enabled"}
  }
}
JSON

echo "==> Enable private vulnerability reporting"
gh api --method PUT "repos/$REPO/private-vulnerability-reporting" >/dev/null

MAIN_ID="$(gh api --paginate "repos/$REPO/rulesets" --jq '.[] | select(.name == "Protect main") | .id' | sed -n '1p')"
[[ -n "$MAIN_ID" ]] || {
  echo "ERROR: Existing '$MAIN_RULESET_NAME' ruleset was not found; refusing to create a duplicate." >&2
  exit 3
}

echo "==> Require the always-running PR gate on main"
gh api --method PUT "repos/$REPO/rulesets/$MAIN_ID" --input - <<JSON
{
  "name": "$MAIN_RULESET_NAME",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "required_linear_history"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "required_reviewers": [],
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true,
        "require_extra_approval_for_unattributed_changes": false,
        "allowed_merge_methods": ["squash"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "required_status_checks": [
          {"context": "$EXPECTED_GATE"}
        ],
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": false
      }
    }
  ],
  "bypass_actors": []
}
JSON

TAG_ID="$(gh api --paginate "repos/$REPO/rulesets" --jq '.[] | select(.name == "Protect release tags") | .id' | sed -n '1p')"
TAG_BODY="$(mktemp)"
trap 'rm -f "$TAG_BODY"' EXIT
cat > "$TAG_BODY" <<'JSON'
{
  "name": "Protect release tags",
  "target": "tag",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/tags/v*"],
      "exclude": []
    }
  },
  "rules": [
    {"type": "creation"},
    {"type": "update"},
    {"type": "deletion"}
  ],
  "bypass_actors": [
    {
      "actor_id": 5,
      "actor_type": "RepositoryRole",
      "bypass_mode": "always"
    }
  ]
}
JSON

echo "==> Protect v* release tags (repository administrators only)"
if [[ -n "$TAG_ID" ]]; then
  gh api --method PUT "repos/$REPO/rulesets/$TAG_ID" --input "$TAG_BODY" >/dev/null
else
  gh api --method POST "repos/$REPO/rulesets" --input "$TAG_BODY" >/dev/null
fi

echo "==> Verify final settings"
gh api "repos/$REPO" --jq '{
  default_branch,
  allow_squash_merge,
  allow_merge_commit,
  allow_rebase_merge,
  delete_branch_on_merge,
  use_squash_pr_title_as_default
}'
gh api "repos/$REPO/actions/permissions/workflow"
gh api --paginate "repos/$REPO/rulesets" --jq '.[] | {id, name, target, enforcement}'
echo "Repository governance settings have been applied."
