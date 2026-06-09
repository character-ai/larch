#!/usr/bin/env bash
# Offline harness for design-postplan-emit.sh.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SUBJECT="$SCRIPT_DIR/design-postplan-emit.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"

PASS=0
FAIL=0

fail() {
    FAIL=$((FAIL + 1))
    printf '  FAIL: %s\n' "$*" >&2
}

pass() {
    PASS=$((PASS + 1))
    printf '  PASS: %s\n' "$*"
}

assert_rc() {
    local name="$1" want="$2" got="$3"
    if [[ "$got" != "$want" ]]; then
        fail "$name — expected exit $want, got $got"
        return 1
    fi
    pass "$name"
}

assert_file_kv() {
    local file="$1" key="$2" want="$3" label="$4" got=""
    got=$(awk -F= -v k="$key" '$1 == k {print substr($0, length(k)+2); found=1; exit} END {if (!found) print ""}' "$file" 2>/dev/null || true)
    if [[ "$got" != "$want" ]]; then
        fail "$label — expected $key=$want, got ${got:-<empty>}"
        return 1
    fi
    pass "$label"
}

assert_contains() {
    local file="$1" needle="$2" label="$3"
    if grep -Fq -- "$needle" "$file"; then
        pass "$label"
    else
        fail "$label"
    fi
}

assert_not_contains() {
    local file="$1" needle="$2" label="$3"
    if grep -Fq -- "$needle" "$file"; then
        fail "$label"
    else
        pass "$label"
    fi
}

assert_not_exists_or_empty() {
    local file="$1" label="$2"
    if [[ ! -s "$file" ]]; then
        pass "$label"
    else
        fail "$label"
    fi
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-postplan-emit.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAKE_PLUGIN="$TMP/plugin"
FAKE_DESIGN="$FAKE_PLUGIN/skills/design/scripts"
FAKE_SCRIPTS="$FAKE_PLUGIN/scripts"
mkdir -p "$FAKE_DESIGN" "$FAKE_SCRIPTS" "$FAKE_PLUGIN/python/stubs/session"
cp "$REPO_ROOT/python/"*.py "$FAKE_PLUGIN/python/"
mv "$FAKE_PLUGIN/python/cli.py" "$FAKE_PLUGIN/python/real-cli.py"
cat >"$FAKE_PLUGIN/python/cli.py" <<'DISPATCHER'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def main() -> None:
    root = Path(__file__).resolve().parent
    if len(sys.argv) >= 3 and sys.argv[1] == "session":
        stub = root / "stubs" / "session" / sys.argv[2]
        if stub.is_file() and os.access(stub, os.X_OK):
            os.execv(str(stub), [str(stub), *sys.argv[3:]])
    os.execv(sys.executable, [sys.executable, str(root / "real-cli.py"), *sys.argv[1:]])

if __name__ == "__main__":
    main()
DISPATCHER
chmod +x "$FAKE_PLUGIN/python/cli.py"
ln -sf "$REPO_ROOT/scripts/lib-quiet.sh" "$FAKE_SCRIPTS/lib-quiet.sh"
ln -sf "$REPO_ROOT/scripts/lib-design-tmpdir.sh" "$FAKE_SCRIPTS/lib-design-tmpdir.sh"
ln -sf "$REPO_ROOT/scripts/append-tool-failure.sh" "$FAKE_SCRIPTS/append-tool-failure.sh"
ln -sf "$REPO_ROOT/scripts/append-execution-issue.sh" "$FAKE_SCRIPTS/append-execution-issue.sh"
ln -sf "$SCRIPT_DIR/lib-phase-driver.sh" "$FAKE_DESIGN/lib-phase-driver.sh"
ln -sf "$SCRIPT_DIR/check-plan-size.sh" "$FAKE_DESIGN/check-plan-size.sh"
ln -sf "$SCRIPT_DIR/lib-plan-optional-trailers.sh" "$FAKE_DESIGN/lib-plan-optional-trailers.sh"
ln -sf "$SCRIPT_DIR/lib-plan-optional-trailers.awk" "$FAKE_DESIGN/lib-plan-optional-trailers.awk"
ln -sf "$SCRIPT_DIR/lib-drift-baseline.sh" "$FAKE_DESIGN/lib-drift-baseline.sh"

cat >"$FAKE_DESIGN/design-driver.sh" <<'STUB'
#!/usr/bin/env bash
while IFS= read -r line || [[ -n "$line" ]]; do
  case "$line" in
    ACTION=EMIT_PLAN)
      echo "design-driver EMIT" >>"${CALL_LOG:?}"
      if [[ "${EMIT_STUB_RC:-0}" -ne 0 ]]; then
        [[ "${EMIT_OMIT_STATUS:-false}" == true ]] || printf 'EMIT_PLAN_STATUS=%s\n' "${EMIT_STATUS_VALUE:-failed}"
        exit "${EMIT_STUB_RC}"
      fi
      printf 'EMIT_PLAN_STATUS=%s\n' "${EMIT_STATUS_VALUE:-ok}"
      if [[ "${EMIT_STATUS_VALUE:-ok}" == ok ]]; then
        printf 'DIFF_LINES=%s\n' "${DIFF_LINES_VALUE:-12}"
      fi
      [[ "${EMIT_STATUS_VALUE:-ok}" == ok ]] || exit 1
      ;;
  esac
done
STUB

cat >"$FAKE_DESIGN/snapshot-plan-round.sh" <<'STUB'
#!/usr/bin/env bash
echo "snapshot $*" >>"${CALL_LOG:?}"
if [[ "${SNAPSHOT_STUB_RC:-0}" -ne 0 ]]; then
  exit "${SNAPSHOT_STUB_RC}"
fi
for arg in "$@"; do
  if [[ "$arg" == --design-tmpdir ]]; then
    shift
    break
  fi
  shift
done
cp -p "${1:?}/plan.txt" "${1:?}/plan.txt-original" 2>/dev/null || : >"${1:?}/plan.txt-original"
STUB

cat >"$FAKE_DESIGN/invoke-plan-validator.sh" <<'STUB'
#!/usr/bin/env bash
echo "validator $*" >>"${CALL_LOG:?}"
if [[ "${VALIDATOR_STUB_RC:-0}" -ne 0 ]]; then
  [[ "${VALIDATOR_EMIT_STATUS_ON_FAIL:-false}" == true ]] && printf 'VALIDATE_STATUS=%s\n' "${VALIDATE_STATUS_VALUE:-defects-found}"
  exit "${VALIDATOR_STUB_RC}"
fi
printf 'VALIDATE_STATUS=%s\n' "${VALIDATE_STATUS_VALUE:-ok}"
printf 'VALIDATE_DEFECT_COUNT=%s\n' "${VALIDATE_DEFECT_COUNT_VALUE:-0}"
printf 'VALIDATE_SKIPPED_COUNT=%s\n' "${VALIDATE_SKIPPED_COUNT_VALUE:-0}"
printf 'VALIDATE_UNSAFE_TOKEN_COUNT=%s\n' "${VALIDATE_UNSAFE_TOKEN_COUNT_VALUE:-0}"
printf 'VALIDATE_LOG_FILE=%s\n' "${DESIGN_TMPDIR:?}/validate-plan-commands.log"
STUB

cat >"$FAKE_SCRIPTS/design-pause-save.sh" <<'STUB'
#!/usr/bin/env bash
echo "pause-save $*" >>"${CALL_LOG:?}"
exit 0
STUB
chmod +x "$FAKE_DESIGN"/*.sh "$FAKE_SCRIPTS"/*.sh
export CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN"
export CALL_LOG="$TMP/call.log"

reset_env() {
    : >"$CALL_LOG"
    unset EMIT_STUB_RC EMIT_STATUS_VALUE EMIT_OMIT_STATUS DIFF_LINES_VALUE \
        SNAPSHOT_STUB_RC VALIDATOR_STUB_RC VALIDATOR_EMIT_STATUS_ON_FAIL \
        VALIDATE_STATUS_VALUE VALIDATE_DEFECT_COUNT_VALUE VALIDATE_SKIPPED_COUNT_VALUE \
        VALIDATE_UNSAFE_TOKEN_COUNT_VALUE ISSUE_NUMBER REPO || true
}

setup_design_tmp() {
    local d="$1" _legacy_budget="${2:-full}" workflow="${3:-SIMPLE}"
    mkdir -p "$d"
    printf '# Plan

diff_lines: 12
' >"$d/plan.txt"
    printf '{"workflow_path":"%s","design_classification":"%s"}
' "$workflow" "$workflow" >"$d/run-params.json"
    printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s
' "$FAKE_PLUGIN" >"$d/session-env.sh"
}

run_subject() {
    local d="$1"
    shift
    reset_env
    bash "$SUBJECT" --design-tmpdir "$d" "$@" >"$d/stdout.txt" 2>"$d/stderr.txt"
}

run_subject_quiet_parent() {
    local d="$1"
    shift
    reset_env
    env -u LARCH_QUIET_DISABLE CALL_LOG="$CALL_LOG" CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" \
        bash "$SUBJECT" --design-tmpdir "$d" "$@" >"$d/stdout.txt" 2>"$d/stderr.txt"
}

fill_plan_lines() {
    local file="$1" n="$2" msg="${3:-body line}"
    if [[ "$file" == /dev/stdout ]]; then
        awk -v n="$n" -v m="$msg" 'BEGIN { for (i = 1; i <= n; i++) print m }'
    else
        awk -v n="$n" -v m="$msg" 'BEGIN { for (i = 1; i <= n; i++) print m }' >>"$file"
    fi
}

write_small_plan() {
    local d="$1"
    printf '# Plan\n\ndiff_lines: 12\n' >"$d/plan.txt"
}

# 1 happy SIMPLE non-quick
D1="$TMP/happy-simple"
setup_design_tmp "$D1" full SIMPLE
set +e
run_subject "$D1"
rc=$?
set -e
assert_rc "happy SIMPLE" 0 "$rc"
assert_file_kv "$D1/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS ok "happy status"
assert_file_kv "$D1/.design-postplan-emit-result.env" SNAPSHOT_STATUS skipped-suppressed "happy snapshot suppressed"
assert_file_kv "$D1/.design-postplan-emit-result.env" VALIDATE_STATUS ok "happy validator"
assert_contains "$CALL_LOG" 'design-driver EMIT' "happy called EMIT"
assert_contains "$CALL_LOG" 'validator' "happy called validator"

# 2 initial HARD snapshot taken
D2="$TMP/hard-snapshot"
setup_design_tmp "$D2" full HARD
set +e
run_subject "$D2" --snapshot-original
rc=$?
set -e
assert_rc "HARD snapshot" 0 "$rc"
assert_file_kv "$D2/.design-postplan-emit-result.env" SNAPSHOT_STATUS taken "HARD snapshot taken"
if [[ -f "$D2/plan.txt-original" ]]; then
    pass "HARD original exists"
else
    fail "HARD original exists"
fi

# 2b idempotent snapshot: plan.txt-original already exists → preserved
D2b="$TMP/hard-preserved"
setup_design_tmp "$D2b" full HARD
: >"$D2b/plan.txt-original"
set +e
run_subject "$D2b" --snapshot-original
rc=$?
set -e
assert_rc "HARD snapshot preserved" 0 "$rc"
assert_file_kv "$D2b/.design-postplan-emit-result.env" SNAPSHOT_STATUS preserved "HARD snapshot preserved"


# 2c classification overrides legacy workflow_path for snapshots
D2c="$TMP/classification-hard-legacy-simple"
setup_design_tmp "$D2c" full SIMPLE
printf '{"workflow_path":"SIMPLE","design_classification":"HARD"}
' >"$D2c/run-params.json"
set +e
run_subject "$D2c" --snapshot-original
rc=$?
set -e
assert_rc "classification HARD snapshot" 0 "$rc"
assert_file_kv "$D2c/.design-postplan-emit-result.env" SNAPSHOT_STATUS taken "classification HARD snapshot taken"

D2d="$TMP/classification-missing"
setup_design_tmp "$D2d" full SIMPLE
printf '{"workflow_path":"SIMPLE"}
' >"$D2d/run-params.json"
set +e
run_subject "$D2d" --snapshot-original
rc=$?
set -e
assert_rc "missing classification snapshot" 0 "$rc"
assert_file_kv "$D2d/.design-postplan-emit-result.env" SNAPSHOT_STATUS taken "missing classification fails closed HARD snapshot"

D2d_warn="$TMP/classification-warning-quiet"
mkdir -p "$D2d_warn"
printf '# Plan\n\ndiff_lines: 12\n' >"$D2d_warn/plan.txt"
printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$FAKE_PLUGIN" >"$D2d_warn/session-env.sh"
reset_env
set +e
env -u LARCH_QUIET_DISABLE CALL_LOG="$CALL_LOG" CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" \
    bash "$SUBJECT" --design-tmpdir "$D2d_warn" >"$D2d_warn/stdout.txt" 2>"$D2d_warn/stderr.txt"
rc=$?
set -e
export LARCH_QUIET_DISABLE=1
assert_rc "classification warning quiet rc" 0 "$rc"
assert_contains "$D2d_warn/stdout.txt" 'WARN=**⚠ read-design-classification: run-params not readable' "classification warning emits WARN in quiet mode"

D2d_invalid_warn="$TMP/classification-invalid-quiet"
mkdir -p "$D2d_invalid_warn"
printf '# Plan\n\ndiff_lines: 12\n' >"$D2d_invalid_warn/plan.txt"
printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$FAKE_PLUGIN" >"$D2d_invalid_warn/session-env.sh"
printf '{"workflow_path":"SIMPLE"}\n' >"$D2d_invalid_warn/run-params.json"
reset_env
set +e
env -u LARCH_QUIET_DISABLE CALL_LOG="$CALL_LOG" CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" \
    bash "$SUBJECT" --design-tmpdir "$D2d_invalid_warn" >"$D2d_invalid_warn/stdout.txt" 2>"$D2d_invalid_warn/stderr.txt"
rc=$?
set -e
export LARCH_QUIET_DISABLE=1
assert_rc "classification invalid quiet rc" 0 "$rc"
assert_contains "$D2d_invalid_warn/stdout.txt" 'WARN=**⚠ read-design-classification: design_classification missing or invalid' "invalid classification warning emits WARN in quiet mode"

D2d_silent_nonzero="$TMP/classification-silent-nonzero"
setup_design_tmp "$D2d_silent_nonzero" full SIMPLE
cat >"$FAKE_PLUGIN/python/stubs/session/read-classification" <<'STUB'
#!/usr/bin/env bash
exit 9
STUB
chmod +x "$FAKE_PLUGIN/python/stubs/session/read-classification"
set +e
run_subject "$D2d_silent_nonzero" --snapshot-original
rc=$?
set -e
assert_rc "classification silent nonzero rc" 0 "$rc"
assert_contains "$D2d_silent_nonzero/stdout.txt" 'WARN=**⚠ read-design-classification: exited 9; defaulting design_classification to HARD.**' "classification silent nonzero emits synthetic WARN"
assert_file_kv "$D2d_silent_nonzero/.design-postplan-emit-result.env" SNAPSHOT_STATUS taken "classification silent nonzero defaults HARD"
rm -f "$FAKE_PLUGIN/python/stubs/session/read-classification"

D2e="$TMP/classification-simple-legacy-hard"
setup_design_tmp "$D2e" full HARD
printf '{"workflow_path":"HARD","design_classification":"SIMPLE"}
' >"$D2e/run-params.json"
set +e
run_subject "$D2e" --snapshot-original
rc=$?
set -e
assert_rc "classification SIMPLE skip snapshot" 0 "$rc"
assert_file_kv "$D2e/.design-postplan-emit-result.env" SNAPSHOT_STATUS skipped-not-hard "classification SIMPLE skips snapshot"

# 3 re-emit snapshot suppressed, even HARD
D3="$TMP/hard-suppressed"
setup_design_tmp "$D3" full HARD
set +e
run_subject "$D3"
rc=$?
set -e
assert_rc "HARD re-emit snapshot suppressed" 0 "$rc"
assert_file_kv "$D3/.design-postplan-emit-result.env" SNAPSHOT_STATUS skipped-suppressed "HARD re-emit suppressed"

# 4 legacy review_budget=quick is ignored; validator still runs
D4="$TMP/legacy-quick-validates"
setup_design_tmp "$D4" quick SIMPLE
printf '{"review_budget":"quick","workflow_path":"SIMPLE","design_classification":"SIMPLE"}
' >"$D4/run-params.json"
set +e
run_subject "$D4"
rc=$?
set -e
assert_rc "legacy quick validates" 0 "$rc"
assert_file_kv "$D4/.design-postplan-emit-result.env" VALIDATE_STATUS ok "legacy quick validator status"
assert_contains "$CALL_LOG" 'validator' "legacy quick called validator"

# 5 defects-found is success
D5="$TMP/defects"
setup_design_tmp "$D5" full SIMPLE
reset_env
export VALIDATE_STATUS_VALUE=defects-found VALIDATE_DEFECT_COUNT_VALUE=2
set +e
bash "$SUBJECT" --design-tmpdir "$D5" >"$D5/stdout.txt" 2>"$D5/stderr.txt"
rc=$?
set -e
assert_rc "defects-found rc" 0 "$rc"
assert_file_kv "$D5/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS ok "defects postplan ok"
assert_file_kv "$D5/.design-postplan-emit-result.env" VALIDATE_STATUS defects-found "defects status surfaced"

# 6 missing diff lines
D6="$TMP/missing-diff"
setup_design_tmp "$D6" full SIMPLE
reset_env
export EMIT_STATUS_VALUE=missing-diff-lines
set +e
bash "$SUBJECT" --design-tmpdir "$D6" >"$D6/stdout.txt" 2>"$D6/stderr.txt"
rc=$?
set -e
assert_rc "missing diff rc" 1 "$rc"
assert_file_kv "$D6/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS missing-diff-lines "missing diff status"
assert_file_kv "$D6/.design-postplan-emit-result.env" VALIDATE_STATUS not-run "missing diff validator not run"

# 7 snapshot failure
D7="$TMP/snapshot-fail"
setup_design_tmp "$D7" full HARD
reset_env
export SNAPSHOT_STUB_RC=1
set +e
bash "$SUBJECT" --design-tmpdir "$D7" --snapshot-original >"$D7/stdout.txt" 2>"$D7/stderr.txt"
rc=$?
set -e
assert_rc "snapshot failure rc" 1 "$rc"
assert_file_kv "$D7/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS snapshot-failed "snapshot failed status"
assert_file_kv "$D7/.design-postplan-emit-result.env" SNAPSHOT_STATUS failed "snapshot status failed"

# 8 validator infra failure
D8="$TMP/validator-fail"
setup_design_tmp "$D8" full SIMPLE
reset_env
export VALIDATOR_STUB_RC=1
set +e
bash "$SUBJECT" --design-tmpdir "$D8" >"$D8/stdout.txt" 2>"$D8/stderr.txt"
rc=$?
set -e
assert_rc "validator infra failure rc" 1 "$rc"
assert_file_kv "$D8/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS validate-driver-failed "validator infra status"

# 8b validator exits 0 but emits no VALIDATE_STATUS → validate-driver-failed
D8b="$TMP/validator-silent"
setup_design_tmp "$D8b" full SIMPLE
reset_env
export VALIDATOR_STUB_RC=0 VALIDATE_STATUS_VALUE=""
# Suppress VALIDATE_STATUS emission from stub
cat >"$FAKE_DESIGN/invoke-plan-validator.sh" <<'STUB2'
#!/usr/bin/env bash
echo "validator $*" >>"${CALL_LOG:?}"
# intentionally emits no VALIDATE_STATUS
exit 0
STUB2
chmod +x "$FAKE_DESIGN/invoke-plan-validator.sh"
set +e
bash "$SUBJECT" --design-tmpdir "$D8b" >"$D8b/stdout.txt" 2>"$D8b/stderr.txt"
rc=$?
set -e
assert_rc "validator silent rc" 1 "$rc"
assert_file_kv "$D8b/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS validate-driver-failed "validator silent status"
# Restore stub
cat >"$FAKE_DESIGN/invoke-plan-validator.sh" <<'STUB'
#!/usr/bin/env bash
echo "validator $*" >>"${CALL_LOG:?}"
if [[ "${VALIDATOR_STUB_RC:-0}" -ne 0 ]]; then
  [[ "${VALIDATOR_EMIT_STATUS_ON_FAIL:-false}" == true ]] && printf 'VALIDATE_STATUS=%s\n' "${VALIDATE_STATUS_VALUE:-defects-found}"
  exit "${VALIDATOR_STUB_RC}"
fi
printf 'VALIDATE_STATUS=%s\n' "${VALIDATE_STATUS_VALUE:-ok}"
printf 'VALIDATE_DEFECT_COUNT=%s\n' "${VALIDATE_DEFECT_COUNT_VALUE:-0}"
printf 'VALIDATE_SKIPPED_COUNT=%s\n' "${VALIDATE_SKIPPED_COUNT_VALUE:-0}"
printf 'VALIDATE_UNSAFE_TOKEN_COUNT=%s\n' "${VALIDATE_UNSAFE_TOKEN_COUNT_VALUE:-0}"
printf 'VALIDATE_LOG_FILE=%s\n' "${DESIGN_TMPDIR:?}/validate-plan-commands.log"
STUB
chmod +x "$FAKE_DESIGN/invoke-plan-validator.sh"

# 9 usage/config error
set +e
bash "$SUBJECT" >"$TMP/usage.out" 2>"$TMP/usage.err"
rc=$?
set -e
assert_rc "usage error" 2 "$rc"

# 10 partial failures still flush mandatory KVs
for d in "$D6" "$D7" "$D8"; do
    for key in POSTPLAN_EMIT_STATUS EMIT_PLAN_STATUS DIFF_LINES SNAPSHOT_STATUS VALIDATE_STATUS VALIDATE_DEFECT_COUNT VALIDATE_SKIPPED_COUNT VALIDATE_UNSAFE_TOKEN_COUNT VALIDATE_LOG_FILE; do
        grep -q "^${key}=" "$d/.design-postplan-emit-result.env" || fail "partial failure missing $key in $d"
    done
done
pass "partial failures write mandatory KV matrix"

# 11 pause before first internal step, export-format source-env issue
D11="$TMP/pause"
setup_design_tmp "$D11" full SIMPLE
printf 'export ISSUE_NUMBER=77\nexport REPO=owner/name\n' >"$D11/source-env.sh"
: >"$D11/.pause-requested"
set +e
run_subject "$D11"
rc=$?
set -e
assert_rc "pause checkpoint rc" 0 "$rc"
assert_contains "$CALL_LOG" 'pause-save --design-tmpdir' "pause-save invoked"
assert_contains "$CALL_LOG" '--issue 77' "pause-save issue resolved"
assert_contains "$CALL_LOG" '--repo owner/name' "pause-save repo resolved"
if grep -Fq 'design-driver EMIT' "$CALL_LOG"; then fail "pause should happen before EMIT"; else pass "pause happened before EMIT"; fi
assert_file_kv "$D11/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS paused "pause writes paused status to result env"

# 11a explicit --repo overrides source-env repo
D11a="$TMP/pause-explicit-repo"
setup_design_tmp "$D11a" full SIMPLE
printf 'export ISSUE_NUMBER=78\nexport REPO=source/repo\n' >"$D11a/source-env.sh"
: >"$D11a/.pause-requested"
set +e
run_subject "$D11a"
rc=$?
set -e
assert_rc "pause source repo checkpoint rc" 0 "$rc"
assert_contains "$CALL_LOG" '--issue 78' "pause explicit repo issue resolved"
assert_contains "$CALL_LOG" '--repo source/repo' "pause source repo forwarded"

# 11a.1 invalid source-env repo emits structured pause failure
D11a_bad_source="$TMP/pause-invalid-source-repo"
setup_design_tmp "$D11a_bad_source" full SIMPLE
printf 'export ISSUE_NUMBER=79\nexport REPO=--bad/repo\n' >"$D11a_bad_source/source-env.sh"
: >"$D11a_bad_source/.pause-requested"
set +e
run_subject "$D11a_bad_source"
rc=$?
set -e
assert_rc "pause invalid source repo rc" 1 "$rc"
assert_contains "$D11a_bad_source/stdout.txt" 'POSTPLAN_EMIT_STATUS=pause-failed' "pause invalid source repo writes pause-failed status"
assert_contains "$D11a_bad_source/stdout.txt" 'PAUSE_OK=false' "pause invalid source repo emits PAUSE_OK=false"
assert_contains "$D11a_bad_source/stdout.txt" 'ERROR=invalid-repo' "pause invalid source repo emits invalid-repo"
assert_not_contains "$CALL_LOG" 'pause-save' "pause invalid source repo skips pause-save"

# 11b empty/absent REPO omits --repo
D11b="$TMP/pause-no-repo"
setup_design_tmp "$D11b" full SIMPLE
printf 'export ISSUE_NUMBER=88\n' >"$D11b/source-env.sh"
: >"$D11b/.pause-requested"
set +e
run_subject "$D11b"
rc=$?
set -e
assert_rc "pause no repo checkpoint rc" 0 "$rc"
assert_contains "$CALL_LOG" '--issue 88' "pause no repo issue resolved"
assert_not_contains "$CALL_LOG" '--repo' "pause no repo omits repo flag"

# 12 --force-validate is removed and rejected as unknown
D12="$TMP/force-removed"
setup_design_tmp "$D12" full SIMPLE
set +e
run_subject "$D12" --force-validate
rc=$?
set -e
assert_rc "force validate removed" 2 "$rc"
assert_not_exists_or_empty "$D12/.design-postplan-emit-result.env" "force validate removed writes no result env"

# --- --with-plan-size merged mode ---
D13="$TMP/merged-clean"
setup_design_tmp "$D13" full SIMPLE
set +e
run_subject "$D13" --with-plan-size
rc=$?
set -e
assert_rc "merged clean" 0 "$rc"
assert_file_kv "$D13/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS ok "merged clean status"
assert_file_kv "$D13/.design-postplan-emit-result.env" PLAN_SIZE_STATUS under-threshold "merged clean plan-size"
assert_contains "$D13/stdout.txt" 'under thresholds' "merged clean breadcrumb"
assert_not_contains "$D13/stdout.txt" 'POSTPLAN_EMIT_STATUS=' "merged no stdout KV"
assert_not_contains "$D13/stdout.txt" 'WARN=' "merged no WARN= leakage"

D14="$TMP/merged-hard-body"
setup_design_tmp "$D14" full SIMPLE
{
    printf '# Plan\n'
    for _ in $(seq 1 5); do printf "### NEW: \`z%s.md\`\n" "$_"; done
    fill_plan_lines /dev/stdout 796 b
    printf 'diff_lines: 400\n'
} >"$D14/plan.txt"
set +e
run_subject "$D14" --with-plan-size
rc=$?
set -e
assert_rc "merged hard body" 12 "$rc"
assert_file_kv "$D14/.design-postplan-emit-result.env" HARD_TRIGGER_FIRED true "merged hard KV"
assert_contains "$D14/stdout.txt" '## Plan Size — Hard Trigger' "merged hard section"

D15="$TMP/merged-hard-diff-added"
setup_design_tmp "$D15" full SIMPLE
{
    printf '# Plan\n'
    for _ in $(seq 1 5); do printf "### NEW: \`q%s.md\`\n" "$_"; done
    fill_plan_lines /dev/stdout 195 b
    printf 'diff_added: 2001\n'
    printf 'diff_lines: 500\n'
} >"$D15/plan.txt"
set +e
run_subject "$D15" --with-plan-size
rc=$?
set -e
assert_rc "merged hard diff_added" 12 "$rc"

D16="$TMP/merged-soft"
setup_design_tmp "$D16" full SIMPLE
{
    printf '# Plan\n'
    for _ in $(seq 1 5); do printf "### NEW: \`m%s.md\`\n" "$_"; done
    fill_plan_lines /dev/stdout 195 b
    printf 'diff_added: 2001\n'
    printf 'mechanical_churn: true\n'
    printf 'diff_lines: 5000\n'
} >"$D16/plan.txt"
set +e
run_subject "$D16" --with-plan-size
rc=$?
set -e
assert_rc "merged soft advisory" 0 "$rc"
assert_contains "$D16/stdout.txt" 'mechanical-churn advisory' "merged soft advisory display"

D17="$TMP/merged-soft-hard"
setup_design_tmp "$D17" full SIMPLE
{
    printf '# Plan\n'
    for _ in $(seq 1 5); do printf "### NEW: \`z%s.md\`\n" "$_"; done
    fill_plan_lines /dev/stdout 796 b
    printf 'diff_added: 2001\n'
    printf 'mechanical_churn: true\n'
    printf 'diff_lines: 5000\n'
} >"$D17/plan.txt"
set +e
run_subject "$D17" --with-plan-size
rc=$?
set -e
assert_rc "merged soft+hard" 12 "$rc"
assert_contains "$D17/stdout.txt" 'mechanical-churn advisory' "merged soft+hard advisory"
assert_contains "$D17/stdout.txt" '## Plan Size — Hard Trigger' "merged soft+hard hard section"

D18="$TMP/merged-partition"
setup_design_tmp "$D18" full SIMPLE
printf '{"review_budget":"full","workflow_path":"SIMPLE","design_classification":"SIMPLE","partition_requested":true}\n' >"$D18/run-params.json"
write_small_plan "$D18"
set +e
run_subject "$D18" --with-plan-size
rc=$?
set -e
assert_rc "merged partition" 13 "$rc"
assert_contains "$D18/stdout.txt" '## Plan Size — Partition requested' "merged partition section"

D18b="$TMP/merged-partition-no-jq"
setup_design_tmp "$D18b" full SIMPLE
printf '{"review_budget":"full","partition_requested":true}\n' >"$D18b/run-params.json"
write_small_plan "$D18b"
PATH_SAVE="$PATH"
PATH=$(printf '%s\n' "$PATH" | tr ':' '\n' | grep -vx 'jq' | paste -sd: -)
set +e
run_subject "$D18b" --with-plan-size
rc=$?
set -e
PATH="$PATH_SAVE"
assert_rc "merged partition no jq" 13 "$rc"

D19="$TMP/merged-partition-hard"
setup_design_tmp "$D19" full SIMPLE
printf '{"review_budget":"full","partition_requested":true}\n' >"$D19/run-params.json"
{
    printf '# Plan\n'
    for _ in $(seq 1 5); do printf "### NEW: \`z%s.md\`\n" "$_"; done
    fill_plan_lines /dev/stdout 796 b
    printf 'diff_lines: 400\n'
} >"$D19/plan.txt"
set +e
run_subject "$D19" --with-plan-size
rc=$?
set -e
assert_rc "merged partition+hard" 12 "$rc"

D20="$TMP/merged-defects"
setup_design_tmp "$D20" full SIMPLE
reset_env
export VALIDATE_STATUS_VALUE=defects-found VALIDATE_DEFECT_COUNT_VALUE=2
set +e
bash "$SUBJECT" --design-tmpdir "$D20" --with-plan-size >"$D20/stdout.txt" 2>"$D20/stderr.txt"
rc=$?
set -e
assert_rc "merged defects" 10 "$rc"
assert_file_kv "$D20/.design-postplan-emit-result.env" VALIDATE_STATUS defects-found "merged defects validate"
assert_file_kv "$D20/.design-postplan-emit-result.env" PLAN_SIZE_STATUS skipped-defects "merged defects skip plan-size"

D21="$TMP/merged-pause"
setup_design_tmp "$D21" full SIMPLE
printf 'export ISSUE_NUMBER=99\n' >"$D21/source-env.sh"
: >"$D21/.pause-requested"
set +e
run_subject "$D21" --with-plan-size
rc=$?
set -e
assert_rc "merged pause" 11 "$rc"
assert_not_contains "$CALL_LOG" 'pause-save' "merged pause no exec"
assert_file_kv "$D21/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS paused "merged pause status"

D22="$TMP/merged-plan-size-rc2"
setup_design_tmp "$D22" full SIMPLE
printf 'x\n' >"$D22/plan.txt"
set +e
run_subject "$D22" --with-plan-size
rc=$?
set -e
assert_rc "merged plan-size rc2" 1 "$rc"
assert_contains "$D22/stdout.txt" 'proceeding without threshold check' "merged rc2 warn display"
assert_not_contains "$D22/stdout.txt" 'APPENDED=' "merged rc2 no APPENDED"
[[ -f "$D22/check-plan-size.validation.log" ]] || fail "merged rc2 validation log"

D23="$TMP/merged-quiet-nested"
setup_design_tmp "$D23" full SIMPLE
set +e
run_subject_quiet_parent "$D23" --with-plan-size
rc=$?
set -e
export LARCH_QUIET_DISABLE=1
assert_rc "merged quiet parent" 0 "$rc"
assert_file_kv "$D23/.design-postplan-emit-result.env" PLAN_SIZE_STATUS under-threshold "merged quiet parent env"

D24="$TMP/merged-classification-warn"
setup_design_tmp "$D24" full SIMPLE
rm -f "$D24/run-params.json"
set +e
run_subject "$D24" --with-plan-size --snapshot-original
rc=$?
set -e
assert_rc "merged classification warn" 0 "$rc"
assert_contains "$D24/stdout.txt" 'read-design-classification' "merged classification warn display"
assert_not_contains "$D24/stdout.txt" 'WARN=' "merged classification no WARN="
grep -Fq 'WARN=' "$D24/.design-postplan-emit-result.env" || fail "merged classification WARN in env"

D25="$TMP/merged-missing-diff"
setup_design_tmp "$D25" full SIMPLE
reset_env
export EMIT_STATUS_VALUE=missing-diff-lines
set +e
bash "$SUBJECT" --design-tmpdir "$D25" --with-plan-size >"$D25/stdout.txt" 2>"$D25/stderr.txt"
rc=$?
set -e
assert_rc "merged missing diff" 1 "$rc"
assert_contains "$D25/stdout.txt" 'missing a final diff_lines' "merged missing diff diagnostic"

D26="$TMP/merged-result-env-refuse"
setup_design_tmp "$D26" full SIMPLE
ln -sf /tmp "$D26/.design-postplan-emit-result.env"
set +e
run_subject "$D26" --with-plan-size
rc=$?
set -e
rm -f "$D26/.design-postplan-emit-result.env"
assert_rc "merged result env refuse" 1 "$rc"
assert_contains "$D26/stdout.txt" 'result env write failed' "merged result env diagnostic"
assert_not_contains "$D26/stdout.txt" 'POSTPLAN_EMIT_STATUS=' "merged result env no stdout fallback"

D27="$TMP/merged-plan-size-append-fails"
rm -f "$FAKE_DESIGN/check-plan-size.sh" "$FAKE_SCRIPTS/append-tool-failure.sh"
cat >"$FAKE_DESIGN/check-plan-size.sh" <<'STUB'
#!/usr/bin/env bash
printf 'PLAN_SIZE_STATUS=missing-plan\n'
printf 'stderr detail from check-plan-size\n' >&2
exit 2
STUB
cat >"$FAKE_SCRIPTS/append-tool-failure.sh" <<'STUB'
#!/usr/bin/env bash
printf 'APPENDED=false\nLOG=/tmp/leak\n'
exit 7
STUB
chmod +x "$FAKE_DESIGN/check-plan-size.sh" "$FAKE_SCRIPTS/append-tool-failure.sh"
setup_design_tmp "$D27" full SIMPLE
set +e
run_subject "$D27" --with-plan-size
rc=$?
set -e
assert_rc "merged plan-size append failure is fatal" 1 "$rc"
assert_contains "$D27/stdout.txt" 'proceeding without threshold check' "merged append failure warning display"
assert_contains "$D27/check-plan-size.validation.log" 'stderr detail from check-plan-size' "merged append failure preserves stderr"
assert_not_contains "$D27/stdout.txt" 'APPENDED=' "merged append failure no APPENDED leak"
assert_not_contains "$D27/stdout.txt" 'LOG=' "merged append failure no LOG leak"
rm -f "$FAKE_DESIGN/check-plan-size.sh" "$FAKE_SCRIPTS/append-tool-failure.sh"
ln -sf "$SCRIPT_DIR/check-plan-size.sh" "$FAKE_DESIGN/check-plan-size.sh"
ln -sf "$REPO_ROOT/scripts/append-tool-failure.sh" "$FAKE_SCRIPTS/append-tool-failure.sh"

D28="$TMP/merged-snapshot-failed-diagnostic"
setup_design_tmp "$D28" full HARD
reset_env
export SNAPSHOT_STUB_RC=9
set +e
bash "$SUBJECT" --design-tmpdir "$D28" --with-plan-size --snapshot-original >"$D28/stdout.txt" 2>"$D28/stderr.txt"
rc=$?
set -e
assert_rc "merged snapshot failed rc1" 1 "$rc"
assert_file_kv "$D28/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS snapshot-failed "merged snapshot failed status"
assert_contains "$D28/stdout.txt" 'failed to snapshot plan.txt-original' "merged snapshot failed diagnostic"

D29="$TMP/merged-validate-driver-failed-diagnostic"
setup_design_tmp "$D29" full SIMPLE
reset_env
export VALIDATOR_STUB_RC=8 VALIDATOR_EMIT_STATUS_ON_FAIL=false
set +e
bash "$SUBJECT" --design-tmpdir "$D29" --with-plan-size >"$D29/stdout.txt" 2>"$D29/stderr.txt"
rc=$?
set -e
assert_rc "merged validate driver failed rc1" 1 "$rc"
assert_file_kv "$D29/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS validate-driver-failed "merged validate driver failed status"
assert_contains "$D29/stdout.txt" 'plan-command validator infrastructure failed' "merged validate driver failed diagnostic"

D30="$TMP/drift-baseline-seed"
setup_design_tmp "$D30" full HARD
set +e
run_subject "$D30" --with-plan-size --snapshot-original
rc=$?
set -e
assert_rc "drift baseline seed rc" 0 "$rc"
assert_file_kv "$D30/drift-baseline.env" BASELINE_PLAN_LINES 2 "drift baseline seed plan lines"
assert_file_kv "$D30/drift-baseline.env" BASELINE_DIFF_LINES 12 "drift baseline seed diff lines"

D31="$TMP/drift-baseline-preserved"
setup_design_tmp "$D31" full HARD
printf 'BASELINE_PLAN_LINES=5\nBASELINE_DIFF_LINES=6\n' >"$D31/drift-baseline.env"
set +e
run_subject "$D31" --with-plan-size --snapshot-original
rc=$?
set -e
assert_rc "drift baseline preserved rc" 0 "$rc"
assert_file_kv "$D31/drift-baseline.env" BASELINE_PLAN_LINES 5 "drift baseline preserves plan lines"
assert_file_kv "$D31/drift-baseline.env" BASELINE_DIFF_LINES 6 "drift baseline preserves diff lines"

D32="$TMP/drift-trigger"
setup_design_tmp "$D32" full HARD
printf 'BASELINE_PLAN_LINES=3\nBASELINE_DIFF_LINES=12\n' >"$D32/drift-baseline.env"
{
    printf '# Plan\n'
    fill_plan_lines /dev/stdout 7 b
    printf 'diff_lines: 25\n'
} >"$D32/plan.txt"
set +e
run_subject "$D32" --with-plan-size --snapshot-original
rc=$?
set -e
assert_rc "drift trigger rc" 0 "$rc"
assert_file_kv "$D32/.design-postplan-emit-result.env" PLAN_SIZE_STATUS drift-advisory "drift trigger status"
assert_not_contains "$D32/stdout.txt" '## Plan Size — Drift' "drift trigger no section"
assert_contains "$D32/execution-issues.md" 'drift advisory' "drift trigger warning logged"

D33="$TMP/drift-hard-precedence"
setup_design_tmp "$D33" full HARD
printf 'BASELINE_PLAN_LINES=3\nBASELINE_DIFF_LINES=12\n' >"$D33/drift-baseline.env"
{
    printf '# Plan\n'
    fill_plan_lines /dev/stdout 801 b
    printf 'diff_lines: 25\n'
} >"$D33/plan.txt"
set +e
run_subject "$D33" --with-plan-size --snapshot-original
rc=$?
set -e
assert_rc "drift hard precedence rc" 12 "$rc"
assert_file_kv "$D33/.design-postplan-emit-result.env" PLAN_SIZE_STATUS hard-trigger "drift hard precedence status"
assert_not_contains "$D33/stdout.txt" '## Plan Size — Drift' "drift hard precedence no drift section"

D34="$TMP/drift-partition-precedence"
setup_design_tmp "$D34" full SIMPLE
printf '{"review_budget":"full","workflow_path":"SIMPLE","design_classification":"SIMPLE","partition_requested":true}\n' >"$D34/run-params.json"
printf 'BASELINE_PLAN_LINES=3\nBASELINE_DIFF_LINES=12\n' >"$D34/drift-baseline.env"
{
    printf '# Plan\n'
    fill_plan_lines /dev/stdout 7 b
    printf 'diff_lines: 25\n'
} >"$D34/plan.txt"
set +e
run_subject "$D34" --with-plan-size --snapshot-original
rc=$?
set -e
assert_rc "drift partition precedence rc" 13 "$rc"
assert_file_kv "$D34/.design-postplan-emit-result.env" PLAN_SIZE_STATUS partition-requested "drift partition precedence status"
assert_not_contains "$D34/stdout.txt" '## Plan Size — Drift' "drift partition precedence no drift section"

D35="$TMP/defects-seed-drift-baseline"
setup_design_tmp "$D35" full HARD
reset_env
export VALIDATE_STATUS_VALUE=defects-found VALIDATE_DEFECT_COUNT_VALUE=2
set +e
bash "$SUBJECT" --design-tmpdir "$D35" --with-plan-size --snapshot-original >"$D35/stdout.txt" 2>"$D35/stderr.txt"
rc=$?
set -e
assert_rc "defects seed drift baseline rc" 10 "$rc"
assert_file_kv "$D35/drift-baseline.env" BASELINE_PLAN_LINES 2 "defects seed drift baseline plan"
assert_file_kv "$D35/drift-baseline.env" BASELINE_DIFF_LINES 12 "defects seed drift baseline diff"

D36="$TMP/defects-drift-trigger"
setup_design_tmp "$D36" full HARD
printf 'BASELINE_PLAN_LINES=3\nBASELINE_DIFF_LINES=12\n' >"$D36/drift-baseline.env"
{
    printf '# Plan\n'
    fill_plan_lines /dev/stdout 7 b
    printf 'diff_lines: 25\n'
} >"$D36/plan.txt"
reset_env
export VALIDATE_STATUS_VALUE=defects-found VALIDATE_DEFECT_COUNT_VALUE=2
set +e
bash "$SUBJECT" --design-tmpdir "$D36" --with-plan-size >"$D36/stdout.txt" 2>"$D36/stderr.txt"
rc=$?
set -e
assert_rc "defects drift trigger rc" 10 "$rc"
assert_file_kv "$D36/.design-postplan-emit-result.env" PLAN_SIZE_STATUS skipped-defects "defects win over drift trigger status"
assert_not_contains "$D36/stdout.txt" '## Plan Size — Drift' "defects win over drift trigger section"

if [[ "$FAIL" -ne 0 ]]; then
    printf 'FAIL: test-design-postplan-emit.sh (%s failed, %s passed)\n' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: test-design-postplan-emit.sh (%s checks)\n' "$PASS"
