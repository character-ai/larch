#!/usr/bin/env bash
# step-architectural-guidelines-write-compose.sh — thin wrapper for compose-time guideline assessment writes.

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

exec python3 "$PLUGIN_ROOT/python/cli.py" architectural-guidelines write-compose-assessment \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --assessment-file "$ASSESSMENT_FILE"
