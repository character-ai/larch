#!/usr/bin/env bash
# test-lint-gh-body-inline.sh - Regression harness for lint-gh-body-inline.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINT="$REPO_ROOT/scripts/lint-gh-body-inline.sh"

if [[ ! -f "$LINT" ]]; then
    printf 'ERROR: lint script not found: %s\n' "$LINT" >&2
    exit 1
fi

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lint-gh-body-inline.XXXXXX")"
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

write_body_case() {
    local path="$1"
    local body_opt='--body'
    mkdir -p "$(dirname "$path")"
    printf '%s issue comment 1 %s "hi"\n' "gh" "$body_opt" >"$path"
}

write_notes_case() {
    local path="$1"
    local notes_opt='--notes'
    mkdir -p "$(dirname "$path")"
    printf '%s release create v1 %s "x"\n' "gh" "$notes_opt" >"$path"
}

write_heredoc_body_case() {
    local path="$1"
    local body_opt='--body'
    mkdir -p "$(dirname "$path")"
    {
        printf "%s pr create %s \"\$(cat <<'EOF'\n" "gh" "$body_opt"
        printf 'body\n'
        printf 'EOF\n'
        printf ')"\n'
    } >"$path"
}

write_python_body_case() {
    local path="$1"
    local body_opt='--body'
    mkdir -p "$(dirname "$path")"
    printf 'import subprocess\nsubprocess.run(["%s", "issue", "create", "%s", "x"])\n' "gh" "$body_opt" >"$path"
}

run_lint() {
    local stderr_file="$1"
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

    if [[ "$rc" -ne "$expected_exit" ]]; then
        printf 'FAIL [%s]: expected exit %s, got %s\n' "$label" "$expected_exit" "$rc" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    for needle in "$@"; do
        if ! grep -Fq "$needle" "$stderr_file"; then
            printf 'FAIL [%s]: stderr missing expected needle: %s\n' "$label" "$needle" >&2
            cat "$stderr_file" >&2
            FAIL=$((FAIL + 1))
            return
        fi
    done
    printf 'PASS [%s]\n' "$label"
    PASS=$((PASS + 1))
}

stderr_file="$(mktemp)"

reset_tree
write_file "$TMPROOT/scripts/good.sh" \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    'gh issue comment 1 --body-file body.md' \
    'gh release create v1 --notes-file notes.md'
rc="$(run_lint "$stderr_file")"
assert_case "clean tree" 0 "$stderr_file" "$rc"

reset_tree
write_body_case "$TMPROOT/scripts/bad-body.sh"
rc="$(run_lint "$stderr_file")"
assert_case "inline body" 1 "$stderr_file" "$rc" \
    "scripts/bad-body.sh:1:" \
    "inline g""h --body is forbidden, use --body-file"

reset_tree
write_notes_case "$TMPROOT/scripts/bad-notes.sh"
rc="$(run_lint "$stderr_file")"
assert_case "inline notes" 1 "$stderr_file" "$rc" \
    "scripts/bad-notes.sh:1:" \
    "inline g""h --notes is forbidden, use --notes-file"

reset_tree
write_heredoc_body_case "$TMPROOT/scripts/heredoc-body.sh"
rc="$(run_lint "$stderr_file")"
assert_case "heredoc-substituted body" 1 "$stderr_file" "$rc" \
    "scripts/heredoc-body.sh:1:" \
    "inline g""h --body is forbidden"

reset_tree
body_opt='--body'
write_file "$TMPROOT/scripts/allowed.sh" \
    "$(printf '%s issue comment 1 %s "hi" # lint-gh-body-inline: ok harness fixture' "gh" "$body_opt")"
rc="$(run_lint "$stderr_file")"
assert_case "allow-comment suppression" 0 "$stderr_file" "$rc"

reset_tree
body_opt='--body'
write_file "$TMPROOT/scripts/comment.sh" \
    "$(printf '# %s pr create %s "x"' "gh" "$body_opt")"
rc="$(run_lint "$stderr_file")"
assert_case "full-line comments skipped" 0 "$stderr_file" "$rc"

reset_tree
write_file "$TMPROOT/scripts/body-file.sh" \
    'gh issue comment 1 --body-file file.md' \
    'gh issue comment 1 --body-file -' \
    "gh issue comment 1 --body-file <(printf \"%s\" \"\$body\")" \
    'gh release create v1 --notes-file notes.md'
rc="$(run_lint "$stderr_file")"
assert_case "body-file variants" 0 "$stderr_file" "$rc"

reset_tree
body_opt='--body'
gh_stub_log_ref="\$GH_STUB_LOG"
write_file "$TMPROOT/scripts/stub-assertion.sh" \
    "$(printf '! grep -Eq '\''(^| )%s( |$)'\'' "%s" || fail "%s pr create should not use inline %s" # lint-gh-body-inline: ok gh-stub assertion fixture' "$body_opt" "$gh_stub_log_ref" "gh" "$body_opt")"
rc="$(run_lint "$stderr_file")"
assert_case "gh-stub assertion suppression" 0 "$stderr_file" "$rc"

reset_tree
write_body_case "$TMPROOT/scripts/fallback-bad.sh"
rc="$(run_lint "$stderr_file")"
assert_case "non-git fallback" 1 "$stderr_file" "$rc" \
    "scripts/fallback-bad.sh:1:" \
    "inline g""h --body is forbidden"

reset_tree
write_python_body_case "$TMPROOT/scripts/bad-python.py"
rc="$(run_lint "$stderr_file")"
assert_case "python argv-list body" 1 "$stderr_file" "$rc" \
    "scripts/bad-python.py:2:" \
    "inline g""h --body is forbidden"

reset_tree
write_file "$TMPROOT/scripts/good-python.py" \
    'import subprocess' \
    'subprocess.run(["gh", "issue", "create", "--body-file", "x"])'
rc="$(run_lint "$stderr_file")"
assert_case "python argv-list body-file" 0 "$stderr_file" "$rc"

if command -v git >/dev/null 2>&1; then
    reset_tree
    (
        cd "$TMPROOT"
        git init -q
    )
    write_body_case "$TMPROOT/larch-logs/run-1/script.sh"
    (
        cd "$TMPROOT"
        git add larch-logs/run-1/script.sh
    )
    rc="$(run_lint "$stderr_file")"
    assert_case "tracked larch-logs excluded" 0 "$stderr_file" "$rc"
else
    printf 'SKIP [tracked larch-logs excluded]: git not on PATH\n'
fi

rm -f "$stderr_file"

printf 'Summary: %s passed, %s failed\n' "$PASS" "$FAIL"
if [[ "$FAIL" -ne 0 ]]; then
    exit 1
fi
