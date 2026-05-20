#!/usr/bin/env bash
# test-verify-run-log-completeness.sh — regression harness for verify-run-log-completeness.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
VERIFY="$SCRIPT_DIR/verify-run-log-completeness.sh"

[ -x "$VERIFY" ] || { echo "FAIL: $VERIFY not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-verify-run-log-completeness.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

pass() { echo "  ok: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }

assert_contains() {
    local label="$1" haystack="$2" needle="$3"
    if [[ "$haystack" == *"$needle"* ]]; then pass "$label"
    else fail "$label (missing '$needle'; got '${haystack:0:200}')"; fi
}

# Required files from the real manifest (condition=always).
REQUIRED_FILES=(
    manifest.json
    plan-goals-test.md
    plan-review-tally.json
    code-review-tally.json
    review-findings-full.jsonl
    version-bump-reasoning.md
    token-report.json
    timing-report.json
    execution-issues.ndjson
    run-statistics.json
    session-transcript.jsonl
)

make_complete_run_dir() {
    local dir="$1"
    mkdir -p "$dir"
    for f in "${REQUIRED_FILES[@]}"; do
        printf 'placeholder\n' > "$dir/$f"
    done
}

# Test 1: all files present → OK
run_ok="$TMP/run-ok"
make_complete_run_dir "$run_ok"
out="$("$VERIFY" "$run_ok" 2>&1 || true)"
assert_contains "complete run emits OK" "$out" "OK"

# Test 2: missing session-transcript.jsonl → MISSING reported
run_missing_transcript="$TMP/run-missing-transcript"
make_complete_run_dir "$run_missing_transcript"
rm "$run_missing_transcript/session-transcript.jsonl"
out="$("$VERIFY" "$run_missing_transcript" 2>&1 || true)"
assert_contains "missing transcript emits MISSING" "$out" "MISSING=session-transcript.jsonl"

# Test 3: missing multiple files → all listed in MISSING
run_missing_multi="$TMP/run-missing-multi"
make_complete_run_dir "$run_missing_multi"
rm "$run_missing_multi/session-transcript.jsonl"
rm "$run_missing_multi/token-report.json"
out="$("$VERIFY" "$run_missing_multi" 2>&1 || true)"
assert_contains "multi-missing includes session-transcript" "$out" "session-transcript.jsonl"
assert_contains "multi-missing includes token-report" "$out" "token-report.json"

# Test 4: nonexistent run dir → error exit
out="$("$VERIFY" "$TMP/nonexistent-run" 2>&1 || true)"
assert_contains "nonexistent dir emits error" "$out" "not found"

# Test 5: verify C068D05A (known pre-fix run) when it exists in repo tree — conditional
repo_root="$(cd "$SCRIPT_DIR/.." && pwd -P)"
pre_fix_run="$repo_root/larch-logs/implement/C068D05A-E9B5-45EC-86E4-3AB8A9161C9D"
if [ -d "$pre_fix_run" ]; then
    out="$("$VERIFY" "$pre_fix_run" 2>&1 || true)"
    assert_contains "pre-fix run missing session-transcript" "$out" "session-transcript.jsonl"
fi

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then exit 1; fi
echo "All assertions passed."
