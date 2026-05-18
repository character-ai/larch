#!/usr/bin/env bash
# test-ship-pr.sh — Offline regression tests for scripts/ship-pr.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

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
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$root/scripts/lib-quiet.sh"
    cp "$REPO_ROOT/scripts/lib-net.sh" "$root/scripts/lib-net.sh"
    cp "$REPO_ROOT/scripts/lib-finalize-state-keys.sh" "$root/scripts/lib-finalize-state-keys.sh"
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
if [[ -n "${LARCH_LOG_STUB_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$LARCH_LOG_STUB_SENTINEL_DIR"
  printf 'APPLY_BUMP_LARCH_NO_LOGS_COMMIT=%s\n' "${LARCH_NO_LOGS_COMMIT:-unset}" >> "$LARCH_LOG_STUB_SENTINEL_DIR/env-calls.txt"
fi
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
    cat > "$root/scripts/gh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${STUB_GH_PR_VIEW_STATE:-}" != "" && "${1:-}" == pr && "${2:-}" == view ]]; then
  echo "$STUB_GH_PR_VIEW_STATE"
  exit 0
fi
exit "${STUB_GH_EXIT:-1}"
SH
    cat > "$root/scripts/tracking-issue-write.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "RENAMED=true"
SH
    for helper in create-pr.sh gh-pr-body-update.sh rebase-push.sh ci-rerun-failed.sh gh-run-logs.sh launch-cursor-ci.sh launch-codex-ci.sh append-token-record.sh git-commit.sh git-push.sh sanitize-mermaid-fragment.sh append-execution-issue.sh append-tool-failure.sh resolve-repo.sh; do
        cat > "$root/scripts/$helper" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "$(basename "$0")" in
  create-pr.sh)
    echo "PR_NUMBER=123"; echo "PR_URL=https://example.invalid/pr/123"; echo "PR_TITLE=Title"; echo "PR_STATUS=created" ;;
  sanitize-mermaid-fragment.sh)
    echo "STATUS=ok" ;;
  append-tool-failure.sh)
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --log) log=$2; shift 2 ;;
        --category) category=$2; shift 2 ;;
        --site) site=$2; shift 2 ;;
        --tool) tool=$2; shift 2 ;;
        --exit-code) exit_code=$2; shift 2 ;;
        --output-file) output_file=$2; shift 2 ;;
        --redact) shift ;;
        *) shift ;;
      esac
    done
    mkdir -p "$(dirname "${log:-/tmp/execution-issues.md}")"
    {
      printf '### %s\n\n' "${category:-Tool Failures}"
      printf -- '- Step %s — %s failed (exit %s)\n' "${site:-unknown}" "${tool:-unknown}" "${exit_code:-unknown}"
      cat "${output_file:-/dev/null}" 2>/dev/null || true
    } >> "${log:-/tmp/execution-issues.md}"
    echo "APPENDED=true"
    echo "LOG=${log:-}"
    ;;
  resolve-repo.sh)
    echo "REPO=owner/repo" ;;
  launch-cursor-ci.sh|launch-codex-ci.sh)
    if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
      mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
      printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
    fi
    ;;
esac
SH
    done
    cat > "$root/scripts/lint-fix-loop.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
site=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --site) site="$2"; shift 2 ;;
    --checks-log) shift 2 ;;
    --tmpdir) shift 2 ;;
    *) shift ;;
  esac
done
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s\n' "${site:-unknown}" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/lint-fix-sites.txt"
fi
echo "LINT_FIX_STATUS=${STUB_LINT_FIX_STATUS:-failed}"
echo "LINT_FIX_SITE=${site:-unknown}"
SH
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
    chmod +x "$root"/scripts/*.sh "$root"/scripts/gh "$root"/.claude/skills/bump-version/scripts/*.sh
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
    local state_tmpdir
    state_tmpdir=$(dirname "$file")
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
IMPLEMENT_TMPDIR=$state_tmpdir
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

assert_stdout_max_bytes() {
    local file=$1 max_bytes=$2 label=$3 actual
    actual=$(wc -c < "$file" | tr -d ' ')
    if [ "$actual" -le "$max_bytes" ]; then
        ok "$label"
    else
        fail "$label (expected <= $max_bytes bytes, got $actual)"
        sed 's/^/    stdout: /' "$file"
    fi
}

root=$(make_repo checks_fail)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
STUB_CHECKS_OK=false run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "checks failure exits 4"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "checks failure marks stall"

root=$(make_repo checks_verbose_failure)
tmp=$(make_tmpdir)
cat > "$root/scripts/run-relevant-checks-captured.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "STATUS=fail FAILURE_REASON=stubbed"
i=0
while [ "$i" -lt 200 ]; do
    printf 'VERBOSE_LEAK_MARKER_%03d=%080d\n' "$i" "$i"
    i=$((i + 1))
done
exit 1
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
write_state "$tmp/ship-pr-state.sh" checks
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "verbose checks failure exits 4"
assert_stdout_max_bytes "$tmp/stdout" 2048 "verbose checks failure keeps stdout under 2048 bytes"
if grep -q '^FAILURE_DETAIL_LOG=' "$tmp/stdout"; then
    ok "verbose checks failure emits diagnostic log envelope"
else
    fail "verbose checks failure emits diagnostic log envelope"
    sed 's/^/    stdout: /' "$tmp/stdout"
fi
if grep -q 'VERBOSE_LEAK_MARKER' "$tmp/stdout"; then
    fail "verbose checks failure does not replay helper output to stdout"
    sed 's/^/    stdout: /' "$tmp/stdout"
else
    ok "verbose checks failure does not replay helper output to stdout"
fi

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
assert_rc "$tmp/rc" 0 "ci-initial merge path exits 0 after same-invocation continuation"
assert_state_line "$tmp/ship-pr-state.sh" "CI_PASSED=true" "ci-initial merge sets CI_PASSED"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "ci-initial merge continues through ci-merge to PHASE=done"
if [ -f "$tmp/post-merge-sentinel" ]; then
    ok "ci-initial merge writes post-merge-sentinel during same-invocation continuation"
else
    fail "ci-initial merge should write post-merge-sentinel during same-invocation continuation"
fi

root=$(make_repo ci_bail)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
STUB_CI_ACTION=bail STUB_BAIL_REASON=fix-attempts-exhausted run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 3 "user-input bail exits 3"
assert_state_line "$tmp/ship-pr-state.sh" "BAIL_NEEDS_USER_INPUT=true" "user-input bail marks state"

root=$(make_repo version_published_pr_merged)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
PATH="$root/scripts:$PATH" STUB_MERGE_RESULT=version_already_published STUB_GH_PR_VIEW_STATE=MERGED run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "version_already_published + merged PR exits 0"
assert_state_line "$tmp/ship-pr-state.sh" "MERGE_RESULT=already_merged" "version_already_published + merged PR records already_merged"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "version_already_published + merged PR completes postmerge"
if [ -f "$tmp/post-merge-sentinel" ]; then
    ok "version_already_published + merged PR writes post-merge-sentinel"
else
    fail "version_already_published + merged PR should write post-merge-sentinel"
fi

root=$(make_repo version_published_pr_open)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-version-published-open.XXXXXX)
write_state "$tmp/ship-pr-state.sh" ci-merge
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$sentinel_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
else
    printf 'ACTION=already_merged\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=2\nELAPSED=1\n'
fi
STUB
for extra in drop-bump-commit.sh git-sync-local-main.sh git-force-push.sh; do
    printf '#!/usr/bin/env bash\nexit 0\n' > "$root/scripts/$extra"
done
chmod +x "$root/scripts/ci-wait.sh" \
         "$root/scripts/drop-bump-commit.sh" \
         "$root/scripts/git-sync-local-main.sh" \
         "$root/scripts/git-force-push.sh"
PATH="$root/scripts:$PATH" LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" STUB_MERGE_RESULT=version_already_published STUB_GH_PR_VIEW_STATE=OPEN run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "version_already_published + open PR exits 0 after re-bump"
if [ "$(cat "$sentinel_dir/ci-wait-count" 2>/dev/null || echo 0)" -ge 2 ]; then
    ok "version_already_published + open PR falls through to run_rebase_rebump"
else
    fail "version_already_published + open PR should fall through to run_rebase_rebump"
fi
rm -rf "$sentinel_dir"

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

# Postmerge manifest finalization: with PR_CLOSED=true, larch-log manifest runs.
root=$(make_repo postmerge_flush)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-postmerge-flush.XXXXXX)
mkdir -p "$tmp/larch-logs/implement/test-run"
printf '{"status":"in-progress"}\n' > "$tmp/larch-logs/implement/test-run/manifest.json"
write_state "$tmp/ship-pr-state.sh" postmerge
awk -F= '{if ($1=="PR_CLOSED") print "PR_CLOSED=true"; else print}' \
    "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-flush" 2>&1)
set -e
if [ -f "$sentinel_dir/larch-log-calls.txt" ]; then
    if grep -q "manifest" "$sentinel_dir/larch-log-calls.txt" && \
       grep -q "status=done" "$sentinel_dir/larch-log-calls.txt"; then
        ok "postmerge manifest finalization calls larch-log manifest with status=done when PR_CLOSED=true"
    else
        fail "postmerge manifest finalization: expected larch-log manifest with status=done; got: $(cat "$sentinel_dir/larch-log-calls.txt")"
    fi
else
    fail "postmerge manifest finalization: larch-log.sh stub was not called (PR_CLOSED=true path)"
fi
rm -rf "$sentinel_dir"

# Postmerge manifest finalization: missing manifest is synthesized before final status.
root=$(make_repo postmerge_missing_manifest)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-postmerge-recovery.XXXXXX)
mkdir -p "$tmp/larch-logs/implement/test-run"
write_state "$tmp/ship-pr-state.sh" postmerge
awk -F= '{if ($1=="PR_CLOSED") print "PR_CLOSED=true"; else print}' \
    "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-recovery" 2>&1)
set -e
if [ -f "$sentinel_dir/larch-log-calls.txt" ]; then
    if grep -q "^LARCH_LOG_ARGS=init" "$sentinel_dir/larch-log-calls.txt" && \
       grep -q "recovery_reason=manifest_lost_mid_run" "$sentinel_dir/larch-log-calls.txt" && \
       grep -q -- "--issue" "$sentinel_dir/larch-log-calls.txt"; then
        ok "postmerge manifest finalization synthesizes and tags a missing manifest (with --issue) before final status"
    else
        fail "postmerge missing-manifest recovery: expected init + partial tag + --issue; got: $(cat "$sentinel_dir/larch-log-calls.txt")"
    fi
else
    fail "postmerge missing-manifest recovery: larch-log.sh stub was not called"
fi
rm -rf "$sentinel_dir"

# Postmerge manifest finalization: with PR_CLOSED=false (draft/no-merge), no manifest update.
root=$(make_repo postmerge_no_flush)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-postmerge-noflush.XXXXXX)
write_state "$tmp/ship-pr-state.sh" postmerge
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-noflush" 2>&1)
set -e
if [ -f "$sentinel_dir/larch-log-calls.txt" ] && \
   grep -q "manifest" "$sentinel_dir/larch-log-calls.txt"; then
    fail "postmerge with PR_CLOSED=false should not call larch-log manifest"
else
    ok "postmerge with PR_CLOSED=false skips larch-log manifest finalization"
fi
rm -rf "$sentinel_dir"

# PR create flush: persist pr_number to the manifest and commit it on success.
root=$(make_repo pr_create_flush)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-pr-create-flush.XXXXXX)
write_state "$tmp/ship-pr-state.sh" pr-create
LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "pr-create happy path exits 0 after continuation"
if [ -f "$sentinel_dir/larch-log-calls.txt" ]; then
    if grep -q -- 'manifest --log-root .* --run-id test-run --field pr_number=123' "$sentinel_dir/larch-log-calls.txt" && \
       grep -q -- 'commit --log-root .* --run-id test-run' "$sentinel_dir/larch-log-calls.txt"; then
        ok "pr-create flush writes manifest pr_number and commits with matching run-id"
    else
        fail "pr-create flush: expected manifest pr_number + commit; got: $(cat "$sentinel_dir/larch-log-calls.txt")"
    fi
else
    fail "pr-create flush: larch-log.sh stub was not called"
fi
rm -rf "$sentinel_dir"

# Regression: CI-fix vendors receive the design plan path from session-env.
root=$(make_repo ci_fix_plan_file)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d /tmp/ship-pr-plan-ci-fix.XXXXXX)
plan_file="$tmp/design-plan.txt"
printf 'preserve this implementation plan\n' > "$plan_file"
printf 'PLAN_FILE=%s\n' "$plan_file" > "$tmp/session-env.sh"
cat > "$root/scripts/cursor" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/cursor" "$root/scripts/ci-wait.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "CI fix plan-file forwarding exits 0"
if [ -f "$call_dir/launcher-calls.txt" ] && \
   grep -q -- "launch-cursor-ci.sh .*--role fix .*--plan-file $plan_file" "$call_dir/launcher-calls.txt"; then
    ok "CI fix forwards --plan-file to cursor launcher"
else
    fail "CI fix should forward --plan-file to cursor launcher"
    sed 's/^/    launcher: /' "$call_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$call_dir"

# Regression: rebase conflict resolver vendors receive the design plan path.
root=$(make_repo conflict_plan_file)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d /tmp/ship-pr-plan-conflict.XXXXXX)
plan_file="$tmp/design-plan.txt"
printf 'preserve this implementation plan through conflict resolution\n' > "$plan_file"
printf 'PLAN_FILE=%s\n' "$plan_file" > "$tmp/session-env.sh"
cat > "$root/scripts/cursor" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
cat > "$root/scripts/rebase-push.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/rebase-push-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    echo "CONFLICT=true"
    exit 1
fi
exit 0
STUB
for extra in drop-bump-commit.sh git-sync-local-main.sh git-force-push.sh; do
    printf '#!/usr/bin/env bash\nexit 0\n' > "$root/scripts/$extra"
done
chmod +x "$root/scripts/cursor" \
         "$root/scripts/ci-wait.sh" \
         "$root/scripts/rebase-push.sh" \
         "$root/scripts/drop-bump-commit.sh" \
         "$root/scripts/git-sync-local-main.sh" \
         "$root/scripts/git-force-push.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "conflict resolver plan-file forwarding exits 0"
if [ -f "$call_dir/launcher-calls.txt" ] && \
   grep -q -- "launch-cursor-ci.sh .*--role resolve-conflict .*--plan-file $plan_file" "$call_dir/launcher-calls.txt"; then
    ok "conflict resolver forwards --plan-file to cursor launcher"
else
    fail "conflict resolver should forward --plan-file to cursor launcher"
    sed 's/^/    launcher: /' "$call_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$call_dir"

# Regression: second evaluate_failure (TRANSIENT_RETRIES=1) escalates to fix agent,
# not another rerun. Guards the threshold change in run_evaluate_failure (issue #1987).
root=$(make_repo ci_fix_escalation)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d /tmp/ship-pr-escalation.XXXXXX)

# ci-wait.sh: return evaluate_failure on first call, merge on subsequent calls.
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"

# ci-rerun-failed.sh: write sentinel if called — must NOT be called when TRANSIENT_RETRIES=1.
cat > "$root/scripts/ci-rerun-failed.sh" <<'STUB'
#!/usr/bin/env bash
printf 'RERUN_SUBMITTED=true\nALREADY_RUNNING=false\nERROR=\n'
touch "${RERUN_SENTINEL_FILE:-/tmp/rerun-called}"
STUB
chmod +x "$root/scripts/ci-rerun-failed.sh"

write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"

rerun_sentinel="$call_dir/rerun-called"
RERUN_SENTINEL_FILE="$rerun_sentinel" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "second evaluate_failure (TRANSIENT_RETRIES=1) exits 0 via fix-agent path"
if [ -f "$rerun_sentinel" ]; then
    fail "second evaluate_failure must NOT submit another rerun when TRANSIENT_RETRIES=1"
else
    ok "second evaluate_failure skips rerun and escalates to fix agent (TRANSIENT_RETRIES=1)"
fi
rm -rf "$call_dir"

# ──────────────────────────────────────────────────────────────────────────────
# --no-logs-commit: exported to lifecycle helper subprocess tree
# ──────────────────────────────────────────────────────────────────────────────

# Helper: override ci-wait.sh (rebase first call, merge second) and add stubs
# required by run_rebase_rebump that are not in write_stubs.
_make_rebase_stubs() {
    local root=$1 count_dir=$2
    cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$count_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
    for extra in drop-bump-commit.sh git-sync-local-main.sh git-force-push.sh; do
        printf '#!/usr/bin/env bash\nexit 0\n' > "$root/scripts/$extra"
    done
    chmod +x "$root/scripts/ci-wait.sh" \
             "$root/scripts/drop-bump-commit.sh" \
             "$root/scripts/git-sync-local-main.sh" \
             "$root/scripts/git-force-push.sh"
}

root=$(make_repo rebump_flush_enabled)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-rebump-enabled.XXXXXX)
# Use ci-initial so run_rebase_rebump fires (on ACTION=rebase) before any
# ci-merge entry; the scenario exits 0 after the second ci-wait
# returns ACTION=merge, advancing to ci-merge without entering postmerge.
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$sentinel_dir"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo --no-logs-commit false \
    > "$tmp/stdout-rebump-enabled" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-enabled"
set -e
assert_rc "$tmp/rc-rebump-enabled" 0 "run_rebase_rebump (--no-logs-commit false): ship-pr exits 0"
if [ -f "$sentinel_dir/env-calls.txt" ] && \
   grep -q "^APPLY_BUMP_LARCH_NO_LOGS_COMMIT=false$" "$sentinel_dir/env-calls.txt"; then
    ok "run_rebase_rebump: LARCH_NO_LOGS_COMMIT=false exported to apply-bump"
else
    fail "run_rebase_rebump: expected LARCH_NO_LOGS_COMMIT=false in apply-bump env"
fi
rm -rf "$sentinel_dir"

root=$(make_repo rebump_flush_suppressed)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-rebump-suppressed.XXXXXX)
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$sentinel_dir"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo --no-logs-commit true \
    > "$tmp/stdout-rebump-suppressed" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-suppressed"
set -e
assert_rc "$tmp/rc-rebump-suppressed" 0 "run_rebase_rebump (--no-logs-commit true): ship-pr exits 0"
if [ -f "$sentinel_dir/env-calls.txt" ] && \
   grep -q "^APPLY_BUMP_LARCH_NO_LOGS_COMMIT=true$" "$sentinel_dir/env-calls.txt"; then
    ok "run_rebase_rebump: LARCH_NO_LOGS_COMMIT=true exported to apply-bump"
else
    fail "run_rebase_rebump: expected LARCH_NO_LOGS_COMMIT=true in apply-bump env"
fi
rm -rf "$sentinel_dir"

# ──────────────────────────────────────────────────────────────────────────────
# run_evaluate_failure: inner local fix loop
# ──────────────────────────────────────────────────────────────────────────────

# Inner loop retries: first 2 local check attempts fail, 3rd succeeds -> exits 0.
root=$(make_repo ci_fix_local_retry)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/ship-pr-local-retry.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
cat > "$root/scripts/run-relevant-checks-captured.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/checks-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -lt 2 ]; then
    log_file="$call_dir/redacted-\$count.log"
    : > "\$log_file"
    echo "STATUS=fail FAILURE_REASON=stubbed"
    echo "REDACTED_LOG_FILE=\$log_file"
    exit 1
fi
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" STUB_LINT_FIX_STATUS=applied \
    SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo > "$tmp/stdout" 2>&1)
printf '%s' "$?" > "$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "local fix loop: 2 failures then success exits 0"
check_count=$(cat "$call_dir/checks-count" 2>/dev/null || echo 0)
if [ "$check_count" -eq 3 ]; then
    ok "local fix loop: ran 3 local check attempts before succeeding"
else
    fail "local fix loop: expected 3 check attempts, got $check_count"
fi
if grep -qx 'ship-pr-ci-initial' "$call_dir/lint-fix-sites.txt" 2>/dev/null; then
    ok "local fix loop: initial CI failures route through ship-pr-ci-initial lint-fix-loop site"
else
    fail "local fix loop: expected ship-pr-ci-initial lint-fix-loop site"
fi
rm -rf "$call_dir"

# Inner loop exhausted: all 3 attempts fail -> stall (exits 4).
root=$(make_repo ci_fix_exhausted)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/ship-pr-exhausted.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
chmod +x "$root/scripts/ci-wait.sh"
cat > "$root/scripts/run-relevant-checks-captured.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/checks-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
log_file="$call_dir/redacted-\$count.log"
: > "\$log_file"
echo "STATUS=fail FAILURE_REASON=stubbed"
echo "REDACTED_LOG_FILE=\$log_file"
exit 1
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" STUB_LINT_FIX_STATUS=applied \
    SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo > "$tmp/stdout" 2>&1)
printf '%s' "$?" > "$tmp/rc"
set -e
assert_rc "$tmp/rc" 4 "local fix loop: all 3 attempts exhausted stalls (exits 4)"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "local fix loop exhausted marks stall"
check_count=$(cat "$call_dir/checks-count" 2>/dev/null || echo 0)
if [ "$check_count" -eq 4 ]; then
    ok "local fix loop exhausted: ran a final verification after the third applied fix"
else
    fail "local fix loop exhausted: expected 4 check attempts, got $check_count"
fi
rm -rf "$call_dir"

# --- Transient-net exit-6 tests (Part C) ---

# Positive case 1: create-pr transient — stub emits a network error signature, expect exit 6.
root=$(make_repo transient_create_pr)
tmp=$(make_tmpdir)
cat > "$root/scripts/create-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "ERROR: Failed to push branch: fatal: unable to access 'https://github.com/owner/repo/'" >&2
echo "ERROR: Failed to push branch: fatal: unable to access 'https://github.com/owner/repo/'"
exit 1
STUB
chmod +x "$root/scripts/create-pr.sh"
write_state "$tmp/ship-pr-state.sh" pr-create
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 6 "transient create-pr: exits 6 on network signature"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "transient create-pr: STALL_TRACKING=false"

# Positive case 2: merge-pr transient — stub emits MERGE_RESULT=error with network signature.
root=$(make_repo transient_merge_pr)
tmp=$(make_tmpdir)
cat > "$root/scripts/merge-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "MERGE_RESULT=error"
echo "ERROR=git fetch origin main failed (network/auth issue)"
STUB
chmod +x "$root/scripts/merge-pr.sh"
write_state "$tmp/ship-pr-state.sh" ci-merge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 6 "transient merge-pr: exits 6 on network/auth signature"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "transient merge-pr: STALL_TRACKING=false"

# Positive case 3: ci-wait bail with transient network signature — expect exit 6.
root=$(make_repo transient_ci_wait_bail)
tmp=$(make_tmpdir)
cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "ACTION=bail"
echo "BAIL_REASON=ci-status.sh returned no valid output 3 times consecutively"
echo "CI_STATUS=pending"
echo "BEHIND_COUNT=0"
echo "FAILED_RUN_ID="
echo "ITERATION=0"
echo "ELAPSED=30"
STUB
chmod +x "$root/scripts/ci-wait.sh"
write_state "$tmp/ship-pr-state.sh" ci-merge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 6 "transient ci-wait bail: exits 6 on no-valid-output-3-times signature"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "transient ci-wait bail: STALL_TRACKING=false"

# Verify poll-budget exhaustion does NOT trigger exit 6 — it's not network-transient.
root=$(make_repo non_transient_ci_timeout)
tmp=$(make_tmpdir)
cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "ACTION=bail"
echo "BAIL_REASON=Poll budget (180 polls / 1800s) exhausted"
echo "CI_STATUS=pending"
echo "BEHIND_COUNT=0"
echo "FAILED_RUN_ID="
echo "ITERATION=0"
echo "ELAPSED=1800"
STUB
chmod +x "$root/scripts/ci-wait.sh"
write_state "$tmp/ship-pr-state.sh" ci-merge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "non-transient ci-wait timeout: exits 4 (poll budget exhaustion is not network-transient)"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "non-transient ci-wait timeout: STALL_TRACKING=true"

# Positive case 4: rebase-push transient — stub emits network error, expect exit 6.
root=$(make_repo transient_rebase_push)
tmp=$(make_tmpdir)
cat > "$root/scripts/rebase-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "REBASE_ERROR=git fetch origin main failed (network/auth issue)" >&2
echo "REBASE_ERROR=git fetch origin main failed (network/auth issue)"
exit 3
STUB
chmod +x "$root/scripts/rebase-push.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
# Set up so ci-wait returns rebase action
cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "ACTION=rebase"
echo "CI_STATUS=pending"
echo "BEHIND_COUNT=1"
echo "FAILED_RUN_ID="
echo "BAIL_REASON="
echo "ITERATION=0"
echo "ELAPSED=0"
STUB
chmod +x "$root/scripts/ci-wait.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 6 "transient rebase-push: exits 6 on network/auth signature"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "transient rebase-push: STALL_TRACKING=false"

# Negative case 1: merge-pr non-transient error — should exit 4.
root=$(make_repo non_transient_merge_pr)
tmp=$(make_tmpdir)
cat > "$root/scripts/merge-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "MERGE_RESULT=error"
echo "ERROR=could not parse origin/main published version (got: corrupt)"
STUB
chmod +x "$root/scripts/merge-pr.sh"
write_state "$tmp/ship-pr-state.sh" ci-merge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "non-transient merge-pr: exits 4 (not 6)"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "non-transient merge-pr: STALL_TRACKING=true"

# Negative case 2: create-pr non-transient error — should exit 4.
root=$(make_repo non_transient_create_pr)
tmp=$(make_tmpdir)
cat > "$root/scripts/create-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "ERROR: Body file not found: /tmp/pr-body.md"
exit 1
STUB
chmod +x "$root/scripts/create-pr.sh"
write_state "$tmp/ship-pr-state.sh" pr-create
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "non-transient create-pr: exits 4 (not 6)"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "non-transient create-pr: STALL_TRACKING=true"
assert_state_line "$tmp/execution-issues.md" "### Tool Failures" "non-transient create-pr: execution issue category logged"
if grep -Fq "Body file not found: /tmp/pr-body.md" "$tmp/execution-issues.md"; then
    ok "non-transient create-pr: captured stderr logged verbatim"
else
    fail "non-transient create-pr: captured stderr logged verbatim"
    sed 's/^/    /' "$tmp/execution-issues.md" 2>/dev/null || true
fi

# Issue #2233: MANIFEST_PATH entry validation contract tests.
# Confirms ship-pr.sh fails fast when MANIFEST_PATH points at a non-JSON file
# (e.g. the /design Step 5 manifest.env shell KV file mistakenly routed here),
# and accepts a valid JSON manifest.
root=$(make_repo manifest_path_non_json)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
# Simulate the failure mode: a shell KEY=VALUE file (design-side manifest.env)
# written into MANIFEST_PATH instead of the implement-side JSON manifest.
cat > "$tmp/fake-design-manifest.env" <<'KV'
PLAN_FILE=/tmp/x
TIMESTAMP=2026-05-17
SESSION_ID=abc
KV
sed -i.bak "s|^MANIFEST_PATH=.*|MANIFEST_PATH=$tmp/fake-design-manifest.env|" "$tmp/ship-pr-state.sh"
rm -f "$tmp/ship-pr-state.sh.bak"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 2 "non-JSON MANIFEST_PATH: ship-pr.sh exits 2 (die_usage) at entry"
if grep -q "MANIFEST_PATH must be empty or a readable JSON file" "$tmp/stderr"; then
    ok "non-JSON MANIFEST_PATH: diagnostic names the offending key"
else
    fail "non-JSON MANIFEST_PATH: diagnostic names the offending key"
    sed 's/^/    stderr: /' "$tmp/stderr"
fi

root=$(make_repo manifest_path_valid_json)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
printf '{"summary_bullets":["x"],"files_modified":[]}\n' > "$tmp/fake-implement-manifest.json"
sed -i.bak "s|^MANIFEST_PATH=.*|MANIFEST_PATH=$tmp/fake-implement-manifest.json|" "$tmp/ship-pr-state.sh"
rm -f "$tmp/ship-pr-state.sh.bak"
run_subject "$root" "$tmp" "$tmp/rc"
if grep -q "MANIFEST_PATH must be empty or a readable JSON file" "$tmp/stderr"; then
    fail "valid JSON MANIFEST_PATH: entry validation must not fire"
    sed 's/^/    stderr: /' "$tmp/stderr"
else
    ok "valid JSON MANIFEST_PATH: entry validation does not fire"
fi

root=$(make_repo manifest_path_empty)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
# write_state already sets MANIFEST_PATH= empty; just confirm the empty path passes.
run_subject "$root" "$tmp" "$tmp/rc"
if grep -q "MANIFEST_PATH must be empty or a readable JSON file" "$tmp/stderr"; then
    fail "empty MANIFEST_PATH: entry validation must not fire"
    sed 's/^/    stderr: /' "$tmp/stderr"
else
    ok "empty MANIFEST_PATH: entry validation does not fire"
fi

if [[ "$FAIL_COUNT" -ne 0 ]]; then
    echo "test-ship-pr: $FAIL_COUNT failure(s), $PASS_COUNT pass(es)" >&2
    exit 1
fi
echo "test-ship-pr: $PASS_COUNT pass(es)"
