#!/usr/bin/env bash
# Regression harness for scripts/get-issue-state.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/get-issue-state.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-get-issue-state.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0
FAILED_TESTS=()

fail_test() {
    local label="$1" detail="$2"
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("$label")
    echo "  FAIL: $label" >&2
    echo "       $detail" >&2
}

pass_test() {
    local label="$1"
    PASS=$((PASS + 1))
    echo "  ok: $label"
}

assert_exit() {
    local actual="$1" expected="$2" label="$3"
    if [[ "$actual" == "$expected" ]]; then
        pass_test "$label"
    else
        fail_test "$label" "expected exit $expected, got $actual"
    fi
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass_test "$label"
    else
        fail_test "$label" "missing needle: $needle; haystack: $(printf '%q' "$haystack")"
    fi
}

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        pass_test "$label"
    else
        fail_test "$label" "unexpected needle: $needle; haystack: $(printf '%q' "$haystack")"
    fi
}

stub_dir="$TMPROOT/bin"
mkdir -p "$stub_dir"
cat > "$stub_dir/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${GH_LOG:?}"
if [[ "$1 $2" != "issue view" ]]; then
    echo "unexpected gh command" >&2
    exit 2
fi
if [[ "${GH_STUB_MODE:-failure}" == "success" ]]; then
    printf "OPEN\thttps://example.test/issues/12\n"
else
    echo "stub issue view failed" >&2
    exit 1
fi
GH
chmod +x "$stub_dir/gh"
STUB_MODE=failure

run_script() {
    local label="$1"
    shift
    LAST_STDOUT=""
    LAST_EXIT=0
    set +e
    LAST_STDOUT=$(GH_LOG="$TMPROOT/$label-gh.log" GH_STUB_MODE="$STUB_MODE" PATH="$stub_dir:$PATH" "$SCRIPT" "$@" 2>"$TMPROOT/$label.err")
    LAST_EXIT=$?
    set -e
}

echo "(a) missing --issue"
run_script missing --repo upstream/repo
assert_exit "$LAST_EXIT" "1" "(a) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(a) FAILED envelope"
assert_contains "$LAST_STDOUT" "ERROR=--issue is required" "(a) preserved missing-arg error"

echo "(b) non-numeric --issue"
run_script alpha --issue abc --repo upstream/repo
assert_exit "$LAST_EXIT" "1" "(b) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(b) FAILED envelope"
assert_contains "$LAST_STDOUT" "ERROR=--issue must be numeric" "(b) numeric validation"

echo "(c) embedded space in --issue"
run_script space --issue "1 2" --repo upstream/repo
assert_exit "$LAST_EXIT" "1" "(c) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(c) FAILED envelope"
assert_contains "$LAST_STDOUT" "ERROR=--issue must be numeric" "(c) numeric validation"

echo "(d) embedded dash in --issue"
run_script dash --issue "1-2" --repo upstream/repo
assert_exit "$LAST_EXIT" "1" "(d) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(d) FAILED envelope"
assert_contains "$LAST_STDOUT" "ERROR=--issue must be numeric" "(d) numeric validation"

echo "(e) numeric zero reaches gh"
run_script zero --issue 0 --repo upstream/repo
assert_exit "$LAST_EXIT" "1" "(e) exit 1 from gh stub"
assert_contains "$LAST_STDOUT" "FAILED=true" "(e) FAILED envelope"
assert_contains "$LAST_STDOUT" "ERROR=gh issue view failed: stub issue view failed" "(e) numeric zero passed validator"
assert_not_contains "$LAST_STDOUT" "--issue must be numeric" "(e) no numeric-validation failure"

echo "(f) numeric issue with gh failure"
run_script gh_fail --issue 12 --repo upstream/repo
assert_exit "$LAST_EXIT" "1" "(f) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(f) FAILED envelope"
assert_contains "$LAST_STDOUT" "ERROR=gh issue view failed: stub issue view failed" "(f) gh failure envelope"

echo "(g) numeric issue with gh success"
STUB_MODE=success
run_script gh_success --issue 12 --repo upstream/repo
assert_exit "$LAST_EXIT" "0" "(g) exit 0"
assert_contains "$LAST_STDOUT" "STATE=OPEN" "(g) state emitted"
assert_contains "$LAST_STDOUT" "URL=https://example.test/issues/12" "(g) url emitted"
assert_contains "$LAST_STDOUT" "IS_PR=false" "(g) issue url classified as non-PR"

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
