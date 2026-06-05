#!/usr/bin/env bash
# record-plan-review-round-timing.sh — Deferred /design plan-review round timing row writer.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

warn() {
    larch_err "record-plan-review-round-timing.sh: WARNING: $*"
}

usage() {
    warn 'Usage: record-plan-review-round-timing.sh --design-tmpdir PATH --round N --start-s S --end-s E'
}

DESIGN_TMPDIR_ARG=""
ROUND_NUM=""
START_S=""
END_S=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR_ARG="${2:?--design-tmpdir requires a value}"; shift 2 ;;
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
[[ -n "$DESIGN_TMPDIR_ARG" && -d "$DESIGN_TMPDIR_ARG" && ! -L "$DESIGN_TMPDIR_ARG" ]] || { warn '--design-tmpdir must name a directory'; exit 2; }

DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
round_decimal="$((10#$ROUND_NUM))"
artifact_root="$DESIGN_TMPDIR"
round_artifact_root="$DESIGN_TMPDIR/plan-review/round-${round_decimal}"
session_has_tallies=false
for _tally_file in accepted-plan-findings.md rejected-findings.md voting-tally.md; do
    if [[ -s "$DESIGN_TMPDIR/$_tally_file" ]]; then
        session_has_tallies=true
        break
    fi
done
if [[ "$session_has_tallies" != true && -d "$round_artifact_root" && ! -L "$round_artifact_root" ]]; then
    artifact_root="$round_artifact_root"
fi
accepted=0
rejected=0
oos=0
if [[ -s "$artifact_root/accepted-plan-findings.md" ]]; then
    accepted=$(grep -cE '^### FINDING_[0-9]+:' "$artifact_root/accepted-plan-findings.md" 2>/dev/null || true)
fi
if [[ -s "$artifact_root/rejected-findings.md" ]]; then
    rejected=$(grep -cE '^### \[Plan Review\] FINDING_[0-9]+' "$artifact_root/rejected-findings.md" 2>/dev/null || true)
fi
if [[ -s "$artifact_root/voting-tally.md" ]]; then
    oos=$(awk -F'|' '
        /^## Findings/ { in_findings=1; next }
        /^## / && in_findings { in_findings=0 }
        in_findings && NF >= 7 {
            item=$2; result=$7
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", item)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", result)
            if (result == "" || result ~ /^-+$/) {
                result=$NF
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", result)
            }
            if (item ~ /^OOS_[0-9]+$/ && result == "accepted") c++
        }
        END { print c + 0 }
    ' "$artifact_root/voting-tally.md")
fi
[[ "$accepted" =~ ^[0-9]+$ ]] || accepted=0
[[ "$rejected" =~ ^[0-9]+$ ]] || rejected=0
[[ "$oos" =~ ^[0-9]+$ ]] || oos=0

export DESIGN_TMPDIR
export LARCH_TIMING_LEDGER="$DESIGN_TMPDIR/timing-ledger.tsv"
export LARCH_TIMING_SKILL=design
ledger="$DESIGN_TMPDIR/timing-ledger.tsv"
step_label="design Step 3 — plan review"
if [[ -f "$ledger" ]]; then
    if awk -F '\t' -v r="$round_decimal" -v s="$START_S" -v e="$END_S" -v step="$step_label" \
        -v a="$accepted" -v rej="$rejected" -v o="$oos" \
        '$2 == "round" && $4 == "design" && $5 == step && $6 == r && $7 == s && $8 == e && $10 == a && $11 == rej && $12 == o { found=1 } END { exit !found }' \
        "$ledger" 2>/dev/null; then
        exit 0
    fi
fi
"$PLUGIN_ROOT/scripts/timing-ledger.sh" record-round \
    --skill design \
    --step "$step_label" \
    --round "$round_decimal" \
    --start-s "$START_S" \
    --end-s "$END_S" \
    --accepted "$accepted" \
    --rejected "$rejected" \
    --oos "$oos" || true
if [[ -f "$ledger" ]] && awk -F '\t' -v r="$round_decimal" -v s="$START_S" -v e="$END_S" -v step="$step_label" \
    '$2 == "round" && $4 == "design" && $5 == step && $6 == r && $7 == s && $8 == e { found=1 } END { exit !found }' \
    "$ledger" 2>/dev/null; then
    exit 0
fi
exit 1
