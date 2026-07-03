#!/usr/bin/env bash
# Regression harness for /design Step 3 review-round cap handling.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SKILL_MD="$ROOT/skills/design/SKILL.md"
APPROVAL_GATES="$ROOT/skills/design/references/approval-gates.md"
CLI="$ROOT/python/cli.py"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

grep -Fq 'plan-review run' "$SKILL_MD" \
    || fail 'SKILL.md must invoke plan-review run'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
grep -Fq '`NEXT_ACTION=step3b-bypass` for all other bypass statuses — before jumping to Step 3b, run `design-step3-gate-b-bypass.sh`' "$SKILL_MD" \
    || fail 'SKILL missing NEXT_ACTION Gate-B-bypass prose'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
grep -Fq 'Covers cap-hit, `LOOP_STATUS=panel-failed`' "$SKILL_MD" \
    || fail 'SKILL missing panel-failed counter-consumption prose'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
grep -Fq 'MUST NOT persist when `TALLY_PLAN_REVIEW_STATUS=tally-error`' "$SKILL_MD" \
    || fail 'SKILL missing tally-error non-consumption prose'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq 'run_step3_review' "$ROOT/python/larch/review/plan_review.py" \
    || fail 'plan_review.py missing Step 3 run entry point'
grep -Fq 'run_step3_review' "$ROOT/python/larch/review/plan_review.py" \
    || fail 'plan_review.py missing Step 3 run entry point'
grep -Fq 'PLAN_REVIEW_CONTINUE_REASON=explicit-approve' "$SKILL_MD" \
    || fail 'SKILL missing explicit --per-round-approval continuation stop contract'
grep -Fq 'Do not jump directly to Step 3b from this post-apply resume branch' "$SKILL_MD" \
    || fail 'SKILL missing Gate B postapply resume continuation guard'
grep -Fq 'launcher-only Step 3 resume fence before launching the next review' "$SKILL_MD" \
    || fail 'SKILL missing launcher-only auto-continuation Step 3 resume contract'
# shellcheck disable=SC2016 # Markdown literal contains parameter syntax intentionally.
grep -Fq 'starting-round "$STEP3_RESUME_ROUND"' "$SKILL_MD" \
    || fail 'SKILL missing shared STEP3_RESUME_ROUND resume launch'
# shellcheck disable=SC2016 # Markdown literal contains parameter syntax intentionally.
if grep -Fq 'starting-round "${FINAL_ROUND_NUM:-${STEP3_REVIEW_ROUND_NUM:-$ROUND_NUM}}"' "$SKILL_MD"; then
    fail 'SKILL must not use inline fallback for Step 3 resume launch'
fi
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
grep -Fq 'Prompt-side Gate B apply runs only on loop bail-outs' "$APPROVAL_GATES" \
    || fail 'approval-gates missing loop-only Gate B branch'
# shellcheck disable=SC2016 # Markdown literal contains parameter syntax intentionally.
grep -Fq 'design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation' "$APPROVAL_GATES" \
    || fail 'approval-gates missing wrapper-owned continuation resume contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
if grep -Fq -- '--mode single' "$SKILL_MD" "$APPROVAL_GATES"; then
    fail 'SKILL/approval-gates must not retain legacy --mode single prose'
fi
grep -Fq 'plan-review continuation' "$ROOT/python/larch/review/plan_review_loop.py" \
    || fail 'plan_review.py missing native continuation entry point'

TMP_PARENT="${TMPDIR:-/tmp}"
if mkdir -p "${HOME}/.cache/larch/sessions" 2>/dev/null && [[ -w "${HOME}/.cache/larch/sessions" ]]; then
    TMP_PARENT="${HOME}/.cache/larch/sessions"
fi
TMPROOT="$(mktemp -d "${TMP_PARENT%/}/larch-step3-cap-test.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

write_common_inputs() {
    local dir="$1"
    mkdir -p "$dir"
    printf '{"schema_version":3,"partition_requested":false,"brainstorm_requested":false}\n' >"$dir/run-params.json"
    printf '# Plan\n\ndiff_lines: 1\n' >"$dir/plan.txt"
    printf 'feature\n' >"$dir/feature-description.txt"
}

write_loop_stub() {
    local dir="$1" body="$2"
    local stub="$dir/plan-review-loop-stub.sh"
    cat >"$stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
$body
EOF
    chmod +x "$stub"
    printf '%s\n' "$stub"
}

write_difficulty_record() {
    local dir="$1" tier="$2" escalations_json="$3"
    PYTHONPATH="$ROOT/python" python3 - "$dir" "$tier" "$escalations_json" <<'PY'
import json
import sys
from pathlib import Path

from larch.calibration import difficulty

dest = Path(sys.argv[1])
tier = difficulty.normalize_tier(sys.argv[2], difficulty.MODERATE)
escalations = tuple(json.loads(sys.argv[3]))
rating = difficulty.validate_rating_object(
    {
        "predicted_tier": tier,
        "confidence": "medium",
        "rationale": "test difficulty seed",
    }
)
record = difficulty.build_record(
    rater="test",
    rater_tool="harness",
    rater_model="stub",
    design_rating=rating,
    panel_tier=tier,
    round_cap=difficulty.tier_ceiling(tier),
    codex_model_role=difficulty.codex_review_model_role(tier),
    audit_evaluated=False,
    audit_upgrade=False,
    escalations=escalations,
    escalated_round=bool(escalations),
)
difficulty.write_record(dest / difficulty.DIFFICULTY_RECORD_BASENAME, record)
PY
}

run_driver() {
    local design_tmpdir="$1" stub="$2"
    env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
        RUN_STEP3_TEST_DH="$design_tmpdir" \
        RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" \
        python3 "$CLI" plan-review run \
        --design-tmpdir "$design_tmpdir"
}

echo "=== missing counter starts at round 1 ==="
D1="$TMPROOT/round1"
write_common_inputs "$D1"
run_driver "$D1" "$(write_loop_stub "$D1" 'exit 0')" >/dev/null
grep -Fq 'STEP3_REVIEW_CAP_REACHED=false' "$D1/.step3-review-cap.env" || fail 'expected cap false on first entry'
grep -Fq 'STEP3_REVIEW_ROUND_NUM=1' "$D1/.step3-review-cap.env" || fail 'expected first entry round number 1'

echo "=== cap reached bypasses loop ==="
D2="$TMPROOT/cap-reached"
write_common_inputs "$D2"
printf '2\n' >"$D2/review-round-count.txt"
printf 'stale accepted\n' >"$D2/accepted-plan-findings.md"
printf 'stale tally\n' >"$D2/voting-tally.md"
stub="$(write_loop_stub "$D2" 'exit 97')"
driver_out=$(run_driver "$D2" "$stub")
printf '%s\n' "$driver_out" | grep -q 'NEXT_ACTION=step3b-bypass' || fail 'expected cap-reached NEXT_ACTION'
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=cap-reached' || fail 'expected cap-reached loop status'
printf '%s\n' "$driver_out" | grep -q 'TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached' || fail 'expected skipped-cap-reached tally status'
printf '%s\n' "$driver_out" | grep -q 'cap reached; skipping' || fail 'expected cap-reached skip breadcrumb'
[[ "$(cat "$D2/review-round-count.txt")" == "2" ]] || fail 'cap-reached path must leave counter unchanged'
[[ -f "$D2/.completed/step-3" ]] || fail 'cap-reached path must write .completed/step-3 sentinel'
[[ ! -e "$D2/accepted-plan-findings.md" ]] || fail 'cap-reached path must clear stale accepted findings'
[[ ! -e "$D2/voting-tally.md" ]] || fail 'cap-reached path must clear stale voting tally'

echo "=== panel-failed consumes the pending round ==="
D3="$TMPROOT/panel-failed"
write_common_inputs "$D3"
printf '1\n' >"$D3/review-round-count.txt"
stub="$(write_loop_stub "$D3" "printf 'LOOP_STATUS=panel-failed\nACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=panel-failed\nAGGREGATOR_STATUS=skipped\nVOTING_TALLY_FILE=\n'; exit 1")"
driver_out=$(run_driver "$D3" "$stub")
printf '%s\n' "$driver_out" | grep -q 'NEXT_ACTION=step3b-bypass' || fail 'expected panel-failed NEXT_ACTION'
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=panel-failed' || fail 'expected panel-failed loop status'
[[ "$(cat "$D3/review-round-count.txt")" == "2" ]] || fail 'panel-failed path should consume pending round'

echo "=== unrecognized loop status still consumes the pending round ==="
D3B="$TMPROOT/unrecognized-status"
write_common_inputs "$D3B"
printf '1\n' >"$D3B/review-round-count.txt"
stub="$(write_loop_stub "$D3B" "printf 'LOOP_STATUS=weird-status\n'; exit 1")"
driver_out=$(run_driver "$D3B" "$stub")
printf '%s\n' "$driver_out" | grep -q 'NEXT_ACTION=step3b-bypass' || fail 'invalid loop status should map NEXT_ACTION to bypass'
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=panel-failed' || fail 'invalid loop status should be normalized to panel-failed'
[[ "$(cat "$D3B/review-round-count.txt")" == "2" ]] || fail 'unrecognized post-launch status should keep pending round consumed'

echo "=== removed passive-summary statuses normalize to panel-failed ==="
DP="$TMPROOT/removed-passive-summary"
write_common_inputs "$DP"
mkdir -p "$DP/plan-review/round-1" "$DP/plan-review/round-2"
printf 'stale\n' >"$DP/plan-review/round-1/stale.txt"
printf 'stale\n' >"$DP/plan-review/round-2/stale.txt"
stub="$(write_loop_stub "$DP" "mkdir -p \"$DP/plan-review/round-1\"; printf 'fresh\n' >\"$DP/plan-review/round-1/new.txt\"; printf 'LOOP_STATUS=converged\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
driver_out=$(run_driver "$DP" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=panel-failed' || fail 'removed converged status should normalize to panel-failed'
printf '%s\n' "$driver_out" | grep -q 'missing or invalid LOOP_STATUS' || fail 'removed converged status should emit invalid-status warning'
[[ "$(cat "$DP/review-round-count.txt")" == "1" ]] || fail 'removed converged status should still consume round 1'
[[ -f "$DP/plan-review/round-1/new.txt" ]] || fail 'fresh round-1 artifact missing after first entry'
[[ ! -e "$DP/plan-review/round-1/stale.txt" ]] || fail 'stale round-1 artifact should be cleaned before launch'
[[ -e "$DP/plan-review/round-2/stale.txt" ]] || fail 'inactive round-2 artifact should be preserved before launch'
stub="$(write_loop_stub "$DP" "mkdir -p \"$DP/plan-review/round-2\"; printf 'fresh\n' >\"$DP/plan-review/round-2/new.txt\"; printf 'LOOP_STATUS=cap-hit\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
driver_out=$(run_driver "$DP" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=panel-failed' || fail 'removed cap-hit status should normalize to panel-failed'
printf '%s\n' "$driver_out" | grep -q 'missing or invalid LOOP_STATUS' || fail 'removed cap-hit status should emit invalid-status warning'
[[ "$(cat "$DP/review-round-count.txt")" == "2" ]] || fail 'removed cap-hit status should still consume round 2'
[[ -f "$DP/plan-review/round-2/new.txt" ]] || fail 'fresh round-2 artifact missing after second entry'

echo "=== hard path advances round 2 after successful round-1 snapshot ==="

echo "=== tally-error does not consume the pending round ==="
D4="$TMPROOT/tally-error"
write_common_inputs "$D4"
printf '1\n' >"$D4/review-round-count.txt"
stub="$(write_loop_stub "$D4" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=tally-error\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 2")"
driver_out=$(run_driver "$D4" "$stub")
printf '%s\n' "$driver_out" | grep -q 'NEXT_ACTION=step3b-bypass' || fail 'expected tally-error NEXT_ACTION'
printf '%s\n' "$driver_out" | grep -q 'TALLY_PLAN_REVIEW_STATUS=tally-error' || fail 'expected tally-error tally status'
[[ "$(cat "$D4/review-round-count.txt")" == "1" ]] || fail 'tally-error path must not consume pending round'

echo "=== degraded-empty-collector does not consume the pending round ==="
D4B="$TMPROOT/degraded-empty-collector"
write_common_inputs "$D4B"
printf '1\n' >"$D4B/review-round-count.txt"
stub="$(write_loop_stub "$D4B" "printf 'LOOP_STATUS=degraded-empty-collector\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 1")"
driver_out=$(run_driver "$D4B" "$stub")
printf '%s\n' "$driver_out" | grep -q 'NEXT_ACTION=step3b-bypass' || fail 'expected degraded-empty-collector NEXT_ACTION'
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=degraded-empty-collector' || fail 'expected degraded-empty-collector loop status'
[[ "$(cat "$D4B/review-round-count.txt")" == "1" ]] || fail 'degraded-empty-collector path must not consume pending round'

echo "=== hard cap blocks the third review round ==="
D5="$TMPROOT/hard-cap"
write_common_inputs "$D5"
printf '2\n' >"$D5/review-round-count.txt"
stub="$(write_loop_stub "$D5" 'exit 97')"
run_driver "$D5" "$stub" >/dev/null
driver_out=$(run_driver "$D5" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=cap-reached' || fail 'expected cap-reached loop status'

echo "=== HARD round 3 reachable with recorded escalation ==="
D6="$TMPROOT/hard-round-3-reachable"
write_common_inputs "$D6"
printf '2\n' >"$D6/review-round-count.txt"
write_difficulty_record "$D6" HARD '[{"round":3,"from_tier":"MODERATE","to_tier":"HARD","trigger":"escalated-high-accepted"}]'
stub="$(write_loop_stub "$D6" "round_num=''; while [[ \$# -gt 0 ]]; do case \"\$1\" in --round-num) round_num=\"\${2:?}\"; shift 2 ;; *) shift ;; esac; done; printf '%s\n' \"\$round_num\" >\"$D6/launched-round.txt\"; [[ \"\$round_num\" == '3' ]] || exit 98; mkdir -p \"$D6/plan-review/round-\$round_num\"; printf 'launched\n' >\"$D6/plan-review/round-\$round_num/launched.txt\"; printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=%s\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n' \"\$round_num\"")"
driver_out=$(run_driver "$D6" "$stub")
[[ "$(cat "$D6/launched-round.txt")" == "3" ]] || fail 'HARD escalation should dispatch round 3'
[[ "$(cat "$D6/review-round-count.txt")" == "3" ]] || fail 'HARD escalation should consume round 3'
[[ -f "$D6/plan-review/round-3/launched.txt" ]] || fail 'HARD escalation should leave round-3 launch artifact'
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=cap-reached' && fail 'HARD escalation should not stop at cap before launching round 3'

echo "=== Gate-C authorized cap blocks HARD round 3 without escalation ==="
DGATE="$TMPROOT/gate-c-authorized-cap"
write_common_inputs "$DGATE"
printf '2\n' >"$DGATE/review-round-count.txt"
write_difficulty_record "$DGATE" HARD '[]'
stub="$(write_loop_stub "$DGATE" "printf 'launched\n' >\"$DGATE/round-3-should-not-launch.txt\"; exit 97")"
driver_out=$(run_driver "$DGATE" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=cap-reached' || fail 'Gate-C cap should stop at round 2 without escalation'
[[ "$(cat "$DGATE/review-round-count.txt")" == "2" ]] || fail 'Gate-C cap should leave counter at 2'
[[ ! -e "$DGATE/round-3-should-not-launch.txt" ]] || fail 'Gate-C cap should not launch round 3'
[[ ! -e "$DGATE/plan-review/round-3" ]] || fail 'Gate-C cap should not create round-3 artifacts'

run_continuation() {
    local design_tmpdir="$1" approve="$2"
    CLAUDE_PLUGIN_ROOT="$ROOT" python3 "$CLI" plan-review continuation --design-tmpdir "$design_tmpdir" --approve-requested "$approve"
}

echo "=== continuation helper stops before cap cleanup ==="
DCAP="$TMPROOT/continuation-cap"
write_common_inputs "$DCAP"
printf '2\n' >"$DCAP/review-round-count.txt"
cat >"$DCAP/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Important
- **Severity**: important
- **Concern**: important issue
EOF
cont_out=$(run_continuation "$DCAP" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'continuation cap should stop'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=cap-reached$' || fail 'continuation cap reason missing'

echo "=== continuation helper honors explicit approve ==="
DAPP="$TMPROOT/continuation-approve"
write_common_inputs "$DAPP"
printf '1\n' >"$DAPP/review-round-count.txt"
cp "$DCAP/accepted-plan-findings.md" "$DAPP/accepted-plan-findings.md"
cont_out=$(run_continuation "$DAPP" true)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'explicit approve should stop auto-continuation'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=explicit-approve$' || fail 'explicit approve reason missing'

echo "=== continuation helper converges pruned-empty below cap (#5255) ==="
DPRUNE="$TMPROOT/continuation-pruned-empty"
write_common_inputs "$DPRUNE"
printf '1\n' >"$DPRUNE/review-round-count.txt"
: >"$DPRUNE/accepted-plan-findings.md"
printf 'PANEL_PRUNED_EMPTY=true\nDEGRADED_PANEL=0\nLOOP_STATUS=complete\nTALLY_PLAN_REVIEW_STATUS=skipped-pruned-empty\n' >"$DPRUNE/.step3-review-result.env"
cont_out=$(run_continuation "$DPRUNE" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'pruned-empty below cap should converge'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=converged-pruned-empty$' || fail 'converged-pruned-empty reason missing'

echo "=== continuation helper stops pruned-empty at cap ==="
DPRUNE_CAP="$TMPROOT/continuation-pruned-empty-cap"
write_common_inputs "$DPRUNE_CAP"
printf '2\n' >"$DPRUNE_CAP/review-round-count.txt"
: >"$DPRUNE_CAP/accepted-plan-findings.md"
printf 'PANEL_PRUNED_EMPTY=true\nDEGRADED_PANEL=0\nLOOP_STATUS=complete\nTALLY_PLAN_REVIEW_STATUS=skipped-pruned-empty\n' >"$DPRUNE_CAP/.step3-review-result.env"
cont_out=$(run_continuation "$DPRUNE_CAP" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'pruned-empty at cap should stop'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=cap-reached$' || fail 'pruned-empty at cap reason missing'

echo "=== continuation helper recomputes high fallback from disk ==="
DHIGH="$TMPROOT/continuation-high"
write_common_inputs "$DHIGH"
printf '1\n' >"$DHIGH/review-round-count.txt"
cat >"$DHIGH/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Missing contract
- **Concern**: Missing required documentation contract violates a stated invariant in the plan.
EOF
cont_out=$(run_continuation "$DHIGH" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'high fallback should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=high-accepted$' || fail 'high fallback reason missing'

echo "=== continuation helper recognizes structured important severity ==="
DIMP="$TMPROOT/continuation-structured-important"
write_common_inputs "$DIMP"
printf '1\n' >"$DIMP/review-round-count.txt"
cat >"$DIMP/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Important structured
- **Severity**: important
- **Concern**: structured important issue
EOF
cont_out=$(run_continuation "$DIMP" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'structured important should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=high-accepted$' || fail 'structured important reason missing'

echo "=== continuation helper recognizes structured blocking severity ==="
DBLOCK="$TMPROOT/continuation-structured-blocking"
write_common_inputs "$DBLOCK"
printf '1\n' >"$DBLOCK/review-round-count.txt"
cat >"$DBLOCK/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Blocking structured
- **Severity**: blocking
- **Concern**: neutral wording with no high fallback keywords
EOF
cont_out=$(run_continuation "$DBLOCK" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'structured blocking should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=high-accepted$' || fail 'structured blocking reason missing'
printf '%s\n' "$cont_out" | grep -q '^HIGH_ACCEPTED_COUNT=1$' || fail 'structured blocking should count as high'

echo "=== continuation helper escalates two new high findings to HARD ==="
DESC="$TMPROOT/continuation-escalates-high"
write_common_inputs "$DESC"
printf '2\n' >"$DESC/review-round-count.txt"
write_difficulty_record "$DESC" MODERATE '[]'
cat >"$DESC/.step3-review-result.env" <<'EOF'
LOOP_STATUS=complete
TALLY_PLAN_REVIEW_STATUS=ok
DEGRADED_PANEL=0
EOF
cat >"$DESC/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Important structured one
- **Severity**: important
- **Concern**: first new issue

### FINDING_2: Blocking structured two
- **Severity**: blocking
- **Concern**: second new issue
EOF
cont_out=$(run_continuation "$DESC" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'two new high findings should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=escalated-high-accepted$' || fail 'two new high findings should escalate'
printf '%s\n' "$cont_out" | grep -q '^REVIEW_ROUND_CAP=3$' || fail 'escalation should raise cap to 3'
printf '%s\n' "$cont_out" | grep -q '^PANEL_TIER=HARD$' || fail 'escalation should set panel tier HARD'
if ! PYTHONPATH="$ROOT/python" python3 - "$DESC/difficulty-rating.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
escalations = data.get("escalations")
if not isinstance(escalations, list) or not escalations:
    raise SystemExit(1)
if data.get("panel_tier") != "HARD" or data.get("round_cap") != 3:
    raise SystemExit(1)
PY
then
    fail 'escalation should append difficulty record entry'
fi

echo "=== continuation helper stops on small clean round ==="
DSMALL="$TMPROOT/continuation-small-clean"
write_common_inputs "$DSMALL"
printf '1\n' >"$DSMALL/review-round-count.txt"
cat >"$DSMALL/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Latent cleanup
- **Severity**: latent
- **Concern**: small cleanup
EOF
cont_out=$(run_continuation "$DSMALL" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'small clean round should stop'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=small-clean$' || fail 'small clean reason missing'

echo "=== continuation helper continues on many non-nit findings ==="
DNONNIT="$TMPROOT/continuation-non-nit"
write_common_inputs "$DNONNIT"
printf '1\n' >"$DNONNIT/review-round-count.txt"
: >"$DNONNIT/accepted-plan-findings.md"
for n in 1 2 3 4 5 6; do
    cat >>"$DNONNIT/accepted-plan-findings.md" <<EOF
### FINDING_${n}: Latent ${n}
- **Severity**: latent
- **Concern**: cleanup ${n}

EOF
done
cont_out=$(run_continuation "$DNONNIT" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'many non-nit findings should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=non-nit-accepted$' || fail 'non-nit reason missing'


echo "=== continuation helper stops on degraded zero-findings without ballot-items-lost ==="
DDEG="$TMPROOT/continuation-degraded-zero"
write_common_inputs "$DDEG"
printf '1\n' >"$DDEG/review-round-count.txt"
: >"$DDEG/accepted-plan-findings.md"
printf 'DEGRADED_PANEL=1\n' >"$DDEG/.step3-review-result.env"
cont_out=$(run_continuation "$DDEG" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'degraded zero-findings round should stop'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=small-clean$' || fail 'degraded zero-findings reason missing'

echo "=== continuation helper continues on ballot-items-lost terminal shape ==="
DBIL_CONT="$TMPROOT/continuation-ballot-items-lost"
write_common_inputs "$DBIL_CONT"
printf '1\n' >"$DBIL_CONT/review-round-count.txt"
: >"$DBIL_CONT/accepted-plan-findings.md"
cat >"$DBIL_CONT/.step3-review-result.env" <<'EOF'
DEGRADED_PANEL=1
TALLY_PLAN_REVIEW_STATUS=ok
LOOP_STATUS=zero-findings-degraded-panel
REASON=ballot-items-lost
EOF
cont_out=$(run_continuation "$DBIL_CONT" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'ballot-items-lost should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=ballot-items-lost$' || fail 'ballot-items-lost reason missing'

echo "=== continuation helper continues ballot-items-lost under explicit approve ==="
DBIL_APPROVE="$TMPROOT/continuation-ballot-items-lost-approve"
write_common_inputs "$DBIL_APPROVE"
printf '1\n' >"$DBIL_APPROVE/review-round-count.txt"
: >"$DBIL_APPROVE/accepted-plan-findings.md"
cat >"$DBIL_APPROVE/.step3-review-result.env" <<'EOF'
DEGRADED_PANEL=1
TALLY_PLAN_REVIEW_STATUS=ok
LOOP_STATUS=zero-findings-degraded-panel
REASON=ballot-items-lost
EOF
cont_out=$(run_continuation "$DBIL_APPROVE" true)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'ballot-items-lost with approve should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=ballot-items-lost$' || fail 'ballot-items-lost with approve reason missing'

echo "=== continuation helper continues ballot-items-lost with snapshot-failed suffix ==="
DBIL_SUFFIX="$TMPROOT/continuation-ballot-items-lost-suffix"
write_common_inputs "$DBIL_SUFFIX"
printf '1\n' >"$DBIL_SUFFIX/review-round-count.txt"
: >"$DBIL_SUFFIX/accepted-plan-findings.md"
cat >"$DBIL_SUFFIX/.step3-review-result.env" <<'EOF'
DEGRADED_PANEL=1
TALLY_PLAN_REVIEW_STATUS=ok
LOOP_STATUS=zero-findings-degraded-panel
REASON=ballot-items-lost,snapshot-failed
EOF
cont_out=$(run_continuation "$DBIL_SUFFIX" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'ballot-items-lost suffix should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=ballot-items-lost$' || fail 'ballot-items-lost suffix reason missing'

echo "=== continuation helper negative: degraded zero without ballot-items-lost reason ==="
DDEG_NEG="$TMPROOT/continuation-degraded-no-ballot-reason"
write_common_inputs "$DDEG_NEG"
printf '1\n' >"$DDEG_NEG/review-round-count.txt"
: >"$DDEG_NEG/accepted-plan-findings.md"
cat >"$DDEG_NEG/.step3-review-result.env" <<'EOF'
DEGRADED_PANEL=1
TALLY_PLAN_REVIEW_STATUS=ok
LOOP_STATUS=zero-findings-degraded-panel
REASON=zero-findings-degraded-panel
EOF
cont_out=$(run_continuation "$DDEG_NEG" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'zero-findings-degraded-panel without ballot-items-lost should stop'

echo "=== continuation helper ignores stale degraded flag after successful retally ==="
DDEG_STALE="$TMPROOT/continuation-degraded-stale-retally"
write_common_inputs "$DDEG_STALE"
printf '1\n' >"$DDEG_STALE/review-round-count.txt"
: >"$DDEG_STALE/accepted-plan-findings.md"
cat >"$DDEG_STALE/.step3-review-result.env" <<'EOF'
DEGRADED_PANEL=1
TALLY_PLAN_REVIEW_STATUS=ok
LOOP_STATUS=complete
EOF
cont_out=$(run_continuation "$DDEG_STALE" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'successful retally stale degraded should stop'
printf '%s\n' "$cont_out" | grep -q '^DEGRADED_PANEL=0$' || fail 'successful retally should clear degraded output'

echo "=== chained continuation launches second review and preserves round-1 artifacts ==="
DCHAIN="$TMPROOT/continuation-chain"
write_common_inputs "$DCHAIN"
# Use approve_requested=true so the second run returns per-round-approval-required
# after launching round 2, without writing .completed/step-3.5
printf '{"schema_version":3,"partition_requested":false,"brainstorm_requested":false,"approve_requested":true}\n' >"$DCHAIN/run-params.json"
chain_stub="$DCHAIN/chain-loop-stub.sh"
cat >"$chain_stub" <<'STUBEOF'
#!/usr/bin/env bash
set -euo pipefail
round_num=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --round-num) round_num="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
mkdir -p "${DESIGN_TMPDIR:?}/plan-review/round-${round_num}"
printf 'launched\n' >"${DESIGN_TMPDIR}/plan-review/round-${round_num}/launched.txt"
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=1\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=%s\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n' "$round_num"
STUBEOF
chmod +x "$chain_stub"
run_driver "$DCHAIN" "$chain_stub" >/dev/null
printf 'prior round artifact\n' >"$DCHAIN/plan-review/round-1/keep.txt"
cat >"$DCHAIN/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Important
- **Severity**: important
- **Concern**: second review needed
EOF
cont_out=$(run_continuation "$DCHAIN" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'chain first continuation should continue'
state_out=$(CLAUDE_PLUGIN_ROOT="$ROOT" python3 "$CLI" plan-review step3-state --design-tmpdir "$DCHAIN" --auto-continuation-entry)
printf '%s\n' "$state_out" | grep -q '^STEP3_STATE=auto-continuation-entry$' || fail 'chain auto-continuation state missing'
printf 'round1 applied plan\n' >"$DCHAIN/plan-after-round-1.txt"
run_driver "$DCHAIN" "$chain_stub" >/dev/null
[[ "$(cat "$DCHAIN/review-round-count.txt")" == "2" ]] || fail 'chain second review should consume round 2'
[[ -f "$DCHAIN/plan-review/round-1/keep.txt" ]] || fail 'chain should preserve prior round artifact'
[[ -f "$DCHAIN/plan-review/round-2/launched.txt" ]] || fail 'chain should launch second review round'
[[ ! -f "$DCHAIN/.completed/step-3.5" ]] || fail 'chain should defer Gate C by not writing step-3.5'

echo "PASS: test-step3-review-cap.sh"
