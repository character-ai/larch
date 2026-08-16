#!/usr/bin/env bash
# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
# Offline coverage for Gate B mode selection and safety-brake handoff.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
CLI="$ROOT/python/cli.py"
LARCH="$ROOT/scripts/larch.sh"
POSTPLAN_CLI=(python3 "$CLI" design postplan-emit)
SETTLE=(python3 "$CLI" design step35-settle)
SKILL_MD="$ROOT/skills/design/SKILL.md"
APPROVAL_GATES="$ROOT/skills/design/references/approval-gates-gate-b.md"

# `session write-run-params` moved to the Rust owner in issue #8058, and its own
# coverage lives in the Rust parity goldens. This harness only needs the schema v3
# fixture the Gate B selector reads, so it writes one directly and stays hermetic.
write_run_params() {
  local output="$1" approve="$2"
  cat >"$output" <<JSON
{
  "schema_version": 3,
  "partition_requested": false,
  "brainstorm_requested": false,
  "approve_requested": $approve,
  "skip_approve_requested": false,
  "difficulty_override": ""
}
JSON
}

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

python3 -m py_compile "$ROOT/python/larch/design/design_postplan.py" || fail 'design_postplan.py py_compile failed'
python3 -m py_compile "$ROOT/python/larch/design/design_gate_render.py" || fail 'design_gate_render.py py_compile failed'
python3 -m py_compile "$ROOT/python/larch/design/design_settle.py" || fail 'design_settle.py py_compile failed'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/tgbam.XXXXXX")
TMP=$(cd "$TMP" && pwd -P)
trap 'rm -rf "$TMP"' EXIT

# The Bash-harness CI lane intentionally has no compiled Rust artifact. Rust
# command parity is covered by the focused Cargo tests; this harness supplies
# only the two command side effects needed to exercise the Gate B caller path.
if [[ -z "${LARCH_BINARY:-}" ]]; then
  PLUGIN_VERSION=$(awk -F '"' '$2 == "version" { print $4 }' "$ROOT/.claude-plugin/plugin.json")
  case "$(uname -s):$(uname -m)" in
    Darwin:arm64|Darwin:aarch64) LARCH_TARGET=aarch64-apple-darwin ;;
    Darwin:x86_64|Darwin:amd64) LARCH_TARGET=x86_64-apple-darwin ;;
    Linux:arm64|Linux:aarch64) LARCH_TARGET=aarch64-unknown-linux-gnu ;;
    Linux:x86_64|Linux:amd64) LARCH_TARGET=x86_64-unknown-linux-gnu ;;
    *) fail 'unsupported harness target' ;;
  esac
  export LARCH_BINARY="$TMP/larch-fixture"
  cat >"$LARCH_BINARY" <<EOF
#!/usr/bin/env bash
set -u
if [[ "\${1:-}" == --version ]]; then printf '%s\n' 'larch $PLUGIN_VERSION'; exit 0; fi
if [[ "\${1:-}" == bootstrap && "\${2:-}" == self-check ]]; then
  printf '%s\n' '{"schema_version":1,"version":"$PLUGIN_VERSION","target":"$LARCH_TARGET"}'
  exit 0
fi
if [[ "\${1:-}" == plan-review && "\${2:-}" == json-get-bool ]]; then
  printf 'false\n'
  exit 0
fi
if [[ "\${1:-}" == plan && "\${2:-}" == validate ]]; then
  printf '%s\n' 'VALIDATE_STATUS=ok' 'VALIDATE_DEFECT_COUNT=0' 'VALIDATE_SKIPPED_COUNT=0' 'VALIDATE_UNSAFE_TOKEN_COUNT=0'
  exit 0
fi
if [[ "\${1:-}" == plan && "\${2:-}" == check-size ]]; then
  shift 2
  design=""
  while [[ \$# -gt 0 ]]; do
    case "\$1" in
      --design-tmpdir) design="\$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  plan_lines=\$(wc -l <"\$design/plan.txt" | tr -d ' ')
  diff_lines=\$(awk '/^diff_lines: [0-9]+\$/ { value=\$2 } END { print value+0 }' "\$design/plan.txt")
  size_trigger=false
  drift_trigger=false
  if [[ "\$plan_lines" -ge 800 ]]; then
    size_trigger=true
  fi
  if [[ -f "\$design/drift-baseline.env" ]]; then
    baseline_plan=\$(awk -F= '\$1=="BASELINE_PLAN_LINES" { print \$2+0 }' "\$design/drift-baseline.env")
    multiple=\${LARCH_DESIGN_DRIFT_MULTIPLE:-2}
    if [[ "\$baseline_plan" -gt 0 && "\$plan_lines" -ge \$((baseline_plan * multiple)) ]]; then
      drift_trigger=true
    fi
  fi
  printf 'PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=%s\nDRIFT_TRIGGER_FIRED=%s\nPLAN_LINES=%s\nDIFF_LINES=%s\n' \
    "\$size_trigger" "\$drift_trigger" "\$plan_lines" "\$diff_lines"
  exit 0
fi
if [[ "\${1:-}" == plan-review && "\${2:-}" == gate-b-dedup ]]; then
  shift 2
  design="" snapshot=false dedup=false
  while [[ \$# -gt 0 ]]; do
    case "\$1" in
      --design-tmpdir) design="\$2"; shift 2 ;;
      --snapshot-trailers) snapshot=true; shift ;;
      --dedup) dedup=true; shift ;;
      *) shift ;;
    esac
  done
  if [[ "\$snapshot" == true ]]; then
    : >"\$design/.gate-b-optional-trailer-keys"
    : >"\$design/.gate-b-optional-trailer-keys.values"
    printf '%s\n' 'GATE_B_DEDUP_STATUS=snapshot'
    exit 0
  fi
  if [[ "\$dedup" == true ]]; then
    before=\$(wc -l <"\$design/plan.txt")
    awk '!seen[\$0]++' "\$design/plan.txt" >"\$design/plan.txt.tmp"
    after=\$(wc -l <"\$design/plan.txt.tmp")
    mv "\$design/plan.txt.tmp" "\$design/plan.txt"
    printf 'dedup-sweep: removed %s duplicate line(s) from plan.txt\n' "\$((before - after))"
    printf '%s\n' 'GATE_B_DEDUP_STATUS=ok'
    exit 0
  fi
fi
if [[ "\${1:-}" == plan-review && "\${2:-}" == emit ]]; then
  shift 2
  design=""
  while [[ \$# -gt 0 ]]; do
    case "\$1" in
      --design-tmpdir) design="\$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  diff_lines=\$(awk '/^diff_lines: [0-9]+\$/ { value=\$2 } END { print value }' "\$design/plan.txt")
  [[ -n "\$diff_lines" ]] || { printf '%s\n' 'EMIT_PLAN_STATUS=missing-diff-lines'; exit 1; }
  printf '%s\n' "\$diff_lines" >"\$design/diff-lines.txt"
  printf 'EMIT_PLAN_STATUS=ok\nDIFF_LINES=%s\n' "\$diff_lines"
  exit 0
fi
exit 2
EOF
  chmod +x "$LARCH_BINARY"
fi

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
  write_run_params "$d/run-params.json" false
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
write_run_params "$D_APPROVE/run-params.json" true
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
"$LARCH" plan-review gate-b-dedup --design-tmpdir "$D_APPLY" --snapshot-trailers >/dev/null
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
