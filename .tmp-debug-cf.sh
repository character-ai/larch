#!/usr/bin/env bash
set -euo pipefail
REPO=/Users/zhupanov/larch4
TMP=$(mktemp -d)
export LARCH_EXECUTION_ISSUES_LOG="$TMP/execution-issues.md"
unset LARCH_QUIET_DISABLE || true
ext="$TMP/codex-generalist-fail-a.txt"
: > "$ext"
printf '1\n' > "${ext}.done"
printf 'non-transient failure\n' > "${ext}.diag"
printf 'external stderr tail alpha\n' > "${ext}.stderr-tail"
collector_results_file="$TMP/collector-results.env"
collector_stderr="$TMP/collect-agent-results.stderr"
ext2="$TMP/cursor-specialist-fail-b.txt"
: > "$ext2"
printf '1\n' > "${ext2}.done"
printf 'non-transient failure\n' > "${ext2}.diag"
printf 'external stderr tail beta\n' > "${ext2}.stderr-tail"
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 \
  LARCH_QUIET_DISABLE=1 "$REPO/scripts/collect-agent-results.sh" --timeout 5 --substantive-validation --validation-mode \
  "$ext" "$ext2" >"$collector_results_file" 2>"$collector_stderr"
echo "stderr bytes: $(wc -c <"$collector_stderr")"
grep -F 'failed agent stderr tail' "$collector_stderr" || echo 'no fence'
echo "tail file after collector:"
wc -c "${ext}.stderr-tail" 2>/dev/null || echo missing
cat "${ext}.stderr-tail" 2>/dev/null || true
