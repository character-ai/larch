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
{"schema_version":2,"design_classification":"SIMPLE","workflow_path":"SIMPLE","approve_requested":false,"partition_requested":false,"brainstorm_requested":false}
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
      RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH="$dir/snapshot-ok.sh" \
      RUN_STEP3_CONTINUATION_SH="$dir/continue-stop.sh" \
      "$LAUNCHER" --design-tmpdir "$dir" --mode loop
}

contains() { case "$1" in *"$2"*) ;; *) fail "$3 (missing $2; got ${1:0:400})" ;; esac; }

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
printf 'POSTPLAN_EMIT_STATUS=ok\nHARD_TRIGGER_FIRED=true\nPLAN_SIZE_STATUS=hard-trigger\n' >"$dir/.design-postplan-emit-result.env"
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
contains "$out" 'WARN=plan-size hard trigger' 'postplan rc=12 warn-and-continue: WARN emitted'
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
  RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH="$D_PAUSE/snapshot-ok.sh" \
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


echo '=== postplan-operator continue marker resumes at continuation ==='
D_OP_CONT="$TMP/postplan-operator-continue"
write_common "$D_OP_CONT"
write_ok_stubs "$D_OP_CONT"
printf '{"schema_version":2,"design_classification":"HARD","workflow_path":"HARD","approve_requested":false,"partition_requested":false,"brainstorm_requested":false}\n' >"$D_OP_CONT/run-params.json"
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
  RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH="$D_OP_CONT/snapshot-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D_OP_CONT/continue-stop.sh" \
  "$LAUNCHER" --design-tmpdir "$D_OP_CONT" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=complete' 'postplan-operator continue completes'
[[ ! -f "$D_OP_CONT/.postplan-operator-continue-1" ]] || fail 'continue marker should be consumed'
[[ "$(cat "$D_OP_CONT/.step3-round-1.phase")" == awaiting-continuation ]] || fail 'continue marker should advance phase'
[[ -f "$D_OP_CONT/plan-after-round-1.txt" ]] || fail 'postplan-operator continue should write HARD snapshot'
[[ "$(cat "$D_OP_CONT/plan-review-round-cursor.txt" 2>/dev/null)" == 2 ]] || fail 'postplan-operator continue should advance HARD cursor'


echo '=== dedup failure restores snapshot and bails to main agent ==='
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
if grep -Fq '# revised' "$D5/plan.txt"; then
    fail 'dedup failure should restore pre-apply snapshot'
fi

echo '=== filtered per-round approval consumes approval env ==='
D6="$TMP/filtered-approval"
write_common "$D6"
write_ok_stubs "$D6"
cat >"$D6/run-params.json" <<'JSON'
{"schema_version":2,"design_classification":"SIMPLE","workflow_path":"SIMPLE","approve_requested":true,"partition_requested":false,"brainstorm_requested":false}
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
  RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH="$D6/snapshot-ok.sh" \
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
  RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH="$D7/snapshot-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D7/continue-stop.sh" \
  "$LAUNCHER" --design-tmpdir "$D7" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=postplan-failed' 'continuation failure envelope'


echo '=== per-round approval bail-out in awaiting-apply ==='
D8="$TMP/per-round-approval-bail"
write_common "$D8"
write_ok_stubs "$D8"
cat >"$D8/run-params.json" <<'JSON'
{"schema_version":2,"design_classification":"SIMPLE","workflow_path":"SIMPLE","approve_requested":true,"partition_requested":false,"brainstorm_requested":false}
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
  RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH="$D8/snapshot-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D8/continue-stop.sh" \
  "$LAUNCHER" --design-tmpdir "$D8" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=per-round-approval-required' 'per-round approval bail-out envelope'


echo '=== empty filtered per-round approval clears stale accepted findings ==='
D9="$TMP/empty-filtered-approval"
write_common "$D9"
write_ok_stubs "$D9"
cat >"$D9/run-params.json" <<'JSON'
{"schema_version":2,"design_classification":"SIMPLE","workflow_path":"SIMPLE","approve_requested":true,"partition_requested":false,"brainstorm_requested":false}
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
  RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH="$D9/snapshot-ok.sh" \
  RUN_STEP3_CONTINUATION_SH="$D9/continue-stop.sh" \
  "$LAUNCHER" --design-tmpdir "$D9" --mode loop --starting-round 1)"
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=complete' 'empty filtered approval completes'
[[ ! -s "$D9/accepted-plan-findings.md" ]] || fail 'empty filtered approval should clear stale accepted-plan-findings.md'


printf 'PASS: test-review-design-step3-loop.sh\n'
