#!/usr/bin/env bash
# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
# Offline coverage for Gate B mode selection and safety-brake handoff.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
WRITE_RUN_PARAMS=(python3 "$ROOT/python/cli.py" session write-run-params)
CLI="$ROOT/python/cli.py"
POSTPLAN_CLI=(python3 "$CLI" design postplan-emit)
SETTLE=(python3 "$CLI" design step35-settle)
SKILL_MD="$ROOT/skills/design/SKILL.md"
APPROVAL_GATES="$ROOT/skills/design/references/approval-gates-gate-b.md"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

python3 -m py_compile "$ROOT/python/larch/design/design_postplan.py" || fail 'design_postplan.py py_compile failed'
python3 -m py_compile "$ROOT/python/larch/design/design_gate_render.py" || fail 'design_gate_render.py py_compile failed'
python3 -m py_compile "$ROOT/python/larch/review/plan_review.py" || fail 'plan_review.py py_compile failed'
python3 -m py_compile "$ROOT/python/larch/design/design_settle.py" || fail 'design_settle.py py_compile failed'

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
    printf '%s\n' '## Files to modify/create'
    printf '%s\n' '### UPDATED: README.md'
    printf '%s\n' '## Closed decisions and ownership'
    printf '%s\n' 'Keep the existing Gate B owner.'
    printf '%s\n' '## Ordered implementation'
    printf '%s\n' '1. Apply the accepted finding.'
    printf '%s\n' '## Acceptance'
    printf '%s\n' 'The Gate B harness passes.'
    printf '%s\n' '## Breaking changes and migration'
    printf '%s\n' 'None.'
    printf '%s\n' '## Approach'
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

python3 "$CLI" design render-gate --gate B --accepted-count 3 --approve-requested false \
  | grep -Fq 'AUTO_APPLY_MESSAGE=ℹ 3.5: Gate B — auto-applying 3 accepted finding(s)' \
  || fail 'render-gate missing default auto-apply breadcrumb'
grep -Fq 'python/cli.py design render-gate --gate B --accepted-count "$N" --approve-requested false' "$APPROVAL_GATES" \
  || fail 'approval-gates missing default auto-apply renderer delegation'
grep -Fq 'explicit per-round prompt' "$SKILL_MD" \
  || fail 'SKILL missing --per-round-approval explicit Gate B branch prose'
grep -Fq 'NEXT_ACTION=step3b-bypass' "$SKILL_MD" \
  || fail 'SKILL missing Gate B bypass routing row'
grep -Fq 'When `LOOP_STATUS=cap-reached` or `TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached`, do not enter Gate B because stale accepted findings from an earlier round would re-surface.' "$SKILL_MD" \
  || fail 'SKILL missing cap-reached stale-findings Gate B bypass rationale'

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
  printf '%s\n' '## Files to modify/create'
  printf '%s\n' '### UPDATED: README.md'
  printf '%s\n' '## Closed decisions and ownership'
  printf '%s\n' 'Keep the existing Gate B owner.'
  printf '%s\n' '## Ordered implementation'
  printf '%s\n' '1. Apply the accepted finding.'
  printf '%s\n' '## Acceptance'
  printf '%s\n' 'The Gate B harness passes.'
  printf '%s\n' '## Breaking changes and migration'
  printf '%s\n' 'None.'
  printf '%s\n' '## Approach'
  printf '%s\n' 'line 1'
  printf '%s\n' 'line 1'
  printf '%s\n' 'Retry failed validator auto-fix attempts from the original plan snapshot only.'
  printf '%s\n' 'diff_lines: 9'
} >"$D_APPLY/plan.txt"
DESIGN_TMPDIR="$D_APPLY" "${SETTLE[@]}" --plugin-root "$ROOT" --site gate-b --round-num 4 >"$D_APPLY/settle.out"
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

pass 'gate-b apply mode harness'
