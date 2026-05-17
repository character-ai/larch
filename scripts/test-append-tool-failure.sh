#!/usr/bin/env bash
# test-append-tool-failure.sh — Regression tests for append-tool-failure.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/append-tool-failure.sh"
TMPDIR_BASE="$(mktemp -d "${TMPDIR:-/tmp}/test-append-tool-failure.XXXXXX")"
PASS_COUNT=0
FAIL_COUNT=0

cleanup() {
    rm -rf "$TMPDIR_BASE"
}
trap cleanup EXIT

ok() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

assert_contains() {
    local label=$1 file=$2 needle=$3
    if grep -Fq -- "$needle" "$file"; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    /' "$file" || true
    fi
}

assert_not_contains() {
    local label=$1 file=$2 needle=$3
    if grep -Fq -- "$needle" "$file"; then
        fail "$label"
        sed 's/^/    /' "$file" || true
    else
        ok "$label"
    fi
}

assert_rc() {
    local label=$1 actual=$2 expected=$3
    if [ "$actual" = "$expected" ]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
    fi
}

extract_first_fence() {
    awk '
        /^  ```$/ {
            fence++
            if (fence == 2) exit
            next
        }
        fence == 1 { print }
    ' "$1"
}

log="$TMPDIR_BASE/execution-issues.md"
input="$TMPDIR_BASE/single.txt"
printf 'fatal: single line error\n' > "$input"
"$SCRIPT" --log "$log" --site "9b" --tool "create-pr.sh" --exit-code 1 --category "Tool Failures" --output-file "$input" >/dev/null
assert_contains "single-line: header" "$log" "### Tool Failures"
assert_contains "single-line: bullet" "$log" "- **Step 9b — create-pr.sh failed (exit 1)**:"
assert_contains "single-line: exact body" "$log" "fatal: single line error"

input="$TMPDIR_BASE/multiline.txt"
printf 'line one\nline two\nline three\n' > "$input"
"$SCRIPT" --log "$log" --site "review" --tool "collect-agent-results.sh" --exit-code 124 --category "External Reviewer Issues" --output-file "$input" >/dev/null
assert_contains "multi-line: category" "$log" "### External Reviewer Issues"
assert_contains "multi-line: body line one" "$log" "line one"
assert_contains "multi-line: body line three" "$log" "line three"

large="$TMPDIR_BASE/large.txt"
awk 'BEGIN { for (i = 0; i < 1024; i++) print "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" }' > "$large"
large_log="$TMPDIR_BASE/large-log.md"
"$SCRIPT" --log "$large_log" --site "7a" --tool "diagram-generator" --exit-code 2 --category "Warnings" --output-file "$large" >/dev/null
extract_first_fence "$large_log" > "$TMPDIR_BASE/large-extracted.txt"
if cmp -s "$large" "$TMPDIR_BASE/large-extracted.txt"; then
    ok "large content: byte-exact preservation"
else
    fail "large content: byte-exact preservation"
fi

for category in "Tool Failures" "External Reviewer Issues" "CI Issues" "Warnings"; do
    cat_log="$TMPDIR_BASE/category-$category.md"
    printf 'body for %s\n' "$category" > "$TMPDIR_BASE/category-input.txt"
    "$SCRIPT" --log "$cat_log" --site "site" --tool "tool" --exit-code 9 --category "$category" --output-file "$TMPDIR_BASE/category-input.txt" >/dev/null
    assert_contains "category routing: $category" "$cat_log" "### $category"
done

verdict_input="$TMPDIR_BASE/verdict-input.txt"
printf 'auth failure\n' > "$verdict_input"
verdict_log="$TMPDIR_BASE/verdict-log.md"
"$SCRIPT" --log "$verdict_log" --site "2" --tool "codex-implement" --exit-code 1 --category "Tool Failures" --output-file "$verdict_input" --verdict "auth-retries-exhausted" >/dev/null
assert_contains "verdict: header suffix" "$verdict_log" "- **Step 2 — codex-implement failed (exit 1 — auth-retries-exhausted)**:"

retry_log="$TMPDIR_BASE/retry-log.md"
"$SCRIPT" --log "$retry_log" --site "2" --tool "cursor-implement" --exit-code 2 --category "Tool Failures" --output-file "$verdict_input" --retry-count 5 >/dev/null
assert_contains "retry-count: header suffix" "$retry_log" "- **Step 2 — cursor-implement failed (exit 2 — retries=5)**:"

combined_log="$TMPDIR_BASE/combined-log.md"
"$SCRIPT" --log "$combined_log" --site "review Step 2" --tool "cursor-review" --exit-code 99 --category "External Reviewer Issues" --output-file "$verdict_input" --verdict "non-auth" --retry-count 1 >/dev/null
assert_contains "verdict and retry-count: header suffix" "$combined_log" "- **Step review Step 2 — cursor-review failed (exit 99 — non-auth — retries=1)**:"

warning_log="$TMPDIR_BASE/warning-log.md"
"$SCRIPT" --log "$warning_log" --site "review Step 3a tsv-fallback" --tool "collect-findings.sh inline-TSV recovery" --exit-code 0 --status-label "warning" --category "External Reviewer Issues" --output-file "$verdict_input" >/dev/null
assert_contains "status-label: warning wording" "$warning_log" "- **Step review Step 3a tsv-fallback — collect-findings.sh inline-TSV recovery warning (exit 0)**:"

set +e
bad_retry_out=$("$SCRIPT" --log "$TMPDIR_BASE/bad-retry-log.md" --site "2" --tool "tool" --exit-code 1 --category "Tool Failures" --output-file "$verdict_input" --retry-count nope 2>&1)
bad_retry_rc=$?
set -e
assert_rc "retry-count: invalid value exits non-zero" "$bad_retry_rc" 1
printf '%s\n' "$bad_retry_out" > "$TMPDIR_BASE/bad-retry-out.txt"
assert_contains "retry-count: invalid value diagnostic" "$TMPDIR_BASE/bad-retry-out.txt" "ERROR=usage: --retry-count must be a non-negative integer"

redact_input="$TMPDIR_BASE/redact.txt"
redact_log="$TMPDIR_BASE/redact-log.md"
secret_token="ghp_""123456789012""345678901234""567890123456"
printf 'token %s\nsafe text\n' "$secret_token" > "$redact_input"
"$SCRIPT" --log "$redact_log" --site "redact" --tool "secret-tool" --exit-code 1 --category "Tool Failures" --output-file "$redact_input" --redact >/dev/null
assert_contains "redaction: token replaced" "$redact_log" "<REDACTED-TOKEN>"
assert_contains "redaction: non-secret preserved" "$redact_log" "safe text"
assert_not_contains "redaction: raw token absent" "$redact_log" "$secret_token"

missing_log="$TMPDIR_BASE/missing-log.md"
printf 'unchanged\n' > "$missing_log"
set +e
missing_out=$("$SCRIPT" --log "$missing_log" --site "missing" --tool "tool" --exit-code 1 --category "Tool Failures" --output-file "$TMPDIR_BASE/does-not-exist" 2>&1)
missing_rc=$?
set -e
assert_rc "missing input: exits non-zero" "$missing_rc" 2
printf '%s\n' "$missing_out" > "$TMPDIR_BASE/missing-out.txt"
assert_contains "missing input: diagnostic" "$TMPDIR_BASE/missing-out.txt" "FAILED=true"
if [ "$(cat "$missing_log")" = "unchanged" ]; then
    ok "missing input: log unchanged"
else
    fail "missing input: log unchanged"
fi

atomic_log="$TMPDIR_BASE/atomic-log.md"
printf 'original\n' > "$atomic_log"
printf 'captured\n' > "$TMPDIR_BASE/atomic-input.txt"
stubbin="$TMPDIR_BASE/stubbin"
mkdir -p "$stubbin"
cat > "$stubbin/awk" <<'SH'
#!/usr/bin/env bash
exit 99
SH
chmod +x "$stubbin/awk"
set +e
PATH="$stubbin:$PATH" "$SCRIPT" --log "$atomic_log" --site "atomic" --tool "tool" --exit-code 1 --category "Tool Failures" --output-file "$TMPDIR_BASE/atomic-input.txt" >/dev/null 2>&1
atomic_rc=$?
set -e
if [ "$atomic_rc" -ne 0 ] && [ "$(cat "$atomic_log")" = "original" ]; then
    ok "delegate failure: log unchanged"
else
    fail "delegate failure: log unchanged"
fi

if [ "$FAIL_COUNT" -ne 0 ]; then
    echo "test-append-tool-failure: $FAIL_COUNT failure(s), $PASS_COUNT pass(es)" >&2
    exit 1
fi
echo "test-append-tool-failure: $PASS_COUNT pass(es)"
