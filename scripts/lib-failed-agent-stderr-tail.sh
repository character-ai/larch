# shellcheck shell=bash
# lib-failed-agent-stderr-tail.sh - sourced library; not executable; no shebang.
# Redacted, bounded stderr tails for failed external-agent subprocesses (#3202).
# Default 30 lines (design Round 1; issue #3202 filed 50). No raw >&2 except
# emit_failed_agent_stderr_tail_raw (non-quiet callers only).

if [[ -n "${LARCH_FAILED_AGENT_STDERR_TAIL_LOADED:-}" ]]; then
    return 0
fi

_LARCH_FAILED_AGENT_STDERR_TAIL_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$_LARCH_FAILED_AGENT_STDERR_TAIL_SCRIPT_DIR/lib-quiet.sh"

_failed_agent_stderr_tail_warn_unavailable() {
    local msg='WARN failed-agent stderr tail unavailable (redaction tooling)'
    if declare -f larch_err &>/dev/null; then
        larch_err "$msg"
    else
        printf '%s\n' "$msg" >&2
    fi
}

_failed_agent_stderr_sanitize_line() {
    local line="$1"
    if declare -f sanitize_diagnostic_line &>/dev/null; then
        printf '%s' "$line" | sanitize_diagnostic_line
    else
        printf '%s' "$line"
    fi
}

_emit_failed_agent_stderr_tail_line() {
    local line="$1" sanitized
    sanitized=$(_failed_agent_stderr_sanitize_line "$line")
    if declare -f larch_err &>/dev/null; then
        larch_err "$sanitized"
    else
        printf '%s\n' "$sanitized" >&2
    fi
}

failed_agent_stderr_tail_lines() {
    local raw="${LARCH_FAILED_AGENT_STDERR_TAIL_LINES:-30}"
    case "$raw" in
        ''|*[!0-9]*) printf '30' ;;
        *) printf '%s' "$raw" ;;
    esac
}

failed_agent_stderr_byte_cap() {
    printf '5120'
}

select_failed_agent_stderr_source() {
    local output_file="$1"
    local capture_stdout="${2:-false}"
    local capture_stdout_only="${3:-false}"
    local candidate=""

    if [[ "$capture_stdout" == "true" ]]; then
        if [[ -s "$output_file" ]]; then
            candidate="$output_file"
        elif [[ -s "${output_file}.diag" ]]; then
            candidate="${output_file}.diag"
        fi
    elif [[ "$capture_stdout_only" == "true" ]]; then
        if [[ -s "${output_file}.diag" ]]; then
            candidate="${output_file}.diag"
        elif [[ -s "$output_file" ]]; then
            candidate="$output_file"
        fi
    else
        if [[ -s "${output_file}.sidecar" ]]; then
            candidate="${output_file}.sidecar"
        elif [[ -s "$output_file" ]]; then
            candidate="$output_file"
        elif [[ -s "${output_file}.diag" ]]; then
            candidate="${output_file}.diag"
        fi
    fi

    if [[ -n "$candidate" ]]; then
        printf '%s' "$candidate"
        return 0
    fi
    return 1
}

render_failed_agent_stderr_tail() {
    local source_file="$1"
    local lines cap redact spool

    lines=$(failed_agent_stderr_tail_lines)
    if [[ "$lines" == "0" ]]; then
        return 1
    fi
    [[ -n "$source_file" && -s "$source_file" ]] || return 1

    cap=$(failed_agent_stderr_byte_cap)
    redact_tmpdir="$_LARCH_FAILED_AGENT_STDERR_TAIL_SCRIPT_DIR/redact-tmpdir-paths.sh"
    redact="$_LARCH_FAILED_AGENT_STDERR_TAIL_SCRIPT_DIR/redact-secrets.sh"
    [[ -x "$redact_tmpdir" && -x "$redact" ]] || return 1

    spool=$(mktemp "${TMPDIR:-/tmp}/larch-stderr-tail-spool.XXXXXX") || return 1
    local _pipe_rc=0
    set +o pipefail 2>/dev/null || true
    tail -n "$lines" "$source_file" | "$redact_tmpdir" | "$redact" >"$spool" || _pipe_rc=$?
    set -o pipefail 2>/dev/null || true
    if [[ "$_pipe_rc" -ne 0 ]] || [[ ! -s "$spool" ]]; then
        rm -f "$spool"
        return 1
    fi
    head -c "$cap" "$spool"
    rm -f "$spool"
    return 0
}

write_failed_agent_stderr_tail() {
    local source_file="$1"
    local output_file="$2"
    local tail_path="${output_file}.stderr-tail"
    local rendered tmp

    rendered=$(render_failed_agent_stderr_tail "$source_file" 2>/dev/null || true)
    if [[ -n "$rendered" ]]; then
        tmp=$(mktemp "${tail_path}.XXXXXX") || return 1
        printf '%s' "$rendered" >"$tmp"
        mv "$tmp" "$tail_path"
        return 0
    fi
    if [[ "$(failed_agent_stderr_tail_lines)" != "0" ]] && [[ -n "$source_file" && -s "$source_file" ]]; then
        _failed_agent_stderr_tail_warn_unavailable
    fi
    rm -f "$tail_path"
    return 1
}

_escape_sed_ere_literal() {
    printf '%s' "$1" | sed 's/[][\\^.$*+?(){}|]/\\&/g'
}

failed_agent_stderr_signature() {
    local tail_file="$1"
    local norm home_cache home_ere

    [[ -s "$tail_file" ]] || return 1
    home_cache="${HOME:-}/.cache/larch/sessions"
    norm=$(
        sed -E \
            -e 's/0x[0-9a-fA-F]+/0x#/g' \
            -e 's/[0-9]+/#/g' \
            -e 's#/tmp[^[:space:]]*#<path>#g' \
            -e 's#/var/folders[^[:space:]]*#<path>#g' \
            <"$tail_file"
    )
    if [[ -n "$home_cache" ]]; then
        home_ere=$(_escape_sed_ere_literal "$home_cache")
        norm=$( ( set +o pipefail 2>/dev/null || true
                  printf '%s' "$norm" | sed -E "s|${home_ere}[^[:space:]]*|<path>|g"
                ) 2>/dev/null) || true
    fi
    norm=$(printf '%s' "$norm" | sed -E 's/[^[:space:]]+\.(txt|stderr-tail|sidecar|diag|done)( |$)/<out>\2/g')
    cksum <<<"$norm" | awk '{print $1}'
}

emit_failed_agent_stderr_tail_file_raw() {
    local tail_file="$1"

    [[ -s "$tail_file" ]] || return 1
    {
        printf '%s\n' '--- failed agent stderr tail ---' >&2
        while IFS= read -r _tail_line || [[ -n "$_tail_line" ]]; do
            printf '%s\n' "$(_failed_agent_stderr_sanitize_line "$_tail_line")" >&2
        done <"$tail_file"
        printf '%s\n' '--- end failed agent stderr tail ---' >&2
    }
    unset _tail_line
    return 0
}

emit_failed_agent_stderr_tail_raw() {
    local output_file="$1"

    emit_failed_agent_stderr_tail_file_raw "${output_file}.stderr-tail"
}

LARCH_FAILED_AGENT_STDERR_TAIL_LOADED=1
