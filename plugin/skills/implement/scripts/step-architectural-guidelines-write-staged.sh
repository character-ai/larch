#!/usr/bin/env bash
# step-architectural-guidelines-write-staged.sh — thin wrapper for staged guideline assessment writes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
ASSESSMENT_ARG="${1:?assessment file path required}"
OUTCOME="${2:-}"
if [[ "$ASSESSMENT_ARG" == /* ]]; then
  if [[ "$ASSESSMENT_ARG" == "$IMPLEMENT_TMPDIR"/* ]]; then
    ASSESSMENT_FILE="$ASSESSMENT_ARG"
  else
    ASSESSMENT_FILE="$IMPLEMENT_TMPDIR/${ASSESSMENT_ARG#/}"
  fi
else
  ASSESSMENT_FILE="$IMPLEMENT_TMPDIR/$ASSESSMENT_ARG"
fi
MATERIALIZE_ENV="$IMPLEMENT_TMPDIR/architectural-guideline-materialize.env"
DIFF_FILE="$IMPLEMENT_TMPDIR/architectural-guideline-materialized-diff.txt"

read_materialize_key() {
  local key=$1
  CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" "$PLUGIN_ROOT/scripts/larch.sh" kv get --file "$MATERIALIZE_ENV" --key "$key" --match last 2>/dev/null || true
}

BASE_REF=""
DIFF_FINGERPRINT=""
ASSESSED_HEAD_SHA=""
if [ -f "$MATERIALIZE_ENV" ]; then
  BASE_REF="$(read_materialize_key BASE_REF)"
  DIFF_FINGERPRINT="$(read_materialize_key DIFF_FINGERPRINT)"
  ASSESSED_HEAD_SHA="$(read_materialize_key HEAD_SHA)"
fi

if [ -n "$DIFF_FINGERPRINT" ] && ! [[ "$DIFF_FINGERPRINT" =~ ^[0-9a-fA-F]{64}$ ]]; then
  DIFF_FINGERPRINT=""
fi
if [ -n "$BASE_REF" ] && ! [[ "$BASE_REF" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  BASE_REF=""
fi
if [ -n "$ASSESSED_HEAD_SHA" ] && ! [[ "$ASSESSED_HEAD_SHA" =~ ^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$ ]]; then
  ASSESSED_HEAD_SHA=""
fi

DIFF_ARGS=()
if [ -f "$DIFF_FILE" ]; then
  DIFF_ARGS=(--diff-file "$DIFF_FILE")
fi

exec env CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" "$PLUGIN_ROOT/scripts/larch.sh" architectural-guidelines write-staged-assessment \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --assessment-file "$ASSESSMENT_FILE" \
  --outcome "$OUTCOME" \
  --assessed-head-sha "${ASSESSED_HEAD_SHA:-}" \
  --diff-fingerprint "${DIFF_FINGERPRINT:-}" \
  --base-ref "${BASE_REF:-}" \
  "${DIFF_ARGS[@]}"
