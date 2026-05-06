#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
HELPER="$SCRIPT_DIR/oos-issue-cap.sh"

PASS_COUNT=0
FAIL_COUNT=0
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-oos-issue-cap.XXXXXX")"
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

make_input() {
    local name="$1"
    local file="$TMP_ROOT/$name/input.md"
    mkdir -p "$(dirname "$file")"
    : > "$file"
    printf '%s\n' "$file"
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
    local input="$1" output="$2" stderr_file="$3"
    shift 3
    set +e
    env "$@" bash "$HELPER" --input-file "$input" --output "$output" 2> "$stderr_file"
    RUN_STATUS=$?
    set -e
    return 0
}

run_helper_in_place() {
    local input="$1" stderr_file="$2"
    shift 2
    set +e
    env "$@" bash "$HELPER" --input-file "$input" 2> "$stderr_file"
    RUN_STATUS=$?
    set -e
    return 0
}

assert_status() {
    local name="$1" actual="$2" expected="$3"
    if [[ "$actual" != "$expected" ]]; then
        fail_case "$name" "expected exit $expected, got $actual"
        return 1
    fi
    return 0
}

heading_count() {
    grep -c '^### OOS_' "$1" || true
}

assert_contains() {
    local name="$1" file="$2" needle="$3"
    if ! grep -Fq -- "$needle" "$file"; then
        fail_case "$name" "missing substring: $needle"
        return 1
    fi
    return 0
}

assert_byte_equal() {
    local name="$1" expected="$2" actual="$3"
    if ! cmp -s "$expected" "$actual"; then
        fail_case "$name" "expected byte-equivalent output"
        echo "Expected:" >&2
        sed -n l "$expected" >&2
        echo "Actual:" >&2
        sed -n l "$actual" >&2
        return 1
    fi
    return 0
}

build_many_oos() {
    local file="$1" count="$2"
    : > "$file"
    for n in $(seq 1 "$count"); do
        append_oos "$file" "$n" "Title $n" "Description for item $n touching skills/foo/item-$n.sh:$n-$((n + 1))"
    done
}

assert_cap_output() {
    local name="$1" output="$2" expected_count="$3" aggregate_title="$4"
    local count
    count="$(heading_count "$output")"
    if [[ "$count" != "$expected_count" ]]; then
        fail_case "$name" "expected $expected_count OOS headings, got $count"
        return 1
    fi
    assert_contains "$name" "$output" "$aggregate_title" || return 1
    assert_contains "$name" "$output" '- **Reviewer**: Combined: capped per-run rollup' || return 1
    return 0
}

case_basic_cap() {
    local name="$1" cap_env="$2" expected_count="$3" first_rolled="$4" last_rolled="$5"
    local input output stderr_file status
    input="$(make_input "$name")"
    build_many_oos "$input" 7
    output="$TMP_ROOT/$name/out.md"
    stderr_file="$TMP_ROOT/$name/stderr.txt"
    if [[ -n "$cap_env" ]]; then
        run_helper "$input" "$output" "$stderr_file" "OOS_ISSUES_PER_RUN_CAP=$cap_env"
    else
        run_helper "$input" "$output" "$stderr_file"
    fi
    status="$RUN_STATUS"
    assert_status "$name" "$status" 0 || return
    assert_cap_output "$name" "$output" "$expected_count" "### OOS_${expected_count}: Aggregated rollup" || return
    assert_contains "$name" "$output" "Title $first_rolled" || return
    assert_contains "$name" "$output" "Title $last_rolled" || return
    pass_case "$name"
}

echo "=== test-oos-issue-cap ==="

case_basic_cap "case-cap-exceeded-default" "" 5 5 7
case_basic_cap "case-cap-exceeded-explicit" "3" 3 3 7

input="$(make_input case-under-cap)"
build_many_oos "$input" 3
output="$TMP_ROOT/case-under-cap/out.md"
stderr_file="$TMP_ROOT/case-under-cap/stderr.txt"
run_helper "$input" "$output" "$stderr_file"
status="$RUN_STATUS"
if assert_status "case-under-cap" "$status" 0 && assert_byte_equal "case-under-cap" "$input" "$output"; then
    pass_case "case-under-cap"
fi

input="$(make_input case-cap-equals-count)"
build_many_oos "$input" 5
output="$TMP_ROOT/case-cap-equals-count/out.md"
stderr_file="$TMP_ROOT/case-cap-equals-count/stderr.txt"
run_helper "$input" "$output" "$stderr_file"
status="$RUN_STATUS"
if assert_status "case-cap-equals-count" "$status" 0 && assert_byte_equal "case-cap-equals-count" "$input" "$output"; then
    pass_case "case-cap-equals-count"
fi

input="$(make_input case-cap-equals-one)"
build_many_oos "$input" 4
output="$TMP_ROOT/case-cap-equals-one/out.md"
stderr_file="$TMP_ROOT/case-cap-equals-one/stderr.txt"
run_helper "$input" "$output" "$stderr_file" OOS_ISSUES_PER_RUN_CAP=1
status="$RUN_STATUS"
if assert_status "case-cap-equals-one" "$status" 0 \
    && [[ "$(heading_count "$output")" == "1" ]] \
    && assert_contains "case-cap-equals-one" "$output" "### OOS_1: Aggregated rollup of 4 capped OOS items" \
    && assert_contains "case-cap-equals-one" "$output" "Title 1" \
    && assert_contains "case-cap-equals-one" "$output" "Title 4"; then
    pass_case "case-cap-equals-one"
else
    fail_case "case-cap-equals-one" "aggregate output did not match cap=1 expectations"
fi

input="$(make_input case-empty-input)"
output="$TMP_ROOT/case-empty-input/out.md"
stderr_file="$TMP_ROOT/case-empty-input/stderr.txt"
run_helper "$input" "$output" "$stderr_file"
status="$RUN_STATUS"
if assert_status "case-empty-input" "$status" 0 && assert_byte_equal "case-empty-input" "$input" "$output"; then
    pass_case "case-empty-input"
fi

for tuple in \
    "case-invalid-env-zero OOS_ISSUES_PER_RUN_CAP=0 OOS_ISSUES_PER_RUN_CAP" \
    "case-invalid-env-non-numeric OOS_ISSUES_PER_RUN_CAP=abc OOS_ISSUES_PER_RUN_CAP" \
    "case-invalid-env-negative OOS_ISSUES_PER_RUN_CAP=-1 OOS_ISSUES_PER_RUN_CAP" \
    "case-invalid-env-empty OOS_ISSUES_PER_RUN_CAP= OOS_ISSUES_PER_RUN_CAP" \
    "case-invalid-excerpt-max-zero OOS_ISSUE_CAP_EXCERPT_MAX=0 OOS_ISSUE_CAP_EXCERPT_MAX" \
    "case-invalid-excerpt-max-non-numeric OOS_ISSUE_CAP_EXCERPT_MAX=abc OOS_ISSUE_CAP_EXCERPT_MAX" \
    "case-invalid-excerpt-max-empty OOS_ISSUE_CAP_EXCERPT_MAX= OOS_ISSUE_CAP_EXCERPT_MAX"; do
    # shellcheck disable=SC2086 # tuple is a controlled three-field fixture row.
    set -- $tuple
    name="$1"
    env_assignment="$2"
    env_name="$3"
    input="$(make_input "$name")"
    build_many_oos "$input" 2
    output="$TMP_ROOT/$name/out.md"
    stderr_file="$TMP_ROOT/$name/stderr.txt"
    run_helper "$input" "$output" "$stderr_file" "$env_assignment"
    status="$RUN_STATUS"
    if assert_status "$name" "$status" 2 \
        && [[ ! -e "$output" ]] \
        && assert_contains "$name" "$stderr_file" "$env_name must be a positive integer"; then
        pass_case "$name"
    fi
done

input="$(make_input case-malformed-no-body)"
build_many_oos "$input" 4
{
    printf '### OOS_5: Missing description\n'
    printf -- '- **Reviewer**: Test\n'
    printf -- '- **Vote tally**: YES=2 NO=0 EXONERATE=0\n'
    printf -- '- **Phase**: implement\n\n'
    printf '### OOS_6: Last\n'
    printf -- '- **Description**: Final body\n'
    printf -- '- **Reviewer**: Test\n'
    printf -- '- **Vote tally**: YES=2 NO=0 EXONERATE=0\n'
    printf -- '- **Phase**: implement\n\n'
} >> "$input"
output="$TMP_ROOT/case-malformed-no-body/out.md"
stderr_file="$TMP_ROOT/case-malformed-no-body/stderr.txt"
run_helper "$input" "$output" "$stderr_file"
status="$RUN_STATUS"
if assert_status "case-malformed-no-body" "$status" 0 \
    && assert_contains "case-malformed-no-body" "$output" "(malformed item — body unavailable)"; then
    pass_case "case-malformed-no-body"
fi

input="$(make_input case-malformed-with-body)"
build_many_oos "$input" 4
{
    printf '### OOS_5: Incomplete\n'
    printf -- '- **Description**: Diagnostic body survives for skills/foo/diagnostic.sh:7\n'
    printf '### OOS_6: Next\n'
    printf -- '- **Description**: Next body\n'
    printf -- '- **Reviewer**: Test\n'
    printf -- '- **Vote tally**: YES=2 NO=0 EXONERATE=0\n'
    printf -- '- **Phase**: implement\n\n'
} >> "$input"
output="$TMP_ROOT/case-malformed-with-body/out.md"
stderr_file="$TMP_ROOT/case-malformed-with-body/stderr.txt"
run_helper "$input" "$output" "$stderr_file"
status="$RUN_STATUS"
if assert_status "case-malformed-with-body" "$status" 0 \
    && assert_contains "case-malformed-with-body" "$output" "Diagnostic body survives" \
    && assert_contains "case-malformed-with-body" "$output" "[Files: skills/foo/diagnostic.sh:7]"; then
    pass_case "case-malformed-with-body"
fi

input="$(make_input case-in-place-rewrite)"
build_many_oos "$input" 7
copy="$TMP_ROOT/case-in-place-rewrite/copy.md"
cp "$input" "$copy"
expected="$TMP_ROOT/case-in-place-rewrite/expected.md"
stderr_file="$TMP_ROOT/case-in-place-rewrite/stderr.txt"
run_helper "$copy" "$expected" "$stderr_file"
run_helper_in_place "$input" "$stderr_file"
status="$RUN_STATUS"
if assert_status "case-in-place-rewrite" "$status" 0 && assert_byte_equal "case-in-place-rewrite" "$expected" "$input"; then
    pass_case "case-in-place-rewrite"
fi

input="$(make_input case-renumbering)"
append_oos "$input" 1 "First" "Body one"
append_oos "$input" 3 "Second" "Body two"
append_oos "$input" 5 "Third" "Body three"
append_oos "$input" 9 "Fourth" "Body four"
append_oos "$input" 11 "Fifth" "Body five"
append_oos "$input" 13 "Sixth" "Body six"
output="$TMP_ROOT/case-renumbering/out.md"
stderr_file="$TMP_ROOT/case-renumbering/stderr.txt"
run_helper "$input" "$output" "$stderr_file" OOS_ISSUES_PER_RUN_CAP=3
status="$RUN_STATUS"
if assert_status "case-renumbering" "$status" 0 \
    && [[ "$(grep '^### OOS_' "$output" | awk '{ print $2 }' | tr '\n' ' ')" == "OOS_1: OOS_2: OOS_3: " ]]; then
    pass_case "case-renumbering"
else
    fail_case "case-renumbering" "headings were not sequential"
fi

name="case-input-missing"
mkdir -p "$TMP_ROOT/$name"
output="$TMP_ROOT/$name/out.md"
stderr_file="$TMP_ROOT/$name/stderr.txt"
run_helper "$TMP_ROOT/$name/missing.md" "$output" "$stderr_file"
status="$RUN_STATUS"
if assert_status "$name" "$status" 1 \
    && [[ ! -e "$output" ]] \
    && assert_contains "$name" "$stderr_file" "input file not found"; then
    pass_case "$name"
fi

for name in case-stale-output-deleted-on-failure case-in-place-failure-preserves-input; do
    input="$(make_input "$name")"
    build_many_oos "$input" 2
    chmod 000 "$input"
    stderr_file="$TMP_ROOT/$name/stderr.txt"
    if [[ "$name" == "case-stale-output-deleted-on-failure" ]]; then
        output="$TMP_ROOT/$name/out.md"
        printf 'stale\n' > "$output"
        run_helper "$input" "$output" "$stderr_file"
        status="$RUN_STATUS"
        chmod 600 "$input"
        if assert_status "$name" "$status" 1 && [[ ! -e "$output" ]]; then
            pass_case "$name"
        else
            fail_case "$name" "stale output survived parser failure"
        fi
    else
        before="$TMP_ROOT/$name/before.md"
        chmod 600 "$input"
        cp "$input" "$before"
        chmod 000 "$input"
        run_helper_in_place "$input" "$stderr_file"
        status="$RUN_STATUS"
        chmod 600 "$input"
        if assert_status "$name" "$status" 1 && assert_byte_equal "$name" "$before" "$input"; then
            pass_case "$name"
        fi
    fi
done

input="$(make_input case-utf8-multibyte-truncation)"
build_many_oos "$input" 4
append_oos "$input" 5 "UTF8" "前缀😀中文字符保持完整 plus trailing prose that should be truncated safely"
append_oos "$input" 6 "After" "Body after UTF8"
output="$TMP_ROOT/case-utf8-multibyte-truncation/out.md"
stderr_file="$TMP_ROOT/case-utf8-multibyte-truncation/stderr.txt"
run_helper "$input" "$output" "$stderr_file" OOS_ISSUE_CAP_EXCERPT_MAX=8
status="$RUN_STATUS"
if assert_status "case-utf8-multibyte-truncation" "$status" 0 \
    && python3 - "$output" <<'PY'
import pathlib
import sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
assert "�" not in text
assert "…" in text
PY
then
    pass_case "case-utf8-multibyte-truncation"
else
    fail_case "case-utf8-multibyte-truncation" "UTF-8 output was invalid or untruncated"
fi

input="$(make_input case-markdown-normalization)"
build_many_oos "$input" 4
append_oos "$input" 5 "# **\`Risky title\`" "# excerpt starts like heading with **bold** and \`code\`"
append_oos "$input" 6 "Normal" "Normal body"
output="$TMP_ROOT/case-markdown-normalization/out.md"
stderr_file="$TMP_ROOT/case-markdown-normalization/stderr.txt"
run_helper "$input" "$output" "$stderr_file"
status="$RUN_STATUS"
if assert_status "case-markdown-normalization" "$status" 0 \
    && assert_contains "case-markdown-normalization" "$output" "  - **Risky title**:" \
    && ! grep -Fq '  - **#' "$output"; then
    pass_case "case-markdown-normalization"
else
    fail_case "case-markdown-normalization" "aggregate bullet was not markdown-clean"
fi

input="$(make_input case-files-suffix-preserves-paths)"
build_many_oos "$input" 4
long_prefix="$(printf 'x%.0s' $(seq 1 80))"
append_oos "$input" 5 "Path after cutoff" "$long_prefix then mentions skills/foo/bar.sh:200-300"
append_oos "$input" 6 "After" "Body after path"
output="$TMP_ROOT/case-files-suffix-preserves-paths/out.md"
stderr_file="$TMP_ROOT/case-files-suffix-preserves-paths/stderr.txt"
run_helper "$input" "$output" "$stderr_file" OOS_ISSUE_CAP_EXCERPT_MAX=20
status="$RUN_STATUS"
if assert_status "case-files-suffix-preserves-paths" "$status" 0 \
    && assert_contains "case-files-suffix-preserves-paths" "$output" "[Files: skills/foo/bar.sh:200-300]"; then
    pass_case "case-files-suffix-preserves-paths"
fi

for cap in 3 1; do
    name="case-parser-heading-parity-mismatch-cap-$cap"
    input="$(make_input "$name")"
    append_oos "$input" 1 "First" "Body one"
    {
        printf '### OOS_2: Incomplete\n'
        printf -- '- **Description**: Body before pending heading\n'
        printf '### Pending generic\n'
        printf 'Generic body\n'
        printf '### OOS_3: Third\n'
        printf -- '- **Description**: Body three\n'
        printf -- '- **Reviewer**: Test\n'
        printf -- '- **Vote tally**: YES=2 NO=0 EXONERATE=0\n'
        printf -- '- **Phase**: implement\n\n'
    } >> "$input"
    output="$TMP_ROOT/$name/out.md"
    stderr_file="$TMP_ROOT/$name/stderr.txt"
    run_helper "$input" "$output" "$stderr_file" "OOS_ISSUES_PER_RUN_CAP=$cap"
    status="$RUN_STATUS"
    if assert_status "$name" "$status" 1 \
        && assert_contains "$name" "$stderr_file" "ITEMS_TOTAL" \
        && [[ ! -e "$output" ]]; then
        pass_case "$name"
    fi
done

input="$(make_input case-non-oos-input-rejected)"
{
    printf '### Generic first\n'
    printf 'Body one\n'
    printf '### Generic second\n'
    printf 'Body two\n'
} >> "$input"
output="$TMP_ROOT/case-non-oos-input-rejected/out.md"
stderr_file="$TMP_ROOT/case-non-oos-input-rejected/stderr.txt"
run_helper "$input" "$output" "$stderr_file"
status="$RUN_STATUS"
if assert_status "case-non-oos-input-rejected" "$status" 1 \
    && assert_contains "case-non-oos-input-rejected" "$stderr_file" "not OOS-shaped"; then
    pass_case "case-non-oos-input-rejected"
fi

name="case-warning-string-consistency"
warning='**⚠ /implement: oos-issue-cap helper failed (exit <N>) — OOS batch NOT filed; review accepted-OOS Descriptions and re-run with corrected env, or have the items filed manually**'
missing=0
for file in \
    "$SCRIPT_DIR/oos-issue-cap.sh" \
    "$SCRIPT_DIR/oos-issue-cap.md" \
    "$REPO_ROOT/skills/implement/references/anchor-comment-template.md" \
    "$REPO_ROOT/docs/configuration-and-permissions.md"; do
    if ! grep -Fq "$warning" "$file"; then
        echo "  missing warning in $file" >&2
        missing=1
    fi
done
if (( missing == 0 )); then
    pass_case "$name"
else
    fail_case "$name" "warning string drifted"
fi

echo "=== test-oos-issue-cap: $PASS_COUNT passed, $FAIL_COUNT failed ==="
if (( FAIL_COUNT > 0 )); then
    exit 1
fi
