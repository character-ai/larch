# shellcheck shell=bash

# Shared reviewer-prune status derivation and concise env writer.
# Sourced by implement and design review dispatch/flush paths.

_prune_bool_true() {
    [[ "${1:-}" == "true" ]]
}

_prune_nonneg_int() {
    case "${1:-}" in
        ''|*[!0-9]*) printf '0' ;;
        *) printf '%s' "$((10#$1))" ;;
    esac
}

derive_prune_status() {
    local prune_active="${1:-false}" filter_rc="${2:-0}" prune_fail_open="${3:-false}"
    local pruned_count="${4:-0}" panel_pruned_empty="${5:-false}" prune_evaluated="${6:-false}"
    pruned_count="$(_prune_nonneg_int "$pruned_count")"
    case "$filter_rc" in ''|*[!0-9]*) filter_rc=1 ;; *) filter_rc=$((10#$filter_rc)) ;; esac

    if [[ "$filter_rc" -ne 0 || "$prune_fail_open" == "true" ]]; then
        printf '%s\n' failed
    elif [[ "$panel_pruned_empty" == "true" ]]; then
        printf '%s\n' pruned-empty
    elif [[ "$prune_active" != "true" || "$prune_evaluated" != "true" ]]; then
        printf '%s\n' skipped
    elif [[ "$pruned_count" -gt 0 ]]; then
        printf '%s\n' active-dropped
    else
        printf '%s\n' active-kept-all
    fi
}

normalize_prune_eligible() {
    local prune_active="${1:-false}" eligible_count="${2:-0}"
    if [[ "$prune_active" != "true" ]]; then
        printf '0\n'
        return 0
    fi
    _prune_nonneg_int "$eligible_count"
    printf '\n'
}

prune_window_evaluated() {
    local round_num="${1:-}"
    case "$round_num" in
        3|4) printf 'true\n' ;;
        *) printf 'false\n' ;;
    esac
}

REVIEWER_PRUNE_LEDGER_HEADER=$'round\ttool\tslot\tlabel\taccepted_count'

# Repair missing, empty, or header-invalid reviewer prune ledgers before reuse.
ensure_reviewer_prune_ledger() {
    local ledger="$1" header="$REVIEWER_PRUNE_LEDGER_HEADER" tmp preserved=""
    [[ -n "$ledger" ]] || return 0
    mkdir -p "$(dirname "$ledger")" || return 1
    if [[ ! -s "$ledger" ]]; then
        printf '%s\n' "$header" > "$ledger"
        return 0
    fi
    if [[ "$(head -n 1 "$ledger")" == "$header" ]]; then
        return 0
    fi
    if [[ $(wc -l < "$ledger" | tr -d '[:space:]') -gt 1 ]]; then
        preserved=$(tail -n +2 "$ledger" | grep -E '^[0-9]+' || true)
    fi
    tmp="${ledger}.repair.$$"
    {
        printf '%s\n' "$header"
        [[ -n "$preserved" ]] && printf '%s\n' "$preserved"
    } > "$tmp" || { rm -f "$tmp"; return 1; }
    mv -f "$tmp" "$ledger"
}

write_prune_decision_env() {
    local dest="$1" round="$2" prune_active="$3" prune_status="$4" panel_full="$5" eligible="$6" pruned_count="$7" pruned_combos="$8" panel_pruned_empty="$9"
    local tmp dir
    dir="$(dirname "$dest")"
    mkdir -p "$dir" || return 1
    tmp="${dest}.tmp.$$"
    panel_full="$(_prune_nonneg_int "$panel_full")"
    eligible="$(_prune_nonneg_int "$eligible")"
    pruned_count="$(_prune_nonneg_int "$pruned_count")"
    {
        printf 'ROUND=%s\n' "$round"
        printf 'PRUNE_ACTIVE=%s\n' "$prune_active"
        printf 'PRUNE_STATUS=%s\n' "$prune_status"
        printf 'PANEL_FULL=%s\n' "$panel_full"
        printf 'ELIGIBLE=%s\n' "$eligible"
        printf 'PRUNED_COUNT=%s\n' "$pruned_count"
        printf 'PRUNED_COMBOS=%s\n' "$pruned_combos"
        printf 'PANEL_PRUNED_EMPTY=%s\n' "$panel_pruned_empty"
    } > "$tmp" || { rm -f "$tmp"; return 1; }
    mv -f "$tmp" "$dest"
}
