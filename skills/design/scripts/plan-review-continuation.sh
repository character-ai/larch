#!/usr/bin/env bash
# plan-review-continuation.sh - Decide whether /design should auto-run another plan-review round.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-design-tmpdir.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"

fail() {
    printf 'plan-review-continuation.sh: %s\n' "$1" >&2
    exit 2
}

usage() {
    printf '%s\n' 'Usage: plan-review-continuation.sh --design-tmpdir DIR --approve-requested true|false' >&2
}

DESIGN_TMPDIR=""
APPROVE_REQUESTED=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"
            shift 2
            ;;
        --approve-requested)
            APPROVE_REQUESTED="${2:?--approve-requested requires a value}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            fail "unknown option: $1"
            ;;
    esac
done

[[ -n "$DESIGN_TMPDIR" ]] || { usage; fail '--design-tmpdir is required'; }
[[ "$APPROVE_REQUESTED" == true || "$APPROVE_REQUESTED" == false ]] || fail '--approve-requested must be true or false'
larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit 2
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"

kv_get() {
    local file="$1" key="$2"
    awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$file" 2>/dev/null || true
}

ROUND_CAP=5
REVIEW_ROUND_COUNT="$(tr -d '[:space:]' <"$DESIGN_TMPDIR/review-round-count.txt" 2>/dev/null || true)"
case "$REVIEW_ROUND_COUNT" in ''|*[!0-9]*) REVIEW_ROUND_COUNT=0 ;; esac
REVIEW_ROUND_COUNT=$((10#$REVIEW_ROUND_COUNT))

DEGRADED_PANEL="$(kv_get "$DESIGN_TMPDIR/.step3-review-result.env" DEGRADED_PANEL)"
case "$DEGRADED_PANEL" in 1|true) DEGRADED_PANEL=1 ;; *) DEGRADED_PANEL=0 ;; esac
TALLY_PLAN_REVIEW_STATUS="$(kv_get "$DESIGN_TMPDIR/.step3-review-result.env" TALLY_PLAN_REVIEW_STATUS)"
LOOP_STATUS="$(kv_get "$DESIGN_TMPDIR/.step3-review-result.env" LOOP_STATUS)"
PANEL_PRUNED_EMPTY="$(kv_get "$DESIGN_TMPDIR/.step3-review-result.env" PANEL_PRUNED_EMPTY)"

ACCEPTED_FILE="$DESIGN_TMPDIR/accepted-plan-findings.md"
PLAN_FILE="$DESIGN_TMPDIR/plan.txt"
RUN_PARAMS="$DESIGN_TMPDIR/run-params.json"

stats="$(
    python3 - "$ACCEPTED_FILE" "$PLAN_FILE" "$RUN_PARAMS" <<'PY'
import json
import re
import sys
from pathlib import Path

accepted_path, plan_path, run_params_path = map(Path, sys.argv[1:4])

try:
    text = accepted_path.read_text(encoding="utf-8", errors="replace")
except OSError:
    text = ""
blocks = [
    m.group(0)
    for m in re.finditer(r"(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)", text)
]

valid_severities = {"important", "latent", "nit"}
structured = bool(blocks)
severities = []
for block in blocks:
    m = re.search(r"(?mi)^- \*\*Severity\*\*:\s*([A-Za-z_-]+)\s*$", block)
    sev = (m.group(1).lower() if m else "")
    severities.append(sev)
    if sev not in valid_severities:
        structured = False

accepted = len(blocks)
nit = sum(1 for sev in severities if sev == "nit")
non_nit = max(0, accepted - nit)

def concern(block: str) -> str:
    m = re.search(r"(?ms)^- \*\*Concern\*\*:\s*(.*?)(?=^- \*\*|\Z)", block)
    return m.group(1).strip() if m else block

def fallback_high(block: str) -> bool:
    c = concern(block).lower()
    high_patterns = [
        r"\bcritical\b",
        r"\bhigh\b",
        r"data loss",
        r"security breach",
        r"\bbuild\b.*\bbreak",
        r"\bci\b.*\bbreak",
        r"\bregression\b",
        r"functional incorrectness",
        r"primary code path",
        r"missing required",
        r"violates? (a )?stated invariant",
    ]
    return any(re.search(p, c) for p in high_patterns)

if structured:
    high = sum(1 for sev in severities if sev == "important")
else:
    high = sum(1 for block in blocks if fallback_high(block))

try:
    plan_text = plan_path.read_text(encoding="utf-8", errors="replace")
except OSError:
    plan_text = ""
diff_lines = 0
for m in re.finditer(r"(?mi)^diff_lines:\s*([0-9]+)\s*$", plan_text):
    diff_lines = int(m.group(1))
plan_lines = len(plan_text.splitlines())

classification = "HARD"
try:
    data = json.loads(run_params_path.read_text(encoding="utf-8", errors="replace"))
    raw_classification = str(data.get("design_classification") or "").upper()
    classification = "SIMPLE" if raw_classification == "SIMPLE" else "HARD"
except Exception:
    classification = "HARD"
structural_large = classification == "HARD" or diff_lines > 500 or plan_lines > 120

for key, value in (
    ("ACCEPTED_COUNT", accepted),
    ("NIT_ACCEPTED_COUNT", nit),
    ("NON_NIT_ACCEPTED_COUNT", non_nit),
    ("HIGH_ACCEPTED_COUNT", high),
    ("STRUCTURAL_OR_LARGE_CHANGE", "true" if structural_large else "false"),
):
    print(f"{key}={value}")
PY
)"

ACCEPTED_COUNT=0
NIT_ACCEPTED_COUNT=0
NON_NIT_ACCEPTED_COUNT=0
HIGH_ACCEPTED_COUNT=0
STRUCTURAL_OR_LARGE_CHANGE=false
while IFS= read -r line || [[ -n "$line" ]]; do
    key="${line%%=*}"
    value="${line#*=}"
    case "$key" in
        ACCEPTED_COUNT|NIT_ACCEPTED_COUNT|NON_NIT_ACCEPTED_COUNT|HIGH_ACCEPTED_COUNT|STRUCTURAL_OR_LARGE_CHANGE)
            printf -v "$key" '%s' "$value"
            ;;
    esac
done <<<"$stats"

CONTINUE=false
REASON=small-clean
if [[ "$TALLY_PLAN_REVIEW_STATUS" == ok && "$LOOP_STATUS" == complete ]]; then
    DEGRADED_PANEL=0
fi
if [[ "$APPROVE_REQUESTED" == true ]]; then
    REASON=explicit-approve
elif (( REVIEW_ROUND_COUNT >= ROUND_CAP )); then
    REASON=cap-reached
elif [[ "$PANEL_PRUNED_EMPTY" == true ]]; then
    CONTINUE=true
    REASON=pruned-empty
elif (( DEGRADED_PANEL != 0 && ACCEPTED_COUNT > 0 )); then
    CONTINUE=true
    REASON=degraded-panel
elif (( HIGH_ACCEPTED_COUNT > 0 )); then
    CONTINUE=true
    REASON=high-accepted
elif (( NON_NIT_ACCEPTED_COUNT > 5 )); then
    CONTINUE=true
    REASON=non-nit-accepted
elif [[ "$STRUCTURAL_OR_LARGE_CHANGE" == true ]] && (( NON_NIT_ACCEPTED_COUNT > 0 && REVIEW_ROUND_COUNT < 2 )); then
    CONTINUE=true
    REASON=structural-or-large-change
fi

printf 'PLAN_REVIEW_CONTINUE=%s\n' "$CONTINUE"
printf 'PLAN_REVIEW_CONTINUE_REASON=%s\n' "$REASON"
printf 'REVIEW_ROUND_COUNT=%s\n' "$REVIEW_ROUND_COUNT"
printf 'REVIEW_ROUND_CAP=%s\n' "$ROUND_CAP"
printf 'ACCEPTED_COUNT=%s\n' "$ACCEPTED_COUNT"
printf 'NIT_ACCEPTED_COUNT=%s\n' "$NIT_ACCEPTED_COUNT"
printf 'NON_NIT_ACCEPTED_COUNT=%s\n' "$NON_NIT_ACCEPTED_COUNT"
printf 'HIGH_ACCEPTED_COUNT=%s\n' "$HIGH_ACCEPTED_COUNT"
printf 'DEGRADED_PANEL=%s\n' "$DEGRADED_PANEL"
printf 'STRUCTURAL_OR_LARGE_CHANGE=%s\n' "$STRUCTURAL_OR_LARGE_CHANGE"
