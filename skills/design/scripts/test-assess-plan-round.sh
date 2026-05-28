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

cat >"$TMP/mock-monitor.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$TMP/mock-monitor.sh"

export LARCH_DISPATCH_PLAN_ASSESSORS_SH="$TMP/mock-dispatch.sh"
export LARCH_BREADCRUMB_MONITOR_SH="$TMP/mock-monitor.sh"
export LARCH_TALLY_PLAN_ASSESSOR_SH="$ROOT/skills/design/scripts/tally-plan-assessor.sh"
export LARCH_SNAPSHOT_PLAN_ROUND_SH="$ROOT/skills/design/scripts/snapshot-plan-round.sh"
unset IMPLEMENT_TMPDIR || true

write_params SIMPLE
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_VERDICT=skipped' || fail 'SIMPLE must skip'

write_params TRIVIAL
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_VERDICT=skipped' || fail 'TRIVIAL must skip'

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
printf 'stale\n' >"$TMP/assessor-verdict-round-2.txt"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_VERDICT=worse-majority' || fail 'round2 pipeline failed'
[[ -f "$TMP/assessor-verdict-round-2.txt" ]] || fail 'missing verdict file'
grep -Fqx 'WORSE: x x' "$TMP/assessor-verdict-round-2.txt" || fail 'stale verdict artifact was not replaced'

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
cat >"$TMP/mock-monitor.sh" <<'STUB'
#!/usr/bin/env bash
exit 6
STUB
chmod +x "$TMP/mock-monitor.sh"
setup_round2
printf 'stale worse\n' >"$TMP/assessor-verdict-round-2.txt"
out=$(LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_STATUS=degraded-default-open' || fail 'monitor failure must degrade open'
grep -Fqx 'NOT_WORSE' "$TMP/assessor-verdict-round-2.txt" || fail 'monitor failure must overwrite stale verdict artifact'

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
cat >"$TMP/mock-monitor.sh" <<'STUB'
#!/usr/bin/env bash
quiet=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet-log) quiet="${2:?}"; shift 2 ;;
    *) shift ;;
  esac
done
[[ -n "$quiet" && -f "$quiet" ]] || exit 8
exit 0
STUB
chmod +x "$TMP/mock-monitor.sh"
export LARCH_TALLY_PLAN_ASSESSOR_SH="$ROOT/skills/design/scripts/tally-plan-assessor.sh"
setup_round2
rm -f "$TMP/breadcrumbs/assessor-round-2.dispatch.kv" "$TMP/breadcrumbs/assessor-round-2.quiet.log"
out=$("$SUBJECT" --design-tmpdir "$TMP" --codex-present true --cursor-present true)
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_VERDICT=not-worse' || fail 'production quiet-mode wiring path failed'
[[ -f "$TMP/breadcrumbs/assessor-round-2.dispatch.kv" ]] || fail 'dispatch kv file missing'
[[ -f "$TMP/breadcrumbs/assessor-round-2.quiet.log" ]] || fail 'quiet log missing'

pass 'assess-plan-round harness'
