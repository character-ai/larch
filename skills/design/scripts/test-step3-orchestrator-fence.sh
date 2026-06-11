#!/usr/bin/env bash
# test-step3-orchestrator-fence.sh - Hermetic harness for SKILL.md Step 3 driver handoff fence.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"

apply_gate_b_bypass_sentinels() {
    local design_tmpdir="$1"
    local _repo_root="$REPO_ROOT"
    SESSION_ENV_PATH="" CLAUDE_PID="test" DESIGN_TMPDIR="$design_tmpdir" ISSUE_NUMBER=1 \
      "$_repo_root/skills/design/scripts/design-step3-gate-b-bypass.sh" \
      --session-env-path /dev/null >/dev/null
}
export -f apply_gate_b_bypass_sentinels

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
    return 0
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-step3-orchestrator-fence.XXXXXX")"
TMP="$(cd "$TMP" && pwd -P)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

pass() {
    printf '  ok: %s\n' "$1"
    PASS=$((PASS + 1))
}

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    FAIL=$((FAIL + 1))
}

# Mirrors skills/design/SKILL.md Step 3 thin-fence (run-step3-review.sh --mode loop handoff).
# Display pass; shared read-result-env safe load; narrow stdout overlay for loop envelope keys.
apply_step3_display_pass() {
    local plan_review_out="$1"
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _key="${_line%%=*}"
        case "$_key" in
            LOOP_STATUS|STEP3_REVIEW_LOOP_STATUS|TALLY_PLAN_REVIEW_STATUS|STEP3_REVIEW_CAP_REACHED|STEP3_REVIEW_ROUND_NUM|ROUND_NUM|ACCEPTED_COUNT|IMPORTANT_ACCEPTED_COUNT|DEGRADED_PANEL|ROUNDS_COMPLETED|AGGREGATOR_STATUS|VOTING_TALLY_FILE|REVIEW_ROUND_COUNT|SCOPE_ANCHOR_FILE|POSTPLAN_RC|DEDUP_RC|PLAN_REVIEW_CONTINUE_REASON|FINAL_ROUND_NUM|WARN)
                : ;;
            *)
                printf '%s\n' "$_line" ;;
        esac
    done <<<"${plan_review_out:-}"
}

apply_step3_handoff() {
    local design_tmpdir="$1" plan_review_out="$2" plan_review_rc="$3"
    unset -v LOOP_STATUS STEP3_REVIEW_LOOP_STATUS ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED \
        TALLY_PLAN_REVIEW_STATUS AGGREGATOR_STATUS VOTING_TALLY_FILE STEP3_REVIEW_CAP_REACHED \
        STEP3_REVIEW_ROUND_NUM ROUND_NUM REVIEW_ROUND_COUNT SCOPE_ANCHOR_FILE POSTPLAN_RC DEDUP_RC PLAN_REVIEW_CONTINUE_REASON FINAL_ROUND_NUM

    if [[ "${DISPLAY_ONLY:-}" == 1 ]]; then
        apply_step3_display_pass "${plan_review_out:-}"
        return 0
    fi

    apply_step3_display_pass "${plan_review_out:-}"

    local result_env_body="" wrapper_out _handoff_rc=0
    if [[ -f "$design_tmpdir/.step3-review-result.env" && ! -L "$design_tmpdir/.step3-review-result.env" ]]; then
        result_env_body=$(cat "$design_tmpdir/.step3-review-result.env")
    fi
    set +e
    wrapper_out=$(invoke_step3_review_wrapper "$design_tmpdir" "$result_env_body" "${plan_review_out:-}" "$plan_review_rc")
    _handoff_rc=$?
    set -e
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _key="${_line%%=*}"
        _value="${_line#*=}"
        case "$_key" in
            LOOP_STATUS|STEP3_REVIEW_LOOP_STATUS|ACCEPTED_COUNT|IMPORTANT_ACCEPTED_COUNT|DEGRADED_PANEL|ROUNDS_COMPLETED| \
            TALLY_PLAN_REVIEW_STATUS|AGGREGATOR_STATUS|VOTING_TALLY_FILE|STEP3_REVIEW_CAP_REACHED|STEP3_REVIEW_ROUND_NUM| \
            ROUND_NUM|REVIEW_ROUND_COUNT|SCOPE_ANCHOR_FILE|POSTPLAN_RC|DEDUP_RC|PLAN_REVIEW_CONTINUE_REASON|FINAL_ROUND_NUM)
                [[ -n "$_value" ]] && printf -v "$_key" '%s' "$_value"
                ;;
            WARN)
                printf '%s\n' "$_line"
                ;;
        esac
    done <<<"${wrapper_out:-}"
    if [[ "${plan_review_rc:-0}" -eq 2 ]]; then
        return 2
    fi
    return 0
}

echo "=== design-step3-review.sh contract pins ==="
STEP3_REVIEW_SH="$REPO_ROOT/skills/design/scripts/design-step3-review.sh"
grep -Fq 'STEP3_REVIEW_LOOP_STATUS=' "$STEP3_REVIEW_SH" \
  || fail 'design-step3-review.sh missing STEP3_REVIEW_LOOP_STATUS emit'
grep -Fq 'LOOP_STATUS=' "$STEP3_REVIEW_SH" \
  || fail 'design-step3-review.sh missing LOOP_STATUS emit'
grep -Fq 'read-result-env.sh' "$STEP3_REVIEW_SH" \
  || fail 'design-step3-review.sh missing read-result-env handoff'
pass 'design-step3-review.sh handoff contract present'

invoke_step3_review_wrapper() {
    local design_tmpdir="$1" result_env_body="$2" stdout_body="$3" review_rc="${4:-0}"
    local plugin stub session_env
    plugin="$design_tmpdir/plugin"
    stub="$plugin/skills/design/scripts"
    session_env="$design_tmpdir/session-env.sh"
    mkdir -p "$stub" "$design_tmpdir/.completed"
    printf 'export DESIGN_TMPDIR=%q\nexport CLAUDE_PLUGIN_ROOT=%q\nexport ISSUE_NUMBER=1\n' \
      "$design_tmpdir" "$plugin" >"$session_env"
    printf '%s\n' "$result_env_body" >"$design_tmpdir/.step3-review-result.env"
    cat >"$stub/run-step3-review.sh" <<STUB
#!/usr/bin/env bash
cat <<'OUT'
${stdout_body}
OUT
exit ${review_rc}
STUB
    chmod +x "$stub/run-step3-review.sh"
    mkdir -p "$plugin/scripts"
    cp "$REPO_ROOT/scripts/read-result-env.sh" "$plugin/scripts/read-result-env.sh"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"
    cp "$REPO_ROOT/skills/design/scripts/lib-phase-driver.sh" "$stub/lib-phase-driver.sh"
    CLAUDE_PLUGIN_ROOT="$plugin" \
      "$REPO_ROOT/skills/design/scripts/design-step3-review.sh" \
      --session-env-path "$session_env" \
      --claude-pid test
}

echo "=== design-step3-review.sh wrapper sources result env ==="
D_WRAPPER="$TMP/wrapper-rc0"
mkdir -p "$D_WRAPPER"
_wrapper_out=$(invoke_step3_review_wrapper "$D_WRAPPER" $'LOOP_STATUS=complete\nTALLY_PLAN_REVIEW_STATUS=ok\nSCOPE_ANCHOR_FILE=/tmp/scope.txt\nREVIEW_ROUND_COUNT=1\n' 'LOOP_STATUS=panel-failed' 0)
if printf '%s\n' "$_wrapper_out" | grep -Fq 'LOOP_STATUS=complete' \
  && printf '%s\n' "$_wrapper_out" | grep -Fq 'TALLY_PLAN_REVIEW_STATUS=ok' \
  && printf '%s\n' "$_wrapper_out" | grep -Fq 'SCOPE_ANCHOR_FILE=/tmp/scope.txt'; then
    pass 'wrapper emits file-first handoff KVs'
else
    fail "wrapper handoff missing expected KVs: $_wrapper_out"
fi

echo "=== design-step3-review.sh wrapper postplan-failed exits 1 ==="
D_WRAPPER_FAIL="$TMP/wrapper-postplan-failed"
mkdir -p "$D_WRAPPER_FAIL"
set +e
_wrapper_fail_rc=0
_wrapper_fail_out=$(invoke_step3_review_wrapper "$D_WRAPPER_FAIL" '' $'STEP3_REVIEW_LOOP_STATUS=postplan-failed\nPOSTPLAN_RC=1\n' 0) || _wrapper_fail_rc=$?
set -e
if [[ "$_wrapper_fail_rc" -eq 1 ]] \
  && printf '%s\n' "$_wrapper_fail_out" | grep -Fq 'STEP3_REVIEW_LOOP_STATUS=postplan-failed' \
  && printf '%s\n' "$_wrapper_fail_out" | grep -Fq 'POSTPLAN_RC=1'; then
    pass 'wrapper postplan-failed exit and emit'
else
    fail "wrapper postplan-failed expected exit 1 with KVs (rc=$_wrapper_fail_rc)"
fi

echo "=== rc=0 sources result env via wrapper ==="
D1="$TMP/rc0-file"
mkdir -p "$D1"
_wrapper_rc0_out=$(invoke_step3_review_wrapper "$D1" $'LOOP_STATUS=complete\nTALLY_PLAN_REVIEW_STATUS=ok\nREVIEW_ROUND_COUNT=1\n' 'LOOP_STATUS=panel-failed' 0)
if printf '%s\n' "$_wrapper_rc0_out" | grep -Fq 'LOOP_STATUS=complete'; then
    pass 'rc=0 file-first LOOP_STATUS via wrapper'
else
    fail "rc=0 wrapper expected complete got $_wrapper_rc0_out"
fi

echo "=== rc=1 still sources non-symlink result env ==="
D2="$TMP/rc1-file"
mkdir -p "$D2"
cat >"$D2/.step3-review-result.env" <<'EOF'
LOOP_STATUS=panel-failed
TALLY_PLAN_REVIEW_STATUS=panel-failed
STEP3_REVIEW_CAP_REACHED=false
STEP3_REVIEW_ROUND_NUM=1
ROUND_NUM=1
ACCEPTED_COUNT=
IMPORTANT_ACCEPTED_COUNT=
DEGRADED_PANEL=
ROUNDS_COMPLETED=
AGGREGATOR_STATUS=
VOTING_TALLY_FILE=
REVIEW_ROUND_COUNT=0
EOF
apply_step3_handoff "$D2" '' 1
if [[ "${LOOP_STATUS:-}" == panel-failed && "${REVIEW_ROUND_COUNT:-}" == 0 ]]; then
    pass 'rc=1 file handoff'
else
    fail 'rc=1 should load panel-failed from result env'
fi

echo "=== symlinked result env falls back to stdout ==="
D3="$TMP/symlink"
mkdir -p "$D3"
ln -sf "$D3/target.env" "$D3/.step3-review-result.env"
apply_step3_handoff "$D3" $'LOOP_STATUS=revision-failed\nREVIEW_ROUND_COUNT=2\n' 0
if [[ "${LOOP_STATUS:-}" == panel-failed && "${REVIEW_ROUND_COUNT:-}" == 2 ]]; then
    pass 'symlink fallback normalizes removed stdout status'
else
    fail 'symlink should normalize removed stdout LOOP_STATUS'
fi

echo "=== missing file and stdout uses panel-failed default ==="
D4="$TMP/missing"
mkdir -p "$D4"
apply_step3_handoff "$D4" '' 0
if [[ "${LOOP_STATUS:-}" == panel-failed ]]; then
    pass 'missing LOOP_STATUS defaults panel-failed'
else
    fail "missing file expected panel-failed got ${LOOP_STATUS:-}"
fi

echo "=== stdout overlay is narrow after file ==="
D5="$TMP/merge"
mkdir -p "$D5"
printf 'LOOP_STATUS=complete\nREVIEW_ROUND_COUNT=1\n' >"$D5/.step3-review-result.env"
apply_step3_handoff "$D5" 'LOOP_STATUS=panel-failed
REVIEW_ROUND_COUNT=9
ROUND_NUM=2
' 0
if [[ "${LOOP_STATUS:-}" == complete && "${REVIEW_ROUND_COUNT:-}" == 1 && -z "${ROUND_NUM:-}" ]]; then
    pass 'stdout overlay ignores non-envelope keys when file is primary'
else
    fail "narrow overlay expected complete/1/<empty> got ${LOOP_STATUS:-}/${REVIEW_ROUND_COUNT:-}/${ROUND_NUM:-}"
fi

echo "=== no-safe-env rc!=0 stdout overrides (symlink file) ==="
D6="$TMP/rc1-nosafe-override"
mkdir -p "$D6"
ln -sf "$D6/target.env" "$D6/.step3-review-result.env"
apply_step3_handoff "$D6" 'LOOP_STATUS=panel-failed
REVIEW_ROUND_COUNT=0
' 1
if [[ "${LOOP_STATUS:-}" == panel-failed ]]; then
    pass 'no-safe-env rc!=0 stdout LOOP_STATUS wins (symlink)'
else
    fail "no-safe-env rc!=0 expected panel-failed got ${LOOP_STATUS:-}"
fi

echo "=== safe-env rc!=0 file wins over stdout LOOP_STATUS ==="
D6B="$TMP/safe-env-rc1-file-wins"
mkdir -p "$D6B"
printf 'LOOP_STATUS=complete\nREVIEW_ROUND_COUNT=3\n' >"$D6B/.step3-review-result.env"
apply_step3_handoff "$D6B" 'LOOP_STATUS=panel-failed
REVIEW_ROUND_COUNT=0
' 1
if [[ "${LOOP_STATUS:-}" == complete && "${REVIEW_ROUND_COUNT:-}" == 3 ]]; then
    pass 'safe-env rc!=0 file LOOP_STATUS wins over stdout'
else
    fail "safe-env rc!=0 expected complete/3 got ${LOOP_STATUS:-}/${REVIEW_ROUND_COUNT:-}"
fi

echo "=== safe-env rc=2 returns 2 after shared reader ==="
D6C="$TMP/safe-env-rc2"
mkdir -p "$D6C"
printf 'LOOP_STATUS=complete\n' >"$D6C/.step3-review-result.env"
set +e
_apply_rc=0
apply_step3_handoff "$D6C" 'LOOP_STATUS=complete' 2 || _apply_rc=$?
set -e
if [[ "$_apply_rc" -eq 2 ]]; then
    pass 'safe-env rc=2 returns 2'
else
    fail "safe-env rc=2 expected exit 2 got $_apply_rc"
fi

echo "=== invalid LOOP_STATUS normalizes to panel-failed ==="
D7="$TMP/invalid-loop"
mkdir -p "$D7"
printf 'LOOP_STATUS=cap_reached\n' >"$D7/.step3-review-result.env"
apply_step3_handoff "$D7" '' 0
if [[ "${LOOP_STATUS:-}" == panel-failed ]]; then
    pass 'invalid LOOP_STATUS normalized'
else
    fail "invalid LOOP_STATUS expected panel-failed got ${LOOP_STATUS:-}"
fi

echo "=== rc=2 configuration error short-circuit ==="
D8="$TMP/rc2"
mkdir -p "$D8"
printf 'LOOP_STATUS=complete\n' >"$D8/.step3-review-result.env"
set +e
_apply_rc=0
apply_step3_handoff "$D8" 'LOOP_STATUS=complete' 2 || _apply_rc=$?
set -e
if [[ "$_apply_rc" -eq 2 ]]; then
    pass 'rc=2 returns 2'
else
    fail "rc=2 expected exit 2 got $_apply_rc"
fi

echo "=== WARN= suppressed in display pass, replayed once in parse ==="
D_WARN="$TMP/warn-dedup"
mkdir -p "$D_WARN"
_disp_only=$(DISPLAY_ONLY=1 apply_step3_handoff "$D_WARN" $'WARN=some-warning\nLOOP_STATUS=complete\n' 0)
if printf '%s\n' "$_disp_only" | command grep -Fq 'WARN='; then
    fail 'WARN= should be suppressed from display pass output'
else
    pass 'WARN= suppressed in display pass'
fi
if printf '%s\n' "$_disp_only" | command grep -Fq 'LOOP_STATUS='; then
    fail 'LOOP_STATUS= should be suppressed from display pass output'
else
    pass 'LOOP_STATUS= suppressed from display pass'
fi
_warn_handoff_out=$(apply_step3_handoff "$D_WARN" $'WARN=some-warning\nLOOP_STATUS=complete\n' 0; printf 'LOOP_STATUS_END=%s\n' "${LOOP_STATUS:-}")
_warn_count=$(printf '%s\n' "$_warn_handoff_out" | command grep -c '^WARN=' || true)
if [[ "$_warn_count" -eq 1 ]]; then
    pass 'WARN= replayed exactly once in parse pass'
else
    fail "WARN= should appear exactly once in full handoff output; got $_warn_count"
fi
if printf '%s\n' "$_warn_handoff_out" | command grep -Fq 'WARN=some-warning'; then
    pass 'WARN=some-warning value preserved in parse replay'
else
    fail 'WARN=some-warning missing from parse replay output'
fi

echo "=== non-KV breadcrumb printed in display pass ==="
D_DISP="$TMP/display-pass"
mkdir -p "$D_DISP"
_disp2_out=$(apply_step3_handoff "$D_DISP" $'**⚠ cap-reached breadcrumb**\nLOOP_STATUS=cap-reached\n' 0; printf 'LOOP_STATUS_END=%s\n' "${LOOP_STATUS:-}")
if printf '%s\n' "$_disp2_out" | command grep -Fq '**⚠ cap-reached breadcrumb**'; then
    pass 'non-KV breadcrumb printed in display pass'
else
    fail 'non-KV breadcrumb should appear in display pass'
fi

echo "=== SCOPE_ANCHOR_FILE survives file-first handoff ==="
D_SCOPE="$TMP/scope-anchor-handoff"
mkdir -p "$D_SCOPE"
printf 'anchor body\n' >"$D_SCOPE/plan-review-scope-anchor.txt"
printf 'LOOP_STATUS=complete\nSCOPE_ANCHOR_FILE=%s/plan-review-scope-anchor.txt\n' "$D_SCOPE" >"$D_SCOPE/.step3-review-result.env"
apply_step3_handoff "$D_SCOPE" 'SCOPE_ANCHOR_FILE=/tmp/should-not-win.txt' 0
if [[ "${SCOPE_ANCHOR_FILE:-}" == "$D_SCOPE/plan-review-scope-anchor.txt" ]]; then
    pass 'SCOPE_ANCHOR_FILE file-first handoff'
else
    fail "SCOPE_ANCHOR_FILE expected $D_SCOPE/plan-review-scope-anchor.txt got ${SCOPE_ANCHOR_FILE:-}"
fi

echo "=== scope-anchor re-tally prose pins ==="
SKILL_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)/SKILL.md"
APPROVAL_GATES_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)/references/approval-gates.md"
# shellcheck disable=SC2016 # Literal documentation probe contains backticks and shell syntax.
if command grep -Fq 'preserve `SCOPE_ANCHOR_FILE` from the Step 3 result state as `_RETALLY_SCOPE_ANCHOR_IN="$SCOPE_ANCHOR_FILE"`' "$SKILL_FILE"; then
    pass 'SKILL pins re-tally input/output separation'
else
    fail 'SKILL missing re-tally input/output separation prose'
fi
# shellcheck disable=SC2016 # Literal documentation probe contains backticks.
if command grep -Fq 'without `--scope-anchor-file`' "$SKILL_FILE"; then
    pass 'SKILL pins no re-tally scope-anchor argv'
else
    fail 'SKILL missing no re-tally scope-anchor argv prose'
fi
# shellcheck disable=SC2016 # Literal documentation probe contains backticks.
if command grep -Fq 'fall back to `_RETALLY_SCOPE_ANCHOR_IN` if non-empty and CR/LF-clean' "$SKILL_FILE"; then
    pass 'SKILL pins re-tally ok fallback'
else
    fail 'SKILL missing re-tally ok fallback prose'
fi
# shellcheck disable=SC2016 # Literal documentation probe contains backticks and shell syntax.
if command grep -Fq 'bind `_RETALLY_SCOPE_ANCHOR_IN="$SCOPE_ANCHOR_FILE"` before launch, unset `_RETALLY_PARSED_SCOPE_ANCHOR_FILE` before parsing stdout' "$APPROVAL_GATES_FILE"; then
    pass 'approval gates mirror re-tally input/output separation'
else
    fail 'approval gates missing re-tally input/output separation'
fi
# shellcheck disable=SC2016 # Literal documentation probe contains backticks.
if command grep -Fq 'Do not persist stale exported `SCOPE_ANCHOR_FILE` on `tally-error`.' "$SKILL_FILE"; then
    pass 'SKILL pins stale scope anchor error omission'
else
    fail 'SKILL missing stale scope anchor error omission prose'
fi
# shellcheck disable=SC2016 # Literal documentation probe contains backticks.
if command grep -Fq 'Raw tally stdout `SCOPE_ANCHOR_FILE=` lines are stripped before relay' "$APPROVAL_GATES_FILE" "$SKILL_FILE" "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)/references/plan-review.md" >/dev/null; then
    pass 'scope anchor raw tally strip documented'
else
    fail 'missing raw tally strip documentation'
fi

echo "=== later-KV-wins with no safe env ==="
D_LATER="$TMP/later-kv-wins"
mkdir -p "$D_LATER"
_wrapper_later_out=$(invoke_step3_review_wrapper "$D_LATER" '' $'LOOP_STATUS=panel-failed\nLOOP_STATUS=complete\n' 0)
if printf '%s\n' "$_wrapper_later_out" | grep -Fq 'LOOP_STATUS=panel-failed'; then
    pass 'wrapper stdout-only handoff preserves first LOOP_STATUS when no safe env'
else
    fail "wrapper stdout-only expected panel-failed got $_wrapper_later_out"
fi

echo "=== loop envelope STEP3_REVIEW_LOOP_STATUS wins over stale LOOP_STATUS ==="
D_LOOP="$TMP/loop-envelope"
mkdir -p "$D_LOOP"
printf 'LOOP_STATUS=complete\nSTEP3_REVIEW_LOOP_STATUS=main-agent-apply-required\nFINAL_ROUND_NUM=1\n' >"$D_LOOP/.step3-review-result.env"
apply_step3_handoff "$D_LOOP" 'STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required
DEDUP_RC=2
FINAL_ROUND_NUM=1
' 0
if [[ "${STEP3_REVIEW_LOOP_STATUS:-}" == main-agent-apply-required && "${DEDUP_RC:-}" == 2 ]]; then
    pass 'loop envelope parsed from stdout'
else
    fail "loop envelope expected main-agent-apply-required/2 got ${STEP3_REVIEW_LOOP_STATUS:-}/${DEDUP_RC:-}"
fi

echo "=== invalid STEP3_REVIEW_LOOP_STATUS normalizes to panel-failed ==="
D_LOOP_BAD="$TMP/loop-invalid"
mkdir -p "$D_LOOP_BAD"
apply_step3_handoff "$D_LOOP_BAD" 'STEP3_REVIEW_LOOP_STATUS=not-a-status' 0
if [[ "${STEP3_REVIEW_LOOP_STATUS:-}" == panel-failed ]]; then
    pass 'invalid loop status normalized'
else
    fail "invalid loop status expected panel-failed got ${STEP3_REVIEW_LOOP_STATUS:-}"
fi

echo "=== postplan-failed envelope preserved ==="
D_POST_FAIL="$TMP/postplan-failed"
mkdir -p "$D_POST_FAIL"
apply_step3_handoff "$D_POST_FAIL" $'STEP3_REVIEW_LOOP_STATUS=postplan-failed\nPOSTPLAN_RC=1\n' 0
if [[ "${STEP3_REVIEW_LOOP_STATUS:-}" == postplan-failed && "${POSTPLAN_RC:-}" == 1 && "${LOOP_STATUS:-}" == postplan-failed ]]; then
    pass 'postplan-failed envelope preserved'
else
    fail "postplan-failed envelope missing (STEP3=${STEP3_REVIEW_LOOP_STATUS:-} LOOP=${LOOP_STATUS:-} POSTPLAN_RC=${POSTPLAN_RC:-})"
fi

echo "=== gate B bypass helper writes dual sentinels from empty state ==="
D9="$TMP/gate-b-helper"
mkdir -p "$D9"
if [[ ! -f "$D9/.completed/step-3" && ! -f "$D9/.completed/step-3.5" ]]; then
    pass 'helper precondition starts empty'
else
    fail 'helper precondition should start empty'
fi
if apply_gate_b_bypass_sentinels "$D9" \
    && [[ -f "$D9/.completed/step-3" ]] \
    && [[ -f "$D9/.completed/step-3.5" ]]; then
    pass 'helper writes dual sentinels'
else
    fail 'helper did not write dual sentinels'
fi

echo "=== gate B bypass helper supplements step-3.5 when step-3 exists ==="
D9b="$TMP/gate-b-helper-step3"
mkdir -p "$D9b/.completed"
: >"$D9b/.completed/step-3"
if apply_gate_b_bypass_sentinels "$D9b" \
    && [[ -f "$D9b/.completed/step-3.5" ]]; then
    pass 'helper supplements missing step-3.5 with pre-existing step-3'
else
    fail 'helper did not supplement step-3.5 with pre-existing step-3'
fi

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-step3-orchestrator-fence.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-step3-orchestrator-fence.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
