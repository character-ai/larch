#!/usr/bin/env bash
# record-implement-review-round-timing.sh — Deferred /implement review round timing row writer.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

warn() {
    larch_err "record-implement-review-round-timing.sh: WARNING: $*"
}

usage() {
    warn 'Usage: record-implement-review-round-timing.sh --implement-tmpdir PATH --round N --start-s S --end-s E'
}

IMPLEMENT_TMPDIR_ARG=""
ROUND_NUM=""
START_S=""
END_S=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir) IMPLEMENT_TMPDIR_ARG="${2:?--implement-tmpdir requires a value}"; shift 2 ;;
        --round) ROUND_NUM="${2:?--round requires a value}"; shift 2 ;;
        --start-s) START_S="${2:?--start-s requires a value}"; shift 2 ;;
        --end-s) END_S="${2:?--end-s requires a value}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) warn "unknown option: $1"; usage; exit 2 ;;
    esac
done

case "$ROUND_NUM" in ''|*[!0-9]*) warn '--round must be a non-negative integer'; exit 2 ;; esac
case "$START_S" in ''|*[!0-9]*) warn '--start-s must be a non-negative integer'; exit 2 ;; esac
case "$END_S" in ''|*[!0-9]*) warn '--end-s must be a non-negative integer'; exit 2 ;; esac
[[ -n "$IMPLEMENT_TMPDIR_ARG" && -d "$IMPLEMENT_TMPDIR_ARG" && ! -L "$IMPLEMENT_TMPDIR_ARG" ]] || { warn '--implement-tmpdir must name a directory'; exit 2; }

IMPLEMENT_TMPDIR="$(cd "$IMPLEMENT_TMPDIR_ARG" && pwd -P)"
round_dir="$IMPLEMENT_TMPDIR/round-$((10#$ROUND_NUM))"
accepted=""
rejected=""

env_get() {
    local file="$1" key="$2"
    awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$file" 2>/dev/null || true
}

if [[ -f "$round_dir/review-tally.env" ]]; then
    accepted=$(env_get "$round_dir/review-tally.env" ACCEPTED_COUNT)
    [[ -n "$accepted" ]] || accepted=$(env_get "$round_dir/review-tally.env" ACCEPTED)
    rejected=$(env_get "$round_dir/review-tally.env" REJECTED_COUNT)
    [[ -n "$rejected" ]] || rejected=$(env_get "$round_dir/review-tally.env" REJECTED)
fi
if [[ ! "$accepted" =~ ^[0-9]+$ ]]; then
    if [[ -s "$round_dir/accepted-findings.md" ]]; then
        accepted=$(grep -cE '^### FINDING_[0-9]+:' "$round_dir/accepted-findings.md" 2>/dev/null || true)
    else
        accepted=0
    fi
fi
if [[ ! "$rejected" =~ ^[0-9]+$ ]]; then
    if [[ -s "$round_dir/rejected-findings.md" ]]; then
        rejected=$(grep -cE '^([0-9]+:)?FINDING_[0-9]+_OUTCOME=rejected$' "$round_dir/rejected-findings.md" 2>/dev/null || true)
    else
        rejected=0
    fi
fi
if [[ ! "$rejected" =~ ^[0-9]+$ || "$rejected" -eq 0 ]]; then
    if [[ -s "$round_dir/review-summary.json" ]] && command -v jq >/dev/null 2>&1; then
        _json_rejected=$(jq -r '.rejected_count // .rejected // empty' "$round_dir/review-summary.json" 2>/dev/null || true)
        [[ "$_json_rejected" =~ ^[0-9]+$ ]] && rejected="$_json_rejected"
    fi
fi
[[ "$accepted" =~ ^[0-9]+$ ]] || accepted=0
[[ "$rejected" =~ ^[0-9]+$ ]] || rejected=0

export IMPLEMENT_TMPDIR
export LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"
export LARCH_TIMING_SKILL=implement
"$PLUGIN_ROOT/scripts/timing-ledger.sh" record-round \
    --skill implement \
    --step "Step 5 — code review" \
    --round "$((10#$ROUND_NUM))" \
    --start-s "$START_S" \
    --end-s "$END_S" \
    --accepted "$accepted" \
    --rejected "$rejected" || true
