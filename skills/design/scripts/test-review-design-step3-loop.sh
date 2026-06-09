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
[[ ! -f "$D1/.completed/step-3.5" ]] || fail 'complete should defer .completed/step-3.5 to Step 3b'
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


echo '=== postplan operator rc ==='
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
printf 'POSTPLAN_EMIT_STATUS=hard\nHARD_TRIGGER_FIRED=true\n' >"$dir/.design-postplan-emit-result.env"
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
contains "$out" 'STEP3_REVIEW_LOOP_STATUS=postplan-operator-required' 'postplan operator envelope'
contains "$out" 'POSTPLAN_RC=12' 'postplan rc carried'


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


printf 'PASS: test-review-design-step3-loop.sh\n'
