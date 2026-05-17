#!/usr/bin/env bash
# check-reviewers.sh — Check external reviewer binary presence.
#
# The skip flags preserve the historic CLI surface, but now mean "skip the
# binary presence check and report the tool as not present".

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh" || { echo "check-reviewers.sh: failed to source lib-quiet.sh" >&2; exit 1; }
larch_quiet_init

SKIP_CODEX_PROBE=false
SKIP_CURSOR_PROBE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-codex-probe)   SKIP_CODEX_PROBE=true; shift ;;
        --skip-cursor-probe)  SKIP_CURSOR_PROBE=true; shift ;;
        *) larch_err "check-reviewers.sh: unknown argument: $1"; exit 1 ;;
    esac
done

CODEX_PRESENT=false
CURSOR_PRESENT=false

if [[ "$SKIP_CODEX_PROBE" != "true" ]] && command -v codex >/dev/null 2>&1; then
    CODEX_PRESENT=true
fi
if [[ "$SKIP_CURSOR_PROBE" != "true" ]] && command -v cursor >/dev/null 2>&1; then
    CURSOR_PRESENT=true
fi

emit_kv CODEX_PRESENT "$CODEX_PRESENT"
emit_kv CURSOR_PRESENT "$CURSOR_PRESENT"
emit_kv CODEX_AVAILABLE "$CODEX_PRESENT"
emit_kv CURSOR_AVAILABLE "$CURSOR_PRESENT"
