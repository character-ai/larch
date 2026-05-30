#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT=/Users/zhupanov/larch4
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-collect-findings.XXXXXX")
export LARCH_EXECUTION_ISSUES_LOG="$TMP/execution-issues.md"
COLLECTOR="$REPO_ROOT/scripts/collect-agent-results.sh"
ext_fail_a="$TMP/codex-generalist-fail-a.txt"
ext_fail_b="$TMP/cursor-specialist-fail-b.txt"
: > "$ext_fail_a"
: > "$ext_fail_b"
printf '1\n' > "${ext_fail_a}.done"
printf '1\n' > "${ext_fail_b}.done"
printf 'non-transient failure\n' > "${ext_fail_a}.diag"
printf 'non-transient failure\n' > "${ext_fail_b}.diag"
printf 'external stderr tail alpha\n' > "${ext_fail_a}.stderr-tail"
printf 'external stderr tail beta\n' > "${ext_fail_b}.stderr-tail"
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 \
    LARCH_QUIET_DISABLE=1 "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode \
    "$ext_fail_a" "$ext_fail_b" >"$TMP/ext-fail.stdout" 2>"$TMP/ext-fail-collector.stderr"
wc -c "$TMP/ext-fail-collector.stderr"
grep alpha "$TMP/ext-fail-collector.stderr" || echo NO_ALPHA
cat "$TMP/ext-fail-collector.stderr"
