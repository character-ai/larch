#!/usr/bin/env bash
# step-architectural-guidelines-write-staged.sh — thin wrapper for staged guideline assessment writes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
ASSESSMENT_FILE="${1:?assessment file path required}"
MATERIALIZE_ENV="$IMPLEMENT_TMPDIR/architectural-guideline-materialize.env"
DIFF_FILE="$IMPLEMENT_TMPDIR/architectural-guideline-materialized-diff.txt"

BASE_REF=""
DIFF_FINGERPRINT=""
if [ -f "$MATERIALIZE_ENV" ]; then
  # shellcheck source=/dev/null
  . "$MATERIALIZE_ENV"
fi

exec python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines write-staged-assessment \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --assessment-file "$ASSESSMENT_FILE" \
  --assessed-head-sha "$(git rev-parse HEAD)" \
  --diff-fingerprint "${DIFF_FINGERPRINT:-}" \
  --base-ref "${BASE_REF:-}" \
  --diff-file "$DIFF_FILE"
