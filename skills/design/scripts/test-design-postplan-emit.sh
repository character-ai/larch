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
mkdir -p "$FAKE_DESIGN" "$FAKE_SCRIPTS"
ln -sf "$REPO_ROOT/scripts/lib-quiet.sh" "$FAKE_SCRIPTS/lib-quiet.sh"
ln -sf "$REPO_ROOT/scripts/read-design-classification.sh" "$FAKE_SCRIPTS/read-design-classification.sh"
ln -sf "$SCRIPT_DIR/lib-phase-driver.sh" "$FAKE_DESIGN/lib-phase-driver.sh"

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
        VALIDATE_UNSAFE_TOKEN_COUNT_VALUE ISSUE_NUMBER || true
}

setup_design_tmp() {
    local d="$1" budget="${2:-full}" workflow="${3:-SIMPLE}"
    mkdir -p "$d"
    printf '# Plan\n\ndiff_lines: 12\n' >"$d/plan.txt"
    printf '{"review_budget":"%s","workflow_path":"%s","design_classification":"%s"}\n' "$budget" "$workflow" "$workflow" >"$d/run-params.json"
    printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$FAKE_PLUGIN" >"$d/session-env.sh"
}

run_subject() {
    local d="$1"
    shift
    reset_env
    bash "$SUBJECT" --design-tmpdir "$d" "$@" >"$d/stdout.txt" 2>"$d/stderr.txt"
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
printf '{"review_budget":"full","workflow_path":"SIMPLE","design_classification":"HARD"}
' >"$D2c/run-params.json"
set +e
run_subject "$D2c" --snapshot-original
rc=$?
set -e
assert_rc "classification HARD snapshot" 0 "$rc"
assert_file_kv "$D2c/.design-postplan-emit-result.env" SNAPSHOT_STATUS taken "classification HARD snapshot taken"

D2d="$TMP/classification-missing"
setup_design_tmp "$D2d" full SIMPLE
printf '{"review_budget":"full","workflow_path":"SIMPLE"}
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

D2e="$TMP/classification-simple-legacy-hard"
setup_design_tmp "$D2e" full HARD
printf '{"review_budget":"full","workflow_path":"HARD","design_classification":"SIMPLE"}
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

# 4 quick skip
D4="$TMP/quick-skip"
setup_design_tmp "$D4" quick SIMPLE
set +e
run_subject "$D4"
rc=$?
set -e
assert_rc "quick skip" 0 "$rc"
assert_file_kv "$D4/.design-postplan-emit-result.env" VALIDATE_STATUS skipped-quick "quick skipped validator"
if grep -Fq validator "$CALL_LOG"; then fail "quick should not call validator"; else pass "quick did not call validator"; fi

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
printf 'export ISSUE_NUMBER=77\n' >"$D11/source-env.sh"
: >"$D11/.pause-requested"
set +e
run_subject "$D11"
rc=$?
set -e
assert_rc "pause checkpoint rc" 0 "$rc"
assert_contains "$CALL_LOG" 'pause-save --design-tmpdir' "pause-save invoked"
assert_contains "$CALL_LOG" '--issue 77' "pause-save issue resolved"
if grep -Fq 'design-driver EMIT' "$CALL_LOG"; then fail "pause should happen before EMIT"; else pass "pause happened before EMIT"; fi
assert_file_kv "$D11/.design-postplan-emit-result.env" POSTPLAN_EMIT_STATUS paused "pause writes paused status to result env"

# 12 quick + force validate runs
D12="$TMP/quick-force"
setup_design_tmp "$D12" quick SIMPLE
set +e
run_subject "$D12" --force-validate
rc=$?
set -e
assert_rc "quick force validate" 0 "$rc"
assert_file_kv "$D12/.design-postplan-emit-result.env" VALIDATE_STATUS ok "quick force validator status"
assert_contains "$CALL_LOG" 'validator' "quick force called validator"

if [[ "$FAIL" -ne 0 ]]; then
    printf 'FAIL: test-design-postplan-emit.sh (%s failed, %s passed)\n' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: test-design-postplan-emit.sh (%s checks)\n' "$PASS"
