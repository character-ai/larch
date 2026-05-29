#!/usr/bin/env bash
# test-refresh-run-logs.sh — Offline behavioral tests for refresh-run-logs.sh.
# Run via: make test-refresh-run-logs
set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/refresh-run-logs.sh"
PASS=0
FAIL=0

pass() { printf 'PASS: %s\n' "$1"; PASS=$((PASS + 1)); }
fail() { printf 'FAIL: %s\n' "$1"; FAIL=$((FAIL + 1)); }

# GitHub-hosted runners often have no global user.*; scope identity to the temp
# repo only (never --global) so init + refresh-run-logs commits succeed.
git_test_repo_identity() {
    git -C "$1" config user.email "larch-harness@users.noreply.github.com"
    git -C "$1" config user.name "Larch Harness"
}

setup_plugin_stub() {
    local root=$1
    mkdir -p "$root/scripts"
    cp "$SCRIPT_DIR/run-log-terminal-outcomes.inc.bash" "$root/scripts/run-log-terminal-outcomes.inc.bash"
    cp "$SCRIPT_DIR/../skills/implement/scripts/flush-execution-issues.sh" "$root/scripts/flush-execution-issues.sh"
    cp "$SCRIPT_DIR/../skills/implement/scripts/write-final-report.sh" "$root/scripts/write-final-report.sh"
    cp "$SCRIPT_DIR/render-run-summary.sh" "$root/scripts/render-run-summary.sh"
    cp "$SCRIPT_DIR/token-cost.sh" "$root/scripts/token-cost.sh"
    cp "$SCRIPT_DIR/lib-cost-line-format.sh" "$root/scripts/lib-cost-line-format.sh"
    cp "$SCRIPT_DIR/lib-quiet.sh" "$root/scripts/lib-quiet.sh"
    cp "$SCRIPT_DIR/lib-execution-issues.sh" "$root/scripts/lib-execution-issues.sh"
    cat > "$root/scripts/tracking-issue-summary.sh" <<'STUB'
#!/usr/bin/env bash
while [ $# -gt 0 ]; do
  case "$1" in
    --content-file) cp "$2" "${TRACKING_CONTENT_LOG:?}"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'COMMENT_URL=https://example.test/comment/final\n'
STUB
    cat > "$root/scripts/larch-log.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
cmd=${1:-}
shift || true
case "$cmd" in
  write)
    log_root=""; skill=""; run_id=""; batch=""; input_file=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --log-root) log_root=$2; shift 2 ;;
        --skill) skill=$2; shift 2 ;;
        --run-id) run_id=$2; shift 2 ;;
        --batch) batch=$2; shift 2 ;;
        --input-file) input_file=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    ext=".json"
    [ "$batch" = "session-transcript" ] && ext=".jsonl"
    [ "$batch" = "execution-issues" ] && ext=".ndjson"
    [ "$batch" = "review-findings" ] && ext=".ndjson"
    [ "$batch" = "review-panel-manifest" ] && ext=".ndjson"
    path="$log_root/$skill/$run_id/$batch$ext"
    mkdir -p "$(dirname "$path")"
    cp "$input_file" "$path"
    printf 'LOG_WRITTEN=true\n'
    ;;
  append)
    log_root=""; skill=""; run_id=""; batch=""; record_file=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --log-root) log_root=$2; shift 2 ;;
        --skill) skill=$2; shift 2 ;;
        --run-id) run_id=$2; shift 2 ;;
        --batch) batch=$2; shift 2 ;;
        --record-file) record_file=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    path="$log_root/$skill/$run_id/$batch.ndjson"
    mkdir -p "$(dirname "$path")"
    cat "$record_file" >> "$path"
    printf 'LOG_WRITTEN=true\n'
    ;;
  commit)
    printf 'UNCHANGED=false\n'
    ;;
  *)
    exit 0
    ;;
esac
STUB
    chmod +x "$root/scripts/"*.sh
}

run_helper() {
    "$HELPER" "$@" 2>/dev/null || true
}

run_flush_helper() {
    local plugin=$1 tmpdir=$2 log_root=$3 run_id=$4 issue_log=$5
    CLAUDE_PLUGIN_ROOT="$plugin" IMPLEMENT_TMPDIR="$tmpdir" \
        "$SCRIPT_DIR/../skills/implement/scripts/flush-execution-issues.sh" \
        --log-root "$log_root" --run-id "$run_id" --issue-log "$issue_log" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# a) Happy path: pre-merge state → commits refreshed logs
# ---------------------------------------------------------------------------
{
    tmp=$(mktemp -d)

    # Set up a minimal git repo.
    git -C "$tmp" init -q
    git_test_repo_identity "$tmp"
    git -C "$tmp" commit -q --allow-empty -m "init"
    git -C "$tmp" checkout -q -b feature-refresh-breadcrumbs

    # Build a state file that looks pre-merge (no MERGE_RESULT key).
    impl_tmpdir="$tmp/impl"
    mkdir -p "$impl_tmpdir/larch-logs"
    state_file="$impl_tmpdir/ship-pr-state.sh"
    run_id="TEST-RUN-$(date +%s)"
    printf 'RUN_ID=%s\nNO_LOGS_COMMIT=false\nPR_URL=https://example.test/pr/123\nPR_NUMBER=99\nMERGE=true\nDRAFT=false\nSTALL_TRACKING=false\nFORKED_TARGET=false\n' "$run_id" > "$state_file"
    printf 'ISSUE_NUMBER=7\nRUN_ID=%s\n' "$run_id" > "$impl_tmpdir/parent-issue.md"
    printf 'DESIGN_ONLY_DONE=false\n' > "$impl_tmpdir/finalize-state.sh"
    transcript_source="$impl_tmpdir/claude-source.env"
    transcript_raw="$impl_tmpdir/raw-transcript.jsonl"
    cat > "$transcript_source" <<EOF
TRANSCRIPT_PATH=$transcript_raw
EOF
    cat > "$transcript_raw" <<'EOF'
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"hello"}]}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"world"}]}}
EOF
    cat > "$impl_tmpdir/session-env.sh" <<EOF
REPO=owner/repo
REPO_UNAVAILABLE=false
LARCH_CLAUDE_SOURCE_FILE=$transcript_source
EOF

    # Create a dummy token-report file so larch-log.sh write has something to stage.
    mkdir -p "$impl_tmpdir/larch-logs/implement/$run_id"
    printf '{"vendors":[]}\n' > "$impl_tmpdir/larch-logs/implement/$run_id/token-report.json"
    git -C "$tmp" add -- "impl/larch-logs/implement/$run_id/token-report.json" 2>/dev/null || true

    plugin_root="$tmp/plugin"
    setup_plugin_stub "$plugin_root"

    # Stub token-report.sh, timing-report.sh, larch-log.sh, read-session-env-key.sh in PATH.
    stub_dir="$tmp/stubs"
    mkdir -p "$stub_dir"
    cat > "$stub_dir/token-report.sh"  << 'STUB'
#!/usr/bin/env bash
out=/dev/null
while [ $# -gt 0 ]; do
  case "$1" in --output) out="$2"; shift 2 ;; *) shift ;; esac
done
printf '{"vendors":[]}\n' > "$out"
STUB
    cat > "$stub_dir/timing-report.sh" << 'STUB'
#!/usr/bin/env bash
out=/dev/null
while [ $# -gt 0 ]; do
  case "$1" in --output) out="$2"; shift 2 ;; *) shift ;; esac
done
printf '{"workflow_path":"unknown","per_step":[],"total_seconds":0,"total_hms":"00:00:00","vendor_task_averages":[]}\n' > "$out"
STUB
    cat > "$stub_dir/larch-log.sh" <<'STUB'
#!/usr/bin/env bash
exec "$CLAUDE_PLUGIN_ROOT/scripts/larch-log.sh" "$@"
STUB
    cp "$SCRIPT_DIR/read-session-env-key.sh" "$stub_dir/read-session-env-key.sh"
    chmod +x "$stub_dir"/*.sh

    cat > "$impl_tmpdir/execution-issues.md" <<'ISSUES'
### Warnings

- refresh this too
ISSUES
    printf 'old-sha\n' > "$impl_tmpdir/.execution-issues-flushed.sha"

    # Run in the tmp repo dir so git operations resolve to it.
    out=$(cd "$tmp" && CLAUDE_PLUGIN_ROOT="$plugin_root" TRACKING_CONTENT_LOG="$tmp/final-summary-content.md" PATH="$stub_dir:$PATH" "$HELPER" \
        --state-file "$state_file" \
        --implement-tmpdir "$impl_tmpdir" 2>/dev/null || true)

    # Expect REFRESH_COMMITTED=true or REFRESH_COMMITTED=false (stub larch-log.sh writes nothing).
    if printf '%s\n' "$out" | grep -q '^REFRESH_COMMITTED='; then
        pass "happy-path: REFRESH_COMMITTED key present"
    elif printf '%s\n' "$out" | grep -q '^REFRESH_SKIPPED='; then
        fail "happy-path: unexpectedly skipped — $out"
    else
        fail "happy-path: unexpected output — $out"
    fi
    if [ -f "$impl_tmpdir/larch-logs/implement/$run_id/execution-issues.ndjson" ]; then
        pass "happy-path: execution issues flushed before commit"
    else
        fail "happy-path: execution issues flushed before commit"
    fi
    if [ -f "$impl_tmpdir/larch-logs/implement/$run_id/session-transcript.jsonl" ]; then
        pass "happy-path: session transcript refreshed before commit"
    else
        fail "happy-path: session transcript refreshed before commit"
    fi
    if grep -Fq 'session-transcript status=' "$impl_tmpdir/larch-logs/implement/$run_id/execution-issues.ndjson"; then
        pass "happy-path: transcript status warning flushed into execution issues batch"
    else
        fail "happy-path: transcript status warning flushed into execution issues batch"
    fi
    if [ ! -s "$impl_tmpdir/execution-issues.md" ]; then
        pass "happy-path: execution issues log cleared after flush"
    else
        fail "happy-path: execution issues log cleared after flush"
    fi
    if grep -Fq 'https://example.test/pr/123' "$impl_tmpdir/larch-logs/implement/$run_id/final-summary.md"; then
        pass "happy-path: final summary refreshed before commit"
    else
        fail "happy-path: final summary refreshed before commit"
    fi
    rm -rf "$tmp"
} || fail "happy-path: exception"

# ---------------------------------------------------------------------------
# a2) Step 7a skip still unlocks later pre-push execution-issues flush
# ---------------------------------------------------------------------------
{
    tmp=$(mktemp -d)

    git -C "$tmp" init -q
    git_test_repo_identity "$tmp"
    git -C "$tmp" commit -q --allow-empty -m "init"
    git -C "$tmp" checkout -q -b feature-refresh-breadcrumbs

    impl_tmpdir="$tmp/impl"
    mkdir -p "$impl_tmpdir/larch-logs"
    state_file="$impl_tmpdir/ship-pr-state.sh"
    run_id="TEST-RUN-SKIP-$(date +%s)"
    {
        printf 'RUN_ID=%s\n' "$run_id"
        printf 'NO_LOGS_COMMIT=false\n'
        printf 'STALL_TRACKING=false\n'
        printf 'FORKED_TARGET=false\n'
        printf 'MERGE=false\n'
        printf 'DRAFT=false\n'
        printf 'PR_NUMBER=0\n'
    } > "$state_file"
    printf 'ISSUE_NUMBER=1\nRUN_ID=%s\n' "$run_id" > "$impl_tmpdir/parent-issue.md"
    printf 'REPO=owner/repo\nREPO_UNAVAILABLE=false\n' > "$impl_tmpdir/session-env.sh"
    printf 'DESIGN_ONLY_DONE=false\n' > "$impl_tmpdir/finalize-state.sh"

    plugin_root="$tmp/plugin"
    setup_plugin_stub "$plugin_root"

    stub_dir="$tmp/stubs"
    mkdir -p "$stub_dir"
    cat > "$stub_dir/token-report.sh"  << 'STUB'
#!/usr/bin/env bash
out=/dev/null
while [ $# -gt 0 ]; do
  case "$1" in --output) out="$2"; shift 2 ;; *) shift ;; esac
done
printf '{"vendors":[]}\n' > "$out"
STUB
    cat > "$stub_dir/timing-report.sh" << 'STUB'
#!/usr/bin/env bash
out=/dev/null
while [ $# -gt 0 ]; do
  case "$1" in --output) out="$2"; shift 2 ;; *) shift ;; esac
done
printf '{"workflow_path":"unknown","per_step":[],"total_seconds":0,"total_hms":"00:00:00","vendor_task_averages":[]}\n' > "$out"
STUB
    cat > "$stub_dir/larch-log.sh" <<'STUB'
#!/usr/bin/env bash
exec "$CLAUDE_PLUGIN_ROOT/scripts/larch-log.sh" "$@"
STUB
    printf '#!/usr/bin/env bash\nprintf ""\n' > "$stub_dir/read-session-env-key.sh"
    chmod +x "$stub_dir"/*.sh

    run_flush_helper "$plugin_root" "$impl_tmpdir" "$impl_tmpdir/larch-logs" "$run_id" "$impl_tmpdir/execution-issues.md" >/dev/null
    cat > "$impl_tmpdir/execution-issues.md" <<'ISSUES'
### Warnings

- logged after an empty Step 7a checkpoint
ISSUES

    out=$(cd "$tmp" && CLAUDE_PLUGIN_ROOT="$plugin_root" PATH="$stub_dir:$PATH" "$HELPER" \
        --state-file "$state_file" \
        --implement-tmpdir "$impl_tmpdir" 2>/dev/null || true)

    if printf '%s\n' "$out" | grep -q '^REFRESH_COMMITTED='; then
        pass "step7a-skip refresh: REFRESH_COMMITTED key present"
    else
        fail "step7a-skip refresh: unexpected output — $out"
    fi
    if [ -f "$impl_tmpdir/larch-logs/implement/$run_id/execution-issues.ndjson" ]; then
        pass "step7a-skip refresh: execution issues flushed without prior batch"
    else
        fail "step7a-skip refresh: execution issues flushed without prior batch"
    fi
    if [ ! -s "$impl_tmpdir/execution-issues.md" ]; then
        pass "step7a-skip refresh: execution issues log cleared after flush"
    else
        fail "step7a-skip refresh: execution issues log cleared after flush"
    fi
    if [ -s "$impl_tmpdir/larch-logs/implement/$run_id/final-summary.md" ] \
        && grep -Fq '## /implement run' "$impl_tmpdir/larch-logs/implement/$run_id/final-summary.md"; then
        pass "step7a-skip refresh: final summary renders without PR_URL (partial upsert tolerance)"
    else
        fail "step7a-skip refresh: expected partial final-summary.md with run header"
    fi
    rm -rf "$tmp"
} || fail "step7a-skip refresh: exception"

# ---------------------------------------------------------------------------
# a3) Real larch-log commit publishes quiet logs during refresh and ignores
#     legacy breadcrumb stream sidecars.
# ---------------------------------------------------------------------------
{
    tmp=$(mktemp -d)

    git -C "$tmp" init -q
    git_test_repo_identity "$tmp"
    git -C "$tmp" commit -q --allow-empty -m "init"
    git -C "$tmp" checkout -q -b feature-refresh-breadcrumbs

    impl_tmpdir="$tmp/impl"
    mkdir -p "$impl_tmpdir/larch-logs" "$impl_tmpdir/breadcrumbs"
    state_file="$impl_tmpdir/ship-pr-state.sh"
    run_id="TEST-RUN-BREADCRUMBS-$(date +%s)"
    {
        printf 'RUN_ID=%s\n' "$run_id"
        printf 'NO_LOGS_COMMIT=false\n'
        printf 'STALL_TRACKING=false\n'
        printf 'FORKED_TARGET=false\n'
        printf 'MERGE=false\n'
        printf 'DRAFT=false\n'
        printf 'PR_NUMBER=0\n'
    } > "$state_file"
    printf 'ISSUE_NUMBER=1\nRUN_ID=%s\n' "$run_id" > "$impl_tmpdir/parent-issue.md"
    printf 'REPO=owner/repo\nREPO_UNAVAILABLE=false\n' > "$impl_tmpdir/session-env.sh"
    printf 'DESIGN_ONLY_DONE=false\n' > "$impl_tmpdir/finalize-state.sh"

    payload="$tmp/plan-goals-test.md"
    cat > "$payload" <<'EOF'
# Test payload
EOF
    (cd "$tmp" && "$SCRIPT_DIR/larch-log.sh" init --log-root "$impl_tmpdir/larch-logs" --skill implement --run-id "$run_id" --issue 42) >/dev/null
    (cd "$tmp" && "$SCRIPT_DIR/larch-log.sh" write --log-root "$impl_tmpdir/larch-logs" --skill implement --run-id "$run_id" --batch plan-goals-test --input-file "$payload") >/dev/null
    {
        printf 'larch:bc t=now d=0 p=1 s=test c=progress text=tmpdir %s\n' "$impl_tmpdir"
        printf '%s%s%s\n' '-----BEGIN RSA ' 'PRIVATE ' 'KEY-----'
        printf '%s%s\n' 'MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeK' 'Ls1Pt8Qu'
        printf '%s%s%s\n' '-----END RSA ' 'PRIVATE ' 'KEY-----'
    } > "$impl_tmpdir/breadcrumbs/refresh.ndjson"
    printf 'quiet sidecar\n' > "$impl_tmpdir/breadcrumbs/refresh.quiet"
    printf 'EXIT_CODE=0\n' > "$impl_tmpdir/breadcrumbs/refresh.done"
    printf 'EXIT_CODE=0\n' > "$impl_tmpdir/breadcrumbs/refresh.status"
    printf 'surfaced\n' > "$impl_tmpdir/breadcrumbs/refresh.surfaced"
    printf '5\n' > "$impl_tmpdir/breadcrumbs/refresh.bc-offset"
    printf 'refresh quiet log line\n' > "$impl_tmpdir/larch-quiet-refresh-run-logs.sh-24680.log"

    out=$(cd "$tmp" && CLAUDE_PLUGIN_ROOT="$SCRIPT_DIR/.." "$HELPER" \
        --state-file "$state_file" \
        --implement-tmpdir "$impl_tmpdir" 2>/dev/null || true)

    if printf '%s\n' "$out" | grep -q '^REFRESH_COMMITTED=true$'; then
        pass "refresh breadcrumbs: commit reported"
    else
        fail "refresh breadcrumbs: unexpected output — $out"
    fi
    committed="$tmp/larch-logs/implement/$run_id/breadcrumbs/refresh.ndjson"
    if [ ! -f "$committed" ]; then
        pass "refresh breadcrumbs: legacy ndjson breadcrumb not committed"
    else
        fail "refresh breadcrumbs: legacy ndjson breadcrumb must stay tmpdir-local"
    fi
    if [ ! -e "$tmp/larch-logs/implement/$run_id/breadcrumbs/refresh.quiet" ] \
        && [ ! -e "$tmp/larch-logs/implement/$run_id/breadcrumbs/refresh.done" ] \
        && [ ! -e "$tmp/larch-logs/implement/$run_id/breadcrumbs/refresh.status" ] \
        && [ ! -e "$tmp/larch-logs/implement/$run_id/breadcrumbs/refresh.surfaced" ] \
        && [ ! -e "$tmp/larch-logs/implement/$run_id/breadcrumbs/refresh.bc-offset" ]; then
        pass "refresh breadcrumbs: non-ndjson sidecars stay tmpdir-local"
    else
        fail "refresh breadcrumbs: sidecars must not be committed"
    fi
    quiet_committed="$tmp/larch-logs/implement/$run_id/breadcrumbs/larch-quiet-refresh-run-logs.sh-24680.log"
    if [ -f "$quiet_committed" ]; then
        pass "refresh breadcrumbs: session-root quiet log committed"
    else
        fail "refresh breadcrumbs: missing committed session-root quiet log"
    fi
    if grep -Fq 'refresh quiet log line' "$quiet_committed"; then
        pass "refresh breadcrumbs: committed quiet log preserves quiet-log content"
    else
        fail "refresh breadcrumbs: expected committed quiet log content"
    fi

    rm -rf "$tmp"
} || fail "refresh breadcrumbs: exception"

# ---------------------------------------------------------------------------
# b) Post-merge state: MERGE_RESULT=merged → exits 0, no commit
# ---------------------------------------------------------------------------
{
    tmp=$(mktemp -d)

    impl_tmpdir="$tmp/impl"
    mkdir -p "$impl_tmpdir"
    state_file="$impl_tmpdir/ship-pr-state.sh"
    printf 'RUN_ID=TEST-RUN\nMERGE_RESULT=merged\nNO_LOGS_COMMIT=false\n' > "$state_file"

    out=$(cd "$tmp" && "$HELPER" \
        --state-file "$state_file" \
        --implement-tmpdir "$impl_tmpdir" 2>/dev/null || true)

    if printf '%s\n' "$out" | grep -q 'REASON=post-merge'; then
        pass "post-merge: skipped with REASON=post-merge"
    else
        fail "post-merge: wrong output — $out"
    fi

    # Repeat with admin_merged.
    printf 'RUN_ID=TEST-RUN\nMERGE_RESULT=admin_merged\nNO_LOGS_COMMIT=false\n' > "$state_file"
    out=$(cd "$tmp" && "$HELPER" \
        --state-file "$state_file" \
        --implement-tmpdir "$impl_tmpdir" 2>/dev/null || true)
    if printf '%s\n' "$out" | grep -q 'REASON=post-merge'; then
        pass "post-merge (admin_merged): skipped with REASON=post-merge"
    else
        fail "post-merge (admin_merged): wrong output — $out"
    fi

    # Repeat with already_merged (external merge action).
    printf 'RUN_ID=TEST-RUN\nMERGE_RESULT=already_merged\nNO_LOGS_COMMIT=false\n' > "$state_file"
    out=$(cd "$tmp" && "$HELPER" \
        --state-file "$state_file" \
        --implement-tmpdir "$impl_tmpdir" 2>/dev/null || true)
    if printf '%s\n' "$out" | grep -q 'REASON=post-merge'; then
        pass "post-merge (already_merged): skipped with REASON=post-merge"
    else
        fail "post-merge (already_merged): wrong output — $out"
    fi
    rm -rf "$tmp"
} || fail "post-merge: exception"

# ---------------------------------------------------------------------------
# c) Probe failure: state file missing → exits 0, no commit (fail-closed)
# ---------------------------------------------------------------------------
{
    tmp=$(mktemp -d)

    impl_tmpdir="$tmp/impl"
    mkdir -p "$impl_tmpdir"
    # Deliberately do NOT create the state file.

    out=$(cd "$tmp" && "$HELPER" \
        --state-file "$impl_tmpdir/ship-pr-state.sh" \
        --implement-tmpdir "$impl_tmpdir" 2>/dev/null || true)

    if printf '%s\n' "$out" | grep -q 'REASON=state-file-missing-fail-closed'; then
        pass "fail-closed: missing state file → skip"
    else
        fail "fail-closed: wrong output — $out"
    fi
    rm -rf "$tmp"
} || fail "fail-closed: exception"

# ---------------------------------------------------------------------------
printf '\nResults: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
