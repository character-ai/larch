#!/usr/bin/env bash
# test-lint-awk-multibyte-regex.sh - Regression harness for lint-awk-multibyte-regex.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINT="$REPO_ROOT/scripts/lint-awk-multibyte-regex.sh"

if [[ ! -f "$LINT" ]]; then
    printf 'ERROR: lint script not found: %s\n' "$LINT" >&2
    exit 1
fi

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lint-awk-multibyte-regex.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0

reset_tree() {
    find "$TMPROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    mkdir -p "$TMPROOT/scripts"
}

write_file() {
    local path="$1"
    shift
    mkdir -p "$(dirname "$path")"
    printf '%s\n' "$@" >"$path"
}

run_lint() {
    local stderr_file="$1"
    : >"$stderr_file"
    set +e
    bash "$LINT" --root "$TMPROOT" 2>"$stderr_file"
    local rc=$?
    set -e
    printf '%s\n' "$rc"
}

assert_case() {
    local label="$1"
    local expected_exit="$2"
    local stderr_file="$3"
    local rc="$4"
    shift 4
    set +e

    if [[ "$rc" -ne "$expected_exit" ]]; then
        printf 'FAIL [%s]: expected exit %s, got %s\n' "$label" "$expected_exit" "$rc" >&2
        command grep -F . "$stderr_file" 2>/dev/null >&2 || true
        FAIL=$((FAIL + 1))
        set -e
        return 0
    fi
    for needle in "$@"; do
        if ! ( command grep -Fq "$needle" "$stderr_file" ) 2>/dev/null; then
            printf 'FAIL [%s]: stderr missing expected needle: %s\n' "$label" "$needle" >&2
            command grep -F . "$stderr_file" 2>/dev/null >&2 || true
            FAIL=$((FAIL + 1))
            set -e
            return 0
        fi
    done
    printf 'PASS [%s]\n' "$label"
    PASS=$((PASS + 1))
    set -e
    return 0
}

assert_negative() {
    local label="$1"
    local stderr_file="$2"
    local rc="$3"
    shift 3
    set +e

    if [[ "$rc" -ne 0 ]]; then
        printf 'FAIL [%s]: expected clean exit 0, got %s\n' "$label" "$rc" >&2
        command grep -F . "$stderr_file" 2>/dev/null >&2 || true
        FAIL=$((FAIL + 1))
        set -e
        return 0
    fi
    for needle in "$@"; do
        if ( command grep -Fq "$needle" "$stderr_file" ) 2>/dev/null; then
            printf 'FAIL [%s]: stderr unexpectedly contains: %s\n' "$label" "$needle" >&2
            command grep -F . "$stderr_file" 2>/dev/null >&2 || true
            FAIL=$((FAIL + 1))
            set -e
            return 0
        fi
    done
    printf 'PASS [%s]\n' "$label"
    PASS=$((PASS + 1))
    set -e
    return 0
}

assert_clean_case() {
    local label="$1"
    local stderr_file="$2"
    local rc="$3"
    set +e

    if [[ "$rc" -ne 0 ]]; then
        printf 'FAIL [%s]: expected clean exit 0, got %s\n' "$label" "$rc" >&2
        command grep -F . "$stderr_file" 2>/dev/null >&2 || true
        FAIL=$((FAIL + 1))
        set -e
        return 0
    fi
    if [[ -s "$stderr_file" ]]; then
        printf 'FAIL [%s]: expected empty stderr for clean fixture\n' "$label" >&2
        command grep -F . "$stderr_file" 2>/dev/null >&2 || true
        FAIL=$((FAIL + 1))
        set -e
        return 0
    fi
    printf 'PASS [%s]\n' "$label"
    PASS=$((PASS + 1))
    set -e
    return 0
}

stderr_file="$(mktemp)"

# 1. Clean fixture (ASCII-only).
reset_tree
write_file "$TMPROOT/scripts/clean.sh" \
    "awk -v style='^plain ascii$' '\$0 ~ style { print }'"
rc="$(run_lint "$stderr_file")"
assert_clean_case "clean ascii-only" "$stderr_file" "$rc"

# 2. Rule 1 em-dash in -v value.
reset_tree
write_file "$TMPROOT/scripts/rule1-emdash.sh" \
    "awk -v style_re='^prefix — suffix$' 'BEGIN { print style_re }'" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "rule1 em-dash in -v" 1 "$stderr_file" "$rc" \
    "awk-v-nonascii" \
    "scripts/rule1-emdash.sh:1:"

# 3. Rule 1 CJK in -v value.
reset_tree
write_file "$TMPROOT/scripts/rule1-cjk.sh" \
    "awk -v label='テスト' 'BEGIN { print label }'" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "rule1 cjk in -v" 1 "$stderr_file" "$rc" \
    "awk-v-nonascii" \
    "scripts/rule1-cjk.sh:1:"

# 4. Rule 2 em-dash in match() inside awk body.
reset_tree
# shellcheck disable=SC2016
write_file "$TMPROOT/scripts/rule2-match.sh" \
    'awk '\''match($0, "^<!-- step:" id "([[:space:]]|—)")'\''' # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "rule2 em-dash in match" 1 "$stderr_file" "$rc" \
    "awk-body-nonascii-regex" \
    "scripts/rule2-match.sh:1:"

# 5. Rule 2 em-dash on $0 ~ var line inside body.
reset_tree
write_file "$TMPROOT/scripts/rule2-tilde.sh" \
    "awk 'BEGIN { re = \"x — y\"; if (\$0 ~ re) print }'" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "rule2 em-dash on tilde line" 1 "$stderr_file" "$rc" \
    "awk-body-nonascii-regex" \
    "scripts/rule2-tilde.sh:1:"

# 6. Rule 2 false-positive guard for non-ASCII in printf format only.
reset_tree
write_file "$TMPROOT/scripts/rule2-printf-fp.sh" \
    "awk 'BEGIN { printf \"テスト\\n\" }'" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_negative "rule2 printf false positive" "$stderr_file" "$rc" \
    "awk-body-nonascii-regex"

# 7. Suppression pragma with reason.
reset_tree
write_file "$TMPROOT/scripts/pragma-ok.sh" \
    "awk -v label='テスト' 'BEGIN { print }' # lint-awk-multibyte-regex: ok display-only" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_negative "pragma with reason" "$stderr_file" "$rc" \
    "awk-v-nonascii"

# 8. Suppression pragma without reason.
reset_tree
write_file "$TMPROOT/scripts/pragma-bad.sh" \
    "awk -v label='テスト' 'BEGIN { print }' # lint-awk-multibyte-regex: ok" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "pragma without reason" 1 "$stderr_file" "$rc" \
    "awk-v-nonascii"

# 9. Excluded node_modules/ prefix.
reset_tree
write_file "$TMPROOT/node_modules/pkg/bad.sh" \
    "awk -v label='テスト' 'BEGIN { print }'" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_negative "excluded node_modules" "$stderr_file" "$rc" \
    "node_modules/"

# 10. Excluded larch-logs/ prefix.
reset_tree
write_file "$TMPROOT/larch-logs/run/bad.sh" \
    "awk -v label='テスト' 'BEGIN { print }'" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_negative "excluded larch-logs" "$stderr_file" "$rc" \
    "larch-logs/"

# 11. Standalone .awk file with non-ASCII at match(.
reset_tree
# shellcheck disable=SC2016
write_file "$TMPROOT/scripts/bad.awk" \
    'BEGIN { if (match($0, "—")) print "hit" }' # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "standalone awk file" 1 "$stderr_file" "$rc" \
    "awk-body-nonascii-regex" \
    "scripts/bad.awk:1:"

# 12. Invalid --root exits 2.
set +e
bash "$LINT" --root "$TMPROOT/nonexistent-$$" 2>"$stderr_file"
rc=$?
set -e
assert_case "invalid --root" 2 "$stderr_file" "$rc" \
    "is not a directory"

# 13. Rule 1 ignores shell comments that mention awk.
reset_tree
write_file "$TMPROOT/scripts/commented-example.sh" \
    "# awk -v label='テスト' 'BEGIN { print label }'" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_negative "rule1 skips shell comments" "$stderr_file" "$rc" \
    "awk-v-nonascii"

# 14. Rule 1 joins backslash continuations and split = assignment.
reset_tree
write_file "$TMPROOT/scripts/rule1-continuation.sh" \
    "awk -v label = \\" \
    "  'テスト' 'BEGIN { print label }'" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "rule1 continuation split assignment" 1 "$stderr_file" "$rc" \
    "awk-v-nonascii" \
    "scripts/rule1-continuation.sh:2:"

# 15. Rule 2 detects heredoc awk bodies.
reset_tree
# shellcheck disable=SC2016
write_file "$TMPROOT/scripts/rule2-heredoc.sh" \
    "awk -f - <<'AWK'" \
    'BEGIN { if (match($0, "—")) print "hit" }' \
    "AWK" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "rule2 heredoc body" 1 "$stderr_file" "$rc" \
    "awk-body-nonascii-regex" \
    "scripts/rule2-heredoc.sh:2:"

# 16. Rule 1 ignores non-awk heredoc bodies.
reset_tree
rule1_nonawk_heredoc_line="awk -v label='テスト' 'BEGIN { print label }'" # lint-awk-multibyte-regex: ok harness fixture
write_file "$TMPROOT/scripts/rule1-nonawk-heredoc.sh" \
    "cat <<'DOC'" \
    "$rule1_nonawk_heredoc_line" \
    "DOC"
rc="$(run_lint "$stderr_file")"
assert_clean_case "rule1 skips non-awk heredoc body" "$stderr_file" "$rc"

# 17. Rule 2 closes single-quoted bodies before pipeline suffixes.
reset_tree
write_file "$TMPROOT/scripts/rule2-pipeline-close.sh" \
    "awk 'BEGIN {" \
    "  if (match(\$0, \"—\")) print \"hit\"" \
    "}' | cat" \
    "printf 'ascii only\\n'" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "rule2 single-quote pipeline close" 1 "$stderr_file" "$rc" \
    "awk-body-nonascii-regex" \
    "scripts/rule2-pipeline-close.sh:2:"

# 18. Rule 2 covers gsub/sub/split/!~ callsites.
reset_tree
write_file "$TMPROOT/scripts/rule2-callsite-tokens.sh" \
    "awk 'BEGIN {" \
    "  if (\$0 !~ \"—\") print \"not match\"" \
    "  gsub(\"—\", \"-\", \$0)" \
    "  sub(\"—\", \"-\", \$0)" \
    "  split(\$0, parts, \"—\")" \
    "}'" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "rule2 extra callsite tokens" 1 "$stderr_file" "$rc" \
    "awk-body-nonascii-regex" \
    "scripts/rule2-callsite-tokens.sh:2:" \
    "scripts/rule2-callsite-tokens.sh:3:" \
    "scripts/rule2-callsite-tokens.sh:4:" \
    "scripts/rule2-callsite-tokens.sh:5:"

# 19. Rule 2 ignores substr( but still catches trailing continuation at EOF.
reset_tree
write_file "$TMPROOT/scripts/rule2-substr-eof.sh" \
    "awk 'BEGIN { \\" \
    "  print substr(\$0, 1, 1); if (\$0 ~ \"—\") print \"hit\"" # lint-awk-multibyte-regex: ok harness fixture
rc="$(run_lint "$stderr_file")"
assert_case "rule2 substr false positive and eof continuation" 1 "$stderr_file" "$rc" \
    "awk-body-nonascii-regex" \
    "scripts/rule2-substr-eof.sh:2:"
clean_rc=0
assert_negative "rule2 substr false positive absent" "$stderr_file" "$clean_rc" \
    "scripts/rule2-substr-eof.sh:1:"

# 20. Manifest scopes shell arm; standalone .awk remains scanned.
reset_tree
mkdir -p "$TMPROOT/scripts"
cat > "$TMPROOT/scripts/residual-bash-paths.txt" <<'EOF'
scripts/in-scope-shell.sh
EOF
write_file "$TMPROOT/scripts/in-scope-shell.sh" \
    "awk 'BEGIN { if (match(\$0, \"—\")) print \"hit\" }'" # lint-awk-multibyte-regex: ok harness fixture
write_file "$TMPROOT/scripts/out-of-scope-shell.sh" \
    "awk 'BEGIN { if (match(\$0, \"—\")) print \"hit\" }'" # lint-awk-multibyte-regex: ok harness fixture
# shellcheck disable=SC2016
write_file "$TMPROOT/scripts/standalone.awk" \
    'BEGIN { if (match($0, "—")) print "hit" }'
rc="$(run_lint "$stderr_file")"
assert_case "manifest scopes shell arm only" 1 "$stderr_file" "$rc" \
    "scripts/in-scope-shell.sh:1:" \
    "awk-body-nonascii-regex"
if grep -Fq "scripts/out-of-scope-shell.sh" "$stderr_file"; then
    printf 'FAIL [manifest skips out-of-scope shell]: stderr mentioned out-of-scope shell\n' >&2
    cat "$stderr_file" >&2
    FAIL=$((FAIL + 1))
else
    printf 'PASS [manifest skips out-of-scope shell]\n'
    PASS=$((PASS + 1))
fi
assert_case "standalone awk still scanned" 1 "$stderr_file" "$rc" \
    "scripts/standalone.awk:1:"

rm -f "$stderr_file"

printf 'Summary: %s passed, %s failed\n' "$PASS" "$FAIL"
if [[ "$FAIL" -ne 0 ]]; then
    exit 1
fi
