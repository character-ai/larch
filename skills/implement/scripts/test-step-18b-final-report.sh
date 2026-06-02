#!/usr/bin/env bash
# test-step-18b-final-report.sh — offline harness for step-18b-final-report.sh

set -euo pipefail

export LARCH_QUIET_DISABLE=1
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
SOURCE_HELPER="$SCRIPT_DIR/step-18b-final-report.sh"

PASS=0
FAIL=0
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-step-18b-final-report.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; shift || true; [ "$#" -gt 0 ] && printf '%s\n' "$@" | sed 's/^/    /'; }

kv() {
    awk -v k="$1" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$2"
}

run_capture() {
    local out=$1
    shift
    set +e
    "$@" >"$out" 2>"$out.err"
    RC=$?
    set -e
}

assert_eq() {
    local expected=$1 actual=$2 label=$3
    if [ "$expected" = "$actual" ]; then pass "$label"; else fail "$label" "expected=$expected actual=$actual"; fi
}

assert_wrapper_did_not_create_step17_sentinel() {
    local tmpdir=$1 had_before=$2 label=$3
    if [ "$had_before" = false ] && [ -f "$tmpdir/.step17-emitted" ]; then
        fail "$label: wrapper wrote .step17-emitted"
    else
        pass "$label"
    fi
}

setup_stub_plugin() {
  local plugin=$1
  mkdir -p "$plugin/scripts"
  cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"
  cp "$REPO_ROOT/scripts/append-tool-failure.sh" "$plugin/scripts/append-tool-failure.sh"
  cp "$REPO_ROOT/scripts/read-session-env-key.sh" "$plugin/scripts/read-session-env-key.sh"
  chmod +x "$plugin/scripts/append-tool-failure.sh" "$plugin/scripts/read-session-env-key.sh"
  cat >"$plugin/scripts/token-report.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [ "${TOKEN_MODE:-ok}" = fail ]; then
  printf 'token-report stub failure\n' >&2
  exit 1
fi
while [ $# -gt 0 ]; do
  case "$1" in
    --output) printf '{}\n' >"$2"; shift 2 ;;
    *) shift ;;
  esac
done
exit 0
STUB
  chmod +x "$plugin/scripts/token-report.sh"
  cat >"$plugin/skills/implement/scripts/write-final-report.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
tmpdir=""
while [ $# -gt 0 ]; do
  case "$1" in
    --implement-tmpdir) tmpdir=$2; shift 2 ;;
    *) shift ;;
  esac
done
case "${WFR_MODE:-ok}" in
  fail) printf 'wfr stub failure\n' >&2; exit 1 ;;
  empty)
    : >"$tmpdir/summary-final.md"
    exit 0
    ;;
  ok|changed)
    printf '## /implement run stub — ok\n\nbody\n' >"$tmpdir/summary-final.md"
    exit 0
    ;;
  no-body) exit 0 ;;
esac
STUB
  chmod +x "$plugin/skills/implement/scripts/write-final-report.sh"
}

prepare_impl_dir() {
  local impl_dir=$1 plugin=$2
  mkdir -p "$impl_dir"
  cp "$SOURCE_HELPER" "$impl_dir/step-18b-final-report.sh"
  cp "$plugin/skills/implement/scripts/write-final-report.sh" "$impl_dir/write-final-report.sh"
  chmod +x "$impl_dir/step-18b-final-report.sh" "$impl_dir/write-final-report.sh"
}

run_wrapper() {
  local tmpdir=$1 impl_dir=$2 plugin=$3 wfr_mode=$4 token_mode=$5 out=$6
  run_capture "$out" env \
    CLAUDE_PLUGIN_ROOT="$plugin" \
    WFR_MODE="$wfr_mode" \
    TOKEN_MODE="$token_mode" \
    "$impl_dir/step-18b-final-report.sh" --implement-tmpdir "$tmpdir"
}

[ -x "$SOURCE_HELPER" ] || { fail "helper not executable: $SOURCE_HELPER"; exit 1; }

plugin="$TMP_ROOT/plugin"
impl_dir="$TMP_ROOT/implement-scripts"
mkdir -p "$plugin/skills/implement/scripts"
setup_stub_plugin "$plugin"
prepare_impl_dir "$impl_dir" "$plugin"

tmpdir="$TMP_ROOT/case-emit-absent"
mkdir -p "$tmpdir"
run_wrapper "$tmpdir" "$impl_dir" "$plugin" ok ok "$TMP_ROOT/case-emit-absent.out"
assert_eq 0 "$RC" "emit true when .step17-emitted absent and write succeeds"
assert_eq true "$(kv EMIT_BODY "$TMP_ROOT/case-emit-absent.out")" "EMIT_BODY=true absent sentinel"
assert_eq 0 "$(kv WFR_RC "$TMP_ROOT/case-emit-absent.out")" "WFR_RC=0 on success"
assert_eq false "$(kv STEP17_EMITTED_PRESENT "$TMP_ROOT/case-emit-absent.out")" "STEP17_EMITTED_PRESENT=false when absent"
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" false "wrapper never writes .step17-emitted"

tmpdir="$TMP_ROOT/case-emit-unchanged"
mkdir -p "$tmpdir"
printf '## /implement run stub — ok\n\nbody\n' >"$tmpdir/summary-final.md"
touch "$tmpdir/.step17-emitted"
run_wrapper "$tmpdir" "$impl_dir" "$plugin" ok ok "$TMP_ROOT/case-emit-unchanged.out"
assert_eq false "$(kv EMIT_BODY "$TMP_ROOT/case-emit-unchanged.out")" "EMIT_BODY=false when sentinel present and body unchanged"
assert_eq true "$(kv STEP17_EMITTED_PRESENT "$TMP_ROOT/case-emit-unchanged.out")" "STEP17_EMITTED_PRESENT=true when present"
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" true "wrapper never writes .step17-emitted when sentinel pre-seeded"

tmpdir="$TMP_ROOT/case-emit-changed"
mkdir -p "$tmpdir"
printf 'old body\n' >"$tmpdir/summary-final.md"
touch "$tmpdir/.step17-emitted"
run_wrapper "$tmpdir" "$impl_dir" "$plugin" changed ok "$TMP_ROOT/case-emit-changed.out"
assert_eq true "$(kv EMIT_BODY "$TMP_ROOT/case-emit-changed.out")" "EMIT_BODY=true when body changed vs snapshot"
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" true "wrapper never writes .step17-emitted when sentinel pre-seeded (changed body)"

tmpdir="$TMP_ROOT/case-emit-sentinel-no-prior-body"
mkdir -p "$tmpdir"
touch "$tmpdir/.step17-emitted"
rm -f "$tmpdir/summary-final.md" "$tmpdir/.step18-prebody"
run_wrapper "$tmpdir" "$impl_dir" "$plugin" ok ok "$TMP_ROOT/case-emit-sentinel-no-prior-body.out"
assert_eq true "$(kv EMIT_BODY "$TMP_ROOT/case-emit-sentinel-no-prior-body.out")" "EMIT_BODY=true when sentinel present and no pre-write summary-final.md"
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" true "wrapper never writes .step17-emitted when sentinel pre-seeded (no prior body)"

tmpdir="$TMP_ROOT/case-emit-cp-fail"
mkdir -p "$tmpdir"
touch "$tmpdir/.step17-emitted"
printf 'old body\n' >"$tmpdir/summary-final.md"
printf 'old body\n' >"$tmpdir/.step18-prebody"
chmod 444 "$tmpdir/.step18-prebody"
run_wrapper "$tmpdir" "$impl_dir" "$plugin" changed ok "$TMP_ROOT/case-emit-cp-fail.out"
assert_eq true "$(kv EMIT_BODY "$TMP_ROOT/case-emit-cp-fail.out")" "EMIT_BODY=true when snapshot cp fails and write succeeds"
assert_eq false "$(kv SNAPSHOT_OK "$TMP_ROOT/case-emit-cp-fail.out")" "SNAPSHOT_OK=false when snapshot cp fails"
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" true "wrapper never writes .step17-emitted when sentinel pre-seeded (cp fail)"

tmpdir="$TMP_ROOT/case-wfr-fail"
mkdir -p "$tmpdir"
run_wrapper "$tmpdir" "$impl_dir" "$plugin" fail ok "$TMP_ROOT/case-wfr-fail.out"
assert_eq false "$(kv EMIT_BODY "$TMP_ROOT/case-wfr-fail.out")" "EMIT_BODY=false when write-final-report fails"
assert_eq 1 "$(kv WFR_RC "$TMP_ROOT/case-wfr-fail.out")" "WFR_RC non-zero on write failure"
if [ -s "$tmpdir/step18-write-final-report.failure.log" ]; then
    pass "write-final-report failure log captured with helper output"
else
    fail "write-final-report failure log missing or empty"
fi
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" false "wrapper never writes .step17-emitted on write failure"

tmpdir="$TMP_ROOT/case-empty-body"
mkdir -p "$tmpdir"
run_wrapper "$tmpdir" "$impl_dir" "$plugin" empty ok "$TMP_ROOT/case-empty-body.out"
assert_eq false "$(kv EMIT_BODY "$TMP_ROOT/case-empty-body.out")" "EMIT_BODY=false when summary-final.md empty"
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" false "wrapper never writes .step17-emitted on empty body"

tmpdir="$TMP_ROOT/case-token-fail"
mkdir -p "$tmpdir"
run_wrapper "$tmpdir" "$impl_dir" "$plugin" ok fail "$TMP_ROOT/case-token-fail.out"
assert_eq true "$(kv EMIT_BODY "$TMP_ROOT/case-token-fail.out")" "EMIT_BODY follows gate when token-report fails but write succeeds"
if [ -s "$tmpdir/step18-token-report.failure.log" ]; then
    pass "token-report failure log captured with helper output"
else
    fail "token-report failure log missing or empty"
fi
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" false "wrapper never writes .step17-emitted on token failure"

tmpdir="$TMP_ROOT/case-session-env"
mkdir -p "$tmpdir"
printf 'LARCH_TOKEN_SESSION_ID=sess-18b\nLARCH_CLAUDE_SOURCE_FILE=/tmp/claude.jsonl\nLARCH_TIMING_LEDGER=/tmp/ledger.json\n' >"$tmpdir/session-env.sh"
run_wrapper "$tmpdir" "$impl_dir" "$plugin" ok ok "$TMP_ROOT/case-session-env.out"
assert_eq 0 "$RC" "session-env rehydration runs helper successfully"
assert_eq true "$(kv EMIT_BODY "$TMP_ROOT/case-session-env.out")" "session-env rehydration preserves emit gate"
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" false "wrapper never writes .step17-emitted with session-env"

tmpdir="$TMP_ROOT/case-plugin-root-fallback"
mkdir -p "$tmpdir"
printf 'CLAUDE_PLUGIN_ROOT=%s\n' "$plugin" >"$tmpdir/plugin-root.env"
run_capture "$TMP_ROOT/case-plugin-root-fallback.out" env -u CLAUDE_PLUGIN_ROOT WFR_MODE=ok TOKEN_MODE=ok bash -c \
  "set -a; . \"\$1/plugin-root.env\"; set +a; \"\$2/step-18b-final-report.sh\" --implement-tmpdir \"\$1\"" \
  bash "$tmpdir" "$impl_dir"
assert_eq 0 "$RC" "plugin-root.env orchestrator pre-source loads stub plugin"
assert_eq true "$(kv EMIT_BODY "$TMP_ROOT/case-plugin-root-fallback.out")" "plugin-root.env orchestrator pre-source emits EMIT_BODY=true"
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" false "wrapper never writes .step17-emitted with plugin-root fallback"

# Integration: real write-final-report.sh with minimal plugin fixture
int_plugin="$TMP_ROOT/int-plugin"
int_impl="$TMP_ROOT/int-implement-scripts"
int_tmpdir="$TMP_ROOT/case-integration-real-wfr"
mkdir -p "$int_plugin/scripts" "$int_impl" "$int_tmpdir/larch-logs/implement/run-int"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$int_plugin/scripts/lib-quiet.sh"
cp "$REPO_ROOT/scripts/read-session-env-key.sh" "$int_plugin/scripts/read-session-env-key.sh"
cp "$REPO_ROOT/scripts/append-tool-failure.sh" "$int_plugin/scripts/append-tool-failure.sh"
cp "$REPO_ROOT/scripts/render-run-summary.sh" "$int_plugin/scripts/render-run-summary.sh"
cp "$REPO_ROOT/scripts/token-cost.sh" "$int_plugin/scripts/token-cost.sh"
cp "$REPO_ROOT/scripts/lib-cost-line-format.sh" "$int_plugin/scripts/lib-cost-line-format.sh"
cp "$REPO_ROOT/scripts/redact-secrets.sh" "$int_plugin/scripts/redact-secrets.sh"
cp "$REPO_ROOT/scripts/run-log-terminal-outcomes.inc.bash" "$int_plugin/scripts/run-log-terminal-outcomes.inc.bash"
chmod +x "$int_plugin/scripts/read-session-env-key.sh" "$int_plugin/scripts/append-tool-failure.sh" \
  "$int_plugin/scripts/render-run-summary.sh" "$int_plugin/scripts/token-cost.sh" \
  "$int_plugin/scripts/redact-secrets.sh"
cat >"$int_plugin/scripts/token-report.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
while [ $# -gt 0 ]; do
  case "$1" in
    --output) printf '{}\n' >"$2"; shift 2 ;;
    *) shift ;;
  esac
done
exit 0
STUB
cat >"$int_plugin/scripts/tracking-issue-summary.sh" <<'STUB'
#!/usr/bin/env bash
while [ $# -gt 0 ]; do case "$1" in --content-file) cp "$2" "${TRACKING_CONTENT_LOG:?}"; shift 2 ;; *) shift ;; esac; done
printf 'COMMENT_URL=https://example.test/comment/int\n'
STUB
cat >"$int_plugin/scripts/larch-log.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$int_plugin/scripts/token-report.sh" "$int_plugin/scripts/tracking-issue-summary.sh" "$int_plugin/scripts/larch-log.sh"
cp "$SOURCE_HELPER" "$int_impl/step-18b-final-report.sh"
cp "$REPO_ROOT/skills/implement/scripts/write-final-report.sh" "$int_impl/write-final-report.sh"
chmod +x "$int_impl/step-18b-final-report.sh" "$int_impl/write-final-report.sh"
printf 'ISSUE_NUMBER=42\nRUN_ID=run-int\nADOPTED=true\n' >"$int_tmpdir/parent-issue.md"
printf 'REPO=owner/repo\n' >"$int_tmpdir/session-env.sh"
{
  printf 'PR_URL=N/A\n'
  printf 'PR_NUMBER=\n'
  printf 'STALL_TRACKING=false\n'
  printf 'MERGE_RESULT=\n'
  printf 'MERGE=false\n'
  printf 'DRAFT=false\n'
  printf 'FORKED_TARGET=false\n'
} >"$int_tmpdir/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\n' >"$int_tmpdir/finalize-state.sh"
printf 'NO_ISSUES=false\n' >"$int_tmpdir/run-flags.sh"
run_capture "$TMP_ROOT/case-integration-real-wfr.out" env \
  CLAUDE_PLUGIN_ROOT="$int_plugin" \
  TRACKING_CONTENT_LOG="$TMP_ROOT/content-integration-real-wfr.md" \
  "$int_impl/step-18b-final-report.sh" --implement-tmpdir "$int_tmpdir"
assert_eq 0 "$RC" "integration real write-final-report exits 0"
assert_eq true "$(kv EMIT_BODY "$TMP_ROOT/case-integration-real-wfr.out")" "integration real write-final-report EMIT_BODY=true without sentinel"
assert_eq 0 "$(kv WFR_RC "$TMP_ROOT/case-integration-real-wfr.out")" "integration real write-final-report WFR_RC=0"
if [ -s "$int_tmpdir/summary-final.md" ]; then
  pass "integration real write-final-report writes summary-final.md"
else
  fail "integration real write-final-report writes summary-final.md"
fi
assert_wrapper_did_not_create_step17_sentinel "$int_tmpdir" false "wrapper never writes .step17-emitted in integration case"

tmpdir="$TMP_ROOT/case-wfr-no-body"
mkdir -p "$tmpdir"
run_wrapper "$tmpdir" "$impl_dir" "$plugin" no-body ok "$TMP_ROOT/case-wfr-no-body.out"
assert_eq 0 "$RC" "wfr succeeds but no summary-final.md: wrapper exits 0"
assert_eq false "$(kv EMIT_BODY "$TMP_ROOT/case-wfr-no-body.out")" "EMIT_BODY=false when WFR succeeds but no summary-final.md created"
assert_eq 0 "$(kv WFR_RC "$TMP_ROOT/case-wfr-no-body.out")" "WFR_RC=0 when wfr exits 0 with no body"
assert_wrapper_did_not_create_step17_sentinel "$tmpdir" false "wrapper never writes .step17-emitted when no body created"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
