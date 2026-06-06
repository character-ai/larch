#!/usr/bin/env bash
# persist-retally-step3-env.sh — refresh Step 3 result envs after MainAgent re-tally.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-scope-anchor-handoff.sh
source "$PLUGIN_ROOT/scripts/lib-scope-anchor-handoff.sh"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$SCRIPT_DIR/lib-phase-driver.sh"

DESIGN_TMPDIR=""
RETALLY_STDOUT_FILE=""
RETALLY_INPUT=""
TALLY_PLAN_REVIEW_STATUS=""
LOOP_STATUS=""

usage() {
    larch_err "Usage: persist-retally-step3-env.sh --design-tmpdir DIR --retally-stdout-file PATH --tally-plan-review-status STATUS --loop-status STATUS [--retally-input-anchor PATH]"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --retally-stdout-file) RETALLY_STDOUT_FILE="${2:?}"; shift 2 ;;
        --retally-input-anchor) RETALLY_INPUT="${2:?}"; shift 2 ;;
        --tally-plan-review-status) TALLY_PLAN_REVIEW_STATUS="${2:?}"; shift 2 ;;
        --loop-status) LOOP_STATUS="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "persist-retally-step3-env.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$DESIGN_TMPDIR" && -d "$DESIGN_TMPDIR" ]] || {
    larch_err "persist-retally-step3-env.sh: --design-tmpdir must name a directory"
    exit 2
}
[[ -n "$RETALLY_STDOUT_FILE" && -f "$RETALLY_STDOUT_FILE" ]] || {
    larch_err "persist-retally-step3-env.sh: --retally-stdout-file must name a readable file"
    exit 2
}
[[ -n "$TALLY_PLAN_REVIEW_STATUS" ]] || {
    larch_err "persist-retally-step3-env.sh: --tally-plan-review-status is required"
    exit 2
}
[[ -n "$LOOP_STATUS" ]] || {
    larch_err "persist-retally-step3-env.sh: --loop-status is required"
    exit 2
}

_PARSED_SCOPE_ANCHOR_FILE=""
while IFS= read -r _line || [[ -n "$_line" ]]; do
    _key="${_line%%=*}"
    _val="${_line#*=}"
    case "$_key" in
        SCOPE_ANCHOR_FILE) _PARSED_SCOPE_ANCHOR_FILE="$_val" ;;
    esac
done <"$RETALLY_STDOUT_FILE"

design_canon="$(cd "$DESIGN_TMPDIR" && pwd -P)" || exit 2
export TALLY_PLAN_REVIEW_STATUS LOOP_STATUS
_scope_handoff="$(larch_scope_anchor_retally_handoff_value "$design_canon" "${_PARSED_SCOPE_ANCHOR_FILE:-}" "${RETALLY_INPUT:-}")"

_rewrite_env_file() {
    local path="$1"
    local -a kvs=()
    local line key value saw_tally=0 saw_loop=0

    [[ -L "$path" ]] && return 0

    if [[ -f "$path" ]]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            key="${line%%=*}"
            value="${line#*=}"
            case "$key" in
                SCOPE_ANCHOR_FILE) continue ;;
                TALLY_PLAN_REVIEW_STATUS)
                    value="$TALLY_PLAN_REVIEW_STATUS"
                    saw_tally=1
                    ;;
                LOOP_STATUS)
                    value="$LOOP_STATUS"
                    saw_loop=1
                    ;;
            esac
            kvs+=("${key}=${value}")
        done <"$path"
    fi
    [[ "$saw_tally" -eq 1 ]] || kvs+=("TALLY_PLAN_REVIEW_STATUS=$TALLY_PLAN_REVIEW_STATUS")
    [[ "$saw_loop" -eq 1 ]] || kvs+=("LOOP_STATUS=$LOOP_STATUS")
    [[ -z "$_scope_handoff" ]] || kvs+=("SCOPE_ANCHOR_FILE=$_scope_handoff")
    phase_driver_write_result_env "$path" "${kvs[@]}"
}

_rewrite_env_file "$DESIGN_TMPDIR/.step3-plan-review-result.env"
_rewrite_env_file "$DESIGN_TMPDIR/.step3-review-result.env"
exit 0
