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

run_script_timeout() {
    local label="$1"
    shift
    LAST_STDOUT=""
    LAST_STDERR=""
    LAST_EXIT=0
    local out_file="$TMPROOT/$label.out" err_file="$TMPROOT/$label.err"
    set +e
    GH_LOG="$TMPROOT/$label-gh.log" GH_STUB_MODE="$STUB_MODE" PATH="$stub_dir:$PATH" \
        python3 - "$SCRIPT" "$out_file" "$err_file" "$@" <<'PYEOF'
import os
import subprocess
import sys

script, out_file, err_file, *argv = sys.argv[1:]
with open(out_file, "wb") as out, open(err_file, "wb") as err:
    try:
        proc = subprocess.run([script, *argv], stdout=out, stderr=err, timeout=5, env=os.environ.copy())
        raise SystemExit(proc.returncode)
    except subprocess.TimeoutExpired:
        err.write(b"timeout after 5s\n")
        raise SystemExit(124)
PYEOF
    LAST_EXIT=$?
    set -e
    LAST_STDOUT=$(cat "$out_file" 2>/dev/null || true)
    LAST_STDERR=$(cat "$err_file" 2>/dev/null || true)
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

STUB_MODE=failure

echo "(h) --issue with no value as final argv"
run_script_timeout issue_missing_value --issue
assert_exit "$LAST_EXIT" "1" "(h) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(h) FAILED envelope"
assert_contains "$LAST_STDOUT" "ERROR=--issue requires a value" "(h) value-required error"
assert_not_contains "$LAST_STDERR" "shift" "(h) no shift-error spam"

echo "(i) --repo with no value as final argv"
run_script_timeout repo_missing_value --issue 12 --repo
assert_exit "$LAST_EXIT" "1" "(i) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(i) FAILED envelope"
assert_contains "$LAST_STDOUT" "ERROR=--repo requires a value" "(i) value-required error"
assert_not_contains "$LAST_STDERR" "shift" "(i) no shift-error spam"

echo "(j) --issue with flag-looking next token"
run_script_timeout issue_flag_value --issue --repo upstream/repo
assert_exit "$LAST_EXIT" "1" "(j) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(j) FAILED envelope"
assert_contains "$LAST_STDOUT" "ERROR=--issue requires a value" "(j) flag-looking value rejected"

echo "(k) --repo with flag-looking next token"
run_script_timeout repo_flag_value --issue 12 --repo --some-flag
assert_exit "$LAST_EXIT" "1" "(k) exit 1"
assert_contains "$LAST_STDOUT" "FAILED=true" "(k) FAILED envelope"
assert_contains "$LAST_STDOUT" "ERROR=--repo requires a value" "(k) flag-looking value rejected"

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
