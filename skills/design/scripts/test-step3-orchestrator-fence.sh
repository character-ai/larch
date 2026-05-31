#!/usr/bin/env bash
# test-step3-orchestrator-fence.sh - Hermetic harness for SKILL.md Step 3 driver handoff fence.

set -euo pipefail

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

# Mirrors skills/design/SKILL.md Step 3 fence (run-step3-review.sh handoff).
apply_step3_handoff() {
    local design_tmpdir="$1" plan_review_out="$2" plan_review_rc="$3"
    unset -v LOOP_STATUS ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED \
        TALLY_PLAN_REVIEW_STATUS AGGREGATOR_STATUS VOTING_TALLY_FILE STEP3_REVIEW_CAP_REACHED \
        STEP3_REVIEW_ROUND_NUM ROUND_NUM REVIEW_ROUND_COUNT
    if [[ -f "$design_tmpdir/.step3-review-result.env" ]]; then
        if [[ -L "$design_tmpdir/.step3-review-result.env" ]]; then
            :
        else
            while IFS= read -r _line || [[ -n "$_line" ]]; do
                _key="${_line%%=*}"
                _value="${_line#*=}"
                case "$_key" in
                    LOOP_STATUS | ACCEPTED_COUNT | IMPORTANT_ACCEPTED_COUNT | DEGRADED_PANEL | ROUNDS_COMPLETED | TALLY_PLAN_REVIEW_STATUS | AGGREGATOR_STATUS | VOTING_TALLY_FILE | STEP3_REVIEW_CAP_REACHED | STEP3_REVIEW_ROUND_NUM | ROUND_NUM | REVIEW_ROUND_COUNT)
                        printf -v "$_key" '%s' "$_value"
                        ;;
                    WARN) printf '%s\n' "WARN=$_value" ;;
                esac
            done <"$design_tmpdir/.step3-review-result.env"
        fi
    fi
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _key="${_line%%=*}"
        _value="${_line#*=}"
        case "$_key" in
            LOOP_STATUS | TALLY_PLAN_REVIEW_STATUS)
                if [[ "${plan_review_rc:-0}" -ne 0 ]]; then
                    [[ -n "$_value" ]] && printf -v "$_key" '%s' "$_value"
                else
                    [[ -n "${!_key:-}" ]] || printf -v "$_key" '%s' "$_value"
                fi
                ;;
            ACCEPTED_COUNT | IMPORTANT_ACCEPTED_COUNT | DEGRADED_PANEL | ROUNDS_COMPLETED | AGGREGATOR_STATUS | VOTING_TALLY_FILE | STEP3_REVIEW_CAP_REACHED | STEP3_REVIEW_ROUND_NUM | ROUND_NUM | REVIEW_ROUND_COUNT)
                [[ -n "${!_key:-}" ]] || printf -v "$_key" '%s' "$_value"
                ;;
            WARN) printf '%s\n' "WARN=$_value" ;;
        esac
    done <<<"${plan_review_out:-}"
    if [[ "${plan_review_rc:-0}" -eq 2 ]]; then
        return 2
    fi
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

echo "=== rc!=0 stdout overrides stale file LOOP_STATUS ==="
D6="$TMP/rc1-override"
mkdir -p "$D6"
printf 'LOOP_STATUS=converged\nREVIEW_ROUND_COUNT=3\n' >"$D6/.step3-review-result.env"
apply_step3_handoff "$D6" 'LOOP_STATUS=panel-failed
REVIEW_ROUND_COUNT=0
' 1
if [[ "${LOOP_STATUS:-}" == panel-failed && "${REVIEW_ROUND_COUNT:-}" == 3 ]]; then
    pass 'rc!=0 stdout LOOP_STATUS overrides file'
else
    fail "rc!=0 override expected panel-failed/3 got ${LOOP_STATUS:-}/${REVIEW_ROUND_COUNT:-}"
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

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-step3-orchestrator-fence.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-step3-orchestrator-fence.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
