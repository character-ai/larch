#!/usr/bin/env bash
# Shared drift-baseline.env writer for /design plan-size helpers.

if [[ -n "${LARCH_LIB_DRIFT_BASELINE_LOADED:-}" ]]; then
    return 0
fi
LARCH_LIB_DRIFT_BASELINE_LOADED=1

larch_drift_baseline_path() {
    printf '%s/drift-baseline.env' "${1:?design tmpdir required}"
}

larch_drift_baseline_unreadable_marker_path() {
    printf '%s/.drift-baseline-unreadable' "${1:?design tmpdir required}"
}

larch_drift_baseline_mark_unreadable() {
    touch "$(larch_drift_baseline_unreadable_marker_path "$1")" 2>/dev/null || true
}

larch_drift_baseline_clear_unreadable() {
    rm -f "$(larch_drift_baseline_unreadable_marker_path "$1")" 2>/dev/null || true
}

larch_drift_baseline_is_unreadable() {
    [[ -f "$(larch_drift_baseline_unreadable_marker_path "$1")" ]]
}

# Write-once seed: skip when any path exists (regular file or symlink).
larch_drift_baseline_write_once() {
    local design_tmpdir="$1" plan_lines="$2" diff_lines="$3"
    local baseline tmp
    baseline="$(larch_drift_baseline_path "$design_tmpdir")"
    [[ ! -e "$baseline" ]] || return 0
    tmp="${baseline}.tmp.$$"
    if { printf 'BASELINE_PLAN_LINES=%s\n' "$plan_lines"; printf 'BASELINE_DIFF_LINES=%s\n' "$diff_lines"; } >"$tmp" 2>/dev/null \
        && mv -f "$tmp" "$baseline" 2>/dev/null; then
        return 0
    fi
    rm -f "$tmp" 2>/dev/null || true
    return 1
}
