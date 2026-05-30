#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT=/Users/zhupanov/larch4
SCRIPT="$REPO_ROOT/skills/review/scripts/collect-findings.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-collect-findings.XXXXXX")
export LARCH_EXECUTION_ISSUES_LOG="$TMP/execution-issues.md"
ext_fail_a="$TMP/codex-generalist-fail-a.txt"
: > "$ext_fail_a"
printf '1\n' > "${ext_fail_a}.done"
printf 'non-transient failure\n' > "${ext_fail_a}.diag"
printf 'external stderr tail alpha\n' > "${ext_fail_a}.stderr-tail"
set +e
WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 LARCH_QUIET_DISABLE=1 "$SCRIPT" \
    --external-output-files "$ext_fail_a" --mode diff --timeout 5 \
    --findings-file "$TMP/findings-cf-fail.md" --oos-file "$TMP/oos-cf-fail.md" \
    2>"$TMP/cf-fail-wrapper.stderr"
set -e
wc -c "$TMP/cf-fail-wrapper.stderr" "$TMP/collect-agent-results.stderr" 2>/dev/null
grep alpha "$TMP/cf-fail-wrapper.stderr" || echo NO_WRAP_ALPHA
grep alpha "$TMP/collect-agent-results.stderr" 2>/dev/null || echo NO_CAP_ALPHA
cat "$TMP/collect-agent-results.stderr" 2>/dev/null || true
echo "collector results:"
cat "$TMP/collector-results.env" 2>/dev/null || true
echo "collector log bytes: $(wc -c <"$TMP/collect-agent-results.log" 2>/dev/null || echo 0)"
