#!/usr/bin/env bash
# test-refresh-anchor.sh — sibling regression harness for refresh-anchor.sh.
#
# Strategy: invoke refresh-anchor.sh with PATH pointing at a stub
# tracking-issue-write.sh (real `gh` calls are out of scope for unit tests).
# The wrapper invokes its sibling scripts via SCRIPT_DIR, so we shadow only
# tracking-issue-write.sh by renaming the real one inside a sandboxed copy
# of the scripts directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_REFRESH="$SCRIPT_DIR/refresh-anchor.sh"
REAL_ASSEMBLE="$SCRIPT_DIR/assemble-anchor.sh"
REAL_MARKERS="$SCRIPT_DIR/anchor-section-markers.sh"

[ -x "$REAL_REFRESH" ]  || { echo "FAIL: $REAL_REFRESH not executable"; exit 1; }
[ -x "$REAL_ASSEMBLE" ] || { echo "FAIL: $REAL_ASSEMBLE not executable"; exit 1; }
[ -f "$REAL_MARKERS" ]  || { echo "FAIL: $REAL_MARKERS missing"; exit 1; }

PASS=0
FAIL=0

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS+1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL+1))
        echo "FAIL: $label"
        echo "  expected to contain: $needle"
        echo "  got:"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

build_sandbox() {
    # Copy the three real helpers into TMPDIR; replace tracking-issue-write.sh
    # with a stub. Then run refresh-anchor.sh from the sandboxed location so
    # its SCRIPT_DIR resolves to the sandbox.
    local sandbox=$1 stub_body=$2
    mkdir -p "$sandbox"
    cp "$REAL_REFRESH"  "$sandbox/refresh-anchor.sh"
    cp "$REAL_ASSEMBLE" "$sandbox/assemble-anchor.sh"
    cp "$REAL_MARKERS"  "$sandbox/anchor-section-markers.sh"
    chmod +x "$sandbox/refresh-anchor.sh" "$sandbox/assemble-anchor.sh"
    cat > "$sandbox/tracking-issue-write.sh" <<EOF
#!/usr/bin/env bash
$stub_body
EOF
    chmod +x "$sandbox/tracking-issue-write.sh"
}

# ── Test 1: happy path — assemble + upsert both succeed.
TMP1=$(mktemp -d)
trap 'rm -rf "$TMP1"' EXIT
build_sandbox "$TMP1/scripts" '
echo "ANCHOR_COMMENT_ID=12345"
echo "ANCHOR_COMMENT_URL=https://example.test/comment/12345"
echo "UPDATED=false"
exit 0
'
mkdir -p "$TMP1/sections"
echo "stub fragment" > "$TMP1/sections/plan-goals-test.md"
OUT1=$("$TMP1/scripts/refresh-anchor.sh" --sections-dir "$TMP1/sections" --issue 42 2>&1)
RC1=$?
assert_contains "ASSEMBLED=true"        "$OUT1" "happy: assemble envelope forwarded"
assert_contains "ANCHOR_COMMENT_ID=12345" "$OUT1" "happy: upsert envelope forwarded"
assert_contains "UPDATED=false"          "$OUT1" "happy: UPDATED forwarded"
if [ "$RC1" -eq 0 ]; then PASS=$((PASS+1)); echo "PASS: happy: rc=0"; else FAIL=$((FAIL+1)); echo "FAIL: happy: rc=$RC1"; fi
if [ -f "$TMP1/anchor-assembled.md" ]; then PASS=$((PASS+1)); echo "PASS: happy: default --output created"; else FAIL=$((FAIL+1)); echo "FAIL: happy: default output missing"; fi

# ── Test 2: upsert failure — wrapper exits 2 and forwards both envelopes.
TMP2=$(mktemp -d)
trap 'rm -rf "$TMP1" "$TMP2"' EXIT
build_sandbox "$TMP2/scripts" '
echo "FAILED=true"
echo "ERROR=stub gh failure"
exit 1
'
mkdir -p "$TMP2/sections"
echo "stub" > "$TMP2/sections/plan-goals-test.md"
set +e
OUT2=$("$TMP2/scripts/refresh-anchor.sh" --sections-dir "$TMP2/sections" --issue 7 2>&1)
RC2=$?
set -e
assert_contains "ASSEMBLED=true"     "$OUT2" "upsert-fail: assemble envelope forwarded"
assert_contains "FAILED=true"        "$OUT2" "upsert-fail: FAILED envelope forwarded"
assert_contains "stub gh failure"    "$OUT2" "upsert-fail: ERROR forwarded"
if [ "$RC2" -eq 2 ]; then PASS=$((PASS+1)); echo "PASS: upsert-fail: rc=2"; else FAIL=$((FAIL+1)); echo "FAIL: upsert-fail: rc=$RC2"; fi

# ── Test 3: missing required flag — invocation error envelope.
set +e
OUT3=$("$TMP1/scripts/refresh-anchor.sh" --issue 1 2>&1)
RC3=$?
set -e
assert_contains "FAILED=true"            "$OUT3" "no-sections: FAILED emitted"
assert_contains "--sections-dir is required" "$OUT3" "no-sections: usage message"
if [ "$RC3" -eq 1 ]; then PASS=$((PASS+1)); echo "PASS: no-sections: rc=1"; else FAIL=$((FAIL+1)); echo "FAIL: no-sections: rc=$RC3"; fi

# ── Test 4: --anchor-id forwarding to upsert (verify by stub recording argv).
TMP4=$(mktemp -d)
trap 'rm -rf "$TMP1" "$TMP2" "$TMP4"' EXIT
build_sandbox "$TMP4/scripts" '
printf "%s\n" "$@" > "'"$TMP4"'/upsert-argv.txt"
echo "ANCHOR_COMMENT_ID=99"
echo "ANCHOR_COMMENT_URL=u"
echo "UPDATED=true"
exit 0
'
mkdir -p "$TMP4/sections"
echo "stub" > "$TMP4/sections/plan-goals-test.md"
"$TMP4/scripts/refresh-anchor.sh" --sections-dir "$TMP4/sections" --issue 11 --anchor-id ABC123 >/dev/null
ARGV=$(cat "$TMP4/upsert-argv.txt")
assert_contains "--anchor-id" "$ARGV" "anchor-id: forwarded to upsert"
assert_contains "ABC123"      "$ARGV" "anchor-id: value forwarded"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
