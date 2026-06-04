#!/usr/bin/env bash
# test-step3-orchestrator-fence.sh - Hermetic harness for SKILL.md Step 3 driver handoff fence.

set -euo pipefail

apply_gate_b_bypass_sentinels() {
    local design_tmpdir="$1"
    if [[ -f "$design_tmpdir/.completed/step-3.5" \
        || -f "$design_tmpdir/.completed/step-3.6" ]]; then
        return 1
    fi
    local DESIGN_TMPDIR="$design_tmpdir"
    mkdir -p "$DESIGN_TMPDIR/.completed"
    if [[ -f "$design_tmpdir/.completed/step-3" ]]; then
        : >"$DESIGN_TMPDIR/.completed/step-3.5"
        : >"$DESIGN_TMPDIR/.completed/step-3.6"
        return 0
    fi
    : >"$DESIGN_TMPDIR/.completed/step-3"
    : >"$DESIGN_TMPDIR/.completed/step-3.5"
    : >"$DESIGN_TMPDIR/.completed/step-3.6"
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

# Mirrors skills/design/SKILL.md Step 3 thin-fence (run-step3-review.sh --no-preview handoff).
# rc=2 check first; display pass; safe-env load via -f && ! -L; file-first vs later-wins.
apply_step3_handoff() {
    local design_tmpdir="$1" plan_review_out="$2" plan_review_rc="$3"
    unset -v LOOP_STATUS ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED \
        TALLY_PLAN_REVIEW_STATUS AGGREGATOR_STATUS VOTING_TALLY_FILE STEP3_REVIEW_CAP_REACHED \
        STEP3_REVIEW_ROUND_NUM ROUND_NUM REVIEW_ROUND_COUNT

    # rc=2 first: abort before display pass, safe-env load, parse, or normalization.
    if [[ "${plan_review_rc:-0}" -eq 2 ]]; then
        printf '%s\n' "**⚠ Step 3: run-step3-review.sh configuration error (exit 2); aborting plan review**"
        return 2
    fi

    # Display pass: print verbatim except twelve-key allowlist KEY=value and WARN=.
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _key="${_line%%=*}"
        case "$_key" in
            LOOP_STATUS|TALLY_PLAN_REVIEW_STATUS|STEP3_REVIEW_CAP_REACHED|STEP3_REVIEW_ROUND_NUM|ROUND_NUM|ACCEPTED_COUNT|IMPORTANT_ACCEPTED_COUNT|DEGRADED_PANEL|ROUNDS_COMPLETED|AGGREGATOR_STATUS|VOTING_TALLY_FILE|REVIEW_ROUND_COUNT|WARN)
                : ;;
            *)
                printf '%s\n' "$_line" ;;
        esac
    done <<<"${plan_review_out:-}"

    # Safe-env load: -f && ! -L (no "is a symlink; refusing to source" message).
    _step3_safe_env_loaded=false
    if [[ -f "$design_tmpdir/.step3-review-result.env" && ! -L "$design_tmpdir/.step3-review-result.env" ]]; then
        _step3_safe_env_loaded=true
        while IFS= read -r _line || [[ -n "$_line" ]]; do
            _key="${_line%%=*}"
            _value="${_line#*=}"
            case "$_key" in
                LOOP_STATUS|TALLY_PLAN_REVIEW_STATUS|STEP3_REVIEW_CAP_REACHED|STEP3_REVIEW_ROUND_NUM|ROUND_NUM|ACCEPTED_COUNT|IMPORTANT_ACCEPTED_COUNT|DEGRADED_PANEL|ROUNDS_COMPLETED|AGGREGATOR_STATUS|VOTING_TALLY_FILE|REVIEW_ROUND_COUNT)
                    printf -v "$_key" '%s' "$_value" ;;
                WARN) printf '%s\n' "WARN=$_value" ;;
            esac
        done <"$design_tmpdir/.step3-review-result.env"
    fi

    # Stdout parse: file-first (fill missing) when safe env loaded; later-wins when not.
    # rc!=0 override for LOOP_STATUS/TALLY applies only on the no-safe-env path.
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _key="${_line%%=*}"
        _value="${_line#*=}"
        case "$_key" in
            LOOP_STATUS|TALLY_PLAN_REVIEW_STATUS)
                if [[ "$_step3_safe_env_loaded" == true ]]; then
                    [[ -n "${!_key:-}" ]] || printf -v "$_key" '%s' "$_value"
                elif [[ "${plan_review_rc:-0}" -ne 0 ]]; then
                    [[ -n "$_value" ]] && printf -v "$_key" '%s' "$_value"
                else
                    printf -v "$_key" '%s' "$_value"
                fi
                ;;
            STEP3_REVIEW_CAP_REACHED|STEP3_REVIEW_ROUND_NUM|ROUND_NUM|ACCEPTED_COUNT|IMPORTANT_ACCEPTED_COUNT|DEGRADED_PANEL|ROUNDS_COMPLETED|AGGREGATOR_STATUS|VOTING_TALLY_FILE|REVIEW_ROUND_COUNT)
                if [[ "$_step3_safe_env_loaded" == true ]]; then
                    [[ -n "${!_key:-}" ]] || printf -v "$_key" '%s' "$_value"
                else
                    printf -v "$_key" '%s' "$_value"
                fi
                ;;
            WARN) printf '%s\n' "WARN=$_value" ;;
        esac
    done <<<"${plan_review_out:-}"

    if [[ -z "${LOOP_STATUS:-}" || ! "${LOOP_STATUS}" =~ ^(complete|converged|cap-hit|cap-reached|zero-findings-degraded-panel|revision-failed|tally-error|degraded-empty-collector|plan-size-trigger|plan-validator-defects|emit-plan-failed|optional-trailer-dedup-loss|panel-failed|main-agent-vote-required)$ ]]; then
        LOOP_STATUS=panel-failed
    fi
}

echo "=== rc=0 sources result env ==="
D1="$TMP/rc0-file"
mkdir -p "$D1"
cat >"$D1/.step3-review-result.env" <<'EOF'
LOOP_STATUS=complete
TALLY_PLAN_REVIEW_STATUS=ok
STEP3_REVIEW_CAP_REACHED=false
STEP3_REVIEW_ROUND_NUM=1
ROUND_NUM=1
ACCEPTED_COUNT=0
IMPORTANT_ACCEPTED_COUNT=0
DEGRADED_PANEL=0
ROUNDS_COMPLETED=1
AGGREGATOR_STATUS=ok
VOTING_TALLY_FILE=
REVIEW_ROUND_COUNT=1
EOF
apply_step3_handoff "$D1" 'LOOP_STATUS=panel-failed' 0
if [[ "${LOOP_STATUS:-}" == complete ]]; then
    pass 'rc=0 file-first LOOP_STATUS'
else
    fail "rc=0 expected complete got ${LOOP_STATUS:-}"
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
if [[ "${LOOP_STATUS:-}" == revision-failed && "${REVIEW_ROUND_COUNT:-}" == 2 ]]; then
    pass 'symlink fallback to stdout'
else
    fail 'symlink should fall back to stdout KVs'
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

echo "=== stdout fills only missing keys after file ==="
D5="$TMP/merge"
mkdir -p "$D5"
printf 'LOOP_STATUS=complete\nREVIEW_ROUND_COUNT=1\n' >"$D5/.step3-review-result.env"
apply_step3_handoff "$D5" 'LOOP_STATUS=panel-failed
REVIEW_ROUND_COUNT=9
ROUND_NUM=2
' 0
if [[ "${LOOP_STATUS:-}" == complete && "${REVIEW_ROUND_COUNT:-}" == 1 && "${ROUND_NUM:-}" == 2 ]]; then
    pass 'stdout fills missing keys only'
else
    fail "merge expected complete/1/2 got ${LOOP_STATUS:-}/${REVIEW_ROUND_COUNT:-}/${ROUND_NUM:-}"
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
printf 'LOOP_STATUS=converged\nREVIEW_ROUND_COUNT=3\n' >"$D6B/.step3-review-result.env"
apply_step3_handoff "$D6B" 'LOOP_STATUS=panel-failed
REVIEW_ROUND_COUNT=0
' 1
if [[ "${LOOP_STATUS:-}" == converged && "${REVIEW_ROUND_COUNT:-}" == 3 ]]; then
    pass 'safe-env rc!=0 file LOOP_STATUS wins over stdout'
else
    fail "safe-env rc!=0 expected converged/3 got ${LOOP_STATUS:-}/${REVIEW_ROUND_COUNT:-}"
fi

echo "=== safe-env rc=2 returns 2 before parse (no LOOP_STATUS from file) ==="
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
if [[ -z "${LOOP_STATUS:-}" ]]; then
    pass 'safe-env rc=2 LOOP_STATUS not set (fence aborted before parse)'
else
    fail "safe-env rc=2 should not set LOOP_STATUS; got ${LOOP_STATUS:-}"
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
_disp_out=$(apply_step3_handoff "$D_WARN" $'WARN=some-warning\nLOOP_STATUS=complete\n' 0; printf 'LOOP_STATUS_END=%s\n' "${LOOP_STATUS:-}")
if printf '%s\n' "$_disp_out" | command grep -Fq 'WARN='; then
    fail 'WARN= should be suppressed from display pass output'
else
    pass 'WARN= suppressed in display pass'
fi
if printf '%s\n' "$_disp_out" | command grep -Fq 'LOOP_STATUS='; then
    fail 'LOOP_STATUS= should be suppressed from display pass output'
else
    pass 'LOOP_STATUS= suppressed from display pass'
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

echo "=== later-KV-wins with no safe env ==="
D_LATER="$TMP/later-kv-wins"
mkdir -p "$D_LATER"
apply_step3_handoff "$D_LATER" $'LOOP_STATUS=panel-failed\nLOOP_STATUS=complete\n' 0
if [[ "${LOOP_STATUS:-}" == complete ]]; then
    pass 'later stdout KV wins when no safe env'
else
    fail "later-KV-wins expected complete got ${LOOP_STATUS:-}"
fi

echo "=== gate B bypass helper writes triple sentinels from empty state ==="
D9="$TMP/gate-b-helper"
mkdir -p "$D9"
if [[ ! -f "$D9/.completed/step-3" && ! -f "$D9/.completed/step-3.5" && ! -f "$D9/.completed/step-3.6" ]]; then
    pass 'helper precondition starts empty'
else
    fail 'helper precondition should start empty'
fi
if apply_gate_b_bypass_sentinels "$D9" \
    && [[ -f "$D9/.completed/step-3" ]] \
    && [[ -f "$D9/.completed/step-3.5" ]] \
    && [[ -f "$D9/.completed/step-3.6" ]]; then
    pass 'helper writes triple sentinels'
else
    fail 'helper did not write triple sentinels'
fi

echo "=== gate B bypass helper supplements 3.5/3.6 when step-3 exists ==="
D9b="$TMP/gate-b-helper-step3"
mkdir -p "$D9b/.completed"
: >"$D9b/.completed/step-3"
if apply_gate_b_bypass_sentinels "$D9b" \
    && [[ -f "$D9b/.completed/step-3.5" ]] \
    && [[ -f "$D9b/.completed/step-3.6" ]]; then
    pass 'helper supplements missing 3.5/3.6 with pre-existing step-3'
else
    fail 'helper did not supplement 3.5/3.6 with pre-existing step-3'
fi

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-step3-orchestrator-fence.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-step3-orchestrator-fence.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
