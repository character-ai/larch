#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER="$SCRIPT_DIR/oos-file-conflict-deps.sh"

PASS_COUNT=0
FAIL_COUNT=0
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-oos-file-conflict-deps.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail_case() {
    local name="$1" message="$2"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "  FAIL: $name — $message" >&2
}

pass_case() {
    local name="$1"
    PASS_COUNT=$((PASS_COUNT + 1))
    echo "  PASS: $name"
}

append_oos() {
    local file="$1" n="$2" title="$3" description="$4"
    {
        printf '### OOS_%s: %s\n' "$n" "$title"
        printf -- '- **Description**: %s\n' "$description"
        printf -- '- **Reviewer**: Test\n'
        printf -- '- **Vote tally**: YES=2 NO=0 EXONERATE=0\n'
        printf -- '- **Phase**: implement\n\n'
    } >> "$file"
}

run_helper() {
    local input="$1" output="$2" stderr_file="$3" cluster_cap="${4:-}" global_cap="${5:-}"
    set +e
    if [[ -n "$cluster_cap" || -n "$global_cap" ]]; then
        OOS_FILE_CONFLICT_CLUSTER_CAP="${cluster_cap:-200}" \
            OOS_FILE_CONFLICT_GLOBAL_CAP="${global_cap:-500}" \
            bash "$HELPER" --input-file "$input" --output "$output" 2> "$stderr_file"
    else
        bash "$HELPER" --input-file "$input" --output "$output" 2> "$stderr_file"
    fi
    local status=$?
    set -e
    return "$status"
}

assert_case() {
    local name="$1" input="$2" expected="$3" expected_status="$4" stderr_substring="${5:-}" expect_no_output="${6:-false}" cluster_cap="${7:-}" global_cap="${8:-}"
    local dir="$TMP_ROOT/$name"
    mkdir -p "$dir"
    local output="$dir/out.tsv"
    local stderr_file="$dir/stderr.txt"

    if run_helper "$input" "$output" "$stderr_file" "$cluster_cap" "$global_cap"; then
        status=0
    else
        status=$?
    fi

    if [[ "$status" != "$expected_status" ]]; then
        fail_case "$name" "expected exit $expected_status, got $status"
        return
    fi
    if [[ "$expect_no_output" == "true" ]]; then
        if [[ -e "$output" ]]; then
            fail_case "$name" "expected no stable output file"
            return
        fi
    else
        if [[ ! -f "$output" ]]; then
            fail_case "$name" "missing output file"
            return
        fi
        local expected_file="$dir/expected.tsv"
        printf '%s' "$expected" > "$expected_file"
        if ! cmp -s "$expected_file" "$output"; then
            fail_case "$name" "TSV mismatch"
            echo "Expected:" >&2
            sed -n l "$expected_file" >&2
            echo "Actual:" >&2
            sed -n l "$output" >&2
            return
        fi
    fi
    if [[ -n "$stderr_substring" ]] && ! grep -Fq "$stderr_substring" "$stderr_file"; then
        fail_case "$name" "stderr missing substring: $stderr_substring"
        return
    fi
    pass_case "$name"
}

make_input() {
    local name="$1"
    local file="$TMP_ROOT/$name/input.md"
    mkdir -p "$(dirname "$file")"
    : > "$file"
    printf '%s\n' "$file"
}

echo "=== test-oos-file-conflict-deps ==="

input="$(make_input case-a)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh"
append_oos "$input" 2 "Second" "Also touches skills/foo/bar.sh"
assert_case "case-a-same-file" "$input" $'1\t2\n' 0

input="$(make_input case-b)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh:1-50"
append_oos "$input" 2 "Second" "Touches skills/foo/bar.sh:200-300"
assert_case "case-b-disjoint-ranges" "$input" "" 0

input="$(make_input case-c)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh:1-100"
append_oos "$input" 2 "Second" "Touches skills/foo/bar.sh:50-150"
assert_case "case-c-overlap" "$input" $'1\t2\n' 0

input="$(make_input case-d)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh:1-50"
append_oos "$input" 2 "Second" "Touches skills/foo/bar.sh"
assert_case "case-d-whole-file" "$input" $'1\t2\n' 0

input="$(make_input case-e)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh"
append_oos "$input" 2 "Second" "Touches skills/foo/bar.sh"
append_oos "$input" 3 "Third" "Touches skills/foo/bar.sh"
assert_case "case-e-all-pairs" "$input" $'1\t2\n1\t3\n2\t3\n' 0

input="$(make_input case-f)"
append_oos "$input" 1 "First" "Touches skills/foo/a.sh"
append_oos "$input" 2 "Second" "Touches skills/foo/b.sh"
assert_case "case-f-different-files" "$input" "" 0

input="$(make_input case-g)"
append_oos "$input" 1 "First" "Mentions /etc/passwd"
append_oos "$input" 2 "Second" "Touches skills/foo/bar.sh"
assert_case "case-g-absolute-rejected" "$input" "" 0

input="$(make_input case-h)"
append_oos "$input" 1 "First" "Mentions ../../etc/passwd"
append_oos "$input" 2 "Second" "Touches skills/foo/bar.sh"
assert_case "case-h-traversal-rejected" "$input" "" 0

input="$(make_input case-i)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh"
{
    printf '### OOS_2: Malformed\n'
    printf -- '- **Reviewer**: Test\n'
    printf -- '- **Vote tally**: YES=2 NO=0 EXONERATE=0\n'
    printf -- '- **Phase**: implement\n\n'
} >> "$input"
append_oos "$input" 3 "Third" "Touches skills/foo/bar.sh"
assert_case "case-i-malformed-preserves-index" "$input" $'1\t3\n' 0

input="$(make_input case-j)"
for n in $(seq 1 22); do
    append_oos "$input" "$n" "Item $n" "Touches skills/foo/bar.sh"
done
expected=""
for n in $(seq 1 21); do
    next=$((n + 1))
    expected+="${n}"$'\t'"${next}"$'\n'
done
assert_case "case-j-cluster-chain" "$input" "$expected" 0 "cluster size 22"

input="$(make_input case-k)"
idx=1
for cluster in $(seq 1 4); do
    for _ in $(seq 1 4); do
        append_oos "$input" "$idx" "Item $idx" "Touches skills/foo/file-${cluster}.sh"
        idx=$((idx + 1))
    done
done
assert_case "case-k-global-cap" "$input" "" 1 "exceeding the 10-row" true 3 10

input="$(make_input case-l)"
append_oos "$input" 1 "First" "Touches Makefile"
append_oos "$input" 2 "Second" "Touches Makefile"
assert_case "case-l-makefile" "$input" $'1\t2\n' 0

input="$(make_input case-m)"
append_oos "$input" 1 "First" "Touches .pre-commit-config.yaml"
append_oos "$input" 2 "Second" "Touches .pre-commit-config.yaml"
assert_case "case-m-dotfile" "$input" $'1\t2\n' 0

input="$(make_input case-n)"
append_oos "$input" 1 "First" "Touches agent-lint.toml"
append_oos "$input" 2 "Second" "Touches agent-lint.toml"
assert_case "case-n-root-long-extension" "$input" $'1\t2\n' 0

input="$(make_input case-o)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh:50-1"
append_oos "$input" 2 "Second" "Touches skills/foo/bar.sh:60-70"
assert_case "case-o-reversed-range" "$input" $'1\t2\n' 0

input="$(make_input case-p)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh:0-10"
append_oos "$input" 2 "Second" "Touches skills/foo/bar.sh:60-70"
assert_case "case-p-zero-range" "$input" $'1\t2\n' 0

input="$(make_input case-q)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh:1-49"
append_oos "$input" 2 "Second" "Touches skills/foo/bar.sh:50-100"
assert_case "case-q-adjacent" "$input" "" 0

input="$(make_input case-r)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh:1-50"
append_oos "$input" 2 "Second" "Touches skills/foo/bar.sh:50-100"
assert_case "case-r-boundary-overlap" "$input" $'1\t2\n' 0

input="$(make_input case-s)"
idx=1
for cluster in $(seq 1 4); do
    for _ in $(seq 1 4); do
        append_oos "$input" "$idx" "Item $idx" "Touches skills/foo/atomic-${cluster}.sh"
        idx=$((idx + 1))
    done
done
assert_case "case-s-atomic-tier2" "$input" "" 1 "exceeding the 10-row" true 3 10

input="$(make_input case-t)"
append_oos "$input" 1 "First" "Touches skills/foo/bar.sh"
{
    printf '### OOS_2: Incomplete\n'
    printf -- '- **Description**: Touches skills/foo/bar.sh\n'
    printf '### Pending generic\n'
    printf 'Generic body touches skills/foo/other.sh\n'
} >> "$input"
append_oos "$input" 3 "Third" "Touches skills/foo/bar.sh"
assert_case "case-t-pending-heading-malformed" "$input" $'1\t4\n' 0

input="$(make_input case-u)"
{
    printf '### Generic first\n'
    printf 'Body touches skills/foo/bar.sh\n'
    printf '### Generic second\n'
    printf 'Body also touches skills/foo/bar.sh\n\n'
} >> "$input"
assert_case "case-u-generic-fallback-body-file" "$input" $'1\t2\n' 0

echo "---"
echo "Results: $PASS_COUNT passed, $FAIL_COUNT failed"
if (( FAIL_COUNT > 0 )); then
    echo "FAILED: test-oos-file-conflict-deps" >&2
    exit 1
fi
echo "PASSED: test-oos-file-conflict-deps"
