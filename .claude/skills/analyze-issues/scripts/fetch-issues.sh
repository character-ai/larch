#!/usr/bin/env bash
set -euo pipefail

REPO=""
LIMIT=""
OUTPUT=""

usage() {
  cat >&2 <<'EOF'
Usage: fetch-issues.sh --repo OWNER/REPO --limit N --output PATH
EOF
}

require_value() {
  if [[ $# -lt 2 ]]; then
    echo "ERROR=Flag $1 requires a value" >&2
    usage
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      require_value "$@"
      REPO="$2"
      shift 2
      ;;
    --limit)
      require_value "$@"
      LIMIT="$2"
      shift 2
      ;;
    --output)
      require_value "$@"
      OUTPUT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR=Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$REPO" || -z "$LIMIT" || -z "$OUTPUT" ]]; then
  echo "ERROR=Missing required --repo, --limit, or --output" >&2
  usage
  exit 2
fi

# Atomic write: stage to a temp file with restrictive permissions, then rename
# on success so a partial gh failure never leaves a torn JSON dump in place.
umask 077
TMP_OUTPUT="${OUTPUT}.tmp.$$"
trap 'rm -f -- "$TMP_OUTPUT"' EXIT

if ! gh issue list --repo "$REPO" --state all --limit "$LIMIT" \
  --json number,title,state,createdAt,closedAt,body,labels,closedByPullRequestsReferences \
  > "$TMP_OUTPUT"; then
  echo "ERROR=gh issue list failed for repo $REPO" >&2
  exit 1
fi

mv -f -- "$TMP_OUTPUT" "$OUTPUT"
trap - EXIT
