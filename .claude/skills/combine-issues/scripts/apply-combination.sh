#!/usr/bin/env bash
# Create a combined issue and close the source issues.
#
# Network retry carve-out: `gh issue create` is intentionally not wrapped in
# `with_transient_retry` — create is not idempotent under server-side success
# with a lost response.
#
# Required flags:
#   --title <title>         Title for the combined issue.
#   --body-file <path>      Path to a file containing the combined issue body.
#   --source-issues <list>  Comma-separated issue numbers to close (e.g. "12,34,56").
#
# Optional flags:
#   --repo <owner/name>     Repository. Auto-detected if omitted.
#   --dry-run               Print what would happen without making changes.
#
# Output on stdout:
#   COMBINED_ISSUE=<number>
#   CLOSED_ISSUES=<count>
#   DRY_RUN=true|false
# On failure: ERROR=<message> on stderr, exit 1.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../../../" && pwd)"
REDACT="$PLUGIN_ROOT/scripts/redact-secrets.sh"
# shellcheck source=scripts/lib-net.sh
source "$PLUGIN_ROOT/scripts/lib-net.sh"

TITLE=""
BODY_FILE=""
SOURCE_ISSUES=""
REPO=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title)         TITLE="$2";         shift 2 ;;
    --body-file)     BODY_FILE="$2";     shift 2 ;;
    --source-issues) SOURCE_ISSUES="$2"; shift 2 ;;
    --repo)          REPO="$2";          shift 2 ;;
    --dry-run)       DRY_RUN=true;       shift ;;
    *)
      echo "ERROR=Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$TITLE" ]]; then
  echo "ERROR=Missing --title" >&2
  exit 1
fi
if [[ -z "$BODY_FILE" || ! -r "$BODY_FILE" ]]; then
  echo "ERROR=Missing or unreadable --body-file: $BODY_FILE" >&2
  exit 1
fi
if [[ -z "$SOURCE_ISSUES" ]]; then
  echo "ERROR=Missing --source-issues" >&2
  exit 1
fi

if [[ -z "$REPO" ]]; then
  REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || true
  if [[ -z "$REPO" ]]; then
    echo "ERROR=Could not determine repository" >&2
    exit 1
  fi
fi

redact_gh_error() {
  local err_text="$1" redacted status=0
  if [[ ! -x "$REDACT" ]]; then
    printf '%s' 'gh failure: redaction unavailable'
    return 0
  fi
  redacted=$(printf '%s' "$err_text" | "$REDACT") || status=$?
  if [[ "$status" -ne 0 ]]; then
    printf '%s' 'gh failure: redaction unavailable'
    return 0
  fi
  case "$redacted" in
    *'[content truncated'*)
      printf '%s' 'gh failure: redaction unavailable'
      return 0
      ;;
  esac
  printf '%s' "$redacted" | tr '\n' ' ' | head -c 500
}

IFS=',' read -ra ISSUES <<< "$SOURCE_ISSUES"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "DRY_RUN=true"
  echo "WOULD_CREATE=$TITLE"
  echo "WOULD_CLOSE=${#ISSUES[@]} issues: ${SOURCE_ISSUES}"
  exit 0
fi

REDACTED_TITLE="$TITLE"
REDACTED_BODY_FILE="$BODY_FILE"
if [[ -x "$REDACT" ]]; then
  REDACTED_TITLE=$("$REDACT" <<< "$TITLE")
  REDACTED_BODY_FILE=$(mktemp /tmp/combine-redacted-XXXXXX)
  "$REDACT" < "$BODY_FILE" > "$REDACTED_BODY_FILE"
fi

CREATE_OUT=$(gh issue create --repo "$REPO" \
  --title "$REDACTED_TITLE" \
  --body-file "$REDACTED_BODY_FILE" 2>&1) || {
  echo "ERROR=Failed to create combined issue: $CREATE_OUT" >&2
  exit 1
}

COMBINED_NUMBER=$(echo "$CREATE_OUT" | grep -oE '/issues/[0-9]+' | grep -oE '[0-9]+' | tail -1) || true
if [[ -z "$COMBINED_NUMBER" ]]; then
  echo "ERROR=Could not parse issue number from gh output: $CREATE_OUT" >&2
  exit 1
fi

CLOSED=0
CLOSE_ERRORS=""
for issue_num in "${ISSUES[@]}"; do
  issue_num=$(echo "$issue_num" | tr -d ' ')
  close_fail_file=$(mktemp "${TMPDIR:-/tmp}/apply-combination-close.XXXXXX")
  if with_transient_retry transient_envelope_predicate_none "$close_fail_file" \
    gh issue close "$issue_num" --repo "$REPO" \
    --comment "Combined into #${COMBINED_NUMBER}"; then
    CLOSED=$((CLOSED + 1))
    rm -f "$close_fail_file"
  else
    CLOSE_ERR=$(cat "$close_fail_file" 2>/dev/null || true)
    rm -f "$close_fail_file"
    CLOSE_ERRORS="${CLOSE_ERRORS}Failed to close #${issue_num}: $(redact_gh_error "$CLOSE_ERR"); "
  fi
done

if [[ -n "$CLOSE_ERRORS" ]]; then
  echo "WARNING=${CLOSE_ERRORS}" >&2
fi

echo "DRY_RUN=false"
echo "COMBINED_ISSUE=$COMBINED_NUMBER"
echo "CLOSED_ISSUES=$CLOSED"
