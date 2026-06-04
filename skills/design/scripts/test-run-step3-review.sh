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
out="$("${launcher_env[@]}" "$LAUNCHER" --round-cap 5 2>&1)"
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
out="$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$DARGV" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass 'missing round-cap exits 2'
else
    fail "missing round-cap rc=$rc"
fi
assert_contains "$out" '--round-cap is required' 'missing round-cap error'

echo "=== unknown option ==="
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$DARGV" --round-cap 5 --bogus 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass 'unknown option exits 2'
else
    fail "unknown option rc=$rc"
fi
assert_contains "$out" 'unknown option: --bogus' 'unknown option error'

echo "=== mutually exclusive mode flags exit 2 ==="
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$DARGV" --preview-only --no-preview 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass '--preview-only --no-preview exits 2'
else
    fail "--preview-only --no-preview rc=$rc"
fi
assert_contains "$out" 'mutually exclusive' 'mutual exclusion error message'

echo "=== omitted mode flags default to --no-preview ==="
D_DEFAULT="$TMP/default-mode"
write_common_inputs "$D_DEFAULT" SIMPLE
stub="$(write_loop_stub "$D_DEFAULT" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D_DEFAULT" --round-cap 5)"
assert_contains "$out" 'LOOP_STATUS=complete' 'omitted mode defaults to no-preview review path'

echo "=== --preview-only renders plan and creates sentinel ==="
D_PV="$TMP/preview"
write_common_inputs "$D_PV" SIMPLE
preview_stub="$D_PV/preview-stub.sh"
cat >"$preview_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf '\n## Plan Candidate for Review\n\npreview body\n'
STUBEOF
chmod +x "$preview_stub"
set +e
out="$("${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$preview_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass '--preview-only exits 0'
else
    fail "--preview-only rc=$rc"
fi
assert_contains "$out" '## Plan Candidate for Review' '--preview-only renders header'
if [[ -e "$D_PV/.step3-entry-plan-printed" ]]; then
    pass '--preview-only creates sentinel'
else
    fail '--preview-only should create .step3-entry-plan-printed sentinel'
fi

echo "=== --preview-only second call skips render (sentinel exists) ==="
set +e
out2="$("${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$preview_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV" 2>&1)"
rc2=$?
set -e
if [[ "$rc2" -eq 0 ]]; then
    pass '--preview-only second call exits 0'
else
    fail "--preview-only second call rc=$rc2"
fi
if [[ -z "$(printf '%s' "$out2" | tr -d '[:space:]')" ]]; then
    pass '--preview-only second call emits nothing (sentinel suppresses)'
else
    fail "--preview-only second call should emit nothing; got: ${out2:0:100}"
fi

echo "=== --preview-only without --round-cap ==="
D_PV2="$TMP/preview-no-cap"
write_common_inputs "$D_PV2" SIMPLE
set +e
out="$("${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$preview_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV2" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass '--preview-only without --round-cap exits 0'
else
    fail "--preview-only without --round-cap rc=$rc (should not require --round-cap)"
fi

echo "=== --preview-only non-header renderer output does not create sentinel ==="
D_PV3="$TMP/preview-nonheader"
write_common_inputs "$D_PV3" SIMPLE
nonheader_stub="$D_PV3/nonheader-stub.sh"
cat >"$nonheader_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf '**⚠ 3: DESIGN_TMPDIR not under allowlist; cannot present plan candidate**\n'
exit 0
STUBEOF
chmod +x "$nonheader_stub"
"${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$nonheader_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV3" >/dev/null 2>&1 || true
if [[ ! -e "$D_PV3/.step3-entry-plan-printed" ]]; then
    pass '--preview-only non-header output does not create sentinel'
else
    fail '--preview-only should not create sentinel for non-header renderer output'
fi

echo "=== --preview-only missing/empty plan.txt sentinel not created without exact warning ==="
D_PV4="$TMP/preview-bare-missing"
mkdir -p "$D_PV4"
cat >"$D_PV4/session-env.sh" <<'SEOF'
LARCH_CLAUDE_PLUGIN_ROOT=PLACEHOLDER
SEOF
missing_stub="$D_PV4/missing-stub.sh"
cat >"$missing_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf 'Some other warning without the exact string\n'
exit 0
STUBEOF
chmod +x "$missing_stub"
"${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$missing_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV4" >/dev/null 2>&1 || true
if [[ ! -e "$D_PV4/.step3-entry-plan-printed" ]]; then
    pass '--preview-only bare missing plan without exact warning: no sentinel'
else
    fail '--preview-only should not create sentinel without exact missing-plan warning'
fi

echo "=== --no-preview captured output has no plan preview ==="
D_NP="$TMP/no-preview"
write_common_inputs "$D_NP" SIMPLE
stub="$(write_loop_stub "$D_NP" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --no-preview --design-tmpdir "$D_NP" --round-cap 5)"
if [[ "$out" == *'## Plan Candidate for Review'* ]]; then
    fail '--no-preview should not output plan preview'
else
    pass '--no-preview captured output has no plan preview'
fi
assert_contains "$out" 'LOOP_STATUS=complete' '--no-preview emits review KVs'

echo "=== cap-reached short-circuit ==="
D1="$TMP/cap"
write_common_inputs "$D1" SIMPLE
printf '3\n' >"$D1/review-round-count.txt"
stub="$(write_loop_stub "$D1" 'exit 97')"
set +e
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D1" --round-cap 5)"
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
    --design-tmpdir "$D1B" --round-cap 5 >/dev/null
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
    --design-tmpdir "$D1S" --round-cap 5)"
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
    --design-tmpdir "$D1C" --round-cap 5)"
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
    --design-tmpdir "$D2" --round-cap 5 >/dev/null
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
    --design-tmpdir "$D3" --round-cap 5 >/dev/null
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
    --design-tmpdir "$D3B" --round-cap 5 >/dev/null
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
    --design-tmpdir "$D4" --round-cap 5 >/dev/null
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
    --design-tmpdir "$D5" --round-cap 5 >/dev/null
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
    --design-tmpdir "$D6" --round-cap 5)"
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'unknown status normalized'

echo "=== unexpected LOOP_STATUS preserved on non-zero rc ==="
D6B="$TMP/revision-failed-rc"
write_common_inputs "$D6B" SIMPLE
stub="$(write_loop_stub "$D6B" "printf 'LOOP_STATUS=revision-failed\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 1")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D6B" --round-cap 5)"
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
    --design-tmpdir "$D6C" --round-cap 5)"
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
    --design-tmpdir "$D10" --round-cap 5)"
rc=$?
set -e
if [[ "$rc" -eq 1 ]]; then
    pass 'write-cursor failure exit 1'
else
    fail "write-cursor failure rc=$rc"
fi
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'write-cursor failure panel-failed'
grep -Fq 'LOOP_STATUS=panel-failed' "$D10/.step3-review-result.env" || fail 'result env panel-failed on cursor failure'
if [[ "$(cat "$D10/review-round-count.txt" 2>/dev/null || echo missing)" == "0" ]]; then
    pass 'write-cursor failure rolls back review-round-count'
else
    fail 'write-cursor failure should roll back review-round-count to 0'
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
    --design-tmpdir "$D7" --round-cap 5)"
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
    --design-tmpdir "$D8" --round-cap 5)"
assert_contains "$out" 'LOOP_STATUS=complete' 'inner file loop status wins'
grep -Fq 'AGGREGATOR_STATUS=file' "$D8/.step3-review-result.env" || fail 'inner file aggregator should win over stdout'

echo "=== invalid round-cap via real plan-review-loop normalizes to panel-failed ==="
D11="$TMP/invalid-cap-real"
write_common_inputs "$D11" SIMPLE
out="$("${launcher_env[@]}" "$LAUNCHER" \
    --design-tmpdir "$D11" --round-cap 0 2>&1)"
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'invalid round-cap panel-failed'
grep -Fq 'LOOP_STATUS=panel-failed' "$D11/.step3-review-result.env" || fail 'invalid round-cap result env panel-failed'

echo "=== driver argv matches plan-review-loop contract ==="
# Edit-in-sync: seam stub argv whitelist must match plan-review-loop.sh case parser
# and every flag run-step3-review.sh forwards; scripts/test-design-structure.sh pins drift.
D_SEAM="$TMP/integration-seam"
write_common_inputs "$D_SEAM" SIMPLE
seam_stub="$D_SEAM/plan-review-loop-seam.sh"
cat >"$seam_stub" <<'STUBEOF'
#!/usr/bin/env bash
set -euo pipefail
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir|--plan-file|--feature-file|--codex-present|--cursor-present|--round-num|--round-cap|--timeout)
            shift 2
            ;;
        *)
            printf 'plan-review-loop.sh: unknown option: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'
exit 0
STUBEOF
chmod +x "$seam_stub"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$seam_stub" "$LAUNCHER" \
    --design-tmpdir "$D_SEAM" --round-cap 5)"
assert_contains "$out" 'LOOP_STATUS=complete' 'integration seam settled LOOP_STATUS'
grep -Fq 'LOOP_STATUS=complete' "$D_SEAM/.step3-review-result.env" || fail 'integration seam result env complete'

echo "=== terminal stdout breadcrumbs include round identifiers ==="
D11B="$TMP/breadcrumb-rounds"
write_common_inputs "$D11B" SIMPLE
stub="$(write_loop_stub "$D11B" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D11B" --round-cap 5)"
assert_contains "$out" 'STEP3_REVIEW_ROUND_NUM=1' 'stdout STEP3_REVIEW_ROUND_NUM breadcrumb'
assert_contains "$out" 'ROUND_NUM=1' 'stdout ROUND_NUM breadcrumb'

echo "=== symlinked inner result env falls back to stdout ==="
D9="$TMP/symlink-inner"
write_common_inputs "$D9" SIMPLE
ln -s "$D9/elsewhere.env" "$D9/.step3-plan-review-result.env"
stub="$(write_loop_stub "$D9" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=stdout\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D9" --round-cap 5)"
assert_contains "$out" 'LOOP_STATUS=complete' 'symlink inner stdout fallback loop status'
grep -Fq 'AGGREGATOR_STATUS=stdout' "$D9/.step3-review-result.env" || fail 'symlink inner should use stdout fallback'

echo "=== symlinked outer result env refuses write with WARN ==="
D12="$TMP/symlink-outer"
write_common_inputs "$D12" SIMPLE
ln -sf "$D12/outer-target.env" "$D12/.step3-review-result.env"
stub="$(write_loop_stub "$D12" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
set +e
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D12" --round-cap 5 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 1 ]]; then
    pass 'symlinked outer result env exit 1'
else
    fail "symlinked outer result env rc=$rc"
fi
assert_contains "$out" 'refusing to write symlinked result env' 'symlinked outer write refusal WARN'
assert_contains "$out" 'LOOP_STATUS=complete' 'symlinked outer still emits LOOP_STATUS on stdout'
[[ -L "$D12/.step3-review-result.env" ]] || fail 'symlinked outer result env must remain a symlink'
[[ ! -f "$D12/outer-target.env" ]] || fail 'symlinked outer must not mutate write target'

echo "=== cap-reached with symlinked outer result env still emits cap-reached ==="
D12B="$TMP/symlink-outer-cap"
write_common_inputs "$D12B" SIMPLE
printf '3\n' >"$D12B/review-round-count.txt"
ln -sf "$D12B/outer-cap-target.env" "$D12B/.step3-review-result.env"
loop_stub="$(write_loop_stub "$D12B" 'exit 97')"
set +e
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$loop_stub" "$LAUNCHER" \
    --design-tmpdir "$D12B" --round-cap 5 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 1 ]]; then
    pass 'cap-reached symlinked outer exit 1'
else
    fail "cap-reached symlinked outer rc=$rc"
fi
assert_contains "$out" 'LOOP_STATUS=cap-reached' 'cap-reached symlinked outer stdout LOOP_STATUS'
assert_contains "$out" 'TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached' 'cap-reached symlinked outer stdout tally'
[[ -L "$D12B/.step3-review-result.env" ]] || fail 'cap-reached symlinked outer must remain a symlink'

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
