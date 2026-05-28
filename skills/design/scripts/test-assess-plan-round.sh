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
printf '%s\n' "$out" | grep -Fq 'ASSESSOR_VERDICT=worse-majority' || fail 'degraded dispatch should still tally usable assessor outputs'
grep -Fq 'EFFECTIVE_ASSESSORS=2' "$TMP/assessor-verdict-round-2.txt.env" || fail 'degraded dispatch tally should record two effective assessors'

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

pass 'assess-plan-round harness'
