#!/usr/bin/env bash
# Regression harness for lint-fix-loop.sh dispatch safety.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SOURCE_SCRIPTS="$REPO_ROOT/scripts"

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lint-fix-loop.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    [[ "$haystack" == *"$needle"* ]] || fail "$label missing '$needle' in: $haystack"
}

make_repo() {
    local dir="$1"
    mkdir -p "$dir"
    (
        cd "$dir"
        git init -q -b main
        git config user.name "Test User"
        git config user.email "test@example.com"
        printf 'base\n' > tracked.txt
        git add tracked.txt
        git commit -q -m "baseline"
    )
}

make_fixture_scripts() {
    local dir="$1"
    mkdir -p "$dir"
    cp "$SOURCE_SCRIPTS/lint-fix-loop.sh" "$dir/lint-fix-loop.sh"
    cp "$SOURCE_SCRIPTS/lib-quiet.sh" "$dir/lib-quiet.sh"
    cp "$SOURCE_SCRIPTS/lib-cursor-launcher-common.sh" "$dir/lib-cursor-launcher-common.sh"
    cp "$SOURCE_SCRIPTS/lib-external-launcher-common.sh" "$dir/lib-external-launcher-common.sh"
    cp "$SOURCE_SCRIPTS/read-session-env-key.sh" "$dir/read-session-env-key.sh"
    cp "$SOURCE_SCRIPTS/git-commit.sh" "$dir/git-commit.sh"
    chmod +x \
        "$dir/lint-fix-loop.sh" \
        "$dir/lib-cursor-launcher-common.sh" \
        "$dir/read-session-env-key.sh" \
        "$dir/git-commit.sh"
}

make_session() {
    local dir="$1"
    mkdir -p "$dir"
    cat > "$dir/session-env.sh" <<'EOF'
CODEX_PRESENT=true
CURSOR_PRESENT=false
EOF
}

write_wrapper_commit_head() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub commit head change\n' > "$output"
printf 'committed-by-stub\n' > tracked.txt
git add tracked.txt
git commit -q -m "stub commit"
EOF
    chmod +x "$path"
}

write_wrapper_modify_only() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub modify only\n' > "$output"
printf 'modified-without-commit\n' > tracked.txt
EOF
    chmod +x "$path"
}

run_case() {
    local fixture_scripts="$1" repo="$2" session="$3" checks_log="$4" wrapper="$5" site="${6:-step3}"
    local rc=0 out
    out=$(
        cd "$repo" && \
        unset LARCH_QUIET_ACTIVE LARCH_QUIET_PID LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG || true
        # shellcheck disable=SC2030,SC2031
        export IMPLEMENT_TMPDIR="$session"
        LINT_FIX_LOOP_RUN_EXTERNAL_AGENT_SH="$wrapper" \
        bash "$fixture_scripts/lint-fix-loop.sh" --tmpdir "$session" --site "$site" --checks-log "$checks_log"
    ) || rc=$?
    printf '%s\n%s\n' "$rc" "$out"
}

# Case 1: external coder commits; lint-fix-loop must fail closed on HEAD drift.
CASE1="$TMPROOT/case1"
REPO1="$CASE1/repo"
SCRIPTS1="$CASE1/scripts"
SESSION1="$CASE1/session"
CHECKS1="$CASE1/checks.log"
WRAPPER1="$CASE1/wrapper.sh"
make_repo "$REPO1"
make_fixture_scripts "$SCRIPTS1"
make_session "$SESSION1"
printf 'synthetic checks failure\n' > "$CHECKS1"
write_wrapper_commit_head "$WRAPPER1"

case1_result=$(run_case "$SCRIPTS1" "$REPO1" "$SESSION1" "$CHECKS1" "$WRAPPER1")
case1_rc=$(printf '%s\n' "$case1_result" | sed -n '1p')
case1_out=$(printf '%s\n' "$case1_result" | sed -n '2,$p')
[[ "$case1_rc" == "1" ]] || fail "case1 expected rc 1, got $case1_rc"
assert_contains "$case1_out" 'LINT_FIX_STATUS=failed' "case1 status"
assert_contains "$case1_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1 reason"

# Case 2: helper-owned commit fails; staged delta paths must be reset.
CASE2="$TMPROOT/case2"
REPO2="$CASE2/repo"
SCRIPTS2="$CASE2/scripts"
SESSION2="$CASE2/session"
CHECKS2="$CASE2/checks.log"
WRAPPER2="$CASE2/wrapper.sh"
make_repo "$REPO2"
make_fixture_scripts "$SCRIPTS2"
make_session "$SESSION2"
printf 'synthetic checks failure\n' > "$CHECKS2"
write_wrapper_modify_only "$WRAPPER2"
cat > "$SCRIPTS2/git-commit.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exit 1
EOF
chmod +x "$SCRIPTS2/git-commit.sh"

case2_result=$(run_case "$SCRIPTS2" "$REPO2" "$SESSION2" "$CHECKS2" "$WRAPPER2")
case2_rc=$(printf '%s\n' "$case2_result" | sed -n '1p')
case2_out=$(printf '%s\n' "$case2_result" | sed -n '2,$p')
[[ "$case2_rc" == "1" ]] || fail "case2 expected rc 1, got $case2_rc"
assert_contains "$case2_out" 'LINT_FIX_STATUS=failed' "case2 status"
assert_contains "$case2_out" 'FAILURE_REASON=git-commit-failed' "case2 reason"
cached_after_case2=$(cd "$REPO2" && git diff --cached --name-only)
[[ -z "$cached_after_case2" ]] || fail "case2 expected empty index, got: $cached_after_case2"
worktree_after_case2=$(cd "$REPO2" && git diff --name-only)
[[ "$worktree_after_case2" == "tracked.txt" ]] || fail "case2 expected unstaged tracked.txt delta, got: $worktree_after_case2"

# Case 3: ship-pr-ci-initial site — success path (coder modifies file).
CASE3="$TMPROOT/case3"
REPO3="$CASE3/repo"
SCRIPTS3="$CASE3/scripts"
SESSION3="$CASE3/session"
CHECKS3="$CASE3/checks.log"
WRAPPER3="$CASE3/wrapper.sh"
make_repo "$REPO3"
make_fixture_scripts "$SCRIPTS3"
make_session "$SESSION3"
printf 'synthetic checks failure\n' > "$CHECKS3"
write_wrapper_modify_only "$WRAPPER3"

case3_result=$(run_case "$SCRIPTS3" "$REPO3" "$SESSION3" "$CHECKS3" "$WRAPPER3" ship-pr-ci-initial)
assert_contains "$case3_result" 'LINT_FIX_STATUS=applied' "case3 status"
assert_contains "$case3_result" 'LINT_FIX_SITE=ship-pr-ci-initial' "case3 site"

# Case 4: ship-pr-ci-initial site — no-changes path (coder makes no changes).
CASE4="$TMPROOT/case4"
REPO4="$CASE4/repo"
SCRIPTS4="$CASE4/scripts"
SESSION4="$CASE4/session"
CHECKS4="$CASE4/checks.log"
WRAPPER4="$CASE4/wrapper.sh"
make_repo "$REPO4"
make_fixture_scripts "$SCRIPTS4"
make_session "$SESSION4"
printf 'synthetic checks failure\n' > "$CHECKS4"
# Wrapper that writes nothing to disk.
cat > "$WRAPPER4" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done
printf 'stub no-op\n' > "$output"
EOF
chmod +x "$WRAPPER4"

case4_result=$(run_case "$SCRIPTS4" "$REPO4" "$SESSION4" "$CHECKS4" "$WRAPPER4" ship-pr-ci-initial)
assert_contains "$case4_result" 'LINT_FIX_STATUS=no-changes' "case4 status"
assert_contains "$case4_result" 'LINT_FIX_SITE=ship-pr-ci-initial' "case4 site"

echo "test-lint-fix-loop: ok"
