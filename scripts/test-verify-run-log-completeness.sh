#!/usr/bin/env bash
# test-verify-run-log-completeness.sh — regression harness for verify-run-log-completeness.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
VERIFY="$SCRIPT_DIR/verify-run-log-completeness.sh"
MANIFEST="$SCRIPT_DIR/../docs/run-logs-required-files.tsv"

[ -x "$VERIFY" ] || { echo "FAIL: $VERIFY not executable" >&2; exit 1; }
[ -f "$MANIFEST" ] || { echo "FAIL: $MANIFEST not found" >&2; exit 1; }

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

load_required_files() {
    awk -F '\t' '
        $1 == "relative_path" { next }
        $1 ~ /^#/ || $1 == "" { next }
        $2 ~ /^(always|step7a)$/ { print $1 }
    ' "$MANIFEST"
}

assert_manifest_matches_batch_table() {
    # shellcheck source=scripts/larch-log-batches.sh
    source "$SCRIPT_DIR/larch-log-batches.sh"

    local mismatch=0 relative_path condition batch_slug extension expected_ext
    while IFS=$'\t' read -r relative_path condition batch_slug extension; do
        [ "$relative_path" = "relative_path" ] && continue
        [ -n "$relative_path" ] || continue
        case "$relative_path" in \#*) continue ;; esac
        [ "$condition" = "always" ] || continue
        [ "$batch_slug" = "manifest" ] && continue

        if ! expected_ext="$(larch_log_batch_extension "$batch_slug" 2>/dev/null)"; then
            fail "manifest batch slug missing from larch-log-batches: $batch_slug"
            mismatch=1
            continue
        fi
        if [ ".$extension" != "$expected_ext" ]; then
            fail "manifest extension mismatch for $batch_slug: manifest .$extension vs batch table $expected_ext"
            mismatch=1
        else
            pass "manifest extension matches batch table for $batch_slug"
        fi
    done < "$MANIFEST"

    return "$mismatch"
}

REQUIRED_FILES=()
while IFS= read -r required_file; do
    REQUIRED_FILES+=("$required_file")
done < <(load_required_files)
assert_manifest_matches_batch_table || true

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

# Test 2: missing session-transcript.jsonl from a Step-7a-complete run → MISSING reported
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

# Test 6: pre-Step-7a partial tree should not require Step-7a+ files
run_pre_step7a="$TMP/run-pre-step7a"
mkdir -p "$run_pre_step7a"
printf 'placeholder\n' > "$run_pre_step7a/manifest.json"
printf 'placeholder\n' > "$run_pre_step7a/plan-goals-test.md"
printf 'placeholder\n' > "$run_pre_step7a/plan-review-tally.json"
printf 'placeholder\n' > "$run_pre_step7a/code-review-tally.json"
printf 'placeholder\n' > "$run_pre_step7a/review-findings-full.jsonl"
out="$("$VERIFY" "$run_pre_step7a" 2>&1 || true)"
assert_contains "pre-step7a partial emits OK" "$out" "OK"

# Test 7: Step-8 tree should not require Step-9a.1-only run-statistics
run_step8="$TMP/run-step8"
mkdir -p "$run_step8"
for f in manifest.json plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md final-summary.md; do
    printf 'placeholder\n' > "$run_step8/$f"
done
out="$("$VERIFY" "$run_step8" 2>&1 || true)"
assert_contains "step8 partial emits OK" "$out" "OK"

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then exit 1; fi
echo "All assertions passed."
