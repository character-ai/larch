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

count_rejected_findings() {
    local source_file="$1" count_value="0"
    count_value="$(grep -Ec '^###[[:space:]]+\[(rejected|Code Review)\][[:space:]]+' "$source_file" 2>/dev/null || printf '0')"
    if [ "$count_value" -gt 0 ] 2>/dev/null; then
        printf '%s\n' "$count_value"
        return 0
    fi
    count_value="$(grep -Ec '^[0-9]+:FINDING_[A-Za-z0-9_]+_OUTCOME=rejected$|^\[[^]]+\]|^- ' "$source_file" 2>/dev/null || printf '0')"
    if [ "$count_value" -gt 0 ] 2>/dev/null; then
        printf '%s\n' "$count_value"
    else
        printf '1\n'
    fi
}

count="$(count_rejected_findings "$detail_file")"

persist_detail_copy() {
    local dest_dir dest_file tmp_file
    dest_dir="$LOG_ROOT/implement/$RUN_ID"
    dest_file="$dest_dir/rejected-findings.md"
    mkdir -p "$dest_dir"
    tmp_file="$(mktemp "${TMPDIR:-/tmp}/rejected-findings-copy.XXXXXX")"
    if [ -x "$REDACT_TMP" ] && [ -x "$REDACT_SECRETS" ]; then
        if ! "$REDACT_TMP" < "$detail_file" | "$REDACT_SECRETS" > "$tmp_file"; then
            rm -f "$tmp_file"
            return 1
        fi
    else
        if ! cp "$detail_file" "$tmp_file"; then
            rm -f "$tmp_file"
            return 1
        fi
    fi
    if [ ! -s "$tmp_file" ]; then
        rm -f "$tmp_file"
        return 1
    fi
    mv -f "$tmp_file" "$dest_file"
}

if [ -n "$RUN_ID" ] && [ -n "$LOG_ROOT" ]; then
    if ! persist_detail_copy; then
        emit_kv REJECTED_COUNT "$count"
        emit_kv STATUS failed
        emit_kv ERROR "failed to persist rejected findings log copy"
        exit 1
    fi
fi

emit "⚠ 16: rejected findings count=$count details=$detail_label"
emit_kv REJECTED_COUNT "$count"
emit_kv STATUS ok
exit 0
