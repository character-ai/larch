#!/usr/bin/env bash
# Regression harness for design-init-runparams.sh Step 0b router-flag jq-merge recovery.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
WRITER="$REPO_ROOT/scripts/write-run-params.sh"
DESIGN_INIT="$REPO_ROOT/skills/design/scripts/design-init-runparams.sh"
HOST_JQ=$(command -v jq) || { echo "FAIL: host jq required" >&2; exit 1; }
HOST_JQ_DIR=$(dirname "$HOST_JQ")

fail() { echo "FAIL: $1" >&2; exit 1; }
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-step0b-recovery.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

merge_run_params() {
  local out="$1" partition_requested="$2" brainstorm_requested="$3" manual_requested="$4"
  local _rp_merge _rp_err
  _rp_merge=$(mktemp "${TMPDIR:-/tmp}/larch-router-flags-merge.XXXXXX")
  _rp_err=$(mktemp "${TMPDIR:-/tmp}/larch-router-flags-merge-err.XXXXXX")
  # shellcheck disable=SC2016 # jq filter literal: $merge_p/$merge_b/$merge_m are jq vars, not shell vars.
  jq -c \
    --argjson merge_p "$([[ "$partition_requested" == true ]] && echo true || echo false)" \
    --argjson merge_b "$([[ "$brainstorm_requested" == true ]] && echo true || echo false)" \
    --argjson merge_m "$([[ "$manual_requested" == true ]] && echo true || echo false)" \
    '.partition_requested = (.partition_requested == true or $merge_p) | .brainstorm_requested = (.brainstorm_requested == true or $merge_b) | .manual_gate_b = $merge_m' \
    "$out" >"$_rp_merge" 2>"$_rp_err" || { cat "$_rp_err" >&2; rm -f "$_rp_merge" "$_rp_err"; return 1; }
  mv -f "$_rp_merge" "$out"
  rm -f "$_rp_err"
}

# Replicates design-init-runparams.sh Step 0b outer guard: recovery runs only when at least one argv flag
# is true and jq exists; when the output file is missing it warns and does not recreate it.
recovery_merge_if_needed() {
  local out="$1" partition_requested="$2" brainstorm_requested="$3" manual_requested="$4"
  if [[ "$partition_requested" == true || "$brainstorm_requested" == true || "$manual_requested" == true ]] && command -v jq >/dev/null 2>&1; then
    if [[ -f "$out" ]]; then
      merge_run_params "$out" "$partition_requested" "$brainstorm_requested" "$manual_requested"
    else
      printf '%s\n' "**⚠ 0b: run-params.json missing after write-run-params.sh; refusing to recreate it with fallback defaults. Re-run \`bash scripts/test-write-run-params.sh\` and fix the Step 0b contract drift first.**"
    fi
  fi
}

write_then_recover() {
  local out="$1" classification="$2" spy="$3" r_partition="$4" r_brainstorm="$5" r_manual="$6"
  if ! "$WRITER" --classification "$classification" \
      --partition-requested false --brainstorm-requested false --manual-gate-b false \
      --output "$out" >/dev/null 2>&1; then
    return 1
  fi
  recovery_merge_if_needed "$out" "$r_partition" "$r_brainstorm" "$r_manual" || return 1
  : > "$spy"
}

# Case 1: successful write; manual-only argv => manual=true (FINDING_9 success path).
OUT1="$TMPROOT/case1.json"
"$WRITER" --classification SIMPLE --partition-requested false --brainstorm-requested false --manual-gate-b false --output "$OUT1" >/dev/null
recovery_merge_if_needed "$OUT1" false false true
jq -e '.partition_requested == false and .brainstorm_requested == false and .manual_gate_b == true' "$OUT1" >/dev/null \
  || fail "case1: manual-only argv merge produced $(cat "$OUT1")"

# Case 2: stored manual=true; argv partition=true + manual=false => manual=false when recovery runs.
# Reachable runtime shape: outer guard true because partition_requested=true; manual overwrite
# clears stale persisted manual (SKILL.md Step 0b rationale).
OUT2="$TMPROOT/case2.json"
"$WRITER" --classification SIMPLE --partition-requested false --brainstorm-requested false --manual-gate-b true --output "$OUT2" >/dev/null
recovery_merge_if_needed "$OUT2" true false false
jq -e '.manual_gate_b == false and .partition_requested == true' "$OUT2" >/dev/null \
  || fail "case2: manual overwrite under reachable guard failed; got $(cat "$OUT2")"

# Case 3: stored partition=true; argv partition=false, brainstorm=true => OR-merge preserves partition.
OUT3="$TMPROOT/case3.json"
"$WRITER" --classification SIMPLE --partition-requested true --brainstorm-requested false --manual-gate-b false --output "$OUT3" >/dev/null
recovery_merge_if_needed "$OUT3" false true false
jq -e '.partition_requested == true and .brainstorm_requested == true and .manual_gate_b == false' "$OUT3" >/dev/null \
  || fail "case3: partition OR-merge regressed; got $(cat "$OUT3")"

# Case 4: stored brainstorm=true; guard enters via partition argv true; brainstorm OR-merge preserves.
OUT4="$TMPROOT/case4.json"
"$WRITER" --classification SIMPLE --partition-requested false --brainstorm-requested true --manual-gate-b false --output "$OUT4" >/dev/null
recovery_merge_if_needed "$OUT4" true false false
jq -e '.brainstorm_requested == true and .partition_requested == true and .manual_gate_b == false' "$OUT4" >/dev/null \
  || fail "case4: brainstorm OR-merge regressed; got $(cat "$OUT4")"

# Case 5: all-false argv => outer guard short-circuits; file unchanged (false-branch no-op).
# Proves the guard's false-branch is exercised so a loosened guard would fail this assertion.
OUT5="$TMPROOT/case5.json"
"$WRITER" --classification SIMPLE --partition-requested false --brainstorm-requested false --manual-gate-b false --output "$OUT5" >/dev/null
before_sum=$(shasum -a 256 "$OUT5" | awk '{print $1}')
recovery_merge_if_needed "$OUT5" false false false
after_sum=$(shasum -a 256 "$OUT5" | awk '{print $1}')
[[ "$before_sum" == "$after_sum" ]] || fail "case5: all-false guard mutated file; before=$before_sum after=$after_sum"
jq -e '.partition_requested == false and .brainstorm_requested == false and .manual_gate_b == false' "$OUT5" >/dev/null \
  || fail "case5: all-false post-state mismatch"

# Case 6: missing run-params.json under a true argv flag warns and does not recreate fallback defaults.
OUT6="$TMPROOT/case6.json"
warning_case6=$(recovery_merge_if_needed "$OUT6" true false false)
[[ ! -e "$OUT6" ]] || fail "case6: missing-file degraded path recreated $OUT6"
[[ "$warning_case6" == "**⚠ 0b: run-params.json missing after write-run-params.sh; refusing to recreate it with fallback defaults. Re-run \`bash scripts/test-write-run-params.sh\` and fix the Step 0b contract drift first.**" ]] \
  || fail "case6: missing-file degraded warning drifted; got: $warning_case6"

# Case 7: a failing writer aborts BEFORE recovery (#3161). Spy absence proves recovery never
# ran; captured stdout proves the missing-file recovery warning was not emitted.
OUT7="$TMPROOT/case7.json"; SPY7="$TMPROOT/case7-recovery-reached"; rm -f "$SPY7"
set +e
out7_stdout=$(write_then_recover "$OUT7" BOGUS "$SPY7" false false true 2>/dev/null)
rc7=$?
set -e
[[ "$rc7" -ne 0 ]] || fail "case7: failing writer must abort before recovery; rc=$rc7"
[[ ! -e "$SPY7" ]] || fail "case7: recovery completed after writer failure (spy present)"
[[ ! -e "$OUT7" ]] || fail "case7: failing writer created $OUT7"
[[ "$out7_stdout" != *"refusing to recreate it with fallback defaults"* ]] \
  || fail "case7: missing-file recovery warning emitted after writer failure (recovery not bypassed)"

# Case 7b (positive control): a successful write reaches AND completes recovery. Writer writes
# manual_gate_b=false; recovery (manual=true) must FLIP it to true. Spy present only because
# recovery returned 0.
OUT7B="$TMPROOT/case7b.json"; SPY7B="$TMPROOT/case7b-recovery-reached"; rm -f "$SPY7B"
set +e; write_then_recover "$OUT7B" SIMPLE "$SPY7B" false false true; rc7b=$?; set -e
[[ "$rc7b" -eq 0 ]] || fail "case7b: successful write_then_recover returned $rc7b"
[[ -e "$SPY7B" ]] || fail "case7b: recovery did not complete after successful write (spy absent)"
jq -e '.manual_gate_b == true' "$OUT7B" >/dev/null \
  || fail "case7b: recovery did not flip manual_gate_b false->true; got $(cat "$OUT7B")"

# --- Production driver integration (stubbed plugin scripts) ---
FAKE_PLUGIN="$TMPROOT/fake-plugin"
STUB_SCRIPTS="$FAKE_PLUGIN/scripts"
mkdir -p "$STUB_SCRIPTS"
for _lib in lib-quiet.sh lib-larch-log.sh write-run-params.sh append-tool-failure.sh append-execution-issue.sh; do
  ln -sf "$REPO_ROOT/scripts/$_lib" "$STUB_SCRIPTS/$_lib"
done
cat >"$STUB_SCRIPTS/write-design-current-env.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$STUB_SCRIPTS/write-design-current-env.sh"
cat >"$STUB_SCRIPTS/tracking-issue-write.sh" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' 'RENAMED=true'
exit 0
STUB
chmod +x "$STUB_SCRIPTS/tracking-issue-write.sh"

run_design_init() {
  local dtmp="$1" partition="$2" brainstorm="$3" manual="$4" extra_path="${5:-}"
  mkdir -p "$dtmp"
  export CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN"
  local _path="$extra_path"
  [[ -n "$_path" ]] || _path="$HOST_JQ_DIR:/usr/bin:/bin:/usr/local/bin"
  PATH="$_path" "$DESIGN_INIT" \
    --design-tmpdir "$dtmp" \
    --issue 42 \
    --session-id RUN-STEP0B-TEST \
    --claude-pid 424242 \
    --classification SIMPLE \
    --partition-requested "$partition" \
    --brainstorm-requested "$brainstorm" \
    --manual-requested "$manual"
}

# Case 8: invoke production driver; manual argv merges into run-params.json.
D8="$TMPROOT/driver8"
set +e
out8=$(run_design_init "$D8" false false true 2>&1)
rc8=$?
set -e
[[ "$rc8" -eq 0 ]] || fail "case8: design-init-runparams.sh rc=$rc8 out=$out8"
[[ -f "$D8/run-params.json" ]] || fail "case8: missing run-params.json"
grep -Fq 'INIT_STATUS=ok' "$D8/.design-init-runparams-result.env" \
  || fail "case8: result env missing INIT_STATUS=ok"
jq -e '.manual_gate_b == true' "$D8/run-params.json" >/dev/null \
  || fail "case8: driver jq-merge failed; got $(cat "$D8/run-params.json")"

# Case 9: rename failure is best-effort; run-params still written.
cat >"$STUB_SCRIPTS/tracking-issue-write.sh" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
chmod +x "$STUB_SCRIPTS/tracking-issue-write.sh"
D9="$TMPROOT/driver9"
set +e
out9=$(run_design_init "$D9" false false false 2>&1)
rc9=$?
set -e
[[ "$rc9" -eq 0 ]] || fail "case9: rename-fail best-effort rc=$rc9 out=$out9"
[[ -f "$D9/run-params.json" ]] || fail "case9: missing run-params.json after rename failure"
printf '%s\n' "$out9" | grep -Fq 'WARN=' \
  || fail "case9: missing rename WARN on stdout"
printf '%s\n' "$out9" | grep -Fq 'rename failed (tracking-issue-write.sh)' \
  || fail "case9: rename WARN text drifted"

# Case 10: jq merge failure appends to execution-issues.md via production driver.
cat >"$STUB_SCRIPTS/tracking-issue-write.sh" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' 'RENAMED=true'
exit 0
STUB
chmod +x "$STUB_SCRIPTS/tracking-issue-write.sh"
JQ_STUB="$TMPROOT/jq-stub-bin"
mkdir -p "$JQ_STUB"
cat >"$JQ_STUB/jq" <<STUB
#!/usr/bin/env bash
if [[ "\${LARCH_TEST_JQ_MERGE_FAIL:-}" == 1 ]] && [[ "\${1:-}" == "-c" ]]; then
  echo 'router-flags-merge failed' >&2
  exit 1
fi
exec "$HOST_JQ" "\$@"
STUB
chmod +x "$JQ_STUB/jq"
D10="$TMPROOT/driver10"
export LARCH_TEST_JQ_MERGE_FAIL=1
set +e
out10=$(run_design_init "$D10" false false true "$JQ_STUB:$HOST_JQ_DIR:/usr/bin:/bin:/usr/local/bin" 2>&1)
unset LARCH_TEST_JQ_MERGE_FAIL
rc10=$?
set -e
[[ "$rc10" -eq 0 ]] || fail "case10: jq-fail driver rc=$rc10 out=$out10"
grep -Fq 'jq(router-flags-merge)' "$D10/execution-issues.md" \
  || fail "case10: execution-issues.md missing jq(router-flags-merge) append"

# Case 11: jq unavailable emits WARN on production driver stdout (write-run-params stubbed; merge needs jq).
# Unlink the symlink before writing so we don't clobber the real scripts/write-run-params.sh.
rm -f "$STUB_SCRIPTS/write-run-params.sh"
cat >"$STUB_SCRIPTS/write-run-params.sh" <<'STUB'
#!/usr/bin/env bash
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\n' '{"schema_version":3,"design_classification":"SIMPLE","partition_requested":false,"brainstorm_requested":false,"manual_gate_b":false}' >"$out"
printf 'RUN_PARAMS_WRITTEN=%s\n' "$out"
exit 0
STUB
chmod +x "$STUB_SCRIPTS/write-run-params.sh"
D11="$TMPROOT/driver11"
# Build a PATH directory that has all tools needed by the script except jq, so
# command -v jq returns non-zero on every platform (e.g. /usr/bin/jq on Ubuntu CI).
_no_jq_path="$TMPROOT/no-jq-path"
mkdir -p "$_no_jq_path"
for _cmd in bash sh dirname basename mktemp mv rm mkdir cat printf chmod; do
  _real=$(command -v "$_cmd" 2>/dev/null || true)
  [ -n "$_real" ] && ln -sf "$_real" "$_no_jq_path/$_cmd"
done
# jq intentionally absent from _no_jq_path
set +e
out11=$(run_design_init "$D11" true false false "$_no_jq_path" 2>&1)
rc11=$?
set -e
[[ "$rc11" -eq 0 ]] || fail "case11: jq-unavailable driver rc=$rc11 out=$out11"
printf '%s\n' "$out11" | grep -Fq 'jq is unavailable' \
  || fail "case11: missing jq-unavailable WARN on stdout"

echo "PASS: test-step0b-router-flag-recovery.sh"
