#!/usr/bin/env bash
# timing-ledger.sh — Session-scoped TSV timing ledger for /implement, /design, and /review.

set -euo pipefail

SCRIPT_NAME=${0##*/}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
FLOCK_WARNED=false

warn() {
    larch_err "$SCRIPT_NAME: WARNING: $*"
}

# Path-validation primitives are shared with timing-report.sh via the
# sourced library so both scripts agree on the allowed-roots set
# (closes review FINDING_1 + FINDING_4).
# shellcheck source=scripts/lib-timing-paths.sh
source "$SCRIPT_DIR/lib-timing-paths.sh"

is_uint() {
    [[ "$1" =~ ^[0-9]+$ ]]
}

validate_under_tmp() {
    local raw="$1"
    local root candidate
    root=$(tmp_root) || {
        warn "cannot canonicalize TMPDIR"
        return 1
    }
    candidate=$(validate_under_roots "$raw" "$root") || {
        warn "--ledger must resolve under ${TMPDIR:-/tmp}: $raw"
        return 1
    }
    printf '%s' "$candidate"
}

allowed_env_roots() {
    timing_allowed_roots
}

validate_env_ledger() {
    local raw="$1"
    local -a roots=()
    local root
    while IFS= read -r root; do
        [[ -n "$root" ]] && roots+=("$root")
    done < <(allowed_env_roots)
    validate_under_roots "$raw" "${roots[@]+"${roots[@]}"}"
}

resolve_ledger_path() {
    local override="$1"
    local env_candidate
    if [[ -n "$override" ]]; then
        validate_under_tmp "$override"
        return
    fi
    if [[ -n "${LARCH_TIMING_LEDGER:-}" ]]; then
        if env_candidate=$(validate_env_ledger "$LARCH_TIMING_LEDGER" 2>/dev/null); then
            printf '%s' "$env_candidate"
            return
        fi
        warn "LARCH_TIMING_LEDGER not under any allowed root: $LARCH_TIMING_LEDGER"
    fi
    if [[ -n "${IMPLEMENT_TMPDIR:-}" && -d "$IMPLEMENT_TMPDIR" ]]; then
        printf '%s/timing-ledger.tsv' "$(canonical_dir "$IMPLEMENT_TMPDIR")"
        return
    fi
    if [[ -n "${SESSION_ENV_PATH:-}" && -d "$(dirname "$SESSION_ENV_PATH")" ]]; then
        printf '%s/timing-ledger.tsv' "$(canonical_dir "$(dirname "$SESSION_ENV_PATH")")"
        return
    fi
    if [[ -n "${DESIGN_TMPDIR:-}" && -d "$DESIGN_TMPDIR" ]]; then
        printf '%s/timing-ledger.tsv' "$(canonical_dir "$DESIGN_TMPDIR")"
        return
    fi
    if [[ -n "${REVIEW_TMPDIR:-}" && -d "$REVIEW_TMPDIR" ]]; then
        printf '%s/timing-ledger.tsv' "$(canonical_dir "$REVIEW_TMPDIR")"
        return
    fi
    warn "no per-run ledger root set; expected one of --ledger, LARCH_TIMING_LEDGER, IMPLEMENT_TMPDIR, SESSION_ENV_PATH, DESIGN_TMPDIR, REVIEW_TMPDIR"
    return 1
}

ensure_ledger() {
    local ledger="$1"
    local parent
    # Reject symlinks before any write. The path validator canonicalizes only
    # the parent directory; if `$ledger` itself is a symlink, every `printf >>`
    # and `chmod` follows the link target — which can be outside the allowed
    # containment roots. Closes review FINDING_13.
    if [[ -L "$ledger" ]]; then
        warn "ledger is a symlink, refusing to write: $ledger"
        return 1
    fi
    parent=$(dirname "$ledger")
    mkdir -p "$parent" 2>/dev/null || return 1
    if [[ ! -e "$ledger" ]]; then
        : > "$ledger" || return 1
    elif [[ ! -f "$ledger" ]]; then
        # Existing path is not a regular file (could be a directory, fifo,
        # device, etc). Refuse to follow.
        warn "ledger exists but is not a regular file: $ledger"
        return 1
    fi
    chmod 600 "$ledger" 2>/dev/null || true
}

append_tsv_line() {
    local ledger="$1"
    local row="$2"
    local lock="${ledger}.lock"
    ensure_ledger "$ledger" || return 1
    if [[ "${LARCH_TEST_FORCE_NO_FLOCK:-}" != "1" ]] && command -v flock >/dev/null 2>&1; then
        if ( flock -w 5 9 && printf '%s\n' "$row" >> "$ledger" ) 9>"$lock"; then
            chmod 600 "$ledger" 2>/dev/null || true
            return 0
        fi
        # Lock acquisition failed (contention, slow disk). Fail closed —
        # an unlocked append would let parallel writers interleave bytes
        # mid-line, producing malformed rows that timing-report.sh would
        # silently drop (NF != 13 skip). Closes review FINDING_7.
        if [[ "$FLOCK_WARNED" != "true" ]]; then
            warn "flock lock acquisition failed; skipping append (fail closed) for $ledger"
            FLOCK_WARNED=true
        fi
        return 1
    fi
    # No flock available at all (e.g., minimal container, BSD without
    # util-linux). Single-process containers should be safe with a plain
    # append. Warn once and continue.
    if [[ "$FLOCK_WARNED" != "true" ]]; then
        warn "flock unavailable; appending without lock (single-writer assumption) for $ledger"
        FLOCK_WARNED=true
    fi
    printf '%s\n' "$row" >> "$ledger"
    chmod 600 "$ledger" 2>/dev/null || true
}

sanitize_field() {
    local value="$1"
    value=${value//$'\t'/<NUL>}
    value=${value//$'\n'/<NUL>}
    value=${value//$'\r'/<NUL>}
    printf '%s' "$value"
}

task_kind_allowed() {
    local kind="$1"
    local allowed
    # shellcheck source=scripts/lib-timing-kinds.sh
    source "$SCRIPT_DIR/lib-timing-kinds.sh"
    for allowed in "${TIMING_TASK_KINDS_ALLOWED[@]}"; do
        [[ "$allowed" == "$kind" ]] && return 0
    done
    return 1
}

cmd_mark() {
    local ledger="$1"
    shift
    local step="${1:-}"
    [[ -n "$step" ]] || { warn "mark requires <step-name>"; return 1; }
    step=$(sanitize_field "$step")
    local ts skill row
    ts=$(date +%s)
    skill=$(sanitize_field "${LARCH_TIMING_SKILL:-implement}")
    printf -v row 'v1\tmark\t%s\t%s\t%s\t-\t-\t-\t-\t-\t-\t-\t-' "$ts" "$skill" "$step"
    append_tsv_line "$ledger" "$row"
}

cmd_workflow_path() {
    local ledger="$1"
    shift
    local path="${1:-}"
    case "$path" in
        HARD|SIMPLE) ;;
        *) warn "workflow-path requires HARD or SIMPLE"; return 1 ;;
    esac
    local ts skill row
    ts=$(date +%s)
    skill=$(sanitize_field "${LARCH_TIMING_SKILL:-implement}")
    printf -v row 'v1\tworkflow\t%s\t%s\t-\t-\t-\t-\t-\t-\t-\t-\t%s' "$ts" "$skill" "$path"
    append_tsv_line "$ledger" "$row"
}

cmd_record_vendor_task() {
    local ledger="$1"
    shift
    local vendor="" task_kind="" start_s="" end_s="" output="" exit_code=0 status=complete
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --vendor) vendor="${2:?--vendor requires a value}"; shift 2 ;;
            --task-kind) task_kind="${2:?--task-kind requires a value}"; shift 2 ;;
            --start-s) start_s="${2:?--start-s requires a value}"; shift 2 ;;
            --end-s) end_s="${2:?--end-s requires a value}"; shift 2 ;;
            --output) output="${2:?--output requires a value}"; shift 2 ;;
            --exit-code) exit_code="${2:?--exit-code requires a value}"; shift 2 ;;
            --status) status="${2:?--status requires a value}"; shift 2 ;;
            *) warn "unknown record-vendor-task flag: $1"; return 1 ;;
        esac
    done
    case "$vendor" in codex|cursor) ;; *) warn "vendor must be codex or cursor"; return 1 ;; esac
    [[ "$task_kind" =~ ^[a-z][a-z0-9-]{0,63}$ ]] || { warn "malformed task-kind: $task_kind"; return 1; }
    task_kind_allowed "$task_kind" || warn "unknown task-kind: $task_kind"
    is_uint "$start_s" || { warn "--start-s must be a non-negative integer"; return 1; }
    is_uint "$end_s" || { warn "--end-s must be a non-negative integer"; return 1; }
    is_uint "$exit_code" || { warn "--exit-code must be a non-negative integer"; return 1; }
    case "$status" in complete|signal|unknown) ;; *) warn "--status must be complete, signal, or unknown"; return 1 ;; esac
    local duration_s
    if (( end_s < start_s )); then
        warn "end_s precedes start_s; clamping duration_s to 0"
        duration_s=0
        status=unknown
    else
        duration_s=$((end_s - start_s))
    fi
    local ts skill output_base row
    ts=$(date +%s)
    skill=$(sanitize_field "${LARCH_TIMING_SKILL:-implement}")
    output_base=$(basename "$output")
    task_kind=$(sanitize_field "$task_kind")
    output_base=$(sanitize_field "$output_base")
    printf -v row 'v1\tvendor\t%s\t%s\t-\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' \
        "$ts" "$skill" "$vendor" "$task_kind" "$start_s" "$end_s" "$duration_s" "$output_base" "$exit_code" "$status"
    append_tsv_line "$ledger" "$row"
}

cmd_dump() {
    local ledger="$1"
    emit "$ledger"
    [[ -s "$ledger" ]] && emit "$(cat "$ledger")"
}

main() {
    local ledger_override="" cmd ledger
    local -a remaining=()
    local i arg next_i
    i=1
    while (( i <= $# )); do
        arg="${!i}"
        if [[ "$arg" == "--ledger" ]]; then
            next_i=$((i + 1))
            if (( next_i > $# )); then
                warn "--ledger requires a value"
                return 1
            fi
            ledger_override="${!next_i}"
            i=$((next_i + 1))
        else
            remaining+=("$arg")
            i=$((i + 1))
        fi
    done
    set -- "${remaining[@]}"
    cmd="${1:-}"
    shift || true
    ledger=$(resolve_ledger_path "$ledger_override") || return 1
    case "$cmd" in
        mark) cmd_mark "$ledger" "$@" ;;
        record-vendor-task) cmd_record_vendor_task "$ledger" "$@" ;;
        workflow-path) cmd_workflow_path "$ledger" "$@" ;;
        dump) cmd_dump "$ledger" ;;
        *) warn "usage: timing-ledger.sh [--ledger PATH] mark <step> | record-vendor-task --vendor V --task-kind K --start-s S --end-s S --output P [--exit-code N] [--status S] | workflow-path HARD|SIMPLE | dump"; return 1 ;;
    esac
}

main "$@" || true
exit 0
