#!/usr/bin/env bash
# test-design-step5c.sh — offline harness for design-step5c publish-tail abort paths.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step5c.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-step5c.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAKE_PLUGIN="$TMP/plugin"
STUB="$FAKE_PLUGIN/skills/design/scripts"
mkdir -p "$STUB" "$FAKE_PLUGIN/scripts" "$FAKE_PLUGIN/skills/implement/scripts"
ln -sf "$ROOT/python" "$FAKE_PLUGIN/python"
# lib-phase-driver.sh ported to python/design_lifecycle.py; python/ symlink provides it
ln -sf "$ROOT/skills/design/scripts/design-stage-terminal-state.sh" "$STUB/design-stage-terminal-state.sh"
ln -sf "$ROOT/skills/implement/scripts/stall-recovery-report.sh" "$FAKE_PLUGIN/skills/implement/scripts/stall-recovery-report.sh"
ln -sf "$ROOT/scripts/lib-design-tmpdir.sh" "$FAKE_PLUGIN/scripts/lib-design-tmpdir.sh"
ln -sf "$ROOT/scripts/lib-quiet.sh" "$FAKE_PLUGIN/scripts/lib-quiet.sh"
ln -sf "$ROOT/scripts/lib-larch-dev-clone.sh" "$FAKE_PLUGIN/scripts/lib-larch-dev-clone.sh"
ln -sf "$ROOT/scripts/read-result-env.sh" "$FAKE_PLUGIN/scripts/read-result-env.sh"

cat >"$STUB/design-publish.sh" <<'STUB'
#!/usr/bin/env bash
printf 'design-publish stub rc=%s\n' "${DESIGN_PUBLISH_STUB_RC:-0}" >&2
case "${DESIGN_PUBLISH_STUB_MODE:-}" in
  success-summary)
    printf 'stub success summary\n' >"${DESIGN_TMPDIR:-}/final-summary.md"
    {
      printf 'PLAN_WRITE_OK=true\n'
      printf 'VALIDATE_STATUS=ok\n'
      printf 'PUBLISH_OK=true\n'
      printf 'FINAL_SUMMARY_PATH=%s/final-summary.md\n' "${DESIGN_TMPDIR:-}"
    } >"${DESIGN_TMPDIR:-}/.design-publish-result.env"
    ;;
  plan-write-failed)
    printf 'PLAN_WRITE_OK=false\n'
    printf 'VALIDATE_STATUS=ok\n'
    printf 'PUBLISH_OK=\n'
    printf 'FINAL_SUMMARY_PATH=%s/final-summary.md\n' "${DESIGN_TMPDIR:-}"
    printf 'stub failed plan write summary\n' >"${DESIGN_TMPDIR:-}/final-summary.md"
    ;;
  validator-defects)
    printf 'PLAN_WRITE_OK=false\n'
    printf 'VALIDATE_STATUS=defects-found\n'
    printf 'VALIDATE_DEFECT_COUNT=2\n'
    printf 'VALIDATE_SKIPPED_COUNT=0\n'
    printf 'VALIDATE_UNSAFE_TOKEN_COUNT=1\n'
    printf 'VALIDATE_LOG_FILE=%s/validate.log\n' "${DESIGN_TMPDIR:-}"
    printf 'FINAL_SUMMARY_PATH=%s/final-summary.md\n' "${DESIGN_TMPDIR:-}"
    ;;
esac
exit "${DESIGN_PUBLISH_STUB_RC:-0}"
STUB
chmod +x "$STUB/design-publish.sh"

cat >"$STUB/render-final-summary.sh" <<'STUB'
#!/usr/bin/env bash
while [ $# -gt 0 ]; do case "$1" in --outcome) shift 2 ;; *) shift ;; esac; done
tmp="${DESIGN_TMPDIR:-}"
[ -n "$tmp" ] || tmp="$(pwd)"
printf 'stub failed publish tail summary\n' >"$tmp/final-summary.md"
exit 0
STUB
chmod +x "$STUB/render-final-summary.sh"

setup_design_tmp() {
  local d=$1
  mkdir -p "$d/.completed"
  : >"$d/.completed/step-5b"
  : >"$d/execution-issues.md"
}

run_step5c() {
  local d=$1 rc=$2
  d=$(cd "$d" && pwd -P)
  setup_design_tmp "$d"
  set +e
  CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$d" DESIGN_PUBLISH_STUB_RC="$rc" \
    "$SUBJECT" >"$d/stdout" 2>"$d/stderr"
  local got=$?
  set -e
  printf '%s\n' "$got"
}

run_step5c_with_mode() {
  local d=$1 rc=$2 mode=$3
  d=$(cd "$d" && pwd -P)
  setup_design_tmp "$d"
  set +e
  CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$d" DESIGN_PUBLISH_STUB_RC="$rc" DESIGN_PUBLISH_STUB_MODE="$mode" \
    "$SUBJECT" >"$d/stdout" 2>"$d/stderr"
  local got=$?
  set -e
  printf '%s\n' "$got"
}

assert_marked_summary_matches() {
  local d=$1 label=$2
  local begin_count end_count
  begin_count=$(grep -xc 'LARCH_FINAL_SUMMARY_BEGIN' "$d/stdout" || true)
  end_count=$(grep -xc 'LARCH_FINAL_SUMMARY_END' "$d/stdout" || true)
  [[ "$begin_count" -eq 1 ]] || fail "$label must emit exactly one final-summary begin marker (got $begin_count)"
  [[ "$end_count" -eq 1 ]] || fail "$label must emit exactly one final-summary end marker (got $end_count)"
  python3 - "$d/stdout" "$d/final-summary.md" "$label" <<'PY'
import re
import sys
from pathlib import Path
stdout = Path(sys.argv[1]).read_text()
summary = Path(sys.argv[2]).read_text()
label = sys.argv[3]
match = re.search(r'^LARCH_FINAL_SUMMARY_BEGIN\n(.*?)^LARCH_FINAL_SUMMARY_END\n?', stdout, re.M | re.S)
if not match:
    print(f'FAIL: {label} missing balanced final-summary markers', file=sys.stderr)
    sys.exit(1)
if match.group(1) != summary:
    print(f'FAIL: {label} marked body does not match final-summary.md', file=sys.stderr)
    sys.exit(1)
PY
}

D=$(mktemp -d "$TMP/rc2.XXXXXX")
D=$(cd "$D" && pwd -P)
printf 'operator action sidecar\n' >"$D/design-failure-operator-action-chat.md"
got=$(run_step5c "$D" 2)
[[ "$got" -eq 1 ]] || fail "publish rc=2 must abort step5c with exit 1 (got $got)"
[ -f "$D/design-failure-terminal-state.env" ] || fail 'rc=2 must stage failed-publish-tail terminal state'
grep -Fxq 'FAILURE_OUTCOME=failed-publish-tail' "$D/design-failure-terminal-state.env" \
  || fail 'rc=2 terminal outcome must be failed-publish-tail'
if [ ! -s "$D/final-summary.md" ]; then
  ls -la "$D" >&2
  fail 'rc=2 must write non-empty final-summary via render'
fi
assert_marked_summary_matches "$D" 'rc=2 publish-tail abort'
grep -Fq 'REPORT_GATE_SIDECARS_FILE=' "$D/stdout" \
  || fail 'rc=2 must emit sidecar file handoff when sidecars exist'
pass 'publish-tail rc=2 stages terminal state and renders marked summary'

D2=$(mktemp -d "$TMP/rc9.XXXXXX")
D2=$(cd "$D2" && pwd -P)
got=$(run_step5c "$D2" 9)
[[ "$got" -eq 1 ]] || fail "unexpected publish rc must abort step5c with exit 1 (got $got)"
[ -f "$D2/design-failure-terminal-state.env" ] || fail 'unexpected rc must stage failed-publish-tail terminal state'
grep -Fxq 'FAILURE_OUTCOME=failed-publish-tail' "$D2/design-failure-terminal-state.env" \
  || fail 'unexpected rc terminal outcome must be failed-publish-tail'
[ -s "$D2/final-summary.md" ] || fail 'unexpected rc must write non-empty final-summary via render'
assert_marked_summary_matches "$D2" 'unexpected publish-tail abort'
pass 'publish-tail unexpected rc stages terminal state and renders marked summary'

D3=$(mktemp -d "$TMP/rc1-stale.XXXXXX")
D3=$(cd "$D3" && pwd -P)
setup_design_tmp "$D3"
cat >"$D3/.design-publish-result.env" <<'EOF_RESULT'
PLAN_WRITE_OK=true
PUBLISH_OK=true
FINAL_SUMMARY_PATH=/stale/final-summary.md
EOF_RESULT
got=$(run_step5c_with_mode "$D3" 1 plan-write-failed)
[[ "$got" -eq 0 ]] || fail "publish rc=1 should parse stdout and exit 0 (got $got)"
grep -Fxq 'PLAN_WRITE_OK=false' "$D3/.design-step5c-status.env" \
  || fail 'rc=1 must parse PLAN_WRITE_OK=false from stdout, not stale file'
grep -Fxq 'CLEANUP_ELIGIBLE=false' "$D3/.design-step5c-status.env" \
  || fail 'rc=1 stale-primary fallback must withhold cleanup'
pass 'publish-tail rc=1 uses stdout authority over stale result env'

D4=$(mktemp -d "$TMP/rc4-stale.XXXXXX")
D4=$(cd "$D4" && pwd -P)
setup_design_tmp "$D4"
cat >"$D4/.design-publish-result.env" <<'EOF_RESULT'
PLAN_WRITE_OK=true
VALIDATE_STATUS=ok
PUBLISH_OK=true
FINAL_SUMMARY_PATH=/stale/final-summary.md
EOF_RESULT
got=$(run_step5c_with_mode "$D4" 4 validator-defects)
[[ "$got" -eq 0 ]] || fail "publish rc=4 should parse stdout and exit 0 (got $got)"
grep -Fxq 'VALIDATE_STATUS=defects-found' "$D4/stdout" \
  || fail 'rc=4 must parse validator defects from stdout, not stale file'
grep -Fxq 'VALIDATE_DEFECT_COUNT=2' "$D4/stdout" \
  || fail 'rc=4 must parse defect count from stdout'
grep -Fxq 'CLEANUP_ELIGIBLE=false' "$D4/.design-step5c-status.env" \
  || fail 'rc=4 stale-primary fallback must withhold cleanup'
grep -Fxq 'STEP5C_STATUS=validator-defects' "$D4/stdout" \
  || fail 'rc=4 should report validator-defects status'
pass 'publish-tail rc=4 uses stdout authority over stale result env'


D5=$(mktemp -d "$TMP/rc0-summary.XXXXXX")
D5=$(cd "$D5" && pwd -P)
got=$(run_step5c_with_mode "$D5" 0 success-summary)
[[ "$got" -eq 0 ]] || fail "publish rc=0 should parse result env and exit 0 (got $got)"
assert_marked_summary_matches "$D5" 'rc=0 publish success'
pass 'publish-tail rc=0 emits marked final summary'

printf 'PASS: test-design-step5c.sh\n'
