#!/usr/bin/env bash
# test-compose-collector-failure-log.sh — regression tests for compose-collector-failure-log.sh

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/compose-collector-failure-log.sh"
TMPDIR_BASE="$(mktemp -d "${TMPDIR:-/tmp}/test-compose-collector-failure-log.XXXXXX")"
PASS_COUNT=0
FAIL_COUNT=0

cleanup() { rm -rf "$TMPDIR_BASE"; }
trap cleanup EXIT

ok()   { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

assert_contains() {
    local label=$1 file=$2 needle=$3
    if grep -Fq -- "$needle" "$file"; then
        ok "$label"
    else
        fail "$label (missing: $needle)"
        sed 's/^/    /' "$file" || true
    fi
}

assert_not_contains() {
    local label=$1 file=$2 needle=$3
    if grep -Fq -- "$needle" "$file"; then
        fail "$label (unexpected: $needle)"
    else
        ok "$label"
    fi
}

assert_rc() {
    local label=$1 actual=$2 expected=$3
    if [ "$actual" = "$expected" ]; then
        ok "$label"
    else
        fail "$label (expected rc=$expected, got rc=$actual)"
    fi
}

assert_nonempty_file() {
    local label=$1 file=$2
    if [ -s "$file" ]; then
        ok "$label"
    else
        fail "$label (file is empty or missing: $file)"
    fi
}

RECORD="REVIEWER_FILE=/tmp/foo.txt|TOOL=cursor|STATUS=EMPTY_OUTPUT|EXIT_CODE=0|FAILURE_REASON=exit-0-empty"

# ── Case 1: happy path — reviewer file + .diag both non-empty ────────────────
echo "Case 1: happy path"
dir1="$TMPDIR_BASE/case1"
mkdir -p "$dir1"
printf 'review findings here\n' > "$dir1/rev.txt"
printf 'stderr diagnostics\n' > "$dir1/rev.txt.diag"
output1="$dir1/out.log"
"$SCRIPT" --reviewer-file "$dir1/rev.txt" --structured-record "$RECORD" --output "$output1"
assert_contains "1: structured record header" "$output1" "## Structured collector record"
assert_contains "1: record line present" "$output1" "REVIEWER_FILE=/tmp/foo.txt"
assert_contains "1: reviewer output header" "$output1" "## Reviewer output"
assert_contains "1: reviewer file content" "$output1" "review findings here"
assert_contains "1: diag header" "$output1" "## Reviewer stderr"
assert_contains "1: diag content" "$output1" "stderr diagnostics"
assert_nonempty_file "1: output guaranteed non-empty" "$output1"

# ── Case 2: empty reviewer file ───────────────────────────────────────────────
echo "Case 2: empty reviewer file"
dir2="$TMPDIR_BASE/case2"
mkdir -p "$dir2"
: > "$dir2/rev.txt"   # 0-byte file
output2="$dir2/out.log"
"$SCRIPT" --reviewer-file "$dir2/rev.txt" --structured-record "$RECORD" --output "$output2"
assert_contains "2: structured record present" "$output2" "## Structured collector record"
assert_contains "2: empty placeholder" "$output2" "(empty:"
assert_nonempty_file "2: output guaranteed non-empty" "$output2"

# ── Case 3: missing reviewer file ─────────────────────────────────────────────
echo "Case 3: missing reviewer file"
dir3="$TMPDIR_BASE/case3"
mkdir -p "$dir3"
output3="$dir3/out.log"
"$SCRIPT" --reviewer-file "$dir3/nonexistent.txt" --structured-record "$RECORD" --output "$output3"
assert_contains "3: structured record present" "$output3" "## Structured collector record"
assert_contains "3: missing placeholder" "$output3" "(file missing:"
assert_nonempty_file "3: output guaranteed non-empty" "$output3"

# ── Case 4: empty .diag file ──────────────────────────────────────────────────
echo "Case 4: empty .diag file"
dir4="$TMPDIR_BASE/case4"
mkdir -p "$dir4"
printf 'some review content\n' > "$dir4/rev.txt"
: > "$dir4/rev.txt.diag"   # 0-byte diag
output4="$dir4/out.log"
"$SCRIPT" --reviewer-file "$dir4/rev.txt" --structured-record "$RECORD" --output "$output4"
assert_contains "4: structured record present" "$output4" "## Structured collector record"
assert_contains "4: reviewer content present" "$output4" "some review content"
assert_contains "4: diag empty placeholder" "$output4" "(empty:"
assert_nonempty_file "4: output guaranteed non-empty" "$output4"

# ── Case 4b: stderr-tail sidecar ─────────────────────────────────────────────
echo "Case 4b: stderr-tail sidecar"
dir4b="$TMPDIR_BASE/case4b"
mkdir -p "$dir4b"
printf 'some review content\n' > "$dir4b/rev.txt"
printf 'redacted stderr tail\n' > "$dir4b/rev.txt.stderr-tail"
output4b="$dir4b/out.log"
"$SCRIPT" --reviewer-file "$dir4b/rev.txt" --structured-record "$RECORD" --output "$output4b"
assert_contains "4b: stderr-tail header" "$output4b" "## Failed-agent stderr tail"
assert_contains "4b: stderr-tail content" "$output4b" "redacted stderr tail"

# ── Case 5: missing .diag file ────────────────────────────────────────────────
echo "Case 5: missing .diag file"
dir5="$TMPDIR_BASE/case5"
mkdir -p "$dir5"
printf 'some review content\n' > "$dir5/rev.txt"
# .diag is intentionally absent
output5="$dir5/out.log"
"$SCRIPT" --reviewer-file "$dir5/rev.txt" --structured-record "$RECORD" --output "$output5"
assert_contains "5: structured record present" "$output5" "## Structured collector record"
assert_contains "5: reviewer content present" "$output5" "some review content"
assert_contains "5: diag missing placeholder" "$output5" "(file missing:"
assert_nonempty_file "5: output guaranteed non-empty" "$output5"

# ── Case 5b: empty --reviewer-file → (no path provided) + no .diag section ───
echo "Case 5b: empty --reviewer-file path"
dir5b="$TMPDIR_BASE/case5b"
mkdir -p "$dir5b"
output5b="$dir5b/out.log"
"$SCRIPT" --reviewer-file "" --structured-record "$RECORD" --output "$output5b"
assert_contains "5b: structured record present" "$output5b" "## Structured collector record"
assert_contains "5b: no-path placeholder" "$output5b" "(no path provided)"
assert_not_contains "5b: no diag section" "$output5b" "## Reviewer stderr"
assert_nonempty_file "5b: output guaranteed non-empty" "$output5b"

# ── Case 6: empty --structured-record → exit 2 ───────────────────────────────
echo "Case 6: empty --structured-record"
dir6="$TMPDIR_BASE/case6"
mkdir -p "$dir6"
output6="$dir6/out.log"
err6="$dir6/err.log"
rc6=0
"$SCRIPT" --reviewer-file "/dev/null" --structured-record "" --output "$output6" 2>"$err6" || rc6=$?
assert_rc "6: exit 2 on empty record" "$rc6" "2"
if [ ! -e "$output6" ]; then
    ok "6: output file not created on failure"
else
    fail "6: output file must not exist when script exits non-zero"
fi

# ── Case 7: missing --output → exit 2 ────────────────────────────────────────
echo "Case 7: missing --output"
err7="$TMPDIR_BASE/err7.log"
rc7=0
"$SCRIPT" --reviewer-file "/dev/null" --structured-record "$RECORD" 2>"$err7" || rc7=$?
assert_rc "7: exit 2 on missing --output" "$rc7" "2"

# ── Case 8: --output parent missing → exit 2 ─────────────────────────────────
echo "Case 8: --output parent missing"
err8="$TMPDIR_BASE/err8.log"
rc8=0
"$SCRIPT" --reviewer-file "/dev/null" \
    --structured-record "$RECORD" \
    --output "/nonexistent-dir-$(date +%s)/out.log" 2>"$err8" || rc8=$?
assert_rc "8: exit 2 on missing parent dir" "$rc8" "2"

# ── Case 9: atomic write — output not created on empty structured-record ──────
# Simulates partial write by checking that a failed invocation does not leave
# the output file at the --output path (only the mktemp file, which is cleaned
# up on exit). We confirm by checking the target path is absent after exit 2.
echo "Case 9: atomic write safety"
dir9="$TMPDIR_BASE/case9"
mkdir -p "$dir9"
output9="$dir9/out.log"
rc9=0
"$SCRIPT" --reviewer-file "/dev/null" --structured-record "" --output "$output9" 2>/dev/null || rc9=$?
assert_rc "9: exit 2 on invalid args" "$rc9" "2"
if [ ! -e "$output9" ]; then
    ok "9: output path not created on failure"
else
    fail "9: output path must not exist when script exits non-zero"
fi

# ── Case 10: output guaranteed non-empty for cases 1-5 (aggregated) ───────────
# Covered individually above; add one explicit check for the key invariant.
echo "Case 10: non-empty output invariant for all valid cases"
for f in "$output1" "$output2" "$output3" "$output4" "$output5" "$output5b"; do
    assert_nonempty_file "10: non-empty: $f" "$f"
done

echo ""
echo "Results: $PASS_COUNT passed, $FAIL_COUNT failed"
[ "$FAIL_COUNT" -eq 0 ]
