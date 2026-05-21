#!/usr/bin/env bash
# test-apply-bump.sh - Offline regression tests for apply-bump.sh.
#
# Creates temporary git repositories and PATH-stubs the origin/main freshness
# reads so the bump application script can be exercised without network access.

set -euo pipefail

# Isolate from an inherited larch quiet session (agent/CI may export
# LARCH_QUIET_BREADCRUMBS / LARCH_QUIET_BREADCRUMB_FD); stale FDs break
# emit_breadcrumb inside apply-bump.sh.
unset LARCH_QUIET_BREADCRUMBS LARCH_QUIET_BREADCRUMB_FD LARCH_QUIET_ACTIVE LARCH_QUIET_PID LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG 2>/dev/null || true
export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REAL_GIT="$(command -v git)"
TMPDIR_BASE="$(mktemp -d -t apply-bump-test.XXXXXX)"

# shellcheck disable=SC2329,SC2317  # body invoked via EXIT trap
cleanup() {
    rm -rf "$TMPDIR_BASE"
}
trap cleanup EXIT

PASS_COUNT=0
FAIL_COUNT=0

ok() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

write_fake_git() {
    local bin_dir="$1"

    cat > "$bin_dir/git" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${GIT_LOG_FILE:?GIT_LOG_FILE required}"
printf '%s\n' "$*" >> "$LOG_FILE"

case "$1" in
    fetch)
        if [[ "${2:-}" == "origin" && "${3:-}" == "main" ]]; then
            exit "${STUB_FETCH_EXIT:-0}"
        fi
        ;;
    show)
        if [[ "${2:-}" == "origin/main:.claude-plugin/plugin.json" ]]; then
            if [[ -n "${STUB_ORIGIN_VERSION_SEQ_FILE:-}" && -f "$STUB_ORIGIN_VERSION_SEQ_FILE" ]]; then
                _seq_ver=$(head -n 1 "$STUB_ORIGIN_VERSION_SEQ_FILE") || {
                    printf '%s\n' "stub git: failed to read origin version sequence head" >&2
                    exit 4
                }
                if [[ -n "$_seq_ver" ]]; then
                    if ! tail -n +2 "$STUB_ORIGIN_VERSION_SEQ_FILE" > "${STUB_ORIGIN_VERSION_SEQ_FILE}.tmp"; then
                        printf '%s\n' "stub git: sequence advance (tail) failed" >&2
                        exit 4
                    fi
                    if ! mv "${STUB_ORIGIN_VERSION_SEQ_FILE}.tmp" "$STUB_ORIGIN_VERSION_SEQ_FILE"; then
                        printf '%s\n' "stub git: sequence advance (mv) failed" >&2
                        exit 4
                    fi
                    printf '{"version":"%s"}' "$_seq_ver"
                else
                    printf '%s' '{"version":"1.0.0"}'
                fi
                exit 0
            fi
            if [[ "${STUB_ORIGIN_PLUGIN_JSON+x}" == "x" ]]; then
                printf '%s' "$STUB_ORIGIN_PLUGIN_JSON"
            else
                printf '%s' '{"version":"1.0.0"}'
            fi
            exit 0
        fi
        ;;
    status|add|commit|rev-parse|reset)
        exec "${REAL_GIT:?REAL_GIT required}" "$@"
        ;;
esac

echo "unexpected git subcommand: $*" >&2
exit 3
SH
    chmod +x "$bin_dir/git"
}

setup_temp_repo() {
    local case_name="$1"
    local repo_dir="$TMPDIR_BASE/$case_name/repo"

    mkdir -p "$repo_dir/.claude-plugin"
    printf '%s\n' '{"version":"1.0.0"}' > "$repo_dir/.claude-plugin/plugin.json"
    "$REAL_GIT" -C "$repo_dir" init -q
    "$REAL_GIT" -C "$repo_dir" config user.email "larch-test@example.invalid"
    "$REAL_GIT" -C "$repo_dir" config user.name "Larch Test"
    "$REAL_GIT" -C "$repo_dir" add .claude-plugin/plugin.json
    "$REAL_GIT" -C "$repo_dir" commit -m "Initial version" -q
    printf '%s\n' "$repo_dir"
}

run_case() {
    local case_name="$1"
    shift
    local runner="$1"
    shift

    local case_dir="$TMPDIR_BASE/$case_name"
    mkdir -p "$case_dir/bin"
    write_fake_git "$case_dir/bin"
    : > "$case_dir/git.log"

    local repo_dir
    repo_dir="$(setup_temp_repo "$case_name")"

    set +e
    GIT_LOG_FILE="$case_dir/git.log" \
    REAL_GIT="$REAL_GIT" \
    PATH="$case_dir/bin:$PATH" \
    "$runner" "$repo_dir" "$@" > "$case_dir/stdout.log" 2> "$case_dir/stderr.log"
    local rc=$?
    set -e
    printf '%s\n' "$rc" > "$case_dir/exit-code"
}

# shellcheck disable=SC2317  # invoked indirectly via run_case "$runner"
invoke_apply() {
    local repo_dir="$1"
    shift
    (cd "$repo_dir" && env "$@" bash "$REPO_ROOT/.claude/skills/bump-version/scripts/apply-bump.sh" --new-version 2.0.0)
}

# shellcheck disable=SC2317  # invoked indirectly via run_case "$runner"
invoke_apply_v() {
    local repo_dir="$1"
    local new_version="$2"
    shift 2
    (cd "$repo_dir" && env "$@" bash "$REPO_ROOT/.claude/skills/bump-version/scripts/apply-bump.sh" --new-version "$new_version")
}

# shellcheck disable=SC2317  # invoked indirectly via run_case "$runner"
invoke_dirty_apply() {
    local repo_dir="$1"
    printf '%s\n' dirty > "$repo_dir/untracked.txt"
    invoke_apply "$repo_dir" STUB_ORIGIN_PLUGIN_JSON='{"version":"1.0.0"}'
}

# shellcheck disable=SC2317  # invoked indirectly via run_case "$runner"
invoke_commit_failure_apply() {
    local repo_dir="$1"
    mkdir -p "$repo_dir/.git/hooks"
    printf '%s\n' "#!/usr/bin/env bash" "exit 1" > "$repo_dir/.git/hooks/pre-commit"
    chmod +x "$repo_dir/.git/hooks/pre-commit"
    invoke_apply "$repo_dir" STUB_ORIGIN_PLUGIN_JSON='{"version":"1.0.0"}'
}

assert_exit_code() {
    local case_name="$1"
    local expected="$2"
    local label="$3"

    local actual
    actual="$(cat "$TMPDIR_BASE/$case_name/exit-code")"
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
        sed 's/^/    stdout: /' "$TMPDIR_BASE/$case_name/stdout.log"
        sed 's/^/    stderr: /' "$TMPDIR_BASE/$case_name/stderr.log"
    fi
}

assert_stdout_contains() {
    local case_name="$1"
    local needle="$2"
    local label="$3"

    if grep -Fqx "$needle" "$TMPDIR_BASE/$case_name/stdout.log"; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    stdout: /' "$TMPDIR_BASE/$case_name/stdout.log"
    fi
}

assert_stdout_matches() {
    local case_name="$1"
    local pattern="$2"
    local label="$3"

    if grep -Eq "$pattern" "$TMPDIR_BASE/$case_name/stdout.log"; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    stdout: /' "$TMPDIR_BASE/$case_name/stdout.log"
    fi
}

assert_stderr_contains() {
    local case_name="$1"
    local needle="$2"
    local label="$3"

    if grep -Fq "$needle" "$TMPDIR_BASE/$case_name/stderr.log"; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    stderr: /' "$TMPDIR_BASE/$case_name/stderr.log"
    fi
}

assert_stdout_not_matches() {
    local case_name="$1"
    local pattern="$2"
    local label="$3"

    if ! grep -Eq "$pattern" "$TMPDIR_BASE/$case_name/stdout.log"; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    stdout: /' "$TMPDIR_BASE/$case_name/stdout.log"
    fi
}

assert_stdout_match_count() {
    local case_name="$1"
    local pattern="$2"
    local expected="$3"
    local label="$4"

    local actual
    actual=$(grep -Ec "$pattern" "$TMPDIR_BASE/$case_name/stdout.log" 2>/dev/null || echo 0)
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label (expected $expected matching lines, got $actual)"
        sed 's/^/    stdout: /' "$TMPDIR_BASE/$case_name/stdout.log"
    fi
}

assert_plugin_version() {
    local case_name="$1"
    local expected="$2"
    local label="$3"

    local repo_dir="$TMPDIR_BASE/$case_name/repo"
    local actual
    actual="$(jq -r '.version' "$repo_dir/.claude-plugin/plugin.json")"
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
    fi
}

assert_backup_absent() {
    local case_name="$1"
    local label="$2"

    if [[ ! -e "$TMPDIR_BASE/$case_name/repo/.claude-plugin/plugin.json.bump-backup" ]]; then
        ok "$label"
    else
        fail "$label"
    fi
}

assert_index_unstaged() {
    local case_name="$1"
    local label="$2"

    local repo_dir="$TMPDIR_BASE/$case_name/repo"
    local cached
    cached="$("$REAL_GIT" -C "$repo_dir" diff --cached --name-only)"
    if [[ -z "$cached" ]]; then
        ok "$label"
    else
        fail "$label"
        printf '%s\n' "$cached" | sed 's/^/    cached: /'
    fi
}

assert_commit_count() {
    local case_name="$1"
    local expected="$2"
    local label="$3"

    local repo_dir="$TMPDIR_BASE/$case_name/repo"
    local actual
    actual="$("$REAL_GIT" -C "$repo_dir" rev-list --count HEAD)"
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
    fi
}

assert_head_subject() {
    local case_name="$1"
    local expected="$2"
    local label="$3"

    local repo_dir="$TMPDIR_BASE/$case_name/repo"
    local actual
    actual="$("$REAL_GIT" -C "$repo_dir" log -1 --format=%s)"
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
    fi
}

echo "Sub-test A: success path commits the new version"
run_case "success" invoke_apply STUB_ORIGIN_PLUGIN_JSON='{"version":"1.0.0"}'
assert_exit_code "success" "0" "A: success exits 0"
assert_stdout_contains "success" "APPLIED=true" "A: success emits APPLIED=true"
assert_stdout_matches "success" "^COMMIT_SHA=[0-9a-f]+$" "A: success emits commit SHA"
assert_plugin_version "success" "2.0.0" "A: plugin.json has new version"
assert_backup_absent "success" "A: backup removed"
assert_commit_count "success" "2" "A: exactly one new commit"
assert_head_subject "success" "Bump version to 2.0.0" "A: bump commit subject is stable"

echo
echo "Sub-test B: fetch failure rolls back before commit"
run_case "fetch_failure" invoke_apply STUB_FETCH_EXIT=128
assert_exit_code "fetch_failure" "1" "B: fetch failure exits 1"
assert_stdout_contains "fetch_failure" "APPLIED=false" "B: fetch failure emits APPLIED=false"
assert_stdout_matches "fetch_failure" "^ERROR=git fetch origin main failed" "B: fetch failure error is stable"
assert_plugin_version "fetch_failure" "1.0.0" "B: plugin.json restored"
assert_index_unstaged "fetch_failure" "B: index unstaged"
assert_backup_absent "fetch_failure" "B: backup removed"
assert_commit_count "fetch_failure" "1" "B: no new commit"

echo
echo "Sub-test C: same-version origin retries and succeeds with a higher version"
run_case "same_version" invoke_apply STUB_ORIGIN_PLUGIN_JSON='{"version":"2.0.0"}'
assert_exit_code "same_version" "0" "C: same-version retries and exits 0"
assert_stdout_contains "same_version" "APPLIED=true" "C: same-version retries and emits APPLIED=true"
assert_stdout_matches "same_version" "^COMMIT_SHA=[0-9a-f]+$" "C: same-version retry emits commit SHA"
assert_plugin_version "same_version" "3.0.0" "C: plugin.json has bumped version after retry (MAJOR: 2.0.0 → 3.0.0)"
assert_backup_absent "same_version" "C: backup removed"
assert_commit_count "same_version" "2" "C: exactly one new commit after retry"
assert_head_subject "same_version" "Bump version to 3.0.0" "C: retry commit subject"
assert_index_unstaged "same_version" "C: index clean after commit"
assert_stdout_match_count "same_version" "^apply-bump: retry" "1" "C: exactly one breadcrumb emitted"

echo
echo "Sub-test D: differing origin version still commits"
run_case "different_origin" invoke_apply STUB_ORIGIN_PLUGIN_JSON='{"version":"1.5.0"}'
assert_exit_code "different_origin" "0" "D: differing origin exits 0"
assert_stdout_contains "different_origin" "APPLIED=true" "D: differing origin emits APPLIED=true"
assert_plugin_version "different_origin" "2.0.0" "D: plugin.json has new version"
assert_commit_count "different_origin" "2" "D: exactly one new commit"

echo
echo "Sub-test E: malformed origin plugin.json fails closed"
run_case "malformed_origin" invoke_apply STUB_ORIGIN_PLUGIN_JSON="{not json"
assert_exit_code "malformed_origin" "1" "E: malformed origin exits 1"
assert_stdout_contains "malformed_origin" "APPLIED=false" "E: malformed origin emits APPLIED=false"
assert_stdout_matches "malformed_origin" "^ERROR=could not parse origin/main published version" "E: malformed origin error is stable"
assert_plugin_version "malformed_origin" "1.0.0" "E: plugin.json restored"
assert_index_unstaged "malformed_origin" "E: index unstaged"
assert_backup_absent "malformed_origin" "E: backup removed"
assert_commit_count "malformed_origin" "1" "E: no new commit"

echo
echo "Sub-test F: dirty worktree fails before mutation"
run_case "dirty_worktree" invoke_dirty_apply
assert_exit_code "dirty_worktree" "1" "F: dirty worktree exits 1"
assert_stdout_contains "dirty_worktree" "APPLIED=false" "F: dirty worktree emits APPLIED=false"
assert_stdout_matches "dirty_worktree" "^ERROR=Working tree is not clean" "F: dirty worktree error is stable"
assert_stdout_matches "dirty_worktree" "phantom file warnings" "F: dirty worktree error mentions phantom guidance"
assert_plugin_version "dirty_worktree" "1.0.0" "F: plugin.json unchanged"
assert_commit_count "dirty_worktree" "1" "F: no new commit"

echo
echo "Sub-test G: commit failure rolls back after commit attempt"
run_case "commit_failure" invoke_commit_failure_apply
assert_exit_code "commit_failure" "1" "G: commit failure exits 1"
assert_stdout_contains "commit_failure" "APPLIED=false" "G: commit failure emits APPLIED=false"
assert_stdout_matches "commit_failure" "^ERROR=git commit failed; rolled back" "G: commit failure error is stable"
assert_plugin_version "commit_failure" "1.0.0" "G: plugin.json restored"
assert_index_unstaged "commit_failure" "G: index unstaged"
assert_backup_absent "commit_failure" "G: backup removed"
assert_commit_count "commit_failure" "1" "G: no new commit"

echo
echo "Sub-test H: regression guard retries and succeeds with a higher version"
run_case "regression_guard" invoke_apply STUB_ORIGIN_PLUGIN_JSON='{"version":"3.0.0"}'
assert_exit_code "regression_guard" "0" "H: regression retries and exits 0"
assert_stdout_contains "regression_guard" "APPLIED=true" "H: regression retries and emits APPLIED=true"
assert_stdout_matches "regression_guard" "^COMMIT_SHA=[0-9a-f]+$" "H: regression retry emits commit SHA"
assert_plugin_version "regression_guard" "4.0.0" "H: plugin.json has bumped version after retry (MAJOR: 3.0.0 → 4.0.0)"
assert_backup_absent "regression_guard" "H: backup removed"
assert_commit_count "regression_guard" "2" "H: exactly one new commit after retry"
assert_head_subject "regression_guard" "Bump version to 4.0.0" "H: retry commit subject"
assert_index_unstaged "regression_guard" "H: index clean after commit"
assert_stdout_match_count "regression_guard" "^apply-bump: retry" "1" "H: exactly one breadcrumb emitted"

echo
echo "Sub-test I: larch-internal untracked artifacts are tolerated"
# shellcheck disable=SC2317  # invoked indirectly via run_case "$runner"
invoke_internal_artifacts_apply() {
    local repo_dir="$1"
    # Place known-larch-internal untracked files in the repo working tree.
    printf 'sidecar data\n' > "$repo_dir/voter-claude.launcher-stderr"
    printf 'redacted log\n' > "$repo_dir/step-3-post-rebase.redacted.log"
    invoke_apply "$repo_dir" STUB_ORIGIN_PLUGIN_JSON='{"version":"1.0.0"}'
}
run_case "internal_artifacts" invoke_internal_artifacts_apply
assert_exit_code "internal_artifacts" "0" "I: larch-internal artifacts exit 0"
assert_stdout_contains "internal_artifacts" "APPLIED=true" "I: larch-internal artifacts emits APPLIED=true"
assert_stderr_contains "internal_artifacts" "WARN:" "I: larch-internal artifacts emits WARN on stderr"
assert_stderr_contains "internal_artifacts" "voter-claude.launcher-stderr" "I: WARN names launcher stderr artifact"
assert_stderr_contains "internal_artifacts" "step-3-post-rebase.redacted.log" "I: WARN names redacted log artifact"
assert_plugin_version "internal_artifacts" "2.0.0" "I: plugin.json has new version"
assert_commit_count "internal_artifacts" "2" "I: exactly one new commit"
assert_backup_absent "internal_artifacts" "I: backup removed"

echo
echo "Sub-test J: in-progress merge/rebase (unmerged paths) exits 4 with distinct error"
# shellcheck disable=SC2317  # invoked indirectly via run_case "$runner"
invoke_unmerged_apply() {
    local repo_dir="$1"
    # Create a genuine UU conflict state via REAL_GIT merge --no-commit.
    # The stub PATH git only handles specific subcommands; use REAL_GIT directly
    # for all setup operations so that checkout/merge/-C are supported.
    # apply-bump.sh's `git status` call passes through the stub to REAL_GIT and
    # will observe the UU state left by the merge conflict.
    local orig_branch
    orig_branch=$("$REAL_GIT" -C "$repo_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)
    # Create a side branch with a competing change
    "$REAL_GIT" -C "$repo_dir" checkout -b conflict-other >/dev/null 2>&1
    printf '{"version":"1.1.0","conflict":"theirs"}\n' > "$repo_dir/.claude-plugin/plugin.json"
    "$REAL_GIT" -C "$repo_dir" add .claude-plugin/plugin.json
    "$REAL_GIT" -C "$repo_dir" commit -q -m "theirs change"
    # Switch back to original branch and make a competing change
    "$REAL_GIT" -C "$repo_dir" checkout "$orig_branch" >/dev/null 2>&1
    printf '{"version":"2.0.0","conflict":"ours"}\n' > "$repo_dir/.claude-plugin/plugin.json"
    "$REAL_GIT" -C "$repo_dir" add .claude-plugin/plugin.json
    "$REAL_GIT" -C "$repo_dir" commit -q -m "ours change"
    # Merge to create the conflict state (--no-commit leaves UU in index)
    "$REAL_GIT" -C "$repo_dir" merge --no-commit conflict-other >/dev/null 2>&1 || true
    invoke_apply "$repo_dir" STUB_ORIGIN_PLUGIN_JSON='{"version":"1.0.0"}'
}
run_case "unmerged_paths" invoke_unmerged_apply
assert_exit_code "unmerged_paths" "4" "J: unmerged paths exits 4"
assert_stdout_contains "unmerged_paths" "APPLIED=false" "J: unmerged paths emits APPLIED=false"
assert_stdout_matches "unmerged_paths" "^ERROR=unmerged paths present:" "J: unmerged paths error is stable"

echo
echo "Sub-test K: single collision then success"
# plugin.json=1.0.0, --new-version 1.0.1 (PATCH); origin returns 1.0.1 once,
# then 1.0.0; retry re-classifies as PATCH relative to 1.0.1 → 1.0.2.
seq_file_k="$TMPDIR_BASE/origin-seq-k.txt"
printf '%s\n' "1.0.1" "1.0.0" > "$seq_file_k"
# shellcheck disable=SC2317
invoke_apply_v_k() {
    local repo_dir="$1"
    invoke_apply_v "$repo_dir" "1.0.1" STUB_ORIGIN_VERSION_SEQ_FILE="$seq_file_k"
}
run_case "retry_single" invoke_apply_v_k
assert_exit_code "retry_single" "0" "K: single collision exits 0"
assert_stdout_contains "retry_single" "APPLIED=true" "K: single collision emits APPLIED=true"
assert_stdout_matches "retry_single" "^COMMIT_SHA=[0-9a-f]+$" "K: single collision emits commit SHA"
assert_plugin_version "retry_single" "1.0.2" "K: plugin.json has version 1.0.2 after retry"
assert_backup_absent "retry_single" "K: backup removed"
assert_commit_count "retry_single" "2" "K: exactly one new commit"
assert_head_subject "retry_single" "Bump version to 1.0.2" "K: retry commit subject"
assert_stdout_match_count "retry_single" "^apply-bump: retry" "1" "K: exactly one breadcrumb emitted"

echo
echo "Sub-test L: multiple collisions then success"
# plugin.json=1.0.0, --new-version 1.0.1; origin advances 1.0.1, 1.0.2 before
# stabilising at 1.0.2 → two retries, lands at 1.0.3.
seq_file_l="$TMPDIR_BASE/origin-seq-l.txt"
printf '%s\n' "1.0.1" "1.0.2" "1.0.2" > "$seq_file_l"
# shellcheck disable=SC2317
invoke_apply_v_l() {
    local repo_dir="$1"
    invoke_apply_v "$repo_dir" "1.0.1" STUB_ORIGIN_VERSION_SEQ_FILE="$seq_file_l"
}
run_case "retry_multi" invoke_apply_v_l
assert_exit_code "retry_multi" "0" "L: multiple collisions exits 0"
assert_stdout_contains "retry_multi" "APPLIED=true" "L: multiple collisions emits APPLIED=true"
assert_stdout_matches "retry_multi" "^COMMIT_SHA=[0-9a-f]+$" "L: multiple collisions emits commit SHA"
assert_plugin_version "retry_multi" "1.0.3" "L: plugin.json has version 1.0.3 after retries"
assert_backup_absent "retry_multi" "L: backup removed"
assert_commit_count "retry_multi" "2" "L: exactly one new commit"
assert_head_subject "retry_multi" "Bump version to 1.0.3" "L: retry commit subject"
assert_stdout_match_count "retry_multi" "^apply-bump: retry" "2" "L: exactly two breadcrumbs emitted"

echo
echo "Sub-test M: cap exhaustion — loud fail after 10 retries"
# plugin.json=1.0.0, --new-version 1.0.1; origin advances on every attempt
# (11 entries: 1.0.1 through 1.0.11); all 10 retries collide, script bails.
seq_file_m="$TMPDIR_BASE/origin-seq-m.txt"
printf '%s\n' "1.0.1" "1.0.2" "1.0.3" "1.0.4" "1.0.5" \
              "1.0.6" "1.0.7" "1.0.8" "1.0.9" "1.0.10" "1.0.11" > "$seq_file_m"
# shellcheck disable=SC2317
invoke_apply_v_m() {
    local repo_dir="$1"
    invoke_apply_v "$repo_dir" "1.0.1" STUB_ORIGIN_VERSION_SEQ_FILE="$seq_file_m"
}
run_case "retry_cap" invoke_apply_v_m
assert_exit_code "retry_cap" "1" "M: cap exhaustion exits 1"
assert_stdout_contains "retry_cap" "APPLIED=false" "M: cap exhaustion emits APPLIED=false"
assert_stdout_matches "retry_cap" "^ERROR=origin/main bump race: could not land version after 10 retries" "M: cap exhaustion error is stable"
assert_plugin_version "retry_cap" "1.0.0" "M: plugin.json restored after cap exhaustion"
assert_index_unstaged "retry_cap" "M: index unstaged after cap exhaustion"
assert_backup_absent "retry_cap" "M: backup removed"
assert_commit_count "retry_cap" "1" "M: no new commit after cap exhaustion"
assert_stdout_match_count "retry_cap" "^apply-bump: retry" "10" "M: exactly 10 breadcrumbs emitted"

echo
echo "Sub-test N: no collision baseline — succeeds on first attempt, no retry"
# shellcheck disable=SC2317
invoke_apply_v_n() {
    local repo_dir="$1"
    invoke_apply_v "$repo_dir" "1.0.1" STUB_ORIGIN_PLUGIN_JSON='{"version":"1.0.0"}'
}
run_case "no_collision" invoke_apply_v_n
assert_exit_code "no_collision" "0" "N: no collision exits 0"
assert_stdout_contains "no_collision" "APPLIED=true" "N: no collision emits APPLIED=true"
assert_stdout_matches "no_collision" "^COMMIT_SHA=[0-9a-f]+$" "N: no collision emits commit SHA"
assert_plugin_version "no_collision" "1.0.1" "N: plugin.json has version 1.0.1"
assert_backup_absent "no_collision" "N: backup removed"
assert_commit_count "no_collision" "2" "N: exactly one new commit"
assert_stdout_not_matches "no_collision" "^apply-bump: retry" "N: no breadcrumb on first-attempt success"

echo
echo "Sub-test O: breadcrumb shape per retry"
# Verifies the exact breadcrumb format on a single-collision case.
seq_file_o="$TMPDIR_BASE/origin-seq-o.txt"
printf '%s\n' "1.0.1" "1.0.0" > "$seq_file_o"
# shellcheck disable=SC2317
invoke_apply_v_o() {
    local repo_dir="$1"
    invoke_apply_v "$repo_dir" "1.0.1" STUB_ORIGIN_VERSION_SEQ_FILE="$seq_file_o"
}
run_case "breadcrumb_shape" invoke_apply_v_o
assert_exit_code "breadcrumb_shape" "0" "O: breadcrumb-shape test exits 0"
assert_stdout_matches "breadcrumb_shape" \
    "^apply-bump: retry 1/10 origin/main=1\\.0\\.1 new-version=1\\.0\\.2$" \
    "O: breadcrumb line matches expected format"
assert_stdout_match_count "breadcrumb_shape" "^apply-bump: retry" "1" "O: exactly one breadcrumb line"

echo
if [[ "$FAIL_COUNT" -eq 0 ]]; then
    echo "PASS: scripts/test-apply-bump.sh ($PASS_COUNT assertions)"
    exit 0
fi

echo "FAIL: scripts/test-apply-bump.sh ($FAIL_COUNT failures, $PASS_COUNT passes)"
exit 1
