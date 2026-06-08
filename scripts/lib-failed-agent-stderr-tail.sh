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
    local explicit_sink="${4:-}"
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
        if [[ -n "$explicit_sink" && -s "$explicit_sink" ]]; then
            candidate="$explicit_sink"
        elif [[ -s "${output_file}.sidecar" ]]; then
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

collector_stderr_tail_candidates() {
    local reviewer_file="$1"
    printf '%s\n' "$reviewer_file"
    case "$reviewer_file" in
        *-phase3.txt)
            printf '%s\n' "${reviewer_file%-phase3.txt}-phase2.txt"
            printf '%s\n' "${reviewer_file%-phase3.txt}.txt"
            ;;
        *-phase2.txt)
            printf '%s\n' "${reviewer_file%-phase2.txt}.txt"
            ;;
        *-phase1.txt)
            printf '%s\n' "${reviewer_file%-phase1.txt}.txt"
            ;;
    esac
}

resolve_collector_stderr_tail_file() {
    local reviewer_file="$1" _retry_tail _ns_retry_tail _candidate _tmp_tail
    _retry_tail="${reviewer_file%.txt}-retry.txt.stderr-tail"
    if [[ -s "$_retry_tail" ]]; then
        printf '%s' "$_retry_tail"
        return 0
    fi
    _ns_retry_tail="${reviewer_file%.txt}-ns-retry.txt.stderr-tail"
    if [[ -s "$_ns_retry_tail" ]]; then
        printf '%s' "$_ns_retry_tail"
        return 0
    fi
    while IFS= read -r _candidate || [[ -n "$_candidate" ]]; do
        [[ -n "$_candidate" ]] || continue
        if [[ -s "${_candidate}.launch-stderr" ]]; then
            _tmp_tail=$(mktemp "${TMPDIR:-/tmp}/larch-launch-stderr-tail.XXXXXX") || return 1
            if render_failed_agent_stderr_tail "${_candidate}.launch-stderr" >"$_tmp_tail" 2>/dev/null && [[ -s "$_tmp_tail" ]]; then
                printf '%s' "$_tmp_tail"
                return 0
            fi
            rm -f "$_tmp_tail"
        fi
        if [[ -s "${_candidate}.stderr-tail" ]]; then
            printf '%s' "${_candidate}.stderr-tail"
            return 0
        fi
    done < <(collector_stderr_tail_candidates "$reviewer_file")
    return 1
}

emit_failed_agent_stderr_tail_larch_err() {
    local output_file="$1" tail_file="${1}.stderr-tail"
    [[ -s "$tail_file" ]] || return 1
    larch_err '--- failed agent stderr tail ---'
    while IFS= read -r _tail_line || [[ -n "$_tail_line" ]]; do
        [[ -n "$_tail_line" ]] || continue
        _emit_failed_agent_stderr_tail_line "$_tail_line"
    done <"$tail_file"
    larch_err '--- end failed agent stderr tail ---'
    unset _tail_line
    return 0
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

# ---------------------------------------------------------------------------
# Vendor-agent failure-diagnostics carrier (#3713).
#
# A single committed failure carrier `${OUTPUT}.failure-diag` preserves enough
# diagnostics to distinguish health-gate fast-fail vs mid-run crash vs timeout
# (124) vs auth vs quota at every vendor-agent call site. The raw per-attempt
# streams (`.sidecar`, `.diag`, `.events.jsonl`, `.sidecar.history`, events
# history) stay publish-excluded; only the composed, bounded, content-filtered
# carrier reaches git. Producers compose the carrier on failure only; a retry
# that later SUCCEEDS clears the carrier so retry-then-success commits nothing.
# All functions are Bash 3.2-safe (no associative arrays / mapfile / namerefs).
# ---------------------------------------------------------------------------

vendor_failure_diag_byte_cap() {
    printf '16384'
}

vendor_failure_diag_section_lines() {
    local raw="${LARCH_VENDOR_FAILURE_DIAG_SECTION_LINES:-120}"
    case "$raw" in
        ''|*[!0-9]*) printf '120' ;;
        *) printf '%s' "$raw" ;;
    esac
}

# Fold only failure-shaped lines out of a tool-native event / transcript stream
# so success transcripts and non-error bulk never reach the committed carrier.
# Reads $1 (a file); writes a bounded filtered tail to stdout. Never fails the
# caller (best-effort under set -e).
_vendor_failure_diag_filter_stream() {
    local src="$1" lines
    [[ -n "$src" && -s "$src" ]] || return 0
    lines=$(vendor_failure_diag_section_lines)
    {
        set +o pipefail 2>/dev/null || true
        grep -aiE 'error|fail|quota|usage[ _-]?limit|rate[ _-]?limit|turn\.failed|unauthor|forbidden|denied|timed?[ _-]?out|exception|panic|fatal|unhealthy|exit[ _-]?code' "$src" 2>/dev/null \
            | tail -n "$lines"
        set -o pipefail 2>/dev/null || true
    } 2>/dev/null || true
    return 0
}

# Append a bounded labeled section for one non-empty source file to a carrier
# temp. $1=label $2=source-file $3=dest(append) $4=filter(true|false).
# Returns 0 when a non-empty section was written, 1 otherwise.
_vendor_failure_diag_append_section() {
    local label="$1" src="$2" dest="$3" filter="${4:-false}"
    local lines body
    [[ -n "$src" && -s "$src" ]] || return 1
    case "$src" in /dev/null) return 1 ;; esac
    lines=$(vendor_failure_diag_section_lines)
    if [[ "$filter" == "true" ]]; then
        body=$(_vendor_failure_diag_filter_stream "$src")
    else
        body=$(tail -n "$lines" "$src" 2>/dev/null || true)
    fi
    [[ -n "$body" ]] || return 1
    {
        printf '===== %s =====\n' "$label"
        printf '%s\n' "$body"
    } >> "$dest" 2>/dev/null || return 1
    return 0
}

# external_stream_reset TARGET HISTORY [LABEL]
# Archive a bounded tail of a per-attempt diagnostic stream to an append-only
# HISTORY file (with an attempt header) when TARGET is non-empty, then truncate
# TARGET. Mirrors the deliberate per-attempt `: > "$SIDECAR"` reset while
# preserving the outgoing content for the composed failure carrier. HISTORY is
# publish-excluded; only the composed `*.failure-diag` reaches git. Never fails
# the caller.
external_stream_reset() {
    local target="$1" history="${2:-}" label="${3:-attempt}" lines
    [[ -n "$target" ]] || return 0
    case "$target" in /dev/null) return 0 ;; esac
    if [[ -n "$history" && -s "$target" ]]; then
        lines=$(vendor_failure_diag_section_lines)
        {
            printf '===== %s =====\n' "$label"
            tail -n "$(( lines * 2 ))" "$target" 2>/dev/null || true
            printf '\n'
        } >> "$history" 2>/dev/null || true
    fi
    : > "$target" 2>/dev/null || true
    return 0
}

# write_failure_diag OUTPUT [--sink PATH] [--history PATH] [--events PATH]
# Compose `${OUTPUT}.failure-diag` from the diagnostic source list (labeled,
# bounded, content-filtered sections for every non-empty stream). Append-with-
# header when the carrier already exists (retry composition). Applies content
# folding + byte caps only; secret/tmpdir redaction happens downstream at the
# publish / append-vendor-failure-diagnostics boundary. Returns 0 when the
# carrier is non-empty after composition, 1 otherwise.
write_failure_diag() {
    local output="" sink="" history="" events=""
    [[ $# -gt 0 ]] || return 1
    output="$1"; shift || true
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --sink) sink="${2:-}"; shift 2 ;;
            --history) history="${2:-}"; shift 2 ;;
            --events) events="${2:-}"; shift 2 ;;
            *) shift ;;
        esac
    done
    [[ -n "$output" ]] || return 1
    case "$output" in /dev/null) return 1 ;; esac

    [[ -n "$history" ]] || history="${output}.sidecar.history"
    [[ -n "$events" ]] || events="${output}.events.jsonl"

    local carrier="${output}.failure-diag"
    local tmp
    tmp=$(mktemp "${carrier}.compose.XXXXXX" 2>/dev/null) || tmp=$(mktemp "${TMPDIR:-/tmp}/larch-failure-diag.XXXXXX" 2>/dev/null) || return 1

    local wrote=false
    # Ordered, labeled sections. Filter event/transcript streams to failure-
    # shaped lines; include already-diagnostic streams (sidecar/diag/stderr) as
    # bounded tails.
    _vendor_failure_diag_append_section 'sidecar.history' "$history" "$tmp" false && wrote=true
    _vendor_failure_diag_append_section 'events.history (filtered)' "${output}.events.history" "$tmp" true && wrote=true
    if [[ -n "$sink" && "$sink" != "$events" && "$sink" != "${output}.sidecar" && "$sink" != "${output}.diag" ]]; then
        _vendor_failure_diag_append_section 'sink' "$sink" "$tmp" false && wrote=true
    fi
    _vendor_failure_diag_append_section 'sidecar' "${output}.sidecar" "$tmp" false && wrote=true
    _vendor_failure_diag_append_section 'diag' "${output}.diag" "$tmp" false && wrote=true
    _vendor_failure_diag_append_section 'events.jsonl (filtered)' "$events" "$tmp" true && wrote=true
    _vendor_failure_diag_append_section 'stderr' "${output}.stderr" "$tmp" false && wrote=true
    _vendor_failure_diag_append_section 'launch-stderr' "${output}.launch-stderr" "$tmp" false && wrote=true
    _vendor_failure_diag_append_section 'launcher-stderr' "${output}.launcher-stderr" "$tmp" false && wrote=true

    if [[ "$wrote" != "true" || ! -s "$tmp" ]]; then
        rm -f "$tmp"
        return 1
    fi

    local cap
    cap=$(vendor_failure_diag_byte_cap)
    if [[ -s "$carrier" ]]; then
        {
            printf '\n===== additional failure diagnostics =====\n'
            head -c "$cap" "$tmp"
        } >> "$carrier"
    else
        head -c "$cap" "$tmp" > "$carrier"
    fi
    rm -f "$tmp"
    [[ -s "$carrier" ]]
}

# resolve_failure_diagnostic_source OUTPUT [--sink PATH] [--history PATH] [--events PATH]
# Print the path of the best available diagnostic source for a failed launch:
# the composed carrier when present, else the first non-empty fallback across the
# source list (including retry / ns-retry carrier candidates — F9). Returns 1
# when every candidate is empty/missing.
resolve_failure_diagnostic_source() {
    local output="" sink="" history="" events=""
    [[ $# -gt 0 ]] || return 1
    output="$1"; shift || true
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --sink) sink="${2:-}"; shift 2 ;;
            --history) history="${2:-}"; shift 2 ;;
            --events) events="${2:-}"; shift 2 ;;
            *) shift ;;
        esac
    done
    [[ -n "$output" ]] || return 1
    local stem="${output%.txt}" c
    for c in \
        "${output}.failure-diag" \
        "${stem}-retry.txt.failure-diag" \
        "${stem}-ns-retry.txt.failure-diag" \
        "$sink" \
        "${output}.sidecar.history" \
        "$history" \
        "${output}.sidecar" \
        "${output}.diag" \
        "$events" \
        "${output}.events.jsonl" \
        "${output}.stderr" \
        "${output}.launch-stderr" \
        "${output}.launcher-stderr" \
        "$output" ; do
        [[ -n "$c" && -s "$c" ]] || continue
        printf '%s' "$c"
        return 0
    done
    return 1
}

# resolve_execution_issues_log
# Shared resolver for the per-run execution-issues.md log location. Precedence:
# LARCH_EXECUTION_ISSUES_LOG → dirname(SESSION_ENV_PATH) → IMPLEMENT_TMPDIR →
# DESIGN_TMPDIR → REVIEW_TMPDIR. Prints the resolved path (file need not exist
# yet); returns 1 when no source is set.
resolve_execution_issues_log() {
    if [[ -n "${LARCH_EXECUTION_ISSUES_LOG:-}" ]]; then
        printf '%s' "$LARCH_EXECUTION_ISSUES_LOG"
        return 0
    fi
    if [[ -n "${SESSION_ENV_PATH:-}" ]]; then
        printf '%s/execution-issues.md' "$(dirname "$SESSION_ENV_PATH")"
        return 0
    fi
    local d
    for d in "${IMPLEMENT_TMPDIR:-}" "${DESIGN_TMPDIR:-}" "${REVIEW_TMPDIR:-}"; do
        [[ -n "$d" ]] || continue
        printf '%s/execution-issues.md' "$d"
        return 0
    done
    return 1
}

# append_vendor_failure_diagnostics --source PATH --site LABEL [--tmpdir DIR] [--exit-code N]
# Append a resolved, redacted failure-diagnostic excerpt to the canonical per-run
# implement batch via per-slot staging — the SOLE durable implement flush path
# (F6). Each call writes its own unique part file under
# `$tmpdir/vendor-failure-diagnostics.parts/`; flush-vendor-failure-diagnostics.sh
# concatenates the parts into `$tmpdir/vendor-failure-diagnostics.txt` before each
# log commit. Per-slot staging avoids interleaved concurrent appends without
# requiring flock (absent on macOS). Best-effort: never fails the caller.
append_vendor_failure_diagnostics() {
    local source="" site="" tmpdir="${IMPLEMENT_TMPDIR:-}" exit_code=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --source) source="${2:-}"; shift 2 ;;
            --site) site="${2:-}"; shift 2 ;;
            --tmpdir) tmpdir="${2:-}"; shift 2 ;;
            --exit-code) exit_code="${2:-}"; shift 2 ;;
            *) shift ;;
        esac
    done
    [[ -n "$tmpdir" && -d "$tmpdir" ]] || return 0
    local parts_dir="$tmpdir/vendor-failure-diagnostics.parts"
    mkdir -p "$parts_dir" 2>/dev/null || return 0
    local cap; cap=$(vendor_failure_diag_byte_cap)
    local redact_tmpdir="$_LARCH_FAILED_AGENT_STDERR_TAIL_SCRIPT_DIR/redact-tmpdir-paths.sh"
    local redact="$_LARCH_FAILED_AGENT_STDERR_TAIL_SCRIPT_DIR/redact-secrets.sh"
    local raw red part
    raw=$(mktemp "${TMPDIR:-/tmp}/larch-vendor-failure-raw.XXXXXX" 2>/dev/null) || return 0
    {
        printf '===== %s =====\n' "${site:-vendor failure}"
        [[ -n "$exit_code" ]] && printf 'exit-code: %s\n' "$exit_code"
        if [[ -n "$source" && -s "$source" ]]; then
            head -c "$cap" "$source"
            printf '\n'
        else
            printf 'no diagnostics captured (exit %s)\n' "${exit_code:-unknown}"
        fi
    } > "$raw" 2>/dev/null || { rm -f "$raw"; return 0; }
    red=$(mktemp "${TMPDIR:-/tmp}/larch-vendor-failure-red.XXXXXX" 2>/dev/null) || { rm -f "$raw"; return 0; }
    if [[ -x "$redact_tmpdir" && -x "$redact" ]]; then
        # Run the redaction pipe in a subshell so `set +o pipefail` cannot leak
        # the disabled state back to callers that run under `set -euo pipefail`.
        if ! ( set +o pipefail; "$redact_tmpdir" < "$raw" | "$redact" > "$red" ) 2>/dev/null; then
            cp "$raw" "$red" 2>/dev/null || true
        fi
    else
        cp "$raw" "$red" 2>/dev/null || true
    fi
    rm -f "$raw"
    [[ -s "$red" ]] || { rm -f "$red"; return 0; }
    part=$(mktemp "$parts_dir/part.XXXXXX" 2>/dev/null) || { rm -f "$red"; return 0; }
    mv "$red" "$part" 2>/dev/null || { cp "$red" "$part" 2>/dev/null || true; rm -f "$red"; }
    return 0
}

LARCH_FAILED_AGENT_STDERR_TAIL_LOADED=1
