#!/usr/bin/env bash
# test-run-step5-review.sh - Regression harness for run-step5-review.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
LAUNCHER="$SCRIPT_DIR/run-step5-review.sh"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-run-step5-review.XXXXXX")"
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
        fail "$label (missing $needle; got ${haystack:0:400})"
    fi
}

assert_file_equals() {
    local file="$1" expected="$2" label="$3"
    local actual
    actual="$(cat "$file")"
    if [[ "$actual" == "$expected" ]]; then
        pass "$label"
    else
        fail "$label"$'\n'"expected:"$'\n'"$expected"$'\n'"actual:"$'\n'"$actual"
    fi
}

make_tmpdir() {
    local dir="$1" _case_label="$2" codex="$3" cursor="$4" session_id="${5:-run-xyz}" dynamic_archetypes="${6:-}"
    mkdir -p "$dir"
    printf '%s\n' "$session_id" > "$dir/session-id"
    printf '%s\n' "Feature description" > "$dir/feature-description.txt"
    printf '%s\n' "Plan body with enough content to be a real plan for launcher tests." > "$dir/plan.txt"
    {
        printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT"
        printf 'CODEX_PRESENT=%s\n' "$codex"
        printf 'CURSOR_PRESENT=%s\n' "$cursor"
        printf 'LARCH_TOKEN_SESSION_ID=%s\n' "run-xyz"
        printf 'LARCH_TIMING_LEDGER=%s\n' "$dir/timing-ledger.tsv"
        if [[ -n "$dynamic_archetypes" ]]; then
            printf 'LARCH_DYNAMIC_ARCHETYPES_MAX=%s\n' "$dynamic_archetypes"
        fi
    } > "$dir/session-env.sh"
}

SPY="$TMP/review-spy.sh"
cat > "$SPY" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$RUN_STEP5_ARGV_FILE"
printf 'REVIEW_AND_FIX_STATUS=complete\n'
EOF
chmod +x "$SPY"

echo "=== missing required flags ==="
set +e
out="$("$LAUNCHER" --round-num 1 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "missing implement tmpdir exits 2"; else fail "missing implement tmpdir rc=$rc"; fi
assert_contains "$out" "--implement-tmpdir is required" "missing implement tmpdir error"

echo "=== reject invalid round number ==="
case_dir="$TMP/invalid-round"
make_tmpdir "$case_dir" default true false
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 0 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "round-num zero exits 2"; else fail "round-num zero rc=$rc"; fi
assert_contains "$out" "--round-num must be a positive integer" "round-num zero error"

echo "=== reject invalid reviewer booleans ==="
case_dir="$TMP/bad-bool"
make_tmpdir "$case_dir" default maybe false
set +e
out="$(RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$TMP/bad-bool.argv" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "bad CODEX_PRESENT exits 2"; else fail "bad CODEX_PRESENT rc=$rc"; fi
assert_contains "$out" "CODEX_PRESENT must be true or false" "bad CODEX_PRESENT error"

echo "=== unified Step 5 argv (round 3, codex on) ==="
case_dir="$TMP/simple"
make_tmpdir "$case_dir" round3-codex true false
argv_file="$TMP/simple.argv"
out="$(RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 3)"
assert_contains "$out" "REVIEW_AND_FIX_STATUS=complete" "downstream stdout passes through"
assert_file_equals "$argv_file" "--implement-tmpdir
$case_dir
--mode
diff
--round-num
3
--round-cap
5
--session-env-path
$case_dir/session-env.sh
--codex-available
true
--cursor-available
false
--plan-file
$case_dir/plan.txt
--feature-file
$case_dir/feature-description.txt
--run-id
run-xyz" "conventional plan path resolved argv"

echo "=== unified Step 5 argv (round 1, dynamic-archetypes) ==="
case_dir="$TMP/hard"
make_tmpdir "$case_dir" round1-dynamic-archetypes false true "run-xyz" 2
argv_file="$TMP/hard.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 >/dev/null
assert_file_equals "$argv_file" "--implement-tmpdir
$case_dir
--mode
diff
--round-num
1
--round-cap
5
--session-env-path
$case_dir/session-env.sh
--codex-available
false
--cursor-available
true
--plan-file
$case_dir/plan.txt
--feature-file
$case_dir/feature-description.txt
--dynamic-archetypes
2
--run-id
run-xyz" "dynamic-archetypes forwarded on unified argv"

echo "=== degraded prior rounds do not extend hard round cap ==="
case_dir="$TMP/degraded-cap"
make_tmpdir "$case_dir" degraded-cap true false
mkdir -p "$case_dir/round-1" "$case_dir/round-2"
printf 'DEGRADED_ROUND=true\n' > "$case_dir/round-1/review-and-fix.env"
printf 'DEGRADED_ROUND=false\n' > "$case_dir/round-2/review-and-fix.env"
argv_file="$TMP/degraded-cap.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 3 >/dev/null
assert_contains "$(cat "$argv_file")" "--round-cap
5" "degraded prior rounds keep unified hard round cap"

echo "=== canonical RUN_ID prefers sentinel over session-id ==="
case_dir="$TMP/run-id-sentinel"
make_tmpdir "$case_dir" default true false "session-only"
cat > "$case_dir/parent-issue.md" <<'EOF'
ISSUE_NUMBER=456
RUN_ID=review-custom-run
ADOPTED=true
EOF
argv_file="$TMP/run-id-sentinel.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 2 >/dev/null
assert_contains "$(cat "$argv_file")" "review-custom-run" "sentinel RUN_ID overrides session-id"

echo "=== canonical RUN_ID falls back to manifest when sentinel missing ==="
case_dir="$TMP/run-id-manifest"
make_tmpdir "$case_dir" default true false "session-only"
mkdir -p "$case_dir/larch-logs/implement/review-manifest-run"
printf '{}\n' > "$case_dir/larch-logs/implement/review-manifest-run/manifest.json"
argv_file="$TMP/run-id-manifest.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 2 >/dev/null
assert_contains "$(cat "$argv_file")" "review-manifest-run" "manifest RUN_ID overrides session-id"

echo "=== loop resume re-marks Step 5 timing interval ==="
case_dir="$TMP/loop-resume-mark"
make_tmpdir "$case_dir" default true false
argv_file="$TMP/loop-resume-mark.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --mode loop --starting-round 2 >/dev/null
if awk -F '\t' '$2 == "mark" && $4 == "implement" && $5 == "Step 5 — code review" { found=1 } END { exit found ? 0 : 1 }' "$case_dir/timing-ledger.tsv"; then
    pass "loop resume records Step 5 timing mark"
else
    fail "loop resume records Step 5 timing mark"
fi
python3 "$REPO_ROOT/python/cli.py" timing report --ledger "$case_dir/timing-ledger.tsv" --full --format json --output "$case_dir/timing-report.json" >/dev/null
if command -v jq >/dev/null 2>&1 && jq -e '.per_step[] | select(.skill == "implement" and .step == "Step 5 — code review")' "$case_dir/timing-report.json" >/dev/null; then
    pass "loop resume mark appears in timing-report"
else
    fail "loop resume mark appears in timing-report"
fi

echo "=== skipped-entry round-1: launcher writes missing Step 5 mark ==="
case_dir="$TMP/skipped-entry-round1"
make_tmpdir "$case_dir" default true false
# Pre-seed ledger with Step 4 mark only (simulates skipped step-5-entry.sh)
printf 'v1\tmark\t100\timplement\tStep 4 — commit implementation\t-\t-\t-\t-\t-\t-\t-\t-\n' \
    > "$case_dir/timing-ledger.tsv"
argv_file="$TMP/skipped-entry-round1.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --mode loop --starting-round 1 >/dev/null
mark_count="$(awk -F '\t' '$2 == "mark" && $4 == "implement" && $5 == "Step 5 — code review" { n++ } END { print n+0 }' "$case_dir/timing-ledger.tsv")"
if [[ "$mark_count" -eq 1 ]]; then
    pass "skipped-entry round-1: launcher writes Step 5 mark"
else
    fail "skipped-entry round-1: expected 1 Step 5 mark, got $mark_count"
fi

echo "=== no-duplicate: prior Step 5 mark present, launcher skips re-mark ==="
case_dir="$TMP/no-duplicate-mark"
make_tmpdir "$case_dir" default true false
# Pre-seed ledger with existing Step 5 mark (simulates normal round-1 entry path)
printf 'v1\tmark\t100\timplement\tStep 5 — code review\t-\t-\t-\t-\t-\t-\t-\t-\n' \
    > "$case_dir/timing-ledger.tsv"
argv_file="$TMP/no-duplicate-mark.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --mode loop --starting-round 1 >/dev/null
mark_count="$(awk -F '\t' '$2 == "mark" && $4 == "implement" && $5 == "Step 5 — code review" { n++ } END { print n+0 }' "$case_dir/timing-ledger.tsv")"
if [[ "$mark_count" -eq 1 ]]; then
    pass "no-duplicate: prior Step 5 mark not duplicated"
else
    fail "no-duplicate: expected 1 Step 5 mark, got $mark_count"
fi

echo "=== conventional plan.txt empty: fail closed ==="
case_dir="$TMP/plan-file-empty"
make_tmpdir "$case_dir" default true false
: > "$case_dir/plan.txt"
argv_file="$TMP/empty-plan.argv"
set +e
out="$(RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "step5: empty plan.txt exits 2"; else fail "step5 empty plan rc=$rc"; fi
assert_contains "$out" "plan file is empty at conventional path" "step5 emits empty-plan error"
[[ ! -f "$argv_file" ]] || fail "review helper should not run when plan.txt empty"

echo "=== conventional plan.txt missing: fail closed even when design-export/plan.txt exists ==="
case_dir="$TMP/plan-file-missing"
make_tmpdir "$case_dir" default true false
rm -f "$case_dir/plan.txt"
mkdir -p "$case_dir/design-export"
printf '%s\n' "Stale local export must not substitute for conventional plan.txt." > "$case_dir/design-export/plan.txt"
argv_file="$TMP/missing-plan.argv"
set +e
out="$(RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "step5: conventional plan.txt missing exits 2 even with design-export"; else fail "step5 plan missing rc=$rc"; fi
assert_contains "$out" "plan file not found at conventional path" "step5 emits conventional-path error"
[[ ! -f "$argv_file" ]] || fail "review helper should not run when plan.txt missing"

echo "=== main-agent-vote-required emits ledger KVs ==="
MAV_SPY="$TMP/review-mav-spy.sh"
cat > "$MAV_SPY" <<'EOF'
#!/usr/bin/env bash
printf 'STEP5_REVIEW_STATUS=main-agent-vote-required\n'
printf 'needs main vote\n' >&2
exit 7
EOF
chmod +x "$MAV_SPY"
case_dir="$TMP/mav-ledger"
make_tmpdir "$case_dir" default true false
set +e
out="$(RUN_STEP5_REVIEW_SH="$MAV_SPY" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 2>/dev/null)"
rc=$?
set -e
if [[ "$rc" -eq 7 ]]; then pass "step5 MAV preserves downstream rc"; else fail "step5 MAV rc=$rc"; fi
assert_contains "$out" "STEP5_REVIEW_LEDGER_READY=true" "step5 MAV emits ledger ready"
assert_contains "$out" "STEP5_REVIEW_LEDGER_SITE=step5-mav" "step5 MAV emits ledger site"
assert_contains "$out" "STEP5_REVIEW_LEDGER_TRIGGER=main-agent-vote-required" "step5 MAV emits ledger trigger"
assert_contains "$out" "STEP5_REVIEW_LEDGER_DISPATCHER=run-step5-review" "step5 MAV emits ledger dispatcher"

echo "=== coder-main-agent-required record-escalation failure fails open ==="
CMAR_SPY="$TMP/review-cmar-spy.sh"
cat > "$CMAR_SPY" <<'EOF'
#!/usr/bin/env bash
printf 'STEP5_REVIEW_STATUS=coder-main-agent-required\n'
printf 'needs main agent\n' >&2
EOF
chmod +x "$CMAR_SPY"
case_dir="$TMP/cmar-record-fail"
make_tmpdir "$case_dir" default true false
printf 'outside\n' >"$TMP/outside-ledger"
ln -s "$TMP/outside-ledger" "$case_dir/stall-recovery-escalation-ledger.tsv"
set +e
out="$(CLAUDE_PLUGIN_ROOT="$REPO_ROOT" RUN_STEP5_REVIEW_SH="$CMAR_SPY" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then pass "step5 CMAR record-escalation failure preserves downstream rc"; else fail "step5 CMAR record-escalation failure rc=$rc"; fi
assert_contains "$out" "must not be a symlink" "step5 CMAR surfaces record-escalation error"
assert_contains "$out" "STEP5_REVIEW_LEDGER_READY=true" "step5 CMAR emits fallback ledger KVs"
assert_contains "$(cat "$case_dir/execution-issues.md")" "Tool Failure: record-escalation" "step5 CMAR writes record-escalation tool failure"

echo "=== conventional plan.txt missing AND design-export missing: fail loud ==="
case_dir="$TMP/plan-file-fail"
make_tmpdir "$case_dir" default true false
rm -f "$case_dir/plan.txt"
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "step5: no conventional plan.txt exits 2"; else fail "step5 no-plan rc=$rc"; fi
assert_contains "$out" "plan file not found at conventional path" "step5 no-plan error"

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-run-step5-review.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-run-step5-review.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
