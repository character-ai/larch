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
    --repo)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        echo "ERROR=--repo requires a value (e.g. --repo owner/name)" >&2
        exit 1
      fi
      REPO="$2"; shift 2
      ;;
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

if ! [[ "$ISSUE_A" =~ ^[1-9][0-9]*$ ]] || ! [[ "$ISSUE_B" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR=Issue numbers must be positive integers (≥1); got: ISSUE_A='$ISSUE_A' ISSUE_B='$ISSUE_B'" >&2
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

# Resolve node IDs for both issues via GraphQL variables (safe: no string interpolation)
# shellcheck disable=SC2016
NODES_OUT=$(gh api graphql \
  -F owner="$OWNER" -F name="$NAME" -F ia="$ISSUE_A" -F ib="$ISSUE_B" \
  -f query='query($owner: String!, $name: String!, $ia: Int!, $ib: Int!) {
    repository(owner: $owner, name: $name) {
      ia: issue(number: $ia) { id }
      ib: issue(number: $ib) { id }
    }
  }' 2>&1) || {
  echo "ERROR=GraphQL node-ID lookup failed: $NODES_OUT" >&2
  exit 1
}

if ! printf '%s' "$NODES_OUT" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); errs=d.get('errors') or []; sys.exit(1 if errs else 0)" 2>/dev/null; then
  echo "ERROR=GraphQL node-ID lookup returned errors: $NODES_OUT" >&2
  exit 1
fi

NODE_A=$(printf '%s' "$NODES_OUT" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d['data']['repository']['ia']['id'])" 2>/dev/null) || true
NODE_B=$(printf '%s' "$NODES_OUT" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d['data']['repository']['ib']['id'])" 2>/dev/null) || true

if [[ -z "$NODE_A" ]]; then
  echo "ERROR=Could not resolve node ID for issue #${ISSUE_A} in ${REPO}" >&2
  exit 1
fi
if [[ -z "$NODE_B" ]]; then
  echo "ERROR=Could not resolve node ID for issue #${ISSUE_B} in ${REPO}" >&2
  exit 1
fi

# Read blocked_by count before mutation for verification (best-effort)
BEFORE=$(gh api "repos/${REPO}/issues/${ISSUE_A}" --jq '.issue_dependencies_summary.blocked_by // 0' 2>/dev/null) || BEFORE=0

# Call addBlockedBy mutation via GraphQL variables (safe: no string interpolation)
# shellcheck disable=SC2016
MUTATION_OUT=$(gh api graphql \
  -F issueId="$NODE_A" -F blockingId="$NODE_B" \
  -f query='mutation($issueId: ID!, $blockingId: ID!) {
    addBlockedBy(input: {issueId: $issueId, blockingIssueId: $blockingId}) {
      clientMutationId
    }
  }' 2>&1) || {
  echo "ERROR=addBlockedBy mutation failed: $MUTATION_OUT" >&2
  exit 1
}

if ! printf '%s' "$MUTATION_OUT" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); errs=d.get('errors') or []; sys.exit(1 if errs else 0)" 2>/dev/null; then
  echo "ERROR=addBlockedBy mutation returned errors: $MUTATION_OUT" >&2
  exit 1
fi

# Verify: blocked_by count should have increased (warn-only; already-blocked is acceptable)
AFTER=$(gh api "repos/${REPO}/issues/${ISSUE_A}" --jq '.issue_dependencies_summary.blocked_by // 0' 2>/dev/null) || AFTER=0

if [[ "$AFTER" -le "$BEFORE" ]]; then
  echo "WARNING=blocked_by count did not increase (before=${BEFORE}, after=${AFTER}) — relationship may already exist" >&2
fi

echo "SUCCESS=true"
echo "✓ #${ISSUE_A} is now blocked by #${ISSUE_B}"
