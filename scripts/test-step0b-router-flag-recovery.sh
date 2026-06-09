#!/usr/bin/env bash
# Regression harness for design-init-runparams.sh Step 0b router-flag jq-merge recovery.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
PYTHON_BIN=$(command -v python3)
WRITER=("$PYTHON_BIN" "$REPO_ROOT/python/cli.py" session write-run-params)
DESIGN_INIT="$REPO_ROOT/skills/design/scripts/design-init-runparams.sh"
HOST_JQ=$(command -v jq) || { echo "FAIL: host jq required" >&2; exit 1; }
HOST_JQ_DIR=$(dirname "$HOST_JQ")

fail() { echo "FAIL: $1" >&2; exit 1; }
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-step0b-recovery.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

merge_run_params() {
  local out="$1" partition_requested="$2" brainstorm_requested="$3" approve_requested="${4:-false}" skip_approve_requested="${5:-false}"
  local _rp_merge _rp_err
  _rp_merge=$(mktemp "${TMPDIR:-/tmp}/larch-router-flags-merge.XXXXXX")
  _rp_err=$(mktemp "${TMPDIR:-/tmp}/larch-router-flags-merge-err.XXXXXX")
  # shellcheck disable=SC2016 # jq filter literal: $merge_p/$merge_b/$merge_a/$merge_s are jq vars, not shell vars.
  jq -c \
    --argjson merge_p "$([[ "$partition_requested" == true ]] && echo true || echo false)" \
    --argjson merge_b "$([[ "$brainstorm_requested" == true ]] && echo true || echo false)" \
    --argjson merge_a "$([[ "$approve_requested" == true ]] && echo true || echo false)" \
    --argjson merge_s "$([[ "$skip_approve_requested" == true ]] && echo true || echo false)" \
    '.partition_requested = (.partition_requested == true or $merge_p) | .brainstorm_requested = (.brainstorm_requested == true or $merge_b) | .approve_requested = (.approve_requested == true or $merge_a) | .skip_approve_requested = (.skip_approve_requested == true or $merge_s)' \
    "$out" >"$_rp_merge" 2>"$_rp_err" || { cat "$_rp_err" >&2; rm -f "$_rp_merge" "$_rp_err"; return 1; }
  mv -f "$_rp_merge" "$out"
  rm -f "$_rp_err"
}

# Replicates design-init-runparams.sh Step 0b outer guard: recovery runs only when at least one argv flag
# is true and jq exists; when the output file is missing it warns and does not recreate it.
recovery_merge_if_needed() {
  local out="$1" partition_requested="$2" brainstorm_requested="$3" approve_requested="${4:-false}" skip_approve_requested="${5:-false}"
  if [[ "$partition_requested" == true || "$brainstorm_requested" == true || "$approve_requested" == true || "$skip_approve_requested" == true ]] && command -v jq >/dev/null 2>&1; then
    if [[ -f "$out" ]]; then
      merge_run_params "$out" "$partition_requested" "$brainstorm_requested" "$approve_requested" "$skip_approve_requested"
    else
      printf '%s\n' "**⚠ 0b: run-params.json missing after session write-run-params; refusing to recreate it with fallback defaults. Re-run \`python -m pytest python/test_session_env.py\` and fix the Step 0b contract drift first.**"
    fi
  fi
}

write_then_recover() {
  local out="$1" classification="$2" spy="$3" r_partition="$4" r_brainstorm="$5" r_approve="${6:-false}" r_skip_approve="${7:-false}"
  if ! "${WRITER[@]}" --classification "$classification" \
      --partition-requested false --brainstorm-requested false \
      --output "$out" >/dev/null 2>&1; then
    return 1
  fi
  recovery_merge_if_needed "$out" "$r_partition" "$r_brainstorm" "$r_approve" "$r_skip_approve" || return 1
  : > "$spy"
}

# Case 1: successful write; partition argv merges true.
OUT1="$TMPROOT/case1.json"
"${WRITER[@]}" --classification SIMPLE --partition-requested false --brainstorm-requested false --output "$OUT1" >/dev/null
recovery_merge_if_needed "$OUT1" true false
jq -e '.partition_requested == true and .brainstorm_requested == false and .approve_requested == false and (has("manual_gate_b") | not)' "$OUT1" >/dev/null \
  || fail "case1: partition argv merge produced $(cat "$OUT1")"

# Case 3: stored partition=true; argv partition=false, brainstorm=true => OR-merge preserves partition.
OUT3="$TMPROOT/case3.json"
"${WRITER[@]}" --classification SIMPLE --partition-requested true --brainstorm-requested false --output "$OUT3" >/dev/null
recovery_merge_if_needed "$OUT3" false true
jq -e '.partition_requested == true and .brainstorm_requested == true and (has("manual_gate_b") | not)' "$OUT3" >/dev/null \
  || fail "case3: partition OR-merge regressed; got $(cat "$OUT3")"

# Case 3a: stored approve=true; argv approve=false with another true flag preserves approve.
OUT3A="$TMPROOT/case3a.json"
"${WRITER[@]}" --classification SIMPLE --partition-requested false --brainstorm-requested false --approve-requested true --output "$OUT3A" >/dev/null
recovery_merge_if_needed "$OUT3A" true false false
jq -e '.partition_requested == true and .brainstorm_requested == false and .approve_requested == true and (has("manual_gate_b") | not)' "$OUT3A" >/dev/null \
  || fail "case3a: approve OR-merge regressed; got $(cat "$OUT3A")"

# Case 4: stored brainstorm=true; guard enters via partition argv true; brainstorm OR-merge preserves.
OUT4="$TMPROOT/case4.json"
"${WRITER[@]}" --classification SIMPLE --partition-requested false --brainstorm-requested true --output "$OUT4" >/dev/null
recovery_merge_if_needed "$OUT4" true false
jq -e '.brainstorm_requested == true and .partition_requested == true and .approve_requested == false and (has("manual_gate_b") | not)' "$OUT4" >/dev/null \
  || fail "case4: brainstorm OR-merge regressed; got $(cat "$OUT4")"

# Case 5: all-false argv => outer guard short-circuits; file unchanged (false-branch no-op).
# Proves the guard's false-branch is exercised so a loosened guard would fail this assertion.
OUT5="$TMPROOT/case5.json"
"${WRITER[@]}" --classification SIMPLE --partition-requested false --brainstorm-requested false --output "$OUT5" >/dev/null
before_sum=$(shasum -a 256 "$OUT5" | awk '{print $1}')
recovery_merge_if_needed "$OUT5" false false
after_sum=$(shasum -a 256 "$OUT5" | awk '{print $1}')
[[ "$before_sum" == "$after_sum" ]] || fail "case5: all-false guard mutated file; before=$before_sum after=$after_sum"
jq -e '.partition_requested == false and .brainstorm_requested == false and .approve_requested == false and (has("manual_gate_b") | not)' "$OUT5" >/dev/null \
  || fail "case5: all-false post-state mismatch"

# Case 6: missing run-params.json under a true argv flag warns and does not recreate fallback defaults.
OUT6="$TMPROOT/case6.json"
warning_case6=$(recovery_merge_if_needed "$OUT6" true false)
[[ ! -e "$OUT6" ]] || fail "case6: missing-file degraded path recreated $OUT6"
[[ "$warning_case6" == "**⚠ 0b: run-params.json missing after session write-run-params; refusing to recreate it with fallback defaults. Re-run \`python -m pytest python/test_session_env.py\` and fix the Step 0b contract drift first.**" ]] \
  || fail "case6: missing-file degraded warning drifted; got: $warning_case6"

# Case 7: a failing writer aborts BEFORE recovery (#3161). Spy absence proves recovery never
# ran; captured stdout proves the missing-file recovery warning was not emitted.
OUT7="$TMPROOT/case7.json"; SPY7="$TMPROOT/case7-recovery-reached"; rm -f "$SPY7"
set +e
out7_stdout=$(write_then_recover "$OUT7" BOGUS "$SPY7" true false 2>/dev/null)
rc7=$?
set -e
[[ "$rc7" -ne 0 ]] || fail "case7: failing writer must abort before recovery; rc=$rc7"
[[ ! -e "$SPY7" ]] || fail "case7: recovery completed after writer failure (spy present)"
[[ ! -e "$OUT7" ]] || fail "case7: failing writer created $OUT7"
[[ "$out7_stdout" != *"refusing to recreate it with fallback defaults"* ]] \
  || fail "case7: missing-file recovery warning emitted after writer failure (recovery not bypassed)"

# Case 7b (positive control): a successful write reaches AND completes recovery.
OUT7B="$TMPROOT/case7b.json"; SPY7B="$TMPROOT/case7b-recovery-reached"; rm -f "$SPY7B"
set +e; write_then_recover "$OUT7B" SIMPLE "$SPY7B" true false; rc7b=$?; set -e
[[ "$rc7b" -eq 0 ]] || fail "case7b: successful write_then_recover returned $rc7b"
[[ -e "$SPY7B" ]] || fail "case7b: recovery did not complete after successful write (spy absent)"
jq -e '.partition_requested == true' "$OUT7B" >/dev/null \
  || fail "case7b: recovery did not merge partition true; got $(cat "$OUT7B")"

# --- Production driver integration (stubbed plugin scripts) ---
FAKE_PLUGIN="$TMPROOT/fake-plugin"
STUB_SCRIPTS="$FAKE_PLUGIN/scripts"
mkdir -p "$STUB_SCRIPTS" "$FAKE_PLUGIN/python"
for _lib in lib-quiet.sh lib-larch-log.sh append-tool-failure.sh append-execution-issue.sh; do
  ln -sf "$REPO_ROOT/scripts/$_lib" "$STUB_SCRIPTS/$_lib"
done
cat >"$FAKE_PLUGIN/python/cli.py" <<STUB
#!/usr/bin/env python3
import os, subprocess, sys
if sys.argv[1:3] == ["session", "write-design-env"]:
    raise SystemExit(0)
raise SystemExit(subprocess.call(["$PYTHON_BIN", "$REPO_ROOT/python/cli.py", *sys.argv[1:]]))
STUB
chmod +x "$FAKE_PLUGIN/python/cli.py"
cat >"$STUB_SCRIPTS/tracking-issue-write.sh" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' 'RENAMED=true'
exit 0
STUB
chmod +x "$STUB_SCRIPTS/tracking-issue-write.sh"

run_design_init() {
  local dtmp="$1" partition="$2" brainstorm="$3" extra_path="${4:-}" approve="${5:-false}" skip_approve="${6:-false}"
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
    --approve-requested "$approve" \
    --skip-approve-requested "$skip_approve"
}

# Case 8: invoke production driver; brainstorm argv merges into run-params.json.
D8="$TMPROOT/driver8"
set +e
out8=$(run_design_init "$D8" false true 2>&1)
rc8=$?
set -e
[[ "$rc8" -eq 0 ]] || fail "case8: design-init-runparams.sh rc=$rc8 out=$out8"
[[ -f "$D8/run-params.json" ]] || fail "case8: missing run-params.json"
grep -Fq 'INIT_STATUS=ok' "$D8/.design-init-runparams-result.env" \
  || fail "case8: result env missing INIT_STATUS=ok"
jq -e '.brainstorm_requested == true and (has("manual_gate_b") | not)' "$D8/run-params.json" >/dev/null \
  || fail "case8: driver jq-merge failed; got $(cat "$D8/run-params.json")"

# Case 8a (#3628): approve argv merges into run-params.json (mirrors case 8 brainstorm merge).
D8A="$TMPROOT/driver8a"
set +e
out8a=$(run_design_init "$D8A" false false "" true 2>&1)
rc8a=$?
set -e
[[ "$rc8a" -eq 0 ]] || fail "case8a: design-init-runparams.sh rc=$rc8a out=$out8a"
[[ -f "$D8A/run-params.json" ]] || fail "case8a: missing run-params.json"
jq -e '.approve_requested == true' "$D8A/run-params.json" >/dev/null \
  || fail "case8a: approve jq-merge failed; got $(cat "$D8A/run-params.json")"

# Case 8b (#3735): skip_approve argv merges into run-params.json (mirrors case 8a approve merge).
D8B="$TMPROOT/driver8b"
set +e
out8b=$(run_design_init "$D8B" false false "" false true 2>&1)
rc8b=$?
set -e
[[ "$rc8b" -eq 0 ]] || fail "case8b: design-init-runparams.sh rc=$rc8b out=$out8b"
[[ -f "$D8B/run-params.json" ]] || fail "case8b: missing run-params.json"
jq -e '.skip_approve_requested == true and .approve_requested == false' "$D8B/run-params.json" >/dev/null \
  || fail "case8b: skip_approve jq-merge failed; got $(cat "$D8B/run-params.json")"

# Case 8c (#3735): stored skip_approve=true; argv=false with another true flag preserves skip_approve.
OUT8C="$TMPROOT/case8c.json"
"${WRITER[@]}" --classification SIMPLE --partition-requested false --brainstorm-requested false \
  --skip-approve-requested true --output "$OUT8C" >/dev/null
recovery_merge_if_needed "$OUT8C" true false false false
jq -e '.partition_requested == true and .skip_approve_requested == true' "$OUT8C" >/dev/null \
  || fail "case8c: skip_approve OR-merge regressed; got $(cat "$OUT8C")"

# Case 9: rename failure is best-effort; run-params still written.
cat >"$STUB_SCRIPTS/tracking-issue-write.sh" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
chmod +x "$STUB_SCRIPTS/tracking-issue-write.sh"
D9="$TMPROOT/driver9"
set +e
out9=$(run_design_init "$D9" false false 2>&1)
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
out10=$(run_design_init "$D10" true false "$JQ_STUB:$HOST_JQ_DIR:/usr/bin:/bin:/usr/local/bin" 2>&1)
unset LARCH_TEST_JQ_MERGE_FAIL
rc10=$?
set -e
[[ "$rc10" -eq 0 ]] || fail "case10: jq-fail driver rc=$rc10 out=$out10"
grep -Fq 'jq(router-flags-merge)' "$D10/execution-issues.md" \
  || fail "case10: execution-issues.md missing jq(router-flags-merge) append"

# Case 11: jq unavailable emits WARN on production driver stdout (write-run-params stubbed; merge needs jq).
# Unlink the symlink before writing so we don't clobber the real python/cli.py session write-run-params.
rm -f "$STUB_SCRIPTS/session write-run-params"
cat >"$STUB_SCRIPTS/session write-run-params" <<'STUB'
#!/usr/bin/env bash
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\n' '{"schema_version":3,"design_classification":"SIMPLE","partition_requested":false,"brainstorm_requested":false}' >"$out"
printf 'RUN_PARAMS_WRITTEN=%s\n' "$out"
exit 0
STUB
chmod +x "$STUB_SCRIPTS/session write-run-params"
D11="$TMPROOT/driver11"
# Build a PATH directory that has all tools needed by the script except jq, so
# command -v jq returns non-zero on every platform (e.g. /usr/bin/jq on Ubuntu CI).
_no_jq_path="$TMPROOT/no-jq-path"
mkdir -p "$_no_jq_path"
for _cmd in bash sh dirname basename mktemp mv rm mkdir cat printf chmod python3; do
  _real=$(command -v "$_cmd" 2>/dev/null || true)
  [ -n "$_real" ] && ln -sf "$_real" "$_no_jq_path/$_cmd"
done
# jq intentionally absent from _no_jq_path
set +e
out11=$(run_design_init "$D11" true false "$_no_jq_path" 2>&1)
rc11=$?
set -e
[[ "$rc11" -eq 0 ]] || fail "case11: jq-unavailable driver rc=$rc11 out=$out11"
printf '%s\n' "$out11" | grep -Fq 'jq is unavailable' \
  || fail "case11: missing jq-unavailable WARN on stdout"

# Case 12: prompt-side Step 0b route fence must merge current argv flags into
# resumed and already-planned flows, not only fresh proceed flows.
# shellcheck disable=SC2016 # fixed-string probe for literal SKILL.md shell text.
grep -Fq 'if [[ "${ROUTE:-}" == resume@* || "${ROUTE:-}" == already-planned ]]; then' "$REPO_ROOT/skills/design/SKILL.md" \
  || fail "case12: SKILL.md missing resume/already-planned route flag merge guard"
# shellcheck disable=SC2016 # fixed-string probe for literal jq filter text.
grep -Fq '.approve_requested = (.approve_requested == true or $merge_a)' "$REPO_ROOT/skills/design/SKILL.md" \
  || fail "case12: SKILL.md route merge must preserve current --per-round-approval"
# shellcheck disable=SC2016 # fixed-string probe for literal jq filter text.
grep -Fq '.skip_approve_requested = (.skip_approve_requested == true or $merge_s)' "$REPO_ROOT/skills/design/SKILL.md" \
  || fail "case12: SKILL.md route merge must preserve current --skip-approve"

echo "PASS: test-step0b-router-flag-recovery.sh"
