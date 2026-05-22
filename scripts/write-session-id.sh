#!/usr/bin/env bash
# write-session-id.sh — write a per-run session id to --output.
#
# Wraps the inline snippet at /implement Step 0 that picks `uuidgen` when
# available and falls back to the session tmpdir's basename otherwise.
# `/implement` forwards this value as LARCH_TOKEN_SESSION_ID for ledgers and
# hook-side tmpdir resolution (see skills/implement/SKILL.md Step 0).
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

OUTPUT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --output)
            [ $# -ge 2 ] || { emit_kv FAILED true; emit_kv ERROR "--output requires a value"; exit 1; }
            OUTPUT="$2"; shift 2 ;;
        *)
            emit_kv FAILED true
            emit_kv ERROR "unknown flag: $1"
            exit 1 ;;
    esac
done

[ -n "$OUTPUT" ] || { emit_kv FAILED true; emit_kv ERROR "--output is required"; exit 1; }

OUTDIR=$(dirname "$OUTPUT")
mkdir -p "$OUTDIR" 2>/dev/null || { echo "FAILED=true"; echo "ERROR=cannot create dir: $OUTDIR"; exit 1; }

if [ -s "$OUTPUT" ]; then
    exit 0
fi

if command -v uuidgen >/dev/null 2>&1; then
    uuidgen > "$OUTPUT"
else
    # Fallback: use the parent directory's basename. Matches the
    # uuidgen-less host path documented in SKILL.md.
    printf '%s\n' "$(basename "$OUTDIR")" > "$OUTPUT"
fi
