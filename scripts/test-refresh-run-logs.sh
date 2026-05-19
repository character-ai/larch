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

setup_plugin_stub() {
    local root=$1
    mkdir -p "$root/scripts"
    cp "$SCRIPT_DIR/../skills/implement/scripts/flush-execution-issues.sh" "$root/scripts/flush-execution-issues.sh"
    cp "$SCRIPT_DIR/../skills/implement/scripts/write-final-report.sh" "$root/scripts/write-final-report.sh"
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
    path="$log_root/$skill/$run_id/$batch.json"
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
    git -C "$tmp" commit -q --allow-empty -m "init"

    # Build a state file that looks pre-merge (no MERGE_RESULT key).
    impl_tmpdir="$tmp/impl"
    mkdir -p "$impl_tmpdir/larch-logs"
    state_file="$impl_tmpdir/ship-pr-state.sh"
    run_id="TEST-RUN-$(date +%s)"
    printf 'RUN_ID=%s\nNO_LOGS_COMMIT=false\nPR_URL=https://example.test/pr/123\nSTALL_TRACKING=false\n' "$run_id" > "$state_file"
    printf 'ISSUE_NUMBER=7\nRUN_ID=%s\n' "$run_id" > "$impl_tmpdir/parent-issue.md"
    printf 'REPO=owner/repo\n' > "$impl_tmpdir/session-env.sh"

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
    printf '#!/usr/bin/env bash\nprintf ""\n' > "$stub_dir/read-session-env-key.sh"
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
    if [ ! -s "$impl_tmpdir/execution-issues.md" ]; then
        pass "happy-path: execution issues log cleared after flush"
    else
        fail "happy-path: execution issues log cleared after flush"
    fi
    if grep -Fq 'PR: https://example.test/pr/123' "$impl_tmpdir/larch-logs/implement/$run_id/final-summary.md"; then
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
    git -C "$tmp" commit -q --allow-empty -m "init"

    impl_tmpdir="$tmp/impl"
    mkdir -p "$impl_tmpdir/larch-logs"
    state_file="$impl_tmpdir/ship-pr-state.sh"
    run_id="TEST-RUN-SKIP-$(date +%s)"
    printf 'RUN_ID=%s\nNO_LOGS_COMMIT=false\n' "$run_id" > "$state_file"

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
    if [ -f "$impl_tmpdir/larch-logs/implement/$run_id/final-summary.md" ]; then
        fail "step7a-skip refresh: final summary must not render before PR_URL exists"
    else
        pass "step7a-skip refresh: final summary gated on PR_URL"
    fi
    rm -rf "$tmp"
} || fail "step7a-skip refresh: exception"

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
