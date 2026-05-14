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

run_helper() {
    "$HELPER" "$@" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# a) Happy path: pre-merge state → commits refreshed logs
# ---------------------------------------------------------------------------
(
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT

    # Set up a minimal git repo.
    git -C "$tmp" init -q
    git -C "$tmp" commit -q --allow-empty -m "init"

    # Build a state file that looks pre-merge (no MERGE_RESULT key).
    impl_tmpdir="$tmp/impl"
    mkdir -p "$impl_tmpdir/larch-logs"
    state_file="$impl_tmpdir/ship-pr-state.sh"
    run_id="TEST-RUN-$(date +%s)"
    printf 'RUN_ID=%s\nNO_LOGS_COMMIT=false\n' "$run_id" > "$state_file"

    # Create a dummy token-report file so larch-log.sh write has something to stage.
    mkdir -p "$impl_tmpdir/larch-logs/implement/$run_id"
    printf '{"vendors":[]}\n' > "$impl_tmpdir/larch-logs/implement/$run_id/token-report.json"
    git -C "$tmp" add -- "impl/larch-logs/implement/$run_id/token-report.json" 2>/dev/null || true

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
    printf '#!/usr/bin/env bash\nexit 0\n' > "$stub_dir/larch-log.sh"
    printf '#!/usr/bin/env bash\nprintf ""\n' > "$stub_dir/read-session-env-key.sh"
    chmod +x "$stub_dir"/*.sh

    # Run in the tmp repo dir so git operations resolve to it.
    out=$(cd "$tmp" && PATH="$stub_dir:$PATH" "$HELPER" \
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
) || fail "happy-path: exception"

# ---------------------------------------------------------------------------
# b) Post-merge state: MERGE_RESULT=merged → exits 0, no commit
# ---------------------------------------------------------------------------
(
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT

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
) || fail "post-merge: exception"

# ---------------------------------------------------------------------------
# c) Probe failure: state file missing → exits 0, no commit (fail-closed)
# ---------------------------------------------------------------------------
(
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT

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
) || fail "fail-closed: exception"

# ---------------------------------------------------------------------------
printf '\nResults: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
