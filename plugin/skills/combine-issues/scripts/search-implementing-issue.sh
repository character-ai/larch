#!/usr/bin/env bash
# Search open issues for in-flight implementing work that would create a missing file.
#
# Usage: search-implementing-issue.sh --file-path <repo-relative-path> [--repo owner/name]
#
# The repo-relative path is sanitized to [A-Za-z0-9/._-] before use. The sanitized
# path is passed to `gh issue list --search` as a single argv element (never as
# interpolated shell command text).
#
# Output on stdout:
#   STATUS=none              — no qualifying implementing issue
#   STATUS=ambiguous         — multiple or non-exact matches; treat as not blocked
#   STATUS=invalid_path      — path empty after sanitization
#   STATUS=blocked           — exactly one match
#   IMPLEMENTING_ISSUE=<n>   — present when STATUS=blocked (positive integer)
#   IMPLEMENTING_TITLE=<t>   — present when STATUS=blocked
#
# On failure: ERROR=<message> on stderr, exit 1.

set -euo pipefail

FILE_PATH=""
REPO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file-path) FILE_PATH="$2"; shift 2 ;;
    --repo)      REPO="$2";      shift 2 ;;
    *)
      echo "ERROR=Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$FILE_PATH" ]]; then
  echo "ERROR=Missing --file-path" >&2
  exit 1
fi

SANITIZED_PATH=$(printf '%s' "$FILE_PATH" | tr -cd 'A-Za-z0-9/._-')
if [[ -z "$SANITIZED_PATH" ]]; then
  echo "STATUS=invalid_path"
  exit 0
fi

if [[ -z "$REPO" ]]; then
  REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || true
  if [[ -z "$REPO" ]]; then
    echo "ERROR=Could not determine repository — pass --repo owner/name" >&2
    exit 1
  fi
fi

RAW=$(gh issue list --repo "$REPO" --state open --limit 100 \
  --json number,title,body --search "$SANITIZED_PATH" 2>/dev/null) || {
  echo "ERROR=gh issue list failed for repo $REPO" >&2
  exit 1
}

if [[ -z "$RAW" || "$RAW" == "[]" ]]; then
  echo "STATUS=none"
  exit 0
fi

MATCHES=$(printf '%s' "$RAW" | jq --arg path "$SANITIZED_PATH" -c '
  [.[] |
    select(.title | test("^\\[(DESIGNING|IMPLEMENTING)\\] ")) |
    select(
      ((.body // "") | contains($path)) or
      ((.title // "") | contains($path))
    )
  ]
')

COUNT=$(printf '%s' "$MATCHES" | jq 'length')

if [[ "$COUNT" -eq 0 ]]; then
  echo "STATUS=none"
  exit 0
fi

if [[ "$COUNT" -gt 1 ]]; then
  echo "STATUS=ambiguous"
  exit 0
fi

IMPLEMENTING_ISSUE=$(printf '%s' "$MATCHES" | jq -r '.[0].number')
IMPLEMENTING_TITLE=$(printf '%s' "$MATCHES" | jq -r '.[0].title' | tr '\n\r' ' ')

if ! [[ "$IMPLEMENTING_ISSUE" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR=Unexpected implementing issue number: $IMPLEMENTING_ISSUE" >&2
  exit 1
fi

echo "STATUS=blocked"
echo "IMPLEMENTING_ISSUE=$IMPLEMENTING_ISSUE"
echo "IMPLEMENTING_TITLE=$IMPLEMENTING_TITLE"
