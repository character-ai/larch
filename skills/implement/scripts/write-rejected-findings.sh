#!/usr/bin/env bash
# write-rejected-findings.sh — summarize rejected code-review findings.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
REDACT_TMP="$PLUGIN_ROOT/scripts/redact-tmpdir-paths.sh"
REDACT_SECRETS="$PLUGIN_ROOT/scripts/redact-secrets.sh"

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
full_file="$IMPLEMENT_TMPDIR/rejected-findings-full.md"
summary_file="$file"
detail_file="$file"
detail_label="rejected-findings.md"
if [ -s "$full_file" ]; then
    detail_file="$full_file"
    detail_label="rejected-findings-full.md"
fi
if [ ! -s "$summary_file" ] && [ -s "$detail_file" ]; then
    summary_file="$detail_file"
fi
if [ ! -s "$summary_file" ]; then
    emit "⏩ 16: rejected findings status=empty count=0"
    emit_kv REJECTED_COUNT 0
    emit_kv STATUS empty
    exit 0
fi

count="$(grep -Ec '^\[[^]]+\]|^- |^###[[:space:]]+\[(rejected|Code Review)\]' "$summary_file" 2>/dev/null || printf '0')"
[ "$count" -gt 0 ] 2>/dev/null || count=1

if [ -n "$RUN_ID" ] && [ -n "$LOG_ROOT" ]; then
    mkdir -p "$LOG_ROOT/implement/$RUN_ID" 2>/dev/null || true
    if [ -x "$REDACT_TMP" ] && [ -x "$REDACT_SECRETS" ]; then
        "$REDACT_TMP" < "$detail_file" | "$REDACT_SECRETS" > "$LOG_ROOT/implement/$RUN_ID/rejected-findings.md" 2>/dev/null || true
    else
        cp "$detail_file" "$LOG_ROOT/implement/$RUN_ID/rejected-findings.md" 2>/dev/null || true
    fi
fi

emit "⚠ 16: rejected findings count=$count details=$detail_label"
emit_kv REJECTED_COUNT "$count"
emit_kv STATUS ok
exit 0
