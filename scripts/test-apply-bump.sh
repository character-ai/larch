#!/usr/bin/env bash
# test-apply-bump.sh - Offline regression tests for apply-bump.sh.
#
# Creates temporary git repositories and PATH-stubs the origin/main freshness
# reads so the bump application script can be exercised without network access.

set -euo pipefail

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

invoke_apply() {
    local repo_dir="$1"
    shift
    (cd "$repo_dir" && env "$@" bash "$REPO_ROOT/.claude/skills/bump-version/scripts/apply-bump.sh" --new-version 2.0.0)
}

invoke_dirty_apply() {
    local repo_dir="$1"
    printf '%s\n' dirty > "$repo_dir/untracked.txt"
    invoke_apply "$repo_dir" STUB_ORIGIN_PLUGIN_JSON='{"version":"1.0.0"}'
}

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
echo "Sub-test C: same-version origin rolls back before commit"
run_case "same_version" invoke_apply STUB_ORIGIN_PLUGIN_JSON='{"version":"2.0.0"}'
assert_exit_code "same_version" "1" "C: same-version exits 1"
assert_stdout_contains "same_version" "APPLIED=false" "C: same-version emits APPLIED=false"
assert_stdout_matches "same_version" "^ERROR=origin/main has already bumped to 2\\.0\\.0" "C: same-version error is stable"
assert_plugin_version "same_version" "1.0.0" "C: plugin.json restored"
assert_index_unstaged "same_version" "C: index unstaged"
assert_backup_absent "same_version" "C: backup removed"
assert_commit_count "same_version" "1" "C: no new commit"

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
if [[ "$FAIL_COUNT" -eq 0 ]]; then
    echo "PASS: scripts/test-apply-bump.sh ($PASS_COUNT assertions)"
    exit 0
fi

echo "FAIL: scripts/test-apply-bump.sh ($FAIL_COUNT failures, $PASS_COUNT passes)"
exit 1
