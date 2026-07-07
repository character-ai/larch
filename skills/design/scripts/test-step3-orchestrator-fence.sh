#!/usr/bin/env bash
# test-step3-orchestrator-fence.sh - Hermetic harness for SKILL.md Step 3 driver handoff fence.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"

apply_gate_b_bypass_sentinels() {
    local design_tmpdir="$1"
    local _repo_root="$REPO_ROOT"
    CLAUDE_PLUGIN_ROOT="$_repo_root" SESSION_ENV_PATH="" CLAUDE_PID="test" DESIGN_TMPDIR="$design_tmpdir" ISSUE_NUMBER=1 \
      "$_repo_root/skills/design/scripts/design-step3-gate-b-bypass.sh" \
      --plugin-root "$_repo_root" \
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
# Display pass; Python normalizer owns safe result-env load and stdout overlay.
apply_step3_display_pass() {
    local plan_review_out="$1"
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _key="${_line%%=*}"
        case "$_key" in
            NEXT_ACTION|LOOP_STATUS|STEP3_REVIEW_LOOP_STATUS|TALLY_PLAN_REVIEW_STATUS|STEP3_REVIEW_CAP_REACHED|STEP3_REVIEW_ROUND_NUM|ROUND_NUM|ACCEPTED_COUNT|IMPORTANT_ACCEPTED_COUNT|DEGRADED_PANEL|ROUNDS_COMPLETED|AGGREGATOR_STATUS|VOTING_TALLY_FILE|REVIEW_ROUND_COUNT|SCOPE_ANCHOR_FILE|POSTPLAN_RC|DEDUP_RC|PLAN_REVIEW_CONTINUE_REASON|FINAL_ROUND_NUM|WARN)
                : ;;
            *)
                printf '%s\n' "$_line" ;;
        esac
    done <<<"${plan_review_out:-}"
}

apply_step3_handoff() {
    local design_tmpdir="$1" plan_review_out="$2" plan_review_rc="$3"
    unset -v NEXT_ACTION LOOP_STATUS STEP3_REVIEW_LOOP_STATUS ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED \
        TALLY_PLAN_REVIEW_STATUS AGGREGATOR_STATUS VOTING_TALLY_FILE STEP3_REVIEW_CAP_REACHED \
        STEP3_REVIEW_ROUND_NUM ROUND_NUM REVIEW_ROUND_COUNT SCOPE_ANCHOR_FILE POSTPLAN_RC DEDUP_RC PLAN_REVIEW_CONTINUE_REASON FINAL_ROUND_NUM

    if [[ "${DISPLAY_ONLY:-}" == 1 ]]; then
        apply_step3_display_pass "${plan_review_out:-}"
        return 0
    fi

    apply_step3_display_pass "${plan_review_out:-}"

    local _stdout_file _normalizer_out _normalizer_rc _line _key _value _had_errexit=0
    case $- in *e*) _had_errexit=1 ;; esac
    _stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-step3-handoff-stdout.XXXXXX")"
    printf '%s\n' "${plan_review_out:-}" >"$_stdout_file"
    set +e
    _normalizer_out=$(CLAUDE_PLUGIN_ROOT="$REPO_ROOT" python3 "$REPO_ROOT/python/cli.py" plan-review normalize-status \
      --design-tmpdir "$design_tmpdir" \
      --stdout-file "$_stdout_file" \
      --loop-rc "$plan_review_rc")
    _normalizer_rc=$?
    if [[ "$_had_errexit" -eq 1 ]]; then
        set -e
    else
        set +e
    fi
    rm -f "$_stdout_file"
    printf '%s\n' "$_normalizer_out"
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _key="${_line%%=*}"
        _value="${_line#*=}"
        case "$_key" in
            NEXT_ACTION|LOOP_STATUS|STEP3_REVIEW_LOOP_STATUS|ACCEPTED_COUNT|IMPORTANT_ACCEPTED_COUNT|DEGRADED_PANEL|ROUNDS_COMPLETED|\
            TALLY_PLAN_REVIEW_STATUS|AGGREGATOR_STATUS|VOTING_TALLY_FILE|STEP3_REVIEW_CAP_REACHED|STEP3_REVIEW_ROUND_NUM|\
            ROUND_NUM|REVIEW_ROUND_COUNT|SCOPE_ANCHOR_FILE|POSTPLAN_RC|DEDUP_RC|PLAN_REVIEW_CONTINUE_REASON|FINAL_ROUND_NUM)
                [[ -n "$_value" ]] && printf -v "$_key" '%s' "$_value"
                ;;
        esac
    done <<<"$_normalizer_out"
    return "$_normalizer_rc"
}

echo "=== design-step3-review.sh contract pins ==="
STEP3_REVIEW_SH="$REPO_ROOT/skills/design/scripts/design-step3-review.sh"
grep -Fq 'plan-review normalize-status' "$STEP3_REVIEW_SH" \
  || fail 'design-step3-review.sh missing normalizer handoff'
grep -Fq -- "--starting-round \"\$STARTING_ROUND\"" "$STEP3_REVIEW_SH" \
  || fail 'design-step3-review.sh missing starting-round forwarding'
pass 'design-step3-review.sh handoff contract present'

_write_step3_wrapper_inputs() {
    local dir="$1" starting_round="${2:-}"
    mkdir -p "$dir"
    printf '{"schema_version":3,"partition_requested":false,"brainstorm_requested":false}\n' >"$dir/run-params.json"
    printf '# Plan\n\ndiff_lines: 1\n' >"$dir/plan.txt"
    printf 'scope anchor\n' >"$dir/plan-review-scope-anchor.txt"
    printf 'feature\n' >"$dir/feature-description.txt"
    if [[ -n "$starting_round" && "$starting_round" =~ ^[0-9]+$ ]]; then
        local prev=$((starting_round - 1))
        [[ "$prev" -lt 1 ]] && prev=1
        printf '%s\n' "$prev" >"$dir/review-round-count.txt"
    fi
}

invoke_step3_review_wrapper() {
    local design_tmpdir="$1" result_env_body="$2" stdout_body="$3" review_rc="${4:-0}" starting_round="${5:-}"
    local session_env _result_env _env_content
    session_env="$design_tmpdir/session-env.sh"
    _write_step3_wrapper_inputs "$design_tmpdir" "$starting_round"
    mkdir -p "$design_tmpdir/.completed" "$design_tmpdir/bgjob"
    printf 'export DESIGN_TMPDIR=%q\nexport CLAUDE_PLUGIN_ROOT=%q\nexport ISSUE_NUMBER=1\n' \
      "$design_tmpdir" "$REPO_ROOT" >"$session_env"
    # Simulate bgjob daemon completion: update round count and write result env.
    if [[ -n "$starting_round" ]]; then
        printf '%s\n' "$starting_round" >"$design_tmpdir/review-round-count.txt"
    fi
    _result_env="$design_tmpdir/bgjob/design-step3-review.result.env"
    if [[ -n "$result_env_body" ]]; then
        _env_content="$result_env_body"
    else
        _env_content="$stdout_body"
    fi
    if [[ -n "$_env_content" ]]; then
        printf '%s\nBGJOB_RC=%s\n' "$_env_content" "$review_rc" >"$_result_env"
    else
        printf 'BGJOB_RC=%s\n' "$review_rc" >"$_result_env"
    fi
    # Normalize via --read-result-env (same as post-DONE orchestrator step).
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
      "$REPO_ROOT/skills/design/scripts/design-step3-review.sh" \
      --session-env-path "$session_env" \
      --claude-pid test \
      --read-result-env
}

echo "=== design-step3-review.sh wrapper sources result env ==="
D_WRAPPER="$TMP/wrapper-rc0"
mkdir -p "$D_WRAPPER"
_wrapper_out=$(invoke_step3_review_wrapper "$D_WRAPPER" $'LOOP_STATUS=complete\nTALLY_PLAN_REVIEW_STATUS=ok\nREVIEW_ROUND_COUNT=1\n' 'LOOP_STATUS=panel-failed' 0)
if printf '%s\n' "$_wrapper_out" | grep -Fq 'LOOP_STATUS=complete' \
  && printf '%s\n' "$_wrapper_out" | grep -Fq 'BGJOB_RC=0'; then
    pass 'wrapper emits file-first handoff KVs'
else
    fail "wrapper handoff missing expected KVs: $_wrapper_out"
fi

echo "=== design-step3-review.sh wrapper forwards starting round ==="
D_WRAPPER_START="$TMP/wrapper-starting-round"
mkdir -p "$D_WRAPPER_START"
_wrapper_start_out=$(invoke_step3_review_wrapper "$D_WRAPPER_START" $'LOOP_STATUS=complete\nTALLY_PLAN_REVIEW_STATUS=ok\n' '' 0 2)
if [[ "$(cat "$D_WRAPPER_START/review-round-count.txt" 2>/dev/null || true)" == "2" ]] \
  && printf '%s\n' "$_wrapper_start_out" | grep -Fq 'LOOP_STATUS=complete'; then
    pass 'wrapper forwards --starting-round'
else
    fail "wrapper did not forward --starting-round (out=$_wrapper_start_out count=$(cat "$D_WRAPPER_START/review-round-count.txt" 2>/dev/null || true))"
fi

echo "=== design-step3-review.sh wrapper postplan-failed exits 1 ==="
D_WRAPPER_FAIL="$TMP/wrapper-postplan-failed"
mkdir -p "$D_WRAPPER_FAIL"
set +e
_wrapper_fail_rc=0
_wrapper_fail_out=$(invoke_step3_review_wrapper "$D_WRAPPER_FAIL" '' $'STEP3_REVIEW_LOOP_STATUS=postplan-failed\nPOSTPLAN_RC=1\nLOOP_STATUS=postplan-failed\n' 0) || _wrapper_fail_rc=$?
set -e
if [[ "$_wrapper_fail_rc" -ne 2 ]] \
  && printf '%s\n' "$_wrapper_fail_out" | grep -Eq '^(STEP3_REVIEW_LOOP_STATUS|LOOP_STATUS)='; then
    pass 'wrapper exercises real plan-review launcher path'
else
    fail "wrapper expected real launcher KV output (rc=$_wrapper_fail_rc out=$_wrapper_fail_out)"
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
mkdir -p "$D2/plan-review/round-1"
printf 'reviewer\n' >"$D2/plan-review/round-1/reviewer-output.txt"
cat >"$D2/.step3-review-result.env" <<'EOF'
LOOP_STATUS=panel-failed
TALLY_PLAN_REVIEW_STATUS=panel-failed
STEP3_REVIEW_CAP_REACHED=false
STEP3_REVIEW_ROUND_NUM=1
ROUND_NUM=1
ACCEPTED_COUNT=
IMPORTANT_ACCEPTED_COUNT=
DEGRADED_PANEL=
ROUNDS_COMPLETED=1
AGGREGATOR_STATUS=
VOTING_TALLY_FILE=
REVIEW_ROUND_COUNT=1
EOF
apply_step3_handoff "$D2" '' 1
if [[ "${LOOP_STATUS:-}" == panel-failed && "${REVIEW_ROUND_COUNT:-}" == 1 ]]; then
    pass 'rc=1 file handoff'
else
    fail 'rc=1 should load panel-failed from result env'
fi

echo "=== symlinked result env falls back to stdout ==="
D3="$TMP/symlink"
mkdir -p "$D3/plan-review/round-1"
printf 'reviewer\n' >"$D3/plan-review/round-1/reviewer-output.txt"
ln -sf "$D3/target.env" "$D3/.step3-review-result.env"
apply_step3_handoff "$D3" $'LOOP_STATUS=revision-failed\nREVIEW_ROUND_COUNT=2\n' 0
if [[ "${LOOP_STATUS:-}" == panel-failed && "${REVIEW_ROUND_COUNT:-}" == 2 ]]; then
    pass 'symlink fallback normalizes removed stdout status'
else
    fail 'symlink should normalize removed stdout LOOP_STATUS'
fi

echo "=== missing file and stdout uses panel-init-failed default ==="
D4="$TMP/missing"
mkdir -p "$D4"
set +e
apply_step3_handoff "$D4" '' 0
_missing_rc=$?
set -e
if [[ "$_missing_rc" -eq 1 && "${LOOP_STATUS:-}" == panel-init-failed ]]; then
    pass 'missing LOOP_STATUS defaults panel-init-failed'
else
    fail "missing file expected panel-init-failed rc=1 got rc=$_missing_rc loop=${LOOP_STATUS:-}"
fi

echo "=== stdout overlay allowlist applies after file ==="
D5="$TMP/merge"
mkdir -p "$D5/plan-review/round-1"
printf 'reviewer\n' >"$D5/plan-review/round-1/reviewer-output.txt"
printf 'LOOP_STATUS=complete\nREVIEW_ROUND_COUNT=1\n' >"$D5/.step3-review-result.env"
apply_step3_handoff "$D5" 'LOOP_STATUS=panel-failed
REVIEW_ROUND_COUNT=9
ROUND_NUM=2
' 0
if [[ "${LOOP_STATUS:-}" == panel-failed && "${REVIEW_ROUND_COUNT:-}" == 9 && "${ROUND_NUM:-}" == 2 ]]; then
    pass 'stdout overlay applies allowlisted KVs when file is primary'
else
    fail "overlay expected panel-failed/9/2 got ${LOOP_STATUS:-}/${REVIEW_ROUND_COUNT:-}/${ROUND_NUM:-}"
fi

echo "=== no-safe-env rc!=0 stdout overrides (symlink file) ==="
D6="$TMP/rc1-nosafe-override"
mkdir -p "$D6/plan-review/round-1"
printf 'reviewer\n' >"$D6/plan-review/round-1/reviewer-output.txt"
ln -sf "$D6/target.env" "$D6/.step3-review-result.env"
apply_step3_handoff "$D6" 'LOOP_STATUS=panel-failed
REVIEW_ROUND_COUNT=1
' 1
if [[ "${LOOP_STATUS:-}" == panel-failed ]]; then
    pass 'no-safe-env rc!=0 stdout LOOP_STATUS wins (symlink)'
else
    fail "no-safe-env rc!=0 expected panel-failed got ${LOOP_STATUS:-}"
fi

echo "=== safe-env rc!=0 stdout overlay wins for allowlisted KVs ==="
D6B="$TMP/safe-env-rc1-file-wins"
mkdir -p "$D6B/plan-review/round-1"
printf 'reviewer\n' >"$D6B/plan-review/round-1/reviewer-output.txt"
printf 'LOOP_STATUS=complete\nREVIEW_ROUND_COUNT=3\n' >"$D6B/.step3-review-result.env"
apply_step3_handoff "$D6B" 'LOOP_STATUS=panel-failed
REVIEW_ROUND_COUNT=1
' 1
if [[ "${LOOP_STATUS:-}" == panel-failed && "${REVIEW_ROUND_COUNT:-}" == 1 ]]; then
    pass 'safe-env rc!=0 stdout overlay wins for allowlisted KVs'
else
    fail "safe-env rc!=0 expected panel-failed/1 got ${LOOP_STATUS:-}/${REVIEW_ROUND_COUNT:-}"
fi

echo "=== env-read failure recovers STEP3_REVIEW_LOOP_STATUS from stdout ==="
D6D="$TMP/env-read-failure-loop-envelope"
mkdir -p "$D6D"
ln -sf "$D6D/target.env" "$D6D/.step3-review-result.env"
apply_step3_handoff "$D6D" 'STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required
LOOP_STATUS=main-agent-vote-required
REVIEW_ROUND_COUNT=2
' 0
if [[ "${STEP3_REVIEW_LOOP_STATUS:-}" == main-agent-vote-required && "${LOOP_STATUS:-}" == main-agent-vote-required ]]; then
    pass 'env-read failure recovers loop envelope from stdout overlay'
else
    fail "env-read failure expected main-agent-vote-required got STEP3=${STEP3_REVIEW_LOOP_STATUS:-} LOOP=${LOOP_STATUS:-}"
fi

echo "=== safe-env rc=2 returns 1 after shared reader ==="
D6C="$TMP/safe-env-rc2"
mkdir -p "$D6C"
printf 'LOOP_STATUS=complete\n' >"$D6C/.step3-review-result.env"
set +e
_apply_rc=0
apply_step3_handoff "$D6C" 'LOOP_STATUS=complete' 2 || _apply_rc=$?
set -e
if [[ "$_apply_rc" -eq 1 ]]; then
    pass 'safe-env rc=2 returns 1'
else
    fail "safe-env rc=2 expected exit 1 got $_apply_rc"
fi

echo "=== invalid LOOP_STATUS normalizes to panel-failed ==="
D7="$TMP/invalid-loop"
mkdir -p "$D7/plan-review/round-1"
printf 'reviewer\n' >"$D7/plan-review/round-1/reviewer-output.txt"
printf 'LOOP_STATUS=cap_reached\nREVIEW_ROUND_COUNT=1\n' >"$D7/.step3-review-result.env"
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
if [[ "$_apply_rc" -eq 1 ]]; then
    pass 'rc=2 returns 1'
else
    fail "rc=2 expected exit 1 got $_apply_rc"
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

echo "=== SCOPE_ANCHOR_FILE stdout overlay wins after file handoff ==="
D_SCOPE="$TMP/scope-anchor-handoff"
mkdir -p "$D_SCOPE"
printf 'anchor body\n' >"$D_SCOPE/plan-review-scope-anchor.txt"
printf 'LOOP_STATUS=complete\nSCOPE_ANCHOR_FILE=%s/plan-review-scope-anchor.txt\n' "$D_SCOPE" >"$D_SCOPE/.step3-review-result.env"
apply_step3_handoff "$D_SCOPE" 'SCOPE_ANCHOR_FILE=/tmp/should-not-win.txt' 0
if [[ "${SCOPE_ANCHOR_FILE:-}" == "/tmp/should-not-win.txt" ]]; then
    pass 'SCOPE_ANCHOR_FILE stdout overlay handoff'
else
    fail "SCOPE_ANCHOR_FILE expected /tmp/should-not-win.txt got ${SCOPE_ANCHOR_FILE:-}"
fi

echo "=== MainAgent MAV wrapper prose pins ==="
SKILL_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)/SKILL.md"
PLAN_REVIEW_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)/references/plan-review.md"
APPROVAL_GATES_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)/references/approval-gates.md"
# shellcheck disable=SC2016 # Literal documentation probe contains backticks.
if ( command grep -Fq '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-mav.sh --phase pre' "$SKILL_FILE" ); then
    pass 'SKILL pins MAV pre launcher fence'
else
    fail 'SKILL missing MAV pre launcher fence'
fi
# shellcheck disable=SC2016 # Literal documentation probe contains backticks.
if ( command grep -Fq 'Parse trusted scalars only from the final `DESIGN_STEP3_MAV_KV_BEGIN` / `DESIGN_STEP3_MAV_KV_END` frame.' "$SKILL_FILE" ); then
    pass 'SKILL pins MAV trusted KV frame parsing'
else
    fail 'SKILL missing MAV trusted KV frame parsing'
fi
# shellcheck disable=SC2016 # Literal documentation probe contains backticks.
if ( command grep -Fq '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-mav.sh --phase post' "$SKILL_FILE" ); then
    pass 'SKILL pins MAV post launcher fence'
else
    fail 'SKILL missing MAV post launcher fence'
fi
# shellcheck disable=SC2016 # Literal documentation probe contains backticks.
if ( command grep -Fq 'Abort on any non-zero post exit' "$SKILL_FILE" ); then
    pass 'SKILL pins MAV post non-zero abort'
else
    fail 'SKILL missing MAV post non-zero abort'
fi
# shellcheck disable=SC2016 # Literal documentation probe contains backticks.
if ( command grep -Fq '`TALLY_PLAN_REVIEW_STATUS=tally-error` is handled by post with `NEXT_ACTION=step3b-bypass`; route it through the Gate B bypass helper and Step 3b instead of entering Gate B.' "$PLAN_REVIEW_FILE" ); then
    pass 'plan-review pins MAV tally-error routing'
else
    fail 'plan-review missing MAV tally-error routing'
fi
if ( command grep -Fq '_RETALLY_SCOPE_ANCHOR_IN' "$SKILL_FILE" "$PLAN_REVIEW_FILE" "$APPROVAL_GATES_FILE" ); then
    fail 'MAV prose must not keep prompt-side _RETALLY_SCOPE_ANCHOR_IN binding'
else
    pass 'MAV prose removed prompt-side retally anchor binding'
fi
# shellcheck disable=SC2016 # Literal prose probe.
if ( command grep -Fq 'end_s=$(date +%s)' "$SKILL_FILE" "$PLAN_REVIEW_FILE" ); then
    fail 'MAV prose must not keep prompt-side raw date timing'
else
    pass 'MAV prose removed prompt-side raw date timing'
fi
# shellcheck disable=SC2016 # Literal prose probe.
if ( command grep -Fq 'persist-retally-step3-env.sh --design-tmpdir "$DESIGN_TMPDIR" --retally-stdout-file' "$SKILL_FILE" "$PLAN_REVIEW_FILE" ); then
    fail 'MAV prose must not keep prompt-composed persist-retally argv'
else
    pass 'MAV prose removed prompt-composed persist-retally argv'
fi

echo "=== later-KV-wins with no safe env ==="
D_LATER="$TMP/later-kv-wins"
mkdir -p "$D_LATER"
apply_step3_handoff "$D_LATER" 'LOOP_STATUS=panel-failed
LOOP_STATUS=complete
' 0
if [[ "${LOOP_STATUS:-}" == complete ]]; then
    pass 'stdout fallback uses last LOOP_STATUS when no safe env'
else
    fail "stdout fallback expected complete got ${LOOP_STATUS:-}"
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
if [[ "${NEXT_ACTION:-}" == gate-b ]]; then
    pass 'loop envelope NEXT_ACTION parsed from stdout'
else
    fail "loop envelope expected NEXT_ACTION=gate-b got ${NEXT_ACTION:-}"
fi

echo "=== invalid STEP3_REVIEW_LOOP_STATUS normalizes to panel-failed ==="
D_LOOP_BAD="$TMP/loop-invalid"
mkdir -p "$D_LOOP_BAD/plan-review/round-1"
printf 'reviewer\n' >"$D_LOOP_BAD/plan-review/round-1/reviewer-output.txt"
apply_step3_handoff "$D_LOOP_BAD" 'STEP3_REVIEW_LOOP_STATUS=not-a-status
REVIEW_ROUND_COUNT=1' 0
if [[ "${STEP3_REVIEW_LOOP_STATUS:-}" == panel-failed ]]; then
    pass 'invalid loop status normalized'
else
    fail "invalid loop status expected panel-failed got ${STEP3_REVIEW_LOOP_STATUS:-}"
fi
if [[ "${NEXT_ACTION:-}" == step3b-bypass ]]; then
    pass 'invalid loop status maps NEXT_ACTION to bypass'
else
    fail "invalid loop status expected NEXT_ACTION=step3b-bypass got ${NEXT_ACTION:-}"
fi

echo "=== postplan-failed envelope preserved ==="
D_POST_FAIL="$TMP/postplan-failed"
mkdir -p "$D_POST_FAIL"
cat >"$D_POST_FAIL/.step3-review-result.env" <<'EOF'
STEP3_REVIEW_LOOP_STATUS=postplan-failed
POSTPLAN_RC=1
EOF
set +e
apply_step3_handoff "$D_POST_FAIL" '' 0
_post_fail_rc=$?
set -e
if [[ "$_post_fail_rc" -eq 1 ]] \
  && [[ "${STEP3_REVIEW_LOOP_STATUS:-}" == postplan-failed && "${POSTPLAN_RC:-}" == 1 && "${LOOP_STATUS:-}" == postplan-failed ]]; then
    pass 'postplan-failed envelope preserved'
else
    fail "postplan-failed envelope missing (STEP3=${STEP3_REVIEW_LOOP_STATUS:-} LOOP=${LOOP_STATUS:-} POSTPLAN_RC=${POSTPLAN_RC:-})"
fi
if [[ "${NEXT_ACTION:-}" == "final-summary:failed-postplan" ]]; then
    pass 'postplan-failed NEXT_ACTION parsed'
else
    fail "postplan-failed expected NEXT_ACTION=final-summary:failed-postplan got ${NEXT_ACTION:-}"
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
