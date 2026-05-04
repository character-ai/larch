#!/usr/bin/env bash
# test-list-issues.sh — Regression for skills/issue/scripts/list-issues.sh.
#
# Usage: bash test-list-issues.sh
# Exit 0 on success, non-zero on any failure.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
HELPER="$SCRIPT_DIR/list-issues.sh"
FIXTURE_DIR="$SCRIPT_DIR/fixtures/list-issues"
TMPDIR_TEST=$(mktemp -d -t test-list-issues-XXXXXX)
trap 'rm -rf "$TMPDIR_TEST"' EXIT

PASSED=0
FAILED=0

REAL_PYTHON3=$(command -v python3 || true)
if [[ -z "$REAL_PYTHON3" ]]; then
    echo "ERROR: python3 is required to run this harness" >&2
    exit 1
fi

FIXTURE_RAW="$TMPDIR_TEST/raw.json"
FAKE_BIN="$TMPDIR_TEST/fake-bin"
MARKER_GH="$TMPDIR_TEST/marker.gh"
MARKER_PYTHON3="$TMPDIR_TEST/marker.python3"
MOCK_CUTOFF="2025-04-04"
export FIXTURE_RAW MARKER_GH MARKER_PYTHON3 MOCK_CUTOFF REAL_PYTHON3

mkdir -p "$FAKE_BIN"
cat "$FIXTURE_DIR/page1.json" "$FIXTURE_DIR/page2.json" >"$FIXTURE_RAW"

cat >"$FAKE_BIN/gh" <<'FAKE_GH'
#!/usr/bin/env bash
set -euo pipefail

: "${FIXTURE_RAW:?FIXTURE_RAW is required}"
: "${MARKER_GH:?MARKER_GH is required}"

case "${1:-}" in
    repo)
        if [[ "${2:-}" == "view" ]]; then
            echo "owner/repo"
            exit 0
        fi
        ;;
    api)
        shift
        while [[ $# -gt 0 && "$1" == --* ]]; do
            case "$1" in
                --paginate)
                    shift
                    ;;
                *)
                    echo "fake-gh: unrecognized api flag: $1" >&2
                    exit 1
                    ;;
            esac
        done
        endpoint="${1:-}"
        if [[ "$endpoint" == *"repos/owner/repo/issues?state=all&per_page=100"* ]]; then
            printf x >>"$MARKER_GH"
            cat "$FIXTURE_RAW"
            exit 0
        fi
        ;;
esac

echo "fake-gh: unrecognized invocation: $*" >&2
exit 1
FAKE_GH
chmod +x "$FAKE_BIN/gh"

cat >"$FAKE_BIN/python3" <<'FAKE_PYTHON3'
#!/usr/bin/env bash
set -euo pipefail

: "${MARKER_PYTHON3:?MARKER_PYTHON3 is required}"
: "${MOCK_CUTOFF:?MOCK_CUTOFF is required}"
: "${REAL_PYTHON3:?REAL_PYTHON3 is required}"

if [[ "${1:-}" == "-c" ]]; then
    body="${2:-}"
    if [[ "$body" == *"datetime.timedelta(days="* ]]; then
        # Extract the integer following `days=` and validate it against the
        # harness's EXPECTED_DAYS — guards against a regression that passes
        # the wrong constant (e.g. always 0 or an off-by-one variable) into
        # datetime.timedelta while still keeping the substring intact.
        days_value="${body##*datetime.timedelta(days=}"
        days_value="${days_value%%)*}"
        if [[ -n "${EXPECTED_DAYS:-}" && "$days_value" != "$EXPECTED_DAYS" ]]; then
            echo "fake-python3: days= mismatch (expected $EXPECTED_DAYS, got $days_value)" >&2
            exit 1
        fi
        printf x >>"$MARKER_PYTHON3"
        echo "$MOCK_CUTOFF"
        exit 0
    fi
    echo "fake-python3: unmatched -c body: $body" >&2
    exit 1
fi

exec "$REAL_PYTHON3" "$@"
FAKE_PYTHON3
chmod +x "$FAKE_BIN/python3"

OPEN_EXPECTED=$(cat <<'EXPECTED'
1	Add foo feature	open	https://github.example/owner/repo/issues/1
2	Fix research summary bug	open	https://github.example/owner/repo/issues/2
14	Open with tab and newline and cr	open	https://github.example/owner/repo/issues/14
EXPECTED
)

CLOSED_EXPECTED=$(cat <<'EXPECTED'
1	Add foo feature	open	https://github.example/owner/repo/issues/1
2	Fix research summary bug	open	https://github.example/owner/repo/issues/2
14	Open with tab and newline and cr	open	https://github.example/owner/repo/issues/14
15	Recent closed	closed	https://github.example/owner/repo/issues/15
16	Boundary on cutoff	closed	https://github.example/owner/repo/issues/16
EXPECTED
)

run_helper() {
    local stdout_file stderr_file rc
    stdout_file="$TMPDIR_TEST/stdout.$$"
    stderr_file="$TMPDIR_TEST/stderr.$$"
    # Tell the fake python3 which days= value to require — production
    # passes --closed-window-days through to datetime.timedelta(days=N)
    # verbatim, so the fake validates the propagation rather than just
    # the substring shape.
    EXPECTED_DAYS="$1"
    export EXPECTED_DAYS
    set +e
    PATH="$FAKE_BIN:$PATH" "$HELPER" --repo owner/repo --closed-window-days "$1" >"$stdout_file" 2>"$stderr_file"
    rc=$?
    set -e
    unset EXPECTED_DAYS
    LAST_STDOUT=$(cat "$stdout_file")
    LAST_STDERR=$(cat "$stderr_file")
    LAST_RC=$rc
    rm -f "$stdout_file" "$stderr_file"
}

assert_rc_eq() {
    local expected="$1" desc="$2"
    if [[ "$LAST_RC" -eq "$expected" ]]; then
        PASSED=$((PASSED + 1))
        echo "  PASS: $desc (rc=$LAST_RC)"
    else
        FAILED=$((FAILED + 1))
        echo "  FAIL: $desc (expected rc=$expected, got $LAST_RC)"
        echo "    stdout: $LAST_STDOUT"
        echo "    stderr: $LAST_STDERR"
    fi
}

assert_status_ok() {
    local desc="$1" first_line
    first_line=$(printf '%s\n' "$LAST_STDOUT" | sed -n '1p')
    if [[ "$first_line" == "LIST_STATUS=ok" ]]; then
        PASSED=$((PASSED + 1))
        echo "  PASS: $desc"
    else
        FAILED=$((FAILED + 1))
        echo "  FAIL: $desc"
        echo "    stdout: $LAST_STDOUT"
        echo "    stderr: $LAST_STDERR"
    fi
}

tsv_body() {
    printf '%s\n' "$1" | sed '1d'
}

assert_tsv_set_eq() {
    local actual="$1" expected="$2" desc="$3" actual_body diff_output
    local expected_count actual_count
    actual_body=$(tsv_body "$actual")
    # Compare as multisets (sort without -u) so duplicate rows from a buggy
    # helper trip the assertion instead of collapsing under sort -u.
    if diff_output=$(diff -u <(printf '%s\n' "$expected" | sort) <(printf '%s\n' "$actual_body" | sort)); then
        expected_count=$(printf '%s\n' "$expected" | grep -c '' || true)
        actual_count=$(printf '%s\n' "$actual_body" | grep -c '' || true)
        if [[ "$expected_count" -ne "$actual_count" ]]; then
            FAILED=$((FAILED + 1))
            echo "  FAIL: $desc (row count mismatch: expected $expected_count, got $actual_count)"
            echo "    actual: $actual_body"
            echo "    stderr: $LAST_STDERR"
        else
            PASSED=$((PASSED + 1))
            echo "  PASS: $desc"
        fi
    else
        FAILED=$((FAILED + 1))
        echo "  FAIL: $desc"
        while IFS= read -r line; do
            printf '    %s\n' "$line"
        done <<<"$diff_output"
        echo "    stderr: $LAST_STDERR"
    fi
}

assert_tsv_contains_title() {
    local title="$1" desc="$2"
    if tsv_body "$LAST_STDOUT" | awk -F '\t' -v title="$title" '$2 == title { found=1 } END { exit found ? 0 : 1 }'; then
        PASSED=$((PASSED + 1))
        echo "  PASS: $desc"
    else
        FAILED=$((FAILED + 1))
        echo "  FAIL: $desc"
        echo "    stdout: $LAST_STDOUT"
        echo "    stderr: $LAST_STDERR"
    fi
}

assert_tsv_lacks_title() {
    local title="$1" desc="$2"
    if tsv_body "$LAST_STDOUT" | awk -F '\t' -v title="$title" '$2 == title { found=1 } END { exit found ? 1 : 0 }'; then
        PASSED=$((PASSED + 1))
        echo "  PASS: $desc"
    else
        FAILED=$((FAILED + 1))
        echo "  FAIL: $desc"
        echo "    stdout: $LAST_STDOUT"
        echo "    stderr: $LAST_STDERR"
    fi
}

assert_marker_nonempty() {
    local marker="$1" desc="$2"
    if [[ -s "$marker" ]]; then
        PASSED=$((PASSED + 1))
        echo "  PASS: $desc"
    else
        FAILED=$((FAILED + 1))
        echo "  FAIL: $desc"
        echo "    stdout: $LAST_STDOUT"
        echo "    stderr: $LAST_STDERR"
    fi
}

echo "TEST 1: open-only branch filters and shapes TSV"
: >"$MARKER_GH"
run_helper 0
assert_rc_eq 0 "open-only branch preserves fail-open rc=0 contract"
assert_status_ok "open-only branch emits LIST_STATUS=ok"
assert_tsv_set_eq "$LAST_STDOUT" "$OPEN_EXPECTED" "open-only TSV rows match expected included issue set"
assert_marker_nonempty "$MARKER_GH" "open-only branch used fake gh"

echo "TEST 2: closed-window branch includes recent closed issues"
: >"$MARKER_GH"
: >"$MARKER_PYTHON3"
run_helper 30
assert_rc_eq 0 "closed-window branch preserves fail-open rc=0 contract"
assert_status_ok "closed-window branch emits LIST_STATUS=ok"
assert_tsv_set_eq "$LAST_STDOUT" "$CLOSED_EXPECTED" "closed-window TSV rows include cutoff-boundary closed issues only"
assert_marker_nonempty "$MARKER_GH" "closed-window branch used fake gh"
assert_marker_nonempty "$MARKER_PYTHON3" "closed-window branch used fake python3 cutoff"

echo "TEST 3: pass-through titles remain present"
run_helper 0
assert_tsv_contains_title "Add foo feature" "ordinary open title passes through"
assert_tsv_contains_title "Fix research summary bug" "non-prefix research substring passes through"
assert_tsv_contains_title "Open with tab and newline and cr" "tab/newline/carriage-return title is TSV-shaped"

echo "TEST 4: prefixes, case, and whitespace are filtered"
run_helper 0
assert_tsv_lacks_title "Researcher settings" "broad research prefix filters Researcher"
assert_tsv_lacks_title "research overhaul" "lowercase research prefix filters"
assert_tsv_lacks_title "Research caching" "mixed-case research prefix filters"
assert_tsv_lacks_title "INVESTIGATE perf" "uppercase investigate prefix filters"
assert_tsv_lacks_title "[Research] cache" "bracketed research prefix filters"
assert_tsv_lacks_title "[INVESTIGATE] X" "bracketed investigate prefix filters"
assert_tsv_lacks_title "[Research Report] Q1" "bracketed research-report prefix filters"
assert_tsv_lacks_title " Research with leading space" "leading-space research title filters"
assert_tsv_lacks_title "	Investigate tab-prefixed" "leading-tab investigate title filters"
assert_tsv_lacks_title "[research]" "exact bracketed research title filters"
assert_tsv_lacks_title "Research Report no brackets" "broad research prefix filters unbracketed Research Report"

echo "TEST 5: PR rows are filtered in both branches"
run_helper 0
assert_tsv_lacks_title "Add PR" "open-only branch filters pull requests"
run_helper 30
assert_tsv_lacks_title "Add PR" "closed-window branch filters pull requests"

echo
echo "RESULTS: passed=$PASSED failed=$FAILED"
if [[ "$FAILED" -gt 0 ]]; then
    exit 1
fi
