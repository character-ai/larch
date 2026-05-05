#!/usr/bin/env bash
# write-session-id.sh — write a per-run session id to --output.
#
# Wraps the inline snippet at /implement Step 0 that picks `uuidgen` when
# available and falls back to the session tmpdir's basename otherwise.
# `/design`'s manifest-freshness check (read-design-manifest.sh) compares
# this value to its stored SESSION_ID before reusing an exported plan.
#
# Usage:
#   write-session-id.sh --output PATH
#
# Output:
#   On success: writes one line containing the session id to PATH.
#   On failure: prints FAILED=true / ERROR=… to stdout and exits non-zero.
#
# Exit codes:
#   0 — success
#   1 — usage error or write failure

set -euo pipefail

OUTPUT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --output)
            [ $# -ge 2 ] || { echo "FAILED=true"; echo "ERROR=--output requires a value"; exit 1; }
            OUTPUT="$2"; shift 2 ;;
        *)
            echo "FAILED=true"
            echo "ERROR=unknown flag: $1"
            exit 1 ;;
    esac
done

[ -n "$OUTPUT" ] || { echo "FAILED=true"; echo "ERROR=--output is required"; exit 1; }

OUTDIR=$(dirname "$OUTPUT")
mkdir -p "$OUTDIR" 2>/dev/null || { echo "FAILED=true"; echo "ERROR=cannot create dir: $OUTDIR"; exit 1; }

if command -v uuidgen >/dev/null 2>&1; then
    uuidgen > "$OUTPUT"
else
    # Fallback: use the parent directory's basename. Matches the
    # uuidgen-less host path documented in SKILL.md.
    printf '%s\n' "$(basename "$OUTDIR")" > "$OUTPUT"
fi
