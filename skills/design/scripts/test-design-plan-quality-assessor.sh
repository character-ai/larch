#!/usr/bin/env bash
# Offline harness for design-plan-quality-assessor.sh and Step 3.6 orchestrator handoff.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SUBJECT="$SCRIPT_DIR/design-plan-quality-assessor.sh"
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
    local haystack="$1" needle="$2" label="$3"
    if grep -Fq -- "$needle" <<<"$haystack"; then
        pass "$label"
    else
        fail "$label"
    fi
}

assert_stderr_contains() {
    local file="$1" needle="$2" label="$3"
    if grep -Fq -- "$needle" "$file" 2>/dev/null; then
        pass "$label"
    else
        fail "$label"
    fi
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-plan-quality-assessor.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAKE_PLUGIN="$TMP/plugin"
FAKE_DESIGN="$FAKE_PLUGIN/skills/design/scripts"
FAKE_SCRIPTS="$FAKE_PLUGIN/scripts"
mkdir -p "$FAKE_DESIGN" "$FAKE_SCRIPTS"
ln -sf "$REPO_ROOT/scripts/lib-quiet.sh" "$FAKE_SCRIPTS/lib-quiet.sh"
ln -sf "$SCRIPT_DIR/lib-phase-driver.sh" "$FAKE_DESIGN/lib-phase-driver.sh"

cat >"$FAKE_DESIGN/snapshot-plan-round.sh" <<'STUB'
#!/usr/bin/env bash
echo "snapshot $*" >>"${CALL_LOG:?}"
mode=""
design_tmpdir=""
round=""
value=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    read-cursor|write-after|write-cursor) mode="$1"; shift ;;
    --design-tmpdir) design_tmpdir="$2"; shift 2 ;;
    --round) round="$2"; shift 2 ;;
    --value) value="$2"; shift 2 ;;
    *) shift ;;
  esac
done
case "$mode" in
  read-cursor)
    printf 'ROUND_CURSOR=%s\n' "${ROUND_CURSOR_VALUE:-2}"
    exit "${READ_CURSOR_RC:-0}"
    ;;
  write-after)
    if [[ "${WRITE_AFTER_FAIL:-false}" == true ]]; then
      exit 1
    fi
    exit 0
    ;;
  write-cursor)
    printf '%s\n' "${value:-1}" >"${design_tmpdir:?}/plan-review-round-cursor.txt"
    exit "${WRITE_CURSOR_RC:-0}"
    ;;
esac
exit 0
STUB

cat >"$FAKE_DESIGN/assess-plan-round.sh" <<'STUB'
#!/usr/bin/env bash
echo "assess $*" >>"${CALL_LOG:?}"
if [[ "${ASSESS_STUB_SKIP:-false}" == true ]]; then
  exit 99
fi
printf 'ASSESSOR_STATUS=%s\n' "${ASSESSOR_STATUS_VALUE:-ok}"
printf 'ASSESSOR_VERDICT=%s\n' "${ASSESSOR_VERDICT_VALUE:-worse-majority}"
printf 'EFFECTIVE_ASSESSORS=%s\n' "${EFFECTIVE_ASSESSORS_VALUE:-3}"
printf 'ASSESSOR_VERDICT_FILE=%s\n' "${ASSESSOR_VERDICT_FILE_VALUE:-/tmp/v.txt}"
printf 'ASSESSOR_VERDICT_ENV=%s\n' "${ASSESSOR_VERDICT_ENV_VALUE:-/tmp/v.env}"
printf 'ROUND_NUM=%s\n' "${ROUND_NUM_VALUE:-2}"
exit "${ASSESS_STUB_RC:-0}"
STUB

cat >"$FAKE_SCRIPTS/append-tool-failure.sh" <<'STUB'
#!/usr/bin/env bash
echo "append-tool-failure $*" >>"${CALL_LOG:?}"
exit 0
STUB

cat >"$FAKE_SCRIPTS/design-pause-save.sh" <<'STUB'
#!/usr/bin/env bash
echo "pause-save $*" >>"${CALL_LOG:?}"
exit 0
STUB

chmod +x "$FAKE_DESIGN"/*.sh "$FAKE_SCRIPTS"/*.sh
export CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN"
export CALL_LOG="$TMP/call.log"

SNAPSHOT_FAIL_WARN='**⚠ 3.6: failed to snapshot post-Gate-B plan for round 2; rolling back pending review-round state and skipping assessor.**'
ZERO_ASSESSORS_WARN='**⚠ 3.6: 0/3 effective assessors; proceeding without quality gate (round 2, see /tmp/v.env).**'

reset_env() {
    : >"$CALL_LOG"
    unset WRITE_AFTER_FAIL READ_CURSOR_RC WRITE_CURSOR_RC ROUND_CURSOR_VALUE \
        ASSESSOR_STATUS_VALUE ASSESSOR_VERDICT_VALUE EFFECTIVE_ASSESSORS_VALUE \
        ASSESSOR_VERDICT_FILE_VALUE ASSESSOR_VERDICT_ENV_VALUE ROUND_NUM_VALUE \
        ASSESS_STUB_RC ASSESS_STUB_SKIP || true
}

setup_design_tmp() {
    local d="$1" workflow="${2:-SIMPLE}"
    mkdir -p "$d"
    printf '# Plan\n' >"$d/plan.txt"
    printf '{"workflow_path":"%s"}\n' "$workflow" >"$d/run-params.json"
    printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$FAKE_PLUGIN" >"$d/session-env.sh"
    printf '2\n' >"$d/review-round-count.txt"
}

run_subject() {
    local d="$1"
    shift
    export LARCH_SNAPSHOT_PLAN_ROUND_SH="$FAKE_DESIGN/snapshot-plan-round.sh"
    export LARCH_ASSESS_PLAN_ROUND_SH="$FAKE_DESIGN/assess-plan-round.sh"
    bash "$SUBJECT" --design-tmpdir "$d" --codex-present true --cursor-present false "$@" >"$d/stdout.txt" 2>"$d/stderr.txt"
}

apply_step3_6_handoff() {
    local d="$1"
    local wp rc=0
    wp=$(jq -r '.workflow_path // ""' "$d/run-params.json" 2>/dev/null || echo "")
    if [[ -z "$wp" ]]; then
        wp=$(sed -n 's/.*"workflow_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$d/run-params.json" 2>/dev/null | head -1)
    fi
    : >"$d/chat.out"
    : >"$d/handoff.stderr"
    if [[ "$wp" == HARD ]]; then
        printf '%s\n' "> **🔶 /design 3.6: assessor**" >>"$d/chat.out"
    else
        printf '%s\n' "⏩ 3.6: assessor — workflow_path=$wp; skipped" >>"$d/chat.out"
    fi
    set +e
    local _assessor_out _assessor_rc
    export LARCH_SNAPSHOT_PLAN_ROUND_SH="${LARCH_SNAPSHOT_PLAN_ROUND_SH:-$FAKE_DESIGN/snapshot-plan-round.sh}"
    export LARCH_ASSESS_PLAN_ROUND_SH="${LARCH_ASSESS_PLAN_ROUND_SH:-$FAKE_DESIGN/assess-plan-round.sh}"
    _assessor_out=$(bash "$SUBJECT" --design-tmpdir "$d" --codex-present true --cursor-present false 2>>"$d/handoff.stderr")
    _assessor_rc=$?
    printf '%s\n' "${_assessor_out:-}" >"$d/handoff-driver.stdout"
    local ASSESSOR_STATUS="" ASSESSOR_VERDICT="" EFFECTIVE_ASSESSORS=""
    local ASSESSOR_VERDICT_FILE="" ASSESSOR_VERDICT_ENV="" ROUND_NUM="" WORKFLOW_PATH=""
    local _assessor_parse_ok=false
    if [[ -f "$d/.step3.6-assessor.env" ]]; then
        if [[ -L "$d/.step3.6-assessor.env" ]]; then
            printf '%s\n' "**⚠ Step 3.6: refusing symlink .step3.6-assessor.env; using stdout fallback.**" >>"$d/handoff.stderr"
        else
            local _assessor_line _assessor_key _assessor_value
            while IFS= read -r _assessor_line || [[ -n "$_assessor_line" ]]; do
                _assessor_key="${_assessor_line%%=*}"
                _assessor_value="${_assessor_line#*=}"
                case "$_assessor_key" in
                    ASSESSOR_STATUS|ASSESSOR_VERDICT|EFFECTIVE_ASSESSORS|ASSESSOR_VERDICT_FILE|ASSESSOR_VERDICT_ENV|ROUND_NUM|WORKFLOW_PATH)
                        printf -v "$_assessor_key" '%s' "$_assessor_value"
                        _assessor_parse_ok=true
                        ;;
                    WARN)
                        printf '%s\n' "$_assessor_value" >>"$d/chat.out"
                        ;;
                esac
            done <"$d/.step3.6-assessor.env"
        fi
    fi
    local _assessor_line _assessor_key _assessor_value
    while IFS= read -r _assessor_line || [[ -n "$_assessor_line" ]]; do
        _assessor_key="${_assessor_line%%=*}"
        _assessor_value="${_assessor_line#*=}"
        case "$_assessor_key" in
            ASSESSOR_STATUS|ASSESSOR_VERDICT|EFFECTIVE_ASSESSORS|ASSESSOR_VERDICT_FILE|ASSESSOR_VERDICT_ENV|ROUND_NUM|WORKFLOW_PATH)
                if [[ -z "${!_assessor_key:-}" ]]; then
                    printf -v "$_assessor_key" '%s' "$_assessor_value"
                fi
                ;;
            WARN)
                if [[ "$_assessor_parse_ok" != true ]]; then
                    printf '%s\n' "$_assessor_value" >>"$d/chat.out"
                fi
                ;;
        esac
    done <<<"${_assessor_out:-}"
    if [[ "${_assessor_rc:-0}" -eq 2 ]]; then
        printf '%s\n' "**⚠ Step 3.6: design-plan-quality-assessor.sh configuration error (exit 2); aborting /design.**" >>"$d/handoff.stderr"
        return 1
    fi
    if [[ "${_assessor_rc:-0}" -eq 0 && -z "${ASSESSOR_STATUS:-}" ]]; then
        printf '%s\n' "**⚠ Step 3.6: design-plan-quality-assessor.sh result env missing/unreadable and stdout did not populate mandatory keys; aborting /design.**" >>"$d/handoff.stderr"
        return 1
    fi
    if [[ "${_assessor_rc:-0}" -ne 0 && "${_assessor_rc:-0}" -ne 2 ]]; then
        printf '%s\n' "**⚠ Step 3.6: design-plan-quality-assessor.sh failed (exit ${_assessor_rc}); aborting /design.**" >>"$d/handoff.stderr"
        return 1
    fi
    return 0
}

# 1 argv: missing --design-tmpdir
reset_env
set +e
bash "$SUBJECT" --codex-present true --cursor-present false >"$TMP/usage.out" 2>"$TMP/usage.err"
rc=$?
set -e
assert_rc "missing design-tmpdir" 2 "$rc"

# 2 argv: unknown flag
reset_env
D0="$TMP/unknown-flag"
setup_design_tmp "$D0"
set +e
bash "$SUBJECT" --design-tmpdir "$D0" --codex-present true --cursor-present false --bogus >"$D0/stdout.txt" 2>"$D0/stderr.txt"
rc=$?
set -e
assert_rc "unknown flag" 2 "$rc"

# 3 non-HARD skip
reset_env
D1="$TMP/simple-skip"
setup_design_tmp "$D1" SIMPLE
set +e
run_subject "$D1"
rc=$?
set -e
assert_rc "non-HARD skip rc" 0 "$rc"
assert_file_kv "$D1/.step3.6-assessor.env" ASSESSOR_STATUS skipped "non-HARD status"
assert_file_kv "$D1/.step3.6-assessor.env" WORKFLOW_PATH SIMPLE "non-HARD workflow"
if grep -Fq 'assess ' "$CALL_LOG"; then fail "assess stub called on SIMPLE"; else pass "assess not called on SIMPLE"; fi

# 4 HARD happy path
reset_env
D2="$TMP/hard-happy"
setup_design_tmp "$D2" HARD
export ASSESSOR_VERDICT_VALUE=not-worse EFFECTIVE_ASSESSORS_VALUE=2
set +e
run_subject "$D2"
rc=$?
set -e
assert_rc "HARD happy rc" 0 "$rc"
assert_file_kv "$D2/.step3.6-assessor.env" ASSESSOR_STATUS ok "HARD happy status"
assert_file_kv "$D2/.step3.6-assessor.env" ASSESSOR_VERDICT not-worse "HARD happy verdict"
assert_contains "$(cat "$D2/stdout.txt")" 'ASSESSOR_STATUS=ok' "HARD happy stdout KV"

# 5 write-after failure
reset_env
D3="$TMP/write-after-fail"
setup_design_tmp "$D3" HARD
export WRITE_AFTER_FAIL=true ROUND_CURSOR_VALUE=2
set +e
run_subject "$D3"
rc=$?
set -e
assert_rc "write-after fail rc" 0 "$rc"
assert_file_kv "$D3/.step3.6-assessor.env" ASSESSOR_STATUS write-after-failed "write-after status"
count=$(cat "$D3/review-round-count.txt" 2>/dev/null || echo "")
if [[ "$count" == "1" ]]; then pass "rollback count"; else fail "rollback count — expected 1, got $count"; fi
grep -Fq 'append-tool-failure' "$CALL_LOG" && pass "append-tool-failure called" || fail "append-tool-failure not called"
warn_in_env=$(awk -F= '$1=="WARN"{print substr($0,6); exit}' "$D3/.step3.6-assessor.env" || true)
if [[ "$warn_in_env" == "$SNAPSHOT_FAIL_WARN" ]]; then pass "write-after WARN in env"; else fail "write-after WARN in env"; fi

# 6 EFFECTIVE_ASSESSORS=0
reset_env
D4="$TMP/zero-assessors"
setup_design_tmp "$D4" HARD
export ASSESSOR_VERDICT_VALUE=not-worse EFFECTIVE_ASSESSORS_VALUE=0 ASSESSOR_STATUS_VALUE=degraded-default-open
set +e
run_subject "$D4"
rc=$?
set -e
assert_rc "zero assessors rc" 0 "$rc"
grep -Fq '0/3 effective assessors' "$D4/.step3.6-assessor.env" && pass "0/3 WARN in env" || fail "0/3 WARN in env"

# 7 handoff: write-after WARN in chat on file parse
reset_env
D5="$TMP/handoff-write-after"
setup_design_tmp "$D5" HARD
export WRITE_AFTER_FAIL=true ROUND_CURSOR_VALUE=2
set +e
apply_step3_6_handoff "$D5"
handoff_rc=$?
set -e
assert_rc "handoff write-after rc" 0 "$handoff_rc"
assert_contains "$(cat "$D5/chat.out")" "$SNAPSHOT_FAIL_WARN" "handoff chat write-after WARN"

# 8 handoff: 0/3 WARN in chat on file parse
reset_env
D6="$TMP/handoff-zero"
setup_design_tmp "$D6" HARD
export ASSESSOR_VERDICT_VALUE=not-worse EFFECTIVE_ASSESSORS_VALUE=0 ASSESSOR_STATUS_VALUE=degraded-default-open
set +e
apply_step3_6_handoff "$D6"
handoff_rc=$?
set -e
assert_rc "handoff zero assessors rc" 0 "$handoff_rc"
assert_contains "$(cat "$D6/chat.out")" '0/3 effective assessors' "handoff chat 0/3 WARN"

# 9 symlink refusal
reset_env
D7="$TMP/symlink"
setup_design_tmp "$D7" HARD
printf 'ASSESSOR_STATUS=skipped\n' >"$TMP/outside-assessor.env"
ln -sf "$TMP/outside-assessor.env" "$D7/.step3.6-assessor.env"
export ASSESSOR_VERDICT_VALUE=worse-majority
: >"$D7/chat.out"
: >"$D7/handoff.stderr"
set +e
apply_step3_6_handoff "$D7"
handoff_rc=$?
set -e
assert_rc "handoff symlink rc" 0 "$handoff_rc"
assert_stderr_contains "$D7/handoff.stderr" 'refusing symlink .step3.6-assessor.env' "symlink stderr"
if grep -Fq 'ASSESSOR_VERDICT=worse-majority' "$D7/handoff-driver.stdout" 2>/dev/null; then
    pass "symlink stdout fallback KVs"
else
    fail "symlink stdout fallback KVs"
fi

# 10 result-env keys
for key in ASSESSOR_STATUS ASSESSOR_VERDICT EFFECTIVE_ASSESSORS ASSESSOR_VERDICT_FILE ASSESSOR_VERDICT_ENV ROUND_NUM WORKFLOW_PATH; do
    grep -q "^${key}=" "$D2/.step3.6-assessor.env" || fail "missing $key in result env"
done
pass "result-env key presence"

# 11 handoff abort: driver exit 2 via stub wrapper
reset_env
D8="$TMP/handoff-exit2"
setup_design_tmp "$D8" HARD
cat >"$D8/bad-driver.sh" <<'BAD'
#!/usr/bin/env bash
exit 2
BAD
chmod +x "$D8/bad-driver.sh"
set +e
SUBJECT_SAVE=$SUBJECT
SUBJECT="$D8/bad-driver.sh"
apply_step3_6_handoff "$D8"
handoff_rc=$?
SUBJECT=$SUBJECT_SAVE
set -e
assert_rc "handoff exit 2" 1 "$handoff_rc"
assert_stderr_contains "$D8/handoff.stderr" 'configuration error (exit 2)' "handoff config error banner"

# 12 handoff abort: empty mandatory keys
reset_env
D9="$TMP/handoff-empty"
setup_design_tmp "$D9" HARD
cat >"$D9/empty-driver.sh" <<'EMPTY'
#!/usr/bin/env bash
exit 0
EMPTY
chmod +x "$D9/empty-driver.sh"
rm -f "$D9/.step3.6-assessor.env"
set +e
SUBJECT_SAVE=$SUBJECT
SUBJECT="$D9/empty-driver.sh"
apply_step3_6_handoff "$D9"
handoff_rc=$?
SUBJECT=$SUBJECT_SAVE
set -e
assert_rc "handoff empty keys" 1 "$handoff_rc"
assert_stderr_contains "$D9/handoff.stderr" 'did not populate mandatory keys' "handoff mandatory-keys banner"

# 13 driver uses seam bindings (not hardcoded plugin paths in body)
contains_driver() {
    grep -Fq -- "$1" "$SUBJECT" || fail "$2"
}
contains_driver 'LARCH_SNAPSHOT_PLAN_ROUND_SH' 'driver missing SNAPSHOT_SH seam'
contains_driver 'LARCH_ASSESS_PLAN_ROUND_SH' 'driver missing ASSESS_SH seam'
contains_driver '"$SNAPSHOT_SH"' 'driver missing SNAPSHOT_SH usage'
contains_driver '"$ASSESS_SH"' 'driver missing ASSESS_SH usage'
if grep -Fq '$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh' "$SUBJECT" \
    && ! grep -Fq 'LARCH_SNAPSHOT_PLAN_ROUND_SH' "$SUBJECT"; then
    fail 'driver hardcodes snapshot path without seam'
else
    pass 'driver snapshot seam default only'
fi

if [[ "$FAIL" -ne 0 ]]; then
    printf 'FAIL: test-design-plan-quality-assessor.sh (%s failed, %s passed)\n' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: test-design-plan-quality-assessor.sh (%s checks)\n' "$PASS"
