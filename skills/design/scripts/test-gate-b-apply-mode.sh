#!/usr/bin/env bash
# Offline coverage for Gate B mode selection and safety-brake handoff.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
WRITE_RUN_PARAMS="$ROOT/scripts/write-run-params.sh"
POSTPLAN="$ROOT/skills/design/scripts/design-postplan-emit.sh"
GATE_B_DEDUP="$ROOT/skills/design/scripts/gate-b-dedup-plan.sh"
SKILL_MD="$ROOT/skills/design/SKILL.md"
APPROVAL_GATES="$ROOT/skills/design/references/approval-gates.md"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

bash -n "$POSTPLAN" || fail 'design-postplan-emit bash -n failed'
bash -n "$GATE_B_DEDUP" || fail 'gate-b-dedup-plan bash -n failed'

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
  "$WRITE_RUN_PARAMS" --classification HARD --partition-requested false --brainstorm-requested false \
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

# Default run-params restore auto-apply; --approve restores the prompt branch.
D_AUTO="$TMP/auto"
mk_design "$D_AUTO"
[[ "$(gate_b_mode "$D_AUTO/run-params.json")" == auto-apply ]] || fail 'default approve_requested=false should auto-apply'

D_APPROVE="$TMP/approve"
mk_design "$D_APPROVE"
"$WRITE_RUN_PARAMS" --classification HARD --partition-requested false --brainstorm-requested false \
  --approve-requested true --output "$D_APPROVE/run-params.json" >/dev/null
[[ "$(gate_b_mode "$D_APPROVE/run-params.json")" == explicit-prompt ]] || fail '--approve should restore explicit prompt'

grep -Fq 'Gate B — auto-applying N accepted finding(s)' "$APPROVAL_GATES" \
  || fail 'approval-gates missing default auto-apply breadcrumb'
grep -Fq 'explicit per-round prompt' "$SKILL_MD" \
  || fail 'SKILL missing --approve explicit Gate B branch prose'
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
"$GATE_B_DEDUP" --design-tmpdir "$D_APPLY" --snapshot-trailers >/dev/null
{
  printf '%s\n' '# Plan'
  printf '%s\n' 'line 1'
  printf '%s\n' 'line 1'
  printf '%s\n' 'Retry failed validator auto-fix attempts from the original plan snapshot only.'
  printf '%s\n' 'diff_lines: 9'
} >"$D_APPLY/plan.txt"
"$GATE_B_DEDUP" --design-tmpdir "$D_APPLY" --dedup >"$D_APPLY/dedup.out"
grep -Fq 'Retry failed validator auto-fix attempts from the original plan snapshot only.' "$D_APPLY/plan.txt" \
  || fail 'Apply-all simulated rewrite did not preserve accepted finding edit'
grep -Fq 'dedup-sweep: removed 1 duplicate line(s) from plan.txt' "$D_APPLY/dedup.out" \
  || fail 'Apply-all dedup sweep did not remove duplicate line'
set +e
"$POSTPLAN" --design-tmpdir "$D_APPLY" --with-plan-size >"$D_APPLY/out.txt" 2>"$D_APPLY/err.txt"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail "Apply-all postplan expected rc 0, got $rc"
grep -Fq 'POSTPLAN_EMIT_STATUS=ok' "$D_APPLY/.design-postplan-emit-result.env" \
  || fail 'Apply-all postplan result env missing ok status'

# Gate B shared post-apply uses design-postplan-emit --with-plan-size, so safety
# brakes still interrupt auto-apply when plan-size thresholds require it.
D_HARD="$TMP/hard"
mk_design "$D_HARD" 805 10
set +e
"$POSTPLAN" --design-tmpdir "$D_HARD" --with-plan-size >"$D_HARD/out.txt" 2>"$D_HARD/err.txt"
rc=$?
set -e
[[ "$rc" -eq 12 ]] || fail "hard size brake expected rc 12, got $rc"
grep -Fq 'PLAN_SIZE_STATUS=hard' "$D_HARD/.design-postplan-emit-result.env" \
  || fail 'hard size brake result env missing'

D_DRIFT="$TMP/drift"
mk_design "$D_DRIFT" 20 10
printf 'BASELINE_PLAN_LINES=5\nBASELINE_DIFF_LINES=5\n' >"$D_DRIFT/drift-baseline.env"
set +e
LARCH_DESIGN_DRIFT_MULTIPLE=2 "$POSTPLAN" --design-tmpdir "$D_DRIFT" --with-plan-size >"$D_DRIFT/out.txt" 2>"$D_DRIFT/err.txt"
rc=$?
set -e
[[ "$rc" -eq 14 ]] || fail "drift size brake expected rc 14, got $rc"
grep -Fq 'PLAN_SIZE_STATUS=drift' "$D_DRIFT/.design-postplan-emit-result.env" \
  || fail 'drift size brake result env missing'

pass 'gate-b apply mode harness'
