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
    warn 'Usage: record-implement-review-round-timing.sh --implement-tmpdir PATH --round N --start-s S --end-s E [--accepted N --rejected N]'
}

IMPLEMENT_TMPDIR_ARG=""
ROUND_NUM=""
START_S=""
END_S=""
ACCEPTED_ARG=""
REJECTED_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir) IMPLEMENT_TMPDIR_ARG="${2:?--implement-tmpdir requires a value}"; shift 2 ;;
        --round) ROUND_NUM="${2:?--round requires a value}"; shift 2 ;;
        --start-s) START_S="${2:?--start-s requires a value}"; shift 2 ;;
        --end-s) END_S="${2:?--end-s requires a value}"; shift 2 ;;
        --accepted) ACCEPTED_ARG="${2:?--accepted requires a value}"; shift 2 ;;
        --rejected) REJECTED_ARG="${2:?--rejected requires a value}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) warn "unknown option: $1"; usage; exit 2 ;;
    esac
done

case "$ROUND_NUM" in ''|*[!0-9]*) warn '--round must be a non-negative integer'; exit 2 ;; esac
case "$START_S" in ''|*[!0-9]*) warn '--start-s must be a non-negative integer'; exit 2 ;; esac
case "$END_S" in ''|*[!0-9]*) warn '--end-s must be a non-negative integer'; exit 2 ;; esac
if [[ -n "$ACCEPTED_ARG" && ! "$ACCEPTED_ARG" =~ ^[0-9]+$ ]]; then
    warn '--accepted must be a non-negative integer'
    exit 2
fi
if [[ -n "$REJECTED_ARG" && ! "$REJECTED_ARG" =~ ^[0-9]+$ ]]; then
    warn '--rejected must be a non-negative integer'
    exit 2
fi
[[ -n "$IMPLEMENT_TMPDIR_ARG" && -d "$IMPLEMENT_TMPDIR_ARG" && ! -L "$IMPLEMENT_TMPDIR_ARG" ]] || { warn '--implement-tmpdir must name a directory'; exit 2; }

IMPLEMENT_TMPDIR="$(cd "$IMPLEMENT_TMPDIR_ARG" && pwd -P)"
round_dir="$IMPLEMENT_TMPDIR/round-$((10#$ROUND_NUM))"
accepted=""
rejected=""

env_get() {
    local file="$1" key="$2"
    awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$file" 2>/dev/null || true
}

if [[ -n "$ACCEPTED_ARG" ]]; then
    accepted="$ACCEPTED_ARG"
fi
if [[ -n "$REJECTED_ARG" ]]; then
    rejected="$REJECTED_ARG"
fi
if [[ -z "$accepted$rejected" && -f "$round_dir/review-tally.env" ]]; then
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
    fi
fi
if [[ ! "$rejected" =~ ^[0-9]+$ ]]; then
    if [[ -s "$round_dir/review-summary.json" ]] && command -v jq >/dev/null 2>&1; then
        _json_rejected=$(jq -r '.rejected_count // .rejected // empty' "$round_dir/review-summary.json" 2>/dev/null || true)
        [[ "$_json_rejected" =~ ^[0-9]+$ ]] && rejected="$_json_rejected"
    fi
fi
[[ "$accepted" =~ ^[0-9]+$ ]] || accepted=0
[[ "$rejected" =~ ^[0-9]+$ ]] || rejected=0

ledger="$IMPLEMENT_TMPDIR/timing-ledger.tsv"
round_decimal="$((10#$ROUND_NUM))"
step_label="Step 5 — code review"
if [[ -f "$ledger" ]]; then
    if awk -F '\t' -v r="$round_decimal" -v s="$START_S" -v e="$END_S" -v step="$step_label" \
        '$2 == "round" && $4 == "implement" && $5 == step && $6 == r && $7 == s && $8 == e { found=1 } END { exit !found }' \
        "$ledger" 2>/dev/null; then
        exit 0
    fi
fi

export IMPLEMENT_TMPDIR
export LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"
export LARCH_TIMING_SKILL=implement
python3 "$PLUGIN_ROOT/python/cli.py" timing record-round \
    --skill implement \
    --step "$step_label" \
    --round "$round_decimal" \
    --start-s "$START_S" \
    --end-s "$END_S" \
    --accepted "$accepted" \
    --rejected "$rejected" || true
if [[ -f "$ledger" ]] && awk -F '\t' -v r="$round_decimal" -v s="$START_S" -v e="$END_S" -v step="$step_label" \
    '$2 == "round" && $4 == "implement" && $5 == step && $6 == r && $7 == s && $8 == e { found=1 } END { exit !found }' \
    "$ledger" 2>/dev/null; then
    exit 0
fi
exit 1
