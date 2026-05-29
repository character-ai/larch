#!/usr/bin/env bash
# Offline harness for assess-plan-round.sh
set -euo pipefail
export LARCH_QUIET_DISABLE=1
unset LARCH_BREADCRUMB_STREAM LARCH_DONE_SENTINEL LARCH_STATUS_FILE \
  LARCH_QUIET_LOG_FILE LARCH_BREADCRUMBS_SURFACED_FILE LARCH_PAIRED_PID_FILE || true

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/assess-plan-round.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/tapr.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
export CLAUDE_PLUGIN_ROOT="$ROOT"

write_params() {
  local wp="$1"
  printf '{"workflow_path":"%s"}\n' "$wp" >"$TMP/run-params.json"
}

setup_round2() {
  write_params HARD
  printf 'orig\n' >"$TMP/plan.txt-original"
  printf 'prev\n' >"$TMP/plan-after-round-1.txt"
  printf 'curr\n' >"$TMP/plan.txt"
  printf '2\n' >"$TMP/plan-review-round-cursor.txt"
  printf 'feat\n' >"$TMP/feature-description.txt"
}

cat >"$TMP/mock-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) DIR="${2:?}"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'DISPATCH_OK=true\n'
printf 'CLAUDE_ASSESSOR_PATH=%s/claude-plan-assessor-round-2.txt\n' "$DIR"
printf 'CODEX_ASSESSOR_PATH=%s/codex-plan-assessor-round-2.txt\n' "$DIR"
printf 'CURSOR_ASSESSOR_PATH=%s/cursor-plan-assessor-round-2.txt\n' "$DIR"
printf 'ASSESSMENT: WORSE\nREASONING: x\nQUALIFICATIONS: y\n' >"$DIR/claude-plan-assessor-round-2.txt"
printf 'ASSESSMENT: WORSE\nREASONING: x\nQUALIFICATIONS: y\n' >"$DIR/codex-plan-assessor-round-2.txt"
printf 'ASSESSMENT: TIE\nREASONING: x\nQUALIFICATIONS: y\n' >"$DIR/cursor-plan-assessor-round-2.txt"
STUB
chmod +x "$TMP/mock-dispatch.sh"

export LARCH_DISPATCH_PLAN_ASSESSORS_SH="$TMP/mock-dispatch.sh"
export LARCH_TALLY_PLAN_ASSESSOR_SH="$ROOT/skills/design/scripts/tally-plan-assessor.sh"
export LARCH_SNAPSHOT_PLAN_ROUND_SH="$ROOT/skills/design/scripts/snapshot-plan-round.sh"
unset IMPLEMENT_TMPDIR || true

write_params SIMPLE
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_VERDICT=skipped' || fail 'SIMPLE must skip'

write_params HARD
printf '1\n' >"$TMP/plan-review-round-cursor.txt"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_STATUS=skipped' || fail 'round 1 must emit skipped status'
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_VERDICT=skipped' || fail 'round 1 must skip'

setup_round2
rm -f "$TMP/feature-description.txt"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_STATUS=missing-snapshot' || fail 'missing feature file must skip before dispatch'
[[ ! -e "$TMP/assessor-verdict-round-2.txt" ]] || fail 'missing-snapshot path must not write verdict artifacts'
grep -Fq 'feature-description.txt' "$TMP/execution-issues.md" || fail 'missing feature file must append execution warning'

setup_round2
rm -f "$TMP/plan.txt-original"
rm -f "$TMP/execution-issues.md"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_STATUS=missing-snapshot' || fail 'missing original snapshot must skip before dispatch'
[[ ! -e "$TMP/assessor-verdict-round-2.txt" ]] || fail 'missing original snapshot path must not write verdict artifacts'
grep -Fq 'plan.txt-original' "$TMP/execution-issues.md" || fail 'missing original snapshot must append execution warning'

setup_round2
rm -f "$TMP/plan-after-round-1.txt"
rm -f "$TMP/execution-issues.md"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_STATUS=missing-snapshot' || fail 'missing prior-round snapshot must skip before dispatch'
[[ ! -e "$TMP/assessor-verdict-round-2.txt" ]] || fail 'missing prior-round snapshot path must not write verdict artifacts'
grep -Fq 'plan-after-round-1.txt' "$TMP/execution-issues.md" || fail 'missing prior-round snapshot must append execution warning'

setup_round2
printf 'stale\n' >"$TMP/claude-plan-assessor-round-2.txt"
printf 'stale diag\n' >"$TMP/claude-plan-assessor-round-2.txt.diag"
printf '{"stale":true}\n' >"$TMP/claude-plan-assessor-round-2.txt.json"
printf 'stale\n' >"$TMP/assessor-verdict-round-2.txt"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_VERDICT=worse-majority' || fail 'round2 pipeline failed'
[[ -f "$TMP/assessor-verdict-round-2.txt" ]] || fail 'missing verdict file'
grep -Fqx 'WORSE: x x' "$TMP/assessor-verdict-round-2.txt" || fail 'stale verdict artifact was not replaced'
grep -Fqx 'ASSESSMENT: WORSE' "$TMP/claude-plan-assessor-round-2.txt" || fail 'stale assessor txt artifact was not replaced'
[[ ! -e "$TMP/claude-plan-assessor-round-2.txt.diag" ]] || fail 'stale assessor diag sidecar should be removed before dispatch'
[[ ! -e "$TMP/claude-plan-assessor-round-2.txt.json" ]] || fail 'stale assessor json sidecar should be removed before dispatch'

cat >"$TMP/mock-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) DIR="${2:?}"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'DISPATCH_OK=false\n'
printf 'CLAUDE_ASSESSOR_PATH=%s/claude-plan-assessor-round-2.txt\n' "$DIR"
printf 'CODEX_ASSESSOR_PATH=%s/codex-plan-assessor-round-2.txt\n' "$DIR"
printf 'CURSOR_ASSESSOR_PATH=%s/cursor-plan-assessor-round-2.txt\n' "$DIR"
printf 'ASSESSMENT: WORSE\nREASONING: codex\nQUALIFICATIONS: cq\n' >"$DIR/codex-plan-assessor-round-2.txt"
printf 'ASSESSMENT: WORSE\nREASONING: cursor\nQUALIFICATIONS: uq\n' >"$DIR/cursor-plan-assessor-round-2.txt"
STUB
chmod +x "$TMP/mock-dispatch.sh"
setup_round2
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_STATUS=degraded-default-open' || fail 'dispatch failure must degrade open'
grep -Fq 'ASSESSOR_VERDICT=not-worse' "$TMP/assessor-verdict-round-2.txt.env" || fail 'dispatch failure should synthesize not-worse verdict env'
grep -Fq 'EFFECTIVE_ASSESSORS=0' "$TMP/assessor-verdict-round-2.txt.env" || fail 'dispatch failure should not tally partial outputs'
grep -Fq 'Plan-quality assessor panel degraded; no WORSE-majority verdict available.' "$TMP/assessor-verdict-round-2.txt.env" || fail 'dispatch failure should synthesize degraded summary'

cat >"$TMP/mock-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) DIR="${2:?}"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'DISPATCH_OK=true\n'
printf 'CLAUDE_ASSESSOR_PATH=%s/claude-plan-assessor-round-2.txt\n' "$DIR"
printf 'CODEX_ASSESSOR_PATH=%s/codex-plan-assessor-round-2.txt\n' "$DIR"
printf 'CURSOR_ASSESSOR_PATH=%s/cursor-plan-assessor-round-2.txt\n' "$DIR"
STUB
chmod +x "$TMP/mock-dispatch.sh"
setup_round2
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_STATUS=degraded-default-open' || fail '0/3 effective assessors must degrade open'
grep -Fq 'EFFECTIVE_ASSESSORS=0' "$TMP/assessor-verdict-round-2.txt.env" || fail '0/3 effective assessors must record zero'

cat >"$TMP/mock-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) DIR="${2:?}"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'DISPATCH_OK=true\n'
printf 'CLAUDE_ASSESSOR_PATH=%s/claude-plan-assessor-round-2.txt\n' "$DIR"
printf 'CODEX_ASSESSOR_PATH=%s/codex-plan-assessor-round-2.txt\n' "$DIR"
printf 'CURSOR_ASSESSOR_PATH=%s/cursor-plan-assessor-round-2.txt\n' "$DIR"
printf 'ASSESSMENT: WORSE\nREASONING: c\nQUALIFICATIONS: cq\n' >"$DIR/claude-plan-assessor-round-2.txt"
STUB
chmod +x "$TMP/mock-dispatch.sh"

cat >"$TMP/mock-tally.sh" <<'STUB'
#!/usr/bin/env bash
echo "tally failed" >&2
exit 7
STUB
chmod +x "$TMP/mock-tally.sh"
export LARCH_TALLY_PLAN_ASSESSOR_SH="$TMP/mock-tally.sh"
setup_round2
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_STATUS=degraded-default-open' || fail 'tally failure should degrade open'
grep -Fq 'ASSESSOR_VERDICT=not-worse' "$TMP/assessor-verdict-round-2.txt.env" || fail 'tally failure should synthesize verdict env'

cat >"$TMP/mock-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
DIR="" ROUND="" 
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) DIR="${2:?}"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'DISPATCH_OK=true\n'
printf 'CLAUDE_ASSESSOR_PATH=%s/claude-plan-assessor-round-2.txt\n' "$DIR"
printf 'CODEX_ASSESSOR_PATH=%s/codex-plan-assessor-round-2.txt\n' "$DIR"
printf 'CURSOR_ASSESSOR_PATH=%s/cursor-plan-assessor-round-2.txt\n' "$DIR"
printf 'ASSESSMENT: TIE\nREASONING: q\nQUALIFICATIONS: z\n' >"$DIR/claude-plan-assessor-round-2.txt"
STUB
chmod +x "$TMP/mock-dispatch.sh"
export LARCH_TALLY_PLAN_ASSESSOR_SH="$ROOT/skills/design/scripts/tally-plan-assessor.sh"
setup_round2
rm -f "$TMP/breadcrumbs/assessor-round-2.dispatch.kv" "$TMP/breadcrumbs/assessor-round-2.quiet.log"
out=$("$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_VERDICT=not-worse' || fail 'production quiet-mode wiring path failed'
[[ -f "$TMP/breadcrumbs/assessor-round-2.dispatch.kv" ]] || fail 'dispatch kv file missing'
[[ -f "$TMP/breadcrumbs/assessor-round-2.quiet.log" ]] || fail 'quiet log missing'

cat >"$TMP/mock-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) DIR="${2:?}"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'DISPATCH_OK=true\n'
printf 'CLAUDE_ASSESSOR_PATH=%s/../../escape.txt\n' "$DIR"
printf 'CODEX_ASSESSOR_PATH=%s/codex-plan-assessor-round-2.txt\n' "$DIR"
printf 'CURSOR_ASSESSOR_PATH=%s/cursor-plan-assessor-round-2.txt\n' "$DIR"
printf 'ASSESSMENT: WORSE\nREASONING: x\nQUALIFICATIONS: y\n' >"$DIR/codex-plan-assessor-round-2.txt"
printf 'ASSESSMENT: WORSE\nREASONING: x\nQUALIFICATIONS: y\n' >"$DIR/cursor-plan-assessor-round-2.txt"
STUB
chmod +x "$TMP/mock-dispatch.sh"
setup_round2
rm -f "$TMP/execution-issues.md"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_STATUS=degraded-default-open' || fail 'dispatch path escape must degrade open'
grep -Fqx 'NOT_WORSE' "$TMP/assessor-verdict-round-2.txt" || fail 'dispatch path escape must synthesize NOT_WORSE verdict'

setup_round2
mkdir -p "$TMP/implement-tmp"
printf 'implement feature\n' >"$TMP/implement-tmp/feature-description.txt"
printf 'design feature\n' >"$TMP/feature-description.txt"
cat >"$TMP/mock-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
DIR=""
feature=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) DIR="${2:?}"; shift 2 ;;
    --feature-file) feature="${2:?}"; shift 2 ;;
    --round-num|--plan-original|--plan-prev|--plan-current|--codex-present|--cursor-present|--timeout) shift 2 ;;
    *) shift ;;
  esac
done
[[ -n "$feature" && -n "$DIR" ]] || exit 2
printf 'DISPATCH_OK=true\n'
printf 'CLAUDE_ASSESSOR_PATH=%s/claude-plan-assessor-round-2.txt\n' "$DIR"
printf 'CODEX_ASSESSOR_PATH=%s/codex-plan-assessor-round-2.txt\n' "$DIR"
printf 'CURSOR_ASSESSOR_PATH=%s/cursor-plan-assessor-round-2.txt\n' "$DIR"
printf '%s\n' "$feature" >"$DIR/feature-path-seen.txt"
printf 'ASSESSMENT: TIE\nREASONING: q\nQUALIFICATIONS: z\n' >"$DIR/claude-plan-assessor-round-2.txt"
printf 'ASSESSMENT: TIE\nREASONING: q\nQUALIFICATIONS: z\n' >"$DIR/codex-plan-assessor-round-2.txt"
printf 'ASSESSMENT: TIE\nREASONING: q\nQUALIFICATIONS: z\n' >"$DIR/cursor-plan-assessor-round-2.txt"
STUB
chmod +x "$TMP/mock-dispatch.sh"
out=$(IMPLEMENT_TMPDIR="$TMP/implement-tmp" LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_VERDICT=not-worse' || fail 'design feature preference path failed'
grep -Fqx "$(cd "$TMP" && pwd -P)/feature-description.txt" "$TMP/feature-path-seen.txt" || fail 'design tmpdir feature-description.txt should win over implement tmpdir copy'

# Two-entry Step 3 integration: cursor advance, snapshots, round-2 assessor firing.
advance_step3_cursor() {
  local tmp="$1" cursor=1 next cursor_out cursor_line
  cursor_out=$("$ROOT/skills/design/scripts/snapshot-plan-round.sh" \
    read-cursor --design-tmpdir "$tmp")
  while IFS= read -r cursor_line || [[ -n "$cursor_line" ]]; do
    case "$cursor_line" in
      ROUND_CURSOR=*) cursor="${cursor_line#ROUND_CURSOR=}" ;;
    esac
  done <<<"$cursor_out"
  case "$cursor" in ''|*[!0-9]*|0) cursor=1 ;; esac
  cursor=$((10#$cursor))
  if [[ -f "$tmp/plan-after-round-${cursor}.txt" ]]; then
    next=$((cursor + 1))
    "$ROOT/skills/design/scripts/snapshot-plan-round.sh" \
      write-cursor --design-tmpdir "$tmp" --value "$next" >/dev/null \
      || fail "advance_step3_cursor: write-cursor failed for round $next"
    cursor=$next
  fi
  printf '%s' "$cursor"
}

write_params_for() {
  local tmp="$1" wp="$2"
  printf '{"workflow_path":"%s"}\n' "$wp" >"$tmp/run-params.json"
}

echo "=== two-entry Step 3 cursor + round-2 assessor integration ==="
case_tmp=$(mktemp -d "${TMPDIR:-/tmp}/tapr-two-entry.XXXXXX")
saved_dispatch_plan_assessors_sh=${LARCH_DISPATCH_PLAN_ASSESSORS_SH-__UNSET__}
saved_breadcrumb_monitor_sh=${LARCH_BREADCRUMB_MONITOR_SH-__UNSET__}
saved_tally_plan_assessor_sh=${LARCH_TALLY_PLAN_ASSESSOR_SH-__UNSET__}
saved_snapshot_plan_round_sh=${LARCH_SNAPSHOT_PLAN_ROUND_SH-__UNSET__}
rm -f "$case_tmp"/plan-after-round-*.txt \
  "$case_tmp"/plan-review-round-cursor.txt \
  "$case_tmp"/assessor-verdict-round-*.txt \
  "$case_tmp"/assessor-verdict-round-*.env \
  "$case_tmp"/plan.txt-original \
  "$case_tmp"/claude-plan-assessor-round-*.txt \
  "$case_tmp"/codex-plan-assessor-round-*.txt \
  "$case_tmp"/cursor-plan-assessor-round-*.txt 2>/dev/null || true
write_params_for "$case_tmp" HARD

cat >"$case_tmp/mock-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) DIR="${2:?}"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'DISPATCH_OK=true\n'
printf 'CLAUDE_ASSESSOR_PATH=%s/claude-plan-assessor-round-2.txt\n' "$DIR"
printf 'CODEX_ASSESSOR_PATH=%s/codex-plan-assessor-round-2.txt\n' "$DIR"
printf 'CURSOR_ASSESSOR_PATH=%s/cursor-plan-assessor-round-2.txt\n' "$DIR"
printf 'ASSESSMENT: WORSE\nREASONING: x\nQUALIFICATIONS: y\n' >"$DIR/claude-plan-assessor-round-2.txt"
printf 'ASSESSMENT: WORSE\nREASONING: x\nQUALIFICATIONS: y\n' >"$DIR/codex-plan-assessor-round-2.txt"
printf 'ASSESSMENT: TIE\nREASONING: x\nQUALIFICATIONS: y\n' >"$DIR/cursor-plan-assessor-round-2.txt"
STUB
chmod +x "$case_tmp/mock-dispatch.sh"
cat >"$case_tmp/mock-monitor.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$case_tmp/mock-monitor.sh"
export LARCH_DISPATCH_PLAN_ASSESSORS_SH="$case_tmp/mock-dispatch.sh"
export LARCH_BREADCRUMB_MONITOR_SH="$case_tmp/mock-monitor.sh"
export LARCH_TALLY_PLAN_ASSESSOR_SH="$ROOT/skills/design/scripts/tally-plan-assessor.sh"
export LARCH_SNAPSHOT_PLAN_ROUND_SH="$ROOT/skills/design/scripts/snapshot-plan-round.sh"

printf 'plan entry1\n' >"$case_tmp/plan.txt"
printf 'feature entry1\n' >"$case_tmp/feature-description.txt"
"$ROOT/skills/design/scripts/snapshot-plan-round.sh" write-original --design-tmpdir "$case_tmp" >/dev/null
cursor1=$(advance_step3_cursor "$case_tmp")
[[ "$cursor1" == "1" ]] || fail 'Entry 1 cursor must remain 1 before first write-after'
"$ROOT/skills/design/scripts/snapshot-plan-round.sh" write-after --design-tmpdir "$case_tmp" --round 1 >/dev/null
out1=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$case_tmp" --codex-present true --cursor-present true)
printf '%s\n' "$out1" | grep -Fq 'ASSESSOR_STATUS=skipped' || fail 'Entry 1 assessor must skip'
printf '%s\n' "$out1" | grep -Fq 'ASSESSOR_VERDICT=skipped' || fail 'Entry 1 assessor verdict must be skipped'
[[ ! -e "$case_tmp/assessor-verdict-round-1.txt" ]] || fail 'Entry 1 must not write round-1 assessor verdict'

printf 'plan entry2 revised\n' >"$case_tmp/plan.txt"
cursor2=$(advance_step3_cursor "$case_tmp")
[[ "$cursor2" == "2" ]] || fail 'Entry 2 cursor must advance to 2'
"$ROOT/skills/design/scripts/snapshot-plan-round.sh" write-after --design-tmpdir "$case_tmp" --round 2 >/dev/null
[[ -f "$case_tmp/plan-after-round-1.txt" && -f "$case_tmp/plan-after-round-2.txt" ]] || fail 'round 1 and 2 snapshots must exist'
cmp -s "$case_tmp/plan-after-round-1.txt" "$case_tmp/plan-after-round-2.txt" && fail 'round snapshots must differ'
out2=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$case_tmp" --codex-present true --cursor-present true)
printf '%s\n' "$out2" | grep -Fq 'ASSESSOR_STATUS=ok' || fail 'Entry 2 assessor must fire'
printf '%s\n' "$out2" | grep -Fq 'ASSESSOR_VERDICT=worse-majority' || fail 'Entry 2 assessor verdict must be worse-majority'
printf '%s\n' "$out2" | grep -Fq 'EFFECTIVE_ASSESSORS=3' || fail 'Entry 2 must tally three effective assessors'
[[ -f "$case_tmp/assessor-verdict-round-2.txt" ]] || fail 'Entry 2 must write assessor-verdict-round-2.txt'
rm -rf "$case_tmp"
if [[ "$saved_dispatch_plan_assessors_sh" == "__UNSET__" ]]; then
  unset LARCH_DISPATCH_PLAN_ASSESSORS_SH
else
  export LARCH_DISPATCH_PLAN_ASSESSORS_SH="$saved_dispatch_plan_assessors_sh"
fi
if [[ "$saved_breadcrumb_monitor_sh" == "__UNSET__" ]]; then
  unset LARCH_BREADCRUMB_MONITOR_SH
else
  export LARCH_BREADCRUMB_MONITOR_SH="$saved_breadcrumb_monitor_sh"
fi
if [[ "$saved_tally_plan_assessor_sh" == "__UNSET__" ]]; then
  unset LARCH_TALLY_PLAN_ASSESSOR_SH
else
  export LARCH_TALLY_PLAN_ASSESSOR_SH="$saved_tally_plan_assessor_sh"
fi
if [[ "$saved_snapshot_plan_round_sh" == "__UNSET__" ]]; then
  unset LARCH_SNAPSHOT_PLAN_ROUND_SH
else
  export LARCH_SNAPSHOT_PLAN_ROUND_SH="$saved_snapshot_plan_round_sh"
fi

pass 'assess-plan-round harness'
