#!/usr/bin/env bash
# test-ship-pr.sh — Offline regression tests for scripts/ship-pr.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_BASE="$(mktemp -d -t ship-pr-test.XXXXXX)"
PASS_COUNT=0
FAIL_COUNT=0

cleanup() {
    rm -rf "$TMP_BASE"
}
trap cleanup EXIT

ok() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

write_subject() {
    local root=$1
    mkdir -p "$root/scripts" "$root/.claude/skills/bump-version/scripts"
    cp "$REPO_ROOT/scripts/ship-pr.sh" "$root/scripts/ship-pr.sh"
    chmod +x "$root/scripts/ship-pr.sh"
}

write_stubs() {
    local root=$1
    cat > "$root/scripts/run-relevant-checks-captured.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${STUB_CHECKS_OK:-true}" == true ]]; then
  echo "RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=full"
  exit 0
fi
echo "STATUS=fail FAILURE_REASON=stubbed"
exit 1
SH
    cat > "$root/.claude/skills/bump-version/scripts/classify-bump.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "CURRENT_VERSION=1.0.0"
echo "NEW_VERSION=1.0.1"
echo "BUMP_TYPE=PATCH"
echo "REASONING_FILE=${IMPLEMENT_TMPDIR:-/tmp}/bump-version-reasoning.md"
SH
    cat > "$root/.claude/skills/bump-version/scripts/apply-bump.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${STUB_APPLY_SAME_VERSION:-false}" == true ]]; then
  echo "APPLIED=false"
  echo "ERROR=origin/main has already bumped to 1.0.1; re-classify needed"
  exit 1
fi
echo "APPLIED=true"
echo "COMMIT_SHA=abc123"
SH
    cat > "$root/scripts/check-bump-version.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
    cat > "$root/scripts/implement-finalize.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  postbump)
    case "${STUB_POSTBUMP_STATUS:-ok}" in
      conflict)
        echo "RESUME_PHASE=force-push-gate"
        echo "CALLER_KIND=step8b_rebase"
        echo "STATUS=conflict"
        ;;
      rebase-failed)
        echo "STATUS=rebase-failed"
        ;;
      *)
        echo "STATUS=ok"
        ;;
    esac
    ;;
  postmerge)
    echo "LOCAL_CLEANUP_STATUS=skipped-merge-false"
    echo "VERIFY_MAIN_STATUS=skipped"
    ;;
  teardown)
    echo "FINALIZE_SUBCOMMAND=teardown"
    ;;
esac
SH
    cat > "$root/scripts/larch-log.sh" <<'SH'
#!/usr/bin/env bash
# Stub: record the explicit log root passed to this child process.
sentinel_dir="${LARCH_LOG_STUB_SENTINEL_DIR:-/tmp}"
printf 'LARCH_LOG_ARGS=%s\n' "$*" \
    >> "$sentinel_dir/larch-log-calls.txt"
SH
    cat > "$root/scripts/ci-wait.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "ACTION=${STUB_CI_ACTION:-merge}"
echo "CI_STATUS=pass"
echo "BEHIND_COUNT=0"
echo "FAILED_RUN_ID=${STUB_FAILED_RUN_ID:-}"
echo "BAIL_REASON=${STUB_BAIL_REASON:-}"
echo "ITERATION=1"
echo "ELAPSED=0"
SH
    cat > "$root/scripts/merge-pr.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "MERGE_RESULT=${STUB_MERGE_RESULT:-merged}"
echo "ERROR=${STUB_MERGE_ERROR:-}"
SH
    cat > "$root/scripts/tracking-issue-write.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "RENAMED=true"
SH
    for helper in create-pr.sh gh-pr-body-update.sh rebase-push.sh ci-rerun-failed.sh gh-run-logs.sh launch-cursor-ci.sh launch-codex-ci.sh append-token-record.sh git-commit.sh git-push.sh sanitize-mermaid-fragment.sh append-execution-issue.sh resolve-repo.sh; do
        cat > "$root/scripts/$helper" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "$(basename "$0")" in
  create-pr.sh)
    echo "PR_NUMBER=123"; echo "PR_URL=https://example.invalid/pr/123"; echo "PR_TITLE=Title"; echo "PR_STATUS=created" ;;
  sanitize-mermaid-fragment.sh)
    echo "STATUS=ok" ;;
  resolve-repo.sh)
    echo "REPO=owner/repo" ;;
esac
SH
    done
    cat > "$root/scripts/read-session-env-key.sh" <<'SH'
#!/usr/bin/env bash
while [[ $# -gt 0 ]]; do
    [[ "$1" == --default ]] && { printf '%s\n' "$2"; exit 0; }; shift
done
SH
    cat > "$root/scripts/token-report.sh" <<'SH'
#!/usr/bin/env bash
while [[ $# -gt 0 ]]; do
    [[ "$1" == --output ]] && { touch "$2"; break; }; shift
done
SH
    cat > "$root/scripts/tracking-issue-summary.sh" <<'SH'
#!/usr/bin/env bash
touch "${IMPLEMENT_TMPDIR:-/tmp}/summary-upsert-called"
SH
    chmod +x "$root"/scripts/*.sh "$root"/.claude/skills/bump-version/scripts/*.sh
}

make_repo() {
    local name=$1 root
    root="$TMP_BASE/$name"
    mkdir -p "$root"
    write_subject "$root"
    write_stubs "$root"
    git -C "$root" init -q
    git -C "$root" config user.email test@example.invalid
    git -C "$root" config user.name Test
    touch "$root/README.md"
    git -C "$root" add README.md
    git -C "$root" commit -q -m initial
    printf '%s\n' "$root"
}

make_tmpdir() {
    mktemp -d /tmp/claude-implement-ship-pr.XXXXXX
}

write_state() {
    local file=$1 phase=$2
    cat > "$file" <<EOF
PHASE=$phase
BRANCH_NAME=master
ISSUE_NUMBER=7
RUN_ID=test-run
REPO=owner/repo
REPO_UNAVAILABLE=false
FORKED_TARGET=false
HAS_BUMP=true
BUMP_TYPE=NONE
NEW_VERSION=
MERGE=true
DRAFT=false
DEFERRED=false
PR_CLOSED=false
DONE_RENAME_APPLIED=false
STALL_TRACKING=false
STALL_STEP=
BAIL_NEEDS_USER_INPUT=false
BAIL_REASON=
CI_PASSED=false
OOS_PENDING=false
PR_NUMBER=123
PR_URL=https://example.invalid/pr/123
PR_TITLE=Title
RESUME_PHASE=
CALLER_KIND=
REBASE_COUNT=0
FIX_ATTEMPTS=0
ITERATION=0
TRANSIENT_RETRIES=0
FAILED_RUN_ID=
MANIFEST_PATH=
TOOL_LABEL=claude
DESIGN_ONLY_DONE=false
EXPECTED_SESSION_ID=
EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-test-
EOF
}

run_subject() {
    local root=$1 tmpdir=$2 rc_file=$3
    set +e
    (cd "$root" && CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmpdir" "$root/scripts/ship-pr.sh" --state-file "$tmpdir/ship-pr-state.sh" --implement-tmpdir "$tmpdir" --merge true --draft false --forked false --repo owner/repo > "$tmpdir/stdout" 2> "$tmpdir/stderr")
    local rc=$?
    set -e
    printf '%s' "$rc" > "$rc_file"
}

assert_state_line() {
    local file=$1 line=$2 label=$3
    if grep -qxF "$line" "$file"; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    state: /' "$file"
    fi
}

assert_rc() {
    local file=$1 expected=$2 label=$3 actual
    actual=$(cat "$file")
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
    fi
}

root=$(make_repo checks_fail)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
STUB_CHECKS_OK=false run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "checks failure exits 4"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "checks failure marks stall"

root=$(make_repo postbump_conflict)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" bump
STUB_POSTBUMP_STATUS=conflict run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 5 "postbump conflict exits 5"
assert_state_line "$tmp/ship-pr-state.sh" "CALLER_KIND=step8b_rebase" "postbump conflict preserves caller kind"

root=$(make_repo same_version)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" bump
STUB_APPLY_SAME_VERSION=true run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 5 "same-version bump exits 5"
assert_state_line "$tmp/ship-pr-state.sh" "CALLER_KIND=step8b_same_version" "same-version writes caller kind"

root=$(make_repo ci_initial)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-initial
STUB_CI_ACTION=merge run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "ci-initial merge checkpoint exits 0"
assert_state_line "$tmp/ship-pr-state.sh" "CI_PASSED=true" "ci-initial merge sets CI_PASSED"

root=$(make_repo ci_bail)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
STUB_CI_ACTION=bail STUB_BAIL_REASON=fix-attempts-exhausted run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 3 "user-input bail exits 3"
assert_state_line "$tmp/ship-pr-state.sh" "BAIL_NEEDS_USER_INPUT=true" "user-input bail marks state"

root=$(make_repo malformed)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
printf 'lowercase_bad=true\n' >> "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 2 "malformed lowercase state exits 2"

root=$(make_repo postmerge)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" postmerge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "postmerge phase exits 0"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "postmerge writes PHASE=done before teardown"
if [ -f "$tmp/summary-upsert-called" ]; then
    fail "postmerge should not call tracking-issue-summary.sh (owned by prompt-side Step 18)"
else
    ok "postmerge does not call tracking-issue-summary.sh (Step 18 owns it)"
fi

# Regression test: ship-pr.sh passes an explicit larch-log root even when
# invoked from a fresh shell without IMPLEMENT_TMPDIR in the environment.
root=$(make_repo export_regression)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-export-test.XXXXXX)
write_state "$tmp/ship-pr-state.sh" ci-merge
# Run WITHOUT IMPLEMENT_TMPDIR in the environment (simulates fresh-shell invocation).
set +e
(cd "$root" && unset IMPLEMENT_TMPDIR && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-export" 2> "$tmp/stderr-export")
set -e
if [ -f "$sentinel_dir/larch-log-calls.txt" ]; then
    if grep -q -- "--log-root $tmp/larch-logs" "$sentinel_dir/larch-log-calls.txt"; then
        ok "explicit --log-root passed to larch-log.sh in ci-merge flush (fresh shell)"
    else
        fail "explicit --log-root missing for larch-log.sh; got: $(cat "$sentinel_dir/larch-log-calls.txt")"
    fi
else
    fail "larch-log.sh stub was not called during ci-merge flush"
fi
rm -rf "$sentinel_dir"

if [[ "$FAIL_COUNT" -ne 0 ]]; then
    echo "test-ship-pr: $FAIL_COUNT failure(s), $PASS_COUNT pass(es)" >&2
    exit 1
fi
echo "test-ship-pr: $PASS_COUNT pass(es)"
