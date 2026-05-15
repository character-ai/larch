#!/usr/bin/env bash
# snapshot-untracked.sh — Capture a sorted list of untracked files for pre-review baseline.
#
# Usage:
#   snapshot-untracked.sh --output <file> [--nul]
#
# On success, writes a sorted list of untracked paths to <file> via atomic rename.
# On any OPERATION failure (git, sort, mv), removes both the temp file and <file>
# so the downstream consumer (check-review-changes.sh) sees
# UNTRACKED_BASELINE=missing and degrades gracefully (issue #651).
#
# On argument-parsing failure (unknown flag, missing --output), logs to stderr
# and exits 0 WITHOUT touching <file> — argument errors must not delete
# user-controlled paths (issue #1486).
#
# Always exits 0 — callers must never abort on snapshot failure.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

OUTPUT=""
NUL_MODE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            if [[ $# -lt 2 || -z "${2:-}" ]]; then
                larch_err "snapshot-untracked.sh: --output requires a value"
                exit 0
            fi
            OUTPUT="$2"
            shift 2
            ;;
        --nul) NUL_MODE=true; shift ;;
        *) larch_err "snapshot-untracked.sh: unknown flag: $1"; exit 0 ;;
    esac
done

if [[ -z "$OUTPUT" ]]; then
    larch_err "snapshot-untracked.sh: --output is required"
    exit 0
fi

TMP="${OUTPUT}.tmp"

if [[ "$NUL_MODE" == "true" ]]; then
    if git ls-files --others --exclude-standard -z 2>/dev/null \
        | LC_ALL=C sort -z > "$TMP" \
        && mv -f "$TMP" "$OUTPUT"; then
        exit 0
    fi
elif git ls-files --others --exclude-standard 2>/dev/null \
    | LC_ALL=C sort > "$TMP" \
    && mv -f "$TMP" "$OUTPUT"; then
    exit 0
fi

rm -f "$OUTPUT" "$TMP"
exit 0
