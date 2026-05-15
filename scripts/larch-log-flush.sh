#!/usr/bin/env bash
# larch-log-flush.sh — best-effort tail-call flush for active /implement runs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

if [ -z "${IMPLEMENT_TMPDIR:-}" ]; then
    exit 0
fi

if [ "${LARCH_NO_LOGS_COMMIT:-false}" = "true" ]; then
    exit 0
fi

if [ -e "$IMPLEMENT_TMPDIR/post-merge-sentinel" ]; then
    exit 0
fi

session_id_file="$IMPLEMENT_TMPDIR/session-id"
if [ ! -s "$session_id_file" ]; then
    exit 0
fi

run_id="$(tr -d '\r\n' < "$session_id_file" 2>/dev/null || true)"
if [ -z "$run_id" ]; then
    exit 0
fi

if ! "$SCRIPT_DIR/larch-log.sh" commit \
    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
    --skill implement \
    --run-id "$run_id" \
    >/dev/null 2>&1; then
    printf 'larch-log-flush.sh: warn — larch-log commit failed for run %s (continuing)\n' "$run_id" >&2
fi

exit 0
