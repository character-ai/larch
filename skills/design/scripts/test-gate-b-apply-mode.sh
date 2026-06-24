#!/usr/bin/env bash
# Offline coverage for Gate B mode selection and safety-brake handoff.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
WRITE_RUN_PARAMS=(python3 "$ROOT/python/cli.py" session write-run-params)
CLI="$ROOT/python/cli.py"
POSTPLAN_CLI=(python3 "$CLI" design postplan-emit)
SETTLE="$ROOT/skills/design/scripts/design-step35-settle.sh"
SKILL_MD="$ROOT/skills/design/SKILL.md"
APPROVAL_GATES="$ROOT/skills/design/references/approval-gates.md"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

python3 -m py_compile "$ROOT/python/design_postplan.py" || fail 'design_postplan.py py_compile failed'
python3 -m py_compile "$ROOT/python/plan_review.py" || fail 'plan_review.py py_compile failed'
bash -n "$SETTLE" || fail 'design-step35-settle bash -n failed'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/tgbam.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

read_approve_requested() {
  local run_params="$1" approve_requested=false
  if command -v jq >/dev/null 2>&1; then
    case "$(jq -r '.approve_requested // false' "$run_params" 2>/dev/null)" in
      true) approve_requested=true ;;
    esac
  elif grep -Eq '"approve_requested"[[:space:]]*:[[:space:]]*true([,}[:space:]]|$)' "$run_params" 2>/dev/null; then
    approve_requested=true
  fi
  printf '%s\n' "$approve_requested"
}

gate_b_mode() {
  case "$(read_approve_requested "$1")" in
    true) printf '%s\n' explicit-prompt ;;
    *) printf '%s\n' auto-apply ;;
  esac
}

mk_design() {
  local d="$1" body_lines="${2:-20}" diff_lines="${3:-10}"
  mkdir -p "$d/.completed"
  : >"$d/.completed/step-2b"
  "${WRITE_RUN_PARAMS[@]}" --partition-requested false --brainstorm-requested false \
    --approve-requested false --output "$d/run-params.json" >/dev/null
  {
    printf '%s\n' '# Plan'
    i=1
    while [ "$i" -le "$body_lines" ]; do
      printf 'line %s\n' "$i"
      i=$((i + 1))
    done
    printf 'diff_lines: %s\n' "$diff_lines"
  } >"$d/plan.txt"
}

# Default run-params restore auto-apply; --per-round-approval restores the prompt branch.
D_AUTO="$TMP/auto"
mk_design "$D_AUTO"
[[ "$(gate_b_mode "$D_AUTO/run-params.json")" == auto-apply ]] || fail 'default approve_requested=false should auto-apply'

D_APPROVE="$TMP/approve"
mk_design "$D_APPROVE"
"${WRITE_RUN_PARAMS[@]}" --partition-requested false --brainstorm-requested false \
  --approve-requested true --output "$D_APPROVE/run-params.json" >/dev/null
[[ "$(gate_b_mode "$D_APPROVE/run-params.json")" == explicit-prompt ]] || fail '--per-round-approval should restore explicit prompt'

grep -Fq 'Gate B — auto-applying N accepted finding(s)' "$APPROVAL_GATES" \
  || fail 'approval-gates missing default auto-apply breadcrumb'
grep -Fq 'explicit per-round prompt' "$SKILL_MD" \
  || fail 'SKILL missing --per-round-approval explicit Gate B branch prose'
grep -Fq 'LOOP_STATUS=cap-reached' "$SKILL_MD" \
  || fail 'SKILL missing cap-reached Gate B bypass branch'

# Simulate the Apply-all rewrite surface: accepted findings have already been
# incorporated into plan.txt, then the shared dedup + postplan fence settles.
D_APPLY="$TMP/apply-all"
mk_design "$D_APPLY" 8 8
cat >"$D_APPLY/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Apply a retry constraint
- **Severity**: important
- **Concern**: Plan needs an explicit retry constraint.
EOF
python3 "$CLI" plan-review gate-b-dedup --design-tmpdir "$D_APPLY" --snapshot-trailers >/dev/null
{
  printf '%s\n' '# Plan'
  printf '%s\n' 'line 1'
  printf '%s\n' 'line 1'
  printf '%s\n' 'Retry failed validator auto-fix attempts from the original plan snapshot only.'
  printf '%s\n' 'diff_lines: 9'
} >"$D_APPLY/plan.txt"
DESIGN_TMPDIR="$D_APPLY" "$SETTLE" --plugin-root "$ROOT" --site gate-b --round-num 4 >"$D_APPLY/settle.out"
grep -Fq 'Retry failed validator auto-fix attempts from the original plan snapshot only.' "$D_APPLY/plan.txt" \
  || fail 'Apply-all simulated rewrite did not preserve accepted finding edit'
[[ "$(grep -Fc 'dedup-sweep: removed 1 duplicate line(s) from plan.txt' "$D_APPLY/settle.out")" -eq 1 ]] \
  || fail 'Apply-all settle should print one dedup sweep breadcrumb'
grep -Fq 'POSTPLAN_RC=0' "$D_APPLY/settle.out" \
  || fail 'Apply-all settle output missing clean postplan rc'
grep -Fq 'SETTLE_NEXT_ACTION=gate-b-continue' "$D_APPLY/settle.out" \
  || fail 'Apply-all settle output missing gate-b continue next action'
[[ -f "$D_APPLY/.completed/step-2b.5" ]] || fail 'Apply-all settle should preserve postplan clean marker behavior'
[[ "$(cat "$D_APPLY/.step3-round-4.phase")" == awaiting-continuation ]] \
  || fail 'Apply-all settle should write awaiting-continuation phase'

# Gate B shared post-apply uses design-postplan-emit --with-plan-size, so safety
# brakes still interrupt auto-apply when plan-size thresholds require it.
D_LARGE="$TMP/hard"
mk_design "$D_LARGE" 805 10
set +e
"${POSTPLAN_CLI[@]}" --design-tmpdir "$D_LARGE" --with-plan-size >"$D_LARGE/out.txt" 2>"$D_LARGE/err.txt"
rc=$?
set -e
[[ "$rc" -eq 12 ]] || fail "hard size brake expected rc 12, got $rc"
grep -Fq 'PLAN_SIZE_STATUS=plan-size-trigger' "$D_LARGE/.design-postplan-emit-result.env" \
  || fail 'hard size brake result env missing'

D_DRIFT="$TMP/drift"
mk_design "$D_DRIFT" 20 10
printf 'BASELINE_PLAN_LINES=5\nBASELINE_DIFF_LINES=5\n' >"$D_DRIFT/drift-baseline.env"
set +e
LARCH_DESIGN_DRIFT_MULTIPLE=2 "${POSTPLAN_CLI[@]}" --design-tmpdir "$D_DRIFT" --with-plan-size >"$D_DRIFT/out.txt" 2>"$D_DRIFT/err.txt"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail "drift size brake expected rc 0, got $rc"
grep -Fq 'PLAN_SIZE_STATUS=drift-advisory' "$D_DRIFT/.design-postplan-emit-result.env" \
  || fail 'drift size brake result env missing'


write_apply_postplan_stub() {
  local path="$1"
  cat >"$path" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >"$DESIGN_TMPDIR/postplan-argv.txt"
cat "$DESIGN_TMPDIR/postplan-output.txt"
if [[ -f "$DESIGN_TMPDIR/postplan-write-clean-marker" ]]; then
  mkdir -p "$DESIGN_TMPDIR/.completed"
  : >"$DESIGN_TMPDIR/.completed/step-2b.5"
fi
exit 0
STUB
  chmod +x "$path"
}

write_apply_dedup_stub() {
  local path="$1"
  cat >"$path" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'dedup stub\n'
exit 0
STUB
  chmod +x "$path"
}

write_apply_dedup_revise_stub() {
  local path="$1"
  cat >"$path" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'dedup revise stub\n'
exit 1
STUB
  chmod +x "$path"
}

POSTPLAN_STUB="$TMP/postplan-stub.sh"
DEDUP_STUB="$TMP/dedup-stub.sh"
DEDUP_REVISE_STUB="$TMP/dedup-revise-stub.sh"
write_apply_postplan_stub "$POSTPLAN_STUB"
write_apply_dedup_stub "$DEDUP_STUB"
write_apply_dedup_revise_stub "$DEDUP_REVISE_STUB"

run_stubbed_settle() {
  local d="$1" round="$2" site="${3:-gate-b}"
  DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" \
    DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" \
    DESIGN_TMPDIR="$d" "$SETTLE" --plugin-root "$ROOT" --site "$site" --round-num "$round"
}

# Wrapper-mediated postplan brakes relay while preserving Gate B phase markers.
for brake in 10 13; do
  d="$TMP/wrapper-brake-$brake"
  mk_design "$d" 5 5
  printf 'POSTPLAN_RC=%s\n' "$brake" >"$d/postplan-output.txt"
  set +e
  run_stubbed_settle "$d" "$brake" >"$d/settle.out"
  rc=$?
  set -e
  [[ "$rc" -eq "$brake" ]] || fail "stubbed postplan rc $brake should exit wrapper rc $brake, got $rc"
  [[ "$(cat "$d/.step3-round-$brake.phase")" == awaiting-postplan-operator ]] \
    || fail "stubbed postplan rc $brake should write awaiting-postplan-operator"
  case "$brake" in
    10) grep -Fq 'SETTLE_NEXT_ACTION=gate-b-validator-fail' "$d/settle.out" \
      || fail 'stubbed postplan rc 10 missing gate-b validator next action' ;;
    13) grep -Fq 'SETTLE_NEXT_ACTION=gate-b-split' "$d/settle.out" \
      || fail 'stubbed postplan rc 13 missing gate-b split next action' ;;
  esac
done

D_WRAP_12="$TMP/wrapper-12"
mk_design "$D_WRAP_12" 5 5
printf 'POSTPLAN_RC=12\n' >"$D_WRAP_12/postplan-output.txt"
set +e
run_stubbed_settle "$D_WRAP_12" 12 >"$D_WRAP_12/settle.out"
rc=$?
set -e
[[ "$rc" -eq 12 ]] || fail "stubbed postplan rc 12 should exit wrapper rc 12, got $rc"
grep -Fq 'SETTLE_NEXT_ACTION=gate-b-hard-size' "$D_WRAP_12/settle.out" \
  || fail 'stubbed postplan rc 12 missing gate-b hard-size next action'
[[ ! -e "$D_WRAP_12/.completed/step-2b.5" ]] \
  || fail 'stubbed postplan rc 12 should not write clean postplan marker'

D_WRAP_PAUSE="$TMP/wrapper-pause"
mk_design "$D_WRAP_PAUSE" 5 5
printf 'PAUSE_OK=true\n' >"$D_WRAP_PAUSE/postplan-output.txt"
set +e
run_stubbed_settle "$D_WRAP_PAUSE" 11 >"$D_WRAP_PAUSE/settle.out"
rc=$?
set -e
[[ "$rc" -eq 11 ]] || fail "stubbed pause output should exit wrapper rc 11, got $rc"
grep -Fq 'SETTLE_NEXT_ACTION=pause' "$D_WRAP_PAUSE/settle.out" \
  || fail 'stubbed pause output missing pause next action'
[[ "$(cat "$D_WRAP_PAUSE/.step3-round-11.phase")" == awaiting-post-apply ]] \
  || fail 'stubbed pause output should not write clean continuation phase'

D_WRAP_CLEAN="$TMP/wrapper-clean-stub"
mk_design "$D_WRAP_CLEAN" 5 5
printf 'POSTPLAN_RC=0\n' >"$D_WRAP_CLEAN/postplan-output.txt"
: >"$D_WRAP_CLEAN/postplan-write-clean-marker"
run_stubbed_settle "$D_WRAP_CLEAN" 14 >"$D_WRAP_CLEAN/settle.out"
grep -Fq 'SETTLE_NEXT_ACTION=gate-b-continue' "$D_WRAP_CLEAN/settle.out" \
  || fail 'stubbed clean rc missing gate-b continue next action'
[[ -f "$D_WRAP_CLEAN/.completed/step-2b.5" ]] \
  || fail 'stubbed clean rc should leave postplan clean marker behavior intact'
[[ "$(cat "$D_WRAP_CLEAN/.step3-round-14.phase")" == awaiting-continuation ]] \
  || fail 'stubbed clean rc should write awaiting-continuation'

D_DEDUP_REVISE="$TMP/dedup-revise"
mk_design "$D_DEDUP_REVISE" 5 5
set +e
DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_REVISE_STUB" \
  DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" \
  DESIGN_TMPDIR="$D_DEDUP_REVISE" "$SETTLE" --plugin-root "$ROOT" --site gate-b --round-num 15 >"$D_DEDUP_REVISE/settle.out"
rc=$?
set -e
[[ "$rc" -eq 1 ]] || fail "stubbed dedup revise should exit wrapper rc 1, got $rc"
grep -Fq 'SETTLE_NEXT_ACTION=dedup-revise' "$D_DEDUP_REVISE/settle.out" \
  || fail 'stubbed dedup revise missing dedup-revise next action'

D_GATE_A="$TMP/gate-a-clean"
mk_design "$D_GATE_A" 5 5
printf 'POSTPLAN_RC=0\n' >"$D_GATE_A/postplan-output.txt"
run_stubbed_settle "$D_GATE_A" 16 gate-a >"$D_GATE_A/settle.out"
grep -Fq 'SETTLE_NEXT_ACTION=gate-a-return' "$D_GATE_A/settle.out" \
  || fail 'gate-a clean rc missing gate-a return next action'

D_ROUND2_VALIDATOR="$TMP/discussion-round2-validator"
mk_design "$D_ROUND2_VALIDATOR" 5 5
printf 'POSTPLAN_RC=10\n' >"$D_ROUND2_VALIDATOR/postplan-output.txt"
set +e
run_stubbed_settle "$D_ROUND2_VALIDATOR" 17 discussion-round2 >"$D_ROUND2_VALIDATOR/settle.out"
rc=$?
set -e
[[ "$rc" -eq 10 ]] || fail "discussion-round2 validator stub should exit wrapper rc 10, got $rc"
grep -Fq 'SETTLE_NEXT_ACTION=gate-a-validator-fail' "$D_ROUND2_VALIDATOR/settle.out" \
  || fail 'discussion-round2 validator rc missing gate-a validator next action'

pass 'gate-b apply mode harness'
