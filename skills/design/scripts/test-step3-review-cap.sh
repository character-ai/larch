#!/usr/bin/env bash
# Regression harness for /design Step 3 review-round cap handling.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SKILL_MD="$ROOT/skills/design/SKILL.md"
LAUNCHER="$ROOT/skills/design/scripts/run-step3-review.sh"

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

mkdir -p "${HOME}/.cache/larch/sessions"
TMPROOT="$(mktemp -d "${HOME}/.cache/larch/sessions/larch-step3-cap-test.XXXXXX")"
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
    env -u LARCH_QUIET_LOG_FILE CLAUDE_PLUGIN_ROOT="$ROOT" \
        RUN_STEP3_TEST_DH="$design_tmpdir" \
        RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" \
        "$LAUNCHER" \
        --design-tmpdir "$design_tmpdir" \
        --round-cap 5
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
printf '3\n' >"$D2/review-round-count.txt"
stub="$(write_loop_stub "$D2" 'exit 97')"
driver_out=$(run_driver "$D2" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=cap-reached' || fail 'expected cap-reached loop status'
printf '%s\n' "$driver_out" | grep -q 'TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached' || fail 'expected skipped-cap-reached tally status'
printf '%s\n' "$driver_out" | grep -q 'cap reached; skipping' || fail 'expected cap-reached skip breadcrumb'
[[ "$(cat "$D2/review-round-count.txt")" == "3" ]] || fail 'cap-reached path must leave counter unchanged'

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

echo "=== passive-summary statuses parse and persist across Step 3 entries ==="
DP="$TMPROOT/passive-summary"
write_common_inputs "$DP" HARD
mkdir -p "$DP/plan-review/round-1" "$DP/plan-review/round-2"
printf 'stale\n' >"$DP/plan-review/round-1/stale.txt"
printf 'stale\n' >"$DP/plan-review/round-2/stale.txt"
stub="$(write_loop_stub "$DP" "mkdir -p \"$DP/plan-review/round-1\"; printf 'fresh\n' >\"$DP/plan-review/round-1/new.txt\"; printf 'LOOP_STATUS=converged\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
driver_out=$(run_driver "$DP" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=converged' || fail 'expected converged passive-summary status'
[[ "$(cat "$DP/review-round-count.txt")" == "1" ]] || fail 'first passive-summary entry should persist round 1'
[[ -f "$DP/plan-review/round-1/new.txt" ]] || fail 'fresh round-1 artifact missing after first entry'
[[ ! -e "$DP/plan-review/round-1/stale.txt" ]] || fail 'stale round-1 artifact should be cleaned before launch'
[[ ! -e "$DP/plan-review/round-2/stale.txt" ]] || fail 'stale round-2 artifact should be cleaned before launch'
stub="$(write_loop_stub "$DP" "mkdir -p \"$DP/plan-review/round-2\"; printf 'fresh\n' >\"$DP/plan-review/round-2/new.txt\"; printf 'LOOP_STATUS=cap-hit\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
driver_out=$(run_driver "$DP" "$stub")
printf '%s\n' "$driver_out" | grep -q 'LOOP_STATUS=cap-hit' || fail 'expected cap-hit passive-summary status'
[[ "$(cat "$DP/review-round-count.txt")" == "2" ]] || fail 'second passive-summary entry should persist round 2'
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

echo "PASS: test-step3-review-cap.sh"
