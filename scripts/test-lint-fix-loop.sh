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

kv_value() {
    local key="$1" text="$2"
    printf '%s\n' "$text" | awk -F= -v key="$key" '$1 == key { print substr($0, index($0,"=")+1); exit }'
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

add_forbidden_submodule_fixture() {
    local dir="$1"
    (
        cd "$dir"
        cat > .gitmodules <<'EOF'
[submodule "submod"]
	path = submod
	url = https://example.invalid/submod.git
EOF
        mkdir -p submod
        printf 'base\n' > submod/file
        git add .gitmodules submod/file
        git commit -q -m "add synthetic submodule path"
    )
}

make_fixture_scripts() {
    local dir="$1"
    mkdir -p "$dir"
    cp "$SOURCE_SCRIPTS/lint-fix-loop.sh" "$dir/lint-fix-loop.sh"
    cp "$SOURCE_SCRIPTS/lib-quiet.sh" "$dir/lib-quiet.sh"
    cp "$SOURCE_SCRIPTS/lib-cursor-launcher-common.sh" "$dir/lib-cursor-launcher-common.sh"
    cp "$SOURCE_SCRIPTS/lib-external-launcher-common.sh" "$dir/lib-external-launcher-common.sh"
    cp "$SOURCE_SCRIPTS/lib-submodule-prohibition.sh" "$dir/lib-submodule-prohibition.sh"
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

write_wrapper_amend_history_rewrite() {
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

printf 'stub amend history rewrite\n' > "$output"
printf 'amended-change\n' > tracked.txt
git add tracked.txt
git commit --amend -q -m "stub amended commit"
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

write_wrapper_commit_forbidden_path() {
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

printf 'stub forbidden commit\n' > "$output"
printf 'forbidden-change\n' > submod/file
git add submod/file
git commit -q -m "stub forbidden commit"
EOF
    chmod +x "$path"
}

write_wrapper_merge_commit() {
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

printf 'stub merge commit\n' > "$output"
git checkout -q -b sibling
printf 'sibling-change\n' > sibling.txt
git add sibling.txt
git commit -q -m "stub sibling commit"
git checkout -q main
printf 'main-change\n' > tracked.txt
git add tracked.txt
git commit -q -m "stub main commit"
git merge --no-ff -q sibling -m "stub merge commit"
EOF
    chmod +x "$path"
}

write_wrapper_detached_commit() {
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

printf 'stub detached commit\n' > "$output"
git checkout -q --detach
printf 'detached-change\n' > tracked.txt
git add tracked.txt
git commit -q -m "stub detached commit"
EOF
    chmod +x "$path"
}

write_wrapper_branch_switch_commit() {
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

printf 'stub branch switch commit\n' > "$output"
git checkout -q -b sibling
printf 'sibling-change\n' > tracked.txt
git add tracked.txt
git commit -q -m "stub sibling commit"
EOF
    chmod +x "$path"
}

write_wrapper_commit_other_file() {
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

printf 'stub dirty baseline commit\n' > "$output"
printf 'new committed file\n' > committed.txt
git add committed.txt
git commit -q -m "stub dirty baseline commit"
EOF
    chmod +x "$path"
}

run_case() {
    local fixture_scripts="$1" repo="$2" session="$3" checks_log="$4" wrapper="$5" site="${6:-step3}" target_args_file="${7:-}"
    local rc=0 out
    local extra_args=()
    if [[ -n "$target_args_file" ]]; then
        extra_args=(--target-cmd-args-file "$target_args_file")
    fi
    out=$(
        cd "$repo" && \
        unset LARCH_QUIET_ACTIVE LARCH_QUIET_PID LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG || true
        # shellcheck disable=SC2030,SC2031
        export IMPLEMENT_TMPDIR="$session"
        LINT_FIX_LOOP_RUN_EXTERNAL_AGENT_SH="$wrapper" \
        bash "$fixture_scripts/lint-fix-loop.sh" --tmpdir "$session" --site "$site" --checks-log "$checks_log" ${extra_args[@]+"${extra_args[@]}"} 2>&1
    ) || rc=$?
    printf '%s\n%s\n' "$rc" "$out"
}

# Case 1: external coder commits on the same clean branch; lint-fix-loop accepts it.
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
[[ "$case1_rc" == "0" ]] || fail "case1 expected rc 0, got $case1_rc"
assert_contains "$case1_out" 'LINT_FIX_STATUS=applied' "case1 status"
case1_commit_sha=$(kv_value LINT_FIX_COMMIT_SHA "$case1_out")
[[ -n "$case1_commit_sha" ]] || fail "case1 expected non-empty LINT_FIX_COMMIT_SHA"
case1_head=$(cd "$REPO1" && git rev-parse HEAD)
[[ "$case1_commit_sha" == "$case1_head" ]] || fail "case1 expected commit sha $case1_head, got $case1_commit_sha"
assert_contains "$case1_out" 'LINT_FIX_HEAD_CHANGED=true' "case1 head changed"
case1_delta_file=$(kv_value LINT_FIX_DELTA_PATHS_FILE "$case1_out")
[[ -n "$case1_delta_file" && -f "$case1_delta_file" ]] || fail "case1 expected readable delta paths file"
grep -Fxq 'tracked.txt' "$case1_delta_file" || fail "case1 expected tracked.txt in delta paths"

# Case 1b: coder commits a forbidden submodule path; lint-fix-loop resets to baseline.
CASE1B="$TMPROOT/case1b"
REPO1B="$CASE1B/repo"
SCRIPTS1B="$CASE1B/scripts"
SESSION1B="$CASE1B/session"
CHECKS1B="$CASE1B/checks.log"
WRAPPER1B="$CASE1B/wrapper.sh"
make_repo "$REPO1B"
add_forbidden_submodule_fixture "$REPO1B"
make_fixture_scripts "$SCRIPTS1B"
make_session "$SESSION1B"
printf 'synthetic checks failure\n' > "$CHECKS1B"
write_wrapper_commit_forbidden_path "$WRAPPER1B"
case1b_baseline=$(cd "$REPO1B" && git rev-parse HEAD)

case1b_result=$(run_case "$SCRIPTS1B" "$REPO1B" "$SESSION1B" "$CHECKS1B" "$WRAPPER1B")
case1b_rc=$(printf '%s\n' "$case1b_result" | sed -n '1p')
case1b_out=$(printf '%s\n' "$case1b_result" | sed -n '2,$p')
[[ "$case1b_rc" == "1" ]] || fail "case1b expected rc 1, got $case1b_rc"
assert_contains "$case1b_out" 'LINT_FIX_STATUS=failed' "case1b status"
assert_contains "$case1b_out" 'FAILURE_REASON=forbidden-path-violation' "case1b reason"
case1b_head=$(cd "$REPO1B" && git rev-parse HEAD)
[[ "$case1b_head" == "$case1b_baseline" ]] || fail "case1b expected reset to $case1b_baseline, got $case1b_head"

# Case 1c: detached HEAD after dispatch still fails closed.
CASE1C="$TMPROOT/case1c"
REPO1C="$CASE1C/repo"
SCRIPTS1C="$CASE1C/scripts"
SESSION1C="$CASE1C/session"
CHECKS1C="$CASE1C/checks.log"
WRAPPER1C="$CASE1C/wrapper.sh"
make_repo "$REPO1C"
make_fixture_scripts "$SCRIPTS1C"
make_session "$SESSION1C"
printf 'synthetic checks failure\n' > "$CHECKS1C"
write_wrapper_detached_commit "$WRAPPER1C"

case1c_result=$(run_case "$SCRIPTS1C" "$REPO1C" "$SESSION1C" "$CHECKS1C" "$WRAPPER1C")
case1c_rc=$(printf '%s\n' "$case1c_result" | sed -n '1p')
case1c_out=$(printf '%s\n' "$case1c_result" | sed -n '2,$p')
[[ "$case1c_rc" == "1" ]] || fail "case1c expected rc 1, got $case1c_rc"
assert_contains "$case1c_out" 'LINT_FIX_STATUS=failed' "case1c status"
assert_contains "$case1c_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1c reason"

# Case 1d: branch switch after dispatch still fails closed.
CASE1D="$TMPROOT/case1d"
REPO1D="$CASE1D/repo"
SCRIPTS1D="$CASE1D/scripts"
SESSION1D="$CASE1D/session"
CHECKS1D="$CASE1D/checks.log"
WRAPPER1D="$CASE1D/wrapper.sh"
make_repo "$REPO1D"
make_fixture_scripts "$SCRIPTS1D"
make_session "$SESSION1D"
printf 'synthetic checks failure\n' > "$CHECKS1D"
write_wrapper_branch_switch_commit "$WRAPPER1D"

case1d_result=$(run_case "$SCRIPTS1D" "$REPO1D" "$SESSION1D" "$CHECKS1D" "$WRAPPER1D")
case1d_rc=$(printf '%s\n' "$case1d_result" | sed -n '1p')
case1d_out=$(printf '%s\n' "$case1d_result" | sed -n '2,$p')
[[ "$case1d_rc" == "1" ]] || fail "case1d expected rc 1, got $case1d_rc"
assert_contains "$case1d_out" 'LINT_FIX_STATUS=failed' "case1d status"
assert_contains "$case1d_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1d reason"

# Case 1d.5: amended history rewrite after dispatch still fails closed.
CASE1D5="$TMPROOT/case1d5"
REPO1D5="$CASE1D5/repo"
SCRIPTS1D5="$CASE1D5/scripts"
SESSION1D5="$CASE1D5/session"
CHECKS1D5="$CASE1D5/checks.log"
WRAPPER1D5="$CASE1D5/wrapper.sh"
make_repo "$REPO1D5"
make_fixture_scripts "$SCRIPTS1D5"
make_session "$SESSION1D5"
printf 'synthetic checks failure\n' > "$CHECKS1D5"
write_wrapper_amend_history_rewrite "$WRAPPER1D5"

case1d5_result=$(run_case "$SCRIPTS1D5" "$REPO1D5" "$SESSION1D5" "$CHECKS1D5" "$WRAPPER1D5")
case1d5_rc=$(printf '%s\n' "$case1d5_result" | sed -n '1p')
case1d5_out=$(printf '%s\n' "$case1d5_result" | sed -n '2,$p')
[[ "$case1d5_rc" == "1" ]] || fail "case1d5 expected rc 1, got $case1d5_rc"
assert_contains "$case1d5_out" 'LINT_FIX_STATUS=failed' "case1d5 status"
assert_contains "$case1d5_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1d5 reason"

# Case 1d.6: merge commits after dispatch still fail closed.
CASE1D6="$TMPROOT/case1d6"
REPO1D6="$CASE1D6/repo"
SCRIPTS1D6="$CASE1D6/scripts"
SESSION1D6="$CASE1D6/session"
CHECKS1D6="$CASE1D6/checks.log"
WRAPPER1D6="$CASE1D6/wrapper.sh"
make_repo "$REPO1D6"
make_fixture_scripts "$SCRIPTS1D6"
make_session "$SESSION1D6"
printf 'synthetic checks failure\n' > "$CHECKS1D6"
write_wrapper_merge_commit "$WRAPPER1D6"

case1d6_result=$(run_case "$SCRIPTS1D6" "$REPO1D6" "$SESSION1D6" "$CHECKS1D6" "$WRAPPER1D6")
case1d6_rc=$(printf '%s\n' "$case1d6_result" | sed -n '1p')
case1d6_out=$(printf '%s\n' "$case1d6_result" | sed -n '2,$p')
[[ "$case1d6_rc" == "1" ]] || fail "case1d6 expected rc 1, got $case1d6_rc"
assert_contains "$case1d6_out" 'LINT_FIX_STATUS=failed' "case1d6 status"
assert_contains "$case1d6_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1d6 reason"

# Case 1e: dirty baseline plus HEAD movement still fails closed without reset.
CASE1E="$TMPROOT/case1e"
REPO1E="$CASE1E/repo"
SCRIPTS1E="$CASE1E/scripts"
SESSION1E="$CASE1E/session"
CHECKS1E="$CASE1E/checks.log"
WRAPPER1E="$CASE1E/wrapper.sh"
make_repo "$REPO1E"
make_fixture_scripts "$SCRIPTS1E"
make_session "$SESSION1E"
printf 'synthetic checks failure\n' > "$CHECKS1E"
printf 'preexisting dirty work\n' > "$REPO1E/tracked.txt"
write_wrapper_commit_other_file "$WRAPPER1E"

case1e_result=$(run_case "$SCRIPTS1E" "$REPO1E" "$SESSION1E" "$CHECKS1E" "$WRAPPER1E")
case1e_rc=$(printf '%s\n' "$case1e_result" | sed -n '1p')
case1e_out=$(printf '%s\n' "$case1e_result" | sed -n '2,$p')
[[ "$case1e_rc" == "1" ]] || fail "case1e expected rc 1, got $case1e_rc"
assert_contains "$case1e_out" 'LINT_FIX_STATUS=failed' "case1e status"
assert_contains "$case1e_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1e reason"
case1e_dirty=$(cd "$REPO1E" && git diff --name-only)
[[ "$case1e_dirty" == "tracked.txt" ]] || fail "case1e expected dirty tracked.txt to survive, got: $case1e_dirty"

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
assert_contains "$case3_result" 'LINT_FIX_DELTA_PATHS_FILE=' "case3 delta paths file"

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

# Case 5: ship-pr-ci-merge site — success path (coder modifies file).
CASE5="$TMPROOT/case5"
REPO5="$CASE5/repo"
SCRIPTS5="$CASE5/scripts"
SESSION5="$CASE5/session"
CHECKS5="$CASE5/checks.log"
WRAPPER5="$CASE5/wrapper.sh"
make_repo "$REPO5"
make_fixture_scripts "$SCRIPTS5"
make_session "$SESSION5"
printf 'synthetic checks failure\n' > "$CHECKS5"
write_wrapper_modify_only "$WRAPPER5"

case5_result=$(run_case "$SCRIPTS5" "$REPO5" "$SESSION5" "$CHECKS5" "$WRAPPER5" ship-pr-ci-merge)
assert_contains "$case5_result" 'LINT_FIX_STATUS=applied' "case5 status"
assert_contains "$case5_result" 'LINT_FIX_SITE=ship-pr-ci-merge' "case5 site"
assert_contains "$case5_result" 'LINT_FIX_DELTA_PATHS_FILE=' "case5 delta paths file"

# Case 6: per-job site includes the display-only local argv in the prompt.
CASE6="$TMPROOT/case6"
REPO6="$CASE6/repo"
SCRIPTS6="$CASE6/scripts"
SESSION6="$CASE6/session"
CHECKS6="$CASE6/checks.log"
WRAPPER6="$CASE6/wrapper.sh"
ARGS6="$CASE6/target-args.txt"
make_repo "$REPO6"
make_fixture_scripts "$SCRIPTS6"
make_session "$SESSION6"
printf 'synthetic per-job failure\n' > "$CHECKS6"
printf '%s\n' env SKIP=agnix,lint-mermaid-fences,shellcheck make lint-only > "$ARGS6"
write_wrapper_modify_only "$WRAPPER6"

case6_result=$(run_case "$SCRIPTS6" "$REPO6" "$SESSION6" "$CHECKS6" "$WRAPPER6" ship-pr-ci-per-job "$ARGS6")
assert_contains "$case6_result" 'LINT_FIX_STATUS=applied' "case6 status"
assert_contains "$case6_result" 'LINT_FIX_SITE=ship-pr-ci-per-job' "case6 site"
case6_prompt=$(find "$SESSION6/lint-fix-loop" -name prompt.md -print -quit)
[[ -n "$case6_prompt" ]] || fail "case6 prompt was not written"
assert_contains "$(cat "$case6_prompt")" "local command \`env SKIP=agnix,lint-mermaid-fences,shellcheck make lint-only\` passes" "case6 prompt local command"

# Case 7: existing sites reject --target-cmd-args-file.
CASE7="$TMPROOT/case7"
REPO7="$CASE7/repo"
SCRIPTS7="$CASE7/scripts"
SESSION7="$CASE7/session"
CHECKS7="$CASE7/checks.log"
WRAPPER7="$CASE7/wrapper.sh"
ARGS7="$CASE7/target-args.txt"
make_repo "$REPO7"
make_fixture_scripts "$SCRIPTS7"
make_session "$SESSION7"
printf 'synthetic checks failure\n' > "$CHECKS7"
printf '%s\n' make lint-only > "$ARGS7"
write_wrapper_modify_only "$WRAPPER7"
case7_result=$(run_case "$SCRIPTS7" "$REPO7" "$SESSION7" "$CHECKS7" "$WRAPPER7" ship-pr-ci-initial "$ARGS7")
case7_rc=$(printf '%s\n' "$case7_result" | sed -n '1p')
[[ "$case7_rc" == "2" ]] || fail "case7 expected rc 2, got $case7_rc"

# Case 8: per-job target argv files reject control characters.
CASE8="$TMPROOT/case8"
REPO8="$CASE8/repo"
SCRIPTS8="$CASE8/scripts"
SESSION8="$CASE8/session"
CHECKS8="$CASE8/checks.log"
WRAPPER8="$CASE8/wrapper.sh"
ARGS8="$CASE8/target-args.txt"
make_repo "$REPO8"
make_fixture_scripts "$SCRIPTS8"
make_session "$SESSION8"
printf 'synthetic checks failure\n' > "$CHECKS8"
printf 'make\ntest-harnesses-3\001\n' > "$ARGS8"
write_wrapper_modify_only "$WRAPPER8"
case8_result=$(run_case "$SCRIPTS8" "$REPO8" "$SESSION8" "$CHECKS8" "$WRAPPER8" ship-pr-ci-per-job "$ARGS8")
case8_rc=$(printf '%s\n' "$case8_result" | sed -n '1p')
[[ "$case8_rc" == "2" ]] || fail "case8 expected rc 2, got $case8_rc"
assert_contains "$case8_result" '--target-cmd-args-file must not contain control characters' "case8 rejection message"

echo "test-lint-fix-loop: ok"
