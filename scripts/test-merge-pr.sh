#!/usr/bin/env bash
# test-merge-pr.sh - Offline regression tests for scripts/merge-pr.sh.
#
# Exercises the load-bearing merge-order and safety-gate behavior with a
# PATH-stubbed gh binary. The tests verify that merge-pr.sh reads merge state
# and CI status before any merge command, tries --admin first by default, falls
# back to a plain merge when --admin fails, and honors --no-admin-fallback as a
# plain-only path.

set -euo pipefail

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
printf '%s\n' "$*" >> "$LOG_FILE"

if [[ "$1" != "pr" ]]; then
    echo "unexpected gh command: $*" >&2
    exit 2
fi

case "$2" in
    view)
        printf '%s\n' "${GH_MERGE_STATE:-CLEAN}"
        ;;
    checks)
        if [[ -n "${GH_CHECKS_JSON:-}" ]]; then
            printf '%s\n' "$GH_CHECKS_JSON"
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

run_case() {
    local name="$1"
    shift

    local case_dir="$TMPDIR_BASE/$name"
    mkdir -p "$case_dir/bin"
    write_fake_gh "$case_dir/bin"

    GH_LOG_FILE="$case_dir/gh.log" \
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

assert_exact_command_count() {
    local case_name="$1"
    local command="$2"
    local expected="$3"
    local label="$4"

    local actual
    actual="$(grep -Fxc "$command" "$TMPDIR_BASE/$case_name/gh.log" 2>/dev/null || true)"
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
        sed 's/^/    gh: /' "$TMPDIR_BASE/$case_name/gh.log"
    fi
}

assert_exact_line_order() {
    local case_name="$1"
    local first="$2"
    local second="$3"
    local label="$4"

    local first_line
    local second_line
    first_line="$(grep -Fxn "$first" "$TMPDIR_BASE/$case_name/gh.log" | head -1 | cut -d: -f1)"
    second_line="$(grep -Fxn "$second" "$TMPDIR_BASE/$case_name/gh.log" | head -1 | cut -d: -f1)"

    if [[ -n "$first_line" && -n "$second_line" && "$first_line" -lt "$second_line" ]]; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    gh: /' "$TMPDIR_BASE/$case_name/gh.log"
    fi
}

echo "Sub-test A: default path tries --admin first"
run_case "admin_success" \
    env GH_MERGE_STATE=CLEAN GH_ADMIN_EXIT=0 GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "admin_success" "MERGE_RESULT=admin_merged" "A: admin success emits admin_merged"
assert_exact_command_count "admin_success" "pr merge 123 --repo owner/repo --squash --admin" "1" "A: exactly one --admin merge command"
assert_exact_command_count "admin_success" "pr merge 123 --repo owner/repo --squash" "0" "A: no plain fallback after admin success"
assert_exact_line_order "admin_success" "pr view 123 --repo owner/repo --json mergeStateStatus -q .mergeStateStatus" "pr merge 123 --repo owner/repo --squash --admin" "A: merge state is read before admin merge"
assert_exact_line_order "admin_success" "pr checks 123 --repo owner/repo --json name,state,bucket,link" "pr merge 123 --repo owner/repo --squash --admin" "A: checks are read before admin merge"

echo
echo "Sub-test B: default path falls back to plain merge when --admin fails"
run_case "admin_fallback" \
    env GH_MERGE_STATE=BLOCKED GH_ADMIN_EXIT=1 GH_ADMIN_OUTPUT="admin unsupported" GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "admin_fallback" "MERGE_RESULT=merged" "B: plain fallback success emits merged"
assert_exact_line_order "admin_fallback" "pr merge 123 --repo owner/repo --squash --admin" "pr merge 123 --repo owner/repo --squash" "B: --admin is attempted before plain fallback"

echo
echo "Sub-test C: --no-admin-fallback uses plain-only merge path"
run_case "no_admin_success" \
    env GH_MERGE_STATE=UNSTABLE GH_ADMIN_EXIT=0 GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo --no-admin-fallback
assert_stdout_contains "no_admin_success" "MERGE_RESULT=merged" "C: plain-only success emits merged"
assert_exact_command_count "no_admin_success" "pr merge 123 --repo owner/repo --squash --admin" "0" "C: --admin is not invoked"

echo
echo "Sub-test D: --no-admin-fallback policy denial"
run_case "no_admin_policy_denied" \
    env GH_MERGE_STATE=HAS_HOOKS GH_PLAIN_EXIT=1 GH_PLAIN_OUTPUT="review required" \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo --no-admin-fallback
assert_stdout_contains "no_admin_policy_denied" "MERGE_RESULT=policy_denied" "D: plain-only failure emits policy_denied"
assert_stdout_contains "no_admin_policy_denied" "ERROR=branch protection denied merge; --no-admin-fallback set" "D: policy_denied error string is stable"
assert_exact_command_count "no_admin_policy_denied" "pr merge 123 --repo owner/repo --squash --admin" "0" "D: --admin is not invoked on policy_denied"

echo
echo "Sub-test E: safety gates short-circuit before merge commands"
run_case "behind_gate" \
    env GH_MERGE_STATE=BEHIND GH_ADMIN_EXIT=0 GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "behind_gate" "MERGE_RESULT=main_advanced" "E1: BEHIND emits main_advanced"
assert_exact_command_count "behind_gate" "pr merge 123 --repo owner/repo --squash --admin" "0" "E1: BEHIND skips admin merge"
assert_exact_command_count "behind_gate" "pr merge 123 --repo owner/repo --squash" "0" "E1: BEHIND skips plain merge"

run_case "ci_gate" \
    env GH_MERGE_STATE=CLEAN GH_CHECKS_JSON='[{"name":"ci","bucket":"fail"}]' GH_ADMIN_EXIT=0 GH_PLAIN_EXIT=0 \
    bash "$REPO_ROOT/scripts/merge-pr.sh" --pr 123 --repo owner/repo
assert_stdout_contains "ci_gate" "MERGE_RESULT=ci_not_ready" "E2: non-pass CI emits ci_not_ready"
assert_exact_command_count "ci_gate" "pr merge 123 --repo owner/repo --squash --admin" "0" "E2: non-pass CI skips admin merge"
assert_exact_command_count "ci_gate" "pr merge 123 --repo owner/repo --squash" "0" "E2: non-pass CI skips plain merge"

echo
if [[ "$FAIL_COUNT" -eq 0 ]]; then
    echo "PASS: scripts/test-merge-pr.sh ($PASS_COUNT assertions)"
    exit 0
fi

echo "FAIL: scripts/test-merge-pr.sh ($FAIL_COUNT failures, $PASS_COUNT passes)"
exit 1
