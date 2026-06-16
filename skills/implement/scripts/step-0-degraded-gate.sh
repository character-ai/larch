#!/usr/bin/env bash
# step-0-degraded-gate.sh — /implement degraded external-tool availability gate.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR

rehydrate_plugin_root() {
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
        # shellcheck source=/dev/null
        . "$IMPLEMENT_TMPDIR/plugin-root.env"
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
        CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
        CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
    fi
    export CLAUDE_PLUGIN_ROOT
}

read_session_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/session-env.sh"
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

rehydrate_larch_triplet() {
    LARCH_TOKEN_SESSION_ID=$(read_session_key LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}")
    LARCH_CLAUDE_SOURCE_FILE=$(read_session_key LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}")
    LARCH_TIMING_LEDGER=$(read_session_key LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}")
    export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
}

rehydrate_plugin_root
CODEX_BINARY_FOUND=$(read_session_key CODEX_BINARY_FOUND "")
CURSOR_BINARY_FOUND=$(read_session_key CURSOR_BINARY_FOUND "")

_check_reviewer_args=(agent check-reviewers)
if ! command -v codex >/dev/null 2>&1; then
    _check_reviewer_args+=(--skip-codex-probe)
fi
if ! command -v cursor >/dev/null 2>&1; then
    _check_reviewer_args+=(--skip-cursor-probe)
fi

_probe_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-degraded-gate-probe.XXXXXX")" || {
    printf '%s\n' "step-0-degraded-gate: could not allocate probe stdout capture" >&2
    exit 1
}
set +e
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" "${_check_reviewer_args[@]}" >"$_probe_stdout_file" 2>/dev/null
_probe_rc=$?
if [[ "$_probe_rc" -ne 0 ]]; then
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" "${_check_reviewer_args[@]}" >"$_probe_stdout_file" 2>/dev/null || true
fi
set -e

CODEX_PRESENT=""
CURSOR_PRESENT=""
while IFS= read -r _probe_line || [[ -n "$_probe_line" ]]; do
    case "$_probe_line" in
        CODEX_PRESENT=*) CODEX_PRESENT="${_probe_line#CODEX_PRESENT=}" ;;
        CURSOR_PRESENT=*) CURSOR_PRESENT="${_probe_line#CURSOR_PRESENT=}" ;;
    esac
done < "$_probe_stdout_file"
rm -f "$_probe_stdout_file"

python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" agent degraded-tools-gate --skill implement   --codex-present "$CODEX_PRESENT"   --cursor-present "$CURSOR_PRESENT"   --codex-binary-found "$CODEX_BINARY_FOUND"   --cursor-binary-found "$CURSOR_BINARY_FOUND"
