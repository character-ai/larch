#!/usr/bin/env bash
# Offline harness for review-design-step3-loop.sh via run-step3-review.sh --mode loop.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
LAUNCHER="$ROOT/skills/design/scripts/run-step3-review.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-review-design-step3-loop.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

write_common() {
    local dir="$1"
    mkdir -p "$dir"
    cat >"$dir/run-params.json" <<'JSON'
JSON
    printf '# Plan\n\ndiff_lines: 1\n' >"$dir/plan.txt"
    printf 'feature\n' >"$dir/feature-description.txt"
    printf 'feature anchor\n' >"$dir/plan-review-scope-anchor.txt"
}

write_round_stub() {
    local dir="$1" body="$2" stub
    stub="$dir/round-stub.sh"
    cat >"$stub" <<EOFSTUB
#!/usr/bin/env bash
set -euo pipefail
$body
EOFSTUB
    chmod +x "$stub"
    printf '%s\n' "$stub"
}

write_ok_stubs() {
    local dir="$1"
    cat >"$dir/revise-ok.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
plan=""
while [[ $# -gt 0 ]]; do
  case "$1" in --plan-file) plan="${2:?}"; shift 2 ;; *) shift ;; esac
done
printf '\n# revised\n' >>"$plan"
printf 'REVISE_STATUS=ok\n'
STUB
    cat >"$dir/dedup-ok.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
exit 0
STUB
    cat >"$dir/postplan-ok.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in --design-tmpdir) dir="${2:?}"; shift 2 ;; *) shift ;; esac
done
printf 'POSTPLAN_EMIT_STATUS=ok\n' >"$dir/.design-postplan-emit-result.env"
exit 0
STUB
    cat >"$dir/snapshot-ok.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
cmd="${1:?}"; shift
dir=""; value=""; round=""
while [[ $# -gt 0 ]]; do
  case "$1" in --design-tmpdir) dir="${2:?}"; shift 2 ;; --value) value="${2:?}"; shift 2 ;; --round) round="${2:?}"; shift 2 ;; *) shift ;; esac
done
case "$cmd" in
  write-after) cp "$dir/plan.txt" "$dir/plan-after-round-${round}.txt" ;;
  write-cursor) printf '%s\n' "$value" >"$dir/plan-review-round-cursor.txt" ;;
  read-cursor) printf 'ROUND_CURSOR=1\n' ;;
esac
STUB
    cat >"$dir/continue-stop.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'PLAN_REVIEW_CONTINUE=false\nPLAN_REVIEW_CONTINUE_REASON=small-clean\nACCEPTED_COUNT=1\nDEGRADED_PANEL=0\n'
STUB
    chmod +x "$dir"/*.sh
}

run_loop() {
    local dir="$1" round_stub="$2"
    env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
      RUN_STEP3_PLAN_REVIEW_LOOP_SH="$round_stub" \
      RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$dir/revise-ok.sh" \
      RUN_STEP3_DEDUP_PLAN_SH="$dir/dedup-ok.sh" \
      RUN_STEP3_POSTPLAN_EMIT_SH="$dir/postplan-ok.sh" \
      RUN_STEP3_CONTINUATION_SH="$dir/continue-stop.sh" \
      "$LAUNCHER" --design-tmpdir "$dir" --mode loop
}

contains() { case "$1" in *"$2"*) ;; *) fail "$3 (missing $2; got ${1:0:400})" ;; esac; }

write_record_timing_stub() {
    local dir="$1" log="$2" stub
    stub="$dir/record-timing-stub.sh"
    cat >"$stub" <<EOFSTUB
#!/usr/bin/env bash
set -euo pipefail
round=""; start_s=""; end_s=""
while [[ \$# -gt 0 ]]; do
  case "\$1" in
    --round) round="\${2:?}"; shift 2 ;;
    --start-s) start_s="\${2:?}"; shift 2 ;;
    --end-s) end_s="\${2:?}"; shift 2 ;;
    --design-tmpdir) shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\t%s\t%s\n' "\$round" "\$start_s" "\$end_s" >>"$log"
EOFSTUB
    chmod +x "$stub"
    printf '%s\n' "$stub"
}

run_loop_recording() {
    local dir="$1" round_stub="$2" record_stub="$3"
    env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
      RUN_STEP3_PLAN_REVIEW_LOOP_SH="$round_stub" \
      RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$dir/revise-ok.sh" \
      RUN_STEP3_DEDUP_PLAN_SH="$dir/dedup-ok.sh" \
      RUN_STEP3_POSTPLAN_EMIT_SH="$dir/postplan-ok.sh" \
      RUN_STEP3_CONTINUATION_SH="$dir/continue-stop.sh" \
      RUN_STEP3_RECORD_TIMING_SH="$record_stub" \
      "$LAUNCHER" --design-tmpdir "$dir" --mode loop --starting-round 1
}

assert_timing_record() {
    local log="$1" expected_start="$2" label="$3" round start_s end_s
    [[ -s "$log" ]] || fail "$label should record timing"
    [[ "$(wc -l <"$log" | tr -d ' ')" == 1 ]] || fail "$label should write exactly one timing record"
    IFS=$'\t' read -r round start_s end_s <"$log"
    [[ "$round" == 1 ]] || fail "$label timing round should be 1"
    [[ "$start_s" == "$expected_start" ]] || fail "$label timing start should use persisted round-start-s"
    case "$end_s" in ''|*[!0-9]*) fail "$label timing end should be numeric" ;; esac
    (( 10#$end_s >= 10#$expected_start )) || fail "$label timing end should be >= start"
}

write_envelope_stub() {
    local dir="$1" body="$2" stub
    stub="$dir/envelope-stub.sh"
    cat >"$stub" <<EOFSTUB
#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source '$ROOT/skills/design/scripts/lib-phase-driver.sh'
# shellcheck source=skills/design/scripts/review-design-step3-loop.sh
source '$ROOT/skills/design/scripts/review-design-step3-loop.sh'
$body
EOFSTUB
    chmod +x "$stub"
    printf '%s\n' "$stub"
}

run_envelope_stub() {
    local dir="$1" stub="$2"
    env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$dir" "$stub"
}

bash -n "$ROOT/skills/design/scripts/review-design-step3-loop.sh" || fail 'loop script bash -n failed'

echo '=== complete after in-loop apply ==='
D1="$TMP/complete"
write_common "$D1"
write_ok_stubs "$D1"
round_stub="$(write_round_stub "$D1" "cat >\"$D1/accepted-plan-findings.md\" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: issue
FINDINGS
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=1\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'")"
out="$(run_loop "$D1" "$round_stub")"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=complete' 'complete envelope'
[[ -f "$D1/.completed/step-3" ]] || fail 'complete should write .completed/step-3'
[[ -f "$D1/.completed/step-3.5" ]] || fail 'complete should write .completed/step-3.5'
[[ -f "$D1/.gate-b-postapply-ready-1" ]] || fail 'dedup success should write gate-b marker'
grep -q '^STEP3_REVIEW_LOOP_STATUS=complete$' "$D1/.step3-review-result.env" || fail 'complete should persist loop envelope'


echo '=== main-agent-vote-required bail-out ==='
D2="$TMP/mav"
write_common "$D2"
write_ok_stubs "$D2"
round_stub="$(write_round_stub "$D2" "printf 'LOOP_STATUS=main-agent-vote-required\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'")"
out="$(run_loop "$D2" "$round_stub")"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required' 'mav envelope'
[[ "$(cat "$D2/.step3-round-1.phase")" == awaiting-apply ]] || fail 'mav should persist awaiting-apply phase'


echo '=== cap-hit envelope ==='
D3="$TMP/cap"
write_common "$D3"
write_ok_stubs "$D3"
printf '5\n' >"$D3/review-round-count.txt"
round_stub="$(write_round_stub "$D3" 'exit 97')"
out="$(run_loop "$D3" "$round_stub")"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=cap-hit' 'cap-hit envelope'
contains "$out" 'ROUNDS_COMPLETED=5' 'cap-hit rounds completed'
contains "$out" 'REVIEW_ROUND_COUNT=5' 'cap-hit review round count'
grep -q '^STEP3_REVIEW_ROUND_NUM=$' <<<"$out" || fail 'cap-hit should clear STEP3_REVIEW_ROUND_NUM'


echo '=== postplan rc=12 warn-and-continue ==='
D4="$TMP/postplan"
write_common "$D4"
write_ok_stubs "$D4"
cat >"$D4/postplan-ok.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in --design-tmpdir) dir="${2:?}"; shift 2 ;; *) shift ;; esac
done
printf 'POSTPLAN_EMIT_STATUS=ok\nSIZE_TRIGGER_FIRED=true\nPLAN_SIZE_STATUS=plan-size-trigger\n' >"$dir/.design-postplan-emit-result.env"
exit 12
STUB
chmod +x "$D4/postplan-ok.sh"
round_stub="$(write_round_stub "$D4" "cat >\"$D4/accepted-plan-findings.md\" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: issue
FINDINGS
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=1\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'")"
out="$(run_loop "$D4" "$round_stub")"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=complete' 'postplan rc=12 warn-and-continue: complete envelope'
contains "$out" 'WARN=plan-size trigger' 'postplan rc=12 warn-and-continue: WARN emitted'
case "$out" in *'POSTPLAN_RC=12'*) fail 'postplan rc=12 should not appear in result (warn-and-continue)' ;; esac
[[ -f "$D4/.completed/step-3" ]] || fail 'postplan rc=12 warn-and-continue: .completed/step-3 written'


echo '=== postplan operator rc 10/13 envelopes (rc=12 no longer surfaces here) ==='
for spec in '10:hard' '13:partition'; do
    rc="${spec%%:*}"
    label="${spec#*:}"
    D_RC="$TMP/postplan-rc-$rc"
    write_common "$D_RC"
    write_ok_stubs "$D_RC"
    cat >"$D_RC/postplan-ok.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
dir=""
while [[ \$# -gt 0 ]]; do
  case "\$1" in --design-tmpdir) dir="\${2:?}"; shift 2 ;; *) shift ;; esac
done
printf 'POSTPLAN_EMIT_STATUS=$label\n' >"\$dir/.design-postplan-emit-result.env"
exit $rc
STUB
    chmod +x "$D_RC/postplan-ok.sh"
    round_stub="$(write_round_stub "$D_RC" "cat >\"$D_RC/accepted-plan-findings.md\" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: issue
FINDINGS
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=1\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'")"
    out="$(run_loop "$D_RC" "$round_stub")"
    contains "$out" 'STEP3_REVIEW_LOOP_STATUS=postplan-operator-required' "postplan operator rc $rc envelope"
    contains "$out" "POSTPLAN_RC=$rc" "postplan rc $rc carried"
done


echo '=== postplan rc 14 routes to postplan-failed ==='
D_RC14="$TMP/postplan-rc-14"
write_common "$D_RC14"
write_ok_stubs "$D_RC14"
cat >"$D_RC14/postplan-ok.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in --design-tmpdir) dir="${2:?}"; shift 2 ;; *) shift ;; esac
done
printf 'POSTPLAN_EMIT_STATUS=drift\n' >"$dir/.design-postplan-emit-result.env"
exit 14
STUB
chmod +x "$D_RC14/postplan-ok.sh"
round_stub="$(write_round_stub "$D_RC14" "cat >\"$D_RC14/accepted-plan-findings.md\" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: issue
FINDINGS
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=1\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'")"
out="$(run_loop "$D_RC14" "$round_stub")"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=postplan-failed' 'postplan rc 14 failure envelope'
contains "$out" 'POSTPLAN_RC=14' 'postplan rc 14 carried'


echo '=== postplan rc 11 routes through pause helper ==='
D_PAUSE="$TMP/postplan-pause"
write_common "$D_PAUSE"
write_ok_stubs "$D_PAUSE"
cat >"$D_PAUSE/postplan-ok.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
exit 11
STUB
cat >"$D_PAUSE/pause-stub.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'PAUSE_STUB=1\n'
exit 0
STUB
chmod +x "$D_PAUSE/postplan-ok.sh" "$D_PAUSE/pause-stub.sh"
round_stub="$(write_round_stub "$D_PAUSE" "cat >\"$D_PAUSE/accepted-plan-findings.md\" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: issue
FINDINGS
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=1\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'")"
out="$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
  RUN_STEP3_PLAN_REVIEW_LOOP_SH="$round_stub" \
  RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$D_PAUSE/revise-ok.sh" \
  RUN_STEP3_DEDUP_PLAN_SH="$D_PAUSE/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$D_PAUSE/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D_PAUSE/continue-stop.sh" \
  RUN_STEP3_DESIGN_PAUSE_SAVE_SH="$D_PAUSE/pause-stub.sh" \
  "$LAUNCHER" --design-tmpdir "$D_PAUSE" --mode loop)"
contains "$out" 'PAUSE_STUB=1' 'postplan rc 11 pause helper'


echo '=== postplan hard failure emits postplan-failed ==='
D_POST_FAIL="$TMP/postplan-hard-fail"
write_common "$D_POST_FAIL"
write_ok_stubs "$D_POST_FAIL"
cat >"$D_POST_FAIL/postplan-ok.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
exit 1
STUB
chmod +x "$D_POST_FAIL/postplan-ok.sh"
round_stub="$(write_round_stub "$D_POST_FAIL" "cat >\"$D_POST_FAIL/accepted-plan-findings.md\" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: issue
FINDINGS
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=1\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'")"
out="$(run_loop "$D_POST_FAIL" "$round_stub")"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=postplan-failed' 'postplan hard failure envelope'
contains "$out" 'POSTPLAN_RC=1' 'postplan hard failure rc'


echo '=== post-apply postplan-failed records persisted round-start timing ==='
D_POST_FAIL_TIMING="$TMP/postplan-hard-fail-timing"
write_common "$D_POST_FAIL_TIMING"
write_ok_stubs "$D_POST_FAIL_TIMING"
mkdir -p "$D_POST_FAIL_TIMING/plan-review/round-1"
printf '123\n' >"$D_POST_FAIL_TIMING/plan-review/round-1/round-start-s"
cat >"$D_POST_FAIL_TIMING/postplan-ok.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
exit 1
STUB
chmod +x "$D_POST_FAIL_TIMING/postplan-ok.sh"
printf 'awaiting-post-apply\n' >"$D_POST_FAIL_TIMING/.step3-round-1.phase"
: >"$D_POST_FAIL_TIMING/.gate-b-postapply-ready-1"
printf '1\n' >"$D_POST_FAIL_TIMING/review-round-count.txt"
timing_log="$D_POST_FAIL_TIMING/timing-records.tsv"
record_stub="$(write_record_timing_stub "$D_POST_FAIL_TIMING" "$timing_log")"
round_stub="$(write_round_stub "$D_POST_FAIL_TIMING" 'exit 99')"
out="$(run_loop_recording "$D_POST_FAIL_TIMING" "$round_stub" "$record_stub")"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=postplan-failed' 'postplan hard failure timing envelope'
assert_timing_record "$timing_log" 123 'postplan hard failure'


echo '=== postplan-operator continue marker resumes at continuation ==='
D_OP_CONT="$TMP/postplan-operator-continue"
write_common "$D_OP_CONT"
write_ok_stubs "$D_OP_CONT"
printf 'awaiting-postplan-operator\n' >"$D_OP_CONT/.step3-round-1.phase"
: >"$D_OP_CONT/.gate-b-postapply-ready-1"
: >"$D_OP_CONT/.postplan-operator-continue-1"
printf '1\n' >"$D_OP_CONT/review-round-count.txt"
round_stub="$(write_round_stub "$D_OP_CONT" 'exit 99')"
out="$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
  RUN_STEP3_PLAN_REVIEW_LOOP_SH="$round_stub" \
  RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$D_OP_CONT/revise-ok.sh" \
  RUN_STEP3_DEDUP_PLAN_SH="$D_OP_CONT/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$D_OP_CONT/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D_OP_CONT/continue-stop.sh" \
  "$LAUNCHER" --design-tmpdir "$D_OP_CONT" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=complete' 'postplan-operator continue completes'
[[ ! -f "$D_OP_CONT/.postplan-operator-continue-1" ]] || fail 'continue marker should be consumed'
[[ "$(cat "$D_OP_CONT/.step3-round-1.phase")" == awaiting-continuation ]] || fail 'continue marker should advance phase'


echo '=== postplan-operator continue marker failure records persisted round-start timing ==='
D_OP_FAIL="$TMP/postplan-operator-continue-fail"
write_common "$D_OP_FAIL"
write_ok_stubs "$D_OP_FAIL"
mkdir -p "$D_OP_FAIL/plan-review/round-1"
printf '456\n' >"$D_OP_FAIL/plan-review/round-1/round-start-s"
printf 'awaiting-postplan-operator\n' >"$D_OP_FAIL/.step3-round-1.phase"
: >"$D_OP_FAIL/.gate-b-postapply-ready-1"
: >"$D_OP_FAIL/.postplan-operator-continue-1"
printf '1\n' >"$D_OP_FAIL/review-round-count.txt"
timing_log="$D_OP_FAIL/timing-records.tsv"
record_stub="$(write_record_timing_stub "$D_OP_FAIL" "$timing_log")"
fake_bin="$D_OP_FAIL/fake-bin"
mkdir -p "$fake_bin"
cat >"$fake_bin/rm" <<'STUB'
#!/usr/bin/env bash
for arg in "$@"; do
  case "$arg" in
    *.postplan-operator-continue-1) exit 1 ;;
  esac
done
exec /bin/rm "$@"
STUB
chmod +x "$fake_bin/rm"
round_stub="$(write_round_stub "$D_OP_FAIL" 'exit 99')"
out="$(PATH="$fake_bin:$PATH" env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
  RUN_STEP3_PLAN_REVIEW_LOOP_SH="$round_stub" \
  RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$D_OP_FAIL/revise-ok.sh" \
  RUN_STEP3_DEDUP_PLAN_SH="$D_OP_FAIL/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$D_OP_FAIL/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D_OP_FAIL/continue-stop.sh" \
  RUN_STEP3_RECORD_TIMING_SH="$record_stub" \
  "$LAUNCHER" --design-tmpdir "$D_OP_FAIL" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=postplan-failed' 'continue marker failure envelope'
assert_timing_record "$timing_log" 456 'continue marker failure'


D5="$TMP/dedup"
write_common "$D5"
write_ok_stubs "$D5"
cat >"$D5/dedup-ok.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
case " $* " in *' --dedup '*) exit 2 ;; *) exit 0 ;; esac
STUB
chmod +x "$D5/dedup-ok.sh"
round_stub="$(write_round_stub "$D5" "cat >\"$D5/accepted-plan-findings.md\" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: issue
FINDINGS
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=1\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'")"
out="$(run_loop "$D5" "$round_stub")"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required' 'dedup bail envelope'
contains "$out" 'DEDUP_RC=2' 'dedup rc carried'
( command grep -Fq '# revised' "$D5/plan.txt" ) || true

echo '=== filtered per-round approval consumes approval env ==='
D6="$TMP/filtered-approval"
write_common "$D6"
write_ok_stubs "$D6"
cat >"$D6/run-params.json" <<'JSON'
JSON
cat >"$D6/accepted-plan-findings.md" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: keep
FINDINGS
cat >"$D6/filtered-findings.md" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: keep
FINDINGS
printf 'FINDINGS_FILE=%s/filtered-findings.md\n' "$D6" >"$D6/.gate-b-per-round-approval-round-1.env"
printf 'awaiting-apply\n' >"$D6/.step3-round-1.phase"
printf '1\n' >"$D6/review-round-count.txt"
cp "$D6/plan.txt" "$D6/plan-pre-apply-round-1.txt"
round_stub="$(write_round_stub "$D6" 'exit 99')"
out="$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
  RUN_STEP3_PLAN_REVIEW_LOOP_SH="$round_stub" \
  RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$D6/revise-ok.sh" \
  RUN_STEP3_DEDUP_PLAN_SH="$D6/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$D6/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D6/continue-stop.sh" \
  "$LAUNCHER" --design-tmpdir "$D6" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=complete' 'filtered approval resume completes'
[[ ! -f "$D6/.gate-b-per-round-approval-round-1.env" ]] || fail 'approval env should be consumed once'
grep -Fq '# revised' "$D6/plan.txt" || fail 'filtered approval should still apply findings'


echo '=== continuation failure emits postplan-failed ==='
D7="$TMP/continuation-fail"
write_common "$D7"
write_ok_stubs "$D7"
cat >"$D7/continue-stop.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
exit 2
STUB
chmod +x "$D7/continue-stop.sh"
printf 'awaiting-continuation\n' >"$D7/.step3-round-1.phase"
printf '1\n' >"$D7/review-round-count.txt"
round_stub="$(write_round_stub "$D7" 'exit 99')"
out="$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
  RUN_STEP3_PLAN_REVIEW_LOOP_SH="$round_stub" \
  RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$D7/revise-ok.sh" \
  RUN_STEP3_DEDUP_PLAN_SH="$D7/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$D7/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D7/continue-stop.sh" \
  "$LAUNCHER" --design-tmpdir "$D7" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=postplan-failed' 'continuation failure envelope'


echo '=== continuation failure records persisted round-start timing ==='
D7_TIMING="$TMP/continuation-fail-timing"
write_common "$D7_TIMING"
write_ok_stubs "$D7_TIMING"
mkdir -p "$D7_TIMING/plan-review/round-1"
printf '789\n' >"$D7_TIMING/plan-review/round-1/round-start-s"
cat >"$D7_TIMING/continue-stop.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
exit 2
STUB
chmod +x "$D7_TIMING/continue-stop.sh"
printf 'awaiting-continuation\n' >"$D7_TIMING/.step3-round-1.phase"
printf '1\n' >"$D7_TIMING/review-round-count.txt"
timing_log="$D7_TIMING/timing-records.tsv"
record_stub="$(write_record_timing_stub "$D7_TIMING" "$timing_log")"
round_stub="$(write_round_stub "$D7_TIMING" 'exit 99')"
out="$(run_loop_recording "$D7_TIMING" "$round_stub" "$record_stub")"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=postplan-failed' 'continuation failure timing envelope'
assert_timing_record "$timing_log" 789 'continuation failure'


echo '=== per-round approval bail-out in awaiting-apply ==='
D8="$TMP/per-round-approval-bail"
write_common "$D8"
write_ok_stubs "$D8"
cat >"$D8/run-params.json" <<'JSON'
{"approve_requested":true}
JSON
cat >"$D8/accepted-plan-findings.md" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: issue
FINDINGS
printf 'awaiting-apply\n' >"$D8/.step3-round-1.phase"
printf '1\n' >"$D8/review-round-count.txt"
round_stub="$(write_round_stub "$D8" 'exit 99')"
out="$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
  RUN_STEP3_PLAN_REVIEW_LOOP_SH="$round_stub" \
  RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$D8/revise-ok.sh" \
  RUN_STEP3_DEDUP_PLAN_SH="$D8/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$D8/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D8/continue-stop.sh" \
  "$LAUNCHER" --design-tmpdir "$D8" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=per-round-approval-required' 'per-round approval bail-out envelope'


echo '=== empty filtered per-round approval clears stale accepted findings ==='
D9="$TMP/empty-filtered-approval"
write_common "$D9"
write_ok_stubs "$D9"
cat >"$D9/run-params.json" <<'JSON'
JSON
cat >"$D9/accepted-plan-findings.md" <<'FINDINGS'
### FINDING_1: Stale accepted
- **Severity**: important
- **Concern**: should be cleared
FINDINGS
: >"$D9/filtered-findings.md"
printf 'FINDINGS_FILE=%s/filtered-findings.md\n' "$D9" >"$D9/.gate-b-per-round-approval-round-1.env"
printf 'awaiting-apply\n' >"$D9/.step3-round-1.phase"
printf '1\n' >"$D9/review-round-count.txt"
round_stub="$(write_round_stub "$D9" 'exit 99')"
out="$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" \
  RUN_STEP3_PLAN_REVIEW_LOOP_SH="$round_stub" \
  RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$D9/revise-ok.sh" \
  RUN_STEP3_DEDUP_PLAN_SH="$D9/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$D9/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D9/continue-stop.sh" \
  "$LAUNCHER" --design-tmpdir "$D9" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=complete' 'empty filtered approval completes'
[[ ! -s "$D9/accepted-plan-findings.md" ]] || fail 'empty filtered approval should clear stale accepted-plan-findings.md'


echo '=== CR/LF sanitization before envelope emission ==='
D_CRLF="$TMP/crlf-sanitize"
write_common "$D_CRLF"
envelope_stub="$(write_envelope_stub "$D_CRLF" 'PLAN_REVIEW_CONTINUE_REASON=$'"'"'reason\nwith\nlines\rand\rcrs'"'"'
SCOPE_ANCHOR_FILE=$'"'"'path\nwith\rnewlines'"'"'
export PLAN_REVIEW_CONTINUE_REASON SCOPE_ANCHOR_FILE
step3_loop_emit_envelope complete 1 1 1')"
out="$(run_envelope_stub "$D_CRLF" "$envelope_stub")"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=complete' 'CR/LF envelope status'
contains "$out" 'PLAN_REVIEW_CONTINUE_REASON=reasonwithlinesandcrs' 'CR/LF sanitized continue reason'
case "$out" in *'SCOPE_ANCHOR_FILE='*) fail 'CR/LF envelope should omit SCOPE_ANCHOR_FILE' ;; esac
[[ -f "$D_CRLF/.step3-review-result.env" ]] || fail 'CR/LF envelope should persist result env'
grep -q '^PLAN_REVIEW_CONTINUE_REASON=reasonwithlinesandcrs$' "$D_CRLF/.step3-review-result.env" || fail 'CR/LF persisted continue reason'
reason_value="$(grep '^PLAN_REVIEW_CONTINUE_REASON=' "$D_CRLF/.step3-review-result.env" | cut -d= -f2-)"
case "$reason_value" in *$'\n'*|*$'\r'*) fail 'persisted continue reason value must not contain CR/LF' ;; esac
grep -q '^STEP3_REVIEW_LOOP_STATUS=complete$' "$D_CRLF/.step3-review-result.env" || fail 'CR/LF persisted loop status'
case "$(cat "$D_CRLF/.step3-review-result.env")" in *SCOPE_ANCHOR_FILE=*) fail 'CR/LF persisted env should omit SCOPE_ANCHOR_FILE' ;; esac


echo '=== merge fallback sanitizes PLAN_REVIEW_CONTINUE_REASON from result env ==='
D_MERGE="$TMP/merge-fallback-cr"
write_common "$D_MERGE"
printf 'PLAN_REVIEW_CONTINUE_REASON=keep\rme\r\n' >"$D_MERGE/.step3-review-result.env"
envelope_stub="$(write_envelope_stub "$D_MERGE" 'unset PLAN_REVIEW_CONTINUE_REASON
step3_loop_persist_envelope complete 1 1 1')"
out="$(run_envelope_stub "$D_MERGE" "$envelope_stub")"
grep -q '^PLAN_REVIEW_CONTINUE_REASON=keepme$' "$D_MERGE/.step3-review-result.env" || fail 'merge fallback should persist sanitized continue reason'
case "$(grep '^PLAN_REVIEW_CONTINUE_REASON=' "$D_MERGE/.step3-review-result.env")" in *$'\r'*) fail 'merge fallback persisted reason must not contain CR' ;; esac


echo '=== merge fallback omits sanitized-empty PLAN_REVIEW_CONTINUE_REASON ==='
D_MERGE_EMPTY="$TMP/merge-fallback-empty"
write_common "$D_MERGE_EMPTY"
printf 'PLAN_REVIEW_CONTINUE_REASON=\r\n' >"$D_MERGE_EMPTY/.step3-review-result.env"
envelope_stub="$(write_envelope_stub "$D_MERGE_EMPTY" 'unset PLAN_REVIEW_CONTINUE_REASON
step3_loop_persist_envelope complete 1 1 1')"
out="$(run_envelope_stub "$D_MERGE_EMPTY" "$envelope_stub")"
case "$(cat "$D_MERGE_EMPTY/.step3-review-result.env")" in *PLAN_REVIEW_CONTINUE_REASON=*) fail 'sanitized-empty merge should omit PLAN_REVIEW_CONTINUE_REASON' ;; esac
grep -q '^STEP3_REVIEW_LOOP_STATUS=complete$' "$D_MERGE_EMPTY/.step3-review-result.env" || fail 'sanitized-empty merge should persist loop status'


echo '=== result-env write failure preserves emitted loop status and logs failure ==='
D_WARN="$TMP/write-failure-warn"
write_common "$D_WARN"
ln -sf "$D_WARN/nonexistent-target" "$D_WARN/.step3-review-result.env"
envelope_stub="$(write_envelope_stub "$D_WARN" 'step3_loop_emit_envelope main-agent-vote-required 1 1 1')"
out="$(run_envelope_stub "$D_WARN" "$envelope_stub")"
contains "$out" 'WARN=step3_loop_persist_envelope: phase_driver_write_result_env failed' 'write failure WARN kv'
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required' 'write failure keeps operational status'
case "$out" in *'STEP3_REVIEW_LOOP_STATUS=panel-failed'*) fail 'write failure must not emit panel-failed replacement status' ;; esac
grep -Fq 'phase_driver_write_result_env' "$D_WARN/execution-issues.md" || fail 'write failure should append Tool Failures entry'


echo '=== loop envelope carries REASON=ballot-items-lost ==='
D_REASON="$TMP/reason-carry"
write_common "$D_REASON"
write_ok_stubs "$D_REASON"
# shellcheck disable=SC2016 # Stub body expands DESIGN_TMPDIR when the generated stub runs.
round_stub="$(write_round_stub "$D_REASON" 'cat >"$DESIGN_TMPDIR/.step3-review-result.env" <<EOF
LOOP_STATUS=zero-findings-degraded-panel
REASON=ballot-items-lost
ACCEPTED_COUNT=0
DEGRADED_PANEL=1
TALLY_PLAN_REVIEW_STATUS=ok
EOF
printf "LOOP_STATUS=zero-findings-degraded-panel\nREASON=ballot-items-lost\nACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nTALLY_PLAN_REVIEW_STATUS=ok\n"')"
out="$(run_loop "$D_REASON" "$round_stub")"
contains "$out" 'REASON=ballot-items-lost' 'envelope carries REASON'
grep -q '^REASON=ballot-items-lost$' "$D_REASON/.step3-review-result.env" || fail 'persisted REASON=ballot-items-lost'


echo '=== clean terminal envelope writes empty REASON ==='
D_REASON_CLEAN="$TMP/reason-clean"
write_common "$D_REASON_CLEAN"
envelope_stub="$(write_envelope_stub "$D_REASON_CLEAN" 'REASON=
step3_loop_emit_envelope complete 1 1 1')"
out="$(run_envelope_stub "$D_REASON_CLEAN" "$envelope_stub")"
grep -q '^REASON=$' "$D_REASON_CLEAN/.step3-review-result.env" || fail 'clean terminal should persist empty REASON'


echo '=== default python revise-waterfall path ==='
D_PY="$TMP/default-python-revise"
write_common "$D_PY"
write_ok_stubs "$D_PY"
FAKE_PLUGIN="$D_PY/fake-plugin"
mkdir -p "$FAKE_PLUGIN/python" "$FAKE_PLUGIN/scripts" "$FAKE_PLUGIN/skills/design/scripts"
cp "$ROOT/python/"*.py "$FAKE_PLUGIN/python/"
mv "$FAKE_PLUGIN/python/cli.py" "$FAKE_PLUGIN/python/real-cli.py"
cat >"$FAKE_PLUGIN/python/cli.py" <<'SPYCLI'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def main() -> None:
    root = Path(__file__).resolve().parent
    if len(sys.argv) >= 3 and sys.argv[1] == "plan" and sys.argv[2] == "revise-waterfall":
        spy = os.environ.get("REVISE_WATERFALL_SPY_LOG")
        if spy:
            with open(spy, "a", encoding="utf-8") as handle:
                handle.write(" ".join(sys.argv[3:]) + "\n")
        if "--plan-file" in sys.argv:
            plan_file = sys.argv[sys.argv.index("--plan-file") + 1]
            with open(plan_file, "a", encoding="utf-8") as handle:
                handle.write("\n# revised\n")
        print("REVISE_STATUS=ok")
        print("REVISE_TIER_1_STATUS=skipped-not-present")
        print("REVISE_TIER_2_STATUS=skipped-not-present")
        print("REVISE_TIER_3_STATUS=skipped-not-present")
        print("REVISE_TIER_4_STATUS=not-attempted")
        raise SystemExit(0)
    os.execv(sys.executable, [sys.executable, str(root / "real-cli.py"), *sys.argv[1:]])

if __name__ == "__main__":
    main()
SPYCLI
chmod +x "$FAKE_PLUGIN/python/cli.py"
ln -sf "$ROOT/skills/design/scripts/review-design-step3-loop.sh" "$FAKE_PLUGIN/skills/design/scripts/review-design-step3-loop.sh"
ln -sf "$D_PY/revise-ok.sh" "$FAKE_PLUGIN/skills/design/scripts/revise-plan-with-waterfall"".sh"
printf 'awaiting-apply\n' >"$D_PY/.step3-round-1.phase"
printf '1\n' >"$D_PY/review-round-count.txt"
cat >"$D_PY/accepted-plan-findings.md" <<'FINDINGS'
### FINDING_1: Important
- **Severity**: important
- **Concern**: issue
FINDINGS
round_stub="$(write_round_stub "$D_PY" 'exit 99')"
: >"$D_PY/revise-waterfall-spy.log"
out="$(env -u LARCH_QUIET_LOG_FILE -u RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH \
  LARCH_QUIET_DISABLE=1 \
  CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" \
  REVISE_WATERFALL_SPY_LOG="$D_PY/revise-waterfall-spy.log" \
  RUN_STEP3_PLAN_REVIEW_LOOP_SH="$round_stub" \
  RUN_STEP3_DEDUP_PLAN_SH="$D_PY/dedup-ok.sh" \
  RUN_STEP3_POSTPLAN_EMIT_SH="$D_PY/postplan-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D_PY/continue-stop.sh" \
  "$LAUNCHER" --design-tmpdir "$D_PY" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=complete' 'default python revise path completes'
grep -q -- '--design-tmpdir' "$D_PY/revise-waterfall-spy.log" || fail 'default path should invoke plan revise-waterfall'
grep -q -- '--round-num' "$D_PY/revise-waterfall-spy.log" || fail 'default path should pass round-num to revise-waterfall'




echo '=== design-step3-review wrapper rejects invalid resume state before writes ==='
WRAPPER="$ROOT/skills/design/scripts/design-step3-review.sh"
D_WRAP="$TMP/wrapper-invalid"
write_common "$D_WRAP"
printf '1\n' >"$D_WRAP/review-round-count.txt"
set +e
out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_WRAP" ISSUE_NUMBER=9 \
  "$WRAPPER" --starting-round 3 --phase awaiting-continuation 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "wrapper impossible starting round rc=$rc: $out"
contains "$out" 'cannot exceed last consumed review round + 1' 'wrapper rejects impossible starting round'
[[ ! -e "$D_WRAP/.step3-round-3.phase" ]] || fail 'impossible starting round wrote phase state'

set +e
out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_WRAP" ISSUE_NUMBER=9 \
  "$WRAPPER" --starting-round 1 --phase awaiting-vote 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "wrapper awaiting-vote rc=$rc: $out"
contains "$out" 'awaiting-vote is internal' 'wrapper rejects awaiting-vote'
[[ ! -e "$D_WRAP/.step3-round-1.phase" ]] || fail 'awaiting-vote wrote phase state'

set +e
out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_WRAP" ISSUE_NUMBER=9 \
  "$WRAPPER" --phase awaiting-continuation 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "wrapper missing starting-round rc=$rc: $out"
contains "$out" 'resume-state flags require --starting-round' 'wrapper requires starting round for resume flags'

OUTSIDE="$TMP/outside-findings.md"
printf 'outside\n' >"$OUTSIDE"
set +e
out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_WRAP" ISSUE_NUMBER=9 \
  "$WRAPPER" --starting-round 1 --findings-file "$OUTSIDE" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "wrapper outside findings rc=$rc: $out"
contains "$out" 'must resolve under DESIGN_TMPDIR' 'wrapper rejects outside findings file'
[[ ! -e "$D_WRAP/.gate-b-per-round-approval-round-1.env" ]] || fail 'outside findings wrote env state'

mkdir -p "$D_WRAP/subdir"
printf 'inside\n' >"$D_WRAP/subdir/inside-findings.md"
ln -s "$D_WRAP/subdir/inside-findings.md" "$D_WRAP/symlink-findings.md"
set +e
out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_WRAP" ISSUE_NUMBER=9 \
  "$WRAPPER" --starting-round 1 --findings-file "$D_WRAP/symlink-findings.md" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "wrapper symlink findings rc=$rc: $out"
contains "$out" 'must not be a symlink' 'wrapper rejects symlink findings file'
[[ ! -e "$D_WRAP/.gate-b-per-round-approval-round-1.env" ]] || fail 'symlink findings wrote env state'

mkdir -p "$D_WRAP/findings-dir"
set +e
out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_WRAP" ISSUE_NUMBER=9 \
  "$WRAPPER" --starting-round 1 --findings-file "$D_WRAP/findings-dir" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "wrapper nonregular findings rc=$rc: $out"
contains "$out" 'must be a regular file' 'wrapper rejects non-regular findings file'
[[ ! -e "$D_WRAP/.gate-b-per-round-approval-round-1.env" ]] || fail 'nonregular findings wrote env state'
printf 'PASS: test-review-design-step3-loop.sh\n'
