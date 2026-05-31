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

assert_file_has_keys() {
    local file="$1" label="$2"
    shift 2
    local key
    for key in "$@"; do
        if grep -Fq "${key}=" "$file"; then
            pass "$label has $key"
        else
            fail "$label missing $key"
        fi
    done
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

echo "=== missing --round-cap ==="
DARGV="$TMP/argv"
write_common_inputs "$DARGV" SIMPLE
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$DARGV" --convergence-threshold 3 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass 'missing round-cap exits 2'
else
    fail "missing round-cap rc=$rc"
fi
assert_contains "$out" '--round-cap is required' 'missing round-cap error'

echo "=== missing --convergence-threshold ==="
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$DARGV" --round-cap 5 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass 'missing convergence-threshold exits 2'
else
    fail "missing convergence-threshold rc=$rc"
fi
assert_contains "$out" '--convergence-threshold is required' 'missing convergence-threshold error'

echo "=== unknown option ==="
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$DARGV" --round-cap 5 --convergence-threshold 3 --bogus 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass 'unknown option exits 2'
else
    fail "unknown option rc=$rc"
fi
assert_contains "$out" 'unknown option: --bogus' 'unknown option error'

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

echo "=== cap-reached cleans stale round forensics ==="
D1B="$TMP/cap-cleanup"
write_common_inputs "$D1B" SIMPLE
printf '3\n' >"$D1B/review-round-count.txt"
mkdir -p "$D1B/plan-review/round-1" "$D1B/plan-review/round-2"
printf 'stale\n' >"$D1B/plan-review/round-1/stale.txt"
printf 'stale\n' >"$D1B/plan-review/round-2/stale.txt"
stub="$(write_loop_stub "$D1B" 'exit 97')"
set +e
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D1B" --round-cap 5 --convergence-threshold 3 >/dev/null
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass 'cap-reached cleanup exit 0'
else
    fail "cap-reached cleanup rc=$rc"
fi
[[ ! -e "$D1B/plan-review/round-1" ]] || fail 'cap-reached should remove stale round-1'
[[ ! -e "$D1B/plan-review/round-2" ]] || fail 'cap-reached should remove stale round-2'

echo "=== symlinked plan-review round dir skipped during cleanup ==="
D1S="$TMP/symlink-round"
write_common_inputs "$D1S" SIMPLE
mkdir -p "$D1S/plan-review/round-1" "$D1S/plan-review/round-keeper"
printf 'stale\n' >"$D1S/plan-review/round-1/stale.txt"
printf 'keep-me\n' >"$D1S/plan-review/round-keeper/stale.txt"
ln -s "$D1S/plan-review/round-keeper" "$D1S/plan-review/round-2"
stub="$(write_loop_stub "$D1S" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D1S" --round-cap 5 --convergence-threshold 3)"
assert_contains "$out" 'refusing to remove symlinked round artifact round-2' 'symlinked round cleanup warning'
[[ ! -e "$D1S/plan-review/round-1" ]] || fail 'non-symlink round-1 should be removed during cleanup'
[[ -f "$D1S/plan-review/round-keeper/stale.txt" ]] || fail 'symlinked round-2 target must survive cleanup'
[[ -L "$D1S/plan-review/round-2" ]] || fail 'symlinked round-2 link should remain'

echo "=== non-numeric review-round-count treated as zero ==="
D1C="$TMP/bad-count"
write_common_inputs "$D1C" SIMPLE
printf 'abc\n' >"$D1C/review-round-count.txt"
stub="$(write_loop_stub "$D1C" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D1C" --round-cap 5 --convergence-threshold 3)"
assert_contains "$out" 'review-round-count.txt non-numeric' 'non-numeric count warning'
if [[ "$(cat "$D1C/review-round-count.txt")" == "1" ]]; then
    pass 'non-numeric count treated as zero then round 1 persisted'
else
    fail 'non-numeric count should persist round 1'
fi

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

echo "=== loop-status tally-error rollback ==="
D3B="$TMP/loop-tally"
write_common_inputs "$D3B" HARD
printf '2\n' >"$D3B/review-round-count.txt"
stub="$(write_loop_stub "$D3B" "printf 'LOOP_STATUS=tally-error\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=3\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D3B" --round-cap 5 --convergence-threshold 3 >/dev/null
if [[ "$(cat "$D3B/review-round-count.txt")" == "2" ]]; then
    pass 'loop-status tally-error rollback'
else
    fail 'loop-status tally-error should rollback count'
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

echo "=== unexpected LOOP_STATUS preserved on non-zero rc ==="
D6B="$TMP/revision-failed-rc"
write_common_inputs "$D6B" SIMPLE
stub="$(write_loop_stub "$D6B" "printf 'LOOP_STATUS=revision-failed\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 1")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D6B" --round-cap 5 --convergence-threshold 3)"
assert_contains "$out" 'LOOP_STATUS=revision-failed' 'revision-failed preserved on rc 1'
if [[ "$out" == *'treating as panel-failed'* && "$out" != *'missing or invalid LOOP_STATUS'* ]]; then
    fail 'unexpected rc should not coerce revision-failed to panel-failed'
else
    pass 'revision-failed not coerced to panel-failed'
fi

echo "=== main-agent-vote-required preserved on non-zero rc ==="
D6C="$TMP/main-agent-rc"
write_common_inputs "$D6C" SIMPLE
stub="$(write_loop_stub "$D6C" "printf 'LOOP_STATUS=main-agent-vote-required\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 1")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D6C" --round-cap 5 --convergence-threshold 3)"
assert_contains "$out" 'LOOP_STATUS=main-agent-vote-required' 'main-agent-vote-required preserved on rc 1'
grep -Fq 'LOOP_STATUS=main-agent-vote-required' "$D6C/.step3-review-result.env" || fail 'result env main-agent-vote-required'

echo "=== HARD write-cursor failure handoff ==="
D10="$TMP/cursor-fail"
write_common_inputs "$D10" HARD
printf '1\n' >"$D10/plan-review-round-cursor.txt"
printf 'plan snapshot\n' >"$D10/plan-after-round-1.txt"
snap_stub="$D10/snapshot-plan-round-stub.sh"
cat >"$snap_stub" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
    read-cursor) printf 'ROUND_CURSOR=1\n'; exit 0 ;;
    write-cursor) exit 1 ;;
    *) exit 0 ;;
esac
EOF
chmod +x "$snap_stub"
loop_stub="$(write_loop_stub "$D10" 'exit 97')"
set +e
out="$("${launcher_env[@]}" RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH="$snap_stub" \
    RUN_STEP3_PLAN_REVIEW_LOOP_SH="$loop_stub" "$LAUNCHER" \
    --design-tmpdir "$D10" --round-cap 5 --convergence-threshold 3)"
rc=$?
set -e
if [[ "$rc" -eq 1 ]]; then
    pass 'write-cursor failure exit 1'
else
    fail "write-cursor failure rc=$rc"
fi
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'write-cursor failure panel-failed'
grep -Fq 'LOOP_STATUS=panel-failed' "$D10/.step3-review-result.env" || fail 'result env panel-failed on cursor failure'
if [[ "$(cat "$D10/review-round-count.txt" 2>/dev/null || echo missing)" == "1" ]]; then
    pass 'write-cursor failure keeps pending round persisted'
else
    fail 'write-cursor failure should leave review-round-count at 1'
fi

echo "=== stale inner result env ignored after launcher failure ==="
D7="$TMP/stale"
write_common_inputs "$D7" SIMPLE
cat >"$D7/.step3-plan-review-result.env" <<'EOF'
LOOP_STATUS=complete
ACCEPTED_COUNT=9
TALLY_PLAN_REVIEW_STATUS=ok
EOF
stub="$(write_loop_stub "$D7" 'exit 2')"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D7" --round-cap 5 --convergence-threshold 3)"
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'stale inner env ignored'
if grep -Fq 'ACCEPTED_COUNT=9' "$D7/.step3-review-result.env"; then
    fail 'stale accepted count leaked into normalized result env'
else
    pass 'stale accepted count did not leak'
fi

echo "=== inner result env takes precedence over stdout ==="
D8="$TMP/file-precedence"
write_common_inputs "$D8" SIMPLE
stub="$(write_loop_stub "$D8" "cat >\"\$DESIGN_TMPDIR/.step3-plan-review-result.env\" <<'EOF'
LOOP_STATUS=complete
ACCEPTED_COUNT=2
IMPORTANT_ACCEPTED_COUNT=1
DEGRADED_PANEL=0
ROUNDS_COMPLETED=1
TALLY_PLAN_REVIEW_STATUS=ok
AGGREGATOR_STATUS=file
VOTING_TALLY_FILE=file-tally.md
COLLECT_OK_COUNT=1
COLLECT_FAILURE_COUNT=0
EOF
printf 'LOOP_STATUS=panel-failed\nACCEPTED_COUNT=7\nAGGREGATOR_STATUS=stdout\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D8" --round-cap 5 --convergence-threshold 3)"
assert_contains "$out" 'LOOP_STATUS=complete' 'inner file loop status wins'
grep -Fq 'AGGREGATOR_STATUS=file' "$D8/.step3-review-result.env" || fail 'inner file aggregator should win over stdout'

echo "=== invalid round-cap via real plan-review-loop normalizes to panel-failed ==="
D11="$TMP/invalid-cap-real"
write_common_inputs "$D11" SIMPLE
out="$("${launcher_env[@]}" "$LAUNCHER" \
    --design-tmpdir "$D11" --round-cap 0 --convergence-threshold 3 2>&1)"
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'invalid round-cap panel-failed'
grep -Fq 'LOOP_STATUS=panel-failed' "$D11/.step3-review-result.env" || fail 'invalid round-cap result env panel-failed'

echo "=== terminal stdout breadcrumbs include round identifiers ==="
D11B="$TMP/breadcrumb-rounds"
write_common_inputs "$D11B" SIMPLE
stub="$(write_loop_stub "$D11B" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D11B" --round-cap 5 --convergence-threshold 3)"
assert_contains "$out" 'STEP3_REVIEW_ROUND_NUM=1' 'stdout STEP3_REVIEW_ROUND_NUM breadcrumb'
assert_contains "$out" 'ROUND_NUM=1' 'stdout ROUND_NUM breadcrumb'

echo "=== symlinked inner result env falls back to stdout ==="
D9="$TMP/symlink-inner"
write_common_inputs "$D9" SIMPLE
ln -s "$D9/elsewhere.env" "$D9/.step3-plan-review-result.env"
stub="$(write_loop_stub "$D9" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=stdout\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D9" --round-cap 5 --convergence-threshold 3)"
assert_contains "$out" 'LOOP_STATUS=complete' 'symlink inner stdout fallback loop status'
grep -Fq 'AGGREGATOR_STATUS=stdout' "$D9/.step3-review-result.env" || fail 'symlink inner should use stdout fallback'

echo "=== normalized result env keys ==="
assert_file_has_keys "$D6/.step3-review-result.env" 'result env' \
    LOOP_STATUS TALLY_PLAN_REVIEW_STATUS STEP3_REVIEW_CAP_REACHED STEP3_REVIEW_ROUND_NUM ROUND_NUM \
    ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED AGGREGATOR_STATUS \
    VOTING_TALLY_FILE REVIEW_ROUND_COUNT

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-run-step3-review.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-run-step3-review.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
