#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LIMIT=2000
SPAN_DAYS=0
TOP_K=10
CATEGORIES="default"

usage() {
  cat >&2 <<'EOF'
Usage: run-analysis.sh [--limit N] [--span-days N] [--top-K N] [--categories=auto|default]
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
    --limit)
      require_value "$@"
      LIMIT="$2"
      shift 2
      ;;
    --span-days)
      require_value "$@"
      SPAN_DAYS="$2"
      shift 2
      ;;
    --top-K|--top-k)
      require_value "$@"
      TOP_K="$2"
      shift 2
      ;;
    --categories=*)
      CATEGORIES="${1#--categories=}"
      shift
      ;;
    --categories)
      require_value "$@"
      CATEGORIES="$2"
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

case "$CATEGORIES" in
  auto|default) ;;
  *)
    echo "ERROR=--categories must be auto or default" >&2
    exit 2
    ;;
esac

if REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)"; then
  :
else
  REMOTE_URL="$(git config --get remote.origin.url || true)"
  REPO="$(printf '%s\n' "$REMOTE_URL" |
    sed -E 's#^git@[^:]+:##; s#^https?://[^/]+/##; s#\.git$##')"
fi

if [[ ! "$REPO" =~ ^[^/]+/[^/]+$ ]]; then
  echo "ERROR=Unable to detect GitHub repo owner/name" >&2
  exit 1
fi

SANITIZED_REPO="$(printf '%s' "$REPO" | tr '/' '-' | tr -cd '[:alnum:]-_')"
if [[ -z "$SANITIZED_REPO" ]]; then
  echo "ERROR=Sanitized repo name is empty (REPO='$REPO')" >&2
  exit 1
fi

# Issue bodies can contain sensitive content — keep dumps user-private.
TMPROOT="${TMPDIR:-/tmp}"
DUMP_DIR="${TMPROOT%/}"
DUMP_PATH="${DUMP_DIR}/${SANITIZED_REPO}-issues.json"
umask 077

"$SCRIPT_DIR/fetch-issues.sh" --repo "$REPO" --limit "$LIMIT" --output "$DUMP_PATH"

ANALYZE_ARGS=(--json "$DUMP_PATH" --top-k "$TOP_K" --categories "$CATEGORIES")
if [[ "$SPAN_DAYS" != "0" ]]; then
  ANALYZE_ARGS+=(--span-days "$SPAN_DAYS")
fi

python3 "$SCRIPT_DIR/analyze.py" "${ANALYZE_ARGS[@]}"
