#!/usr/bin/env bash
# flush-vendor-failure-diagnostics.sh — merge per-slot vendor failure-diagnostic
# parts into the canonical batch file and (when a log root + run id are given)
# write the `vendor-failure-diagnostics` larch-log batch. #3713.
#
# Producers append redacted per-slot part files under
# `$tmpdir/vendor-failure-diagnostics.parts/` via
# `append_vendor_failure_diagnostics` (`python/agents.py`).
# This helper derives the canonical `$tmpdir/vendor-failure-diagnostics.txt` by
# overwriting it from the full parts set on every checkpoint, so repeated local
# checkpoints and the Step 18 terminal snapshot converge idempotently.
#
# Clear-after-success: when no parts exist, no batch is written — a successful
# run with no vendor-agent failures commits nothing (preserves #3534 intent).
#
# This helper never makes a Git commit or publishes an archive. `run-log write`
# only stages the batch under the mutable log root. Step 18 owns terminal
# publication.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

usage() {
    echo "Usage: flush-vendor-failure-diagnostics.sh --tmpdir DIR [--run-id ID --log-root DIR] [--skill NAME]" >&2
}

TMPDIR_ARG=""
RUN_ID=""
LOG_ROOT=""
SKILL="implement"
while [ $# -gt 0 ]; do
    case "$1" in
        --tmpdir) TMPDIR_ARG="${2:-}"; shift 2 ;;
        --run-id) RUN_ID="${2:-}"; shift 2 ;;
        --log-root) LOG_ROOT="${2:-}"; shift 2 ;;
        --skill) SKILL="${2:-}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

if [ -z "$TMPDIR_ARG" ] || [ ! -d "$TMPDIR_ARG" ]; then
    printf 'FLUSH_STATUS=skipped REASON=no-tmpdir\n'
    exit 0
fi

parts_dir="$TMPDIR_ARG/vendor-failure-diagnostics.parts"
batch_file="$TMPDIR_ARG/vendor-failure-diagnostics.txt"

# Clear-after-success: no parts directory or no part files → nothing to flush.
part_count=0
if [ -d "$parts_dir" ]; then
    part_count=$(find "$parts_dir" -type f -name 'part.*' 2>/dev/null | wc -l | tr -d ' ')
fi
case "$part_count" in ''|*[!0-9]*) part_count=0 ;; esac
if [ "$part_count" = "0" ]; then
    printf 'FLUSH_STATUS=empty PARTS=0\n'
    exit 0
fi

# Derive the canonical batch file from the full parts set (sorted for
# determinism). Overwrite — idempotent across repeated flushes.
: > "$batch_file"
find "$parts_dir" -type f -name 'part.*' 2>/dev/null | LC_ALL=C sort | while IFS= read -r p; do
    [ -s "$p" ] || continue
    cat "$p" >> "$batch_file"
done

if [ ! -s "$batch_file" ]; then
    printf 'FLUSH_STATUS=empty PARTS=%s\n' "$part_count"
    exit 0
fi

WROTE_BATCH=false
if [ -n "$LOG_ROOT" ] && [ -n "$RUN_ID" ]; then
    if python3 "$SCRIPT_DIR/../python/cli.py" run-log write \
        --log-root "$LOG_ROOT" \
        --skill "$SKILL" \
        --run-id "$RUN_ID" \
        --batch vendor-failure-diagnostics \
        --input-file "$batch_file" >/dev/null 2>&1; then
        WROTE_BATCH=true
    fi
fi

printf 'FLUSH_STATUS=flushed PARTS=%s BATCH_WRITTEN=%s\n' "$part_count" "$WROTE_BATCH"
exit 0
