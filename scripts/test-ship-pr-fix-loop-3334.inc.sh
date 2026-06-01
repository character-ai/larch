# shellcheck shell=bash
# Offline regressions for #3334 (deterministic-default blind-rerun gate).
# Sourced from scripts/test-ship-pr.sh inside `if section_runs fix-loop; then`.

run_ship_pr_3334_deterministic_no_blind_rerun() {
    local root tmp call_dir rerun_sentinel launch_sentinel logs_count_file
    root=$(make_repo ship_pr_3334_deterministic_no_blind_rerun)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/3334-det.XXXXXX")
    rerun_sentinel="$call_dir/rerun-called"
    launch_sentinel="$call_dir/launch-called"
    logs_count_file="$call_dir/gh-run-logs-count"
    cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
    cat > "$root/scripts/gh-run-logs.sh" <<STUB
#!/usr/bin/env bash
count_file="$logs_count_file"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
printf 'FAIL AssertionError: expected True\n'
exit 0
STUB
    cat > "$root/scripts/ci-rerun-failed.sh" <<STUB
#!/usr/bin/env bash
touch "$rerun_sentinel"
printf 'RERUN_SUBMITTED=true\nALREADY_RUNNING=false\nERROR=\n'
STUB
    cat > "$root/scripts/ci-failed-jobs.sh" <<'STUB'
#!/usr/bin/env bash
printf 'FAILED_JOBS_COUNT=0\n'
exit 0
STUB
    for launcher in launch-cursor-ci.sh launch-codex-ci.sh launch-claude-ci.sh; do
        cat > "$root/scripts/$launcher" <<STUB
#!/usr/bin/env bash
touch "$launch_sentinel"
printf 'LAUNCHER_EXIT=1\n'
exit 0
STUB
        chmod +x "$root/scripts/$launcher"
    done
    chmod +x "$root/scripts/ci-wait.sh" "$root/scripts/gh-run-logs.sh" \
        "$root/scripts/ci-rerun-failed.sh" "$root/scripts/ci-failed-jobs.sh"
    write_state "$tmp/ship-pr-state.sh" ci-initial
    awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=0"; next}
         /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
         {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
        && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    if [ -f "$rerun_sentinel" ]; then
        fail "3334 deterministic: must not call ci-rerun-failed.sh"
        return
    fi
    if [ ! -f "$launch_sentinel" ]; then
        fail "3334 deterministic: fix loop must dispatch vendor tiers"
        return
    fi
    assert_rc "$tmp/rc" 4 "3334 deterministic: fix-loop exhaustion stalls (no blind rerun)"
    ok "3334 deterministic: skips blind rerun on deterministic ready log"
    rm -rf "$call_dir"
}

run_ship_pr_3334_upfront_ready_log_reuse() {
    local root tmp call_dir logs_count_file
    root=$(make_repo ship_pr_3334_upfront_ready_log_reuse)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/3334-reuse.XXXXXX")
    logs_count_file="$call_dir/gh-run-logs-count"
    cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
    cat > "$root/scripts/gh-run-logs.sh" <<STUB
#!/usr/bin/env bash
count_file="$logs_count_file"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
printf 'FAIL AssertionError: expected True\n'
exit 0
STUB
    cat > "$root/scripts/ci-failed-jobs.sh" <<'STUB'
#!/usr/bin/env bash
printf 'FAILED_JOBS_COUNT=0\n'
exit 0
STUB
    for launcher in launch-cursor-ci.sh launch-codex-ci.sh launch-claude-ci.sh; do
        cat > "$root/scripts/$launcher" <<'STUB'
#!/usr/bin/env bash
printf 'LAUNCHER_EXIT=1\n'
exit 0
STUB
        chmod +x "$root/scripts/$launcher"
    done
    chmod +x "$root/scripts/ci-wait.sh" "$root/scripts/gh-run-logs.sh" "$root/scripts/ci-failed-jobs.sh"
    write_state "$tmp/ship-pr-state.sh" ci-initial
    awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=0"; next}
         /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
         {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
        && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    logs_count=$(cat "$logs_count_file" 2>/dev/null || echo 0)
    if [ "$logs_count" -ne 1 ]; then
        fail "3334 upfront reuse: expected one gh-run-logs fetch (got $logs_count)"
        return
    fi
    ok "3334 upfront reuse: fix-loop iteration 1 reuses stashed ready logs"
    rm -rf "$call_dir"
}

run_ship_pr_3334_transient_gated_rerun() {
    local root tmp call_dir rerun_sentinel
    root=$(make_repo ship_pr_3334_transient_gated_rerun)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/3334-trans.XXXXXX")
    rerun_sentinel="$call_dir/rerun-called"
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
    cat > "$root/scripts/gh-run-logs.sh" <<'STUB'
#!/usr/bin/env bash
printf 'fatal: unable to access https://github.com/owner/repo/\n'
exit 0
STUB
    cat > "$root/scripts/ci-rerun-failed.sh" <<STUB
#!/usr/bin/env bash
touch "$rerun_sentinel"
printf 'RERUN_SUBMITTED=true\nALREADY_RUNNING=false\nERROR=\n'
STUB
    chmod +x "$root/scripts/ci-wait.sh" "$root/scripts/gh-run-logs.sh" "$root/scripts/ci-rerun-failed.sh"
    write_state "$tmp/ship-pr-state.sh" ci-initial
    awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=0"; next}
         /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
         {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
        && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    if [ ! -f "$rerun_sentinel" ]; then
        fail "3334 transient: expected ci-rerun-failed.sh on network-signature log"
        return
    fi
    assert_rc "$tmp/rc" 0 "3334 transient: gated blind rerun exits 0"
    ok "3334 transient: blind rerun fires for ready network-signature log"
    rm -rf "$call_dir"
}
