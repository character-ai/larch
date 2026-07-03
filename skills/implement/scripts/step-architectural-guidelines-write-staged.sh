#!/usr/bin/env bash
# step-architectural-guidelines-write-staged.sh — thin wrapper for staged guideline assessment writes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
ASSESSMENT_ARG="${1:?assessment file path required}"
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
  local key=$1 line
  line=$(grep "^${key}=" "$MATERIALIZE_ENV" 2>/dev/null | tail -n 1 || true)
  if [ -n "$line" ]; then
    printf '%s\n' "${line#*=}"
  fi
}

BASE_REF=""
DIFF_FINGERPRINT=""
if [ -f "$MATERIALIZE_ENV" ]; then
  BASE_REF="$(read_materialize_key BASE_REF)"
  DIFF_FINGERPRINT="$(read_materialize_key DIFF_FINGERPRINT)"
fi

if [ -n "$DIFF_FINGERPRINT" ] && ! [[ "$DIFF_FINGERPRINT" =~ ^[0-9a-fA-F]{64}$ ]]; then
  DIFF_FINGERPRINT=""
fi
if [ -n "$BASE_REF" ] && ! [[ "$BASE_REF" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  BASE_REF=""
fi

DIFF_ARGS=()
if [ -f "$DIFF_FILE" ]; then
  DIFF_ARGS=(--diff-file "$DIFF_FILE")
fi

exec python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines write-staged-assessment \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --assessment-file "$ASSESSMENT_FILE" \
  --assessed-head-sha "$(git rev-parse HEAD)" \
  --diff-fingerprint "${DIFF_FINGERPRINT:-}" \
  --base-ref "${BASE_REF:-}" \
  "${DIFF_ARGS[@]}"
