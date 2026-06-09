#!/usr/bin/env bash
# Regression harness for /design Step 3 review-round cap handling.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SKILL_MD="$ROOT/skills/design/SKILL.md"
LAUNCHER="$ROOT/skills/design/scripts/run-step3-review.sh"
CONTINUATION="$ROOT/skills/design/scripts/plan-review-continuation.sh"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

grep -Fq 'run-step3-review.sh' "$SKILL_MD" \
    || fail 'SKILL.md must invoke run-step3-review.sh'
grep -Fq 'The Step 3.5 continuation block below is bypassed on this path.' "$SKILL_MD" \
    || fail 'SKILL missing explicit Step 3.5 bypass prose'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
grep -Fq 'including `LOOP_STATUS=panel-failed`' "$SKILL_MD" \
    || fail 'SKILL missing panel-failed counter-consumption prose'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
grep -Fq 'MUST NOT persist when `TALLY_PLAN_REVIEW_STATUS=tally-error`' "$SKILL_MD" \
    || fail 'SKILL missing tally-error non-consumption prose'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq 'review-round cap (${_round_cap}) reached for ${_tier}' "$ROOT/skills/design/scripts/run-step3-review.sh" \
    || fail 'run-step3-review.sh missing Step 3 cap breadcrumb emit'
grep -Fq 'refusing to clean symlinked plan-review directory' "$ROOT/skills/design/scripts/run-step3-review.sh" \
    || fail 'run-step3-review.sh missing symlinked plan-review cleanup warning'
grep -Fq 'PLAN_REVIEW_CONTINUE_REASON=explicit-approve' "$SKILL_MD" \
    || fail 'SKILL missing explicit --per-round-approval continuation stop contract'
grep -Fq 'Do not jump directly to Step 3b from this post-apply resume branch' "$SKILL_MD" \
    || fail 'SKILL missing Gate B postapply resume continuation guard'
grep -Fq 'snapshot-plan-round.sh write-after' "$SKILL_MD" \
    || fail 'SKILL missing Gate B round snapshot handoff'
grep -Fq 'Step 3 prelude before launching the next review' "$SKILL_MD" \
    || fail 'SKILL missing auto-continuation Step 3 prelude contract'
[[ -x "$CONTINUATION" ]] || fail 'plan-review-continuation.sh must be executable'

TMP_PARENT="${TMPDIR:-/tmp}"
if mkdir -p "${HOME}/.cache/larch/sessions" 2>/dev/null && [[ -w "${HOME}/.cache/larch/sessions" ]]; then
    TMP_PARENT="${HOME}/.cache/larch/sessions"
fi
TMPROOT="$(mktemp -d "${TMP_PARENT%/}/larch-step3-cap-test.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

write_common_inputs() {
    local dir="$1" classification="$2"
    mkdir -p "$dir"
    cat >"$dir/run-params.json" <<EOF
{"schema_version":2,"design_classification":"$classification","workflow_path":"$classification","partition_requested":false,"brainstorm_requested":false}
EOF
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

run_driver() {
    local design_tmpdir="$1" stub="$2"
    env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
        RUN_STEP3_TEST_DH="$design_tmpdir" \
        RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" \
        "$LAUNCHER" \
        --design-tmpdir "$design_tmpdir"
}

echo "=== missing counter starts at round 1 ==="
D1="$TMPROOT/round1"
write_common_inputs "$D1" SIMPLE
run_driver "$D1" "$(write_loop_stub "$D1" 'exit 0')" >/dev/null
grep -Fq 'STEP3_REVIEW_CAP_REACHED=false' "$D1/.step3-review-cap.env" || fail 'expected cap false on first entry'
grep -Fq 'STEP3_REVIEW_ROUND_NUM=1' "$D1/.step3-review-cap.env" || fail 'expected first entry round number 1'

echo "=== cap reached bypasses loop ==="
D2="$TMPROOT/cap-reached"
write_common_inputs "$D2" SIMPLE
printf '5\n' >"$D2/review-round-count.txt"
printf 'stale accepted\n' >"$D2/accepted-plan-findings.md"
printf 'stale tally\n' >"$D2/voting-tally.md"
stub="$(write_loop_stub "$D2" 'exit 97')"
driver_out=$(run_driver "$D2" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=cap-reached' || fail 'expected cap-reached loop status'
printf '%s\n' "$driver_out" | grep -q 'TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached' || fail 'expected skipped-cap-reached tally status'
printf '%s\n' "$driver_out" | grep -q 'cap reached; skipping' || fail 'expected cap-reached skip breadcrumb'
[[ "$(cat "$D2/review-round-count.txt")" == "5" ]] || fail 'cap-reached path must leave counter unchanged'
[[ ! -e "$D2/accepted-plan-findings.md" ]] || fail 'cap-reached path must clear stale accepted findings'
[[ ! -e "$D2/voting-tally.md" ]] || fail 'cap-reached path must clear stale voting tally'

echo "=== panel-failed consumes the pending round ==="
D3="$TMPROOT/panel-failed"
write_common_inputs "$D3" SIMPLE
printf '1\n' >"$D3/review-round-count.txt"
stub="$(write_loop_stub "$D3" "printf 'LOOP_STATUS=panel-failed\nACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=panel-failed\nAGGREGATOR_STATUS=skipped\nVOTING_TALLY_FILE=\n'; exit 1")"
driver_out=$(run_driver "$D3" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=panel-failed' || fail 'expected panel-failed loop status'
[[ "$(cat "$D3/review-round-count.txt")" == "2" ]] || fail 'panel-failed path should consume pending round'

echo "=== unrecognized loop status still consumes the pending round ==="
D3B="$TMPROOT/unrecognized-status"
write_common_inputs "$D3B" SIMPLE
printf '1\n' >"$D3B/review-round-count.txt"
stub="$(write_loop_stub "$D3B" "printf 'LOOP_STATUS=weird-status\n'; exit 1")"
driver_out=$(run_driver "$D3B" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=panel-failed' || fail 'invalid loop status should be normalized to panel-failed'
[[ "$(cat "$D3B/review-round-count.txt")" == "2" ]] || fail 'unrecognized post-launch status should keep pending round consumed'

echo "=== removed passive-summary statuses normalize to panel-failed ==="
DP="$TMPROOT/removed-passive-summary"
write_common_inputs "$DP" HARD
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
DH="$TMPROOT/hard-round2"
write_common_inputs "$DH" HARD
printf '1\n' >"$DH/review-round-count.txt"
printf '1\n' >"$DH/plan-review-round-cursor.txt"
printf 'round1 snapshot\n' >"$DH/plan-after-round-1.txt"
stub="$DH/round-num-stub.sh"
cat >"$stub" <<'STUBEOF'
#!/usr/bin/env bash
set -euo pipefail
round_num=""
dh="${RUN_STEP3_TEST_DH:?}"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --round-num) round_num="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
printf '%s\n' "$round_num" >"$dh/round-num-seen.txt"
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=%s\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n' "$round_num"
STUBEOF
chmod +x "$stub"
driver_out=$(run_driver "$DH" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=complete' || fail 'hard round-2 path should still complete'
[[ "$(cat "$DH/round-num-seen.txt")" == "2" ]] || fail 'hard round-2 path must pass --round-num 2 to plan-review-loop.sh'
[[ "$(cat "$DH/plan-review-round-cursor.txt")" == "2" ]] || fail 'hard round-2 path must persist cursor 2 before launch'

echo "=== tally-error does not consume the pending round ==="
D4="$TMPROOT/tally-error"
write_common_inputs "$D4" HARD
printf '2\n' >"$D4/review-round-count.txt"
stub="$(write_loop_stub "$D4" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=3\nTALLY_PLAN_REVIEW_STATUS=tally-error\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 2")"
driver_out=$(run_driver "$D4" "$stub")
printf '%s\n' "$driver_out" | grep -q 'TALLY_PLAN_REVIEW_STATUS=tally-error' || fail 'expected tally-error tally status'
[[ "$(cat "$D4/review-round-count.txt")" == "2" ]] || fail 'tally-error path must not consume pending round'

echo "=== hard cap blocks the sixth review round ==="
D5="$TMPROOT/hard-cap"
write_common_inputs "$D5" HARD
printf '5\n' >"$D5/review-round-count.txt"
stub="$(write_loop_stub "$D5" 'exit 97')"
run_driver "$D5" "$stub" >/dev/null
grep -Fq 'STEP3_REVIEW_CAP_REACHED=true' "$D5/.step3-review-cap.env" || fail 'expected HARD cap reached env'
driver_out=$(run_driver "$D5" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=cap-reached' || fail 'expected HARD cap-reached loop status'
[[ "$(cat "$D5/review-round-count.txt")" == "5" ]] || fail 'HARD cap path must leave counter unchanged'

run_continuation() {
    local design_tmpdir="$1" approve="$2"
    CLAUDE_PLUGIN_ROOT="$ROOT" "$CONTINUATION" --design-tmpdir "$design_tmpdir" --approve-requested "$approve"
}

echo "=== continuation helper stops before cap cleanup ==="
DCAP="$TMPROOT/continuation-cap"
write_common_inputs "$DCAP" SIMPLE
printf '5\n' >"$DCAP/review-round-count.txt"
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
write_common_inputs "$DAPP" SIMPLE
printf '1\n' >"$DAPP/review-round-count.txt"
cp "$DCAP/accepted-plan-findings.md" "$DAPP/accepted-plan-findings.md"
cont_out=$(run_continuation "$DAPP" true)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'explicit approve should stop auto-continuation'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=explicit-approve$' || fail 'explicit approve reason missing'

echo "=== continuation helper continues pruned-empty below cap ==="
DPRUNE="$TMPROOT/continuation-pruned-empty"
write_common_inputs "$DPRUNE" SIMPLE
printf '3\n' >"$DPRUNE/review-round-count.txt"
: >"$DPRUNE/accepted-plan-findings.md"
printf 'PANEL_PRUNED_EMPTY=true\nDEGRADED_PANEL=0\nLOOP_STATUS=complete\nTALLY_PLAN_REVIEW_STATUS=skipped-pruned-empty\n' >"$DPRUNE/.step3-review-result.env"
cont_out=$(run_continuation "$DPRUNE" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'pruned-empty below cap should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=pruned-empty$' || fail 'pruned-empty reason missing'

echo "=== continuation helper stops pruned-empty at cap ==="
DPRUNE_CAP="$TMPROOT/continuation-pruned-empty-cap"
write_common_inputs "$DPRUNE_CAP" SIMPLE
printf '5\n' >"$DPRUNE_CAP/review-round-count.txt"
: >"$DPRUNE_CAP/accepted-plan-findings.md"
printf 'PANEL_PRUNED_EMPTY=true\nDEGRADED_PANEL=0\nLOOP_STATUS=complete\nTALLY_PLAN_REVIEW_STATUS=skipped-pruned-empty\n' >"$DPRUNE_CAP/.step3-review-result.env"
cont_out=$(run_continuation "$DPRUNE_CAP" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'pruned-empty at cap should stop'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=cap-reached$' || fail 'pruned-empty at cap reason missing'

echo "=== continuation helper recomputes high fallback from disk ==="
DHIGH="$TMPROOT/continuation-high"
write_common_inputs "$DHIGH" SIMPLE
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
write_common_inputs "$DIMP" SIMPLE
printf '1\n' >"$DIMP/review-round-count.txt"
cat >"$DIMP/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Important structured
- **Severity**: important
- **Concern**: structured important issue
EOF
cont_out=$(run_continuation "$DIMP" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'structured important should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=high-accepted$' || fail 'structured important reason missing'

echo "=== continuation helper stops on small clean SIMPLE round ==="
DSMALL="$TMPROOT/continuation-small-clean"
write_common_inputs "$DSMALL" SIMPLE
printf '1\n' >"$DSMALL/review-round-count.txt"
cat >"$DSMALL/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Latent cleanup
- **Severity**: latent
- **Concern**: small cleanup
EOF
cont_out=$(run_continuation "$DSMALL" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'small clean SIMPLE round should stop'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=small-clean$' || fail 'small clean reason missing'

echo "=== continuation helper continues on many non-nit findings ==="
DNONNIT="$TMPROOT/continuation-non-nit"
write_common_inputs "$DNONNIT" SIMPLE
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

echo "=== continuation helper continues on first-round structural HARD ==="
DSTRUCT="$TMPROOT/continuation-structural"
write_common_inputs "$DSTRUCT" HARD
printf '1\n' >"$DSTRUCT/review-round-count.txt"
cat >"$DSTRUCT/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Latent structural
- **Severity**: latent
- **Concern**: structural follow-up
EOF
cont_out=$(run_continuation "$DSTRUCT" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'first-round structural HARD should continue'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=structural-or-large-change$' || fail 'structural reason missing'

echo "=== continuation helper stops on nit-only structural HARD ==="
DNIT="$TMPROOT/continuation-structural-nit"
write_common_inputs "$DNIT" HARD
printf '1\n' >"$DNIT/review-round-count.txt"
cat >"$DNIT/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Nit structural
- **Severity**: nit
- **Concern**: spelling cleanup
EOF
cont_out=$(run_continuation "$DNIT" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'nit-only structural HARD should stop'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=small-clean$' || fail 'nit-only structural reason should be small-clean'

echo "=== continuation helper ignores stale workflow_path when design_classification is SIMPLE ==="
DSTALE="$TMPROOT/continuation-stale-workflow"
write_common_inputs "$DSTALE" SIMPLE
printf '{"schema_version":2,"design_classification":"SIMPLE","workflow_path":"HARD"}\n' >"$DSTALE/run-params.json"
printf '1\n' >"$DSTALE/review-round-count.txt"
cp "$DSMALL/accepted-plan-findings.md" "$DSTALE/accepted-plan-findings.md"
cont_out=$(run_continuation "$DSTALE" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'stale workflow_path must not force structural continuation'
printf '%s\n' "$cont_out" | grep -q '^STRUCTURAL_OR_LARGE_CHANGE=false$' || fail 'stale workflow_path should not mark structural'

echo "=== continuation helper defaults invalid classification to HARD ==="
DINVALID="$TMPROOT/continuation-invalid-classification"
write_common_inputs "$DINVALID" SIMPLE
printf '{"schema_version":2,"design_classification":"UNKNOWN","workflow_path":"SIMPLE"}\n' >"$DINVALID/run-params.json"
printf '1\n' >"$DINVALID/review-round-count.txt"
cp "$DSMALL/accepted-plan-findings.md" "$DINVALID/accepted-plan-findings.md"
cont_out=$(run_continuation "$DINVALID" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=true$' || fail 'invalid classification should default HARD and continue'
printf '%s\n' "$cont_out" | grep -q '^STRUCTURAL_OR_LARGE_CHANGE=true$' || fail 'invalid classification should mark structural'

echo "=== continuation helper stops on degraded zero-findings ==="
DDEG="$TMPROOT/continuation-degraded-zero"
write_common_inputs "$DDEG" SIMPLE
printf '1\n' >"$DDEG/review-round-count.txt"
: >"$DDEG/accepted-plan-findings.md"
printf 'DEGRADED_PANEL=1\n' >"$DDEG/.step3-review-result.env"
cont_out=$(run_continuation "$DDEG" false)
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE=false$' || fail 'degraded zero-findings round should stop'
printf '%s\n' "$cont_out" | grep -q '^PLAN_REVIEW_CONTINUE_REASON=small-clean$' || fail 'degraded zero-findings reason missing'

echo "=== continuation helper ignores stale degraded flag after successful retally ==="
DDEG_STALE="$TMPROOT/continuation-degraded-stale-retally"
write_common_inputs "$DDEG_STALE" SIMPLE
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
write_common_inputs "$DCHAIN" HARD
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
state_out=$(CLAUDE_PLUGIN_ROOT="$ROOT" "$ROOT/skills/design/scripts/design-step3-state.sh" --design-tmpdir "$DCHAIN" --auto-continuation-entry)
printf '%s\n' "$state_out" | grep -q '^STEP3_STATE=auto-continuation-entry$' || fail 'chain auto-continuation state missing'
printf 'round1 applied plan\n' >"$DCHAIN/plan-after-round-1.txt"
CLAUDE_PLUGIN_ROOT="$ROOT" "$ROOT/skills/design/scripts/snapshot-plan-round.sh" write-cursor --design-tmpdir "$DCHAIN" --value 2 >/dev/null
run_driver "$DCHAIN" "$chain_stub" >/dev/null
[[ "$(cat "$DCHAIN/review-round-count.txt")" == "2" ]] || fail 'chain second review should consume round 2'
[[ -f "$DCHAIN/plan-review/round-1/keep.txt" ]] || fail 'chain should preserve prior round artifact'
[[ -f "$DCHAIN/plan-review/round-2/launched.txt" ]] || fail 'chain should launch second review round'
[[ ! -f "$DCHAIN/.completed/step-3.5" ]] || fail 'chain should defer Gate C by not writing step-3.5'

echo "PASS: test-step3-review-cap.sh"
