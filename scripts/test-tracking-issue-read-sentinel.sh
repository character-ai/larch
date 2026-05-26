#!/usr/bin/env bash
# test-tracking-issue-read-sentinel.sh — regression harness for
# scripts/tracking-issue-read.sh's --sentinel branch.
#
# Pins the ISSUE_NUMBER=, RUN_ID=, and ADOPTED= field contracts defined
# by issue #359 for Phase 3 consumption, including --issue argv
# validation. Coverage includes allowed values, absence semantics (empty
# == unusable, NEVER false), parser behavior (column-0 keys only, first
# match wins, BOM stripping, trailing \r stripping, other trailing
# whitespace preserved), exact three-line success / failure stdout
# envelopes on sentinel paths, and one stubbed issue-read case that
# proves stable `<!-- larch:diagrams v1 -->` comments are filtered from
# TASK_FILE.
#
# Structure mirrors the shared-helpers pattern of
# scripts/test-tracking-issue-write.sh (set -euo pipefail, REPO_ROOT,
# assert_* helpers, mktemp sandbox, PASS/FAIL accounting). No gh stub
# needed — --sentinel mode is purely local.
#
# Usage:
#   bash scripts/test-tracking-issue-read-sentinel.sh
#
# Exit codes:
#   0 — all assertions passed
#   1 — any assertion failed (summary at EOF)
#
# Conventions: Bash 3.2-safe.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
READ_SCRIPT="$REPO_ROOT/scripts/tracking-issue-read.sh"

if [[ ! -x "$READ_SCRIPT" ]]; then
    echo "FAIL: $READ_SCRIPT not found or not executable" >&2
    exit 1
fi

PASS=0
FAIL=0
FAILED_TESTS=()

# On assertion failure, also surface LAST_STDERR (set by run_sentinel)
# so any regression that emits unexpected warnings / errors to stderr is
# visible in local debug output and CI logs.
print_stderr_if_any() {
    if [[ -n "${LAST_STDERR:-}" ]]; then
        echo "       stderr: $(printf '%q' "$LAST_STDERR")" >&2
    fi
}

assert_equal_stdout() {
    local actual="$1" expected="$2" label="$3"
    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label")
        echo "  FAIL: $label" >&2
        echo "       expected (quoted): $(printf '%q' "$expected")" >&2
        echo "       actual   (quoted): $(printf '%q' "$actual")" >&2
        print_stderr_if_any
    fi
}

assert_equal_exit() {
    local actual="$1" expected="$2" label="$3"
    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label")
        echo "  FAIL: $label (expected exit $expected, got $actual)" >&2
        print_stderr_if_any
    fi
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label")
        echo "  FAIL: $label (missing needle: $needle)" >&2
        echo "       haystack: $(printf '%q' "$haystack")" >&2
        print_stderr_if_any
    fi
}

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label")
        echo "  FAIL: $label (unexpected needle: $needle)" >&2
        echo "       haystack: $(printf '%q' "$haystack")" >&2
        print_stderr_if_any
    fi
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/test-tracking-issue-read-sentinel-XXXXXX")
# shellcheck disable=SC2317
trap 'rm -rf "$TMPROOT"' EXIT

# Helper: invoke --sentinel and capture stdout + exit code + stderr.
# Sets globals LAST_STDOUT, LAST_STDERR, and LAST_EXIT for the caller to
# assert against. Stderr is captured (not dropped) so regressions that
# emit unexpected warnings remain visible in local debugging and in CI
# --verbose logs.
run_sentinel() {
    local sentinel_path="$1"
    local stderr_file
    stderr_file=$(mktemp "${TMPROOT}/stderr-XXXXXX")
    LAST_STDOUT=""
    LAST_STDERR=""
    LAST_EXIT=0
    LAST_STDOUT=$(bash "$READ_SCRIPT" --sentinel "$sentinel_path" 2>"$stderr_file") || LAST_EXIT=$?
    LAST_EXIT="${LAST_EXIT:-0}"
    LAST_STDERR=$(cat "$stderr_file")
    rm -f "$stderr_file"
}

run_read_args() {
    local stderr_file
    stderr_file=$(mktemp "${TMPROOT}/stderr-XXXXXX")
    LAST_STDOUT=""
    LAST_STDERR=""
    LAST_EXIT=0
    LAST_STDOUT=$(bash "$READ_SCRIPT" "$@" 2>"$stderr_file") || LAST_EXIT=$?
    LAST_EXIT="${LAST_EXIT:-0}"
    LAST_STDERR=$(cat "$stderr_file")
    rm -f "$stderr_file"
}

run_issue_read_with_stub() {
    local stub_dir="$1" out_dir="$2" mode="${3:-stable}" stderr_file body_json
    mkdir -p "$stub_dir" "$out_dir"
    if [[ "$mode" == "legacy" ]]; then
        body_json='{"id":101,"body":"<!-- larch:diagrams v1 runid=old -->\n## Code Flow Diagram\n\n```mermaid\ngraph TD\n  A --> B\n```"}'
    else
        body_json='{"id":101,"body":"<!-- larch:diagrams v1 -->\n## Code Flow Diagram\n\n```mermaid\ngraph TD\n  A --> B\n```"}'
    fi
    cat > "$stub_dir/gh" <<GHSTUB
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "api" && "${2:-}" == "/repos/owner/repo/issues/7" ]]; then
    printf 'Issue body\n'
    exit 0
fi
if [[ "${1:-}" == "api" && "${2:-}" == "/repos/owner/repo/issues/7/comments" ]]; then
    cat <<'EOF'
$body_json
{"id":102,"body":"operator comment"}
EOF
    exit 0
fi
exit 1
GHSTUB
    chmod +x "$stub_dir/gh"
    LAST_STDOUT=""
    LAST_STDERR=""
    LAST_EXIT=0
    stderr_file=$(mktemp "${TMPROOT}/stderr-XXXXXX")
    LAST_STDOUT=$(PATH="$stub_dir:$PATH" bash "$READ_SCRIPT" --issue 7 --out-dir "$out_dir" --repo owner/repo 2>"$stderr_file") || LAST_EXIT=$?
    LAST_EXIT="${LAST_EXIT:-0}"
    LAST_STDERR=$(cat "$stderr_file")
    rm -f "$stderr_file"
}

# ---------------------------------------------------------------------------
# (a) ADOPTED=true only
echo "(a) ADOPTED=true — exact stdout"
F="$TMPROOT/a.md"
printf 'ADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(a) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=\nRUN_ID=\nADOPTED=true')" "(a) stdout"

# (b) ADOPTED=false only
echo "(b) ADOPTED=false — exact stdout"
F="$TMPROOT/b.md"
printf 'ADOPTED=false\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(b) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=\nRUN_ID=\nADOPTED=false')" "(b) stdout"

# (c) empty file → all three keys absent from source; keys still emitted with empty values
echo "(c) empty file — all values empty (keys still emitted with empty value)"
F="$TMPROOT/c.md"
: > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(c) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=\nRUN_ID=\nADOPTED=')" "(c) stdout"

# (d) ADOPTED= (explicit empty) → same stdout as (c)
echo "(d) ADOPTED= (explicit empty)"
F="$TMPROOT/d.md"
printf 'ADOPTED=\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(d) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=\nRUN_ID=\nADOPTED=')" "(d) stdout"

# (e) ADOPTED=yes → invalid, exit 1, exact envelope
echo "(e) ADOPTED=yes — invalid"
F="$TMPROOT/e.md"
printf 'ADOPTED=yes\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(e) exit 1"
assert_equal_stdout "$LAST_STDOUT" "$(printf "FAILED=true\nERROR=invalid ADOPTED value in sentinel: ADOPTED: 'malformed-value-omitted'")" "(e) stdout fixed-token envelope"
assert_not_contains "$LAST_STDOUT" "'yes'" "(e) stdout omits quoted malformed value"
assert_not_contains "$LAST_STDOUT" "ADOPTED=yes" "(e) stdout omits raw rejected token"

# (f) ADOPTED=TRUE → case-strict rejection
echo "(f) ADOPTED=TRUE — case-strict reject"
F="$TMPROOT/f.md"
printf 'ADOPTED=TRUE\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(f) exit 1"
assert_equal_stdout "$LAST_STDOUT" "$(printf "FAILED=true\nERROR=invalid ADOPTED value in sentinel: ADOPTED: 'malformed-value-omitted'")" "(f) stdout fixed-token envelope"
assert_not_contains "$LAST_STDOUT" "'TRUE'" "(f) stdout omits quoted rejected value"
assert_not_contains "$LAST_STDOUT" "ADOPTED=TRUE" "(f) stdout omits raw rejected token"

# (g) ADOPTED=1 → numeric rejection
echo "(g) ADOPTED=1 — numeric reject"
F="$TMPROOT/g.md"
printf 'ADOPTED=1\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(g) exit 1"
assert_equal_stdout "$LAST_STDOUT" "$(printf "FAILED=true\nERROR=invalid ADOPTED value in sentinel: ADOPTED: 'malformed-value-omitted'")" "(g) stdout fixed-token envelope"
assert_not_contains "$LAST_STDOUT" "'1'" "(g) stdout omits quoted rejected value"
assert_not_contains "$LAST_STDOUT" "ADOPTED=1" "(g) stdout omits raw rejected token"

# (h) ADOPTED=true (trailing space, no \r) → rejected
echo "(h) ADOPTED=true␠ — trailing space reject"
F="$TMPROOT/h.md"
printf 'ADOPTED=true \n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(h) exit 1"
assert_equal_stdout "$LAST_STDOUT" "$(printf "FAILED=true\nERROR=invalid ADOPTED value in sentinel: ADOPTED: 'malformed-value-omitted'")" "(h) stdout fixed-token envelope"
assert_not_contains "$LAST_STDOUT" "'true '" "(h) stdout omits quoted rejected value"
assert_not_contains "$LAST_STDOUT" "ADOPTED=true " "(h) stdout omits raw rejected token"

# (i) sentinel file not found
echo "(i) sentinel file not found"
F="$TMPROOT/does-not-exist.md"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(i) exit 1"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'FAILED=true\nERROR=sentinel file not found: %s' "$F")" "(i) stdout"

# (j) all three keys valid (no RUN_ID in file)
echo "(j) all three keys valid (no RUN_ID)"
F="$TMPROOT/j.md"
printf 'ISSUE_NUMBER=123\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(j) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=123\nRUN_ID=\nADOPTED=true')" "(j) stdout"

# (j2) all three keys valid with non-empty RUN_ID
echo "(j2) all three keys valid with non-empty RUN_ID"
F="$TMPROOT/j2.md"
printf 'ISSUE_NUMBER=456\nRUN_ID=abc123\nADOPTED=false\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(j2) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=456\nRUN_ID=abc123\nADOPTED=false')" "(j2) stdout with RUN_ID"

# (k) duplicate ADOPTED lines — first wins
echo "(k) duplicate ADOPTED — first wins"
F="$TMPROOT/k.md"
printf 'ADOPTED=true\nADOPTED=false\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(k) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=\nRUN_ID=\nADOPTED=true')" "(k) stdout"

# (l) CRLF line endings — \r stripped from value (all three keys)
printf '(l) CRLF line endings -- \\r stripped (all three keys)\n'
F="$TMPROOT/l.md"
printf 'ISSUE_NUMBER=123\r\nADOPTED=true\r\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(l) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=123\nRUN_ID=\nADOPTED=true')" "(l) stdout (all three values \\r-stripped)"

# (m) UTF-8 BOM at start — stripped before parsing
echo "(m) UTF-8 BOM — stripped"
F="$TMPROOT/m.md"
printf '\xef\xbb\xbfISSUE_NUMBER=42\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(m) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=42\nRUN_ID=\nADOPTED=true')" "(m) stdout"

# (n) Leading whitespace — column-0 rule; indented line treated as absent
echo "(n) leading whitespace — column-0 rule"
F="$TMPROOT/n.md"
printf '  ADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(n) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=\nRUN_ID=\nADOPTED=')" "(n) stdout"

# (o) Unreadable sentinel file (mode 000) — fail-closed with envelope.
# Skipped when running as root because chmod 000 does not block root reads
# (root bypasses DAC mode bits on most Unix kernels).
echo "(o) unreadable sentinel — fail-closed with envelope"
if (( EUID == 0 )); then
    echo "  skip: (o) root can read mode-000 files; skipping"
else
    F="$TMPROOT/o.md"
    printf 'ADOPTED=true\n' > "$F"
    chmod 000 "$F"
    run_sentinel "$F"
    chmod 600 "$F"  # restore so EXIT trap can delete
    assert_equal_exit "$LAST_EXIT" "1" "(o) exit 1"
    assert_equal_stdout "$LAST_STDOUT" "$(printf 'FAILED=true\nERROR=sentinel file not readable: %s' "$F")" "(o) stdout envelope"
fi

# (p) ISSUE_NUMBER=abc — invalid, fixed-token no-echo envelope
echo "(p) ISSUE_NUMBER=abc — non-numeric reject"
F="$TMPROOT/p.md"
printf 'ISSUE_NUMBER=abc\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(p) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(p) stdout FAILED"
assert_contains "$LAST_STDOUT" "ERROR=invalid ISSUE_NUMBER in sentinel: ISSUE_NUMBER: 'malformed-value-omitted'" "(p) stdout fixed-token error"
assert_not_contains "$LAST_STDOUT" "abc" "(p) stdout omits malformed value"

# (q) ISSUE_NUMBER=12.3 — decimal rejected
echo "(q) ISSUE_NUMBER=12.3 — decimal reject"
F="$TMPROOT/q.md"
printf 'ISSUE_NUMBER=12.3\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(q) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(q) stdout FAILED"
assert_contains "$LAST_STDOUT" "ERROR=invalid ISSUE_NUMBER in sentinel: ISSUE_NUMBER: 'malformed-value-omitted'" "(q) stdout fixed-token error"
assert_not_contains "$LAST_STDOUT" "12.3" "(q) stdout omits malformed value"

# (r) ISSUE_NUMBER= explicit empty — pass-through remains empty
echo "(r) ISSUE_NUMBER= explicit empty — pass-through"
F="$TMPROOT/r.md"
printf 'ISSUE_NUMBER=\nRUN_ID=run-ok\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(r) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=\nRUN_ID=run-ok\nADOPTED=true')" "(r) stdout"

# (s) missing ISSUE_NUMBER key — pass-through remains empty
echo "(s) missing ISSUE_NUMBER — pass-through"
F="$TMPROOT/s.md"
printf 'RUN_ID=run-ok\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(s) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=\nRUN_ID=run-ok\nADOPTED=true')" "(s) stdout"

# (t) RUN_ID with embedded space — invalid and no verbatim echo
echo "(t) RUN_ID=has space — charset reject"
F="$TMPROOT/t.md"
printf 'ISSUE_NUMBER=42\nRUN_ID=has space\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(t) exit 1"
assert_contains "$LAST_STDOUT" "ERROR=invalid RUN_ID in sentinel: RUN_ID: 'malformed-value-omitted'" "(t) stdout fixed-token error"
assert_not_contains "$LAST_STDOUT" "has space" "(t) stdout omits malformed value"

# (u) RUN_ID with slash — invalid and no verbatim echo
echo "(u) RUN_ID=path/traversal — charset reject"
F="$TMPROOT/u.md"
printf 'ISSUE_NUMBER=42\nRUN_ID=path/traversal\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(u) exit 1"
assert_contains "$LAST_STDOUT" "ERROR=invalid RUN_ID in sentinel: RUN_ID: 'malformed-value-omitted'" "(u) stdout fixed-token error"
assert_not_contains "$LAST_STDOUT" "path/traversal" "(u) stdout omits malformed value"

# (v) RUN_ID with embedded tab — invalid same-line byte
echo "(v) RUN_ID with embedded tab — charset reject"
F="$TMPROOT/v.md"
printf 'ISSUE_NUMBER=42\nRUN_ID=tab\there\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(v) exit 1"
assert_contains "$LAST_STDOUT" "ERROR=invalid RUN_ID in sentinel: RUN_ID: 'malformed-value-omitted'" "(v) stdout fixed-token error"
assert_not_contains "$LAST_STDOUT" $'tab\there' "(v) stdout omits malformed value"

# (w) RUN_ID with non-trailing CR — invalid same-line byte
echo "(w) RUN_ID with non-trailing CR — charset reject"
F="$TMPROOT/w.md"
printf 'ISSUE_NUMBER=42\nRUN_ID=cr\rinjected\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "1" "(w) exit 1"
assert_contains "$LAST_STDOUT" "ERROR=invalid RUN_ID in sentinel: RUN_ID: 'malformed-value-omitted'" "(w) stdout fixed-token error"
assert_not_contains "$LAST_STDOUT" $'cr\rinjected' "(w) stdout omits malformed value"

# (x) RUN_ID= explicit empty — pass-through remains empty
echo "(x) RUN_ID= explicit empty — pass-through"
F="$TMPROOT/x.md"
printf 'ISSUE_NUMBER=42\nRUN_ID=\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(x) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=42\nRUN_ID=\nADOPTED=true')" "(x) stdout"

# (y) missing RUN_ID key — pass-through remains empty
echo "(y) missing RUN_ID — pass-through"
F="$TMPROOT/y.md"
printf 'ISSUE_NUMBER=42\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(y) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=42\nRUN_ID=\nADOPTED=true')" "(y) stdout"

# (z) Valid three-key sentinel with expanded RUN_ID charset
echo "(z) valid ISSUE_NUMBER + RUN_ID + ADOPTED — three-line success"
F="$TMPROOT/z.md"
printf 'ISSUE_NUMBER=42\nRUN_ID=run-1.0_test-abc\nADOPTED=true\n' > "$F"
run_sentinel "$F"
assert_equal_exit "$LAST_EXIT" "0" "(z) exit 0"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'ISSUE_NUMBER=42\nRUN_ID=run-1.0_test-abc\nADOPTED=true')" "(z) stdout"

# (aa) argv --issue validation fires before out-dir / gh work
echo "(aa) argv --issue=abc — usage reject"
run_read_args --issue abc --out-dir "$TMPROOT/no-such-dir"
assert_equal_exit "$LAST_EXIT" "1" "(aa) exit 1"
assert_equal_stdout "$LAST_STDOUT" "$(printf 'FAILED=true\nERROR=usage: --issue must be numeric')" "(aa) stdout"

# (ab) Stable larch:diagrams summary comment is filtered from issue reads
echo "(ab) stable larch:diagrams comments are skipped from TASK_FILE"
run_issue_read_with_stub "$TMPROOT/stub-ab" "$TMPROOT/out-ab"
assert_equal_exit "$LAST_EXIT" "0" "(ab) exit 0"
assert_contains "$LAST_STDOUT" "TASK_SOURCE=issue-only" "(ab) stdout task source"
task_file=$(printf '%s\n' "$LAST_STDOUT" | awk -F= '$1=="TASK_FILE"{print substr($0, index($0, "=") + 1); exit}')
task_body=$(cat "$task_file" 2>/dev/null || true)
assert_contains "$task_body" '<external_issue_comment id="102">' "(ab) task file keeps normal comment"
assert_not_contains "$task_body" '<external_issue_comment id="101">' "(ab) task file skips stable diagrams comment"
assert_not_contains "$task_body" '<!-- larch:diagrams v1 -->' "(ab) task file omits stable marker payload"

# (ac) Legacy runid-bearing larch:diagrams summary comment is also filtered
echo "(ac) legacy larch:diagrams comments are skipped from TASK_FILE"
run_issue_read_with_stub "$TMPROOT/stub-ac" "$TMPROOT/out-ac" legacy
assert_equal_exit "$LAST_EXIT" "0" "(ac) exit 0"
assert_contains "$LAST_STDOUT" "TASK_SOURCE=issue-only" "(ac) stdout task source"
task_file=$(printf '%s\n' "$LAST_STDOUT" | awk -F= '$1=="TASK_FILE"{print substr($0, index($0, "=") + 1); exit}')
task_body=$(cat "$task_file" 2>/dev/null || true)
assert_contains "$task_body" '<external_issue_comment id="102">' "(ac) task file keeps normal comment"
assert_not_contains "$task_body" '<external_issue_comment id="101">' "(ac) task file skips legacy diagrams comment"
assert_not_contains "$task_body" 'runid=old' "(ac) task file omits legacy marker payload"

# ---------------------------------------------------------------------------
# Summary
echo
echo "=========================================="
echo "Passed: $PASS"
echo "Failed: $FAIL"
if (( FAIL > 0 )); then
    echo "Failed tests:"
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t"
    done
    exit 1
fi
echo "All assertions passed."
