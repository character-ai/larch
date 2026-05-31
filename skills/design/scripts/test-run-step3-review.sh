#!/usr/bin/env bash
# test-run-step3-review.sh - Regression harness for run-step3-review.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
LAUNCHER="$SCRIPT_DIR/run-step3-review.sh"

mkdir -p "${HOME}/.cache/larch/sessions"
TMP="$(mktemp -d "${HOME}/.cache/larch/sessions/test-run-step3-review.XXXXXX")"
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

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing $needle; got ${haystack:0:300})"
    fi
}

assert_file_equals() {
    local file="$1" expected="$2" label="$3"
    local actual
    actual="$(cat "$file")"
    if [[ "$actual" == "$expected" ]]; then
        pass "$label"
    else
        fail "$label"
    fi
}

write_common_inputs() {
    local dir="$1" classification="$2"
    mkdir -p "$dir"
    cat >"$dir/run-params.json" <<EOF
{"schema_version":2,"design_classification":"$classification","workflow_path":"$classification","partition_requested":false,"brainstorm_requested":false}
EOF
    printf '# Plan\n\ndiff_lines: 1\n' >"$dir/plan.txt"
    printf 'feature\n' >"$dir/feature-description.txt"
}

write_loop_stub() {
    local dir="$1" body="$2"
    local stub="$dir/plan-review-loop-stub.sh"
    cat >"$stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
$body
EOF
    chmod +x "$stub"
    printf '%s\n' "$stub"
}

launcher_env=(env -u LARCH_QUIET_LOG_FILE CLAUDE_PLUGIN_ROOT="$REPO_ROOT")

echo "=== missing --design-tmpdir ==="
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" --round-cap 5 --convergence-threshold 3 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass 'missing design-tmpdir exits 2'
else
    fail "missing design-tmpdir rc=$rc"
fi
assert_contains "$out" '--design-tmpdir is required' 'missing design-tmpdir error'

echo "=== cap-reached short-circuit ==="
D1="$TMP/cap"
write_common_inputs "$D1" SIMPLE
printf '3\n' >"$D1/review-round-count.txt"
stub="$(write_loop_stub "$D1" 'exit 97')"
set +e
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D1" --round-cap 5 --convergence-threshold 3)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass 'cap-reached exit 0'
else
    fail "cap-reached rc=$rc"
fi
assert_contains "$out" 'LOOP_STATUS=cap-reached' 'cap-reached KV'
assert_contains "$out" 'TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached' 'skipped-cap-reached KV'
grep -Fq 'LOOP_STATUS=cap-reached' "$D1/.step3-review-result.env" || fail 'result env cap-reached'
[[ "$(cat "$D1/review-round-count.txt")" == "3" ]] || fail 'cap-reached leaves counter unchanged'

echo "=== pending round persisted before launch ==="
D2="$TMP/persist"
write_common_inputs "$D2" SIMPLE
stub="$(write_loop_stub "$D2" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D2" --round-cap 5 --convergence-threshold 3 >/dev/null
if [[ "$(cat "$D2/review-round-count.txt")" == "1" ]]; then
    pass 'pending round persisted'
else
    fail 'pending round not persisted'
fi

echo "=== tally-error rollback ==="
D3="$TMP/tally"
write_common_inputs "$D3" HARD
printf '2\n' >"$D3/review-round-count.txt"
stub="$(write_loop_stub "$D3" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=3\nTALLY_PLAN_REVIEW_STATUS=tally-error\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 2")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D3" --round-cap 5 --convergence-threshold 3 >/dev/null
if [[ "$(cat "$D3/review-round-count.txt")" == "2" ]]; then
    pass 'tally-error rollback'
else
    fail 'tally-error should rollback count'
fi

echo "=== degraded-empty-collector rollback ==="
D4="$TMP/degraded"
write_common_inputs "$D4" SIMPLE
printf '1\n' >"$D4/review-round-count.txt"
stub="$(write_loop_stub "$D4" "printf 'LOOP_STATUS=degraded-empty-collector\nACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=skipped\nVOTING_TALLY_FILE=\n'; exit 0")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D4" --round-cap 5 --convergence-threshold 3 >/dev/null
if [[ "$(cat "$D4/review-round-count.txt")" == "1" ]]; then
    pass 'degraded-empty-collector rollback'
else
    fail 'degraded rollback failed'
fi

echo "=== panel-failed keeps round ==="
D5="$TMP/panel"
write_common_inputs "$D5" SIMPLE
printf '1\n' >"$D5/review-round-count.txt"
stub="$(write_loop_stub "$D5" "printf 'LOOP_STATUS=panel-failed\nACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=panel-failed\nAGGREGATOR_STATUS=skipped\nVOTING_TALLY_FILE=\n'; exit 1")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D5" --round-cap 5 --convergence-threshold 3 >/dev/null
if [[ "$(cat "$D5/review-round-count.txt")" == "2" ]]; then
    pass 'panel-failed keeps round'
else
    fail 'panel-failed should keep pending round'
fi

echo "=== unknown LOOP_STATUS normalizes to panel-failed ==="
D6="$TMP/weird"
write_common_inputs "$D6" SIMPLE
stub="$(write_loop_stub "$D6" "printf 'LOOP_STATUS=weird-status\n'; exit 1")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D6" --round-cap 5 --convergence-threshold 3)"
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'unknown status normalized'

echo "=== normalized result env keys ==="
if grep -Fq 'LOOP_STATUS=' "$D6/.step3-review-result.env"; then
    pass 'result env has LOOP_STATUS'
else
    fail 'result env missing LOOP_STATUS'
fi
if grep -Fq 'REVIEW_ROUND_COUNT=' "$D6/.step3-review-result.env"; then
    pass 'result env has REVIEW_ROUND_COUNT'
else
    fail 'result env missing REVIEW_ROUND_COUNT'
fi

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-run-step3-review.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-run-step3-review.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
