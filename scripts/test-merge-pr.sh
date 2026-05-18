#!/usr/bin/env bash
# test-merge-pr.sh - Offline regression tests for scripts/merge-pr.sh.
#
# Exercises the load-bearing merge-order and safety-gate behavior with
# PATH-stubbed gh and git binaries. The tests verify that merge-pr.sh reads
# merge state and CI status before any merge command, evaluates the same-version
# bump gate before all merge paths, tries --admin first by default, falls back to
# plain merge when --admin fails, and honors --no-admin-fallback as a plain-only
# path.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_BASE="$(mktemp -d -t merge-pr-test.XXXXXX)"

# shellcheck disable=SC2329,SC2317  # body invoked via EXIT trap
cleanup() {
    rm -rf "$TMPDIR_BASE"
}
trap cleanup EXIT

PASS_COUNT=0
FAIL_COUNT=0

ok() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

write_fake_gh() {
    local bin_dir="$1"

    cat > "$bin_dir/gh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${GH_LOG_FILE:?GH_LOG_FILE required}"
TRACE_FILE="${TRACE_LOG_FILE:?TRACE_LOG_FILE required}"
printf '%s\n' "$*" >> "$LOG_FILE"
printf 'gh %s\n' "$*" >> "$TRACE_FILE"

if [[ "$1" != "pr" ]]; then
    echo "unexpected gh command: $*" >&2
    exit 2
fi

case "$2" in
    view)
        # Compound call: returns JSON with both mergeStateStatus and headRefOid.
        # __EMPTY__ sentinel → null mergeStateStatus so jq // "" yields "".
        # GH_VIEW_SECOND_*: if set, return it on 2nd+ call (flush recovery).
        HEAD_OID="${STUB_PR_HEAD_OID:-aaaa1111}"
        MERGE_STATE="${GH_MERGE_STATE:-CLEAN}"
        if [[ -n "${GH_VIEW_SECOND_HEAD_OID:-}" ]] && [[ -n "${GH_VIEW_COUNT_FILE:-}" ]]; then
            _count=$(( $(cat "$GH_VIEW_COUNT_FILE" 2>/dev/null || echo 0) + 1 ))
            printf '%s\n' "$_count" > "$GH_VIEW_COUNT_FILE"
            if [[ "$_count" -ge 2 ]]; then
                HEAD_OID="$GH_VIEW_SECOND_HEAD_OID"
                MERGE_STATE="${GH_VIEW_SECOND_MERGE_STATE:-$MERGE_STATE}"
            fi
        fi
        if [[ "$MERGE_STATE" == "__EMPTY__" ]]; then
            printf '{"mergeStateStatus":null,"headRefOid":"%s"}\n' "$HEAD_OID"
        else
            printf '{"mergeStateStatus":"%s","headRefOid":"%s"}\n' "$MERGE_STATE" "$HEAD_OID"
        fi
        ;;
    checks)
        CHECKS_JSON="${GH_CHECKS_JSON:-}"
        if [[ -n "${GH_CHECKS_SECOND_JSON:-}" ]] && [[ -n "${GH_CHECKS_COUNT_FILE:-}" ]]; then
            _count=$(( $(cat "$GH_CHECKS_COUNT_FILE" 2>/dev/null || echo 0) + 1 ))
            printf '%s\n' "$_count" > "$GH_CHECKS_COUNT_FILE"
            if [[ "$_count" -ge 2 ]]; then
                CHECKS_JSON="$GH_CHECKS_SECOND_JSON"
            fi
        fi
        if [[ -n "$CHECKS_JSON" ]]; then
            printf '%s\n' "$CHECKS_JSON"
        else
            printf '[{"name":"ci","bucket":"pass"}]\n'
        fi
        ;;
    merge)
        is_admin=false
        for arg in "$@"; do
            if [[ "$arg" == "--admin" ]]; then
                is_admin=true
                break
            fi
        done
        if $is_admin; then
            printf '%s\n' "${GH_ADMIN_OUTPUT:-admin merge output}"
            exit "${GH_ADMIN_EXIT:-0}"
        fi
        printf '%s\n' "${GH_PLAIN_OUTPUT:-plain merge output}"
        exit "${GH_PLAIN_EXIT:-0}"
        ;;
    *)
        echo "unexpected gh pr subcommand: $2" >&2
        exit 2
        ;;
esac
SH
    chmod +x "$bin_dir/gh"
}

write_fake_git() {
    local bin_dir="$1"

    cat > "$bin_dir/git" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${GIT_LOG_FILE:?GIT_LOG_FILE required}"
TRACE_FILE="${TRACE_LOG_FILE:?TRACE_LOG_FILE required}"
printf '%s\n' "$*" >> "$LOG_FILE"
printf 'git %s\n' "$*" >> "$TRACE_FILE"

case "$1" in
    rev-parse)
        if [[ "${2:-}" == "HEAD" ]]; then
            printf '%s\n' "${STUB_HEAD_OID:-aaaa1111}"
            exit 0
        fi
        # git rev-parse origin/<branch> — used by git-force-push.sh failure path
        if [[ "${2:-}" =~ ^origin/ ]]; then
            printf '%s\n' "${STUB_REMOTE_OID:-${STUB_HEAD_OID:-aaaa1111}}"
            exit 0
        fi
        ;;
    fetch)
        if [[ "${2:-}" == "origin" ]]; then
            exit "${STUB_FETCH_EXIT:-0}"
        fi
        ;;
    log)
        if [[ "${2:-}" == "--format=%s" && "${3:-}" == "origin/main..HEAD" ]]; then
            if [[ -n "${STUB_BRANCH_LOG:-}" ]]; then
                printf '%s\n' "$STUB_BRANCH_LOG"
            else
                printf '%s\n' "${STUB_LOCAL_SUBJECT:-Add feature X}"
            fi
            exit 0
        fi
        # git log --format=%s <pr_head_oid>..HEAD — flush-recovery range scan
        if [[ "${2:-}" == "--format=%s" && "${3:-}" =~ \.\.HEAD$ ]]; then
            printf '%s\n' "${STUB_FLUSH_AHEAD_LOG:-}"
            exit 0
        fi
        ;;
    diff)
        if [[ "${2:-}" == "--name-only" && "${3:-}" =~ \.\.HEAD$ ]]; then
            printf '%s\n' "${STUB_FLUSH_AHEAD_DIFF:-larch-logs/implement/run-1/manifest.json}"
            exit 0
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
    merge-base)
        if [[ "${2:-}" == "--is-ancestor" && "${3:-}" == "origin/main" && "${4:-}" == "HEAD" ]]; then
            exit "${STUB_ANCESTOR_EXIT:-0}"
        fi
        if [[ "${2:-}" == "--is-ancestor" && "${4:-}" == "HEAD" ]]; then
            exit "${STUB_PR_HEAD_ANCESTOR_EXIT:-${STUB_ANCESTOR_EXIT:-0}}"
        fi
        ;;
    symbolic-ref)
        # git symbolic-ref --short HEAD — used by git-force-push.sh
        if [[ "${2:-}" == "--short" && "${3:-}" == "HEAD" ]]; then
            printf '%s\n' "${STUB_BRANCH_NAME:-feature-branch}"
            exit 0
        fi
        ;;
    push)
        # git push --force-with-lease — used by git-force-push.sh
        exit "${STUB_PUSH_EXIT:-0}"
        ;;
esac

echo "unexpected git subcommand: $*" >&2
exit 3
SH
    chmod +x "$bin_dir/git"
}

run_case() {
    local name="$1"
    shift

    local case_dir="$TMPDIR_BASE/$name"
    mkdir -p "$case_dir/bin"
    write_fake_gh "$case_dir/bin"
    write_fake_git "$case_dir/bin"
    # No-op sleep so git-force-push.sh's 5s retry delay doesn't slow tests.
    printf '#!/usr/bin/env bash\nexit 0\n' > "$case_dir/bin/sleep"
    chmod +x "$case_dir/bin/sleep"
    : > "$case_dir/gh.log"
    : > "$case_dir/git.log"
    : > "$case_dir/trace.log"
    : > "$case_dir/gh_view_count"
    : > "$case_dir/gh_checks_count"

    GH_LOG_FILE="$case_dir/gh.log" \
    GIT_LOG_FILE="$case_dir/git.log" \
    TRACE_LOG_FILE="$case_dir/trace.log" \
    GH_VIEW_COUNT_FILE="$case_dir/gh_view_count" \
    GH_CHECKS_COUNT_FILE="$case_dir/gh_checks_count" \
    PATH="$case_dir/bin:$PATH" \
    "$@" > "$case_dir/stdout.log" 2> "$case_dir/stderr.log"
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

assert_command_count() {
    local case_name="$1"
    local log_name="$2"
    local command="$3"
    local expected="$4"
    local label="$5"

    local actual
    actual="$(grep -Fxc "$command" "$TMPDIR_BASE/$case_name/$log_name" 2>/dev/null || true)"
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
        sed "s/^/    $log_name: /" "$TMPDIR_BASE/$case_name/$log_name"
    fi
}

assert_no_merge_commands() {
    local case_name="$1"
    local label="$2"

    local actual
    actual="$(grep -Fc "pr merge 123 --repo owner/repo --squash" "$TMPDIR_BASE/$case_name/gh.log" 2>/dev/null || true)"
    if [[ "$actual" == "0" ]]; then
        ok "$label"
    else
        fail "$label (expected 0, got $actual)"
        sed 's/^/    gh: /' "$TMPDIR_BASE/$case_name/gh.log"
    fi
}

assert_line_order() {
    local case_name="$1"
    local log_name="$2"
    local first="$3"
    local second="$4"
    local label="$5"

    local first_line
    local second_line
    first_line="$(grep -m 1 -Fxn "$first" "$TMPDIR_BASE/$case_name/$log_name" | cut -d: -f1)"
    second_line="$(grep -m 1 -Fxn "$second" "$TMPDIR_BASE/$case_name/$log_name" | cut -d: -f1)"

    if [[ -n "$first_line" && -n "$second_line" && "$first_line" -lt "$second_line" ]]; then
        ok "$label"
    else
        fail "$label"
        sed "s/^/    $log_name: /" "$TMPDIR_BASE/$case_name/$log_name"
    fi
}

echo "Sub-test A: default path tries --admin first"
run_case "admin_success" \
    env GH_MERGE_STATE=CLEAN GH_ADMIN_EXIT=0 GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "admin_success" "MERGE_RESULT=admin_merged" "A: admin success emits admin_merged"
assert_command_count "admin_success" "gh.log" "pr merge 123 --repo owner/repo --squash --admin" "1" "A: exactly one --admin merge command"
assert_command_count "admin_success" "gh.log" "pr merge 123 --repo owner/repo --squash" "0" "A: no plain fallback after admin success"
assert_line_order "admin_success" "trace.log" "gh pr view 123 --repo owner/repo --json mergeStateStatus,headRefOid" "gh pr merge 123 --repo owner/repo --squash --admin" "A: merge state and head OID are read before admin merge (compound call)"
assert_line_order "admin_success" "trace.log" "gh pr checks 123 --repo owner/repo --json name,state,bucket,link" "gh pr merge 123 --repo owner/repo --squash --admin" "A: checks are read before admin merge"
assert_line_order "admin_success" "trace.log" "git fetch origin main --quiet" "gh pr merge 123 --repo owner/repo --squash --admin" "A: origin/main refresh happens before admin merge"
assert_line_order "admin_success" "trace.log" "git log --format=%s origin/main..HEAD" "gh pr merge 123 --repo owner/repo --squash --admin" "A: branch-range scan happens before admin merge"

echo
echo "Sub-test B: default path falls back to plain merge when --admin fails"
run_case "admin_fallback" \
    env GH_MERGE_STATE=BLOCKED GH_ADMIN_EXIT=1 GH_ADMIN_OUTPUT="admin unsupported" GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "admin_fallback" "MERGE_RESULT=merged" "B: plain fallback success emits merged"
assert_line_order "admin_fallback" "trace.log" "git log --format=%s origin/main..HEAD" "gh pr merge 123 --repo owner/repo --squash --admin" "B: same-version gate completes before --admin"
assert_line_order "admin_fallback" "trace.log" "gh pr merge 123 --repo owner/repo --squash --admin" "gh pr merge 123 --repo owner/repo --squash" "B: --admin is attempted before plain fallback"

echo
echo "Sub-test C: --no-admin-fallback uses plain-only merge path"
run_case "no_admin_success" \
    env GH_MERGE_STATE=UNSTABLE GH_ADMIN_EXIT=0 GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo --no-admin-fallback
assert_stdout_contains "no_admin_success" "MERGE_RESULT=merged" "C: plain-only success emits merged"
assert_command_count "no_admin_success" "gh.log" "pr merge 123 --repo owner/repo --squash --admin" "0" "C: --admin is not invoked"
assert_line_order "no_admin_success" "trace.log" "git log --format=%s origin/main..HEAD" "gh pr merge 123 --repo owner/repo --squash" "C: same-version gate completes before plain merge"

echo
echo "Sub-test D: --no-admin-fallback policy denial"
run_case "no_admin_policy_denied" \
    env GH_MERGE_STATE=HAS_HOOKS GH_PLAIN_EXIT=1 GH_PLAIN_OUTPUT="review required" \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo --no-admin-fallback
assert_stdout_contains "no_admin_policy_denied" "MERGE_RESULT=policy_denied" "D: plain-only failure emits policy_denied"
assert_stdout_contains "no_admin_policy_denied" "ERROR=branch protection denied merge; --no-admin-fallback set" "D: policy_denied error string is stable"
assert_command_count "no_admin_policy_denied" "gh.log" "pr merge 123 --repo owner/repo --squash --admin" "0" "D: --admin is not invoked on policy_denied"

echo
echo "Sub-test E: safety gates short-circuit before merge commands"
run_case "behind_gate" \
    env GH_MERGE_STATE=BEHIND GH_ADMIN_EXIT=0 GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "behind_gate" "MERGE_RESULT=main_advanced" "E1: BEHIND emits main_advanced"
assert_no_merge_commands "behind_gate" "E1: BEHIND skips merge commands"
assert_command_count "behind_gate" "git.log" "fetch origin main --quiet" "0" "E1: BEHIND skips same-version gate"

run_case "ci_gate" \
    env GH_MERGE_STATE=CLEAN GH_CHECKS_JSON='[{"name":"ci","bucket":"fail"}]' GH_ADMIN_EXIT=0 GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "ci_gate" "MERGE_RESULT=ci_not_ready" "E2: non-pass CI emits ci_not_ready"
assert_no_merge_commands "ci_gate" "E2: non-pass CI skips merge commands"
assert_command_count "ci_gate" "git.log" "fetch origin main --quiet" "0" "E2: non-pass CI skips same-version gate"

echo
echo "Sub-test F: default path emits admin_failed when both --admin and plain merges fail"
run_case "admin_failed" \
    env GH_MERGE_STATE=BLOCKED GH_ADMIN_EXIT=1 GH_ADMIN_OUTPUT="admin denied"$'\n'"second line" GH_PLAIN_EXIT=1 GH_PLAIN_OUTPUT="plain denied"$'\n'"second line" \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "admin_failed" "MERGE_RESULT=admin_failed" "F: both-failed emits admin_failed"
assert_line_order "admin_failed" "trace.log" "gh pr merge 123 --repo owner/repo --squash --admin" "gh pr merge 123 --repo owner/repo --squash" "F: --admin attempted before plain fallback"
ERROR_LINE_COUNT="$(grep -c '^ERROR=' "$TMPDIR_BASE/admin_failed/stdout.log" || true)"
if [[ "$ERROR_LINE_COUNT" == "1" ]]; then
    ok "F: ERROR is a single line"
else
    fail "F: ERROR is a single line (got $ERROR_LINE_COUNT)"
    sed 's/^/    stdout: /' "$TMPDIR_BASE/admin_failed/stdout.log"
fi

echo
echo "Sub-test G: empty / UNKNOWN mergeStateStatus short-circuits to error"
run_case "empty_state" \
    env GH_MERGE_STATE=__EMPTY__ GH_ADMIN_EXIT=0 GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "empty_state" "MERGE_RESULT=error" "G1: empty mergeStateStatus emits error"
assert_no_merge_commands "empty_state" "G1: empty mergeStateStatus skips merge commands"

run_case "unknown_state" \
    env GH_MERGE_STATE=UNKNOWN GH_ADMIN_EXIT=0 GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "unknown_state" "MERGE_RESULT=error" "G2: UNKNOWN mergeStateStatus emits error"
assert_no_merge_commands "unknown_state" "G2: UNKNOWN mergeStateStatus skips merge commands"

echo
echo "Sub-test H: same-version gate stops duplicate bump merges"
run_case "same_version" \
    env STUB_BRANCH_LOG="Bump version to 2.3.4" STUB_ORIGIN_PLUGIN_JSON='{"version":"2.3.4"}' \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "same_version" "MERGE_RESULT=version_already_published" "H1: same-version bump emits version_already_published"
assert_stdout_contains "same_version" "ERROR=origin/main HEAD already bumped to 2.3.4; rebase and re-bump" "H1: same-version error is stable"
assert_no_merge_commands "same_version" "H1: same-version skips merge commands"

run_case "same_version_ci_fix" \
    env STUB_BRANCH_LOG=$'Fix CI failure\nBump version to 2.3.4' STUB_ORIGIN_PLUGIN_JSON='{"version":"2.3.4"}' \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "same_version_ci_fix" "MERGE_RESULT=version_already_published" "H2: bump under CI-fix commit still emits version_already_published"
assert_no_merge_commands "same_version_ci_fix" "H2: bump under CI-fix skips merge commands"

echo
echo "Sub-test I: same-version gate no-op cases proceed to merge"
run_case "no_bump_commit" \
    env STUB_BRANCH_LOG="Fix implementation" GH_ADMIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "no_bump_commit" "MERGE_RESULT=admin_merged" "I1: no bump commit proceeds to normal merge"
assert_command_count "no_bump_commit" "git.log" "show origin/main:.claude-plugin/plugin.json" "0" "I1: no bump commit skips origin version read"

run_case "origin_diff_ancestor" \
    env STUB_BRANCH_LOG="Bump version to 2.3.4" STUB_ORIGIN_PLUGIN_JSON='{"version":"2.3.3"}' STUB_ANCESTOR_EXIT=0 GH_ADMIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "origin_diff_ancestor" "MERGE_RESULT=admin_merged" "I2: differing origin version with ancestor proceeds to merge"
assert_command_count "origin_diff_ancestor" "git.log" "merge-base --is-ancestor origin/main HEAD" "1" "I2: differing origin version checks ancestry"

run_case "origin_advanced" \
    env STUB_BRANCH_LOG="Bump version to 2.3.4" STUB_ORIGIN_PLUGIN_JSON='{"version":"2.3.3"}' STUB_ANCESTOR_EXIT=1 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "origin_advanced" "MERGE_RESULT=main_advanced" "I3: differing origin version with non-ancestor emits main_advanced"
assert_stdout_contains "origin_advanced" "ERROR=origin/main advanced to a different version; rebase needed" "I3: origin advanced error is stable"
assert_no_merge_commands "origin_advanced" "I3: origin advanced skips merge commands"

echo
echo "Sub-test J: same-version gate fails closed on stale or unsafe inputs"
run_case "fetch_fail" \
    env STUB_FETCH_EXIT=128 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "fetch_fail" "MERGE_RESULT=error" "J1: fetch failure emits error"
assert_stdout_contains "fetch_fail" "ERROR=git fetch origin main failed; cannot verify same-version race" "J1: fetch failure error is stable"
assert_no_merge_commands "fetch_fail" "J1: fetch failure skips merge commands"

run_case "oid_mismatch" \
    env STUB_HEAD_OID=aaaa1111 STUB_PR_HEAD_OID=bbbb2222 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "oid_mismatch" "MERGE_RESULT=error" "J2: OID mismatch emits error"
assert_stdout_contains "oid_mismatch" "ERROR=local HEAD (aaaa1111) does not match PR head OID (bbbb2222); refusing to evaluate same-version gate" "J2: OID mismatch error is stable"
assert_command_count "oid_mismatch" "git.log" "fetch origin main --quiet" "0" "J2: OID mismatch skips fetch"
assert_no_merge_commands "oid_mismatch" "J2: OID mismatch skips merge commands"

for case_name in origin_missing origin_malformed origin_null origin_missing_version; do
    case "$case_name" in
        origin_missing) origin_json="" ;;
        origin_malformed) origin_json="{not json" ;;
        origin_null) origin_json='{"version":null}' ;;
        origin_missing_version) origin_json='{}' ;;
    esac
    run_case "$case_name" \
        env STUB_BRANCH_LOG="Bump version to 2.3.4" STUB_ORIGIN_PLUGIN_JSON="$origin_json" \
        bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
    assert_stdout_contains "$case_name" "MERGE_RESULT=error" "J: $case_name emits error"
    assert_stdout_matches "$case_name" "^ERROR=could not parse origin/main published version" "J: $case_name parse error is stable"
    assert_no_merge_commands "$case_name" "J: $case_name skips merge commands"
done

echo
echo "Sub-test K: flush-only divergence recovers via force-push and merges"
run_case "flush_recovery_success" \
    env GH_MERGE_STATE=CLEAN \
    STUB_HEAD_OID=cccc3333 \
    STUB_PR_HEAD_OID=aaaa1111 \
    GH_VIEW_SECOND_HEAD_OID=cccc3333 \
    "STUB_FLUSH_AHEAD_LOG=chore(larch-logs): flush implement run ABC
chore(larch-logs): flush implement run DEF" \
    STUB_PUSH_EXIT=0 \
    STUB_BRANCH_NAME=feature-branch \
    STUB_REMOTE_OID=cccc3333 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "flush_recovery_success" "MERGE_RESULT=admin_merged" "K1: flush-only divergence recovers and proceeds to merge"
assert_command_count "flush_recovery_success" "git.log" "push --force-with-lease=refs/heads/feature-branch:aaaa1111" "1" "K1: force-push uses explicit expected lease exactly once"
assert_command_count "flush_recovery_success" "gh.log" "pr checks 123 --repo owner/repo --json name,state,bucket,link" "2" "K2: CI is re-checked after force-push recovery"

echo
echo "Sub-test L: flush-only divergence, force-push fails"
run_case "flush_recovery_push_fail" \
    env GH_MERGE_STATE=CLEAN \
    STUB_HEAD_OID=cccc3333 \
    STUB_PR_HEAD_OID=aaaa1111 \
    STUB_FLUSH_AHEAD_LOG="chore(larch-logs): flush implement run ABC" \
    STUB_PUSH_EXIT=1 \
    STUB_BRANCH_NAME=feature-branch \
    STUB_REMOTE_OID=dddd4444 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "flush_recovery_push_fail" "MERGE_RESULT=error" "L1: force-push failure emits error"
assert_stdout_matches "flush_recovery_push_fail" "ERROR=.*force-push failed" "L1: error mentions force-push failed"
assert_no_merge_commands "flush_recovery_push_fail" "L1: force-push failure skips merge commands"

echo
echo "Sub-test M: recovery re-checks CI after force-push"
run_case "flush_recovery_ci_pending" \
    env GH_MERGE_STATE=CLEAN \
    STUB_HEAD_OID=cccc3333 \
    STUB_PR_HEAD_OID=aaaa1111 \
    GH_VIEW_SECOND_HEAD_OID=cccc3333 \
    STUB_FLUSH_AHEAD_LOG="chore(larch-logs): flush implement run ABC" \
    GH_CHECKS_SECOND_JSON='[{"name":"ci","bucket":"pending"}]' \
    STUB_PUSH_EXIT=0 \
    STUB_BRANCH_NAME=feature-branch \
    STUB_REMOTE_OID=cccc3333 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "flush_recovery_ci_pending" "MERGE_RESULT=ci_not_ready" "M1: pending checks after recovery emit ci_not_ready"
assert_stdout_contains "flush_recovery_ci_pending" "ERROR=CI checks are not all passing after force-push recovery" "M2: post-recovery CI error is stable"
assert_no_merge_commands "flush_recovery_ci_pending" "M3: pending checks after recovery skip merge commands"

echo
echo "Sub-test N: mixed commits (flush + non-flush) preserve original OID error"
run_case "flush_recovery_mixed" \
    env GH_MERGE_STATE=CLEAN \
    STUB_HEAD_OID=cccc3333 \
    STUB_PR_HEAD_OID=aaaa1111 \
    "STUB_FLUSH_AHEAD_LOG=chore(larch-logs): flush implement run ABC
Fix some real bug" \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "flush_recovery_mixed" "MERGE_RESULT=error" "N1: mixed commits emit error"
assert_stdout_contains "flush_recovery_mixed" "ERROR=local HEAD (cccc3333) does not match PR head OID (aaaa1111); refusing to evaluate same-version gate" "N2: mixed commits preserve original OID error"
assert_no_merge_commands "flush_recovery_mixed" "N3: mixed commits skip merge commands"

echo
echo "Sub-test N2: flush-subject range with non-log paths preserves original OID error"
run_case "flush_recovery_non_log_paths" \
    env GH_MERGE_STATE=CLEAN \
    STUB_HEAD_OID=cccc3333 \
    STUB_PR_HEAD_OID=aaaa1111 \
    STUB_FLUSH_AHEAD_LOG="chore(larch-logs): flush implement run ABC" \
    "STUB_FLUSH_AHEAD_DIFF=larch-logs/implement/run-1/manifest.json
scripts/merge-pr.sh" \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "flush_recovery_non_log_paths" "MERGE_RESULT=error" "N2a: non-log path divergence emits error"
assert_stdout_contains "flush_recovery_non_log_paths" "ERROR=local HEAD (cccc3333) does not match PR head OID (aaaa1111); refusing to evaluate same-version gate" "N2b: non-log path divergence preserves original OID error"
assert_no_merge_commands "flush_recovery_non_log_paths" "N2c: non-log path divergence skips merge commands"

echo
echo "Sub-test O: non-ancestor flush-only range preserves original OID error"
run_case "flush_recovery_non_ancestor" \
    env GH_MERGE_STATE=CLEAN \
    STUB_HEAD_OID=cccc3333 \
    STUB_PR_HEAD_OID=aaaa1111 \
    STUB_FLUSH_AHEAD_LOG="chore(larch-logs): flush implement run ABC" \
    STUB_PR_HEAD_ANCESTOR_EXIT=1 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "flush_recovery_non_ancestor" "MERGE_RESULT=error" "O1: non-ancestor flush-only range emits error"
assert_stdout_contains "flush_recovery_non_ancestor" "ERROR=local HEAD (cccc3333) does not match PR head OID (aaaa1111); refusing to evaluate same-version gate" "O2: non-ancestor range preserves original OID error"
assert_no_merge_commands "flush_recovery_non_ancestor" "O3: non-ancestor range skips merge commands"

echo
echo "Sub-test P: >5 flush commits cap preserves original OID error"
run_case "flush_recovery_cap" \
    env GH_MERGE_STATE=CLEAN \
    STUB_HEAD_OID=cccc3333 \
    STUB_PR_HEAD_OID=aaaa1111 \
    "STUB_FLUSH_AHEAD_LOG=chore(larch-logs): flush implement run 1
chore(larch-logs): flush implement run 2
chore(larch-logs): flush implement run 3
chore(larch-logs): flush implement run 4
chore(larch-logs): flush implement run 5
chore(larch-logs): flush implement run 6" \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "flush_recovery_cap" "MERGE_RESULT=error" "P1: >5 flush commits emit error"
assert_stdout_contains "flush_recovery_cap" "ERROR=local HEAD (cccc3333) does not match PR head OID (aaaa1111); refusing to evaluate same-version gate" "P2: >5 flush commits preserve original OID error"
assert_no_merge_commands "flush_recovery_cap" "P3: >5 flush commits skip merge commands"

echo
if [[ "$FAIL_COUNT" -eq 0 ]]; then
    echo "PASS: scripts/test-merge-pr.sh ($PASS_COUNT assertions)"
    exit 0
fi

echo "FAIL: scripts/test-merge-pr.sh ($FAIL_COUNT failures, $PASS_COUNT passes)"
exit 1
