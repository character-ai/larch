# shellcheck shell=bash
# Offline regressions for #2632 (run_ci_fix_vendor 3-tier + gh-run-logs).
# Sourced from scripts/test-ship-pr.sh inside `if section_runs fix-loop; then`.

# 4) LAUNCHER_EXIT=124 with wrapper rc 0 → Codex runs; failure log mentions launcher_exit=124.
run_ship_pr_2632_t4() {
    local root tmp call_dir
    root=$(make_repo ci_fix_vendor_launcher_exit_nonzero)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/call.XXXXXX")
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
    cat > "$root/scripts/run-relevant-checks-captured.sh" <<'STUB'
#!/usr/bin/env bash
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
    chmod +x "$root/scripts/run-relevant-checks-captured.sh"
    cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=124\n'
STUB
    cat > "$root/scripts/launch-codex-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=codex\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=0\n'
STUB
    write_min_launch_claude "$root"
    chmod +x "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh" "$root/scripts/launch-claude-ci.sh"
    write_state "$tmp/ship-pr-state.sh" ci-initial
    awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
         /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
         {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    assert_rc "$tmp/rc" 0 "ci_fix_vendor_launcher_exit_nonzero"
    grep -q 'launch-codex-ci.sh' "$call_dir/launcher-calls.txt" || { fail "t4: Codex should run after LAUNCHER_EXIT=124"; return; }
    grep -qE '124|launcher_exit' "$tmp/execution-issues.md" 2>/dev/null || { fail "t4: execution-issues should mention launcher exit 124"; return; }
    ok "ci_fix_vendor_launcher_exit_nonzero: Codex runs; failure cites 124"
    rm -rf "$call_dir"
}

write_min_launch_claude() {
    local root=$1
    cat > "$root/scripts/launch-claude-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'LAUNCHER_EXIT=1\n'
STUB
}

# Common: ci-wait evaluate then merge; checks always ok.
write_ci_wait_merge() {
    local call_dir=$1
    local root=$2
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
    cat > "$root/scripts/run-relevant-checks-captured.sh" <<'STUB'
#!/usr/bin/env bash
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
    chmod +x "$root/scripts/run-relevant-checks-captured.sh"
}

write_all_fail_launchers() {
    local root=$1
    cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=1\n'
STUB
    cp "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh"
    cp "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-claude-ci.sh"
    chmod +x "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh" "$root/scripts/launch-claude-ci.sh"
}

write_state_eval_fail() {
    local tmp=$1
    write_state "$tmp/ship-pr-state.sh" ci-initial
    awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
         /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
         {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
}

# 5) All tiers fail each outer → 9 launches, stall 4.
run_ship_pr_2632_t5() {
    local root tmp call_dir
    root=$(make_repo ci_fix_vendor_all_tiers_fail)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/call.XXXXXX")
    write_ci_wait_merge "$call_dir" "$root"
    cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
    chmod +x "$root/scripts/ci-wait.sh"
    write_all_fail_launchers "$root"
    write_state_eval_fail "$tmp"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" STUB_LINT_FIX_STATUS=applied \
        SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    assert_rc "$tmp/rc" 4 "ci_fix_vendor_all_tiers_fail"
    lc=$(wc -l <"$call_dir/launcher-calls.txt" 2>/dev/null || echo 0)
    [[ "$lc" -eq 9 ]] || { fail "t5: expected 9 launcher lines (3 outer × 3 tiers), got $lc"; return; }
    ok "ci_fix_vendor_all_tiers_fail: nine launcher invocations then stall"
    rm -rf "$call_dir"
}

# 6) Outer budget: gh-run-logs called once per outer (3) alongside 9 launches.
run_ship_pr_2632_t6() {
    local root tmp call_dir
    root=$(make_repo ci_fix_vendor_outer_budget)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/call.XXXXXX")
    cat > "$root/scripts/gh-run-logs.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/gh-run-logs-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
echo "stub log line"
exit 0
STUB
    chmod +x "$root/scripts/gh-run-logs.sh"
    cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
    chmod +x "$root/scripts/ci-wait.sh"
    cat > "$root/scripts/run-relevant-checks-captured.sh" <<'STUB'
#!/usr/bin/env bash
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
    chmod +x "$root/scripts/run-relevant-checks-captured.sh"
    write_all_fail_launchers "$root"
    write_state_eval_fail "$tmp"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" STUB_LINT_FIX_STATUS=applied \
        SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    assert_rc "$tmp/rc" 4 "ci_fix_vendor_outer_budget"
    gh_c=$(cat "$call_dir/gh-run-logs-count" 2>/dev/null || echo 0)
    [[ "$gh_c" -eq 3 ]] || fail "t6: expected gh-run-logs 3 times, got $gh_c"
    lc=$(wc -l <"$call_dir/launcher-calls.txt" 2>/dev/null || echo 0)
    [[ "$lc" -eq 9 ]] || fail "t6: expected 9 launches, got $lc"
    ok "ci_fix_vendor_outer_budget: three gh-run-logs refreshes with nine launches"
    rm -rf "$call_dir"
}

# 7) PLAN_FILE forwarded to all tiers (grep --plan-file in each launcher line).
run_ship_pr_2632_t7() {
    local root tmp call_dir planf
    root=$(make_repo ci_fix_vendor_plan_file_all_tiers)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/call.XXXXXX")
    planf="$tmp/plan.txt"
    echo plan >"$planf"
    printf 'PLAN_FILE=%s\n' "$planf" >"$tmp/session-env.sh"
    write_ci_wait_merge "$call_dir" "$root"
    cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=1\n'
STUB
    cp "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh"
    cat > "$root/scripts/launch-claude-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=0\n'
STUB
    chmod +x "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh" "$root/scripts/launch-claude-ci.sh"
    write_state_eval_fail "$tmp"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    assert_rc "$tmp/rc" 0 "ci_fix_vendor_forwards_plan_file (merge on second ci-wait)"
    grep -F 'launch-cursor-ci.sh' "$call_dir/launcher-calls.txt" | grep -Fq -- '--plan-file' || { fail "t7: cursor missing --plan-file"; return; }
    grep -F 'launch-codex-ci.sh' "$call_dir/launcher-calls.txt" | grep -Fq -- '--plan-file' || { fail "t7: codex missing --plan-file"; return; }
    grep -F 'launch-claude-ci.sh' "$call_dir/launcher-calls.txt" | grep -Fq -- '--plan-file' || { fail "t7: claude missing --plan-file"; return; }
    ok "ci_fix_vendor_forwards_plan_file_to_all_tiers"
    rm -rf "$call_dir"
}

# 8) gh-run-logs rc=0 + redaction → every tier receives --failure-log path ending .redacted
run_ship_pr_2632_t8() {
    local root tmp call_dir line
    root=$(make_repo ci_fix_vendor_failure_log_all_tiers)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/call.XXXXXX")
    write_ci_wait_merge "$call_dir" "$root"
    cat > "$root/scripts/gh-run-logs.sh" <<'STUB'
#!/usr/bin/env bash
echo "ci log line for vendor context"
exit 0
STUB
    chmod +x "$root/scripts/gh-run-logs.sh"
    cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=1\n'
STUB
    cp "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh"
    cat > "$root/scripts/launch-claude-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=0\n'
STUB
    chmod +x "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh" "$root/scripts/launch-claude-ci.sh"
    write_state_eval_fail "$tmp"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    assert_rc "$tmp/rc" 0 "ci_fix_vendor_failure_log_all_tiers"
    lc=$(wc -l <"$call_dir/launcher-calls.txt" 2>/dev/null || echo 0)
    [[ "$lc" -eq 3 ]] || { fail "t8: expected 3 tier launches, got $lc"; return; }
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" ]] && continue
        grep -Fq -- '--failure-log' <<<"$line" || { fail "t8: tier line missing --failure-log: $line"; return; }
        grep -Fq '.redacted' <<<"$line" || { fail "t8: tier line missing .redacted path: $line"; return; }
    done <"$call_dir/launcher-calls.txt"
    ok "ci_fix_vendor_forwards_failure_log_redacted_to_all_tiers"
    rm -rf "$call_dir"
}

# 9) gh-run-logs rc=1 → --failure-log omitted from all launcher lines
run_ship_pr_2632_t9() {
    local root tmp call_dir
    root=$(make_repo ci_fix_vendor_omit_failure_log_rc1)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/call.XXXXXX")
    write_ci_wait_merge "$call_dir" "$root"
    cat > "$root/scripts/gh-run-logs.sh" <<'STUB'
#!/usr/bin/env bash
echo "header only"
exit 1
STUB
    chmod +x "$root/scripts/gh-run-logs.sh"
    write_all_fail_launchers "$root"
    write_state_eval_fail "$tmp"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" STUB_LINT_FIX_STATUS=applied \
        SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    assert_rc "$tmp/rc" 4 "ci_fix_vendor_omit_failure_log_rc1"
    grep -Fq -- '--failure-log' "$call_dir/launcher-calls.txt" 2>/dev/null && { fail "t9: should not pass --failure-log when gh-run-logs rc=1"; return; }
    ok "ci_fix_vendor_omits_failure_log_when_gh_logs_rc_nonzero"
    rm -rf "$call_dir"
}

# 10) redact-secrets.sh fails → --failure-log omitted
run_ship_pr_2632_t10() {
    local root tmp call_dir
    root=$(make_repo ci_fix_vendor_redact_fails)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/call.XXXXXX")
    write_ci_wait_merge "$call_dir" "$root"
    cat > "$root/scripts/gh-run-logs.sh" <<'STUB'
#!/usr/bin/env bash
echo "log body"
exit 0
STUB
    chmod +x "$root/scripts/gh-run-logs.sh"
    printf '#!/bin/sh\nexit 1\n' >"$root/scripts/redact-secrets.sh"
    chmod +x "$root/scripts/redact-secrets.sh"
    write_all_fail_launchers "$root"
    write_state_eval_fail "$tmp"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" STUB_LINT_FIX_STATUS=applied \
        SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    assert_rc "$tmp/rc" 4 "ci_fix_vendor_redact_fails"
    grep -Fq -- '--failure-log' "$call_dir/launcher-calls.txt" 2>/dev/null && { fail "t10: should omit --failure-log when redaction fails"; return; }
    ok "ci_fix_vendor_omits_failure_log_when_redaction_fails"
    rm -rf "$call_dir"
}

# 11) Redacted failure log drops GitHub PAT-shaped token
run_ship_pr_2632_t11() {
    local root tmp call_dir path
    root=$(make_repo ci_fix_vendor_redacts_failure_log_token)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/call.XXXXXX")
    write_ci_wait_merge "$call_dir" "$root"
    cat > "$root/scripts/gh-run-logs.sh" <<'STUB'
#!/usr/bin/env bash
echo "log with ghp_0123456789012345678901 embedded"
exit 0
STUB
    chmod +x "$root/scripts/gh-run-logs.sh"
    cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=1\n'
STUB
    cp "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh"
    cat > "$root/scripts/launch-claude-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=0\n'
STUB
    chmod +x "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh" "$root/scripts/launch-claude-ci.sh"
    write_state_eval_fail "$tmp"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    assert_rc "$tmp/rc" 0 "ci_fix_vendor_redacts_failure_log_token"
    path=$(sed -n 's/.*--failure-log[[:space:]]\{1,\}\([^[:space:]]\{1,\}\).*/\1/p' "$call_dir/launcher-calls.txt" | head -1)
    [[ -n "$path" && -f "$path" ]] || { fail "t11: could not resolve --failure-log path"; return; }
    grep -qF 'ghp_0123456789012345678901' "$path" 2>/dev/null && { fail "t11: redacted file still contains raw token"; return; }
    grep -qF '<REDACTED-TOKEN>' "$path" || { fail "t11: expected redaction marker in failure log file"; return; }
    ok "ci_fix_vendor_redacts_failure_log_content"
    rm -rf "$call_dir"
}

# 12) gh-run-logs rc=3 defers vendor on first attempts; third attempt runs vendor
run_ship_pr_2632_t12() {
    local root tmp call_dir
    root=$(make_repo ci_fix_vendor_rc3_defer)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/call.XXXXXX")
    write_ci_wait_merge "$call_dir" "$root"
    cat > "$root/scripts/gh-run-logs.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ghc"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -lt 2 ]; then
  echo "in progress"
  exit 3
fi
echo "final failure log"
exit 0
STUB
    chmod +x "$root/scripts/gh-run-logs.sh"
    cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=0\n'
STUB
    chmod +x "$root/scripts/launch-cursor-ci.sh"
    cp "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh"
    cp "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-claude-ci.sh"
    chmod +x "$root/scripts/launch-codex-ci.sh" "$root/scripts/launch-claude-ci.sh"
    write_state_eval_fail "$tmp"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    assert_rc "$tmp/rc" 0 "ci_fix_vendor_rc3_defer_then_success"
    gh_c=$(cat "$call_dir/ghc" 2>/dev/null || echo 0)
    [[ "$gh_c" -eq 3 ]] || { fail "t12: expected 3 gh-run-logs calls, got $gh_c"; return; }
    lc=$(wc -l <"$call_dir/launcher-calls.txt" 2>/dev/null || echo 0)
    [[ "$lc" -eq 1 ]] || { fail "t12: expected 1 launcher line (vendor only on third outer), got $lc"; return; }
    grep -Fq 'gh-run-logs rc=3' "$tmp/out" || { fail "t12: expected deferral breadcrumb"; return; }
    ok "ci_fix_vendor_rc3_short_circuits_vendor_then_recover"
    rm -rf "$call_dir"
}

# 21) Missing launch-claude-ci.sh → Warnings + 3 outer × 2 tiers = 6 launches
run_ship_pr_2632_t21() {
    local root tmp call_dir
    root=$(make_repo ci_fix_vendor_missing_claude_launcher)
    tmp=$(make_tmpdir)
    call_dir=$(mktemp -d "$tmp/call.XXXXXX")
    write_ci_wait_merge "$call_dir" "$root"
    write_all_fail_launchers "$root"
    rm -f "$root/scripts/launch-claude-ci.sh"
    write_state_eval_fail "$tmp"
    set +e
    (cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" STUB_LINT_FIX_STATUS=applied \
        SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
        "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
        --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
    printf '%s' "$?" >"$tmp/rc"
    set -e
    assert_rc "$tmp/rc" 4 "ci_fix_vendor_missing_claude_launcher"
    lc=$(wc -l <"$call_dir/launcher-calls.txt" 2>/dev/null || echo 0)
    [[ "$lc" -eq 6 ]] || { fail "t21: expected 6 launches (3 outer × 2 tiers), got $lc"; return; }
    grep -Fq 'launch-claude-ci.sh unavailable' "$tmp/execution-issues.md" 2>/dev/null || \
        grep -Fq 'launch-claude-ci.sh unavailable' "$tmp/out" || { fail "t21: expected missing-claude warning"; return; }
    ok "ci_fix_vendor_skips_claude_when_launcher_missing"
    rm -rf "$call_dir"
}

run_ship_pr_2632_t4
run_ship_pr_2632_t5
run_ship_pr_2632_t6
run_ship_pr_2632_t7
run_ship_pr_2632_t8
run_ship_pr_2632_t9
run_ship_pr_2632_t10
run_ship_pr_2632_t11
run_ship_pr_2632_t12
run_ship_pr_2632_t21
