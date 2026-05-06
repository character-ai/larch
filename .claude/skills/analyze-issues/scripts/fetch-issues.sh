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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --output)
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

if ! gh issue list --repo "$REPO" --state all --limit "$LIMIT" \
  --json number,title,state,createdAt,closedAt,body,labels,closedByPullRequestsReferences \
  > "$OUTPUT"; then
  echo "ERROR=gh issue list failed for repo $REPO" >&2
  exit 1
fi
