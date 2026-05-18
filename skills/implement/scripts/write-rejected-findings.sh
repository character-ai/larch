#!/usr/bin/env bash
# write-rejected-findings.sh — summarize rejected code-review findings.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: write-rejected-findings.sh --implement-tmpdir PATH [--run-id ID --log-root PATH]"
}

fail_usage() {
    usage
    emit_kv REJECTED_COUNT 0
    emit_kv STATUS failed
    emit_kv ERROR "$1"
    exit 2
}

IMPLEMENT_TMPDIR=""
RUN_ID=""
LOG_ROOT=""
while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) [ $# -ge 2 ] || fail_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || fail_usage "--run-id requires a value"; RUN_ID=$2; shift 2 ;;
        --log-root) [ $# -ge 2 ] || fail_usage "--log-root requires a value"; LOG_ROOT=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir is required"
[ -d "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir not found"

file="$IMPLEMENT_TMPDIR/rejected-findings.md"
if [ ! -s "$file" ]; then
    emit "⏩ 16: rejected findings status=empty count=0"
    emit_kv REJECTED_COUNT 0
    emit_kv STATUS empty
    exit 0
fi

count="$(grep -Ec '^\[[^]]+\]|^- ' "$file" 2>/dev/null || printf '0')"
[ "$count" -gt 0 ] 2>/dev/null || count=1

if [ -n "$RUN_ID" ] && [ -n "$LOG_ROOT" ]; then
    mkdir -p "$LOG_ROOT/implement/$RUN_ID" 2>/dev/null || true
    full_file="$IMPLEMENT_TMPDIR/rejected-findings-full.md"
    if [ -s "$full_file" ]; then
        cp "$full_file" "$LOG_ROOT/implement/$RUN_ID/rejected-findings.md" 2>/dev/null || true
    else
        cp "$file" "$LOG_ROOT/implement/$RUN_ID/rejected-findings.md" 2>/dev/null || true
    fi
fi

emit "⚠ 16: rejected findings count=$count details=rejected-findings.md"
emit_kv REJECTED_COUNT "$count"
emit_kv STATUS ok
exit 0
