#!/usr/bin/env bash
# Add a native GitHub blocked-by relationship between two issues.
#
# Usage: add-blocked-by.sh <ISSUE_A> <ISSUE_B> [--repo owner/name]
#
# ISSUE_A is the issue to be blocked; ISSUE_B is the blocking issue.
# Repo is auto-detected via `gh repo view` when --repo is omitted.
#
# Stdout on success:
#   SUCCESS=true
#   ✓ #<ISSUE_A> is now blocked by #<ISSUE_B>
#
# On failure: ERROR=<message> on stderr, exit 1.

set -euo pipefail

ISSUE_A=""
ISSUE_B=""
REPO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    -*)
      echo "ERROR=Unknown flag: $1" >&2
      exit 1
      ;;
    *)
      if [[ -z "$ISSUE_A" ]]; then
        ISSUE_A="$1"
      elif [[ -z "$ISSUE_B" ]]; then
        ISSUE_B="$1"
      else
        echo "ERROR=Unexpected argument: $1" >&2
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$ISSUE_A" || -z "$ISSUE_B" ]]; then
  echo "ERROR=Usage: add-blocked-by.sh <ISSUE_A> <ISSUE_B> [--repo owner/name]" >&2
  exit 1
fi

if ! [[ "$ISSUE_A" =~ ^[0-9]+$ ]] || ! [[ "$ISSUE_B" =~ ^[0-9]+$ ]]; then
  echo "ERROR=Issue numbers must be positive integers; got: ISSUE_A='$ISSUE_A' ISSUE_B='$ISSUE_B'" >&2
  exit 1
fi

if [[ -z "$REPO" ]]; then
  REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || true
  if [[ -z "$REPO" ]]; then
    echo "ERROR=Could not determine repository — pass --repo owner/name" >&2
    exit 1
  fi
fi

OWNER="${REPO%%/*}"
NAME="${REPO##*/}"

# Resolve node IDs for both issues in one GraphQL call
NODES_OUT=$(gh api graphql -f query="
{
  repository(owner: \"${OWNER}\", name: \"${NAME}\") {
    ia: issue(number: ${ISSUE_A}) { id }
    ib: issue(number: ${ISSUE_B}) { id }
  }
}" 2>&1) || {
  echo "ERROR=GraphQL node-ID lookup failed: $NODES_OUT" >&2
  exit 1
}

NODE_A=$(printf '%s' "$NODES_OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['repository']['ia']['id'])" 2>/dev/null) || true
NODE_B=$(printf '%s' "$NODES_OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['repository']['ib']['id'])" 2>/dev/null) || true

if [[ -z "$NODE_A" ]]; then
  echo "ERROR=Could not resolve node ID for issue #${ISSUE_A} in ${REPO}" >&2
  exit 1
fi
if [[ -z "$NODE_B" ]]; then
  echo "ERROR=Could not resolve node ID for issue #${ISSUE_B} in ${REPO}" >&2
  exit 1
fi

# Read blocked_by count before mutation for verification
BEFORE=$(gh api "repos/${REPO}/issues/${ISSUE_A}" --jq '.issue_dependencies_summary.blocked_by // 0' 2>/dev/null) || BEFORE=0

# Call addBlockedBy mutation
MUTATION_OUT=$(gh api graphql -f query="
mutation {
  addBlockedBy(input: {issueId: \"${NODE_A}\", blockingIssueId: \"${NODE_B}\"}) {
    clientMutationId
  }
}" 2>&1) || {
  echo "ERROR=addBlockedBy mutation failed: $MUTATION_OUT" >&2
  exit 1
}

if printf '%s' "$MUTATION_OUT" | grep -q '"errors"'; then
  echo "ERROR=addBlockedBy mutation returned errors: $MUTATION_OUT" >&2
  exit 1
fi

# Verify: blocked_by count must have increased
AFTER=$(gh api "repos/${REPO}/issues/${ISSUE_A}" --jq '.issue_dependencies_summary.blocked_by // 0' 2>/dev/null) || AFTER=0

if [[ "$AFTER" -le "$BEFORE" ]]; then
  echo "WARNING=blocked_by count did not increase (before=${BEFORE}, after=${AFTER}) — relationship may already exist" >&2
fi

echo "SUCCESS=true"
echo "✓ #${ISSUE_A} is now blocked by #${ISSUE_B}"
