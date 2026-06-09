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
_RESOLVED_ROUND_NUM=""
_RESOLVED_ROUND_DIR=""

_resolve_retally_round() {
    local env_file="$DESIGN_TMPDIR/.step3-plan-review-result.env"
    local line key value round_num="" rounds_completed=""
    if [[ -f "$env_file" ]]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            key="${line%%=*}"
            value="${line#*=}"
            case "$key" in
                ROUND_NUM) round_num="$value" ;;
                ROUNDS_COMPLETED) rounds_completed="$value" ;;
            esac
        done <"$env_file"
    fi
    case "$round_num" in ''|*[!0-9]*) round_num="" ;; esac
    case "$rounds_completed" in ''|*[!0-9]*) rounds_completed="" ;; esac
    [[ -n "$round_num" ]] || round_num="$rounds_completed"
    [[ -n "$round_num" ]] || return 0
    round_num=$((10#$round_num))
    [[ "$round_num" -gt 0 ]] || return 0
    local round_dir="$DESIGN_TMPDIR/plan-review/round-${round_num}"
    if [[ -d "$round_dir" ]]; then
        _RESOLVED_ROUND_NUM="$round_num"
        _RESOLVED_ROUND_DIR="$round_dir"
    elif [[ "$TALLY_PLAN_REVIEW_STATUS" == "tally-error" ]]; then
        emit_kv WARN "persist-retally-step3-env: round-${round_num} snapshot missing; skipped round-meta removal"
    fi
}

_merge_retally_accepted_all() {
    [[ "$TALLY_PLAN_REVIEW_STATUS" == "ok" ]] || return 0
    local accepted="$DESIGN_TMPDIR/accepted-plan-findings.md"
    local cumulative="$DESIGN_TMPDIR/accepted-plan-findings-all.md"
    [[ -s "$accepted" ]] || return 0
    python3 - "$cumulative" "$accepted" <<'PY'
import re
import sys
from pathlib import Path

cumulative_path = Path(sys.argv[1])
accepted_path = Path(sys.argv[2])

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

def blocks(text: str):
    return [m.group(0).strip() for m in re.finditer(r"(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)", text)]

existing = blocks(read(cumulative_path))
seen = set(existing)
out = list(existing)
for block in blocks(read(accepted_path)):
    if block in seen:
        continue
    seen.add(block)
    out.append(block)

if out:
    cumulative_path.write_text("\n\n".join(out) + "\n\n", encoding="utf-8")
PY
}

_merge_retally_oos_accepted() {
    [[ "$TALLY_PLAN_REVIEW_STATUS" == "ok" ]] || return 0
    local prior="$DESIGN_TMPDIR/.oos-accepted-design.prev.md"
    local current="$DESIGN_TMPDIR/oos-accepted-design.md"
    python3 - "$prior" "$current" <<'PY'
import re
import sys
from pathlib import Path

prior_path = Path(sys.argv[1])
current_path = Path(sys.argv[2])

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

def blocks(text: str):
    return [m.group(0).strip() for m in re.finditer(r"(?ms)^### OOS_[0-9]+:.*?(?=^### |\Z)", text)]

def desc_key(block: str) -> str:
    match = re.search(r"\*\*Description\*\*:\s*(.+?)(?:\n|$)", block, re.S)
    text = match.group(1) if match else block
    return " ".join(text.strip().lower().split())

out = []
seen = set()
for block in blocks(read(prior_path)):
    key = desc_key(block)
    if key in seen:
        continue
    seen.add(key)
    out.append(block)

for block in blocks(read(current_path)):
    key = desc_key(block)
    if key in seen:
        continue
    seen.add(key)
    out.append(block)

if out:
    current_path.write_text("\n\n".join(out) + "\n\n", encoding="utf-8")
else:
    try:
        current_path.unlink()
    except FileNotFoundError:
        pass
PY
}

_clear_failed_retally_accepted() {
    [[ "$TALLY_PLAN_REVIEW_STATUS" == "tally-error" ]] || return 0
    rm -f "$DESIGN_TMPDIR/accepted-plan-findings.md"
    : >"$DESIGN_TMPDIR/accepted-plan-findings.md"
}

_clear_design_round_meta_on_tally_error() {
    [[ "$TALLY_PLAN_REVIEW_STATUS" == "tally-error" ]] || return 0
    local round_num="${_RESOLVED_ROUND_NUM:-}"
    [[ -n "$round_num" ]] || return 0
    local round_dir="$DESIGN_TMPDIR/plan-review/round-${round_num}"
    [[ -d "$round_dir" ]] || return 0
    rm -f "$round_dir/round-meta.json" "$round_dir/panel-manifest.ndjson" 2>/dev/null || true
}

_refresh_design_round_meta_after_ok_retally() {
    [[ "$TALLY_PLAN_REVIEW_STATUS" == "ok" ]] || return 0
    local round_dir="${_RESOLVED_ROUND_DIR:-}"
    if [[ -z "$round_dir" || ! -d "$round_dir" ]]; then
        emit_kv WARN "persist-retally-step3-env: retally round snapshot missing; skipped round-meta refresh"
        return 0
    fi
    if [[ -f "$DESIGN_TMPDIR/voting-tally.md" ]]; then
        cp -f "$DESIGN_TMPDIR/voting-tally.md" "$round_dir/voting-tally.md" 2>/dev/null || true
    fi
    "$PLUGIN_ROOT/scripts/write-design-round-meta.sh" --round-dir "$round_dir" 2>/dev/null || \
        emit_kv WARN "persist-retally-step3-env: round-meta refresh failed (non-fatal)"
}

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
                STEP3_REVIEW_LOOP_STATUS|POSTPLAN_RC|DEDUP_RC|PLAN_REVIEW_CONTINUE_REASON|FINAL_ROUND_NUM) continue ;;
                TALLY_PLAN_REVIEW_STATUS)
                    value="$TALLY_PLAN_REVIEW_STATUS"
                    saw_tally=1
                    ;;
                LOOP_STATUS)
                    value="$LOOP_STATUS"
                    saw_loop=1
                    ;;
                ACCEPTED_COUNT|IMPORTANT_ACCEPTED_COUNT|NIT_ACCEPTED_COUNT|NON_NIT_ACCEPTED_COUNT)
                    if [[ "$TALLY_PLAN_REVIEW_STATUS" == "tally-error" ]]; then
                        value=0
                    fi
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

_rollback_mav_round_state() {
    [[ "$TALLY_PLAN_REVIEW_STATUS" == "tally-error" ]] || return 0
    local count_file="$DESIGN_TMPDIR/review-round-count.txt" prior=0 round_num="${_RESOLVED_ROUND_NUM:-}"
    [[ -n "$round_num" ]] || return 0
    prior=$((round_num - 1))
    (( prior < 0 )) && prior=0
    printf '%s\n' "$prior" >"$count_file"
    rm -f "$DESIGN_TMPDIR/.step3-round-${round_num}.phase"
    rm -f "$DESIGN_TMPDIR/plan-pre-apply-round-${round_num}.txt"
}

_resolve_retally_round
_merge_retally_oos_accepted
_merge_retally_accepted_all
_clear_failed_retally_accepted
_rollback_mav_round_state
_clear_design_round_meta_on_tally_error
_rewrite_env_file "$DESIGN_TMPDIR/.step3-plan-review-result.env"
_rewrite_env_file "$DESIGN_TMPDIR/.step3-review-result.env"
_refresh_design_round_meta_after_ok_retally
exit 0
